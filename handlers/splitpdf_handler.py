"""
Handler for splitting PDF files
"""
import os
from pyrogram import filters
from PyPDF2 import PdfReader, PdfWriter
from utils.logging_utils import setup_logging

logger = setup_logging()

class SplitPdfHandler:
    def __init__(self):
        self.processing_status = {}
        self.base_dir = "Downloads/Split"
        
        # Create base directory if it doesn't exist
        if not os.path.exists(self.base_dir):
            os.makedirs(self.base_dir)

    def get_user_dir(self, chat_id):
        user_dir = os.path.join(self.base_dir, f"{chat_id}_pdfsplit")
        if not os.path.exists(user_dir):
            os.makedirs(user_dir)
        return user_dir

    async def handle_split_pdf(self, client, message):
        if not message.reply_to_message or not message.reply_to_message.document:
            await message.reply_text("Please reply to a PDF file with the /splitpdf command.")
            return

        chat_id = message.chat.id
        replied_document = message.reply_to_message.document
        file_id = replied_document.file_id
        file_size = replied_document.file_size
        file_name = replied_document.file_name

        if not file_name.lower().endswith('.pdf'):
            await message.reply_text("Invalid file format. Please reply to a valid PDF file.")
            return

        if file_size > 200 * 1024 * 1024:  # 200 MB limit
            await message.reply_text("Sorry, the maximum file size allowed is 200 MB.")
            return

        if self.processing_status.get(chat_id, False):
            await message.reply_text(
                "Sorry, another PDF file is currently being processed. Please wait or use /cancel."
            )
            return

        user_dir = self.get_user_dir(chat_id)
        self.processing_status[chat_id] = True
        status_message = await message.reply_text("📥 Downloading PDF file...")
        
        try:
            # Download file
            pdf_path = os.path.join(user_dir, f"{file_id}.pdf")
            downloaded_file_path = await client.download_media(
                replied_document,
                file_name=pdf_path,
                progress=lambda current, total: self.handle_progress(
                    current, total, status_message, "Downloading"
                )
            )
            
            if not self.processing_status.get(chat_id, False):
                await status_message.edit_text("❌ Process cancelled by user.")
                return
        
            # Delete the previous status message and create a new one
            await status_message.delete()
            status_message = await message.reply_text("📄 Analyzing PDF file...")
            
            if os.path.exists(pdf_path):
                # Read PDF and get total pages
                pdf = PdfReader(pdf_path)
                total_pages = len(pdf.pages)
        
                # Delete the previous status message and create a new one
                await status_message.delete()
                status_message = await message.reply_text(f"📑 Found {total_pages} pages. Starting split process...")
        
                pages = self.split_pdf_pages(pdf_path)
                if not pages:
                    await status_message.edit_text("❌ Error: Could not split the PDF. It might be empty.")
                    return
        
                for i, page in enumerate(pages):
                    if not self.processing_status.get(chat_id, False):
                        await status_message.edit_text("❌ PDF splitting cancelled.")
                        return
                        
                    page_name = os.path.join(user_dir, f"page_{i + 1}.pdf")
                    with open(page_name, 'wb') as f:
                        page.write(f)
                    
                    # Delete the previous status message and create a new one
                    await status_message.delete()
                    status_message = await message.reply_text(
                        f"📤 Sending page {i + 1}/{total_pages} ({((i + 1)/total_pages)*100:.1f}%)"
                    )
                    
                    await client.send_document(
                        chat_id,
                        page_name,
                        caption=f"Page {i + 1} of {total_pages}"
                    )
                    
                    if os.path.exists(page_name):
                        os.remove(page_name)
        
                await client.send_message(chat_id, "✅ PDF splitting completed successfully!")
            else:
                await client.send_message(chat_id, "❌ Error: Failed to process the PDF file.")

                
        except Exception as e:
            logger.error(f"Error in split_pdf: {str(e)}")
            error_message = str(e)
            if "No such file or directory" in error_message:
                await status_message.edit_text("❌ Process was cancelled or interrupted.")
            else:
                await status_message.edit_text(f"❌ An error occurred: {error_message}")
        finally:
            self.cleanup_user_data(chat_id)

    async def handle_progress(self, current, total, message, action):
        try:
            percent = (current * 100) / total
            progress_text = f"{action}: {percent:.1f}%\n"
            progress_text += self.create_progress_bar(percent)
            await message.edit_text(progress_text)
        except Exception as e:
            logger.error(f"Error updating progress: {e}")

    def create_progress_bar(self, percent):
        completed = int(percent / 10)
        remaining = 10 - completed
        return f"[{'█' * completed}{'░' * remaining}]"

    def split_pdf_pages(self, file_path):
        try:
            input_pdf = PdfReader(file_path)
            pages = []
            for i in range(len(input_pdf.pages)):
                output = PdfWriter()
                output.add_page(input_pdf.pages[i])
                pages.append(output)
            return pages
        except Exception as e:
            logger.error(f"Error splitting PDF: {e}")
            return []

    def cleanup_user_data(self, chat_id):
        """Clean up user data and reset processing status"""
        try:
            user_dir = self.get_user_dir(chat_id)
            if os.path.exists(user_dir):
                for file in os.listdir(user_dir):
                    try:
                        file_path = os.path.join(user_dir, file)
                        if os.path.exists(file_path):
                            os.remove(file_path)
                    except Exception as e:
                        logger.error(f"Error removing file {file}: {e}")
        except Exception as e:
            logger.error(f"Error in cleanup: {e}")
        finally:
            self.processing_status[chat_id] = False
