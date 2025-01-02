import os
import pymupdf
from pyrogram import Client, filters
from utils.file_utils import create_user_folder

class PdfToImageHandler:
    def __init__(self):
        self.user_pdfs = {}

    async def handle_pdf_to_image(self, client, message):
        try:
            chat_id = message.chat.id
            
            # First check if message is a reply
            if not message.reply_to_message:
                await message.reply_text("❌ Please reply to a PDF file with /pdf2image command.")
                return
            
            # Then check if the replied message has a document
            if not message.reply_to_message.document:
                await message.reply_text("❌ Please reply to a PDF file, not a message.")
                return
            
            # Finally check if the document is a PDF
            if not message.reply_to_message.document.file_name.lower().endswith('.pdf'):
                await message.reply_text("❌ The file must be a PDF document.")
                return

            # Create user-specific folder
            user_folder = create_user_folder(chat_id, "Downloads/pdf2image")

            # Rest of your code remains the same
            pdf_path = await client.download_media(
                message.reply_to_message.document, 
                file_name=os.path.join(user_folder, message.reply_to_message.document.file_name)
            )

            pdf_document = pymupdf.open(pdf_path)
            total_pages = len(pdf_document)

            status_message = await message.reply_text("Starting PDF to image conversion...")

            for i in range(total_pages):
                page = pdf_document[i]
                zoom = 2
                mat = pymupdf.Matrix(zoom, zoom)
                pix = page.get_pixmap(matrix=mat)
                image_name = os.path.join(user_folder, f"page_{i + 1}.png")
                pix.save(image_name)

                await status_message.edit_text(
                    f"📤 Converting and sending page {i + 1}/{total_pages} ({((i + 1)/total_pages)*100:.1f}%)"
                )

                await client.send_document(
                    chat_id,
                    image_name,
                    caption=f"Page {i + 1} of {total_pages}"
                )

                if os.path.exists(image_name):
                    os.remove(image_name)

            pdf_document.close()
            if os.path.exists(pdf_path):
                os.remove(pdf_path)
            
            await status_message.delete()
            await message.reply_text("✅ PDF to image conversion completed.")

        except Exception as e:
            print(f"Error in handle_pdf_to_image: {e}")
            await message.reply_text("❌ An error occurred during the PDF to image conversion.")
            if 'pdf_document' in locals():
                pdf_document.close()
