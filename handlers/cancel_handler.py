"""
Handler for cancel command
"""
from pyrogram import Client, filters
from utils.file_utils import cleanup_user_data
from handlers.unarchive_handler import cancel_extraction

class CancelHandler:
    def __init__(self, user_settings, pdf_handler=None, split_pdf_handler=None, pdf2image_handler=None, merge_pdf_handler=None):
        self.user_settings = user_settings
        self.pdf_handler = pdf_handler
        self.split_pdf_handler = split_pdf_handler
        self.pdf2image_handler = pdf2image_handler
        self.merge_pdf_handler = merge_pdf_handler

    async def handle_cancel(self, client, message):
        try:
            chat_id = message.chat.id
            
            # Check if there's an active resize operation
            resize_cancelled = False
            if chat_id in self.user_settings:
                cleanup_user_data(chat_id, self.user_settings)
                resize_cancelled = True

            # Check if there's an active PDF operation
            pdf_cancelled = False
            if self.pdf_handler and chat_id in self.pdf_handler.user_images:
                self.pdf_handler.cleanup_user_data(chat_id)
                pdf_cancelled = True

            # Check if there's an active PDF split operation
            split_cancelled = False
            if self.split_pdf_handler and chat_id in self.split_pdf_handler.processing_status:
                self.split_pdf_handler.cleanup_user_data(chat_id)
                split_cancelled = True

            # Check if there's an active PDF to image operation
            pdf2image_cancelled = False
            if self.pdf2image_handler and chat_id in self.pdf2image_handler.user_pdfs:
                del self.pdf2image_handler.user_pdfs[chat_id]
                pdf2image_cancelled = True

            # Add to existing cancel checks
            merge_cancelled = False
            if self.merge_pdf_handler and chat_id in self.merge_pdf_handler.merge_sessions:
                self.merge_pdf_handler.cleanup_user_data(chat_id)
                merge_cancelled = True

            # Check if there's an active extraction
            archive_cancelled = await cancel_extraction(chat_id)

            if resize_cancelled or pdf_cancelled or split_cancelled or pdf2image_cancelled or archive_cancelled or merge_cancelled:
                await message.reply_text("✅ Current operation has been cancelled. You can start a new operation.")
            else:
                await message.reply_text("No active operation to cancel.")
                
        except Exception as e:
            print(f"Error in handle_cancel: {e}")
            await message.reply_text("An error occurred while trying to cancel the operation.")
