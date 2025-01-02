"""
Handler for image-related commands
"""
from pyrogram import Client, filters
from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from PIL import Image
from services.image_service import ImageService
from utils.file_utils import get_user_folder, cleanup_user_data
import os
import logging

logger = logging.getLogger(__name__)

class ImageHandler:
    def __init__(self):
        self.image_service = ImageService()
        self.user_settings = {}

    async def handle_resize_image(self, client, message):
        """Handle the /resizeimage command"""
        try:
            chat_id = message.chat.id
    
            # Verify command and image
            if not message.reply_to_message or not message.reply_to_message.photo:
                await message.reply_text("Please reply to an image with the /resizeimage command.")
                return
    
            # Download and process image
            await message.reply_text("Processing your image...")
            photo = message.reply_to_message.photo
            if isinstance(photo, list):
                photo = photo[-1]  # Get the highest resolution if it's a list
    
            # Ensure directories exist
            user_folder = os.path.join("Downloads", "Resize", str(chat_id))
            os.makedirs(user_folder, exist_ok=True)
    
            downloaded_file = await client.download_media(photo, file_name=os.path.join(user_folder, "original_image.jpg"))
    
            try:
                image = Image.open(downloaded_file)
    
                # Store user session data
                self.user_settings[chat_id] = {
                    'command_state': 'choose_modification',
                    'image': image,
                    'user_folder': user_folder,
                    'original_path': downloaded_file,
                }
    
                # Prepare image details
                file_size_mb = os.path.getsize(downloaded_file) / (1024 * 1024)
                file_size_kb = os.path.getsize(downloaded_file) / 1024
                image_details = (
                    f"Image Details:\n\n"
                    f"File Size: {file_size_mb:.2f} MB ({file_size_kb:.2f} KB)\n"
                    f"Dimensions: {image.width}x{image.height}px"
                )
    
                # Create inline keyboard
                markup = InlineKeyboardMarkup([
                    [InlineKeyboardButton(text="Modify File Size", callback_data="modify_file_size")],
                    [InlineKeyboardButton(text="Modify Dimensions", callback_data="modify_file_dimensions")],
                    [InlineKeyboardButton(text="Cancel", callback_data="cancel")]
                ])
    
                await message.reply_text(
                    f"{image_details}\n\nPlease choose a modification option:",
                    reply_markup=markup
                )
    
            except Exception as e:
                logger.error(f"Error processing image: {e}")
                await message.reply_text("Error processing the image. Please try again with a different image.")
                cleanup_user_data(chat_id, self.user_settings)
                if os.path.exists(downloaded_file):
                    os.remove(downloaded_file)
    
        except Exception as e:
            logger.error(f"Error in handle_resize_image: {e}")
            await message.reply_text("An error occurred while processing your request.")
            cleanup_user_data(chat_id, self.user_settings)

    async def handle_callback(self, client, callback_query):
        """Handle inline keyboard callbacks"""
        try:
            chat_id = callback_query.message.chat.id
            data = callback_query.data

            if chat_id not in self.user_settings:
                await callback_query.answer("Session expired. Please start over.", show_alert=True)
                return

            if data == "cancel":
                cleanup_user_data(chat_id, self.user_settings)
                await callback_query.message.reply_text("Operation cancelled.")
                await callback_query.answer()
                return

            if data == "modify_file_size":
                await callback_query.message.reply_text(
                    "Please enter the desired file size in kilobytes (KB).\n"
                    "For example: 500 for 500KB"
                )
                self.user_settings[chat_id]['command_state'] = 'enter_file_size'

            elif data == "modify_file_dimensions":
                await callback_query.message.reply_text(
                    "Please enter the desired width and height in pixels (separated by a space).\n"
                    "For example: 800 600 for 800x600 pixels"
                )
                self.user_settings[chat_id]['command_state'] = 'enter_dimensions'

            await callback_query.answer()

        except Exception as e:
            logger.error(f"Error in handle_callback: {e}")
            await callback_query.answer("An error occurred.", show_alert=True)
            cleanup_user_data(chat_id, self.user_settings)

    async def handle_text(self, client, message):
        """Handle text input for image modifications"""
        try:
            chat_id = message.chat.id

            # Check for active session or cancel command
            if chat_id not in self.user_settings:
                return

            if message.text.lower() == "/cancel":
                await message.reply_text("Operation cancelled.")
                cleanup_user_data(chat_id, self.user_settings)
                return

            command_state = self.user_settings[chat_id]['command_state']
            user_folder = self.user_settings[chat_id]['user_folder']
            image = self.user_settings[chat_id]['image']

            if command_state == 'enter_file_size':
                await self._handle_file_size(message, chat_id, image, user_folder)
            elif command_state == 'enter_dimensions':
                await self._handle_dimensions(message, chat_id, image, user_folder)

        except Exception as e:
            logger.error(f"Error in handle_text: {e}")
            await message.reply_text("An error occurred while processing your request.")
            cleanup_user_data(chat_id, self.user_settings)

    async def _handle_file_size(self, message, chat_id, image, user_folder):
        """Handle file size modification"""
        try:
            target_file_size = float(message.text.strip())
            if target_file_size <= 0:
                await message.reply_text("Please enter a positive file size.")
                return

            output_path = os.path.join(user_folder, 'resized_image.jpg')

            try:
                output_path, quality = self.image_service.process_image_size(
                    image, target_file_size, output_path
                )

                if output_path is None or not os.path.exists(output_path):
                    await message.reply_text("Couldn't achieve the target file size. Please try a larger size.")
                    return

                # Send the processed image
                await message.reply_photo(
                    photo=output_path,
                    caption=(
                        f"Resized Image Details:\n"
                        f"File Size: {os.path.getsize(output_path) / 1024:.2f} KB\n"
                        f"Quality: {quality}%\n"
                        f"Dimensions: {image.width}x{image.height}px"
                    )
                )

            finally:
                # Cleanup
                if output_path and os.path.exists(output_path):
                    os.remove(output_path)
                cleanup_user_data(chat_id, self.user_settings)

        except ValueError:
            await message.reply_text(
                "Invalid file size. Please enter a valid number in kilobytes (KB).\n"
                "For example: 500 for 500KB"
            )

    async def _handle_dimensions(self, message, chat_id, image, user_folder):
        """Handle dimension modification"""
        try:
            # Parse dimensions
            try:
                width, height = map(int, message.text.strip().split())
            except ValueError:
                await message.reply_text(
                    "Invalid dimensions. Please enter two numbers separated by a space.\n"
                    "For example: 800 600 for 800x600 pixels"
                )
                return

            if width <= 0 or height <= 0:
                await message.reply_text("Please enter positive dimensions.")
                return

            output_path = os.path.join(user_folder, 'resized_image.jpg')

            try:
                # Process the image and save the resized version
                with image as img:  # Use a context manager to ensure the file is properly closed
                    output_path = self.image_service.process_image_dimensions(
                        img, width, height, output_path
                    )

                if output_path is None or not os.path.exists(output_path):
                    await message.reply_text("Error processing image dimensions. Please try different dimensions.")
                    return

                # Open and send the resized image
                with Image.open(output_path) as resized_image:
                    await message.reply_photo(
                        photo=output_path,
                        caption=(
                            f"Resized Image Details:\n"
                            f"File Size: {os.path.getsize(output_path) / 1024:.2f} KB\n"
                            f"Dimensions: {resized_image.width}x{resized_image.height}px"
                        )
                    )

            finally:
                # Cleanup: Ensure file is properly closed and removed
                if os.path.exists(output_path):
                    os.remove(output_path)
                cleanup_user_data(chat_id, self.user_settings)

        except Exception as e:
            logger.error(f"Error processing dimensions: {e}")
            await message.reply_text("Error processing dimensions. Please try again.")
            cleanup_user_data(chat_id, self.user_settings)

def cleanup_user_data(chat_id, user_settings):
    """Clean up user-specific data"""
    try:
        if chat_id in user_settings:
            user_data = user_settings[chat_id]

            # Remove original image file
            original_path = user_data.get("original_path")
            if original_path and os.path.exists(original_path):
                os.remove(original_path)

            # Delete user folder if empty
            user_folder = user_data.get("user_folder")
            if user_folder and os.path.exists(user_folder):
                try:
                    os.rmdir(user_folder)  # Removes the folder if it's empty
                except OSError:
                    pass  # Ignore if the folder is not empty

            # Remove user session data
            del user_settings[chat_id]
    except Exception as e:
        logger.error(f"Error in cleanup_user_data: {e}")
