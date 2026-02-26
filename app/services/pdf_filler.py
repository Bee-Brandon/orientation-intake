"""
PDF Form Filler Service
-----------------------
Fills three county WIOA forms with participant data and signature.

Forms handled:
  1. Attachment V  - WIOA Applicant Acknowledgement Statements (fillable fields)
  2. Attachment IV - WIOA Complaint Resolution / Participant Acceptance (text overlay)
  3. Code of Conduct - AJCC Code of Conduct (text overlay)

All operations are in-memory. No files are written to disk.
Returns filled PDF bytes ready for zip packaging.

Template PDFs must be placed in: templates/county_forms/
"""

import os
import json
import tempfile
from io import BytesIO
from datetime import datetime

from pypdf import PdfReader, PdfWriter
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import letter


# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

# Path to the folder containing the blank template PDFs
# Relative to the project root (where app.py lives)
TEMPLATES_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), 
                             "templates", "county_forms")

TEMPLATE_FILES = {
    "attachment_v": "Attachment_V_WIOA_Applicant_Acknowledgement_Statements.pdf",
    "attachment_iv": "Attachment_IV_WIOA_Complaint_Resolutions__Participant_Acceptance_Form.pdf",
    "code_of_conduct": "code_of_conduct.pdf",
}

# AJCC office info for Attachment IV page 2
AJCC_INFO = {
    "address": "3250 Wilshire Blvd., Ste 1010, Los Angeles, CA 90010",
    "phone_fax": "Phone (213) 736-5456 / Fax (213) 736-5654",
    "attn": "Jesse Limon",
}


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _get_template_path(form_key: str) -> str:
    """Get the full path to a template PDF."""
    filename = TEMPLATE_FILES.get(form_key)
    if not filename:
        raise ValueError(f"Unknown form key: {form_key}")
    path = os.path.join(TEMPLATES_DIR, filename)
    if not os.path.exists(path):
        raise FileNotFoundError(
            f"Template not found: {path}. "
            f"Place the blank PDF in templates/county_forms/"
        )
    return path


def _overlay_signature(pdf_bytes: bytes, signature_bytes: bytes, page_configs: list) -> bytes:
    """
    Overlay a signature image onto specific pages of a PDF.
    
    Args:
        pdf_bytes: The PDF to add signatures to (as bytes).
        signature_bytes: The signature image (PNG bytes from session state).
        page_configs: List of dicts, each with:
            - page_num (int): 0-indexed page number
            - x (float): Left edge in PDF points (y=0 at bottom)
            - y (float): Bottom edge in PDF points (y=0 at bottom)
            - width (float): Width in PDF points
            - height (float): Height in PDF points
    
    Returns:
        bytes: The PDF with signature(s) overlaid.
    """
    # Write signature bytes to a temp file (ReportLab needs a file path)
    with tempfile.NamedTemporaryFile(suffix=".png", delete=False) as tmp:
        tmp.write(signature_bytes)
        tmp_sig_path = tmp.name

    try:
        reader = PdfReader(BytesIO(pdf_bytes))
        writer = PdfWriter()

        for page_idx, page in enumerate(reader.pages):
            configs_for_page = [c for c in page_configs if c["page_num"] == page_idx]

            if configs_for_page:
                mediabox = page.mediabox
                page_width = float(mediabox.width)
                page_height = float(mediabox.height)

                overlay_buf = BytesIO()
                c = canvas.Canvas(overlay_buf, pagesize=(page_width, page_height))

                for config in configs_for_page:
                    c.drawImage(
                        tmp_sig_path,
                        config["x"],
                        config["y"],
                        width=config["width"],
                        height=config["height"],
                        mask="auto",
                        preserveAspectRatio=True,
                        anchor="sw",
                    )

                c.save()
                overlay_buf.seek(0)

                overlay_reader = PdfReader(overlay_buf)
                page.merge_page(overlay_reader.pages[0])

            writer.add_page(page)

        output_buf = BytesIO()
        writer.write(output_buf)
        return output_buf.getvalue()

    finally:
        os.unlink(tmp_sig_path)


