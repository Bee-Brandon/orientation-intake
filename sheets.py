"""
Google Sheets Integration for WIOA Orientation Intake

Stores participant data and form responses in Google Sheets for persistence.
Data is flattened for easy reading in the spreadsheet.
"""

import json
import streamlit as st
from datetime import datetime

try:
    import gspread
    from google.oauth2.service_account import Credentials
    HAS_GSPREAD = True
except ImportError:
    HAS_GSPREAD = False

# Google Sheets configuration
SPREADSHEET_ID = "1ZKu9EWVskUHJeY-OKsZEH6W_DZsJN7d_C2uYT6DLMFo"
SCOPES = [
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/drive"
]

# Document type IDs
DOC_TYPES = ["ca_id", "ca_drivers_license", "ssn", "birth_cert", "calfresh", "ebt", "social_relief", "tanf", "ssi", "other_benefits"]

# Form IDs (14 forms)
FORM_IDS = [
    "01_center_application",
    "02_complaint_resolution",
    "03_code_of_conduct",
    "04_wioa_acknowledgement",
    "05_follow_up_info",
    "06_employment_verification",
    "07_picture_release",
    "08_client_rights",
    "09_consent_for_services",
    "10_health_disclosure",
    "11_privacy_practices",
    "12_supportive_services",
    "13_applicant_statement",
    "14_income_worksheet",
]


def get_gspread_client():
    """Get authenticated gspread client using Streamlit secrets or local file."""
    if not HAS_GSPREAD:
        return None

    try:
        # Try Streamlit secrets first (for cloud deployment)
        if hasattr(st, 'secrets') and 'gcp_service_account' in st.secrets:
            creds_dict = dict(st.secrets["gcp_service_account"])
            # Ensure private_key has proper newlines
            if 'private_key' in creds_dict:
                creds_dict['private_key'] = creds_dict['private_key'].replace('\\n', '\n')
            creds = Credentials.from_service_account_info(creds_dict, scopes=SCOPES)
        else:
            # Fall back to local file
            import os
            creds_file = os.environ.get('GOOGLE_APPLICATION_CREDENTIALS',
                         r'C:\Users\Brandon\Downloads\wioa-orientation-0a794b9d252f.json')
            if os.path.exists(creds_file):
                creds = Credentials.from_service_account_file(creds_file, scopes=SCOPES)
            else:
                return None

        client = gspread.authorize(creds)
        return client
    except Exception as e:
        # Don't show error to user, just return None to fall back to local mode
        print(f"Google Sheets connection error: {e}")
        return None


def get_spreadsheet():
    """Get the spreadsheet object."""
    client = get_gspread_client()
    if not client:
        return None

    try:
        return client.open_by_key(SPREADSHEET_ID)
    except Exception as e:
        print(f"Failed to open spreadsheet: {e}")
        return None


