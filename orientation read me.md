# INVEST Orientation Intake Portal

A zero-persistence digital intake system for workforce development program orientations. Participants complete paperwork, upload documents, and provide signatures through a web interface — everything is packaged into a zip file and emailed directly to staff. Nothing is stored on the server.

## The Problem

Program orientations required one staff member to proctor paperwork while another handled computer input. With more than three participants, the process became chaotic — documents were misfiled, signatures missed, and the entire process took 2-3 hours per person. Non-tech-savvy staff compounded errors under pressure, and compliance requirements meant every document had to be properly filed and accounted for.

## The Solution

This system moves orientation paperwork entirely online. Participants receive a link, complete 14 digital forms, upload required documents (government ID, proof of address, work authorization), and sign electronically. On submission, everything is packaged into an organized zip file and emailed to the designated staff member. The server retains nothing — full compliance with data handling requirements.

Orientation time drops from 2-3 hours to approximately 30 minutes per participant.

## Key Features

- **Zero-Persistence Architecture** — All data lives in the browser session. On submission, files are packaged in memory, emailed, and discarded. Nothing touches the server's filesystem.
- **14 Digital Orientation Forms** — Complete form suite with conditional field logic, validation, and PDF generation matching original paper formats.
- **County Form Auto-Fill** — Automatically populates county-required WIOA forms (Attachment V, Attachment IV, Code of Conduct) with participant data and embeds drawn signatures at the correct positions.
- **AI-Powered Document Verification** — Uses Claude Vision API to validate that uploaded documents match the expected type (e.g., confirms a government ID is actually an ID, not a utility bill).
- **Digital Signature Capture** — Works on phone, tablet, or computer. Signatures are embedded directly into generated PDFs and county forms.
- **Image Quality Checking** — Validates uploaded document photos meet minimum resolution and quality thresholds before accepting them.
- **QR Code Check-In** — Generates QR codes for participants to scan and begin the intake process on their own device.
- **Step-by-Step Navigation** — Back/forward arrows with progress indicator let participants move between sections while preserving entered data.
- **Automatic File Naming & Organization** — Zip files arrive with documents, forms, county forms, and signatures organized into labeled folders with consistent naming conventions.
- **Email Delivery with Recipient Management** — Pre-configured default recipients with option for custom email entry and send confirmation.
- **Mobile-Friendly Interface** — Responsive design for participants completing intake on phones or tablets.
- **Configurable for Multiple Programs** — Architecture supports adaptation for different programs through configuration changes rather than code changes.
- **Deployment-Ready** — Configured for Streamlit Community Cloud deployment with secrets management.

## Tech Stack

- **Runtime:** Python 3.11+
- **Web Framework:** Streamlit
- **AI Integration:** Anthropic Claude Vision API (document verification)
- **PDF Generation:** ReportLab (form creation), pypdf (county form filling)
- **Email Delivery:** smtplib (Gmail SMTP)
- **Image Processing:** Pillow (PIL)
- **QR Codes:** qrcode library
- **Data Handling:** In-memory only (BytesIO, session state)

## Project Structure

```
orientation-intake/
├── app.py                     # Main Streamlit application (routing + pages)
├── config.py                  # Central configuration (paths, email, constants)
├── forms.py                   # 14 form definitions + PDF generation
├── sheets.py                  # Google Sheets integration (optional, disabled)
├── requirements.txt           # Python dependencies
├── .env.example               # Environment variable template
│
├── app/
│   ├── __init__.py
│   ├── styling.py             # CSS styling module
│   └── services/              # Modular service layer
│       ├── __init__.py        # Service exports
│       ├── image_processor.py # Image quality validation and enhancement
│       ├── data_manager.py    # Session-based data management (no disk I/O)
│       ├── document_verifier.py # AI document verification (Claude Vision)
│       ├── email_sender.py    # SMTP email delivery with zip attachments
│       ├── pdf_filler.py      # County form auto-fill with signature overlay
│       ├── qr_generator.py    # QR code generation for check-in URLs
│       └── zip_builder.py     # In-memory zip packaging from session data
│
├── templates/
│   └── county_forms/          # Blank county PDF templates
│       ├── Attachment_V_WIOA_Applicant_Acknowledgement_Statements.pdf
│       ├── Attachment_IV_WIOA_Complaint_Resolutions__Participant_Acceptance_Form.pdf
│       └── code_of_conduct.pdf
│
├── program_configs/           # Program-specific configuration (JSON)
├── static/                    # CSS and JavaScript assets
├── qr_codes/                  # Generated QR code images (cache)
└── .streamlit/                # Streamlit configuration
    └── config.toml
```

## Services Architecture

The `app/services/` module provides a clean separation of concerns:

| Service | Purpose |
|---------|---------|
| `image_processor.py` | Validates image quality (resolution, file size) and enhances uploads |
| `data_manager.py` | Manages session state, converts images/signatures to bytes |
| `document_verifier.py` | AI-powered document type verification via Claude Vision |
| `email_sender.py` | SMTP email delivery with zip attachments |
| `pdf_filler.py` | Auto-fills county WIOA forms with participant data and signatures |
| `qr_generator.py` | Generates QR codes for participant check-in URLs |
| `zip_builder.py` | Packages all data into organized zip files in-memory |

All services operate in-memory with no disk I/O for participant data.

## County Form Auto-Fill

The `pdf_filler.py` service automatically fills three county-required WIOA forms:

1. **Attachment V** — WIOA Applicant Acknowledgement Statements (fillable PDF fields + signature overlay)
2. **Attachment IV** — WIOA Complaint Resolution / Participant Acceptance Form (text overlay + signature)
3. **Code of Conduct** — AJCC Code of Conduct (date + signature overlay)

