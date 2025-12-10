# CapitalFinance_Final.py
"""
Single-file Streamlit app:
TATA CAPITAL THEME — Loan Sanction Demo
Features:
 - Tata-themed UI (gradient + cards)
 - Loan EMI calculator
 - Purpose dropdown
 - PAN validation
 - Mobile & email validation (cleaning)
 - OCR (optional, fallback if not available)
 - Dummy credit-risk score
 - Generate PDF sanction letter with QR embedded
 - Download PDF
 - WhatsApp share link generation
 - SMTP email send with PDF attachment (optional)
"""

import streamlit as st
import requests
from io import BytesIO
from datetime import datetime
import qrcode
from reportlab.lib.pagesizes import A4
from reportlab.lib import colors
from reportlab.lib.units import inch
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, Image as RLImage, Table
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.enums import TA_CENTER, TA_LEFT
import re
import smtplib
from email.message import EmailMessage
import urllib.parse
import pandas as pd
import numpy as np

# Optional OCR imports
OCR_AVAILABLE = True
try:
    from PIL import Image
    import pytesseract
except Exception:
    OCR_AVAILABLE = False

# -------------------- Helper functions --------------------
def is_valid_pan(pan: str) -> bool:
    """Validate Indian PAN format: 5 letters, 4 digits, 1 letter e.g. ABCDE1234F"""
    return bool(re.fullmatch(r"[A-Z]{5}[0-9]{4}[A-Z]", (pan or "").strip().upper()))

def clean_mobile(mob: str) -> str:
    """Return only digits from mobile input"""
    if not mob:
        return ""
    digits = re.sub(r"\D", "", mob)
    # If leading country code 91 present and length > 10, strip it
    if len(digits) > 10 and digits.endswith(digits[-10:]):
        # keep last 10 digits
        digits = digits[-10:]
    return digits

def calculate_emi(principal: float, annual_rate: float, months: int) -> float:
    """Standard EMI formula. returns monthly EMI (float)."""
    if months <= 0:
        return 0.0
    r = annual_rate / 12.0 / 100.0
    try:
        emi = principal * r * (1 + r) ** months / ((1 + r) ** months - 1)
        return float(emi)
    except Exception:
        return 0.0

def generate_qr_image_bytes(data: str) -> BytesIO:
    """Return BytesIO containing PNG image of QR code."""
    qr = qrcode.QRCode(error_correction=qrcode.constants.ERROR_CORRECT_M, box_size=8, border=2)
    qr.add_data(data)
    qr.make(fit=True)
    img = qr.make_image(fill_color="black", back_color="white")
    bio = BytesIO()
    img.save(bio, format="PNG")
    bio.seek(0)
    return bio

def compute_dummy_credit_score(salary_monthly: float, loan_amount: float, pan_ok: bool) -> float:
    """
    Simple interpretable credit score:
    - Higher monthly salary -> better score
    - Lower LTV (loan / annual income) -> better score
    - PAN presence -> small boost
    Result scaled 0-100
    """
    salary = max(float(salary_monthly or 0), 0.0)
    annual_income = max(salary * 12.0, 1.0)
    ltv = loan_amount / annual_income

    score = 50.0
    # salary boost
    if salary >= 200000:
        score += 20
    elif salary >= 100000:
        score += 12
    elif salary >= 50000:
        score += 6
    elif salary >= 25000:
        score += 2

    # ltv effect
    if ltv < 0.4:
        score += 18
    elif ltv < 0.75:
        score += 6
    elif ltv < 1.25:
        score -= 6
    else:
        score -= 15

    # PAN
    if pan_ok:
        score += 4

    # clamp
    score = max(0.0, min(100.0, score))
    return round(score, 1)

def try_ocr_extract_text(uploaded_file) -> str:
    """Try to run OCR on uploaded image/pdf and return extracted text or message."""
    if not OCR_AVAILABLE:
        return "OCR not available in this environment."
    try:
        # PIL can open the uploaded file (Streamlit's UploadedFile behaves like a file)
        img = Image.open(uploaded_file)
        text = pytesseract.image_to_string(img)
        return text.strip() or "OCR ran but extracted no text."
    except Exception as e:
        return f"OCR failed: {str(e)}"

