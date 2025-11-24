import os
import streamlit as st
import pdfplumber
import google.generativeai as genai
from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas
from io import BytesIO
import textwrap
import base64 # <-- FIX: Moved this import to the top

# ---------------------- PAGE THEME FIX ----------------------
st.markdown("""
    <style>
        html, body, [data-testid="stAppViewContainer"], [data-testid="stHeader"] {
            background-color: #f4f7fb !important;
            color: #000 !important;
        }
    </style>
""", unsafe_allow_html=True)

# ---------------------- API KEY HANDLING ----------------------
api_key = ""

# 1. Use Streamlit Secrets (deployment)
if "GOOGLE_API_KEY" in st.secrets:
    api_key = st.secrets["GOOGLE_API_KEY"]

# 2. Use local environment variable (testing)
elif os.environ.get("GOOGLE_API_KEY"):
    api_key = os.environ.get("GOOGLE_API_KEY")

# Configure Gemini
genai.configure(api_key=api_key)

MODEL_NAME = "models/gemini-2.5-flash"

st.set_page_config(
    page_title="AI PDF Simplifier + Chat",
    layout="wide",
    page_icon="📄"
)

# ---------------------- PREMIUM UI CSS ----------------------
st.markdown("""
<style>
body, .main {
    background-color: #f4f7fb !important;
}

.main .block-container {
    padding-left: 2rem;
    padding-right: 2rem;
}

.card {
    background: #ffffff;
    border-radius: 18px;
    padding: 25px;
    margin-top: 20px;
    box-shadow: 4px 4px 12px #d9d9d9, -4px -4px 12px #ffffff;
}

.neu-button {
    background: #ffffff !important;
    padding: 12px 28px !important;
    border-radius: 40px !important;
    border: none !important;
    box-shadow: 4px 4px 12px #d9d9d9, -4px -4px 12px #ffffff !important;
    font-weight: 600 !important;
    transition: 0.2s !important;
}
.neu-button:hover {
    box-shadow: inset 4px 4px 12px #d9d9d9, inset -4px -4px 12px #ffffff !important;
}

textarea, input {
    border-radius: 14px !important;
    padding: 10px !important;
    border: 1px solid #ccc !important;
}
</style>
""", unsafe_allow_html=True)

# ---------------------- SESSION STATE ----------------------
if "raw_text" not in st.session_state:
    st.session_state.raw_text = ""

if "uploaded_file_obj" not in st.session_state:
    st.session_state.uploaded_file_obj = None

if "chat_answer" not in st.session_state:
    st.session_state.chat_answer = ""

# ---------------------- PDF TEXT EXTRACTION ----------------------
def extract_pdf_text(uploaded_file):
    text = ""
    try:
        uploaded_file.seek(0)
        with pdfplumber.open(uploaded_file) as pdf:
            for page in pdf.pages:
                content = page.extract_text()
                if content:
                    text += content + "\n"
        uploaded_file.seek(0)
    except Exception as e:
        st.error(f"PDF extraction error: {e}")
        return ""
    return text

# ---------------------- PDF GENERATOR ----------------------
def generate_pdf(simplified, bullets, glossary):
    buffer = BytesIO()
    c = canvas.Canvas(buffer, pagesize=letter)

    width, height = letter
    y = height - 50
    line_height = 14

    def heading(text):
        nonlocal y
        c.setFont("Helvetica-Bold", 15)
        c.drawString(40, y, text)
        y -= 25

    def paragraph(text):
        nonlocal y
        c.setFont("Helvetica", 11)
        for line in textwrap.wrap(text, 100):
            if y < 60:
                c.showPage()
                y = height - 50
            c.drawString(40, y, line)
            y -= line_height
        y -= 10

    def bullet_list(text):
        nonlocal y
        c.setFont("Helvetica", 11)
        items = [line.strip() for line in text.split("\n") if line.strip()]
        for item in items:
            clean = item.lstrip("*- ").strip()
            wrapped = textwrap.wrap(clean, 95)

            if y < 60:
                c.showPage()
                y = height - 50

            c.drawString(55, y, f"• {wrapped[0]}")
            y -= line_height

            for sub in wrapped[1:]:
                if y < 60:
                    c.showPage()
                    y = height - 50
                c.drawString(75, y, sub)
                y -= line_height
        y -= 10

    heading("Simplified PDF Output")

    heading("1. Simplified Text")
    paragraph(simplified)

    heading("2. Bullet Points Summary")
    bullet_list(bullets)

    heading("3. Glossary")
    bullet_list(glossary)

    c.save()
    buffer.seek(0)
    return buffer

# ---------------------- TITLE ----------------------
st.markdown("<div class='card'><h2 style='text-align:center;'>📄 AI PDF Simplifier + Chat</h2></div>", unsafe_allow_html=True)

