"""
WIOA Orientation Intake System
Mobile-friendly document capture for orientation check-in.

Features:
- QR code entry point
- Pre-registration links
- PDF output format
- AI document verification
- Digital signature capture
- Camera + file upload support

Run with: streamlit run app.py --server.port 8504
"""

import base64
from datetime import datetime
from PIL import Image
import io

import streamlit as st

# Optional imports for enhanced features
try:
    from streamlit_drawable_canvas import st_canvas
    HAS_CANVAS = True
except ImportError:
    HAS_CANVAS = False

try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

# Forms module
try:
    from forms import (
        ORIENTATION_FORMS, render_form, get_form_list,
        generate_form_pdf, save_form_response
    )
    HAS_FORMS = True
except ImportError:
    HAS_FORMS = False

# Configuration
from config import (
    BASE_DIR, QR_CODES_DIR, CLOUD_URL,
    DOCUMENT_GROUPS, DOCUMENT_TYPES, DOCUMENT_PATTERNS,
    MIN_WIDTH, MIN_HEIGHT, MIN_FILE_SIZE,
    EmailConfig, DEFAULT_RECIPIENTS
)

# Services
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
from app.services.email_sender import send_submission_email
from app.styling import get_app_css

# Disable Google Sheets - use local storage instead
USE_SHEETS = False

# ─── Streamlit Page Config ───────────────────────────────────────────────────

st.set_page_config(
    page_title="Orientation Intake",
    page_icon=":camera:",
    layout="centered",
    initial_sidebar_state="collapsed",
)


# Apply custom CSS styling
st.markdown(get_app_css(), unsafe_allow_html=True)


# ─── Session State ──────────────────────────────────────────────────────────

if "mode" not in st.session_state:
    st.session_state.mode = "home"
if "participant_id" not in st.session_state:
    st.session_state.participant_id = None
if "participant_data" not in st.session_state:
    st.session_state.participant_data = None
if "current_doc" not in st.session_state:
    st.session_state.current_doc = 0
if "ai_verification_enabled" not in st.session_state:
    st.session_state.ai_verification_enabled = True
if "current_form" not in st.session_state:
    st.session_state.current_form = None
if "forms_completed" not in st.session_state:
    st.session_state.forms_completed = []


# ─── Helper Functions ───────────────────────────────────────────────────────

# Participant flow order for navigation
PARTICIPANT_FLOW = ["participant_start", "participant_capture", "participant_forms", "participant_complete"]
FLOW_LABELS = {
    "participant_start": "Registration",
    "participant_capture": "Documents",
    "participant_forms": "Forms",
    "participant_complete": "Submit",
}


def render_navigation():
    """Render back/forward navigation arrows for participant flow."""
    current_mode = st.session_state.mode
    if current_mode not in PARTICIPANT_FLOW:
        return

    current_idx = PARTICIPANT_FLOW.index(current_mode)
    prev_mode = PARTICIPANT_FLOW[current_idx - 1] if current_idx > 0 else None
    next_mode = PARTICIPANT_FLOW[current_idx + 1] if current_idx < len(PARTICIPANT_FLOW) - 1 else None

    # Build step indicator
    steps_html = []
    for i, mode in enumerate(PARTICIPANT_FLOW):
        label = FLOW_LABELS[mode]
        if i < current_idx:
            steps_html.append(f'<span style="color: #28a745;">✓ {label}</span>')
        elif i == current_idx:
            steps_html.append(f'<span style="color: #1976d2; font-weight: bold;">● {label}</span>')
        else:
            steps_html.append(f'<span style="color: #999;">○ {label}</span>')

    st.markdown(f"""
    <div style="display: flex; justify-content: center; gap: 16px; margin: 8px 0 16px 0; font-size: 13px;">
        {" → ".join(steps_html)}
    </div>
    """, unsafe_allow_html=True)

    col1, col2, col3 = st.columns([1, 2, 1])

    with col1:
        if prev_mode:
            if st.button(f"← {FLOW_LABELS[prev_mode]}", key="nav_back", use_container_width=True):
                st.session_state.mode = prev_mode
                st.rerun()
        elif current_mode == "participant_start":
            if st.button("← Home", key="nav_home", use_container_width=True):
                st.session_state.mode = "home"
                st.rerun()

    with col3:
        if next_mode:
            # Only allow forward if we have participant data (past registration)
            can_go_forward = st.session_state.participant_data is not None
            if st.button(f"{FLOW_LABELS[next_mode]} →", key="nav_forward", disabled=not can_go_forward, use_container_width=True):
                st.session_state.mode = next_mode
                st.rerun()


def render_progress(participant):
    """Render document collection progress."""
    docs = participant.get("documents", {})

    # Count required groups that have at least one document
    required_groups = [g for g in DOCUMENT_GROUPS if g["required"]]
    collected = 0
    for group in required_groups:
        if any(opt["id"] in docs for opt in group["options"]):
            collected += 1

    total = len(required_groups)
    percent = int((collected / total) * 100) if total > 0 else 0

    st.markdown(f"""
    <div style="margin: 16px 0;">
        <p style="margin: 0 0 8px 0; font-weight: 600; color: #333;">
            Required Documents: {collected}/{total}
        </p>
        <div class="progress-bar">
            <div class="progress-fill" style="width: {percent}%;"></div>
        </div>
    </div>
    """, unsafe_allow_html=True)


