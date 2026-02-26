"""
Data management services for participant records.

Session-based storage - no persistence to disk.
All data is kept in Streamlit session state and cleared after email delivery.
"""

import uuid
import base64
import io
from datetime import datetime
from PIL import Image


def init_participant_session(first_name, last_name, email="", phone=""):
    """
    Initialize a new participant session.

    Returns a dict to be stored in st.session_state.participant_data.
    No disk writes occur.
    """
    participant_id = str(uuid.uuid4())[:8]

    return {
        "id": participant_id,
        "first_name": first_name,
        "last_name": last_name,
        "full_name": f"{first_name} {last_name}",
        "email": email,
        "phone": phone,
        "created_at": datetime.now().isoformat(),
        "status": "in_progress",
        "documents": {},
        "signature": None,
        "forms": {},
    }


def convert_image_to_pdf_bytes(image_data, doc_type, doc_name, group_id, ai_verification=None):
    """
    Convert an image to PDF and JPEG bytes for session storage.

    Args:
        image_data: Raw image bytes or file-like object
        doc_type: Document type ID (e.g., 'ca_id')
        doc_name: Human-readable document name
        group_id: Document group ID (e.g., 'identity')
        ai_verification: Optional AI verification result dict

    Returns:
        dict: Document info with image_bytes and pdf_bytes for session storage
    """
    # Open and process the image
    if isinstance(image_data, bytes):
        img = Image.open(io.BytesIO(image_data))
    else:
        img = Image.open(image_data)

    # Convert to RGB if necessary (for PNG with alpha)
    if img.mode in ('RGBA', 'P'):
        img = img.convert('RGB')

    # Save as JPEG for preview
    jpeg_buffer = io.BytesIO()
    img.save(jpeg_buffer, "JPEG", quality=90)
    jpeg_bytes = jpeg_buffer.getvalue()

    # Save as PDF for submission
    pdf_buffer = io.BytesIO()
    img.save(pdf_buffer, "PDF", resolution=100.0)
    pdf_bytes = pdf_buffer.getvalue()

    return {
        "doc_type": doc_type,
        "doc_name": doc_name,
        "group": group_id,
        "uploaded_at": datetime.now().isoformat(),
        "image_bytes": jpeg_bytes,
        "pdf_bytes": pdf_bytes,
        "ai_verification": ai_verification or {"verified": True, "message": "OK"},
    }


def convert_pdf_to_bytes(pdf_data, doc_type, doc_name, group_id):
    """
    Store a PDF directly for session storage.

    Args:
        pdf_data: Raw PDF bytes
        doc_type: Document type ID
        doc_name: Human-readable document name
        group_id: Document group ID

    Returns:
        dict: Document info with pdf_bytes for session storage
    """
    return {
        "doc_type": doc_type,
        "doc_name": doc_name,
        "group": group_id,
        "uploaded_at": datetime.now().isoformat(),
        "image_bytes": None,  # PDFs don't have image preview
        "pdf_bytes": pdf_data,
        "ai_verification": {"verified": True, "message": "PDF uploaded"},
    }


def convert_signature_to_bytes(signature_data, signature_type="drawn"):
    """
    Convert signature data to PNG bytes for session storage.

    Args:
        signature_data: Base64 data URL, raw bytes, or PIL Image
        signature_type: Type of signature ('drawn' or 'acknowledgment')

    Returns:
        dict: Signature info with image_bytes for session storage
    """
    if signature_type == "acknowledgment":
        # Checkbox acknowledgment - no image needed
        return {
            "type": "acknowledgment",
            "signed_at": datetime.now().isoformat(),
            "image_bytes": None,
        }

    png_bytes = None

    if isinstance(signature_data, str) and signature_data.startswith("data:image"):
        # Base64 data URL
        header, encoded = signature_data.split(",", 1)
        png_bytes = base64.b64decode(encoded)
    elif isinstance(signature_data, bytes):
        # Raw bytes
        png_bytes = signature_data
    else:
        # PIL Image - convert to PNG bytes
        buffer = io.BytesIO()
        signature_data.save(buffer, "PNG")
        png_bytes = buffer.getvalue()

    return {
        "type": "drawn",
        "signed_at": datetime.now().isoformat(),
        "image_bytes": png_bytes,
    }


def clear_participant_session(session_state):
    """
    Clear all participant data from session state.

    Call this after successful email delivery.
    """
    session_state.participant_data = None
    session_state.participant_id = None
    session_state.current_form = None
    session_state.forms_completed = []
    session_state.current_doc = 0


def get_document_preview_base64(doc_info):
    """
    Get base64-encoded image for document preview display.

    Args:
        doc_info: Document dict from session state

    Returns:
        str: Base64 data URL for img src, or None if no preview available
    """
    image_bytes = doc_info.get("image_bytes")
    if not image_bytes:
        return None

    b64 = base64.b64encode(image_bytes).decode('utf-8')
    return f"data:image/jpeg;base64,{b64}"


def get_signature_preview_base64(signature_info):
    """
    Get base64-encoded image for signature preview display.

    Args:
        signature_info: Signature dict from session state

    Returns:
        str: Base64 data URL for img src, or None if no preview available
    """
    if not signature_info or signature_info.get("type") == "acknowledgment":
        return None

    image_bytes = signature_info.get("image_bytes")
    if not image_bytes:
        return None

    b64 = base64.b64encode(image_bytes).decode('utf-8')
    return f"data:image/png;base64,{b64}"