def make_whatsapp_link(message: str, phone_number: str = "") -> str:
    """Return a wa.me link. phone_number optional (digits only)."""
    encoded = urllib.parse.quote(message)
    phone = re.sub(r"\D", "", phone_number or "")
    if phone:
        return f"https://wa.me/{phone}?text={encoded}"
    return f"https://wa.me/?text={encoded}"

def send_email_smtp(smtp_host, smtp_port, smtp_user, smtp_password, to_email, subject, body, attachment_bytes=None, attachment_name="Sanction_Letter.pdf"):
    """Send email using SMTP (TLS). Returns (ok, message)."""
    try:
        msg = EmailMessage()
        msg['Subject'] = subject
        msg['From'] = smtp_user
        msg['To'] = to_email
        msg.set_content(body)
        if attachment_bytes:
            msg.add_attachment(attachment_bytes, maintype='application', subtype='pdf', filename=attachment_name)
        server = smtplib.SMTP(smtp_host, smtp_port, timeout=20)
        server.ehlo()
        server.starttls()
        server.login(smtp_user, smtp_password)
        server.send_message(msg)
        server.quit()
        return True, "Email sent successfully"
    except Exception as e:
        return False, f"Email failed: {str(e)}"

# -------------------- PDF builder --------------------
def build_sanction_pdf(applicant: dict, loan_info: dict, qr_bytes_io: BytesIO, pdf_title: str = "TATA CAPITAL FINANCE – LOAN APPROVAL LETTER") -> bytes:
    """
    Build a professional PDF with logo, table details and embedded QR code.
    Returns raw PDF bytes.
    applicant: {name, mobile, email, pan}
    loan_info: {amount, roi, tenure, emi, processing_fee, net_disbursed, purpose, credit_score}
    qr_bytes_io: BytesIO of QR PNG
    """
    buffer = BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=A4, topMargin=0.8*inch, bottomMargin=0.8*inch, leftMargin=0.7*inch, rightMargin=0.7*inch)
    story = []
    styles = getSampleStyleSheet()

    # Header: try get logo
    try:
        logo_url = "https://upload.wikimedia.org/wikipedia/commons/thumb/8/81/Tata_Capital_Logo.svg/512px-Tata_Capital_Logo.svg.png"
        resp = requests.get(logo_url, timeout=5)
        if resp.status_code == 200:
            logo_img = RLImage(BytesIO(resp.content), width=2.6*inch, height=0.85*inch, hAlign='CENTER')
            story.append(logo_img)
            story.append(Spacer(1, 8))
    except Exception:
        pass

    # Title
    title_style = ParagraphStyle(name="TitleStyle", fontSize=18, alignment=TA_CENTER, textColor=colors.HexColor('#0b3b61'), spaceAfter=6)
    sub_style = ParagraphStyle(name="SubStyle", fontSize=14, alignment=TA_CENTER, textColor=colors.HexColor('#c8102e'), spaceAfter=12)
    story.append(Paragraph(pdf_title, title_style))
    story.append(Paragraph("PERSONAL LOAN SANCTION LETTER (PROVISIONAL)", sub_style))
    story.append(Spacer(1, 8))

    # Applicant details
    normal = ParagraphStyle(name='Normal', fontSize=10.5, leading=14)
    story.append(Paragraph(f"<b>Date:</b> {datetime.now().strftime('%d %B %Y')}", normal))
    story.append(Paragraph(f"<b>Applicant:</b> {applicant.get('name','N/A')}", normal))
    story.append(Paragraph(f"<b>Mobile:</b> {applicant.get('mobile','N/A')}  |  <b>Email:</b> {applicant.get('email','N/A')}", normal))
    story.append(Paragraph(f"<b>PAN:</b> {applicant.get('pan','N/A')}", normal))
    story.append(Paragraph(f"<b>Purpose:</b> {loan_info.get('purpose','N/A')}", normal))
    story.append(Spacer(1, 12))

    # Loan table
    data = [
        ['Loan Detail', 'Value'],
        ['Loan Amount Sanctioned', f"₹{int(loan_info['amount']):,}"],
        ['Rate of Interest (Reducing)', f"{loan_info['roi']}% p.a."],
        ['Loan Tenure', f"{loan_info['tenure']} Months"],
        ['Estimated Monthly EMI', f"₹{int(round(loan_info['emi'])):,}"],
        ['Processing Fee + GST', f"₹{int(round(loan_info['processing_fee'])):,}"],
        ['Net Amount to be Disbursed', f"₹{int(round(loan_info['net_disbursed'])):,}"],
        ['Credit Risk Score (0-100)', f"{loan_info.get('credit_score', 0)}"],
    ]
    table = Table(data, colWidths=[320, 180])
    table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#c8102e')),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
        ('FONTNAME', (0, 0), (-1, -1), 'Helvetica'),
        ('FONTSIZE', (0, 0), (-1, -1), 10.5),
        ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
        ('BACKGROUND', (0, 1), (-1, -1), colors.whitesmoke),
        ('GRID', (0, 0), (-1, -1), 0.5, colors.gray),
        ('BOTTOMPADDING', (0,0), (-1,-1), 8),
    ]))
    story.append(table)
    story.append(Spacer(1, 12))

    # Note paragraph
    note_text = ("This sanction letter is provisional and subject to verification of documents, KYC, "
                 "credit underwriting and execution of loan documentation. Final terms will be as per the loan agreement.")
    story.append(Paragraph(note_text, ParagraphStyle(name='Note', fontSize=9.5, leading=13)))

    story.append(Spacer(1, 20))

    # Footer with QR on right and signatory text left
    try:
        qr_img = RLImage(qr_bytes_io, width=1.6*inch, height=1.6*inch, hAlign='RIGHT')
        footer_table = Table([[Paragraph("<b>Authorized Signatory</b><br/>Capital Finance", normal), qr_img]],
                             colWidths=[340, 120])
        footer_table.setStyle(TableStyle([('VALIGN', (0,0), (-1,-1), 'TOP')]))
        story.append(footer_table)
    except Exception:
        story.append(Paragraph("<b>Authorized Signatory</b><br/>Capital Finance", normal))

    doc.build(story)
    buffer.seek(0)
    return buffer.read()