def render_doc_status(participant, doc_type, doc_name, required):
    """Render a single document status."""
    docs = participant.get("documents", {})
    is_collected = doc_type in docs
    doc_info = docs.get(doc_type, {})
    ai_status = doc_info.get("ai_verification", {})

    req_badge = '<span style="color:#dc3545;font-weight:600;">(Required)</span>' if required else ""

    if is_collected:
        verified = ai_status.get("verified", True)
        if verified:
            st.markdown(f"""
            <div class="doc-complete">
                <span style="font-size:24px;">&#10003;</span><br>
                <strong>{doc_name}</strong> {req_badge}<br>
                <small style="color:#28a745;">Uploaded (PDF)</small>
            </div>
            """, unsafe_allow_html=True)
        else:
            st.markdown(f"""
            <div class="doc-warning">
                <span style="font-size:24px;">&#9888;</span><br>
                <strong>{doc_name}</strong> {req_badge}<br>
                <small style="color:#dc3545;">{ai_status.get('message', 'Needs review')}</small>
            </div>
            """, unsafe_allow_html=True)
    else:
        st.markdown(f"""
        <div class="doc-pending">
            <span style="font-size:24px;">&#9675;</span><br>
            <strong>{doc_name}</strong> {req_badge}<br>
            <small style="color:#856404;">Not yet uploaded</small>
        </div>
        """, unsafe_allow_html=True)


# ─── Page Functions ─────────────────────────────────────────────────────────

def home_page():
    """Landing page with role selection."""
    st.markdown("""
    <div class="main-header">
        <h1>Orientation Check-In</h1>
        <p style="margin: 8px 0 0 0; opacity: 0.9;">WIOA Document Upload</p>
    </div>
    """, unsafe_allow_html=True)

    st.markdown("### Welcome!")
    st.markdown("Please select an option below:")

    col1, col2 = st.columns(2)

    with col1:
        if st.button("Start Check-In", type="primary", width="stretch"):
            st.session_state.mode = "participant_start"
            st.rerun()

    with col2:
        if st.button("Staff Dashboard", type="secondary", width="stretch"):
            st.session_state.mode = "staff"
            st.rerun()

    # Check if there's an active session in progress
    if st.session_state.participant_data:
        st.markdown("---")
        st.markdown("##### Continue Your Session")
        participant = st.session_state.participant_data
        st.info(f"You have an active session: **{participant['full_name']}** (ID: {participant['id']})")

        if st.button("Continue Check-In", type="primary", key="continue_session"):
            st.session_state.mode = "participant_capture"
            st.rerun()

        if st.button("Start Fresh (Clear Current Session)", type="secondary", key="clear_session"):
            clear_participant_session(st.session_state)
            st.rerun()
    else:
        # No persistence message
        st.markdown("---")
        st.info("**Note:** Your session data is stored temporarily in your browser. "
                "Please complete your check-in in one sitting. If you close your browser, "
                "you will need to start over.")


def participant_start_page():
    """Participant registration page."""
    st.markdown("""
    <div class="main-header">
        <h1>Let's Get Started</h1>
        <p style="margin: 8px 0 0 0; opacity: 0.9;">Enter your information below</p>
    </div>
    """, unsafe_allow_html=True)

    render_navigation()

    with st.form("registration_form"):
        col1, col2 = st.columns(2)

        with col1:
            first_name = st.text_input("First Name *", placeholder="John")
        with col2:
            last_name = st.text_input("Last Name *", placeholder="Smith")

        st.markdown("*Please provide at least one contact method:*")
        email = st.text_input("Email", placeholder="john.smith@email.com")
        phone = st.text_input("Phone", placeholder="(555) 123-4567")

        submitted = st.form_submit_button("Continue", type="primary", width="stretch")

        if submitted:
            if not first_name or not last_name:
                st.error("Please enter your first and last name.")
            elif not email.strip() and not phone.strip():
                st.error("Please provide at least one contact method (email or phone).")
            else:
                # Initialize participant in session state (no disk write)
                participant = init_participant_session(
                    first_name.strip(),
                    last_name.strip(),
                    email.strip(),
                    phone.strip()
                )
                st.session_state.participant_data = participant
                st.session_state.participant_id = participant["id"]
                st.session_state.mode = "participant_capture"
                st.rerun()


