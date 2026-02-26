"""
QR code generation for check-in URLs.

Generates and caches QR codes for participant check-in.
"""

import socket

# Optional qrcode import
try:
    import qrcode
    HAS_QRCODE = True
except ImportError:
    HAS_QRCODE = False

from config import QR_CODES_DIR


def get_local_ip():
    """Get the local IP address for network access."""
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        ip = s.getsockname()[0]
        s.close()
        return ip
    except Exception:
        return "localhost"


def generate_qr_code(url):
    """Generate a QR code for the intake URL. Reuses existing QR if URL matches."""
    if not HAS_QRCODE:
        return None

    # Use a fixed filename - only regenerate if URL changes
    filepath = QR_CODES_DIR / "orientation_checkin_qr.png"
    url_file = QR_CODES_DIR / "qr_url.txt"

    # Check if we already have a QR code for this URL
    if filepath.exists() and url_file.exists():
        saved_url = url_file.read_text().strip()
        if saved_url == url:
            return filepath  # Reuse existing QR code

    # Generate new QR code
    qr = qrcode.QRCode(
        version=1,
        error_correction=qrcode.constants.ERROR_CORRECT_L,
        box_size=10,
        border=4,
    )
    qr.add_data(url)
    qr.make(fit=True)

    img = qr.make_image(fill_color="black", back_color="white")
    img.save(filepath)

    # Save the URL so we know what this QR code is for
    url_file.write_text(url)

    return filepath