# -------------------- Streamlit UI layout & styling --------------------
st.set_page_config(page_title="Capital Finance - Instant Sanction", layout="centered")
# Custom CSS for Tata-themed gradient + card
st.markdown(
    """
    <style>
    .stApp { background: radial-gradient(circle at 10% 10%, rgba(200,16,46,0.06), transparent 5%),
                        linear-gradient(135deg, #071428 0%, #0b2a45 50%, #071428 100%); }
    .card {
        background: linear-gradient(180deg, rgba(255,255,255,0.98), rgba(250,250,250,0.95));
        border-radius: 18px;
        padding: 22px;
        box-shadow: 0 12px 40px rgba(2,6,23,0.55);
        border: 1px solid rgba(200,16,46,0.06);
    }
    .highlight-title {
        font-size: 36px !important;
        font-weight: 800 !important;
        color: #ffffff !important;
        background: linear-gradient(90deg, #c8102e, #e63946);
        padding: 18px 28px;
        border-radius: 40px;
        text-align: center;
        margin: 10px auto 22px auto;
        box-shadow: 0 8px 30px rgba(200,16,46,0.25);
        max-width: 920px;
    }
    .subtle { color: #94a3b8; }
    </style>
    """,
    unsafe_allow_html=True,
)

# Header card
st.markdown("<div class='highlight-title'>TATA CAPITAL FINANCE</div>", unsafe_allow_html=True)
st.markdown("<div style='text-align:center; margin-bottom:18px;'><p style='color:#e6eef7'>Personal Loan • Instant Sanction • Transparent Fees</p></div>", unsafe_allow_html=True)