def participant_capture_page():
    """Document capture page for participants."""
    participant = st.session_state.participant_data

    if not participant:
        st.error("Session not found. Please start over.")
        if st.button("Start Over"):
            st.session_state.mode = "home"
            clear_participant_session(st.session_state)
            st.rerun()
        return

    # Header
    pre_reg_badge = '<span style="background:#9c27b0;padding:4px 8px;border-radius:4px;font-size:12px;">PRE-REGISTRATION</span>' if participant.get("pre_registration") else ""

    st.markdown(f"""
    <div class="main-header">
        <h1>Upload Documents</h1>
        <p style="margin: 8px 0 0 0; opacity: 0.9;">
            {participant['full_name']} {pre_reg_badge}<br>
            <small>Session ID: {participant['id']}</small>
        </p>
    </div>
    """, unsafe_allow_html=True)

    render_navigation()

    # Progress
    render_progress(participant)

    # Forms section - link to digital forms
    if HAS_FORMS:
        completed_forms = participant.get("forms", {})
        total_forms = len(ORIENTATION_FORMS)
        forms_done = len(completed_forms)

        st.markdown(f"""
        <div class="info-card" style="background: linear-gradient(135deg, #e8f5e9, #c8e6c9);
                                       border: 2px solid #4caf50;">
            <h3 style="margin: 0 0 8px 0; color: #2e7d32;">WIOA Orientation Forms</h3>
            <p style="margin: 0; color: #1a1a2e;">
                Complete the required paperwork digitally - no paper needed!<br>
                <strong>Progress: {forms_done}/{total_forms} forms completed</strong>
            </p>
        </div>
        """, unsafe_allow_html=True)

        if st.button("Complete Orientation Forms", type="primary", width="stretch"):
            st.session_state.mode = "participant_forms"
            st.rerun()

        st.markdown("---")

    # Document upload section - grouped format
    st.markdown("### Upload Documents")

    # Process each document group
    for group in DOCUMENT_GROUPS:
        group_id = group["id"]
        group_name = group["name"]
        is_required = group["required"]
        options = group["options"]

        # Check if this group already has a document uploaded
        group_uploaded = any(
            opt["id"] in participant.get("documents", {})
            for opt in options
        )
        uploaded_doc = None
        for opt in options:
            if opt["id"] in participant.get("documents", {}):
                uploaded_doc = opt
                break

        # Group header with status
        req_badge = '<span style="color:#dc3545;font-weight:600;">(Required)</span>' if is_required else '<span style="color:#666;">(Optional)</span>'
        status_icon = "&#10003;" if group_uploaded else "&#9675;"
        status_color = "#28a745" if group_uploaded else ("#ffc107" if is_required else "#6c757d")

        st.markdown(f"""
        <div style="background: {'#d4edda' if group_uploaded else '#f8f9fa'};
                    border: 2px solid {status_color}; border-radius: 12px;
                    padding: 16px; margin: 12px 0;">
            <h4 style="margin: 0 0 8px 0; color: #1a1a2e;">
                <span style="font-size: 20px;">{status_icon}</span> {group_name} {req_badge}
            </h4>
            <p style="margin: 0; color: #555; font-size: 14px;">{group["description"]}</p>
            {f'<p style="margin: 8px 0 0 0; color: #28a745;"><strong>Uploaded:</strong> {uploaded_doc["name"]}</p>' if uploaded_doc else ''}
        </div>
        """, unsafe_allow_html=True)

        # Dropdown to select which document type
        option_names = [opt["name"] for opt in options]

        with st.expander(f"{'Change' if group_uploaded else 'Upload'} {group_name}", expanded=not group_uploaded and is_required):
            selected_option = st.selectbox(
                f"Select type:",
                options=range(len(option_names)),
                format_func=lambda x, opts=option_names: opts[x],
                key=f"select_{group_id}"
            )

            selected_doc = options[selected_option]
            doc_type = selected_doc["id"]
            doc_name = selected_doc["name"]

            # Upload method tabs
            tab_camera, tab_upload = st.tabs(["📷 Take Photo", "📁 Upload File"])

            image_to_save = None

            with tab_camera:
                st.markdown(f"**Take a photo of your {doc_name}:**")
                camera_image = st.camera_input(
                    f"Capture {doc_name}",
                    key=f"camera_{group_id}_{doc_type}",
                    label_visibility="collapsed"
                )
                if camera_image:
                    image_to_save = camera_image

            with tab_upload:
                st.markdown(f"**Upload your {doc_name}:**")
                st.caption("Select from gallery or files")
                uploaded_file = st.file_uploader(
                    "Choose file",
                    type=["jpg", "jpeg", "png", "pdf"],
                    key=f"upload_{group_id}_{doc_type}",
                    label_visibility="collapsed"
                )
                if uploaded_file:
                    image_to_save = uploaded_file

            # Process the upload
            if image_to_save:
                is_pdf = hasattr(image_to_save, 'type') and image_to_save.type == "application/pdf"

                if not is_pdf:
                    st.image(image_to_save, caption=f"Preview: {doc_name}", width="stretch")
                    quality_result = check_image_quality(image_to_save.getvalue())

                    if quality_result["issues"]:
                        st.error("**Quality Issues:** " + ", ".join(quality_result["issues"]))
                    elif quality_result["warnings"]:
                        st.warning("**Warnings:** " + ", ".join(quality_result["warnings"]))
                    else:
                        st.success("Image quality looks good!")
                else:
                    st.success(f"PDF ready: {image_to_save.name}")

                # Save button
                if st.button(f"Save {doc_name}", type="primary", key=f"save_{group_id}", width="stretch"):
                    with st.spinner("Saving..."):
                        if is_pdf:
                            # Store PDF bytes in session
                            doc_info = convert_pdf_to_bytes(
                                image_to_save.getvalue(),
                                doc_type,
                                doc_name,
                                group_id
                            )
                            st.session_state.participant_data["documents"][doc_type] = doc_info
                            st.success(f"{doc_name} saved!")
                            st.rerun()
                        else:
                            # Process and store image as PDF bytes
                            image_data = image_to_save.getvalue()
                            image_data = enhance_image(image_data)

                            ai_result = None
                            if st.session_state.ai_verification_enabled and HAS_ANTHROPIC:
                                ai_result = verify_document_with_ai(image_data, doc_type)

                            # Store bytes in session (no disk write)
                            doc_info = convert_image_to_pdf_bytes(
                                image_data,
                                doc_type,
                                doc_name,
                                group_id,
                                ai_result
                            )
                            st.session_state.participant_data["documents"][doc_type] = doc_info
                            st.success(f"{doc_name} saved!")
                            st.rerun()

    # Photo tips
    with st.expander("📸 Tips for a Good Photo", expanded=False):
        col1, col2 = st.columns(2)
        with col1:
            st.markdown("""
            **DO:**
            - Place document on a **dark, flat surface**
            - Make sure **all 4 corners** are visible
            - Use **good lighting** (natural light is best)
            - Hold phone **steady and straight**
            - Fill the frame with the document
            """)
        with col2:
            st.markdown("""
            **DON'T:**
            - Don't cut off any edges
            - Don't use flash (causes glare)
            - Don't take at an angle
            - Don't photograph in low light
            - Don't include fingers in the shot
            """)

        st.markdown("""
        <div style="background: #e8f5e9; padding: 12px; border-radius: 8px; margin-top: 8px;">
            <strong style="color: #2e7d32;">✓ GOOD:</strong> <span style="color: #1a1a2e;">Flat, all corners visible, clear text, good lighting</span><br>
            <strong style="color: #c62828;">✗ BAD:</strong> <span style="color: #1a1a2e;">Angled, edges cut off, blurry, too dark, glare</span>
        </div>
        """, unsafe_allow_html=True)

    st.markdown("---")

    # Signature section - highly visible
    st.markdown("""
    <div class="signature-section">
        <h3 style="color: #1565c0; margin: 0 0 8px 0;">✍️ Digital Signature Required</h3>
        <p style="color: #1a1a2e; margin: 0;">Sign below to acknowledge your participation in WIOA services.</p>
    </div>
    """, unsafe_allow_html=True)

    if participant.get("signature"):
        st.success("Signature captured!")
        sig_preview = get_signature_preview_base64(participant["signature"])
        if sig_preview:
            st.markdown(f'<img src="{sig_preview}" alt="Your Signature" width="300">', unsafe_allow_html=True)
        elif participant["signature"].get("type") == "acknowledgment":
            st.info("Acknowledged via checkbox")
    else:
        if HAS_CANVAS:
            st.markdown("**Draw your signature below:**")
            canvas_result = st_canvas(
                fill_color="rgba(255, 255, 255, 0)",
                stroke_width=3,
                stroke_color="#000000",
                background_color="#ffffff",
                height=150,
                width=600,
                drawing_mode="freedraw",
                key=f"signature_{participant['id']}",
            )

            if st.button("Save Signature", type="primary", width="stretch"):
                if canvas_result.image_data is not None:
                    # Convert to PIL Image
                    img = Image.fromarray(canvas_result.image_data.astype("uint8"), "RGBA")
                    # Check if anything was drawn (not all white)
                    if img.getbbox():
                        # Store signature bytes in session (no disk write)
                        sig_info = convert_signature_to_bytes(img, "drawn")
                        st.session_state.participant_data["signature"] = sig_info
                        st.success("Signature saved!")
                        st.rerun()
                    else:
                        st.warning("Please sign above before saving.")
        else:
            st.warning("Signature pad not available. Please use the checkbox below instead.")
            st.info("To enable signature drawing, install: `pip install streamlit-drawable-canvas`")
            # Fallback: checkbox acknowledgment
            if st.checkbox("✓ I acknowledge my participation in WIOA services (signature alternative)"):
                sig_info = convert_signature_to_bytes(None, "acknowledgment")
                st.session_state.participant_data["signature"] = sig_info
                st.success("Acknowledgment recorded!")
                st.rerun()

    st.markdown("---")

    # Check if all required document groups have at least one document
    docs = participant.get("documents", {})
    all_required_collected = True
    for group in DOCUMENT_GROUPS:
        if group["required"]:
            group_has_doc = any(
                opt["id"] in docs for opt in group["options"]
            )
            if not group_has_doc:
                all_required_collected = False
                break

    has_signature = participant.get("signature") is not None

    if all_required_collected and has_signature:
        st.success("All required documents and signature have been captured!")
        if st.button("Complete Check-In", type="primary", width="stretch"):
            # Update status in session
            st.session_state.participant_data["status"] = "complete"
            st.session_state.mode = "participant_complete"
            st.rerun()
    elif all_required_collected:
        st.info("Please provide your signature above to complete check-in.")
    else:
        st.info("Please upload all required documents to complete check-in.")

    # Warning about session persistence
    st.markdown("---")
    st.warning("**Important:** Your data is stored temporarily in your browser. "
               "Please complete your check-in now - if you close your browser, you will need to start over.")


