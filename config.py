"""
Configuration for INVEST Orientation Intake System

All hardcoded settings, paths, and constants are defined here.
Supports both local .env files and Streamlit Cloud secrets.
"""

import os
from pathlib import Path


def get_secret(key: str, default: str = "") -> str:
    """
    Get a configuration value from environment variables or Streamlit secrets.

    Priority: os.environ > st.secrets > default
    """
    # First try environment variable
    value = os.getenv(key)
    if value:
        return value

    # Fall back to Streamlit secrets (for Cloud deployment)
    try:
        import streamlit as st
        if hasattr(st, "secrets") and key in st.secrets:
            return str(st.secrets[key])
    except Exception:
        pass

    return default

# ─── Directory Paths ─────────────────────────────────────────────────────────

BASE_DIR = Path(__file__).parent
QR_CODES_DIR = BASE_DIR / "qr_codes"

# Ensure QR codes directory exists (only directory needed for no-persistence mode)
QR_CODES_DIR.mkdir(exist_ok=True)

# Legacy paths (kept for reference but not used in no-persistence mode)
SAVED_SESSIONS_DIR = BASE_DIR / "saved_sessions"
UPLOADS_DIR = SAVED_SESSIONS_DIR / "uploads"
DATA_DIR = SAVED_SESSIONS_DIR
PARTICIPANTS_FILE = DATA_DIR / "participants.json"

# ─── Cloud Deployment ────────────────────────────────────────────────────────

# Cloud deployment URL - set this to your Streamlit Cloud URL
CLOUD_URL = "https://invest2026.streamlit.app"

# ─── Document Groups ─────────────────────────────────────────────────────────
# Document categories - grouped options (pick one from each group)

DOCUMENT_GROUPS = [
    {
        "id": "identity",
        "name": "Identity Document",
        "required": True,
        "description": "Choose ONE of the following:",
        "options": [
            {"id": "ca_id", "name": "California ID"},
            {"id": "ca_drivers_license", "name": "CA Driver's License"},
        ]
    },
    {
        "id": "verification",
        "name": "Identity Verification",
        "required": True,
        "description": "Choose ONE of the following:",
        "options": [
            {"id": "ssn", "name": "Social Security Card"},
            {"id": "birth_cert", "name": "Birth Certificate"},
        ]
    },
    {
        "id": "benefits",
        "name": "Benefits Verification (If Applicable)",
        "required": False,
        "description": "Only if receiving benefits - upload verification:",
        "options": [
            {"id": "calfresh", "name": "CalFresh/SNAP"},
            {"id": "ebt", "name": "EBT Card"},
            {"id": "social_relief", "name": "General Relief/Social Relief"},
            {"id": "tanf", "name": "TANF/CalWORKs"},
            {"id": "ssi", "name": "SSI/SSDI"},
            {"id": "other_benefits", "name": "Other Benefits"},
        ]
    },
]

# ─── Legacy Document Types ───────────────────────────────────────────────────
# Legacy format for compatibility

DOCUMENT_TYPES = [
    ("identity", "Identity Document (CA ID or Driver's License)", True),
    ("verification", "Verification (SSN or Birth Certificate)", True),
    ("benefits", "Benefits Verification", False),
]

# ─── AI Document Verification Patterns ───────────────────────────────────────
# Expected document patterns for AI verification

DOCUMENT_PATTERNS = {
    "ca_id": ["california", "identification", "state id", "ca id"],
    "ca_drivers_license": ["driver", "license", "dmv", "ca dl"],
    "ssn": ["social security", "ssn", "social security administration"],
    "birth_cert": ["birth", "certificate", "vital records", "born"],
    "calfresh": ["calfresh", "snap", "food stamps", "ebt"],
    "ebt": ["ebt", "electronic benefit"],
    "social_relief": ["general relief", "social relief", "gr"],
    "tanf": ["tanf", "calworks", "temporary assistance"],
    "ssi": ["ssi", "ssdi", "supplemental security"],
}

# ─── Image Quality Requirements ──────────────────────────────────────────────
# Minimum image requirements for document uploads

MIN_WIDTH = 800  # pixels
MIN_HEIGHT = 600  # pixels
MIN_FILE_SIZE = 50 * 1024  # 50 KB


# ─── Email Configuration ─────────────────────────────────────────────────────
# SMTP settings loaded from environment variables or Streamlit secrets

class EmailConfig:
    """Email configuration from environment variables or Streamlit secrets."""

    SMTP_SERVER = get_secret("SMTP_SERVER")
    SMTP_PORT = int(get_secret("SMTP_PORT", "587"))
    SMTP_USERNAME = get_secret("SMTP_USERNAME")
    SMTP_PASSWORD = get_secret("SMTP_PASSWORD")

    @classmethod
    def is_configured(cls):
        """Check if email is properly configured."""
        return all([cls.SMTP_SERVER, cls.SMTP_USERNAME, cls.SMTP_PASSWORD])


# Default recipients - comma-separated list from environment or secrets
_recipients_str = get_secret("DEFAULT_RECIPIENTS")
DEFAULT_RECIPIENTS = [
    email.strip()
    for email in _recipients_str.split(",")
    if email.strip()
]
