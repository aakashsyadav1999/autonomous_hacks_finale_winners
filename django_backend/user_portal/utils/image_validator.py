"""
Image validation and processing utilities.

This module provides utilities for validating and processing base64-encoded
images, including size validation and conversion to Django ImageField format.
"""

import base64
import logging
import io
from typing import Tuple, Optional
from django.core.files.uploadedfile import InMemoryUploadedFile
from PIL import Image


logger = logging.getLogger(__name__)


def validate_base64_image(base64_string: str) -> Tuple[bool, Optional[str]]:
    """
    Validate base64-encoded image string.
    
    Checks:
    - Valid base64 encoding
    - Valid image format (JPEG, PNG, WebP)
    - Image size <= 5MB
    
    Args:
        base64_string: Base64-encoded image (with or without data URI prefix)
    
    Returns:
        Tuple of (is_valid, error_message)
        - (True, None) if valid
        - (False, error_message) if invalid
    
    Example:
        >>> is_valid, error = validate_base64_image(image_data)
        >>> if not is_valid:
        ...     print(error)
    """
    try:
        # Remove data URI prefix if present
        if ',' in base64_string:
            base64_string = base64_string.split(',')[1]
        
        # Decode base64
        image_data = base64.b64decode(base64_string)
        
        # Check size (5MB limit)
        max_size_bytes = 5 * 1024 * 1024
        if len(image_data) > max_size_bytes:
            size_mb = len(image_data) / (1024 * 1024)
            return False, f"Image size {size_mb:.2f}MB exceeds 5MB limit"
        
        # Validate it's a valid image
        try:
            img = Image.open(io.BytesIO(image_data))
            img.verify()
            
            # Check format
            valid_formats = ['JPEG', 'PNG', 'WEBP']
            if img.format not in valid_formats:
                return False, f"Invalid image format. Allowed: {', '.join(valid_formats)}"
            
            return True, None
        
        except Exception as e:
            return False, f"Invalid image data: {str(e)}"
    
    except base64.binascii.Error:
        return False, "Invalid base64 encoding"
    
    except Exception as e:
        logger.error(f"Image validation error: {str(e)}")
        return False, f"Image validation failed: {str(e)}"


def base64_to_image_file(
    base64_string: str,
    filename: str = 'complaint.jpg'
) -> Optional[InMemoryUploadedFile]:
    """
    Convert base64 string to Django InMemoryUploadedFile.
    
    This allows saving base64 images to Django ImageField.
    
    Args:
        base64_string: Base64-encoded image
        filename: Filename to use for the uploaded file
    
    Returns:
        InMemoryUploadedFile instance or None if conversion fails
    
    Example:
        >>> image_file = base64_to_image_file(base64_data, 'photo.jpg')
        >>> complaint.image = image_file
        >>> complaint.save()
    """
    try:
        # Remove data URI prefix if present
        if ',' in base64_string:
            base64_string = base64_string.split(',')[1]
        
        # Decode base64
        image_data = base64.b64decode(base64_string)
        
        # Open image with Pillow
        img = Image.open(io.BytesIO(image_data))
        
        # Determine format and extension
        img_format = img.format if img.format else 'JPEG'
        extension_map = {
            'JPEG': 'jpg',
            'PNG': 'png',
            'WEBP': 'webp'
        }
        
        # Ensure filename has correct extension
        base_name = filename.rsplit('.', 1)[0]
        extension = extension_map.get(img_format, 'jpg')
        filename = f"{base_name}.{extension}"
        
        # Convert image to BytesIO buffer
        buffer = io.BytesIO()
        
        # Save image to buffer
        if img_format == 'JPEG':
            # Convert RGBA to RGB for JPEG
            if img.mode in ('RGBA', 'LA', 'P'):
                background = Image.new('RGB', img.size, (255, 255, 255))
                background.paste(img, mask=img.split()[-1] if img.mode == 'RGBA' else None)
                img = background
            img.save(buffer, format='JPEG', quality=85, optimize=True)
        else:
            img.save(buffer, format=img_format, optimize=True)
        
        buffer.seek(0)
        
        # Create InMemoryUploadedFile
        image_file = InMemoryUploadedFile(
            buffer,
            'ImageField',
            filename,
            f'image/{extension}',
            buffer.getbuffer().nbytes,
            None
        )
        
        logger.info(f"Converted base64 to image file: {filename}")
        
        return image_file
    
    except Exception as e:
        logger.error(f"Failed to convert base64 to image file: {str(e)}")
        return None


def optimize_image(image_path: str, max_width: int = 1920) -> None:
    """
    Optimize image file by resizing and compressing.
    
    Reduces storage space while maintaining visual quality.
    Useful for thumbnails and web display.
    
    Args:
        image_path: Path to image file
        max_width: Maximum width in pixels (maintains aspect ratio)
    
    Note:
        Modifies the image file in place.
    """
    try:
        img = Image.open(image_path)
        
        # Resize if larger than max_width
        if img.width > max_width:
            aspect_ratio = img.height / img.width
            new_height = int(max_width * aspect_ratio)
            img = img.resize((max_width, new_height), Image.Resampling.LANCZOS)
        
        # Save with optimization
        img.save(image_path, optimize=True, quality=85)
        
        logger.info(f"Optimized image: {image_path}")
    
    except Exception as e:
        logger.error(f"Failed to optimize image {image_path}: {str(e)}")