def participant_forms_page():
    """Digital forms page for participants to complete WIOA paperwork."""
    participant = st.session_state.participant_data

    if not participant:
        st.error("Session not found. Please start over.")
        if st.button("Start Over"):
            st.session_state.mode = "home"
            clear_participant_session(st.session_state)
            st.rerun()
        return

    if not HAS_FORMS:
        st.error("Forms module not available.")
        if st.button("Back to Documents"):
            st.session_state.mode = "participant_capture"
            st.rerun()
        return

    # Header
    st.markdown("""
    <div class="main-header" style="background: linear-gradient(135deg, #00796b, #009688);">
        <h1>Complete Forms</h1>
        <p style="margin: 8px 0 0 0; opacity: 0.9;">WIOA Orientation Paperwork</p>
    </div>
    """, unsafe_allow_html=True)

    render_navigation()

    # Get completed forms
    completed_forms = participant.get("forms", {})
    form_list = get_form_list()

    # Show progress
    total_forms = len(form_list)
    completed_count = len(completed_forms)
    progress_pct = int((completed_count / total_forms) * 100) if total_forms > 0 else 0

    st.markdown(f"""
    <div style="margin: 16px 0;">
        <p style="margin: 0 0 8px 0; font-weight: 600; color: #333;">
            Forms Completed: {completed_count}/{total_forms}
        </p>
        <div class="progress-bar">
            <div class="progress-fill" style="width: {progress_pct}%;"></div>
        </div>
    </div>
    """, unsafe_allow_html=True)

    # Signature section - show at top if not signed yet
    if participant.get("signature"):
        # Already signed - show confirmation
        st.markdown("""
        <div style="background: #d4edda; border: 2px solid #28a745; border-radius: 8px;
                    padding: 12px; margin: 16px 0;">
            <span style="font-size: 20px;">✓</span>
            <strong style="color: #1a1a2e;">Signature on file</strong> -
            <span style="color: #555;">Your signature will be applied to all forms automatically.</span>
        </div>
        """, unsafe_allow_html=True)
    else:
        # Need signature - show canvas
        st.markdown("""
        <div class="signature-section" style="background: #fff3cd; border: 3px solid #ffc107;
                    border-radius: 12px; padding: 16px; margin: 16px 0;">
            <h3 style="color: #856404; margin: 0 0 8px 0;">✍️ Please Sign First</h3>
            <p style="color: #1a1a2e; margin: 0;">
                Your signature will be automatically applied to all forms you complete.
            </p>
        </div>
        """, unsafe_allow_html=True)

        if HAS_CANVAS:
            st.markdown("**Draw your signature below:**")
            canvas_result = st_canvas(
                fill_color="rgba(255, 255, 255, 0)",
                stroke_width=3,
                stroke_color="#000000",
                background_color="#ffffff",
                height=150,
                width=600,
                drawing_mode="freedraw",
                key=f"forms_signature_{participant['id']}",
            )

            if st.button("Save Signature", type="primary", width="stretch", key="save_sig_forms"):
                if canvas_result.image_data is not None:
                    img = Image.fromarray(canvas_result.image_data.astype("uint8"), "RGBA")
                    if img.getbbox():
                        # Store signature bytes in session (no disk write)
                        sig_info = convert_signature_to_bytes(img, "drawn")
                        st.session_state.participant_data["signature"] = sig_info
                        st.success("Signature saved! It will be applied to all forms.")
                        st.rerun()
                    else:
                        st.warning("Please sign above before saving.")
        else:
            st.warning("Signature pad not available.")
            st.info("To enable signature drawing, install: `pip install streamlit-drawable-canvas`")
            if st.checkbox("✓ I acknowledge this as my electronic signature", key="sig_ack_forms"):
                sig_info = convert_signature_to_bytes(None, "acknowledgment")
                st.session_state.participant_data["signature"] = sig_info
                st.success("Acknowledgment recorded!")
                st.rerun()

        st.markdown("---")

    # If a form is selected, show it
    if st.session_state.current_form:
        form_id = st.session_state.current_form
        form_def = ORIENTATION_FORMS.get(form_id, {})

        st.markdown("---")

        # Get existing form data
        existing_data = completed_forms.get(form_id, {}).get("data", {})

        # Render the form WITHOUT st.form() wrapper so conditional fields update immediately
        form_data = render_form(form_id, existing_data, participant)

        # Signature section - show status
        if form_def.get("signature_required"):
            st.markdown("---")
            if participant.get("signature"):
                st.markdown("""
                <div style="background: #d4edda; border: 2px solid #28a745; border-radius: 8px;
                            padding: 12px; margin: 8px 0;">
                    <span style="font-size: 18px;">✓</span>
                    <strong style="color: #155724;">Your signature will be applied to this form.</strong>
                </div>
                """, unsafe_allow_html=True)
                if form_data:
                    form_data['signature_confirmed'] = True
            else:
                st.warning("Please sign at the top of the page before submitting this form.")

        # Submit buttons (regular buttons, not form buttons)
        st.markdown("---")
        col_submit, col_cancel = st.columns(2)
        with col_submit:
            submitted = st.button("Save Form", type="primary", width="stretch", key=f"submit_{form_id}")
        with col_cancel:
            cancelled = st.button("Cancel", width="stretch", key=f"cancel_{form_id}")

        # Handle form submission
        if submitted:
            # Save form data
            try:
                # Ensure form_data is a dict
                saved_data = form_data if form_data else {}

                # Get participant from session
                participant = st.session_state.participant_data
                if not participant.get("forms"):
                    participant["forms"] = {}

                # Get signature bytes for PDF generation
                sig_bytes = None
                if participant.get("signature"):
                    sig_bytes = participant["signature"].get("image_bytes")

                # Generate PDF (returns bytes, no disk write)
                pdf_bytes, error = generate_form_pdf(
                    form_id, saved_data, participant,
                    signature_image=sig_bytes
                )

                if error:
                    st.error(f"Error generating PDF: {error}")
                else:
                    # Store form data and PDF bytes in session
                    participant["forms"][form_id] = {
                        "data": saved_data,
                        "completed_at": datetime.now().isoformat(),
                        "status": "completed",
                        "pdf_bytes": pdf_bytes
                    }

                    st.success("Form saved!")
                    # Clear form and go back to list
                    st.session_state.current_form = None
                    st.rerun()

            except Exception as e:
                st.error(f"Error saving form: {str(e)}")

        if cancelled:
            st.session_state.current_form = None
            st.rerun()

    else:
        # Show form selection
        st.markdown("### Select a Form to Complete")

        # Group by category
        simple_forms = [f for f in form_list if f['category'] == 'simple']
        medium_forms = [f for f in form_list if f['category'] == 'medium']
        complex_forms = [f for f in form_list if f['category'] == 'complex']

        # Quick signature forms (simple)
        st.markdown("#### Quick Signature Forms")
        st.caption("These are policy acknowledgements - just read and sign")

        cols = st.columns(2)
        for i, form in enumerate(simple_forms):
            with cols[i % 2]:
                is_complete = form['id'] in completed_forms
                status_icon = "&#10003;" if is_complete else "&#9675;"
                status_color = "#28a745" if is_complete else "#ffc107"

                st.markdown(f"""
                <div style="background: {'#d4edda' if is_complete else '#fff3cd'};
                            border: 2px solid {status_color}; border-radius: 8px;
                            padding: 12px; margin: 4px 0; color: #1a1a2e;">
                    <span style="font-size: 18px;">{status_icon}</span>
                    <strong>{form['title']}</strong>
                </div>
                """, unsafe_allow_html=True)

                if st.button("Open" if not is_complete else "Edit", key=f"open_{form['id']}", width="stretch"):
                    st.session_state.current_form = form['id']
                    st.rerun()

        # Forms with fields
        st.markdown("#### Forms with Information")
        st.caption("These require entering some information")

        for form in medium_forms + complex_forms:
            is_complete = form['id'] in completed_forms
            status_icon = "&#10003;" if is_complete else "&#9675;"
            status_color = "#28a745" if is_complete else "#ffc107"

            col1, col2 = st.columns([3, 1])
            with col1:
                st.markdown(f"""
                <div style="background: {'#d4edda' if is_complete else '#fff3cd'};
                            border: 2px solid {status_color}; border-radius: 8px;
                            padding: 12px; margin: 4px 0; color: #1a1a2e;">
                    <span style="font-size: 18px;">{status_icon}</span>
                    <strong>{form['title']}</strong><br>
                    <small style="color: #666;">{form['description']}</small>
                </div>
                """, unsafe_allow_html=True)
            with col2:
                if st.button("Open" if not is_complete else "Edit", key=f"open_{form['id']}", width="stretch"):
                    st.session_state.current_form = form['id']
                    st.rerun()

        # Check if all forms complete
        st.markdown("---")
        if completed_count == total_forms:
            st.success("All forms completed!")
            if st.button("Continue to Document Upload", type="primary", width="stretch"):
                st.session_state.mode = "participant_capture"
                st.rerun()
        else:
            remaining = total_forms - completed_count
            st.info(f"{remaining} form(s) remaining. Complete all forms to proceed.")


