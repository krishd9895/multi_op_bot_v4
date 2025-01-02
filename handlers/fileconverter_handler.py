from pyrogram import Client, filters
from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton, Message
from pdf2docx import Converter
import camelot
import pandas as pd
import os
import logging
import traceback
from typing import Optional

class FileConverterHandler:
    def __init__(self):
        self.pdf_expected = {}
        self.txt_expected = {}
        self.current_pdf = {}
        self.base_path = os.path.join("Downloads", "FileConverter")
        os.makedirs(self.base_path, exist_ok=True)
        logging.basicConfig(level=logging.INFO)
        self.logger = logging.getLogger(__name__)

    def get_user_folder(self, chat_id):
        folder = os.path.join(self.base_path, str(chat_id))
        os.makedirs(folder, exist_ok=True)
        return folder

    def cleanup_user_data(self, chat_id):
        if chat_id in self.current_pdf:
            if os.path.exists(self.current_pdf[chat_id]):
                os.remove(self.current_pdf[chat_id])
            del self.current_pdf[chat_id]
        self.pdf_expected[chat_id] = False
        self.txt_expected[chat_id] = False

    async def start_conversion(self, client: Client, message: Message):
        keyboard = InlineKeyboardMarkup([
            [InlineKeyboardButton("PDF", callback_data="pdf"),
             InlineKeyboardButton("Text Message", callback_data="text_message")]
        ])
        await message.reply_text(
            "What type of file do you want to convert?",
            reply_markup=keyboard
        )

    async def handle_callback(self, client: Client, callback_query):
        chat_id = callback_query.message.chat.id
        status_message = None
        try:
            if callback_query.data == "pdf":
                self.pdf_expected[chat_id] = True
                await callback_query.message.reply_text(
                    "Please send me the PDF file you want to convert 📄"
                )
                return
            elif callback_query.data == "text_message":
                self.txt_expected[chat_id] = True
                await callback_query.message.reply_text(
                    "Please send me the text message you want to save in a file 📝"
                )
                return
            if callback_query.data == "word":
                if chat_id in self.current_pdf:
                    pdf_path = self.current_pdf[chat_id]
                    output_path = os.path.join(self.get_user_folder(chat_id), "converted.docx")
                    try:
                        status_message = await callback_query.message.reply_text(
                            "Starting conversion... ⏳"
                        )
                        
                        class ProgressHandler:
                            def __init__(self, status_message):
                                self.status_message = status_message
                            
                            async def update(self, message):
                                await self.status_message.edit_text(f"{message} ⏳")
    
                        progress = ProgressHandler(status_message)
                        cv = Converter(pdf_path)
                        
                        # Monkey patch the logging
                        original_info = self.logger.info
                        async def new_info(msg):
                            original_info(msg)
                            if any(x in msg for x in ["Opening", "Analyzing", "Parsing", "Creating"]):
                                await progress.update(msg)
                        self.logger.info = new_info
                        
                        try:
                            cv.convert(output_path)
                        finally:
                            self.logger.info = original_info
                        
                        cv.close()
                        
                        if os.path.exists(output_path) and os.path.getsize(output_path) > 0:
                            await status_message.edit_text("Sending converted file... 📤")
                            await callback_query.message.reply_document(
                                output_path,
                                caption="Converted Word document 📄"
                            )
                        else:
                            raise Exception("Empty output file")
                    except Exception as e:
                        self.logger.error(f"Word conversion error: {str(e)}")
                        await callback_query.message.reply_text(
                            "Conversion failed. Please try again with a different PDF. 🚫"
                        )
                    finally:
                        if os.path.exists(output_path):
                            os.remove(output_path)
                        self.cleanup_user_data(chat_id)
                        if status_message:
                            await status_message.delete()

            elif callback_query.data == "excel":
                if chat_id in self.current_pdf:
                    pdf_path = self.current_pdf[chat_id]
                    output_path = os.path.join(self.get_user_folder(chat_id), "converted.xlsx")
                    try:
                        status_message = await callback_query.message.reply_text(
                            "Converting PDF to Excel... ⏳"
                        )
                        tables = camelot.read_pdf(pdf_path, pages='all')
                        if not tables:
                            raise Exception("No tables found in PDF")
                        
                        await status_message.edit_text("Processing tables... ⚙️")
                        with pd.ExcelWriter(output_path) as writer:
                            for i, table in enumerate(tables):
                                df = table.df
                                df.to_excel(writer, sheet_name=f'Table_{i+1}', index=False)
                        
                        if os.path.exists(output_path) and os.path.getsize(output_path) > 0:
                            await status_message.edit_text("Sending converted file... 📤")
                            await callback_query.message.reply_document(
                                output_path,
                                caption="Converted Excel file 📊"
                            )
                        else:
                            raise Exception("Conversion produced empty file")
                    except Exception as e:
                        self.logger.error(f"Excel conversion error: {str(e)}")
                        await callback_query.message.reply_text(
                            "Conversion failed. This might be due to unrecognizable tables. Try a different PDF. 🚫"
                        )
                    finally:
                        if os.path.exists(output_path):
                            os.remove(output_path)
                        self.cleanup_user_data(chat_id)
                        if status_message:
                            await status_message.delete()

        except Exception as e:
            self.logger.error(f"Callback handling error: {str(e)}\n{traceback.format_exc()}")
            await callback_query.message.reply_text(
                "Sorry, something went wrong. Please try again later. 🚫"
            )
            self.cleanup_user_data(chat_id)
            if status_message:
                await status_message.delete()

    async def handle_pdf(self, client: Client, message: Message):
        chat_id = message.chat.id
        if chat_id in self.pdf_expected and self.pdf_expected[chat_id]:
            if message.document.mime_type == "application/pdf":
                status_message = await message.reply_text("Downloading PDF... ⏳")
                try:
                    file_path = os.path.join(self.get_user_folder(chat_id), "input.pdf")
                    await message.download(file_path)
                    self.current_pdf[chat_id] = file_path
                    keyboard = InlineKeyboardMarkup([
                        [InlineKeyboardButton("Word", callback_data="word"),
                         InlineKeyboardButton("Excel", callback_data="excel")]
                    ])
                    await message.reply_text("Choose the output format:", reply_markup=keyboard)
                    self.pdf_expected[chat_id] = False
                except Exception as e:
                    self.logger.error(f"PDF handling error: {str(e)}\n{traceback.format_exc()}")
                    await message.reply_text(
                        "Sorry, there was an error processing your PDF. Please try again. 🚫"
                    )
                    self.cleanup_user_data(chat_id)
                finally:
                    await status_message.delete()

    async def handle_text(self, client: Client, message: Message):
        chat_id = message.chat.id
        if chat_id in self.txt_expected and self.txt_expected[chat_id]:
            status_message = await message.reply_text("Processing your text... ⏳")
            try:
                text = message.text
                output_path = os.path.join(self.get_user_folder(chat_id), "message.txt")
                with open(output_path, "w", encoding='utf-8') as f:
                    f.write(text)
                await status_message.edit_text("Text file created! Sending... 📤")
                await message.reply_document(
                    output_path,
                    caption="Here's your text file 📝"
                )
            except Exception as e:
                self.logger.error(f"Text handling error: {str(e)}\n{traceback.format_exc()}")
                await message.reply_text(
                    "Sorry, there was an error creating your text file. Please try again. 🚫"
                )
            finally:
                if os.path.exists(output_path):
                    os.remove(output_path)
                self.txt_expected[chat_id] = False
                await status_message.delete()