# Main container
st.markdown("<div class='card'>", unsafe_allow_html=True)

# Sidebar SMTP settings
st.sidebar.header("App Options & SMTP (optional)")
with st.sidebar.expander("SMTP Settings (optional)"):
    smtp_host = st.text_input("SMTP Host", value="smtp.gmail.com")
    smtp_port = st.number_input("SMTP Port", value=587)
    smtp_user = st.text_input("SMTP User (from email)")
    smtp_password = st.text_input("SMTP Password / App Password", type="password")
st.sidebar.markdown("⚠ For Gmail use App Passwords when 2FA is enabled.")

# Application form
st.markdown("## Apply for Personal Loan")
st.caption("Fill the form below. PDF will be generated only after accepting Terms & Conditions.")

col1, col2 = st.columns([2,1])
with col1:
    name = st.text_input("Full Name", value="Sanjana Kushwah")
    mobile = st.text_input("Mobile Number (10 digits)", value="6261511249")
    email = st.text_input("Email ID", value="skushwah6261@gmail.com")
    pan = st.text_input("PAN Number (ABCDE1234F)", value="ABCDE1234F").upper()
    purpose = st.selectbox("Purpose of Loan", options=[
        "Debt Consolidation", "Home Renovation", "Medical Expenses", "Education", "Business", "Wedding",
        "Travel", "Vehicle Purchase", "Others"
    ], index=1)
    salary = st.number_input("Monthly Income (₹)", min_value=5000, max_value=2000000, value=60000, step=5000)
with col2:
    amount = st.number_input("Loan Amount (₹)", min_value=50000, max_value=5000000, value=200000, step=5000)
    tenure = st.selectbox("Tenure (Months)", options=[12, 24, 36, 48, 60, 72, 84], index=1)
    roi = st.number_input("Rate of Interest (%)", min_value=5.0, max_value=25.0, value=12.75, step=0.05)
    agree = st.checkbox("I agree to Terms & Conditions and authorize Capital Finance to check my credit score", value=False)

# Document upload
st.subheader("Upload ID / Address Proof (optional)")
uploaded_file = st.file_uploader("Upload JPG/PNG/PDF for OCR (optional)", type=["jpg", "jpeg", "png", "pdf"])
ocr_text = ""
if uploaded_file is not None:
    st.info("File uploaded. Attempting OCR (if available)...")
    ocr_text = try_ocr_extract_text(uploaded_file)
    st.text_area("OCR Extracted Text (best-effort)", value=ocr_text, height=160)
else:
    st.info("OCR is optional. If unavailable, this will not block PDF generation.")

# PAN quick indicator
if pan:
    if is_valid_pan(pan):
        st.success("PAN format looks valid.")
    else:
        st.error("PAN format invalid. Correct format: ABCDE1234F")

# Estimates & EMI
processing_fee_base = 1499
processing_fee = processing_fee_base + round(processing_fee_base * 0.18)
net_disbursed = max(int(amount - processing_fee), 0)
emi = calculate_emi(amount, roi, int(tenure))
st.markdown("---")
st.subheader("Estimate")
st.write(f"🔹 Estimated EMI: ₹{int(round(emi)):,} / month")
st.write(f"🔹 Processing Fee + GST: ₹{processing_fee:,}")
st.write(f"🔹 Net Disbursed (approx): ₹{net_disbursed:,}")

credit_score = compute_dummy_credit_score(salary, amount, is_valid_pan(pan))
st.write(f"🔸 Dummy Credit Risk Score: {credit_score} / 100")

# ---------- Generation button with robust validation ----------
st.markdown("---")
st.write("Click to generate your provisional sanction letter (PDF).")

def validate_inputs(name_val, mobile_val, email_val, agree_flag):
    errors = []
    name_clean = (name_val or "").strip()
    mobile_clean = clean_mobile(mobile_val or "")
    email_clean = (email_val or "").strip()

    if not name_clean:
        errors.append("Full Name")
    if not (mobile_clean and len(mobile_clean) == 10):
        errors.append("Mobile (10 digits)")
    if not (email_clean and "@" in email_clean and "." in email_clean.split("@")[-1]):
        errors.append("Valid Email")
    if not agree_flag:
        errors.append("Accept Terms & Conditions (checkbox)")
    return errors, name_clean, mobile_clean, email_clean