def participant_complete_page():
    """Email delivery page - sends submission and clears session on success."""
    participant = st.session_state.participant_data

    if not participant:
        st.error("Session not found. Please start over.")
        if st.button("Start Over"):
            st.session_state.mode = "home"
            clear_participant_session(st.session_state)
            st.rerun()
        return

    st.markdown("""
    <div class="main-header" style="background: linear-gradient(135deg, #1565c0, #1976d2);">
        <h1>Submit Your Documents</h1>
        <p style="margin: 8px 0 0 0; opacity: 0.9;">Review and send your submission</p>
    </div>
    """, unsafe_allow_html=True)

    render_navigation()

    # Submission summary
    doc_count = len(participant.get("documents", {}))
    form_count = len(participant.get("forms", {}))
    has_signature = bool(participant.get("signature"))

    st.markdown(f"""
    <div class="info-card">
        <h3 style="margin-top: 0;">Submission Summary</h3>
        <p><strong>Name:</strong> {participant['full_name']}</p>
        <p><strong>Session ID:</strong> {participant['id']}</p>
        <p><strong>Documents:</strong> {doc_count}</p>
        <p><strong>Forms Completed:</strong> {form_count}</p>
        <p><strong>Signature:</strong> {"Yes" if has_signature else "No"}</p>
    </div>
    """, unsafe_allow_html=True)

    # Document list
    if participant.get("documents"):
        st.markdown("**Documents included:**")
        for doc_type, doc_info in participant["documents"].items():
            st.markdown(f"- {doc_info.get('doc_name', doc_type)}")

    # Forms list
    if participant.get("forms"):
        st.markdown("**Forms included:**")
        for form_id, form_info in participant["forms"].items():
            st.markdown(f"- {form_id}")

    st.markdown("---")

    # Email delivery section
    st.markdown("### Send Submission")

    if not EmailConfig.is_configured():
        st.error("Email is not configured. Please contact staff to complete your submission.")
        st.info("Staff: Set SMTP_SERVER, SMTP_USERNAME, and SMTP_PASSWORD in the .env file.")

        # Still allow starting over
        if st.button("Start New Check-In", type="secondary"):
            clear_participant_session(st.session_state)
            st.session_state.mode = "home"
            st.rerun()
        return

    # Build recipient options
    recipient_options = list(DEFAULT_RECIPIENTS) if DEFAULT_RECIPIENTS else []
    recipient_options.append("Custom...")

    # Recipient selection
    selected_recipient = st.selectbox(
        "Send to:",
        options=recipient_options,
        key="email_recipient"
    )

    # Custom email input
    custom_email = ""
    if selected_recipient == "Custom...":
        custom_email = st.text_input(
            "Enter email address:",
            key="custom_email"
        )

    # Determine final recipient
    final_recipient = custom_email if selected_recipient == "Custom..." else selected_recipient

    # Send button
    col1, col2 = st.columns(2)

    with col1:
        if st.button("Send Submission", type="primary", width="stretch", disabled=not final_recipient):
            if not final_recipient:
                st.error("Please enter a valid email address.")
            else:
                with st.spinner("Building zip file and sending email..."):
                    try:
                        # Build the zip file from session data
                        zip_bytes = build_submission_zip(participant)
                        zip_filename = get_zip_filename(participant)

                        # Send the email
                        subject = f"INVEST Submission: {participant.get('full_name', 'Unknown')}"
                        success = send_submission_email(
                            recipient=final_recipient,
                            subject=subject,
                            zip_bytes=zip_bytes,
                            zip_filename=zip_filename
                        )

                        if success:
                            # Clear session data and go to success page
                            st.session_state.email_sent_to = final_recipient
                            st.session_state.participant_name = participant.get('full_name', 'Participant')
                            clear_participant_session(st.session_state)
                            st.session_state.mode = "submission_success"
                            st.rerun()
                        else:
                            st.error("Failed to send email. Please try again or contact staff.")
                    except Exception as e:
                        st.error(f"Error: {str(e)}")

    with col2:
        if st.button("Cancel", width="stretch"):
            st.session_state.mode = "participant_capture"
            st.rerun()

    # Warning
    st.markdown("---")
    st.warning("**Important:** After sending, your session data will be cleared. "
               "Make sure all information is correct before sending.")


