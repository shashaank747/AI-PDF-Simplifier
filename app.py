# app.py - AI PDF Simplifier + Chat (with robust OCR fallback)
# Requirements (pip):
# pip install streamlit pdfplumber google-genai reportlab pytesseract pdf2image pillow
# System-level (required):
# - Tesseract OCR installed and in PATH (https://github.com/tesseract-ocr/tesseract)
# - Poppler installed (for pdf2image) and in PATH (https://poppler.freedesktop.org/)
# Notes: On Windows install Tesseract and Poppler and set environment PATH.

import os
import io
import math
import streamlit as st
import pdfplumber
import google.generativeai as genai
from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas
from io import BytesIO
import textwrap
import base64
from pdf2image import convert_from_bytes
import pytesseract
from PIL import Image, ImageOps, ImageFilter

# ---------------------- CONFIG / NOTES ----------------------
# Put your Gemini API key in Streamlit Secrets as GOOGLE_API_KEY for deployment
api_key = ""
if "GOOGLE_API_KEY" in st.secrets:
    api_key = st.secrets["GOOGLE_API_KEY"]
elif os.environ.get("GOOGLE_API_KEY"):
    api_key = os.environ.get("GOOGLE_API_KEY")

if api_key:
    try:
        genai.configure(api_key=api_key)
    except Exception:
        pass

MODEL_NAME = "models/gemini-2.5-flash"

st.set_page_config(page_title="AI PDF Simplifier + Chat (OCR)", layout="wide", page_icon="📄")

# ---------------------- CSS ----------------------
st.markdown("""
<style>
body, .main { background-color: #f4f7fb !important; }
.main .block-container { padding-left: 2rem; padding-right: 2rem; }
.card { background: #ffffff; border-radius: 18px; padding: 20px; margin-top: 16px; box-shadow: 4px 4px 12px #d9d9d9, -4px -4px 12px #ffffff; }
textarea, input { border-radius: 12px !important; padding: 8px !important; border: 1px solid #ccc !important; }
</style>
""", unsafe_allow_html=True)

# ---------------------- SESSION STATE ----------------------
if "raw_text" not in st.session_state:
    st.session_state.raw_text = ""
if "uploaded_file_obj" not in st.session_state:
    st.session_state.uploaded_file_obj = None
if "chat_answer" not in st.session_state:
    st.session_state.chat_answer = ""

# ---------------------- OCR + Extraction Utilities ----------------------

def ocr_image(img: Image.Image) -> str:
    """Run OCR on a PIL Image with mild preprocessing to improve recognition."""
    try:
        # Convert to grayscale
        img_gray = img.convert("L")
        # Auto-contrast
        img_ac = ImageOps.autocontrast(img_gray)
        # Slight blur to reduce noise then sharpen could help; apply only if big image
        img_filtered = img_ac.filter(ImageFilter.MedianFilter(size=3))
        text = pytesseract.image_to_string(img_filtered, lang=None)
        return text
    except Exception as e:
        st.warning(f"OCR image error: {e}")
        return ""


def ocr_from_pdf_bytes(pdf_bytes: bytes, max_pages=50) -> str:
    """Convert PDF bytes to images and OCR them. Limit pages to avoid memory blowups."""
    try:
        # convert_from_bytes returns list of PIL images
        # Use dpi 300 for decent OCR accuracy
        pil_images = convert_from_bytes(pdf_bytes, dpi=300)
    except Exception as e:
        st.error(f"pdf2image conversion error: {e}")
        return ""

    texts = []
    total = len(pil_images)
    limit = min(total, max_pages)
    for i, img in enumerate(pil_images[:limit]):
        st.info(f"Running OCR on page {i+1}/{limit}...")
        page_text = ocr_image(img)
        texts.append(page_text)
    return "\n".join(texts)


# ---------------------- Robust PDF text extraction ----------------------

def extract_pdf_text(uploaded_file) -> str:
    """Try native text extraction first (pdfplumber). If result is too short, fall back to OCR."""
    try:
        uploaded_file.seek(0)
        text = ""
        try:
            with pdfplumber.open(uploaded_file) as pdf:
                for page in pdf.pages:
                    try:
                        content = page.extract_text()
                        if content:
                            text += content + "\n"
                    except Exception:
                        # continue if one page fails
                        continue
        except Exception as e:
            # pdfplumber could fail on some scanned-only PDFs; continue to OCR
            text = ""

        # If pdfplumber returned very little text, use OCR
        if len(text.strip()) < 80:
            # read raw bytes and perform OCR
            uploaded_file.seek(0)
            pdf_bytes = uploaded_file.read()
            ocr_text = ocr_from_pdf_bytes(pdf_bytes, max_pages=50)
            if len(ocr_text.strip()) > 0:
                return ocr_text
            else:
                # fallback to whatever pdfplumber gave (even if empty)
                return text
        else:
            return text

    except Exception as e:
        st.error(f"PDF extraction error: {e}")
        return ""


# ---------------------- PDF summary generator (writes summary into PDF) ----------------------

def generate_pdf(summary_text: str) -> BytesIO:
    buffer = BytesIO()
    c = canvas.Canvas(buffer, pagesize=letter)
    width, height = letter
    y = height - 50
    line_height = 14

    c.setFont("Helvetica-Bold", 14)
    c.drawString(40, y, "AI Summary")
    y -= 28
    c.setFont("Helvetica", 11)

    for paragraph in summary_text.split("\n"):
        if not paragraph.strip():
            y -= 6
            continue
        wrapped = textwrap.wrap(paragraph, 95)
        for line in wrapped:
            if y < 60:
                c.showPage()
                y = height - 50
                c.setFont("Helvetica", 11)
            c.drawString(40, y, line)
            y -= line_height
        y -= 6

    c.save()
    buffer.seek(0)
    return buffer


