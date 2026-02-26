"""
WIOA Orientation Forms Module

Digital versions of the 14 paper orientation forms.
Generates PDFs matching original paper format.
"""

from datetime import datetime, date
from dataclasses import dataclass, field
from typing import Any
import io
import json
from pathlib import Path

# PDF generation
try:
    from reportlab.lib.pagesizes import letter
    from reportlab.lib.units import inch
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
    from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_JUSTIFY, TA_RIGHT
    from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, Image as RLImage, PageBreak
    from reportlab.lib import colors
    from reportlab.pdfgen import canvas
    HAS_REPORTLAB = True
except ImportError:
    HAS_REPORTLAB = False


# ─── Form Definitions ────────────────────────────────────────────────────────
# Exact replicas of the 14 paper orientation forms

ORIENTATION_FORMS = {
    "01_center_application": {
        "title": "Center Application",
        "org": "America's Job Center of California - East LA/West San Gabriel Valley",
        "pages": 1,
        "category": "complex",
        "description": "AJCC main intake application with personal information, employment status, and emergency contacts",
        "sections": [
            {
                "name": "personal_info",
                "title": "",
                "layout": "grid",
                "fields": [
                    {"id": "full_name", "label": "Full Name", "type": "text", "required": True},
                    {"id": "phone", "label": "Phone#", "type": "phone", "required": True},
                    {"id": "dob", "label": "Date of Birth", "type": "date", "format": "mm/dd/yyyy", "required": True},
                    {"id": "ssn", "label": "Social Security #", "type": "ssn", "format": "XXX-XX-", "required": True},
                    {"id": "address", "label": "Address", "type": "text", "required": True},
                    {"id": "city", "label": "City", "type": "text", "required": True},
                    {"id": "zip", "label": "Zip", "type": "text", "required": True},
                    {"id": "email", "label": "Email", "type": "email"},
                ]
            },
            {
                "name": "section_1",
                "title": "Section 1",
                "fields": [
                    {"id": "currently_working", "label": "ARE YOU CURRENTLY WORKING?", "type": "radio",
                     "options": ["NO", "YES, PART TIME", "YES, FULL TIME"]},
                    {"id": "is_veteran", "label": "ARE YOU A VETERAN?", "type": "radio",
                     "options": ["NO", "YES, HONORABLE DISCHARGE"]},
                    {"id": "veteran_separation_date", "label": "Separation Date", "type": "date",
                     "show_if": {"field": "is_veteran", "value": "YES, HONORABLE DISCHARGE"}},
                    {"id": "veteran_spouse", "label": "Are you a Veteran Spouse?", "type": "radio", "options": ["No", "Yes"]},
                    {"id": "has_children", "label": "Do you have any children?", "type": "radio", "options": ["No", "Yes"]},
                    {"id": "single_parent", "label": "Are you a Single Parent?", "type": "radio", "options": ["No", "Yes"]},
                    {"id": "is_offender", "label": "Are you an offender?", "type": "radio", "options": ["No", "Yes"]},
                    {"id": "offender_type", "label": "Please indicate", "type": "radio",
                     "options": ["Felony", "Non-Felony"], "show_if": {"field": "is_offender", "value": "Yes"}},
                    {"id": "on_parole", "label": "Are you currently on Parole?", "type": "radio", "options": ["No", "Yes"],
                     "show_if": {"field": "is_offender", "value": "Yes"}},
                    {"id": "financial_assistance", "label": "Are you currently receiving any of the following financial assistance?",
                     "type": "multiselect", "options": ["Cal Works/TANF (Cash Aid)", "Food Stamps", "SSI (Supplemental Security Insurance)",
                                                         "GR (General Relief)", "Refugee Cash"]},
                    {"id": "ethnic_group", "label": "ETHNIC GROUP", "type": "radio",
                     "options": ["WHITE", "HISPANIC", "BLACK", "AMERICAN INDIAN", "ASIAN/PACIFIC ISLANDER"]},
                    {"id": "selective_service", "label": "SELECTIVE SERVICE (ONLY FOR MALES 18 YRS. OR OLDER)", "type": "checkbox"},
                    {"id": "is_homeless", "label": "ARE YOU HOMELESS?", "type": "radio", "options": ["No", "Yes"]},
                    {"id": "education_level", "label": "Highest Educational Level Completed", "type": "text"},
                    {"id": "family_size", "label": "Family Size", "type": "number"},
                ]
            },
            {
                "name": "emergency_contacts",
                "title": "Alternate/Emergency Contacts",
                "repeatable": True,
                "max_items": 3,
                "fields": [
                    {"id": "ec_name", "label": "Name", "type": "text"},
                    {"id": "ec_phone", "label": "Phone#", "type": "phone"},
                    {"id": "ec_relationship", "label": "Relationship", "type": "text"},
                ]
            },
            {
                "name": "section_2",
                "title": "Section 2 - EMPLOYMENT INFORMATION",
                "fields": [
                    {"id": "receiving_ui", "label": "Are you currently receiving Unemployment Insurance (UI)?",
                     "type": "radio", "options": ["No", "Yes"]},
                    {"id": "ui_claim_pending", "label": "Is your Unemployment Insurance (UI) claim pending?",
                     "type": "radio", "options": ["No", "Yes"]},
                    {"id": "ui_exhausted", "label": "Have you exhausted your Unemployment Insurance (UI)?",
                     "type": "radio", "options": ["No", "Yes"]},
                    {"id": "self_employed_now_unemployed", "label": "Were you self-employed but are now unemployed due to economic conditions?",
                     "type": "radio", "options": ["No", "Yes"]},
                    {"id": "business_closed", "label": "Are you no longer working because the business closed, relocated or downsized?",
                     "type": "radio", "options": ["No", "Yes"]},
                ]
            },
            {
                "name": "section_3",
                "title": "Section 3 - Last Employer Information",
                "fields": [
                    {"id": "employer_name", "label": "Employer Name", "type": "text"},
                    {"id": "employer_address", "label": "Employer Full Address", "type": "text"},
                    {"id": "employer_phone", "label": "Employer Phone #", "type": "phone"},
                    {"id": "job_title", "label": "Job Title", "type": "text"},
                    {"id": "hourly_wage", "label": "Hourly Wage", "type": "currency"},
                    {"id": "hours_worked", "label": "Hours Worked", "type": "number"},
                    {"id": "industry", "label": "Industry", "type": "text"},
                    {"id": "start_date", "label": "Start Date", "type": "date", "format": "MM/DD/YY"},
                    {"id": "last_day_of_work", "label": "Last Day of Work", "type": "date"},
                    {"id": "reason_employment_ended", "label": "Reason employment Ended", "type": "text"},
                ]
            },
        ],
        "certification_text": """Your Social Security Number and personal information will be kept strictly confidential. With your consent, this information may be shared within the Americas Job Center Partnership to determine eligibility for additional services. I certify that this information is true to the best of my knowledge. I am aware that the information provided is subject to review and verification and I may have to provide documents to support this application. I am aware that I am subject to immediate termination if I am found ineligible after enrollment and may be prosecuted for fraud and/or perjury. I allow the release of this information for verification purposes and understand that it will be used to determine eligibility. Disclosure of your social security number is voluntary but necessary for your enrollment.""",
        "signature_required": True,
        "footer": "East Los Angeles/West San Gabriel Valley America's Job Center of California AJCC ~5301 Whittier Blvd. 2nd Floor, Los Angeles, CA 90022~\nTel: (323) 887-7122 TTY: (323) 832-1278",
    },

    "02_complaint_resolution": {
        "title": "WIOA Complaint and Resolution Policies and Procedures - Participant Acceptance Form",
        "org": "East Los Angeles West San Gabriel Valley AJCC",
        "pages": 4,
        "category": "simple",
        "description": "WIOA grievance procedures, Equal Opportunity law, and complaint filing instructions",
        "policy_text": """EQUAL OPPORTUNITY IS THE LAW

It is against the law for this recipient of federal financial assistance to discriminate on the following basis:

Against any individual in the United States, because of race; color; religion; sex (including pregnancy, childbirth, and related medical conditions, sex stereotyping, transgender status, and gender identity); national origin (including limited English proficiency); age; disability, political affiliation, or belief; and

Against any beneficiary of, applicant to, or participant in, programs financially assisted under Title I of the Workforce Innovation and Opportunity Act (WIOA), because of the individual's citizenship status or participation in any WIOA Title I financially assisted program or activity.

The recipient must not discriminate in any of the following areas:
- Deciding who will be admitted, or have access, to any WIOA Title I financially assisted program or activity;
- Providing opportunities in, or treating any person regarding, such a program or activity; or
- Making employment decisions in the administration of, or in connection with, such a program or activity.

Recipients of federal financial assistance must take reasonable steps to ensure that communications with individuals with disabilities are as effective as communications with others.

WHAT TO DO IF YOU BELIEVE YOU HAVE EXPERIENCED DISCRIMINATION

If you think that you have been subjected to discrimination under a WIOA Title I financially assisted program or activity, you may file a complaint within one hundred eighty (180) days from the date of the alleged violation with either:

County of Los Angeles Department of Economic Opportunity
510 S. Vermont Avenue, Los Angeles, CA 90020-1708
Attn: Latrice Mcknight
compliance@opportunity.lacounty.gov
(213) 418-7120

OR

Civil Rights Center (CRC)
U.S. Department of Labor
200 Constitution Avenue, N.W., Room N4123
Washington, D.C. 20210
Or electronically as directed on the CRC website at www.dol.gov/crc""",
        "sections": [
            {
                "name": "staff_info",
                "title": "Staff Information",
                "fields": [
                    {"id": "staff_name", "label": "Staff Name", "type": "text", "default": "Judy Manzanarez"},
                ]
            },
        ],
        "acknowledgment_text": "I hereby acknowledge receipt of a signed copy of the Local Workforce Innovation and Opportunity Act Complaint and Resolutions Policies and Procedures Participant Acceptance Form and a copy of the County of Los Angeles Workforce Innovation and Opportunity Act Complaint and Resolution Policies and Procedures. My signature below certifies that I have read and understand the procedures and will comply with the policies in the Workforce Innovation and Opportunity Act (WIOA) funded Program.",
        "signature_required": True,
        "parent_guardian_signature": True,
        "staff_signature_required": True,
        "revision": "Rev. 06/2024",
    },

    "03_code_of_conduct": {
        "title": "Code of Conduct",
        "org": "America's Job Center of California - East Los Angeles/West San Gabriel AJCC",
        "pages": 1,
        "category": "simple",
        "description": "AJCC center behavioral expectations and guidelines",
        "policy_text": """Welcome. You've taken an important step toward reaching your employment and career goals just by being here! While you are here, you can expect a safe and accessible environment. Please ask a staff member if you need reasonable accommodations to access services or need other assistance.

To ensure your experience here is a positive one, please adhere to the guidelines below. If you have any questions about these items, please ask staff to explain the code of conduct. Thank you for your cooperation.

Disruptive behavior or failure to comply with any of the following procedures may result in you being asked to leave:

1. Each time you visit, sign in at the Reception Desk

2. Behavior in Center:
   You are expected to behave in a professional manner and treat other clients and staff respectfully. Please be patient while waiting to be assisted and keep all conversation to a low volume.
   Cell phone usage: To limit distractions to other clients, cell phones use is prohibited in the Resource center area. Please put your cells phones on vibrate and take your phone calls in the hallway.
   Visitors are not permitted to charge equipment on any of the Resource Center outlets.
   Food and beverages are not allowed in the Resource Center.

3. Violence and/or threats of violence will result in immediate expulsion from the center.
   Possession of any type of weapon, violence, and/or threats of violence, including "mock" threats, will not be tolerated. Anyone in violation of this policy will be banned from the center indefinitely.

4. Harassment, vulgar, lewd or indecent behavior will not be tolerated.
   Abusive language toward staff or client is strictly prohibited. Harassment on the basis of race, color, religion, national origin, age, gender, veteran status, marital status, sexual orientation, disability or medical condition is strictly prohibited and will not be tolerated. Anyone in violation of this policy will be asked to leave the Center immediately and will not be allowed to return in the future.

5. Theft, destruction, or removal of center property will be reported to the proper authorities.

6. No smoking, alcohol or illegal drugs are allowed in the center. Clients should not be under the influence of drugs or alcohol while utilizing the center.

7. Bathrooms are located outside by the elevators. No sleeping, bathing, shaving, or excessive grooming on the premises. *If you need assistance with emergency shelter/housing/etc., please ask center staff.

8. Children are the responsibility of the parent and/or caretaker, and are expected to refrain from running or making loud noises while in the center.""",
        "sections": [],
        "signature_required": True,
    },

    "04_wioa_acknowledgement": {
        "title": "WIOA Applicant Acknowledgement Statements",
        "org": "County of Los Angeles - Workforce Innovation & Opportunity Act",
        "pages": 1,
        "category": "medium",
        "description": "SSN use, confidentiality, fraud protection, and nepotism acknowledgements",
        "acknowledgments": [
            {
                "title": "USE OF SOCIAL SECURITY ACCOUNT NUMBER",
                "text": "I understand that the number will be used by County of Los Angeles AJCCs, AJCC staff and its agents, the U.S. Department of Labor and its grantees or contractors for payroll and management information tracking purposes, as well as to assist in determining and confirming my eligibility for WIOA funded services."
            },
            {
                "title": "APPLICATION INFORMATION CONFIDENTIAL & SUBJECT TO REVIEW",
                "text": "I am aware that the information being collected on this form will be stored in a secured computer system and that all information is confidential. I allow the use and release of the information I have provided to those agencies serving me and I am aware that the information is subject to review and verification. I am aware that I may have to provide documents to support this application or sign form(s) which will allow other agencies to provide this information to the County of Los Angeles."
            },
            {
                "title": "PROTECTION AGAINST FRAUD",
                "text": "I further understand that either falsification of the information provided by me on the WIOA Application or a finding during the Verification and Certification Process of my eligibility for WIOA funded services shall be grounds for my termination from any program in which I may participate, and that I may be subject to actions for the collection of any monies received by me or prosecution under the law."
            },
            {
                "title": "APPLICANT RIGHT TO REVIEW FILE",
                "text": "I further understand that, upon my written request, all information provided by me or collected by the County of Los Angeles or its agents or contractors through the next five years pertaining to my application or eligibility for, or participation in, WIOA funded programs sponsored by the County of Los Angeles will be made available to me for review."
            },
            {
                "title": "NEPOTISM PROVISION",
                "text": "I have been informed that I cannot be hired in, or accept, a public service employment position, funded by WIOA, if a member of my immediate family is engaged in an administrative capacity for a County of Los Angeles WIOA funded program."
            },
        ],
        "sections": [
            {
                "name": "civil_rights",
                "title": "CIVIL RIGHTS AND COMPLAINTS SUMMARY FORM",
                "fields": [
                    {"id": "civil_rights_ack", "label": "I hereby acknowledge receipt of a civil rights and complaints summary form.", "type": "checkbox", "required": True},
                ]
            },
            {
                "name": "emergency_contact",
                "title": "EMERGENCY CONTACT INFORMATION",
                "fields": [
                    {"id": "contact_name", "label": "Name", "type": "text", "required": True},
                    {"id": "contact_street", "label": "Street", "type": "text"},
                    {"id": "contact_city", "label": "City", "type": "text"},
                    {"id": "contact_zip", "label": "Zip", "type": "text"},
                    {"id": "contact_phone", "label": "Phone", "type": "phone", "required": True},
                ]
            },
        ],
        "signature_required": True,
        "revision": "Rev. 06/2024",
    },

    "05_follow_up_info": {
        "title": "Follow-up Information",
        "org": "LA County America's Job Center of California",
        "pages": 1,
        "category": "medium",
        "description": "Personal contact information for follow-up services with emergency contacts",
        "intro_text": """I understand there are times when it is important for my career coach to be able to reach me. These situations may include notification of job opening, change of appointment times, notice of service availability, or other reasons related to the overall administration of my employment plan. The following persons are provided as alternate contacts for me in event I am not able to be reached at the primary phone and address. I am responsible for updating my person contact information and notifying my assigned Career Coach if my address or phone number changes:""",
        "sections": [
            {
                "name": "personal_contact",
                "title": "PLEASE PRINT YOUR OWN:",
                "fields": [
                    {"id": "full_name", "label": "NAME", "type": "text", "required": True},
                    {"id": "address", "label": "ADDRESS", "type": "text"},
                    {"id": "city_state_zip", "label": "CITY/STATE/ZIP CODE", "type": "text"},
                    {"id": "phone", "label": "TELEPHONE", "type": "phone", "required": True},
                    {"id": "email", "label": "EMAIL", "type": "email"},
                ]
            },
            {
                "name": "emergency_contact_1",
                "title": "PLEASE PRINT the name, address and telephone number of your contact person who will always know how to get ahold of you in case you move. (2- Emergency Contact)",
                "fields": [
                    {"id": "ec1_name", "label": "NAME", "type": "text"},
                    {"id": "ec1_address", "label": "ADDRESS", "type": "text"},
                    {"id": "ec1_city_state_zip", "label": "CITY/STATE/ZIP CODE", "type": "text"},
                    {"id": "ec1_phone", "label": "TELEPHONE", "type": "phone"},
                    {"id": "ec1_relationship", "label": "RELATIONSHIP", "type": "text"},
                ]
            },
            {
                "name": "emergency_contact_2",
                "title": "",
                "fields": [
                    {"id": "ec2_name", "label": "NAME", "type": "text"},
                    {"id": "ec2_address", "label": "ADDRESS", "type": "text"},
                    {"id": "ec2_city_state_zip", "label": "CITY/STATE/ZIP CODE", "type": "text"},
                    {"id": "ec2_phone", "label": "TELEPHONE", "type": "phone"},
                    {"id": "ec2_relationship", "label": "RELATIONSHIP", "type": "text"},
                ]
            },
        ],
        "signature_required": False,
        "revision": "Rev. May 12, 2020",
    },

    "06_employment_verification": {
        "title": "Employment Verification",
        "org": "LA County America's Job Center of California - East Los Angeles/West San Gabriel Valley",
        "pages": 1,
        "category": "medium",
        "description": "Release information and employment verification waiver for WIOA participation",
        "locations": [
            "East Los Angeles/West San Gabriel Valley - 5301 Whittier Blvd, 2nd Floor, Los Angeles, CA 90022 - PH:323-887-7122 FAX:323-887-8236",
            "Affiliate ALHAMBRA - 2550 Main Street, Suite 103, Alhambra, CA 91801 - PH: 626-677-2600 FAX: 626-284-9951",
            "EAST LOS ANGELES COMMUNITY COLLEGE SPECIALIZED - 1301 Avenida Cesar Chavez, #K7, Los Angeles, CA 91801 - PH: 323-780-6700 FAX: 323-832-8236",
        ],
        "authorization_text": "I, ___, AUTHORIZE THE AMERICA'S JOB CENTER OF CALIFORNIA (AJCC) CENTERS TO COLLECT EMPLOYMENT INFORMATION WHICH MY BE NECESSARY FOR MY PARTICIPATION IN THE WIOA PROGRAM.",
        "employer_auth_text": """EMPLOYER AUTHORIZATION TO RELEASE THE FOLLOWING INFORMATION:

EMPLOYEE'S NAME, SOCIAL SECURITY NUMBER, HIRE DATE, TERMINATION DATE, LAYOFF NOTICE, JOB TITLE, HOURS PER WEEK, LAST HOURLY WAGE, If currently EMPLOYED (YES) / (NO)

By my signature below, I authorize release of the following information to AJCC Centers:""",
        "sections": [
            {
                "name": "employer_info",
                "title": "Employment Verification for:",
                "fields": [
                    {"id": "attention", "label": "ATTENTION", "type": "text"},
                    {"id": "business_name", "label": "BUSINESS NAME", "type": "text"},
                    {"id": "employee_name", "label": "EMPLOYEE NAME", "type": "text", "required": True},
                    {"id": "employee_ssn_last4", "label": "EMPLOYEE SS#(last 4#)", "type": "text"},
                    {"id": "date_of_hire", "label": "Date of Hire", "type": "date"},
                    {"id": "first_day_of_work", "label": "First day of work", "type": "date"},
                    {"id": "position_title", "label": "Position Title", "type": "text"},
                    {"id": "hours_per_week", "label": "Hours worked Per week", "type": "number"},
                    {"id": "starting_salary", "label": "Starting Salary $", "type": "currency"},
                    {"id": "current_salary", "label": "Current Salary $", "type": "currency"},
                    {"id": "has_benefits", "label": "Benefits", "type": "radio", "options": ["YES", "NO"]},
                    {"id": "last_day_of_work", "label": "If no longer employed, last day of work (Date)", "type": "date"},
                    {"id": "reason_for_leaving", "label": "Reason for leaving", "type": "text"},
                    {"id": "employer_name", "label": "Employer's Name", "type": "text"},
                    {"id": "employer_address", "label": "Employer's Address", "type": "text"},
                    {"id": "employer_rep_name", "label": "Employer Representative completing this form (print)", "type": "text"},
                ]
            },
        ],
        "signature_required": True,
        "employer_signature": True,
        "agency_signature": True,
        "revision": "Rev.May 12,2020",
    },

    "07_picture_release": {
        "title": "Picture & Information Release Form",
        "org": "Catholic Charities of Los Angeles, Inc.",
        "address": "1531 James M. Wood Blvd., Los Angeles, CA 90015",
        "pages": 1,
        "category": "simple",
        "description": "Photo and information release consent for Catholic Charities",
        "policy_text": """I, ___ (Please PRINT your name)
give free consent to Catholic Charities of Los Angeles, Inc. ("the Agency") for the Agency to:

1. take pictures (photographs, video and/or film) of myself or my family, if one or more family member(s) is/are under 18 years of age, and/or

2. use information about the experiences of myself or my family, if one or more family member(s) is/are under 18 years of age,

to be used, without the use of my or my family's real name(s), for informational purposes by the Agency, to be published in newspapers, brochures, displayed on posters, in television, slide or Powerpoint presentations and/or any other multi-media format presentation, on the Agency's website, in appeal literature, or other related fundraising or public relations material that promotes the Agency's work, staff, and services.

- I waive all claims for any compensation for use or for damages.
- I understand that these pictures and/or this information may be used beyond the year in which they are taken.
- This agreement may be cancelled at any time by notifying Catholic Charities in writing that I no longer approve of the future use of my or my family's photograph(s) or information.""",
        "sections": [
            {
                "name": "participant_info",
                "title": "",
                "fields": [
                    {"id": "participant_name", "label": "Name (Please PRINT)", "type": "text", "required": True},
                    {"id": "address_full", "label": "Address, City, State, Zip Code", "type": "text"},
                    {"id": "phone", "label": "Phone Number (daytime, if possible)", "type": "phone"},
                ]
            },
            {
                "name": "picture_identification",
                "title": "For Picture/Information Identification:",
                "fields": [
                    {"id": "shoot_location", "label": "Location of \"Shoot\" or Interview", "type": "text"},
                    {"id": "description", "label": "Description of Subject", "type": "text"},
                    {"id": "photographer", "label": "Photographer, if applicable", "type": "text"},
                    {"id": "interviewer", "label": "Interviewer, if applicable", "type": "text"},
                ]
            },
        ],
        "signature_required": True,
        "signature_label": "Signature (Parent or Guardian Must sign for Minor, under 18 years of age)",
    },

    "08_client_rights": {
        "title": "Client Rights and Responsibilities",
        "org": "Catholic Charities of Los Angeles, Inc.",
        "pages": 1,
        "category": "simple",
        "description": "Client rights and responsibilities acknowledgement for Catholic Charities services",
        "intro_text": "Each person applying for or receiving services from Catholic Charities shall have rights and responsibilities that include, but are not limited to, the following:",
        "client_rights": [
            "To be treated with dignity and respect",
            "To receive services free from any form of discrimination",
            "To receive services in a safe and comfortable setting",
            "To be fully informed about services and any cost involved",
            "To have personal information protected by confidentiality",
            "To understand the limitations and exceptions to confidentiality",
            "To fully participate in any service planning process",
            "To receive information about how to file a complaint",
            "To evaluate and comment upon any service received",
        ],
        "client_responsibilities": [
            "To ask questions about services",
            "To provide necessary information about what is needed",
            "To recommend ways to improve the quality of service",
            "To treat agency staff and others with dignity and respect",
        ],
        "complaint_text": "How to File a Complaint: I acknowledge that I received a copy and understand the rights and responsibilities of clients as specified above. I also understand that I have the right to file a complaint according to the guidelines set forth by Catholic Charities of Los Angeles if I am unsatisfied with any service rendered or I believe that the agency has failed to comply with my rights, as described above. To initiate the complaint process, simply contact a case manager or other program representative and request a complaint form.",
        "sections": [],
        "signature_required": True,
        "signature_label": "Parent/Guardian Signature",
    },

    "09_consent_for_services": {
        "title": "Consent for Services",
        "org": "Catholic Charities of Los Angeles, Inc.",
        "pages": 1,
        "category": "simple",
        "description": "Consent to receive WIOA services from Catholic Charities",
        "intro_text": "Welcome to Catholic Charities of Los Angeles, Inc.\n\nThis Consent for Services form is designed to provide the client information about giving consent prior to receiving services and having the right to:",
        "rights_list": [
            "Participate in all service decisions;",
            "Be informed of the benefits, risks, side effects, and alternatives to planned services.",
            "Be offered the most appropriate and least restrictive or intrusive service alternative to meet my needs.",
            "Receive service in a manner that is free from harassment or coercion and that protects the person's right to self-determination.",
            "Refuse any service, treatment or medication, unless mandated by law or court order.",
            "Be informed about the consequences of such refusal, which can include discharge.",
        ],
        "sections": [
            {
                "name": "client_info",
                "title": "",
                "fields": [
                    {"id": "client_name", "label": "Client Name", "type": "text", "required": True},
                ]
            }
        ],
        "acknowledgment_text": "I have read the above statement or have had it read and explained to me in a language which I understand.",
        "signature_required": True,
        "signature_label": "Client Signature",
    },

    "10_health_disclosure": {
        "title": "Authorization to Disclose Confidential or Protected Health Information to Others",
        "org": "Catholic Charities of Los Angeles, Inc.",
        "pages": 1,
        "category": "medium",
        "description": "HIPAA-compliant authorization to release confidential health information",
        "sections": [
            {
                "name": "section_a",
                "title": "A. Name of the Person whose confidential or protected health information will be released:",
                "fields": [
                    {"id": "person_name", "label": "Name of Person", "type": "text", "required": True},
                    {"id": "program_name", "label": "Name of Program", "type": "text"},
                ]
            },
            {
                "name": "section_c",
                "title": "C. Description of the information to be disclosed:",
                "fields": [
                    {"id": "info_description", "label": "The specific information to be disclosed is described below", "type": "textarea", "rows": 3},
                ]
            },
            {
                "name": "section_d",
                "title": "D. Purpose of each disclosure:",
                "fields": [
                    {"id": "purpose", "label": "The specific purpose(s) for which the information is to be used is/are described below", "type": "textarea", "rows": 3},
                ]
            },
            {
                "name": "section_ef",
                "title": "",
                "fields": [
                    {"id": "effective_date", "label": "E. Date release will takes effect", "type": "date"},
                    {"id": "expiration_date", "label": "F. Date release expires", "type": "date"},
                ]
            },
            {
                "name": "section_g",
                "title": "G. Name of person(s) or organization(s) that will receive the disclosed information:",
                "fields": [
                    {"id": "recipient_name", "label": "Name of Person or Name of Organization", "type": "text"},
                ]
            },
            {
                "name": "section_h",
                "title": "H. Name of person or organization that is disclosing the confidential information:",
                "fields": [
                    {"id": "disclosing_org", "label": "Name of Person or Name of Organization", "type": "text"},
                ]
            },
        ],
        "revocation_text": "I. The person authorizing the disclosure of his/her confidential or protected health information may revoke this authorization in writing at any time by notifying Catholic Charities Los Angeles, Inc., and by signing and dating the Authorization Revoked line below. Such revocation becomes effective only after it is received and processed and it does not apply to any prior disclosure that Catholic Charities of Los Angeles, Inc., has made in reliance upon the authorization. Please Note: The information being disclosed above in compliance with this authorization may no longer be protected from further disclosure by the person receiving the confidential or protected health information, if that person is not subject to federal, state or other privacy laws or privacy policies that afford protection to the person authorizing disclosure. The person authorizing this disclosure or their parent/guardian/representative is entitled to receive a copy of this authorization.",
        "signature_required": True,
        "signature_label": "Signature of Person Authorizing Disclosure",
        "parent_guardian_signature": True,
        "representative_field": True,
    },

    "11_privacy_practices": {
        "title": "Notice of Privacy Practices",
        "org": "Catholic Charities of Los Angeles, Inc.",
        "subtitle": "(FOR PERSONS SERVED)",
        "effective_date": "April 14, 2004",
        "pages": 5,
        "category": "simple",
        "description": "HIPAA Notice of Privacy Practices acknowledgement",
        "header_text": "THIS NOTICE DESCRIBES HOW HEALTH INFORMATION ABOUT YOU MAY BE USED AND DISCLOSED AND HOW YOU CAN GAIN ACCESS TO THIS INFORMATION. PLEASE REVIEW IT CAREFULLY.",
        "policy_summary": """This Notice defines the privacy practices of Catholic Charities of Los Angeles for the individuals and families that it serves and it describes how this agency may use and disclose your protected health information ("PHI") to carry out treatment, payment, and/or health care operations, and for other purposes as permitted or required by law.

Catholic Charities of Los Angeles understands that your health information and that of any of your dependents is personal, and it is committed to protecting this information. In addition, Catholic Charities of Los Angeles is required under the Health Insurance Portability & Accountability Act of 1996 (HIPAA) to maintain the privacy of your protected health information ("PHI").

Catholic Charities of Los Angeles is required by law to make sure that your health information is kept private, when obtained, and to give you notice of our legal duties and privacy practices.

For questions about this Notice, please contact our Privacy Officer:
Attn: Privacy Office of Catholic Charities of Los Angeles, Inc.
Address: 1531 James M. Wood Blvd., Los Angeles, CA 90015
Telephone: (213) 251-3416
Email Address: Lratleff@ccharities.org""",
        "sections": [],
        "acknowledgment_text": "I acknowledge receipt of the Notice of Privacy Practices of Catholic Charities of Los Angeles, Inc.",
        "signature_required": True,
        "signature_label": "Signature (Client/Parent/Guardian/Conservator/Representative)",
        "inability_section": True,
        "revision": "Revised 11/22/11",
    },

    "12_supportive_services": {
        "title": "Notification of East Los Angeles/West San Gabriel Valley AJCC Supportive Services",
        "org": "East Los Angeles/West San Gabriel Valley AJCC",
        "pages": 1,
        "category": "simple",
        "description": "AJCC supportive services policy notification and eligibility information",
        "intro_text": "Individuals registered in a Workforce Innovation and Opportunity Act (WIOA) program MAY be eligible for supportive services. Supportive Services include but are not limited to:",
        "services_list": [
            "Transportation",
            "Uniforms/Tools",
            "Materials for individuals with disabilities",
            "Clothing",
        ],
        "policy_text": """Supportive Services enable individuals to participate in appropriate activities at an AJCC Center in order to achieve economic self-sufficiency which may include participation in training, getting a job, keeping a job, and getting a better job. Supportive services will be provided only when they are NECESSARY for the individual to participate in a WIOA activity such as staff assisted job search, training and/or employment.

All supportive services cost must be NECESSARY, REASONABLE, and ALLOWABLE in accordance with Federal, State and local guidelines/standards. Examples of cost that are not allowable include, but are not limited to fines penalties for failure to comply with Federal, State, and local laws and regulations (including traffic tickets); bad debt expenses; and interest change.

EAST LOS ANGELES/WEST SAN GABRIEL VALLEY AJCC are required to seek non Workforce Innovation and Opportunity Act (WIOA) resources first before using WIOA funds for supportive services; because supportive services resources and WIOA funds are limited, individuals eligible for these services may receive limited or no supportive services. Individuals who can afford to pay for Supportive Services with their own resources are expected to do so.

EAST LOS ANGELES/WEST SAN GABRIEL VALLEY AJCC is composed of a collaboration of different programs, many of which offer supportive services, each with their own eligibility requirements, as a result, any customers receive different supportive services depending upon their individual situation and eligibility for other programs.

In order to receive or be reimbursed for any Supportive Services, customer must follow the center's procedures, including but not limited to completing the appropriate forms, submitting the required documentation, and receiving approval from staff prior to expending any funds for supportive services.""",
        "sections": [
            {
                "name": "customer_info",
                "title": "",
                "fields": [
                    {"id": "customer_name", "label": "Print Customer Name", "type": "text", "required": True},
                ]
            }
        ],
        "acknowledgment_text": "I certify that I have been informed of the EAST LOS ANGELES/WEST SAN GABRIEL VALLEY AJCC supportive services policy and procedures including how to request supportive services, that I have received a copy of this document, and that I understand that there is no guarantee that I will receive any supportive services because (1) I am not participating in a WIOA activity, (2) the supportive services I have requested are not necessary, reasonable, or allowable; or (3) lack of funding.",
        "signature_required": True,
        "signature_label": "Customer Signature",
        "staff_signature_required": True,
    },

    "13_applicant_statement": {
        "title": "Applicant Statement",
        "org": "",
        "pages": 1,
        "category": "medium",
        "description": "Self-certification statement for information that cannot be documented",
        "sections": [
            {
                "name": "statement",
                "title": "",
                "intro": "I, ___ hereby certify that the following information is true:",
                "fields": [
                    {"id": "statement_text", "label": "Statement", "type": "textarea", "rows": 8,
                     "help": "Enter the information you are certifying as true"},
                ]
            },
            {
                "name": "certification",
                "title": "",
                "fields": [
                    {"id": "print_name", "label": "Print Name", "type": "text", "required": True},
                ]
            }
        ],
        "acknowledgment_text": "I attest that the information stated above is true and accurate, and understand that the above information, if misrepresented, or incomplete, maybe grounds for immediate termination and/or penalties as specified by law.",
        "signature_required": True,
        "signature_label": "Signature of Customer",
        "staff_section": {
            "title": "Agency Use Only",
            "fields": [
                {"id": "items_attempted", "label": "List other items you made attempts to obtain", "type": "textarea", "rows": 2},
                {"id": "reason", "label": "Reason for Applicant Statement", "type": "text"},
            ]
        },
        "staff_signature_required": True,
        "revision": "Created by CY 8/18/11",
    },

    "14_income_worksheet": {
        "title": "Income Worksheet",
        "org": "",
        "pages": 1,
        "category": "complex",
        "description": "6-month income calculation worksheet for WIOA eligibility determination",
        "sections": [
            {
                "name": "applicant_info",
                "title": "",
                "fields": [
                    {"id": "applicant_name", "label": "NAME OF APPLICANT", "type": "text", "required": True},
                    {"id": "primary_wage_earner", "label": "PRIMARY WAGE EARNER", "type": "radio", "options": ["YES", "NO"]},
                    {"id": "low_income", "label": "LOW INCOME", "type": "radio", "options": ["YES", "NO"]},
                ]
            },
            {
                "name": "month_headers",
                "title": "",
                "type": "month_row",
                "description": "Enter the month names for each of the 6 months (e.g., 'January', 'February')",
            },
            {
                "name": "comments",
                "title": "COMMENTS",
                "fields": [
                    {"id": "comments", "label": "", "type": "textarea", "rows": 2},
                ]
            },
            {
                "name": "income_grid",
                "title": "Income Grid",
                "type": "income_table",
                "columns": ["Month 1", "Month 2", "Month 3", "Month 4", "Month 5", "Month 6"],
                "rows": [
                    {"id": "family_size", "label": "Number in Family for Each Month", "type": "number"},
                    {"id": "income_source_1", "label": "Customer (Income Source 1)", "type": "currency"},
                    {"id": "income_source_2", "label": "Income Source 2", "type": "currency"},
                    {"id": "income_source_3", "label": "Income Source 3", "type": "currency"},
                    {"id": "income_source_4", "label": "Income Source 4", "type": "currency"},
                ]
            },
            {
                "name": "uib_status",
                "title": "UIB (Unemployment Insurance Benefits)",
                "fields": [
                    {"id": "uib_status", "label": "UIB Status", "type": "select",
                     "options": ["Current", "Not Eligible", "Exhausted", "Claim Pending", "Filing", "N/A"]},
                    {"id": "uib_address_street", "label": "Address Street", "type": "text"},
                    {"id": "uib_address_city_zip", "label": "City/Zip", "type": "text"},
                ]
            },
            {
                "name": "summary",
                "title": "Summary Calculations",
                "fields": [
                    {"id": "max_family_size", "label": "Maximum Family Size", "type": "number"},
                    {"id": "max_income_pl", "label": "Maximum Income for Family Size - PL ($)", "type": "currency"},
                    {"id": "max_income_llsil", "label": "Maximum Income for Family Size - LLSIL ($)", "type": "currency"},
                    {"id": "max_income_125", "label": "Maximum Income for Family Size - 125% ($)", "type": "currency"},
                    {"id": "total_income_6mo", "label": "Total Income For Last Six Months ($)", "type": "currency"},
                    {"id": "annualized_income", "label": "Annualized Income ($)", "type": "currency"},
                ]
            }
        ],
        "certification_text": "APPLICANT'S CERTIFICATION: My signature below indicates that I have informed of and understand the information contained on this form. I certify, under penalty of perjury, that all of the above information is true and complete. I agree that any information I have supplied is subject to verification. I understand that falsification of any item is grounds for termination from the WIA Program and may result in action to recover any monies paid to me while participating in the program.",
        "signature_required": True,
        "signature_label": "Signature",
        "staff_signature_required": True,
    },
}