def submission_success_page():
    """Success page shown after email is sent and session is cleared."""
    st.markdown("""
    <div class="main-header" style="background: linear-gradient(135deg, #28a745, #20c997);">
        <h1>Submission Complete!</h1>
        <p style="margin: 8px 0 0 0; opacity: 0.9;">Your documents have been sent</p>
    </div>
    """, unsafe_allow_html=True)

    # Show success details
    email_sent_to = st.session_state.get("email_sent_to", "staff")
    participant_name = st.session_state.get("participant_name", "Participant")

    st.markdown(f"""
    <div class="info-card" style="background: #d4edda; border: 2px solid #28a745;">
        <h3 style="margin-top: 0; color: #155724;">Success!</h3>
        <p><strong>{participant_name}</strong>, your submission has been sent to:</p>
        <p style="font-size: 16px; font-weight: bold;">{email_sent_to}</p>
    </div>
    """, unsafe_allow_html=True)

    st.markdown("""
    <div class="info-card">
        <h3 style="margin-top: 0;">Next Steps</h3>
        <p>Please have a seat. A staff member will call your name shortly.</p>
        <p>If you have any questions, please let the front desk know.</p>
    </div>
    """, unsafe_allow_html=True)

    if st.button("Start New Check-In", type="primary", width="stretch"):
        # Clear any leftover state
        st.session_state.pop("email_sent_to", None)
        st.session_state.pop("participant_name", None)
        st.session_state.mode = "home"
        st.rerun()


