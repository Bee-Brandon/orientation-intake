"""
CSS styling for the INVEST Orientation Intake app.

Provides mobile-friendly, accessible styling for the Streamlit interface.
"""


def get_app_css():
    """Return the custom CSS for the Streamlit app."""
    return """
<style>
    /* Mobile-friendly styling */
    .stApp {
        background-color: #f5f7fa !important;
    }

    /* ===========================================
       FORCE ALL TEXT TO BE DARK/VISIBLE
       (except buttons - those stay white)
       =========================================== */

    /* All text elements - force dark color */
    .stApp p, .stApp label,
    .stMarkdown, .stMarkdown p, .stMarkdown span,
    h1, h2, h3, h4, h5, h6,
    [data-testid="stMarkdownContainer"],
    [data-testid="stMarkdownContainer"] p,
    [data-testid="stMarkdownContainer"] span,
    [data-testid="stText"] {
        color: #1a1a2e !important;
    }

    /* Exclude buttons from dark text rule */
    .stButton p, .stButton span, .stButton div,
    .stDownloadButton p, .stDownloadButton span {
        color: #ffffff !important;
    }

    /* Input labels */
    .stTextInput label, .stSelectbox label, .stFileUploader label,
    .stCheckbox label, .stRadio label {
        color: #1a1a2e !important;
    }

    /* Captions and small text */
    .stCaption, small, .stCaption p {
        color: #4a5568 !important;
    }

    /* Form inputs */
    input, textarea, select {
        color: #1a1a2e !important;
        background-color: #ffffff !important;
    }

    /* Tabs */
    .stTabs [data-baseweb="tab"],
    .stTabs [data-baseweb="tab"] p {
        color: #1a1a2e !important;
    }

    /* ===========================================
       BUTTONS - White text, visible on all states
       =========================================== */

    /* Large touch-friendly buttons */
    .stButton > button {
        width: 100%;
        padding: 16px 24px !important;
        font-size: 18px !important;
        font-weight: 600 !important;
        border-radius: 12px !important;
        margin: 8px 0 !important;
        background-color: #1976d2 !important;
        color: #ffffff !important;
        border: none !important;
    }

    /* Button text - force white */
    .stButton > button p,
    .stButton > button span,
    .stButton > button div {
        color: #ffffff !important;
    }

    /* Button hover state - stays visible */
    .stButton > button:hover {
        background-color: #1565c0 !important;
        color: #ffffff !important;
        border: none !important;
    }

    .stButton > button:hover p,
    .stButton > button:hover span,
    .stButton > button:hover div {
        color: #ffffff !important;
    }

    /* Button focus/active state */
    .stButton > button:focus,
    .stButton > button:active {
        background-color: #0d47a1 !important;
        color: #ffffff !important;
        outline: none !important;
    }

    /* Primary button (type="primary") */
    .stButton > button[kind="primary"],
    .stButton > button[data-testid="baseButton-primary"] {
        background-color: #1976d2 !important;
        color: #ffffff !important;
    }

    /* Secondary button */
    .stButton > button[kind="secondary"],
    .stButton > button[data-testid="baseButton-secondary"] {
        background-color: #455a64 !important;
        color: #ffffff !important;
    }

    .stButton > button[kind="secondary"]:hover,
    .stButton > button[data-testid="baseButton-secondary"]:hover {
        background-color: #37474f !important;
        color: #ffffff !important;
    }

    /* Download button */
    .stDownloadButton > button {
        background-color: #2e7d32 !important;
        color: #ffffff !important;
    }

    .stDownloadButton > button:hover {
        background-color: #1b5e20 !important;
        color: #ffffff !important;
    }

    .stDownloadButton > button p,
    .stDownloadButton > button span {
        color: #ffffff !important;
    }

    /* Success state */
    .doc-complete {
        background: #d4edda;
        border: 2px solid #28a745;
        border-radius: 12px;
        padding: 16px;
        margin: 8px 0;
        text-align: center;
        color: #1a1a2e !important;
    }

    /* Pending state */
    .doc-pending {
        background: #fff3cd;
        border: 2px solid #ffc107;
        border-radius: 12px;
        padding: 16px;
        margin: 8px 0;
        text-align: center;
        color: #1a1a2e !important;
    }

    /* Verification warning */
    .doc-warning {
        background: #f8d7da;
        border: 2px solid #dc3545;
        border-radius: 12px;
        padding: 16px;
        margin: 8px 0;
        text-align: center;
        color: #1a1a2e !important;
    }

    /* Header styling */
    .main-header {
        background: linear-gradient(135deg, #1976d2, #1565c0);
        color: white;
        padding: 24px;
        border-radius: 16px;
        text-align: center;
        margin-bottom: 24px;
    }

    .main-header h1, .main-header p, .main-header span, .main-header small {
        color: white !important;
        margin: 0;
    }

    /* Card styling */
    .info-card {
        background: white;
        border-radius: 12px;
        padding: 20px;
        box-shadow: 0 2px 8px rgba(0,0,0,0.1);
        margin: 16px 0;
        color: #1a1a2e !important;
    }

    .info-card h3, .info-card p, .info-card span {
        color: #1a1a2e !important;
    }

    /* Progress indicator */
    .progress-bar {
        background: #e0e0e0;
        border-radius: 10px;
        height: 20px;
        overflow: hidden;
    }

    .progress-fill {
        background: linear-gradient(90deg, #4caf50, #8bc34a);
        height: 100%;
        transition: width 0.3s ease;
    }

    /* QR code container */
    .qr-container {
        background: white;
        padding: 24px;
        border-radius: 16px;
        text-align: center;
        box-shadow: 0 4px 12px rgba(0,0,0,0.15);
    }

    /* Signature section - highly visible */
    .signature-section {
        background: #e3f2fd;
        border: 3px solid #1976d2;
        border-radius: 16px;
        padding: 20px;
        margin: 24px 0;
    }

    .signature-section h3 {
        color: #1565c0 !important;
        margin-top: 0;
    }

    /* Expanders - full styling */
    [data-testid="stExpander"] {
        background-color: #ffffff !important;
        border: 1px solid #e0e0e0 !important;
        border-radius: 8px !important;
    }

    [data-testid="stExpander"] summary {
        background-color: #f5f5f5 !important;
        padding: 12px !important;
        border-radius: 8px !important;
    }

    [data-testid="stExpander"] summary span,
    [data-testid="stExpander"] summary p,
    [data-testid="stExpander"] [data-testid="stMarkdownContainer"] {
        color: #1a1a2e !important;
    }

    [data-testid="stExpander"] summary:hover {
        background-color: #e8e8e8 !important;
    }

    /* Expander content area */
    [data-testid="stExpander"] [data-testid="stVerticalBlock"] {
        background-color: #ffffff !important;
        padding: 12px !important;
    }

    /* Secondary/Cancel buttons - ensure visible text */
    .stButton > button[kind="secondary"],
    .stButton > button[data-testid="baseButton-secondary"],
    .stFormSubmitButton > button:not([kind="primary"]) {
        background-color: #6c757d !important;
        color: #ffffff !important;
        border: none !important;
    }

    .stFormSubmitButton > button:not([kind="primary"]):hover {
        background-color: #5a6268 !important;
        color: #ffffff !important;
    }

    /* Form submit buttons */
    .stFormSubmitButton > button {
        color: #ffffff !important;
    }

    .stFormSubmitButton > button[kind="primary"] {
        background-color: #1976d2 !important;
    }

    /* All form buttons text white */
    .stFormSubmitButton > button p,
    .stFormSubmitButton > button span {
        color: #ffffff !important;
    }
</style>
"""