# ─── Form Rendering (Streamlit) ──────────────────────────────────────────────

def render_form_field(field, form_data, prefix=""):
    """Render a single form field in Streamlit."""
    import streamlit as st
    from datetime import date as date_type

    field_id = f"{prefix}{field['id']}" if prefix else field['id']
    label = field['label']
    required = field.get('required', False)
    if required:
        label = f"{label} *"

    field_type = field.get('type', 'text')
    default_value = form_data.get(field_id, field.get('default', ''))

    # Ensure default_value is never None for text fields
    if default_value is None:
        default_value = ''

    try:
        if field_type == 'text':
            value = st.text_input(label, value=str(default_value), key=field_id,
                                 max_chars=field.get('max_length'))

        elif field_type == 'textarea':
            value = st.text_area(label, value=str(default_value), key=field_id,
                                height=field.get('rows', 3) * 25,
                                help=field.get('help'))

        elif field_type == 'date':
            # Handle date field - convert string to date or use None
            date_val = None
            if isinstance(default_value, str) and default_value:
                try:
                    date_val = datetime.strptime(default_value, "%Y-%m-%d").date()
                except:
                    date_val = None
            elif isinstance(default_value, date_type):
                date_val = default_value
            # Use today as default if no value
            value = st.date_input(label, value=date_val, key=field_id)

        elif field_type == 'select':
            options = field.get('options', [])
            if not options:
                options = ['N/A']
            idx = options.index(default_value) if default_value in options else 0
            value = st.selectbox(label, options=options, index=idx, key=field_id)

        elif field_type == 'multiselect':
            options = field.get('options', [])
            if not options:
                options = ['N/A']
            default_vals = default_value if isinstance(default_value, list) else []
            # Filter out invalid defaults
            default_vals = [v for v in default_vals if v in options]
            value = st.multiselect(label, options=options, default=default_vals, key=field_id)

        elif field_type == 'radio':
            options = field.get('options', [])
            if not options:
                options = ['Yes', 'No']
            idx = options.index(default_value) if default_value in options else 0
            value = st.radio(label, options=options, index=idx, key=field_id, horizontal=True)

        elif field_type == 'checkbox':
            value = st.checkbox(label, value=bool(default_value), key=field_id)

        elif field_type == 'number':
            num_val = 0
            if default_value:
                try:
                    num_val = int(default_value)
                except:
                    num_val = 0
            value = st.number_input(label, value=num_val, key=field_id)

        elif field_type == 'currency':
            curr_val = 0.0
            if default_value:
                try:
                    curr_val = float(default_value)
                except:
                    curr_val = 0.0
            value = st.number_input(label, value=curr_val, key=field_id, format="%.2f")

        elif field_type == 'phone':
            value = st.text_input(label, value=str(default_value), key=field_id,
                                 placeholder="(555) 123-4567")

        elif field_type == 'email':
            value = st.text_input(label, value=str(default_value), key=field_id,
                                 placeholder="email@example.com")

        elif field_type == 'ssn':
            value = st.text_input(label, value=str(default_value), key=field_id,
                                 placeholder="XXX-XX-XXXX", type="password",
                                 help="Your SSN is encrypted and protected")

        else:
            value = st.text_input(label, value=str(default_value), key=field_id)

        return value

    except Exception as e:
        st.error(f"Error rendering field '{label}': {str(e)}")
        return None


