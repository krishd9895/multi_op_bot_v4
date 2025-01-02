"""
Utility functions for file operations
"""
import os

def get_user_folder(chat_id):
    """Create and return user-specific folder in Resize directory"""
    user_folder = os.path.join('Downloads', 'Resize', str(chat_id))
    if not os.path.exists(user_folder):
        os.makedirs(user_folder)
    return user_folder

def create_user_folder(chat_id, base_path):
    """Create and return user-specific folder in given base path"""
    user_folder = os.path.join(base_path, str(chat_id))
    if not os.path.exists(user_folder):
        os.makedirs(user_folder, mode=0o777, exist_ok=True)
    return user_folder

def cleanup_user_data(chat_id, user_settings):
    """Clean up user data and temporary files"""
    if chat_id in user_settings:
        if 'original_path' in user_settings[chat_id]:
            try:
                os.remove(user_settings[chat_id]['original_path'])
            except:
                pass
        del user_settings[chat_id]