# ---------------------- UI: Title & Upload ----------------------
st.markdown("<div class='card'><h2 style='text-align:center;'>📄 AI PDF Simplifier + Chat (OCR-enabled)</h2></div>", unsafe_allow_html=True)

if not api_key:
    st.error("🚨 API Key Missing! Please add GOOGLE_API_KEY in Streamlit Secrets or set environment variable.")

uploaded_file = st.file_uploader("Upload your PDF (scanned or digital)", type=["pdf"]) 

if uploaded_file:
    # If newly uploaded, extract text and store
    if st.session_state.uploaded_file_obj is None or st.session_state.uploaded_file_obj.name != uploaded_file.name:
        st.session_state.uploaded_file_obj = uploaded_file
        with st.spinner("Extracting text (pdfplumber → OCR fallback)..."):
            extracted = extract_pdf_text(uploaded_file)
            st.session_state.raw_text = extracted
        if st.session_state.raw_text.strip():
            st.success("Text extracted from PDF (ready for summarization/chat)")
        else:
            st.warning("No text could be extracted from this PDF (OCR may have failed). Check image quality or try a clearer scan.")

# ---------------------- Simplify (Bullet Summary only) ----------------------
if uploaded_file and st.session_state.raw_text:
    if st.button("✨ Simplify PDF (Bullet summary)", disabled=not api_key):
        if not api_key:
            st.error("Cannot summarize: API Key missing.")
        else:
            with st.spinner("Generating bullet summary..."):
                prompt = f"""
Create a detailed bullet-point summary from the PDF content below.

RULES:
- Use '-' for each bullet point.
- Each bullet must be 2–3 lines long.
- No headings, no sections, no numbering.
- Only include information present in the PDF.

PDF CONTENT:
{st.session_state.raw_text}
"""
                try:
                    model = genai.GenerativeModel(MODEL_NAME)
                    resp = model.generate_content(prompt)
                    summary = resp.text.strip()
                    if not summary:
                        summary = "Summary not available from the model."

                    st.markdown("<div class='card'>", unsafe_allow_html=True)
                    st.subheader("📌 Detailed Summary (Bullet points)")
                    st.markdown(summary)
                    st.markdown("</div>", unsafe_allow_html=True)

                    # Offer download
                    pdf_buf = generate_pdf(summary)
                    st.download_button("📥 Download Summary PDF", data=pdf_buf, file_name="summary.pdf", mime="application/pdf")

                except Exception as e:
                    st.error(f"Error during summarization: {e}")

# ---------------------- Layout: Preview + Chat ----------------------
col_pdf, col_chat = st.columns([2, 1])

with col_pdf:
    st.markdown("<div class='card'>", unsafe_allow_html=True)
    st.subheader("📝 Document Preview")
    if st.session_state.uploaded_file_obj:
        try:
            st.session_state.uploaded_file_obj.seek(0)
            pdf_bytes = st.session_state.uploaded_file_obj.read()
            base64_pdf = base64.b64encode(pdf_bytes).decode('utf-8')
            embed = f"<iframe src=\"data:application/pdf;base64,{base64_pdf}\" width=\"100%\" height=800></iframe>"
            st.components.v1.html(embed, height=800)
        except Exception as e:
            st.warning(f"Could not render preview: {e}")
    else:
        st.info("Upload a PDF to preview it.")
    st.markdown("</div>", unsafe_allow_html=True)

with col_chat:
    st.markdown("<div class='card'>", unsafe_allow_html=True)
    st.subheader("💬 Chat With PDF")

    if not st.session_state.raw_text:
        st.warning("Upload a PDF and ensure text extraction completed to enable chat.")

    chat_disabled = not st.session_state.raw_text or not api_key
    question = st.text_input("Ask something about the PDF:", disabled=chat_disabled)

    col1, col2 = st.columns(2)
    with col1:
        ask = st.button("Ask ✨", disabled=chat_disabled)
    with col2:
        clear = st.button("Clear ❌")

    if clear:
        st.session_state.chat_answer = ""
        st.rerun()

    if ask and question.strip():
        with st.spinner("Thinking..."):
            chat_prompt = f"""
Answer the user's question ONLY using the PDF content below.

RULES:
- If the question asks to explain/describe/what is → return a short paragraph (4–6 sentences).
- If the question asks to list/features/types/advantages → answer ONLY in bullet points.
- Do NOT add information not present in the PDF.

PDF CONTENT:
{st.session_state.raw_text}

QUESTION:
{question}

If the answer is not in the PDF, reply with exactly:
"Sorry, this information is not available in the PDF."
"""
            try:
                model = genai.GenerativeModel(MODEL_NAME)
                resp = model.generate_content(chat_prompt)
                st.session_state.chat_answer = resp.text
            except Exception as e:
                st.error(f"Chat error: {e}")

    if st.session_state.chat_answer:
        st.write("### 🧠 Answer:")
        st.markdown(st.session_state.chat_answer)

    st.markdown("</div>", unsafe_allow_html=True)

# ---------------------- End ----------------------

# Helpful reminder for the user
st.markdown("""
**Notes & Troubleshooting**
- For best OCR results: upload clear, high-resolution scans (>= 300 DPI) with dark ink on light background.
- If OCR fails on messy handwriting, try re-scanning with better lighting or typing a digital copy.
- Ensure Tesseract and Poppler are installed on the host machine (required by pytesseract & pdf2image).
""")
