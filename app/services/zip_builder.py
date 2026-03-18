"""
Zip file builder for participant submissions.

Packages all participant documents, forms, and signatures into an in-memory zip file.
Works with session-based data (bytes) instead of file paths.
"""

import io
import zipfile
from datetime import datetime

from app.services.pdf_filler import fill_all_county_forms


def build_submission_zip(participant):
    """
    Build a zip file from session-based participant data.

    Args:
        participant: Dict containing participant data with documents, forms, and signature
                    Documents and forms contain *_bytes fields instead of file paths.

    Returns:
        bytes: The zip file contents as bytes
    """
    # Create in-memory zip file
    zip_buffer = io.BytesIO()

    # Build zip filename prefix from participant info
    last_name = participant.get("last_name", "Unknown")
    first_name = participant.get("first_name", "Unknown")
    participant_id = participant.get("id", "unknown")
    name_prefix = f"{last_name}_{first_name}_{participant_id}"

    with zipfile.ZipFile(zip_buffer, "w", zipfile.ZIP_DEFLATED) as zf:
        # Add uploaded documents
        documents = participant.get("documents", {})
        for doc_type, doc_info in documents.items():
            doc_name = doc_info.get("doc_name", doc_type).replace(" ", "_")

            # Add PDF version from bytes
            pdf_bytes = doc_info.get("pdf_bytes")
            if pdf_bytes:
                pdf_filename = f"{doc_name}_{last_name}_{first_name}.pdf"
                zf.writestr(f"documents/{pdf_filename}", pdf_bytes)

            # Add image version from bytes (if available)
            image_bytes = doc_info.get("image_bytes")
            if image_bytes:
                img_filename = f"{doc_name}_{last_name}_{first_name}.jpg"
                zf.writestr(f"documents/{img_filename}", image_bytes)

        # Add completed forms
        forms = participant.get("forms", {})
        for form_id, form_info in forms.items():
            pdf_bytes = form_info.get("pdf_bytes")
            if pdf_bytes:
                pdf_filename = f"{form_id}_{last_name}_{first_name}.pdf"
                zf.writestr(f"forms/{pdf_filename}", pdf_bytes)

        # Add signature
        signature = participant.get("signature")
        if signature:
            sig_bytes = signature.get("image_bytes")
            if sig_bytes:
                sig_filename = f"signature_{last_name}_{first_name}.png"
                zf.writestr(f"signature/{sig_filename}", sig_bytes)

        # Add filled county forms
        signature = participant.get("signature")
        if signature:
            sig_bytes = signature.get("image_bytes")
            if sig_bytes:
                try:
                    county_forms = fill_all_county_forms(
                        participant_data=participant,
                        signature_bytes=sig_bytes,
                        emergency_contact=participant.get("emergency_contact"),
                        staff_name=participant.get("staff_name", ""),
                    )
                    for form_key, pdf_bytes in county_forms.items():
                        pdf_filename = f"{form_key}_{last_name}_{first_name}.pdf"
                        zf.writestr(f"county_forms/{pdf_filename}", pdf_bytes)
                except Exception:
                    pass  # Skip county forms if templates missing or error

        # Add participant info as text file
info_content = _build_participant_info(participant)
zf.writestr(f"{name_prefix}_info.txt", info_content)

# Add CalJOBS entry reference PDF
try:
    from app.services.calJOBS_summary import generate_calJOBS_reference
    calJOBS_pdf = generate_calJOBS_reference(participant)
    if calJOBS_pdf:
        calJOBS_filename = f"CalJOBS_Entry_Reference_{last_name}_{first_name}.pdf"
        zf.writestr(f"staff_reference/{calJOBS_filename}", calJOBS_pdf)
except Exception:
    pass

    # Get bytes from buffer
    zip_buffer.seek(0)
    return zip_buffer.getvalue()


def get_zip_filename(participant):
    """
    Generate a filename for the participant's zip file.

    Args:
        participant: Dict containing participant data

    Returns:
        str: Filename for the zip file
    """
    last_name = participant.get("last_name", "Unknown")
    first_name = participant.get("first_name", "Unknown")
    participant_id = participant.get("id", "unknown")
    date_str = datetime.now().strftime("%Y%m%d")

    return f"{last_name}_{first_name}_{participant_id}_{date_str}.zip"


def _build_participant_info(participant):
    """Build a text summary of participant information."""
    lines = [
        "INVEST Orientation Intake - Participant Submission",
        "=" * 50,
        "",
        f"Name: {participant.get('full_name', 'N/A')}",
        f"ID: {participant.get('id', 'N/A')}",
        f"Email: {participant.get('email', 'N/A')}",
        f"Phone: {participant.get('phone', 'N/A')}",
        f"Status: {participant.get('status', 'N/A')}",
        f"Created: {participant.get('created_at', 'N/A')}",
        "",
        "Documents Uploaded:",
        "-" * 30,
    ]

    documents = participant.get("documents", {})
    if documents:
        for doc_type, doc_info in documents.items():
            doc_name = doc_info.get("doc_name", doc_type)
            uploaded_at = doc_info.get("uploaded_at", "N/A")
            lines.append(f"  - {doc_name} ({uploaded_at})")
    else:
        lines.append("  (none)")

    lines.extend([
        "",
        "Forms Completed:",
        "-" * 30,
    ])

    forms = participant.get("forms", {})
    if forms:
        for form_id, form_info in forms.items():
            completed_at = form_info.get("completed_at", "N/A")
            lines.append(f"  - {form_id} ({completed_at})")
    else:
        lines.append("  (none)")

    lines.extend([
        "",
        "Signature:",
        "-" * 30,
    ])

    signature = participant.get("signature")
    if signature:
        sig_type = signature.get("type", "unknown")
        signed_at = signature.get("signed_at", "N/A")
        lines.append(f"  Type: {sig_type}")
        lines.append(f"  Signed: {signed_at}")
    else:
        lines.append("  (not signed)")

    lines.extend([
        "",
        "=" * 50,
        f"Generated: {datetime.now().isoformat()}",
    ])

    return "\n".join(lines)
