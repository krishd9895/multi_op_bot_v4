import os
import re
from PIL import Image
from pyrogram import Client, filters
from utils.logging_utils import setup_logging

logger = setup_logging()

class ImageToPdfHandler:
    def __init__(self):
        self.user_images = {}
        self.user_pdf_name = {}
        # Add state tracking
        self.waiting_for_images = {}
        self.waiting_for_name = {}

    def get_user_dir(self, chat_id):
        """Create and return a user-specific directory"""
        user_dir = os.path.join("Downloads", "PDF", str(chat_id))
        os.makedirs(user_dir, exist_ok=True)
        return user_dir

    async def start_image_to_pdf(self, client, message):
        """Initialize the PDF creation process"""
        logger.info("start_image_to_pdf called")
        chat_id = message.chat.id
        logger.info(f"Starting PDF creation for chat_id: {chat_id}")
        
        # Initialize user state
        self.user_images[chat_id] = []
        self.waiting_for_images[chat_id] = True
        self.waiting_for_name[chat_id] = False
        
        self.get_user_dir(chat_id)
        await message.reply_text("Send the images you want to convert to PDF.\nWhen you're done, type 'go'.")

    async def handle_pdf_image(self, client, message):
        """Handle incoming images or documents for PDF creation"""
        chat_id = message.chat.id
        logger.info(f"Received image or document for chat_id: {chat_id}")
        
        if chat_id not in self.waiting_for_images or not self.waiting_for_images[chat_id]:
            logger.info(f"Ignoring image/document - user not in image collection state: {chat_id}")
            return
    
        user_dir = self.get_user_dir(chat_id)
        try:
            file_path = None
            if message.photo:
                # Handle photo message
                file_path = await message.download()
                file_extension = ".jpg"
            elif message.document:
                # Handle document message
                mime_type = message.document.mime_type
                if mime_type.startswith("image/"):
                    file_path = await message.download()
                    file_extension = os.path.splitext(message.document.file_name)[1].lower()
                    if file_extension not in [".jpg", ".jpeg", ".png", ".gif"]:
                        file_extension = ".jpg"  # Default to .jpg if extension is not recognized
                else:
                    await message.reply_text("Please send only image files.")
                    return
            
            if not file_path:
                await message.reply_text("Please send an image or an image file (jpg, jpeg, png, gif).")
                return
    
            new_file_name = f"{len(self.user_images[chat_id])}{file_extension}"
            new_file_path = os.path.join(user_dir, new_file_name)
            os.rename(file_path, new_file_path)
            self.user_images[chat_id].append(new_file_path)
            await message.reply_text(f"Received image {len(self.user_images[chat_id])}. Send more or type 'go'.")
        except Exception as e:
            logger.error(f"Error processing image/document: {str(e)}")
            await message.reply_text(f"Error processing image/document: {str(e)}")



    async def handle_go_command(self, client, message):
        """Handle 'go' command to proceed with PDF creation"""
        chat_id = message.chat.id
        logger.info(f"Received go command for chat_id: {chat_id}")
        
        if chat_id not in self.user_images or not self.user_images[chat_id]:
            await message.reply_text("You haven't sent any images yet.")
            return
            
        self.waiting_for_images[chat_id] = False
        self.waiting_for_name[chat_id] = True
        await message.reply_text("Please send a name for your PDF file. If you want to skip, click /skip.")

    async def handle_pdf_name(self, client, message):
        """Handle PDF name input"""
        chat_id = message.chat.id
        logger.info(f"Received PDF name for chat_id: {chat_id}")
        
        if not self.waiting_for_name.get(chat_id):
            return
            
        if chat_id in self.user_images:
            pdf_name = re.sub(r'[<>:"/\\|?*]', '', message.text.strip())
            self.user_pdf_name[chat_id] = f"{pdf_name}.pdf"
            await self.create_pdf(client, message)

    async def handle_skip_name(self, client, message):
        """Handle skip command for PDF name"""
        chat_id = message.chat.id
        logger.info(f"Received skip command for chat_id: {chat_id}")
        
        if not self.waiting_for_name.get(chat_id):
            return
            
        if chat_id in self.user_images:
            pdf_name = self.user_pdf_name.get(chat_id, "images.pdf")
            self.user_pdf_name[chat_id] = pdf_name
            await self.create_pdf(client, message)

    async def create_pdf(self, client, message):
        """Create and send PDF file"""
        chat_id = message.chat.id
        logger.info(f"Creating PDF for chat_id: {chat_id}")
        
        if chat_id not in self.user_images or not self.user_images[chat_id]:
            await message.reply_text("You haven't sent any images yet.")
            return
    
        try:
            pdf_filename = self.user_pdf_name.get(chat_id, "images.pdf")
            pdf_filename = os.path.basename(pdf_filename)  # Ensure only the filename is used
            user_dir = self.get_user_dir(chat_id)
            pdf_path = os.path.join(user_dir, pdf_filename)
    
            images = [Image.open(img).convert('RGB') for img in self.user_images[chat_id]]
            total_pages = len(images)
            images[0].save(pdf_path, save_all=True, append_images=images[1:])
    
            with open(pdf_path, 'rb') as pdf_file:
                await client.send_document(chat_id, pdf_file, file_name=pdf_filename)  # Use pdf_filename here
    
            # Cleanup
            await self.cleanup_user_data(chat_id, pdf_path)
            await message.reply_text(f"Your PDF has been created and sent! It contains {total_pages} pages.")
            
        except Exception as e:
            logger.error(f"Error creating PDF: {str(e)}")
            await message.reply_text(f"Error creating PDF: {str(e)}")
            await self.cleanup_user_data(chat_id, pdf_path)


    async def handle_cancel(self, client, message):
        """Handle cancel command to clean up and stop the process"""
        chat_id = message.chat.id
        logger.info(f"Received cancel command for chat_id: {chat_id}")
        await self.cleanup_user_data(chat_id)
        await message.reply_text("PDF creation process has been canceled, and all data has been cleaned up.")


    async def cleanup_user_data(self, chat_id, pdf_path=None):
        """Clean up user data and files"""
        if chat_id in self.user_images:
            user_dir = self.get_user_dir(chat_id)
            for img in self.user_images[chat_id]:
                try:
                    os.remove(img)
                except OSError:
                    pass
            try:
                os.rmdir(user_dir)
            except OSError:
                pass
            del self.user_images[chat_id]
        
        if pdf_path and os.path.exists(pdf_path):
            try:
                os.remove(pdf_path)
            except OSError:
                pass
            
        if chat_id in self.user_pdf_name:
            del self.user_pdf_name[chat_id]
            
        if chat_id in self.waiting_for_images:
            del self.waiting_for_images[chat_id]
            
        if chat_id in self.waiting_for_name:
            del self.waiting_for_name[chat_id]