def init_sheets():
    """Initialize the sheets with headers if they don't exist."""
    spreadsheet = get_spreadsheet()
    if not spreadsheet:
        return False

    try:
        # ─── Participants Sheet ───────────────────────────────────────────────
        try:
            participants_sheet = spreadsheet.worksheet("Participants")
        except gspread.WorksheetNotFound:
            participants_sheet = spreadsheet.add_worksheet("Participants", 1000, 50)

        # Build header row - flattened and readable
        participant_headers = [
            # Basic Info
            'ID', 'First Name', 'Last Name', 'Full Name', 'Email', 'Phone',
            'Created At', 'Status',
            # Signature
            'Signed', 'Signature Date',
            # Documents (Yes/No for each)
            'Has CA ID', 'Has Drivers License', 'Has SSN Card', 'Has Birth Cert',
            'Has CalFresh', 'Has EBT', 'Has General Relief', 'Has TANF', 'Has SSI', 'Has Other Benefits',
            # Forms completed (Yes/No for each)
            'Form 01 - Center App', 'Form 02 - Complaint', 'Form 03 - Code of Conduct',
            'Form 04 - WIOA Ack', 'Form 05 - Follow Up', 'Form 06 - Employment Ver',
            'Form 07 - Picture Release', 'Form 08 - Client Rights', 'Form 09 - Consent',
            'Form 10 - Health', 'Form 11 - Privacy', 'Form 12 - Supportive Svc',
            'Form 13 - Applicant Statement', 'Form 14 - Income',
            # Count summaries
            'Docs Uploaded', 'Forms Completed'
        ]

        # Check if headers exist
        existing_headers = participants_sheet.row_values(1)
        if not existing_headers or existing_headers != participant_headers:
            participants_sheet.update('A1', [participant_headers])

        # ─── FormResponses Sheet ──────────────────────────────────────────────
        try:
            forms_sheet = spreadsheet.worksheet("FormResponses")
        except gspread.WorksheetNotFound:
            forms_sheet = spreadsheet.add_worksheet("FormResponses", 1000, 30)

        # Flattened form response headers - key fields expanded
        form_headers = [
            'Submitted At', 'Participant ID', 'Participant Name',
            'Form ID', 'Form Title',
            # Common fields that appear across forms (expanded for readability)
            'Full Name', 'Phone', 'DOB', 'Address', 'City', 'Zip', 'Email',
            'Currently Working', 'Is Veteran', 'Has Children', 'Single Parent',
            'Is Offender', 'Ethnic Group', 'Is Homeless', 'Education Level',
            'Emergency Contact 1', 'Emergency Contact 2',
            # Generic answer columns for other fields
            'Answer 1', 'Answer 2', 'Answer 3', 'Answer 4', 'Answer 5',
            'Answer 6', 'Answer 7', 'Answer 8', 'Answer 9', 'Answer 10',
            # Full data backup
            'All Answers (JSON)'
        ]

        existing_form_headers = forms_sheet.row_values(1)
        if not existing_form_headers or existing_form_headers != form_headers:
            forms_sheet.update('A1', [form_headers])

        return True
    except Exception as e:
        print(f"Failed to initialize sheets: {e}")
        return False


def load_participants_from_sheets():
    """Load all participants from Google Sheets."""
    try:
        spreadsheet = get_spreadsheet()
        if not spreadsheet:
            return {}
    except Exception as e:
        print(f"Error getting spreadsheet: {e}")
        return {}

    try:
        sheet = spreadsheet.worksheet("Participants")
        records = sheet.get_all_records()

        participants = {}
        for record in records:
            pid = record.get('ID')
            if not pid:
                continue

            # Reconstruct documents dict from flattened columns
            documents = {}
            doc_column_map = {
                'Has CA ID': 'ca_id',
                'Has Drivers License': 'ca_drivers_license',
                'Has SSN Card': 'ssn',
                'Has Birth Cert': 'birth_cert',
                'Has CalFresh': 'calfresh',
                'Has EBT': 'ebt',
                'Has General Relief': 'social_relief',
                'Has TANF': 'tanf',
                'Has SSI': 'ssi',
                'Has Other Benefits': 'other_benefits',
            }
            for col_name, doc_id in doc_column_map.items():
                if record.get(col_name) == 'Yes':
                    documents[doc_id] = {"uploaded": True}

            # Reconstruct forms dict from flattened columns
            forms = {}
            form_column_map = {
                'Form 01 - Center App': '01_center_application',
                'Form 02 - Complaint': '02_complaint_resolution',
                'Form 03 - Code of Conduct': '03_code_of_conduct',
                'Form 04 - WIOA Ack': '04_wioa_acknowledgement',
                'Form 05 - Follow Up': '05_follow_up_info',
                'Form 06 - Employment Ver': '06_employment_verification',
                'Form 07 - Picture Release': '07_picture_release',
                'Form 08 - Client Rights': '08_client_rights',
                'Form 09 - Consent': '09_consent_for_services',
                'Form 10 - Health': '10_health_disclosure',
                'Form 11 - Privacy': '11_privacy_practices',
                'Form 12 - Supportive Svc': '12_supportive_services',
                'Form 13 - Applicant Statement': '13_applicant_statement',
                'Form 14 - Income': '14_income_worksheet',
            }
            for col_name, form_id in form_column_map.items():
                if record.get(col_name) == 'Yes':
                    forms[form_id] = {"status": "completed"}

            # Build signature dict
            signature = None
            if record.get('Signed') == 'Yes':
                signature = {
                    'type': 'drawn',
                    'signed_at': record.get('Signature Date', '')
                }

            participants[pid] = {
                'id': pid,
                'first_name': record.get('First Name', ''),
                'last_name': record.get('Last Name', ''),
                'full_name': record.get('Full Name', ''),
                'email': record.get('Email', ''),
                'phone': record.get('Phone', ''),
                'created_at': record.get('Created At', ''),
                'status': record.get('Status', 'in_progress'),
                'signature': signature,
                'documents': documents,
                'forms': forms,
                'folder': ''  # No local folder in cloud mode
            }

        return participants
    except Exception as e:
        print(f"Failed to load participants: {e}")
        return {}