def _overlay_text_annotations(pdf_bytes: bytes, annotations: list) -> bytes:
    """
    Overlay text onto specific positions on a PDF (for non-fillable forms).
    
    Args:
        pdf_bytes: The PDF to add text to (as bytes).
        annotations: List of dicts, each with:
            - page_num (int): 0-indexed page number
            - x (float): X position in PDF points (y=0 at bottom)
            - y (float): Y position (baseline) in PDF points
            - text (str): Text to place
            - font_size (int): Font size in points
            - font_name (str, optional): Font name (default: Helvetica)
    
    Returns:
        bytes: The PDF with text overlaid.
    """
    reader = PdfReader(BytesIO(pdf_bytes))
    writer = PdfWriter()

    for page_idx, page in enumerate(reader.pages):
        annots_for_page = [a for a in annotations if a["page_num"] == page_idx]

        if annots_for_page:
            mediabox = page.mediabox
            page_width = float(mediabox.width)
            page_height = float(mediabox.height)

            overlay_buf = BytesIO()
            c = canvas.Canvas(overlay_buf, pagesize=(page_width, page_height))

            for annot in annots_for_page:
                font_name = annot.get("font_name", "Helvetica")
                c.setFont(font_name, annot["font_size"])
                c.drawString(annot["x"], annot["y"], annot["text"])

            c.save()
            overlay_buf.seek(0)

            overlay_reader = PdfReader(overlay_buf)
            page.merge_page(overlay_reader.pages[0])

        writer.add_page(page)

    output_buf = BytesIO()
    writer.write(output_buf)
    return output_buf.getvalue()


# ---------------------------------------------------------------------------
# Public API — one function per form
# ---------------------------------------------------------------------------

def fill_attachment_v(participant_data: dict, signature_bytes: bytes, 
                      emergency_contact: dict = None) -> bytes:
    """
    Fill Attachment V — WIOA Applicant Acknowledgement Statements.
    
    This form has native fillable fields (AcroForm). We inject values directly
    into the existing form fields, then overlay the drawn signature.
    
    Args:
        participant_data: Dict with at minimum:
            - first_name (str)
            - last_name (str)
        signature_bytes: PNG bytes of the drawn signature.
        emergency_contact: Optional dict with:
            - name (str)
            - street (str)
            - city (str)
            - zip (str)
            - phone (str)
            - relationship (str, optional): Only for Box 1 (government employee)
            - is_government (bool): If True, fills Box 1; otherwise Box 2.
    
    Returns:
        bytes: Filled PDF as bytes.
    """
    template_path = _get_template_path("attachment_v")
    reader = PdfReader(template_path)
    writer = PdfWriter()
    writer.append(reader)

    today = datetime.now().strftime("%m/%d/%Y")
    full_name = f"{participant_data.get('first_name', '')} {participant_data.get('last_name', '')}"

    # Fill the form fields
    field_values = {
        "Participant Name Print": full_name,
        "Date": today,
    }

    # Emergency contact — Box 1 (government relative) or Box 2 (standard)
    if emergency_contact:
        if emergency_contact.get("is_government", False):
            field_values["Name"] = emergency_contact.get("name", "")
            field_values["Relationship"] = emergency_contact.get("relationship", "")
            field_values["Street_2"] = emergency_contact.get("street", "")
            field_values["City_2"] = emergency_contact.get("city", "")
            field_values["Zip_2"] = emergency_contact.get("zip", "")
            field_values["Phone_2"] = emergency_contact.get("phone", "")
        else:
            field_values["Name_2"] = emergency_contact.get("name", "")
            field_values["Street"] = emergency_contact.get("street", "")
            field_values["City"] = emergency_contact.get("city", "")
            field_values["Zip"] = emergency_contact.get("zip", "")
            field_values["Phone"] = emergency_contact.get("phone", "")

    # Update form fields on all pages (pypdf handles field-to-page mapping)
    writer.update_page_form_field_values(writer.pages[0], field_values)

    # Get the intermediate PDF bytes
    buf = BytesIO()
    writer.write(buf)
    pdf_bytes = buf.getvalue()

    # Overlay drawn signature
    # Signature field rect (y=0 at bottom): [233.2, 241.6, 429.0, 260.8]
    pdf_bytes = _overlay_signature(pdf_bytes, signature_bytes, [
        {
            "page_num": 0,
            "x": 235,
            "y": 242,
            "width": 190,
            "height": 18,
        }
    ])

    return pdf_bytes


