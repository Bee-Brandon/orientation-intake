"""
CalJOBS Entry Reference PDF Generator

Generates a clean one-page PDF summary of participant data
ordered to match the CalJOBS enrollment sequence.
Included in the submission zip for staff data entry.
"""

from io import BytesIO
from datetime import datetime

try:
    from reportlab.lib.pagesizes import letter
    from reportlab.lib.units import inch
    from reportlab.lib import colors
    from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
    from reportlab.lib.enums import TA_LEFT, TA_CENTER
    HAS_REPORTLAB = True
except ImportError:
    HAS_REPORTLAB = False


def generate_calJOBS_reference(participant: dict) -> bytes:
    """
    Generate a CalJOBS entry reference PDF from participant data.

    Ordered to match CalJOBS enrollment sequence:
    1. Basic Demographics
    2. Contact Info
    3. Selective Service
    4. Education
    5. Employment Status
    6. Special Populations / Barriers
    7. Financial / Benefits
    8. Emergency Contact

    Args:
        participant: The full participant dict from session state

    Returns:
        bytes: PDF file contents
    """
    if not HAS_REPORTLAB:
        return b""

    buf = BytesIO()
    doc = SimpleDocTemplate(
        buf,
        pagesize=letter,
        leftMargin=0.75 * inch,
        rightMargin=0.75 * inch,
        topMargin=0.6 * inch,
        bottomMargin=0.6 * inch,
    )

    styles = getSampleStyleSheet()

    # --- Custom styles ---
    title_style = ParagraphStyle(
        "Title",
        parent=styles["Heading1"],
        fontSize=13,
        textColor=colors.HexColor("#1a1a2e"),
        spaceAfter=4,
        alignment=TA_CENTER,
    )
    subtitle_style = ParagraphStyle(
        "Subtitle",
        parent=styles["Normal"],
        fontSize=8,
        textColor=colors.grey,
        spaceAfter=10,
        alignment=TA_CENTER,
    )
    section_style = ParagraphStyle(
        "Section",
        parent=styles["Heading2"],
        fontSize=9,
        textColor=colors.white,
        spaceAfter=0,
        spaceBefore=8,
        leftIndent=4,
    )
    field_label_style = ParagraphStyle(
        "FieldLabel",
        parent=styles["Normal"],
        fontSize=8,
        textColor=colors.HexColor("#555555"),
        leading=11,
    )
    field_value_style = ParagraphStyle(
        "FieldValue",
        parent=styles["Normal"],
        fontSize=9,
        textColor=colors.black,
        leading=11,
    )

    # --- Pull data ---
    # Try to get form data from the forms dict
    forms = participant.get("forms", {})
    app_data = {}
    for form_id, form_info in forms.items():
        form_data = form_info.get("data", {})
        app_data.update(form_data)

    # Also check top-level participant keys
    def get(key, fallback="—"):
        val = app_data.get(key) or participant.get(key, "")
        if val is None or str(val).strip() == "":
            return fallback
        return str(val).strip()

    # --- Helper to build a field row ---
    def row(label, value):
        return [
            Paragraph(label, field_label_style),
            Paragraph(value, field_value_style),
        ]

    # --- Section header row ---
    def section_header(title):
        header_para = Paragraph(f"  {title}", section_style)
        t = Table([[header_para]], colWidths=[7 * inch])
        t.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, -1), colors.HexColor("#1a1a2e")),
            ("TOPPADDING", (0, 0), (-1, -1), 4),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
            ("LEFTPADDING", (0, 0), (-1, -1), 6),
        ]))
        return t

    # --- Table style for field rows ---
    field_table_style = TableStyle([
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("TOPPADDING", (0, 0), (-1, -1), 3),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
        ("LEFTPADDING", (0, 0), (0, -1), 6),
        ("LINEBELOW", (0, 0), (-1, -1), 0.25, colors.HexColor("#e0e0e0")),
    ])

    def field_table(rows_data):
        t = Table(rows_data, colWidths=[2.2 * inch, 4.8 * inch])
        t.setStyle(field_table_style)
        return t

    # --- Build content ---
    content = []

    # Title
    full_name = get("full_name", get("applicant_name", "Unknown Participant"))
    content.append(Paragraph("CalJOBS ENTRY REFERENCE", title_style))
    content.append(Paragraph(
        f"Participant: {full_name}  |  Generated: {datetime.now().strftime('%m/%d/%Y %I:%M %p')}",
        subtitle_style
    ))

    # 1. Basic Demographics
    content.append(section_header("1. BASIC DEMOGRAPHICS"))
    content.append(field_table([
        row("Full Name", get("full_name", get("applicant_name"))),
        row("Date of Birth", get("dob")),
        row("Social Security #", get("ssn")),
        row("Ethnic Group", get("ethnic_group")),
        row("Gender / Selective Service",
            f"Selective Service Registered: {get('selective_service')}"),
    ]))

    # 2. Contact Information
    content.append(section_header("2. CONTACT INFORMATION"))
    content.append(field_table([
        row("Address", get("address")),
        row("City", get("city")),
        row("Zip Code", get("zip")),
        row("Phone", get("phone")),
        row("Email", get("email")),
    ]))

    # 3. Education
    content.append(section_header("3. EDUCATION"))
    content.append(field_table([
        row("Highest Education Level", get("education_level")),
    ]))

    # 4. Employment Status
    content.append(section_header("4. EMPLOYMENT STATUS"))
    content.append(field_table([
        row("Currently Working", get("currently_working")),
        row("Employer Name", get("employer_name")),
        row("Employer Address", get("employer_address")),
        row("Job Title", get("job_title")),
        row("Hourly Wage", get("hourly_wage")),
        row("Hours/Week", get("hours_worked")),
        row("Industry", get("industry")),
        row("Start Date", get("start_date")),
        row("Last Day of Work", get("last_day_of_work")),
        row("Reason Employment Ended", get("reason_employment_ended")),
        row("Receiving UI", get("receiving_ui")),
        row("UI Claim Pending", get("ui_claim_pending")),
        row("UI Exhausted", get("ui_exhausted")),
    ]))

    # 5. Special Populations / Barriers
    content.append(section_header("5. SPECIAL POPULATIONS / BARRIERS"))
    content.append(field_table([
        row("Veteran", get("is_veteran")),
        row("Veteran Separation Date", get("veteran_separation_date")),
        row("Veteran Spouse", get("veteran_spouse")),
        row("Offender", get("is_offender")),
        row("Offender Type", get("offender_type")),
        row("Currently on Parole", get("on_parole")),
        row("Homeless", get("is_homeless")),
        row("Has Children", get("has_children")),
        row("Single Parent", get("single_parent")),
    ]))

    # 6. Financial / Benefits
    content.append(section_header("6. FINANCIAL / BENEFITS"))
    content.append(field_table([
        row("Family Size", get("family_size")),
        row("Low Income", get("low_income")),
        row("Primary Wage Earner", get("primary_wage_earner")),
        row("Financial Assistance", get("financial_assistance")),
        row("Total Income (6 months)", get("total_income_6mo")),
        row("Annualized Income", get("annualized_income")),
        row("Income Source 1 (Customer)", get("income_source_1")),
        row("Income Source 2", get("income_source_2")),
        row("Income Source 3", get("income_source_3")),
        row("Income Source 4", get("income_source_4")),
    ]))

    # 7. Emergency Contact
    content.append(section_header("7. EMERGENCY CONTACT"))
    content.append(field_table([
        row("Name", get("ec_name", get("ec1_name"))),
        row("Phone", get("ec_phone", get("ec1_phone"))),
        row("Relationship", get("ec_relationship", get("ec1_relationship"))),
        row("Address", get("ec1_address")),
    ]))

    # Footer note
    content.append(Spacer(1, 0.15 * inch))
    note_style = ParagraphStyle(
        "Note", parent=styles["Normal"],
        fontSize=7, textColor=colors.grey, alignment=TA_CENTER
    )
    content.append(Paragraph(
        "This document is for internal CalJOBS data entry use only. "
        "Do not share with participants. Generated automatically by Orientation Intake System.",
        note_style
    ))

    doc.build(content)
    buf.seek(0)
    return buf.getvalue()