def participant_exit_page():
    """Exit page - warns about session loss since we don't persist."""
    participant = st.session_state.participant_data

    st.markdown("""
    <div class="main-header" style="background: linear-gradient(135deg, #f44336, #e91e63);">
        <h1>Warning: Session Will Be Lost</h1>
        <p style="margin: 8px 0 0 0; opacity: 0.9;">Your data is not saved</p>
    </div>
    """, unsafe_allow_html=True)

    st.warning("**Important:** If you leave now, all your uploaded documents and forms will be lost. "
               "This system does not save data between sessions.")

    if participant:
        st.markdown(f"""
        <div class="info-card">
            <h3 style="margin-top: 0;">Current Progress</h3>
            <p><strong>Name:</strong> {participant['full_name']}</p>
            <p><strong>Documents:</strong> {len(participant.get('documents', {}))}</p>
            <p><strong>Forms:</strong> {len(participant.get('forms', {}))}</p>
            <p><strong>Signature:</strong> {"Yes" if participant.get('signature') else "No"}</p>
        </div>
        """, unsafe_allow_html=True)

    col1, col2 = st.columns(2)

    with col1:
        if st.button("Go Back (Keep Working)", type="primary", width="stretch"):
            st.session_state.mode = "participant_capture"
            st.rerun()

    with col2:
        if st.button("Leave Anyway (Lose Data)", type="secondary", width="stretch"):
            clear_participant_session(st.session_state)
            st.session_state.mode = "home"
            st.rerun()