def fill_attachment_iv(participant_data: dict, signature_bytes: bytes,
                       staff_name: str = "") -> bytes:
    """
    Fill Attachment IV — WIOA Complaint Resolution / Participant Acceptance Form.
    
    This form has NO fillable fields. We overlay text at precise coordinates
    and place the drawn signature image.
    
    Fills:
        - Page 2: AJCC Grievance Filing Officer info (address, phone, attn)
        - Page 4: Participant name, date, drawn signature, staff name + date
    
    Args:
        participant_data: Dict with at minimum:
            - first_name (str)
            - last_name (str)
        signature_bytes: PNG bytes of the drawn signature.
        staff_name: Optional staff member name for the staff signature line.
    
    Returns:
        bytes: Filled PDF as bytes.
    """
    template_path = _get_template_path("attachment_iv")

    with open(template_path, "rb") as f:
        pdf_bytes = f.read()

    today = datetime.now().strftime("%m/%d/%Y")
    full_name = f"{participant_data.get('first_name', '')} {participant_data.get('last_name', '')}"

    # Text annotations (coordinates in PDF points, y=0 at bottom, page height=792)
    annotations = [
        # Page 2 — AJCC Filing Officer info
        # Underscores at y_top=169 from top -> y from bottom = 792-178 = 614
        {
            "page_num": 1,
            "x": 225,
            "y": 792 - 178,     # ~614 from bottom
            "text": AJCC_INFO["address"],
            "font_size": 7,
        },
        {
            "page_num": 1,
            "x": 225,
            "y": 792 - 189,     # ~603 from bottom
            "text": AJCC_INFO["phone_fax"],
            "font_size": 7,
        },
        {
            "page_num": 1,
            "x": 228,
            "y": 792 - 202,     # ~590 from bottom
            "text": AJCC_INFO["attn"],
            "font_size": 7,
        },
        # Page 4 — Participant Name (Print)
        # Underscores at y_top=99 from top -> y from bottom = 792-107 = 685
        {
            "page_num": 3,
            "x": 60,
            "y": 792 - 107,     # ~685 from bottom
            "text": full_name,
            "font_size": 10,
        },
        # Page 4 — Participant Date
        {
            "page_num": 3,
            "x": 488,
            "y": 792 - 107,
            "text": today,
            "font_size": 10,
        },
    ]

    # Staff name and date (if provided)
    if staff_name:
        annotations.extend([
            {
                "page_num": 3,
                "x": 60,
                "y": 792 - 174,  # Staff line position
                "text": staff_name,
                "font_size": 10,
            },
            {
                "page_num": 3,
                "x": 488,
                "y": 792 - 174,
                "text": today,
                "font_size": 10,
            },
        ])

    # Add text overlays
    pdf_bytes = _overlay_text_annotations(pdf_bytes, annotations)

    # Overlay drawn signature on page 4 (participant signature line)
    # Underscores: x0=247.3, y_top=99 from top -> y from bottom = 792-109 = 683
    pdf_bytes = _overlay_signature(pdf_bytes, signature_bytes, [
        {
            "page_num": 3,
            "x": 255,
            "y": 685,
            "width": 170,
            "height": 20,
        }
    ])

    return pdf_bytes


def fill_code_of_conduct(signature_bytes: bytes) -> bytes:
    """
    Fill Code of Conduct — AJCC Code of Conduct.
    
    This form is a flat scan with NO fillable fields. We overlay the date
    and place the drawn signature image.
    
    Args:
        signature_bytes: PNG bytes of the drawn signature.
    
    Returns:
        bytes: Filled PDF as bytes.
    """
    template_path = _get_template_path("code_of_conduct")

    with open(template_path, "rb") as f:
        pdf_bytes = f.read()

    today = datetime.now().strftime("%m/%d/%Y")

    # Page height for this scanned doc: 786.6
    PAGE_HEIGHT = 786.6

    # Date annotation — "Date:" label is at x=396, y_top=749.9 from top
    annotations = [
        {
            "page_num": 0,
            "x": 422,
            "y": PAGE_HEIGHT - 758,   # ~28.6 from bottom
            "text": today,
            "font_size": 10,
        },
    ]

    pdf_bytes = _overlay_text_annotations(pdf_bytes, annotations)

    # Overlay drawn signature on signature line
    # "Signature:" label at x=72, line area x=148 to ~390
    pdf_bytes = _overlay_signature(pdf_bytes, signature_bytes, [
        {
            "page_num": 0,
            "x": 148,
            "y": 29,
            "width": 200,
            "height": 18,
        }
    ])

    return pdf_bytes


def fill_all_county_forms(participant_data: dict, signature_bytes: bytes,
                          emergency_contact: dict = None,
                          staff_name: str = "") -> dict:
    """
    Fill all three county forms at once.
    
    Convenience function that calls all three individual fillers
    and returns a dict of {form_name: pdf_bytes}.
    
    Args:
        participant_data: Dict with first_name, last_name.
        signature_bytes: PNG bytes of the drawn signature.
        emergency_contact: Optional emergency contact dict for Attachment V.
        staff_name: Optional staff name for Attachment IV.
    
    Returns:
        dict: {
            "attachment_v": bytes,
            "attachment_iv": bytes,
            "code_of_conduct": bytes,
        }
    """
    return {
        "attachment_v": fill_attachment_v(
            participant_data, signature_bytes, emergency_contact
        ),
        "attachment_iv": fill_attachment_iv(
            participant_data, signature_bytes, staff_name
        ),
        "code_of_conduct": fill_code_of_conduct(signature_bytes),
    }
