"""
Services module for INVEST Orientation Intake.
"""

from app.services.image_processor import check_image_quality, enhance_image
from app.services.data_manager import (
    init_participant_session,
    convert_image_to_pdf_bytes,
    convert_pdf_to_bytes,
    convert_signature_to_bytes,
    clear_participant_session,
    get_document_preview_base64,
    get_signature_preview_base64,
)
from app.services.document_verifier import verify_document_with_ai, HAS_ANTHROPIC
from app.services.qr_generator import get_local_ip, generate_qr_code, HAS_QRCODE
from app.services.zip_builder import build_submission_zip, get_zip_filename
from app.services.email_sender import send_submission_email, send_submission_to_default_recipients
from app.services.pdf_filler import fill_all_county_forms

__all__ = [
    # Image processing
    'check_image_quality',
    'enhance_image',
    # Data management (session-based, no persistence)
    'init_participant_session',
    'convert_image_to_pdf_bytes',
    'convert_pdf_to_bytes',
    'convert_signature_to_bytes',
    'clear_participant_session',
    'get_document_preview_base64',
    'get_signature_preview_base64',
    # Document verification
    'verify_document_with_ai',
    'HAS_ANTHROPIC',
    # QR code generation
    'get_local_ip',
    'generate_qr_code',
    'HAS_QRCODE',
    # Zip builder
    'build_submission_zip',
    'get_zip_filename',
    # Email sender
    'send_submission_email',
    'send_submission_to_default_recipients',
    # PDF filler
    'fill_all_county_forms',
]
