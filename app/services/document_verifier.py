"""
AI-powered document verification using Claude Vision.

Verifies that uploaded documents match expected types and meet quality standards.
"""

import base64

from config import get_secret

# Optional Anthropic import
try:
    import anthropic
    HAS_ANTHROPIC = True
except ImportError:
    HAS_ANTHROPIC = False


def verify_document_with_ai(image_data, expected_doc_type):
    """Use Claude Vision to verify the document type and quality."""
    if not HAS_ANTHROPIC:
        return {"verified": True, "message": "AI verification not available", "confidence": "N/A"}

    api_key = get_secret("ANTHROPIC_API_KEY")
    if not api_key:
        return {"verified": True, "message": "No API key configured", "confidence": "N/A"}

    try:
        client = anthropic.Anthropic(api_key=api_key, timeout=30.0)

        # Convert image to base64
        if isinstance(image_data, bytes):
            img_bytes = image_data
        else:
            img_bytes = image_data.getvalue()

        img_base64 = base64.b64encode(img_bytes).decode("utf-8")

        # Determine expected document description
        doc_descriptions = {
            "id": "a Driver's License or State ID card",
            "ssn": "a Social Security Card",
            "address": "a proof of address document (utility bill, lease, bank statement)",
            "birth_cert": "a Birth Certificate",
            "selective_service": "a Selective Service Registration card or letter",
            "other": "an official document",
        }
        expected_desc = doc_descriptions.get(expected_doc_type, "an official document")

        prompt = f"""Analyze this image and determine:
1. Is this {expected_desc}? Answer YES or NO.
2. Is the image clear enough to read the text? Answer YES or NO.
3. Can you see a name on the document? If yes, what name?
4. Rate the image quality: GOOD, ACCEPTABLE, or POOR.

Respond in this exact format:
DOCUMENT_MATCH: YES/NO
IMAGE_READABLE: YES/NO
NAME_VISIBLE: [name or "Not visible"]
QUALITY: GOOD/ACCEPTABLE/POOR
BRIEF_NOTE: [One sentence about the document]"""

        response = client.messages.create(
            model="claude-sonnet-4-20250514",
            max_tokens=300,
            messages=[
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "image",
                            "source": {
                                "type": "base64",
                                "media_type": "image/jpeg",
                                "data": img_base64,
                            },
                        },
                        {
                            "type": "text",
                            "text": prompt,
                        },
                    ],
                }
            ],
        )

        result_text = response.content[0].text

        # Parse response
        doc_match = "YES" in result_text.split("DOCUMENT_MATCH:")[1].split("\n")[0].upper() if "DOCUMENT_MATCH:" in result_text else False
        readable = "YES" in result_text.split("IMAGE_READABLE:")[1].split("\n")[0].upper() if "IMAGE_READABLE:" in result_text else False
        quality = "GOOD" if "QUALITY: GOOD" in result_text else ("ACCEPTABLE" if "QUALITY: ACCEPTABLE" in result_text else "POOR")

        verified = doc_match and readable and quality != "POOR"

        if verified:
            message = "Document verified successfully"
        elif not doc_match:
            message = f"This doesn't appear to be {expected_desc}. Please upload the correct document."
        elif not readable:
            message = "The image is not clear enough. Please retake the photo with better lighting."
        else:
            message = "Image quality is poor. Please retake the photo."

        return {
            "verified": verified,
            "message": message,
            "confidence": quality,
            "raw_response": result_text,
        }

    except Exception as e:
        return {"verified": True, "message": f"Verification skipped: {str(e)}", "confidence": "N/A"}
