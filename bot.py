"""
Main bot file that initializes and runs the bot
"""
import re
from pyrogram import Client, filters
from config.settings import API_ID, API_HASH, BOT_TOKEN
from handlers.help_handler import HelpHandler
from handlers.image_handler import ImageHandler
from handlers.image2pdf_handler import ImageToPdfHandler
from handlers.cancel_handler import CancelHandler
from handlers.unarchive_handler import start_unarchive, handle_archive
from handlers.splitpdf_handler import SplitPdfHandler
from handlers.pdf2image_handler import PdfToImageHandler
from handlers.mergepdf_handler import MergePdfHandler
from handlers.fileconverter_handler import FileConverterHandler
from utils.logging_utils import setup_logging

from webserver import run_flask  # Import the Flask web server function
from threading import Thread  # For running Flask in a separate thread

logger = setup_logging()

class Bot:
    def __init__(self):
        self.app = Client(
            "pyrogram_bot",
            api_id=API_ID,
            api_hash=API_HASH,
            bot_token=BOT_TOKEN
        )
        # Initialize all handlers first
        self.image_handler = ImageHandler()
        self.pdf_handler = ImageToPdfHandler()
        self.split_pdf_handler = SplitPdfHandler()
        self.pdf2image_handler = PdfToImageHandler()
        self.merge_pdf_handler = MergePdfHandler()
        self.file_converter_handler = FileConverterHandler()
        
        # Initialize cancel handler after all other handlers
        self.cancel_handler = CancelHandler(
            user_settings=self.image_handler.user_settings,
            pdf_handler=self.pdf_handler,
            split_pdf_handler=self.split_pdf_handler,
            pdf2image_handler=self.pdf2image_handler,
            merge_pdf_handler=self.merge_pdf_handler,
            file_converter_handler=self.file_converter_handler
        )
        
        self.setup_handlers()
    
    def setup_handlers(self):
        # Help handler
        @self.app.on_message(filters.command("help"))
        async def help_command(client, message):
            await HelpHandler.handle_help(client, message)

        # Image resize handlers
        @self.app.on_message(filters.command("resizeimage"))
        async def resize_command(client, message):
            await self.image_handler.handle_resize_image(client, message)

        @self.app.on_callback_query()
        async def callback(client, callback_query):
            chat_id = callback_query.message.chat.id
            if chat_id in self.image_handler.user_settings:
                await self.image_handler.handle_callback(client, callback_query)
            else:
                await self.file_converter_handler.handle_callback(client, callback_query)


        # PDF handlers
        @self.app.on_message(filters.command("image2pdf"))
        async def pdf_command(client, message):
            await self.pdf_handler.start_image_to_pdf(client, message)

        @self.app.on_message(filters.command("pdf2image") & filters.reply)
        async def pdf2image_command(client, message):
            await self.pdf2image_handler.handle_pdf_to_image(client, message)

        # Split PDF handlers
        @self.app.on_message(filters.command("splitpdf"))
        async def split_pdf_command(client, message):
            await self.split_pdf_handler.handle_split_pdf(client, message)

        # Merge PDF handlers
        @self.app.on_message(filters.command("mergepdf"))
        async def merge_pdf_command(client, message):
            await self.merge_pdf_handler.start_merge(client, message)

        # Unarchive handlers
        @self.app.on_message(filters.command("unarchive"))
        async def unarchive_command(client, message):
            await start_unarchive(client, message)

        @self.app.on_message(filters.command("fileconv"))
        async def file_conversion_command(client, message):
            await self.file_converter_handler.start_conversion(client, message)

        @self.app.on_message(filters.document)
        async def document_handler(client, message):
            chat_id = message.chat.id
            if chat_id in self.pdf_handler.waiting_for_images:
                await self.pdf_handler.handle_pdf_image(client, message)
            elif chat_id in self.merge_pdf_handler.merge_sessions:
                await self.merge_pdf_handler.handle_pdf(client, message)
            elif chat_id in self.file_converter_handler.pdf_expected:
                await self.file_converter_handler.handle_pdf(client, message)
            else:
                await handle_archive(client, message)

        
        @self.app.on_message(filters.photo)
        async def handle_photo(client, message):
            await self.pdf_handler.handle_pdf_image(client, message)

        @self.app.on_message(filters.text & filters.regex(r"^go$", re.IGNORECASE))
        async def handle_go(client, message):
            await self.pdf_handler.handle_go_command(client, message)

        @self.app.on_message(filters.command("skip"))
        async def handle_skip(client, message):
            await self.pdf_handler.handle_skip_name(client, message)

        @self.app.on_message(filters.text & ~filters.command(["help", "resizeimage", "image2pdf", "skip", "cancel", "unarchive", "splitpdf", "pdf2image", "mergepdf", "fileconv"]))
        async def handle_text(client, message):
            chat_id = message.chat.id
            if chat_id in self.merge_pdf_handler.merge_sessions:
                await self.merge_pdf_handler.handle_merge_complete(client, message)
            elif chat_id in self.pdf_handler.waiting_for_name:
                await self.pdf_handler.handle_pdf_name(client, message)
            elif chat_id in self.file_converter_handler.txt_expected:
                await self.file_converter_handler.handle_text(client, message)
            else:
                await self.image_handler.handle_text(client, message)

        # Cancel handler
        @self.app.on_message(filters.command("cancel"))
        async def cancel_command(client, message):
            await self.cancel_handler.handle_cancel(client, message)

    def run(self):
        logger.info("Bot is starting...")
        # Run Flask in a separate thread
        flask_thread = Thread(target=run_flask)
        flask_thread.start()
        
        # Run the bot
        self.app.run()

if __name__ == "__main__":
    bot = Bot()
    bot.run()