def staff_dashboard():
    """Staff dashboard - simplified for no-persistence mode."""
    st.markdown("""
    <div class="main-header" style="background: linear-gradient(135deg, #37474f, #455a64);">
        <h1>Staff Dashboard</h1>
        <p style="margin: 8px 0 0 0; opacity: 0.9;">Orientation Check-In Management</p>
    </div>
    """, unsafe_allow_html=True)

    if st.button("< Back to Home"):
        st.session_state.mode = "home"
        st.rerun()

    # System status
    st.markdown("### System Status")

    col1, col2 = st.columns(2)

    with col1:
        # Email configuration status
        if EmailConfig.is_configured():
            st.success("**Email:** Configured")
        else:
            st.error("**Email:** Not configured")
            st.caption("Set SMTP_SERVER, SMTP_USERNAME, and SMTP_PASSWORD in .env file")

    with col2:
        # Default recipients
        if DEFAULT_RECIPIENTS:
            st.info(f"**Default Recipients:** {len(DEFAULT_RECIPIENTS)}")
            for recipient in DEFAULT_RECIPIENTS:
                st.caption(f"- {recipient}")
        else:
            st.warning("**Default Recipients:** None configured")
            st.caption("Set DEFAULT_RECIPIENTS in .env file")

    st.markdown("---")

    # QR Code section
    st.markdown("### QR Code for Participant Check-In")

    # Use cloud URL if set, otherwise fall back to local IP
    if CLOUD_URL:
        checkin_url = CLOUD_URL
    else:
        local_ip = get_local_ip()
        port = 8504
        checkin_url = f"http://{local_ip}:{port}"

    st.markdown(f"**Share this URL:** `{checkin_url}`")

    if HAS_QRCODE:
        qr_path = generate_qr_code(checkin_url)
        if qr_path and qr_path.exists():
            col1, col2 = st.columns([1, 1])
            with col1:
                st.image(str(qr_path), caption="Scan to Check In", width=200)
            with col2:
                st.markdown("**How to use:**")
                st.markdown("1. Print this QR code")
                st.markdown("2. Post in waiting area")
                st.markdown("3. Participants scan with phone")
                st.markdown("4. They complete forms on their device")
                st.markdown("5. Submission is emailed directly")

                with open(qr_path, "rb") as f:
                    st.download_button(
                        label="Download QR Code",
                        data=f.read(),
                        file_name="orientation_checkin_qr.png",
                        mime="image/png",
                    )
    else:
        st.warning("Install `qrcode` for QR code: `pip install qrcode[pil]`")

    st.markdown("---")

    # No-persistence mode explanation
    st.markdown("### About This System")

    st.info("""
    **No-Persistence Mode**

    This system is configured for privacy-first operation:

    - **No data is stored on the server** - All participant data exists only in their browser session
    - **Direct email delivery** - When participants complete check-in, their documents are emailed directly
    - **Automatic cleanup** - Session data is cleared after successful submission
    - **No participant list** - Staff cannot view or manage submissions (they're sent via email)

    This approach ensures participant data is never stored on shared systems.
    """)

    st.markdown("### Workflow")

    st.markdown("""
    1. **Participant scans QR code** on their phone
    2. **Fills out registration** and uploads documents
    3. **Completes required forms** digitally
    4. **Provides signature**
    5. **Submits via email** - Documents sent to configured recipients
    6. **Session cleared** - No data remains on system

    All submissions arrive in the configured email inbox(es) as zip files containing:
    - Uploaded documents (as PDFs)
    - Completed forms (as PDFs)
    - Signature image
    - Summary text file
    """)


def staff_qr_page():
    """QR code generation page for staff."""
    st.markdown("""
    <div class="main-header" style="background: linear-gradient(135deg, #37474f, #455a64);">
        <h1>QR Code for Check-In</h1>
        <p style="margin: 8px 0 0 0; opacity: 0.9;">Print this for participants to scan</p>
    </div>
    """, unsafe_allow_html=True)

    if st.button("< Back to Dashboard"):
        st.session_state.mode = "staff"
        st.rerun()

    # Get local IP
    local_ip = get_local_ip()
    port = 8504

    # URLs
    local_url = f"http://localhost:{port}"
    network_url = f"http://{local_ip}:{port}"

    st.markdown("### Access URLs")
    st.code(f"This computer: {local_url}")
    st.code(f"Other devices (same WiFi): {network_url}")

    st.markdown("---")

    if HAS_QRCODE:
        st.markdown("### QR Code (for phones on same network)")

        # Generate QR code
        qr_path = generate_qr_code(network_url)

        if qr_path and qr_path.exists():
            st.markdown('<div class="qr-container">', unsafe_allow_html=True)
            st.image(str(qr_path), caption="Scan to Check In", width=300)
            st.markdown("</div>", unsafe_allow_html=True)

            # Download button
            with open(qr_path, "rb") as f:
                st.download_button(
                    label="Download QR Code",
                    data=f.read(),
                    file_name="orientation_checkin_qr.png",
                    mime="image/png",
                    width="stretch"
                )

            st.markdown("---")
            st.markdown("### How to Use")
            st.markdown("""
            1. **Print this QR code** and post it in the waiting area
            2. Participants **scan with their phone camera**
            3. They fill out info and upload documents on their own phone
            4. Staff sees submissions in the dashboard
            """)
    else:
        st.warning("QR code generation requires the `qrcode` library. Install with: `pip install qrcode[pil]`")
        st.markdown("**For now, share this URL with participants:**")
        st.code(network_url)


# ─── Main Router ────────────────────────────────────────────────────────────

def main():
    mode = st.session_state.mode

    if mode == "home":
        home_page()
    elif mode == "participant_start":
        participant_start_page()
    elif mode == "participant_capture":
        participant_capture_page()
    elif mode == "participant_forms":
        participant_forms_page()
    elif mode == "participant_complete":
        participant_complete_page()
    elif mode == "participant_exit":
        participant_exit_page()
    elif mode == "submission_success":
        submission_success_page()
    elif mode == "staff":
        staff_dashboard()
    elif mode == "staff_qr":
        staff_qr_page()
    else:
        home_page()


if __name__ == "__main__":
    main()