def save_participant_to_sheets(participant):
    """Save or update a participant in Google Sheets with flattened data."""
    spreadsheet = get_spreadsheet()
    if not spreadsheet:
        return False

    try:
        sheet = spreadsheet.worksheet("Participants")
        pid = participant['id']

        # Prepare flattened row data
        docs = participant.get('documents', {})
        forms = participant.get('forms', {})

        # Signature info
        signed = 'Yes' if participant.get('signature') else 'No'
        signature_date = ''
        if participant.get('signature'):
            signature_date = participant['signature'].get('signed_at', '')

        # Document columns (Yes/No)
        has_ca_id = 'Yes' if 'ca_id' in docs else 'No'
        has_drivers = 'Yes' if 'ca_drivers_license' in docs else 'No'
        has_ssn = 'Yes' if 'ssn' in docs else 'No'
        has_birth = 'Yes' if 'birth_cert' in docs else 'No'
        has_calfresh = 'Yes' if 'calfresh' in docs else 'No'
        has_ebt = 'Yes' if 'ebt' in docs else 'No'
        has_relief = 'Yes' if 'social_relief' in docs else 'No'
        has_tanf = 'Yes' if 'tanf' in docs else 'No'
        has_ssi = 'Yes' if 'ssi' in docs else 'No'
        has_other = 'Yes' if 'other_benefits' in docs else 'No'

        # Form columns (Yes/No)
        form_01 = 'Yes' if '01_center_application' in forms else 'No'
        form_02 = 'Yes' if '02_complaint_resolution' in forms else 'No'
        form_03 = 'Yes' if '03_code_of_conduct' in forms else 'No'
        form_04 = 'Yes' if '04_wioa_acknowledgement' in forms else 'No'
        form_05 = 'Yes' if '05_follow_up_info' in forms else 'No'
        form_06 = 'Yes' if '06_employment_verification' in forms else 'No'
        form_07 = 'Yes' if '07_picture_release' in forms else 'No'
        form_08 = 'Yes' if '08_client_rights' in forms else 'No'
        form_09 = 'Yes' if '09_consent_for_services' in forms else 'No'
        form_10 = 'Yes' if '10_health_disclosure' in forms else 'No'
        form_11 = 'Yes' if '11_privacy_practices' in forms else 'No'
        form_12 = 'Yes' if '12_supportive_services' in forms else 'No'
        form_13 = 'Yes' if '13_applicant_statement' in forms else 'No'
        form_14 = 'Yes' if '14_income_worksheet' in forms else 'No'

        # Summary counts
        docs_count = len(docs)
        forms_count = len(forms)

        row_data = [
            # Basic Info
            pid,
            participant.get('first_name', ''),
            participant.get('last_name', ''),
            participant.get('full_name', ''),
            participant.get('email', ''),
            participant.get('phone', ''),
            participant.get('created_at', ''),
            participant.get('status', 'in_progress'),
            # Signature
            signed,
            signature_date,
            # Documents
            has_ca_id, has_drivers, has_ssn, has_birth,
            has_calfresh, has_ebt, has_relief, has_tanf, has_ssi, has_other,
            # Forms
            form_01, form_02, form_03, form_04, form_05, form_06, form_07,
            form_08, form_09, form_10, form_11, form_12, form_13, form_14,
            # Counts
            docs_count, forms_count
        ]

        # Check if participant exists
        try:
            cell = sheet.find(pid, in_column=1)
            # Update existing row
            end_col = chr(ord('A') + len(row_data) - 1)
            sheet.update(f'A{cell.row}:{end_col}{cell.row}', [row_data])
        except gspread.CellNotFound:
            # Append new row
            sheet.append_row(row_data)

        return True
    except Exception as e:
        print(f"Failed to save participant: {e}")
        return False