def render_form(form_id, form_data=None, participant=None):
    """Render a complete form in Streamlit."""
    import streamlit as st

    if form_id not in ORIENTATION_FORMS:
        st.error(f"Form not found: {form_id}")
        return {}

    form_def = ORIENTATION_FORMS[form_id]
    form_data = form_data or {}
    collected_data = {}

    # Pre-fill from participant if available
    if participant:
        form_data.setdefault('first_name', participant.get('first_name', ''))
        form_data.setdefault('last_name', participant.get('last_name', ''))
        form_data.setdefault('full_name', participant.get('full_name', ''))
        form_data.setdefault('email', participant.get('email', ''))
        form_data.setdefault('phone', participant.get('phone', ''))
        form_data.setdefault('client_name', participant.get('full_name', ''))
        form_data.setdefault('customer_name', participant.get('full_name', ''))
        form_data.setdefault('print_name', participant.get('full_name', ''))
        form_data.setdefault('person_name', participant.get('full_name', ''))
        form_data.setdefault('applicant_name', participant.get('full_name', ''))
        form_data.setdefault('participant_name', participant.get('full_name', ''))
        form_data.setdefault('employee_name', participant.get('full_name', ''))

    # Form header
    st.markdown(f"### {form_def['title']}")
    if form_def.get('org'):
        st.caption(form_def['org'])
    if form_def.get('description'):
        st.caption(form_def['description'])

    # Show intro text if present
    if form_def.get('intro_text'):
        st.markdown(form_def['intro_text'])

    # Show policy text for forms with policy content
    if form_def.get('policy_text'):
        with st.expander("View Full Policy", expanded=form_def['category'] == 'simple'):
            st.markdown(form_def['policy_text'])

    # Show policy summary for privacy practices
    if form_def.get('policy_summary'):
        with st.expander("View Privacy Practices Summary", expanded=False):
            st.markdown(form_def['policy_summary'])

    # Show client rights list if present (Form 08)
    if form_def.get('client_rights'):
        st.markdown("#### CLIENT RIGHTS")
        for right in form_def['client_rights']:
            st.markdown(f"• {right}")

    # Show client responsibilities if present (Form 08)
    if form_def.get('client_responsibilities'):
        st.markdown("#### CLIENT RESPONSIBILITIES")
        for resp in form_def['client_responsibilities']:
            st.markdown(f"• {resp}")

    # Show complaint text if present (Form 08)
    if form_def.get('complaint_text'):
        st.markdown("---")
        st.markdown(f"**{form_def['complaint_text']}**")

    # Show rights list if present (Form 09)
    if form_def.get('rights_list'):
        for i, right in enumerate(form_def['rights_list'], 1):
            st.markdown(f"{i}. {right}")

    # Show services list if present (Form 12)
    if form_def.get('services_list'):
        cols = st.columns(2)
        for i, service in enumerate(form_def['services_list']):
            cols[i % 2].markdown(f"• **{service}**")

    # Show acknowledgments if any (for structured acknowledgments like Form 04)
    if form_def.get('acknowledgments'):
        for i, ack in enumerate(form_def['acknowledgments']):
            if isinstance(ack, dict):
                with st.expander(ack['title'], expanded=True):
                    st.markdown(ack['text'])
                    collected_data[f'ack_{i}'] = st.checkbox(
                        f"I acknowledge and understand the {ack['title']}",
                        key=f"{form_id}_ack_{i}"
                    )
            else:
                collected_data[f'ack_{i}'] = st.checkbox(ack, key=f"{form_id}_ack_{i}")

    # Render sections
    for section in form_def.get('sections', []):
        # Check if section has a conditional show_if
        section_show_if = section.get('show_if')
        should_show_section = True

        if section_show_if and isinstance(section_show_if, dict):
            controlling_field = section_show_if.get('field')
            required_value = section_show_if.get('value')

            current_value = None
            if controlling_field in st.session_state:
                current_value = st.session_state[controlling_field]
            elif controlling_field in collected_data:
                current_value = collected_data[controlling_field]
            elif controlling_field in form_data:
                current_value = form_data[controlling_field]

            should_show_section = (current_value == required_value)

        if not should_show_section:
            continue

        if section.get('title'):
            st.markdown(f"#### {section['title']}")

        # Show section intro if present
        if section.get('intro'):
            st.markdown(section['intro'])

        # Handle special section types
        if section.get('type') == 'income_table':
            # Render income table
            st.markdown("**Enter income for each month:**")
            cols = st.columns(len(section['columns']) + 1)

            # Header row
            cols[0].markdown("**Item**")
            for i, col_name in enumerate(section['columns']):
                cols[i + 1].markdown(f"**{col_name}**")

            # Data rows
            for row in section['rows']:
                row_cols = st.columns(len(section['columns']) + 1)
                row_cols[0].markdown(row['label'])
                for i, col_name in enumerate(section['columns']):
                    field_key = f"{row['id']}_{i}"
                    collected_data[field_key] = row_cols[i + 1].text_input(
                        "", key=f"{form_id}_{field_key}", label_visibility="collapsed"
                    )
        elif section.get('type') == 'month_row':
            # Render month name inputs
            st.markdown("**Enter the month names:**")
            month_cols = st.columns(6)
            for i in range(6):
                collected_data[f'month_{i}'] = month_cols[i].text_input(
                    f"Month {i+1} OF", key=f"{form_id}_month_{i}", label_visibility="collapsed",
                    placeholder=f"Month {i+1}"
                )
        else:
            # Regular fields
            for field in section.get('fields', []):
                # Check if field has a conditional show_if
                show_if = field.get('show_if')
                should_show = True

                if show_if and isinstance(show_if, dict):
                    # Get the controlling field's current value
                    controlling_field = show_if.get('field')
                    required_value = show_if.get('value')

                    # Check session state first, then collected_data, then form_data
                    current_value = None
                    if controlling_field in st.session_state:
                        current_value = st.session_state[controlling_field]
                    elif controlling_field in collected_data:
                        current_value = collected_data[controlling_field]
                    elif controlling_field in form_data:
                        current_value = form_data[controlling_field]

                    should_show = (current_value == required_value)

                if should_show:
                    collected_data[field['id']] = render_form_field(field, form_data, prefix="")
                else:
                    # Field is hidden, store None or empty value
                    collected_data[field['id']] = None

    # Staff section if present
    if form_def.get('staff_section'):
        st.markdown("---")
        st.markdown(f"### {form_def['staff_section']['title']}")
        st.info("This section is for staff use only")
        for field in form_def['staff_section'].get('fields', []):
            collected_data[f"staff_{field['id']}"] = render_form_field(field, form_data, prefix="staff_")

    # Certification text if present
    if form_def.get('certification_text'):
        st.markdown("---")
        st.markdown(f"**{form_def['certification_text']}**")

    # Acknowledgment text
    if form_def.get('acknowledgment_text'):
        st.markdown("---")
        st.markdown(f"**{form_def['acknowledgment_text']}**")
        # Add acknowledgment checkbox
        collected_data['acknowledged'] = st.checkbox(
            "I have read and agree to the above",
            key=f"{form_id}_final_ack"
        )

    # For simple forms with only policy text, add a read confirmation
    if form_def.get('category') == 'simple' and not form_def.get('acknowledgment_text'):
        st.markdown("---")
        collected_data['policy_read'] = st.checkbox(
            "I have read and understand this policy",
            key=f"{form_id}_policy_read"
        )

    # Always capture completion timestamp in data
    collected_data['_form_id'] = form_id
    collected_data['_form_title'] = form_def.get('title', form_id)

    return collected_data


