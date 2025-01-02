import os
import re
from PyPDF2 import PdfMerger
from pyrogram import Client, filters

class MergePdfHandler:
    def __init__(self):
        self.merge_sessions = {}
        self.base_path = os.path.join("Downloads", "Mergepdf")
        os.makedirs(self.base_path, exist_ok=True)

    def get_user_folder(self, chat_id):
        folder_path = os.path.join(self.base_path, str(chat_id))
        os.makedirs(folder_path, exist_ok=True)
        return folder_path

    def clean_filename(self, filename):
        cleaned = re.sub(r'[<>:"/\\|?*]', '', filename)
        cleaned = cleaned.strip()
        if not cleaned.lower().endswith('.pdf'):
            cleaned += '.pdf'
        if len(cleaned) <= 4:
            cleaned = 'merged.pdf'
        return cleaned

    def cleanup_user_data(self, chat_id):
        if chat_id in self.merge_sessions:
            session = self.merge_sessions[chat_id]
            folder_path = session.get('folder_path')
            if folder_path and os.path.exists(folder_path):
                for file in os.listdir(folder_path):
                    try:
                        os.remove(os.path.join(folder_path, file))
                    except Exception as e:
                        print(f"Error removing file: {e}")
            del self.merge_sessions[chat_id]

    async def start_merge(self, client, message):
        chat_id = message.chat.id
        self.merge_sessions[chat_id] = {
            'pdfs_received': [],
            'status_messages': [],
            'in_progress': True,
            'folder_path': self.get_user_folder(chat_id)
        }
        await message.reply_text(
            "Please send the PDFs one by one (maximum 10 files, 20MB each).\n"
            "When finished, you can either:\n"
            "• Send 'DONE' to merge with default filename\n"
            "• Send any other text to use as the merged file's name"
        )

    async def handle_pdf(self, client, message):
        chat_id = message.chat.id
        if chat_id not in self.merge_sessions:
            return

        session = self.merge_sessions[chat_id]
        if not session['in_progress']:
            return

        if not (message.document.mime_type == "application/pdf" or
                (message.document.file_name and message.document.file_name.lower().endswith('.pdf'))):
            await message.reply_text("❌ Please send only PDF files.")
            return

        file_size = message.document.file_size
        if file_size > 5 * 1024 * 1024:
            await message.reply_text("❌ File size exceeds the limit of 5 MB")
            return

        if len(session['pdfs_received']) >= 50:
            await message.reply_text("❌ Maximum file limit of 50 reached. Send 'DONE' or filename to merge.")
            return

        file_info = {
            'file_id': message.document.file_id,
            'file_name': message.document.file_name or f"document_{len(session['pdfs_received']) + 1}.pdf",
            'file_size': file_size
        }
        session['pdfs_received'].append(file_info)

        if session['status_messages']:
            try:
                await client.delete_messages(chat_id, session['status_messages'][-1].message_id)
                session['status_messages'].pop()
            except Exception:
                pass

        count = len(session['pdfs_received'])
        reply = await message.reply_text(
            f"✅ {count} PDF{'s' if count > 1 else ''} received:\n" +
            "\n".join(f"{i + 1}. {pdf['file_name']}" for i, pdf in enumerate(session['pdfs_received'])) +
            "\n\nSend more PDFs, 'DONE' for default filename, or send custom filename for the merged PDF."
        )
        session['status_messages'].append(reply)

    async def handle_merge_complete(self, client, message):
        chat_id = message.chat.id
        if chat_id not in self.merge_sessions:
            return

        session = self.merge_sessions[chat_id]
        if not session['in_progress']:
            return

        session['in_progress'] = False

        if not session['pdfs_received']:
            await message.reply_text("❌ No PDFs received. Please send PDFs first.")
            self.cleanup_user_data(chat_id)
            return

        total_size = sum(pdf['file_size'] for pdf in session['pdfs_received'])
        if total_size > 100 * 1024 * 1024:
            await message.reply_text("❌ Total file size exceeds 100 MB limit.")
            self.cleanup_user_data(chat_id)
            return

        output_filename = 'merged.pdf' if message.text.strip().upper() == 'DONE' else self.clean_filename(message.text.strip())
        progress_msg = None
        temp_files = []

        try:
            progress_msg = await message.reply_text("🔄 Merging PDFs...")
            merger = PdfMerger()

            for i, pdf in enumerate(session['pdfs_received']):
                file_path = os.path.join(session['folder_path'], f"temp_{i}.pdf")
                temp_files.append(file_path)
                await client.download_media(pdf['file_id'], file_path)
                merger.append(file_path)

            output_path = os.path.join(session['folder_path'], output_filename)
            merger.write(output_path)
            merger.close()

            await client.send_document(
                chat_id,
                output_path,
                caption=f"✅ Successfully merged {len(session['pdfs_received'])} PDFs into '{output_filename}'!"
            )

        except Exception as e:
            await message.reply_text(f"❌ Error merging PDFs: {str(e)}")

        finally:
            if progress_msg:
                try:
                    await progress_msg.delete()
                except Exception:
                    pass

            self.cleanup_user_data(chat_id)
