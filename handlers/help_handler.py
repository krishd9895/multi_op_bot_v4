# handlers/help_handler.py
"""
Handler for help command
"""
from pyrogram import Client, filters

class HelpHandler:
    @staticmethod
    async def handle_help(client, message):
        help_text = (
            "🤖 <b>Welcome to the Bot Help Center</b>\n\n"
            "<b>📑 PDF Operations:</b>\n"
            "• <b>/mergepdf</b> - Merge multiple PDF files into one 📚\n"
            "• <b>/splitpdf</b> - Split a PDF into individual pages ✂️\n"
            "• <b>/pdf2image</b> - Convert a PDF to images (reply to a PDF file) 🖼️\n"
            "• <b>/fileconv</b> - Convert PDFs to Word/Excel or create a text file 📄\n\n"
            "<b>📦 Unarchive Operations:</b>\n"
            "• <b>/unarchive</b> - Extract compressed files (zip, rar, 7z) 📂\n\n"
            "<b>🎨 Image Operations:</b>\n"
            "• <b>/resizeimage</b> - Resize an image 🔄\n"
            "• <b>/image2pdf</b> - Convert images into a PDF 📄\n\n"
            "<b>ℹ️ General Commands:</b>\n"
            "• <b>/cancel</b> - Cancel the current operation ❌\n"
            "• <b>/help</b> - Display this help message ℹ️\n\n"
        )
        await message.reply_text(help_text, disable_web_page_preview=True)