def get_form_list():
    """Return list of all forms for selection."""
    forms = []
    for form_id, form_def in ORIENTATION_FORMS.items():
        forms.append({
            "id": form_id,
            "title": form_def['title'],
            "category": form_def['category'],
            "description": form_def.get('description', ''),
            "pages": form_def.get('pages', 1),
            "org": form_def.get('org', ''),
        })
    return forms


def get_simple_forms():
    """Return list of simple signature-only forms."""
    return [f for f in get_form_list() if f['category'] == 'simple']


def get_complex_forms():
    """Return list of complex forms with multiple fields."""
    return [f for f in get_form_list() if f['category'] in ('medium', 'complex')]


# ─── PDF Generation ──────────────────────────────────────────────────────────

def generate_form_pdf(form_id, form_data, participant, signature_image=None, output_path=None):
    """
    Generate a PDF from completed form data that matches original paper format.

    Args:
        form_id: The form ID from ORIENTATION_FORMS
        form_data: Dict of field values from form submission
        participant: Participant data dict
        signature_image: Either a file path string OR raw PNG bytes of signature
        output_path: Ignored - always returns bytes (kept for compatibility)

    Returns:
        tuple: (bytes_buffer, error_message) - buffer contains PDF bytes on success
    """
    if not HAS_REPORTLAB:
        return None, "ReportLab not installed. Install with: pip install reportlab"

    if form_id not in ORIENTATION_FORMS:
        return None, f"Form not found: {form_id}"

    form_def = ORIENTATION_FORMS[form_id]

    # Create PDF buffer
    buffer = io.BytesIO()

    # Create document
    doc = SimpleDocTemplate(
        buffer,
        pagesize=letter,
        rightMargin=0.5*inch,
        leftMargin=0.5*inch,
        topMargin=0.5*inch,
        bottomMargin=0.5*inch
    )

    # Styles
    styles = getSampleStyleSheet()
    styles.add(ParagraphStyle(
        name='FormTitle',
        parent=styles['Heading1'],
        fontSize=14,
        alignment=TA_CENTER,
        spaceAfter=12,
        fontName='Helvetica-Bold',
    ))
    styles.add(ParagraphStyle(
        name='OrgName',
        parent=styles['Normal'],
        fontSize=10,
        alignment=TA_CENTER,
        spaceAfter=12,
        textColor=colors.grey,
    ))
    styles.add(ParagraphStyle(
        name='SectionTitle',
        parent=styles['Heading2'],
        fontSize=11,
        spaceBefore=10,
        spaceAfter=6,
        fontName='Helvetica-Bold',
    ))
    styles.add(ParagraphStyle(
        name='PolicyText',
        parent=styles['Normal'],
        fontSize=9,
        alignment=TA_JUSTIFY,
        spaceBefore=4,
        spaceAfter=4,
        leading=12,
    ))
    styles.add(ParagraphStyle(
        name='FieldLabel',
        parent=styles['Normal'],
        fontSize=9,
        textColor=colors.grey,
    ))
    styles.add(ParagraphStyle(
        name='FieldValue',
        parent=styles['Normal'],
        fontSize=10,
        fontName='Helvetica-Bold',
    ))
    styles.add(ParagraphStyle(
        name='CheckboxStyle',
        parent=styles['Normal'],
        fontSize=10,
    ))
    styles.add(ParagraphStyle(
        name='CertificationText',
        parent=styles['Normal'],
        fontSize=8,
        alignment=TA_JUSTIFY,
        spaceBefore=8,
        spaceAfter=8,
        leading=10,
    ))

    # Build content
    story = []

    # Organization header
    if form_def.get('org'):
        story.append(Paragraph(form_def['org'], styles['OrgName']))

    # Title
    story.append(Paragraph(form_def['title'].upper(), styles['FormTitle']))
    story.append(Spacer(1, 6))

    # Intro text
    if form_def.get('intro_text'):
        story.append(Paragraph(form_def['intro_text'], styles['PolicyText']))
        story.append(Spacer(1, 6))

    # Policy text
    if form_def.get('policy_text'):
        for para in form_def['policy_text'].strip().split('\n\n'):
            if para.strip():
                story.append(Paragraph(para.strip().replace('\n', '<br/>'), styles['PolicyText']))
                story.append(Spacer(1, 4))

    # Client rights (Form 08)
    if form_def.get('client_rights'):
        story.append(Paragraph("CLIENT RIGHTS", styles['SectionTitle']))
        for right in form_def['client_rights']:
            story.append(Paragraph(f"• {right}", styles['PolicyText']))

    # Client responsibilities (Form 08)
    if form_def.get('client_responsibilities'):
        story.append(Paragraph("CLIENT RESPONSIBILITIES", styles['SectionTitle']))
        for resp in form_def['client_responsibilities']:
            story.append(Paragraph(f"• {resp}", styles['PolicyText']))

    # Complaint text (Form 08)
    if form_def.get('complaint_text'):
        story.append(Spacer(1, 8))
        story.append(Paragraph(form_def['complaint_text'], styles['PolicyText']))

    # Rights list (Form 09)
    if form_def.get('rights_list'):
        for i, right in enumerate(form_def['rights_list'], 1):
            story.append(Paragraph(f"{i}. {right}", styles['PolicyText']))

    # Services list (Form 12)
    if form_def.get('services_list'):
        services_text = " • ".join(form_def['services_list'])
        story.append(Paragraph(f"• {services_text}", styles['PolicyText']))

    # Acknowledgments (Form 04)
    if form_def.get('acknowledgments'):
        for i, ack in enumerate(form_def['acknowledgments']):
            if isinstance(ack, dict):
                story.append(Paragraph(ack['title'], styles['SectionTitle']))
                story.append(Paragraph(ack['text'], styles['PolicyText']))
                checked = form_data.get(f'ack_{i}', False)
                checkbox = "[X]" if checked else "[ ]"
                story.append(Paragraph(f"{checkbox} I acknowledge and understand", styles['CheckboxStyle']))
            else:
                checked = form_data.get(f'ack_{i}', False)
                checkbox = "[X]" if checked else "[ ]"
                story.append(Paragraph(f"{checkbox} {ack}", styles['CheckboxStyle']))

    # Sections
    for section in form_def.get('sections', []):
        if section.get('title'):
            story.append(Paragraph(section['title'], styles['SectionTitle']))

        if section.get('intro'):
            story.append(Paragraph(section['intro'], styles['PolicyText']))

        # Create table for fields
        if section.get('fields'):
            field_data = []
            for field in section['fields']:
                label = field['label']
                value = form_data.get(field['id'], '')
                if isinstance(value, (list, tuple)):
                    value = ', '.join(str(v) for v in value)
                elif isinstance(value, date):
                    value = value.strftime("%m/%d/%Y")
                elif isinstance(value, bool):
                    value = "[X]" if value else "[ ]"

                field_data.append([
                    Paragraph(f"{label}:", styles['FieldLabel']),
                    Paragraph(str(value) if value else "_____________", styles['FieldValue'])
                ])

            if field_data:
                t = Table(field_data, colWidths=[2.5*inch, 4.5*inch])
                t.setStyle(TableStyle([
                    ('VALIGN', (0, 0), (-1, -1), 'TOP'),
                    ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
                    ('TOPPADDING', (0, 0), (-1, -1), 2),
                ]))
                story.append(t)

    # Certification text
    if form_def.get('certification_text'):
        story.append(Spacer(1, 12))
        story.append(Paragraph(form_def['certification_text'], styles['CertificationText']))

    # Acknowledgment text
    if form_def.get('acknowledgment_text'):
        story.append(Spacer(1, 8))
        story.append(Paragraph(form_def['acknowledgment_text'], styles['PolicyText']))
        acknowledged = form_data.get('acknowledged', False)
        checkbox = "[X]" if acknowledged else "[ ]"
        story.append(Paragraph(f"{checkbox} I have read and agree to the above", styles['CheckboxStyle']))

    # Signature section
    if form_def.get('signature_required'):
        story.append(Spacer(1, 20))

        sig_label = form_def.get('signature_label', 'Signature')
        sig_date = datetime.now().strftime("%m/%d/%Y")

        # Add signature image if provided
        sig_added = False
        if signature_image:
            try:
                # Handle both file path and raw bytes
                if isinstance(signature_image, bytes):
                    # Signature provided as bytes
                    sig_buffer = io.BytesIO(signature_image)
                    story.append(Paragraph(f"{sig_label}:", styles['FieldLabel']))
                    story.append(RLImage(sig_buffer, width=2*inch, height=0.5*inch))
                    sig_added = True
                elif isinstance(signature_image, str) and Path(signature_image).exists():
                    # Signature provided as file path (legacy support)
                    story.append(Paragraph(f"{sig_label}:", styles['FieldLabel']))
                    story.append(RLImage(str(signature_image), width=2*inch, height=0.5*inch))
                    sig_added = True
            except Exception:
                pass

        if not sig_added:
            story.append(Paragraph(f"{sig_label}: _________________________", styles['Normal']))

        story.append(Spacer(1, 4))
        story.append(Paragraph(f"Date: {sig_date}", styles['Normal']))

        # Parent/Guardian signature if required
        if form_def.get('parent_guardian_signature'):
            story.append(Spacer(1, 12))
            story.append(Paragraph("Parent/Guardian Signature: _________________________  Date: _____________", styles['Normal']))

        # Staff signature if required
        if form_def.get('staff_signature_required'):
            story.append(Spacer(1, 16))
            story.append(Paragraph("Staff Signature: _________________________  Date: _____________", styles['Normal']))
            story.append(Paragraph("Staff Name (Print): _________________________", styles['Normal']))

    # Footer
    if form_def.get('footer'):
        story.append(Spacer(1, 20))
        story.append(Paragraph(form_def['footer'], styles['OrgName']))

    # Revision info
    if form_def.get('revision'):
        story.append(Spacer(1, 12))
        story.append(Paragraph(form_def['revision'], styles['OrgName']))

    # Build PDF
    doc.build(story)

    # Always return bytes - no disk writes
    buffer.seek(0)
    return buffer.getvalue(), None


def save_form_response(participant_id, form_id, form_data, participants_data):
    """Save form response to participant record."""
    if participant_id not in participants_data:
        return False

    if 'forms' not in participants_data[participant_id]:
        participants_data[participant_id]['forms'] = {}

    participants_data[participant_id]['forms'][form_id] = {
        'data': form_data,
        'completed_at': datetime.now().isoformat(),
        'status': 'completed'
    }

    return True
