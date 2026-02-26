"""
Image processing services for document capture.

Provides image quality validation and enhancement for uploaded documents.
"""

import io
from PIL import Image, ImageEnhance

from config import MIN_WIDTH, MIN_HEIGHT, MIN_FILE_SIZE


def check_image_quality(image_data):
    """Check image quality and return issues found."""
    issues = []
    warnings = []

    try:
        if isinstance(image_data, bytes):
            img = Image.open(io.BytesIO(image_data))
            file_size = len(image_data)
        else:
            img = Image.open(image_data)
            image_data.seek(0, 2)  # Seek to end
            file_size = image_data.tell()
            image_data.seek(0)  # Reset

        width, height = img.size

        # Check resolution
        if width < MIN_WIDTH or height < MIN_HEIGHT:
            issues.append(f"Image too small ({width}x{height}). Move closer or use higher quality.")

        # Check file size (too small = likely low quality)
        if file_size < MIN_FILE_SIZE:
            warnings.append("Image file size is small. Quality may be low.")

        # Check brightness (convert to grayscale and check average)
        if img.mode != 'L':
            gray = img.convert('L')
        else:
            gray = img

        # Get average brightness (0-255)
        pixels = list(gray.getdata())
        avg_brightness = sum(pixels) / len(pixels)

        if avg_brightness < 50:
            issues.append("Image is too dark. Use better lighting.")
        elif avg_brightness > 220:
            warnings.append("Image may be overexposed. Reduce lighting or glare.")
        elif avg_brightness < 80:
            warnings.append("Image is a bit dark. Better lighting recommended.")

        # Check contrast (standard deviation of brightness)
        variance = sum((p - avg_brightness) ** 2 for p in pixels) / len(pixels)
        std_dev = variance ** 0.5

        if std_dev < 30:
            warnings.append("Low contrast. Make sure document is on a contrasting background.")

        return {
            "passed": len(issues) == 0,
            "issues": issues,
            "warnings": warnings,
            "width": width,
            "height": height,
            "brightness": avg_brightness,
            "contrast": std_dev,
        }

    except Exception as e:
        return {
            "passed": True,  # Don't block on error
            "issues": [],
            "warnings": [f"Could not analyze image quality: {str(e)}"],
            "width": 0,
            "height": 0,
        }


def enhance_image(image_data):
    """Auto-enhance image brightness and contrast."""
    try:
        if isinstance(image_data, bytes):
            img = Image.open(io.BytesIO(image_data))
        else:
            img = Image.open(image_data)

        # Convert to RGB if needed
        if img.mode in ('RGBA', 'P'):
            img = img.convert('RGB')

        # Auto-adjust brightness
        gray = img.convert('L')
        pixels = list(gray.getdata())
        avg_brightness = sum(pixels) / len(pixels)

        # Target brightness around 128 (middle)
        if avg_brightness < 100:
            brightness_factor = min(1.5, 128 / max(avg_brightness, 1))
            enhancer = ImageEnhance.Brightness(img)
            img = enhancer.enhance(brightness_factor)

        # Slightly increase contrast
        enhancer = ImageEnhance.Contrast(img)
        img = enhancer.enhance(1.1)

        # Slight sharpening
        enhancer = ImageEnhance.Sharpness(img)
        img = enhancer.enhance(1.2)

        # Convert back to bytes
        buffer = io.BytesIO()
        img.save(buffer, format='JPEG', quality=90)
        buffer.seek(0)

        return buffer.getvalue()

    except Exception as e:
        # Return original if enhancement fails
        if isinstance(image_data, bytes):
            return image_data
        else:
            image_data.seek(0)
            return image_data.read()
