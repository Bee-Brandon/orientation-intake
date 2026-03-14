# save as test_forms.py in your project root
from app.services.pdf_filler import fill_attachment_iv, fill_attachment_v, fill_code_of_conduct
from pathlib import Path

# Dummy participant data
test_data = {
    "first_name": "John",
    "last_name": "Doe",
    "date_of_birth": "01/01/1990",
    "phone": "626-555-1234",
    "email": "test@test.com",
    "address": "123 Main St, Los Angeles CA 90001",
}

# Emergency contact — separate dict for fill_attachment_v
emergency_contact = {
    "name": "Jane Doe",
    "street": "456 Oak Ave",
    "city": "Los Angeles",
    "zip": "90001",
    "phone": "626-555-5678",
    "is_government": False,  # False = Box 2 (standard), True = Box 1 (gov employee)
    # "relationship": "Sister",  # Only needed if is_government=True
}

staff_name = "Staff Member"

# Dummy signature — small black rectangle PNG as placeholder
from PIL import Image
from io import BytesIO

def make_test_signature():
    # Create a simple black rectangle as a PNG image
    img = Image.new('RGBA', (190, 18), (0, 0, 0, 255))
    buf = BytesIO()
    img.save(buf, format='PNG')
    return buf.getvalue()

sig_bytes = make_test_signature()

# Generate all three
print("Generating Attachment V...")
v_bytes = fill_attachment_v(test_data, sig_bytes, emergency_contact=emergency_contact)
Path("test_attachment_v_filled.pdf").write_bytes(v_bytes)

print("Generating Attachment IV...")
iv_bytes = fill_attachment_iv(test_data, sig_bytes, staff_name=staff_name)
Path("test_attachment_iv_filled.pdf").write_bytes(iv_bytes)

print("Generating Code of Conduct...")
coc_bytes = fill_code_of_conduct(sig_bytes)  # Only takes signature_bytes
Path("test_code_of_conduct_filled.pdf").write_bytes(coc_bytes)

print("Done. Open the three PDFs and compare to the originals.")