Each form is populated with participant name, date, and the drawn signature positioned at the correct coordinates. The filled PDFs are included in the submission zip under `county_forms/`.

## Setup

### 1. Clone the repository

```bash
git clone <your-repo-url>
cd orientation-intake
```

### 2. Install dependencies

```bash
pip install -r requirements.txt
```

### 3. Configure environment

```bash
copy .env.example .env
```

Edit `.env` with your actual values:

```
ANTHROPIC_API_KEY=your_api_key_here
SMTP_SERVER=smtp.gmail.com
SMTP_PORT=587
SMTP_USERNAME=your_email@gmail.com
SMTP_PASSWORD=your_gmail_app_password
DEFAULT_RECIPIENTS=staff1@org.com,staff2@org.com
```

For Gmail, you need an App Password (not your regular password). See the Gmail App Password setup section below.

### 4. Run the application

```bash
streamlit run app.py
```

The app will be available at `http://localhost:8501`

## Gmail App Password Setup

Gmail requires a special App Password for sending email through code:

1. Enable Two-Factor Authentication at https://myaccount.google.com/security
2. Generate an App Password at https://myaccount.google.com/apppasswords
3. Enter a name like "Orientation Portal" and click Create
4. Copy the 16-character password (remove spaces) into your `.env` file as `SMTP_PASSWORD`

## Streamlit Community Cloud Deployment

This app is configured for deployment on Streamlit Community Cloud:

1. Push the repository to GitHub
2. Go to [share.streamlit.io](https://share.streamlit.io) and connect your repo
3. Set the main file path to `app.py`
4. Add secrets in the Streamlit dashboard (Settings > Secrets):

```toml
ANTHROPIC_API_KEY = "your_api_key_here"
SMTP_SERVER = "smtp.gmail.com"
SMTP_PORT = "587"
SMTP_USERNAME = "your_email@gmail.com"
SMTP_PASSWORD = "your_gmail_app_password"
DEFAULT_RECIPIENTS = "staff1@org.com,staff2@org.com"
```

The app reads from `st.secrets` when environment variables aren't available, making it compatible with both local `.env` files and Streamlit Cloud secrets.

## How It Works

### Participant Flow

1. **Registration** — Participant scans QR code or receives link, enters name and contact info
2. **Document Upload** — Uploads required documents (ID, proof of address, work authorization). AI verifies each document matches the expected type.
3. **Forms** — Completes 14 digital orientation forms with validation and conditional logic
4. **Signature** — Provides digital signature captured on-screen (applied to all forms and county documents)
5. **Submit** — Staff confirms recipient and sends. Everything is packaged into an organized zip and emailed.
6. **Session Cleared** — All data is purged from memory. Nothing persists.

Participants can navigate back and forward between steps using the arrow buttons. Data is preserved in session state throughout.

### Zero-Persistence Architecture

All participant data exists only in the browser's session state (Streamlit's `st.session_state`). Documents, forms, and signatures are held as bytes in memory — never written to disk. When the submission is sent:

1. `zip_builder.py` reads all bytes from session state and packages them in-memory using `BytesIO`
2. `pdf_filler.py` generates filled county forms with signature overlays
3. `email_sender.py` attaches the zip and sends via SMTP
4. `data_manager.py` clears the session state completely

If the browser is closed before sending, all data is lost. This is intentional — it ensures compliance with data handling requirements.

### Zip File Structure

Recipients receive an organized zip file:

```
Smith_John_abc123_20260223.zip
├── documents/
│   ├── government_id_Smith_John.pdf
│   ├── proof_of_address_Smith_John.pdf
│   └── right_to_work_Smith_John.pdf
├── forms/
│   ├── form_01_program_agreement_Smith_John.pdf
│   ├── form_02_confidentiality_Smith_John.pdf
│   └── ... (14 forms total)
├── county_forms/
│   ├── attachment_v_Smith_John.pdf
│   ├── attachment_iv_Smith_John.pdf
│   └── code_of_conduct_Smith_John.pdf
├── signature/
│   └── signature_Smith_John.png
└── Smith_John_abc123_info.txt
```

## Configuring for a New Program

This system is designed to be adaptable. To deploy for a different program:

1. Create a new JSON configuration in `program_configs/`
2. Update form definitions in `forms.py` for the new program's requirements
3. Replace PDFs in `templates/county_forms/` with your program's forms
4. Update `pdf_filler.py` field mappings and signature coordinates for new forms
5. Update `.env` with the new program's email recipients
6. Adjust document group requirements in `config.py`

The core architecture — session management, zip packaging, email delivery, AI verification — remains unchanged across programs.

## Results

- Orientation time reduced from **2-3 hours to ~30 minutes** per participant
- Document filing errors **eliminated** through automatic naming and AI verification
- Staff workload reduced by approximately **10-15 hours per week**
- **Zero data persistence** — full compliance with data handling requirements
- County forms **auto-filled** — no manual data entry for Attachment V, IV, or Code of Conduct
- Scalable to multiple concurrent participants without added confusion
- Mobile-friendly — participants can complete intake on their own devices

## Deployment Notes

- No data is stored on the server at any point during or after the intake process
- All files are processed in memory and discarded after email delivery
- Email delivery requires SMTP access (configured via `.env` or Streamlit secrets)
- AI document verification requires an Anthropic API key (optional — system works without it)
- QR code generation is the only feature that writes to disk (cached QR images in `qr_codes/`)
- County form templates must be placed in `templates/county_forms/` before deployment

## Author

Built by Brandon Olivares — workflow automation and process optimization for nonprofit and workforce development organizations.

Contact: beeoperations100@gmail.com
