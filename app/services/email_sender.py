"""
Email sender service for participant submissions.

Sends zip file attachments via Gmail SMTP using settings from config.
"""

import smtplib
import logging
from email.mime.multipart import MIMEMultipart
from email.mime.base import MIMEBase
from email.mime.text import MIMEText
from email import encoders

from config import EmailConfig

# Set up logging
logger = logging.getLogger(__name__)


def send_submission_email(recipient, subject, zip_bytes, zip_filename, body=None):
    """
    Send a submission email with zip attachment.

    Args:
        recipient: Email address to send to
        subject: Email subject line
        zip_bytes: The zip file contents as bytes
        zip_filename: Filename for the attachment
        body: Optional email body text (default: auto-generated)

    Returns:
        bool: True on success, False on failure
    """
    # Check if email is configured
    if not EmailConfig.is_configured():
        logger.error("Email not configured. Set SMTP_SERVER, SMTP_USERNAME, and SMTP_PASSWORD in .env")
        return False

    # Build default body if not provided
    if body is None:
        body = f"""INVEST Orientation Intake Submission

A new participant submission has been received.

Attached: {zip_filename}

This is an automated message from the INVEST Orientation Intake System.
"""

    try:
        # Create message
        msg = MIMEMultipart()
        msg["From"] = EmailConfig.SMTP_USERNAME
        msg["To"] = recipient
        msg["Subject"] = subject

        # Attach body text
        msg.attach(MIMEText(body, "plain"))

        # Attach zip file
        attachment = MIMEBase("application", "zip")
        attachment.set_payload(zip_bytes)
        encoders.encode_base64(attachment)
        attachment.add_header(
            "Content-Disposition",
            f"attachment; filename={zip_filename}"
        )
        msg.attach(attachment)

        # Connect and send
        with smtplib.SMTP(EmailConfig.SMTP_SERVER, EmailConfig.SMTP_PORT) as server:
            server.starttls()
            server.login(EmailConfig.SMTP_USERNAME, EmailConfig.SMTP_PASSWORD)
            server.send_message(msg)

        logger.info(f"Email sent successfully to {recipient}")
        return True

    except smtplib.SMTPAuthenticationError as e:
        logger.error(f"SMTP authentication failed: {e}")
        return False

    except smtplib.SMTPConnectError as e:
        logger.error(f"Failed to connect to SMTP server: {e}")
        return False

    except smtplib.SMTPRecipientsRefused as e:
        logger.error(f"Recipient refused: {e}")
        return False

    except smtplib.SMTPException as e:
        logger.error(f"SMTP error occurred: {e}")
        return False

    except Exception as e:
        logger.error(f"Unexpected error sending email: {e}")
        return False


def send_submission_to_default_recipients(subject, zip_bytes, zip_filename, body=None):
    """
    Send submission to all default recipients from config.

    Args:
        subject: Email subject line
        zip_bytes: The zip file contents as bytes
        zip_filename: Filename for the attachment
        body: Optional email body text

    Returns:
        dict: Results for each recipient {email: bool}
    """
    from config import DEFAULT_RECIPIENTS

    if not DEFAULT_RECIPIENTS:
        logger.warning("No default recipients configured in DEFAULT_RECIPIENTS")
        return {}

    results = {}
    for recipient in DEFAULT_RECIPIENTS:
        results[recipient] = send_submission_email(
            recipient=recipient,
            subject=subject,
            zip_bytes=zip_bytes,
            zip_filename=zip_filename,
            body=body
        )

    return results