if st.button("Generate Sanction Letter PDF"):
    errs, name_clean, mobile_clean, email_clean = validate_inputs(name, mobile, email, agree)
    if errs:
        st.error("Please fix the following fields before generating the letter: " + ", ".join(errs))
    else:
        # Build applicant and loan_info dicts
        applicant = {
            "name": name_clean,
            "mobile": mobile_clean,
            "email": email_clean,
            "pan": pan.strip().upper()
        }
        loan_info = {
            "amount": int(amount),
            "roi": float(roi),
            "tenure": int(tenure),
            "emi": emi,
            "processing_fee": processing_fee,
            "net_disbursed": net_disbursed,
            "purpose": purpose,
            "credit_score": credit_score
        }

        # Prepare QR payload (short summary)
        qr_payload = (f"TATA|Applicant:{applicant['name']}|Mobile:{applicant['mobile']}|"
                      f"Loan:₹{loan_info['amount']:,}|Tenure:{loan_info['tenure']}m|EMI:₹{int(round(loan_info['emi'])):,}")
        qr_bio = generate_qr_image_bytes(qr_payload)

        # Build PDF bytes
        pdf_bytes = build_sanction_pdf(applicant, loan_info, qr_bio, pdf_title="TATA CAPITAL FINANCE – LOAN APPROVAL LETTER")

        # Offer download
        st.success("Sanction letter generated successfully ✅")
        st.download_button("⬇ Download Sanction Letter (PDF)", pdf_bytes, file_name="Sanction_Letter.pdf", mime="application/pdf")

        # Show QR preview and WhatsApp message + code of the share text
        st.image(qr_bio, caption="QR encoded sanction summary", width=180)

        wa_msg = (f"Hello, I ({applicant['name']}) have been provisionally sanctioned a loan of ₹{loan_info['amount']:,} "
                  f"for '{loan_info['purpose']}' with EMI ₹{int(round(loan_info['emi'])):,}/month for {loan_info['tenure']} months.")
        wa_link = make_whatsapp_link(wa_msg, phone_number="")  # generic
        st.markdown(f"*WhatsApp Share:* [Open WhatsApp]({wa_link})")
        st.code(wa_msg)

        # Email send option
        with st.expander("Send this sanction letter by email (optional)"):
            to_email = st.text_input("Recipient Email", value=applicant['email'])
            email_subject = st.text_input("Email Subject", value=f"Sanction Letter — TATA CAPITAL FINANCE — {applicant['name']}")
            email_body = st.text_area("Email Body", value=(f"Dear {applicant['name']},\n\nPlease find attached your provisional sanction letter.\n\nRegards,\nTata Capital Finance"))
            if st.button("Send Email Now"):
                if not (smtp_host and smtp_port and smtp_user and smtp_password):
                    st.error("Please fill SMTP details in the sidebar (host, port, user, password).")
                else:
                    sent_ok, sent_msg = send_email_smtp(smtp_host, int(smtp_port), smtp_user, smtp_password, to_email, email_subject, email_body, attachment_bytes=pdf_bytes, attachment_name="Sanction_Letter.pdf")
                    if sent_ok:
                        st.success(sent_msg)
                    else:
                        st.error(sent_msg)

# Footer close of card
st.markdown("</div>", unsafe_allow_html=True)

# Troubleshooting & notes
st.markdown("---")
st.markdown("""
*Notes & Troubleshooting*
- If OCR shows "not available", install pytesseract and the Tesseract binary on your machine.
- Email sending uses SMTP — for Gmail, use App Passwords if you have 2FA.
- The credit score is a placeholder/computational heuristic — replace with production underwriting for real use.
- QR encodes a short summary — do not include very sensitive data in the QR in production.
""")