def save_form_response_to_sheets(participant_id, participant_name, form_id, form_title, form_data):
    """Save a form response with flattened fields for readability."""
    spreadsheet = get_spreadsheet()
    if not spreadsheet:
        return False

    try:
        sheet = spreadsheet.worksheet("FormResponses")

        # Extract common fields if present
        full_name = form_data.get('full_name', '')
        phone = form_data.get('phone', '')
        dob = form_data.get('dob', '')
        address = form_data.get('address', '')
        city = form_data.get('city', '')
        zip_code = form_data.get('zip', '')
        email = form_data.get('email', '')
        currently_working = form_data.get('currently_working', '')
        is_veteran = form_data.get('is_veteran', '')
        has_children = form_data.get('has_children', '')
        single_parent = form_data.get('single_parent', '')
        is_offender = form_data.get('is_offender', '')
        ethnic_group = form_data.get('ethnic_group', '')
        is_homeless = form_data.get('is_homeless', '')
        education_level = form_data.get('education_level', '')

        # Emergency contacts
        ec1 = form_data.get('ec_name', '') or form_data.get('emergency_contact_1', '')
        ec2 = form_data.get('emergency_contact_2', '')

        # Get remaining fields as generic answers
        common_fields = {'full_name', 'phone', 'dob', 'address', 'city', 'zip', 'email',
                        'currently_working', 'is_veteran', 'has_children', 'single_parent',
                        'is_offender', 'ethnic_group', 'is_homeless', 'education_level',
                        'ec_name', 'emergency_contact_1', 'emergency_contact_2',
                        'signature_confirmed'}

        other_answers = []
        for key, value in form_data.items():
            if key not in common_fields and value:
                # Format as "Field: Value" for readability
                if isinstance(value, list):
                    value = ', '.join(str(v) for v in value)
                other_answers.append(f"{key}: {value}")

        # Pad to 10 answer slots
        while len(other_answers) < 10:
            other_answers.append('')

        row_data = [
            datetime.now().strftime('%Y-%m-%d %H:%M'),
            participant_id,
            participant_name,
            form_id,
            form_title,
            # Common fields
            full_name, phone, dob, address, city, zip_code, email,
            currently_working, is_veteran, has_children, single_parent,
            is_offender, ethnic_group, is_homeless, education_level,
            ec1, ec2,
            # Other answers (up to 10)
            other_answers[0], other_answers[1], other_answers[2], other_answers[3], other_answers[4],
            other_answers[5], other_answers[6], other_answers[7], other_answers[8], other_answers[9],
            # Full JSON backup
            json.dumps(form_data)
        ]

        # Always append (keep history of all submissions)
        sheet.append_row(row_data)
        return True
    except Exception as e:
        print(f"Failed to save form response: {e}")
        return False


def delete_participant_from_sheets(participant_id):
    """Delete a participant from Google Sheets."""
    spreadsheet = get_spreadsheet()
    if not spreadsheet:
        return False

    try:
        sheet = spreadsheet.worksheet("Participants")
        cell = sheet.find(participant_id, in_column=1)
        if cell:
            sheet.delete_rows(cell.row)
        return True
    except gspread.CellNotFound:
        return True  # Already doesn't exist
    except Exception as e:
        print(f"Failed to delete participant: {e}")
        return False


def get_participant_from_sheets(participant_id):
    """Get a single participant by ID."""
    participants = load_participants_from_sheets()
    return participants.get(participant_id)
