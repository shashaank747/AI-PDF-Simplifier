import os
import streamlit as st
import pdfplumber
import google.generativeai as genai
import fitz  # PyMuPDF for PDF → image
from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas
from io import BytesIO
import textwrap
import base64

# ---------------------- THEME ----------------------
st.set_page_config(page_title="AI PDF Simplifier + Chat", layout="wide", page_icon="📄")

st.markdown("""
<style>
body, .main { background-color: #f4f7fb !important; }
.card {
    background: #ffffff; border-radius: 18px; padding: 25px; margin-top: 20px;
    box-shadow: 4px 4px 12px #d9d9d9, -4px -4px 12px #ffffff;
}
textarea, input { border-radius: 14px !important; padding: 10px !important; border: 1px solid #ccc !important; }
</style>
""", unsafe_allow_html=True)

# ---------------------- API KEY ----------------------
api_key = ""

if "GOOGLE_API_KEY" in st.secrets:
    api_key = st.secrets["GOOGLE_API_KEY"]
elif os.environ.get("GOOGLE_API_KEY"):
    api_key = os.environ.get("GOOGLE_API_KEY")

if api_key:
    genai.configure(api_key=api_key)
else:
    st.error("🚨 API key missing! Add GOOGLE_API_KEY in Streamlit Secrets.")
    st.stop()

MODEL_TEXT = "models/gemini-2.5-flash"
MODEL_VISION = "models/gemini-2.0-flash"

# ---------------------- STATE ----------------------
if "raw_text" not in st.session_state:
    st.session_state.raw_text = ""
if "chat_answer" not in st.session_state:
    st.session_state.chat_answer = ""
if "uploaded_file_obj" not in st.session_state:
    st.session_state.uploaded_file_obj = None

# ---------------------- OCR ENGINE (GEMINI VISION) ----------------------
def ocr_with_gemini(image_bytes):
    model = genai.GenerativeModel(MODEL_VISION)
    try:
        response = model.generate_content(["Extract all readable text from this image:", image_bytes])
        return response.text
    except:
        return ""

def extract_scanned_pdf_text(uploaded_file):
    """Convert PDF pages → images → Gemini Vision OCR"""
    text = ""
    pdf_bytes = uploaded_file.read()
    doc = fitz.open(stream=pdf_bytes, filetype="pdf")

    for page_num in range(len(doc)):
        page = doc.load_page(page_num)
        pix = page.get_pixmap(dpi=200)
        img_bytes = pix.tobytes("png")
        ocr_text = ocr_with_gemini(img_bytes)
        text += ocr_text + "\n"

    uploaded_file.seek(0)
    return text

# ---------------------- DIGITAL PDF TEXT ----------------------
def extract_digital_text(uploaded_file):
    try:
        uploaded_file.seek(0)
        text = ""
        with pdfplumber.open(uploaded_file) as pdf:
            for page in pdf.pages:
                c = page.extract_text()
                if c: text += c + "\n"
        uploaded_file.seek(0)
        return text
    except:
        return ""

# ---------------------- AUTO-DETECT PDF TYPE ----------------------
def extract_pdf_text(uploaded_file):
    """First try digital extraction → if empty → use OCR"""
    digital_text = extract_digital_text(uploaded_file)
    if len(digital_text.strip()) > 50:
        return digital_text
    return extract_scanned_pdf_text(uploaded_file)

# ---------------------- PDF OUTPUT ----------------------
def generate_pdf(bullets):
    buffer = BytesIO()
    c = canvas.Canvas(buffer, pagesize=letter)
    width, height = letter
    y = height - 50
    line_height = 14

    c.setFont("Helvetica-Bold", 16)
    c.drawString(40, y, "AI Generated PDF Summary")
    y -= 30

    c.setFont("Helvetica", 12)
    for point in bullets.split("\n"):
        wrapped = textwrap.wrap(point, 95)
        for line in wrapped:
            if y < 60:
                c.showPage()
                y = height - 50
            c.drawString(40, y, f"• {line}")
            y -= line_height
        y -= 5

    c.save()
    buffer.seek(0)
    return buffer

# ---------------------- UI ----------------------
st.markdown("<div class='card'><h2 style='text-align:center;'>📄 AI PDF Simplifier + Chat</h2></div>", unsafe_allow_html=True)

uploaded_file = st.file_uploader("Upload your PDF", type="pdf")

if uploaded_file:
    st.session_state.uploaded_file_obj = uploaded_file

    with st.spinner("Extracting text (Auto-detecting: Digital / Scanned / Handwritten)..."):
        st.session_state.raw_text = extract_pdf_text(uploaded_file)

    st.success("PDF processed successfully!")

    # ---------------------- SUMMARY BUTTON ----------------------
    if st.button("✨ Generate Detailed Bullet Summary"):
        with st.spinner("Summarizing PDF..."):
            prompt = f"""
Create a detailed bullet-point summary of the following PDF content.
Rules:
- Each bullet should be 2–3 lines long
- Cover every important idea
- No headings, no sections
- Only bullet points

PDF CONTENT:
{st.session_state.raw_text}
"""

            model = genai.GenerativeModel(MODEL_TEXT)
            response = model.generate_content(prompt)
            bullets = response.text

            st.markdown("<div class='card'>", unsafe_allow_html=True)
            st.subheader("📌 Summary")
            st.markdown(bullets)
            st.markdown("</div>", unsafe_allow_html=True)

            pdf_output = generate_pdf(bullets)
            st.download_button("📥 Download Summary PDF", pdf_output, "Summary.pdf", "application/pdf")

# ---------------------- PREVIEW ----------------------
col_pdf, col_chat = st.columns([2, 1])

with col_pdf:
    st.markdown("<div class='card'>", unsafe_allow_html=True)
    st.subheader("📝 PDF Preview")

    if st.session_state.uploaded_file_obj:
        st.session_state.uploaded_file_obj.seek(0)
        pdf_bytes = st.session_state.uploaded_file_obj.read()
        b64 = base64.b64encode(pdf_bytes).decode()
        st.markdown(f"""<iframe src="data:application/pdf;base64,{b64}" width="100%" height="800px"></iframe>""", unsafe_allow_html=True)
    else:
        st.info("Upload a PDF to preview it.")

    st.markdown("</div>", unsafe_allow_html=True)

# ---------------------- CHAT ----------------------
with col_chat:
    st.markdown("<div class='card'>", unsafe_allow_html=True)
    st.subheader("💬 Chat With PDF")

    q = st.text_input("Ask a question about the PDF:")

    if st.button("Ask"):
        with st.spinner("Thinking..."):
            chat_prompt = f"""
Answer the question ONLY using the PDF content.

Rules:
- If the question asks to explain → give 4–6 sentence paragraph
- If the question asks to list → use bullet points only
- No extra info outside the PDF

PDF CONTENT:
{st.session_state.raw_text}

QUESTION:
{q}
"""

            model = genai.GenerativeModel(MODEL_TEXT)
            response = model.generate_content(chat_prompt)
            st.session_state.chat_answer = response.text

    if st.session_state.chat_answer:
        st.write("### 🧠 Answer:")
        st.markdown(st.session_state.chat_answer)

    st.markdown("</div>", unsafe_allow_html=True)
