from pyrogram import Client
from pyrogram.types import Message
import os
import time
from typing import Tuple, List, Dict
from pyunpack import Archive
import shutil
import asyncio
from urllib.parse import unquote

SUPPORTED_ARCHIVE_TYPES = {
    'application/zip', 'application/x-rar-compressed',
    'application/x-7z-compressed', 'application/x-zip-compressed'
}

MAX_FILE_SIZE = 2 * 1024 * 1024 * 1024  # 2GB
ARCHIVE_DIR = os.path.join("Downloads", "archive_op")
os.makedirs(ARCHIVE_DIR, exist_ok=True)

# Track active downloads and extractions
active_extractions: Dict[int, Dict] = {}
download_tasks: Dict[int, asyncio.Task] = {}

async def start_unarchive(client: Client, message: Message):
    """Handler for /unarchive command"""
    await message.reply_text(
        "Send me an archive file (ZIP/RAR/7Z) to extract.\n"
        f"Maximum file size: {MAX_FILE_SIZE/(1024*1024*1024):.1f}GB\n"
        "Use /cancel to stop the extraction process."
    )

async def progress_callback(current, total, status_msg, text, start_time):
    try:
        percentage = current * 100 / total
        speed = current / (time.time() - start_time)
        elapsed_time = round(time.time() - start_time)
        
        if speed > 0:
            eta = round((total - current) / speed)
        else:
            eta = 0
            
        await status_msg.edit_text(
            f"{text}\n"
            f"Progress: {percentage:.1f}%\n"
            f"Speed: {get_size_format(speed)}/s\n"
            f"ETA: {format_time(eta)}\n"
            f"Elapsed: {format_time(elapsed_time)}"
        )
    except:
        pass

def get_size_format(b):
    for unit in ['B', 'KB', 'MB', 'GB']:
        if b < 1024.0:
            return f"{b:.2f} {unit}"
        b /= 1024.0
    return f"{b:.2f} TB"

def format_time(seconds):
    hours = seconds // 3600
    minutes = (seconds % 3600) // 60
    seconds = seconds % 60
    return f"{hours:02d}:{minutes:02d}:{seconds:02d}"

def get_directory_structure_for_file(path: str, file_name: str) -> List[str]:
    """Get directory structure for specific file"""
    structure = []
    rel_path = file_name.split(os.sep)
    current_path = ""
    
    for i, part in enumerate(rel_path):
        if i == len(rel_path) - 1:  # Last part (file)
            structure.append("  " * i + f"📄 {part}")
        else:  # Directory
            structure.append("  " * i + f"📁 {part}")
    
    return structure

async def download_file(client, message, file_path, progress_args):
    try:
        await message.download(
            file_path,
            progress=progress_callback,
            progress_args=progress_args
        )
        return True
    except asyncio.CancelledError:
        return False

def cleanup_extraction(chat_id: int):
    """Clean up temporary files and data"""
    if chat_id in active_extractions:
        data = active_extractions[chat_id]
        try:
            if os.path.exists(data['input_path']):
                os.remove(data['input_path'])
            if os.path.exists(data['extract_dir']):
                shutil.rmtree(data['extract_dir'])
        except Exception as e:
            print(f"Cleanup error: {str(e)}")
        finally:
            del active_extractions[chat_id]

async def cancel_extraction(chat_id: int) -> bool:
    """Cancel ongoing extraction process"""
    if chat_id in download_tasks:
        download_tasks[chat_id].cancel()
        del download_tasks[chat_id]
        
    if chat_id in active_extractions:
        data = active_extractions[chat_id]
        try:
            await data['status_msg'].edit_text("❌ Operation cancelled.")
        except:
            pass
        cleanup_extraction(chat_id)
        return True
    return False

async def handle_archive(client: Client, message: Message):
    """Main handler for archive files"""
    if not message.document or message.document.mime_type not in SUPPORTED_ARCHIVE_TYPES:
        return

    chat_id = message.chat.id
    
    if message.document.file_size > MAX_FILE_SIZE:
        await message.reply_text("File is too large. Maximum size allowed is 2GB.")
        return

    status_msg = await message.reply_text("📥 Downloading archive...")
    
    # Create unique directory for this extraction
    extract_id = f"{message.from_user.id}_{int(time.time())}"
    input_path = os.path.join(ARCHIVE_DIR, f"archive_{extract_id}{os.path.splitext(message.document.file_name)[1]}")
    extract_dir = os.path.join(ARCHIVE_DIR, f"extracted_{extract_id}")
    os.makedirs(extract_dir, exist_ok=True)

    # Store extraction info
    active_extractions[chat_id] = {
        'input_path': input_path,
        'extract_dir': extract_dir,
        'status_msg': status_msg
    }

    try:
        # Create download task
        download_task = asyncio.create_task(
            download_file(client, message, input_path, 
                        (status_msg, "Downloading archive...", time.time()))
        )
        download_tasks[chat_id] = download_task
        
        # Wait for download to complete
        download_success = await download_task

        if not download_success:
            await status_msg.edit_text("❌ Download cancelled.")
            cleanup_extraction(chat_id)
            return

        if chat_id not in active_extractions:
            return

        await status_msg.edit_text("⚙️ Extracting files...")
        
        # Extract using pyunpack
        try:
            Archive(input_path).extractall(extract_dir)
            extracted_files = []
            for root, _, files in os.walk(extract_dir):
                for file in files:
                    rel_path = os.path.relpath(os.path.join(root, file), extract_dir)
                    extracted_files.append(rel_path)
        except Exception as e:
            await status_msg.edit_text(f"❌ Extraction error: {str(e)}")
            return

        await status_msg.edit_text(f"📤 Sending {len(extracted_files)} files...")

        for i, file_name in enumerate(extracted_files, 1):
            if chat_id not in active_extractions:
                return

            file_path = os.path.join(extract_dir, file_name)
            if os.path.isfile(file_path):
                try:
                    # Get file-specific directory structure
                    dir_structure = get_directory_structure_for_file(extract_dir, file_name)
                    structure_text = "📂 File Location:\n" + "\n".join(dir_structure)

                    # Delete previous status message
                    await status_msg.delete()
                    
                    # Create new status message
                    status_msg = await message.reply_text(f"📤 Sending file {i}/{len(extracted_files)}...")
                    active_extractions[chat_id]['status_msg'] = status_msg

                    await message.reply_document(
                        file_path,
                        caption=structure_text,
                        progress=progress_callback,
                        progress_args=(status_msg, f"Sending file {i}/{len(extracted_files)}...", time.time())
                    )
                except Exception as e:
                    await message.reply_text(f"❌ Error sending {file_name}: {str(e)}")

        if chat_id in active_extractions:
            await client.send_message(chat_id, "✅ Extraction complete!")

    except Exception as e:
        if chat_id in active_extractions:
            await status_msg.edit_text(f"❌ Error: {str(e)}")
    finally:
        cleanup_extraction(chat_id)