# ---------------------- FILE UPLOADER ----------------------
uploaded_file = st.file_uploader("Upload your PDF", type="pdf")

if uploaded_file:
    if st.session_state.uploaded_file_obj is None or st.session_state.uploaded_file_obj.name != uploaded_file.name:

        st.session_state.uploaded_file_obj = uploaded_file
        text = extract_pdf_text(uploaded_file)
        st.session_state.raw_text = text

        st.success("PDF uploaded successfully!")

    # ---------------------- SIMPLIFY BUTTON ----------------------
    if st.button("✨ Simplify PDF"):
        with st.spinner("Simplifying using Gemini..."):

            prompt = f"""
Rewrite the PDF content into EXACTLY THREE SECTIONS:

=== SECTION 1: SIMPLIFIED TEXT ===
Write 2–4 easy paragraphs.

=== SECTION 2: BULLET POINT SUMMARY ===
List 5–10 important bullet points.

=== SECTION 3: GLOSSARY ===
List 5–10 important terms with short meanings.

PDF CONTENT:
{st.session_state.raw_text}
"""

            try:
                model = genai.GenerativeModel(MODEL_NAME)
                response = model.generate_content(prompt)
                output = response.text

                simplified = output.split("=== SECTION 2")[0].replace("=== SECTION 1: SIMPLIFIED TEXT ===", "").strip()
                bullets = output.split("=== SECTION 2: BULLET POINT SUMMARY ===")[1].split("=== SECTION 3")[0].strip()
                glossary = output.split("=== SECTION 3: GLOSSARY ===")[1].strip()

                st.markdown("<div class='card'>", unsafe_allow_html=True)
                st.subheader("📘 Simplified Text")
                st.markdown(simplified)

                st.subheader("📌 Bullet Points")
                st.markdown(bullets)

                st.subheader("📚 Glossary")
                st.markdown(glossary)
                st.markdown("</div>", unsafe_allow_html=True)

                pdf_output = generate_pdf(simplified, bullets, glossary)
                st.download_button("📥 Download Simplified PDF", data=pdf_output, file_name="Simplified.pdf", mime="application/pdf")

            except Exception as e:
                st.error(f"Error: {e}")

# ---------------------- LAYOUT: PREVIEW + CHAT ----------------------
col_pdf, col_chat = st.columns([2, 1])

# ---------------------- PDF PREVIEW (Chrome Safe) ----------------------
with col_pdf:
    st.markdown("<div class='card'>", unsafe_allow_html=True)
    st.subheader("📝 Document Preview")

    if st.session_state.uploaded_file_obj:
        st.session_state.uploaded_file_obj.seek(0)
        pdf_bytes = st.session_state.uploaded_file_obj.read()

        # base64 import is now at the top of the file
        base64_pdf = base64.b64encode(pdf_bytes).decode("utf-8")

        # Using iframe tag, which is generally better supported than embed in Streamlit
        pdf_display = f'''
            <iframe src="data:application/pdf;base64,{base64_pdf}"
                     width="100%" height="800px" type="application/pdf">
            </iframe>
        '''

        st.markdown(pdf_display, unsafe_allow_html=True)

    else:
        st.info("Upload a PDF file to preview it.")

    st.markdown("</div>", unsafe_allow_html=True)


# ---------------------- CHAT WITH PDF ----------------------
with col_chat:
    st.markdown("<div class='card'>", unsafe_allow_html=True)
    st.subheader("💬 Chat With PDF")

    if not st.session_state.raw_text:
        st.warning("Upload a PDF first to enable chat.")

    question = st.text_input("Ask something about the PDF:", disabled=not st.session_state.raw_text)

    col1, col2 = st.columns(2)
    with col1:
        ask = st.button("Ask ✨", disabled=not st.session_state.raw_text)
    with col2:
        clear = st.button("Clear ❌")

    if clear:
        st.session_state.chat_answer = ""
        st.rerun()

    if ask and question.strip():
        with st.spinner("Thinking..."):

            chat_prompt = f"""
You are an expert teacher. Answer using ONLY the PDF content.

RULES:
- If the question asks to "explain", "describe", "tell about", "what is":
    → Write a simple paragraph (4–6 sentences).
- If the question asks for "list", "features", "advantages", "types", "difference":
    → Answer ONLY in bullet points.
- No headings. No long essays.

PDF CONTENT:
{st.session_state.raw_text}

QUESTION:
{question}

If not found in the PDF, reply:
"Sorry, this information is not available in the PDF."
"""

            try:
                model = genai.GenerativeModel(MODEL_NAME)
                response = model.generate_content(chat_prompt)
                st.session_state.chat_answer = response.text
            except Exception as e:
                st.error(f"Chat error: {e}")

    if st.session_state.chat_answer:
        st.write("### 🧠 Answer:")
        st.markdown(st.session_state.chat_answer)

    st.markdown("</div>", unsafe_allow_html=True)
