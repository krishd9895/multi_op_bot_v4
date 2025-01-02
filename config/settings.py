# config/settings.py
"""
Configuration settings for the Telegram bot
"""
import os

API_ID = os.getenv("API_ID")
API_HASH = os.getenv("API_HASH")
BOT_TOKEN = os.getenv("BOT_TOKEN")

# Base directories
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DOWNLOADS_DIR = os.path.join(BASE_DIR, "Downloads")
RESIZE_DIR = os.path.join(DOWNLOADS_DIR, "Resize")
PDF_DIR = os.path.join(DOWNLOADS_DIR, "PDF")

# Create necessary directories
os.makedirs(DOWNLOADS_DIR, exist_ok=True)
os.makedirs(RESIZE_DIR, exist_ok=True)
os.makedirs(PDF_DIR, exist_ok=True)

# Configure allowed file types
ALLOWED_IMAGE_TYPES = ['jpeg', 'jpg', 'png']

# Configure maximum file sizes (in bytes)
MAX_FILE_SIZE = 200 * 1024 * 1024  # 200MB

# Configure timeout settings (in seconds)
OPERATION_TIMEOUT = 300  # 5 minutes

# Configure logging
LOG_DIR = os.path.join(BASE_DIR, "logs")
os.makedirs(LOG_DIR, exist_ok=True)
