# services/image_service.py
"""
Service layer for image processing operations
"""
from PIL import Image
from io import BytesIO
import os

class ImageService:
    def __init__(self):
        self.user_settings = {}

    def process_image_size(self, image, target_file_size, output_path):
        """Process image to match target file size"""
        min_quality = 1
        max_quality = 95
        best_output = None
        best_quality = None

        while min_quality <= max_quality:
            quality = (min_quality + max_quality) // 2
            output = BytesIO()
            image.save(output, format='JPEG', quality=quality)
            size_kb = output.tell() / 1024

            if abs(size_kb - target_file_size) < 1 or max_quality - min_quality <= 1:
                best_output = output
                best_quality = quality
                break
            elif size_kb > target_file_size:
                max_quality = quality - 1
            else:
                min_quality = quality + 1

        if best_output is None:
            return None, None

        with open(output_path, 'wb') as f:
            f.write(best_output.getvalue())

        return output_path, best_quality

    def process_image_dimensions(self, image, width, height, output_path):
        """Process image to match target dimensions"""
        resized_image = image.copy()
        resized_image.thumbnail((width, height), Image.LANCZOS)
        resized_image.save(output_path, 'JPEG', quality=95)
        return output_path
