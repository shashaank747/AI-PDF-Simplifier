import os
import streamlit as st
import pdfplumber
import google.generativeai as genai
from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas
from io import BytesIO
import textwrap
import base64

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

if "GOOGLE_API_KEY" in st.secrets:
    api_key = st.secrets["GOOGLE_API_KEY"]
elif os.environ.get("GOOGLE_API_KEY"):
    api_key = os.environ.get("GOOGLE_API_KEY")

if api_key:
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
body, .main { background-color: #f4f7fb !important; }
.main .block-container { padding-left: 2rem; padding-right: 2rem; }
.card {
    background: #ffffff;
    border-radius: 18px;
    padding: 25px;
    margin-top: 20px;
    box-shadow: 4px 4px 12px #d9d9d9, -4px -4px 12px #ffffff;
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
def generate_pdf(summary):
    buffer = BytesIO()
    c = canvas.Canvas(buffer, pagesize=letter)

    width, height = letter
    y = height - 50
    line_height = 14

    c.setFont("Helvetica-Bold", 16)
    c.drawString(40, y, "PDF Summary")
    y -= 30

    c.setFont("Helvetica", 11)

    for line in summary.split("\n"):
        wrap = textwrap.wrap(line, 95)
        for w in wrap:
            if y < 60:
                c.showPage()
                y = height - 50
                c.setFont("Helvetica", 11)
            c.drawString(40, y, w)
            y -= line_height
        y -= 5

    c.save()
    buffer.seek(0)
    return buffer


# ---------------------- TITLE ----------------------
st.markdown("<div class='card'><h2 style='text-align:center;'>📄 AI PDF Simplifier + Chat</h2></div>", unsafe_allow_html=True)

if not api_key:
    st.error("🚨 API Key Missing! Add GOOGLE_API_KEY in Streamlit Secrets.")

# ---------------------- FILE UPLOADER ----------------------
uploaded_file = st.file_uploader("Upload your PDF", type="pdf")

if uploaded_file:
    if st.session_state.uploaded_file_obj is None or st.session_state.uploaded_file_obj.name != uploaded_file.name:

        st.session_state.uploaded_file_obj = uploaded_file
        st.session_state.raw_text = extract_pdf_text(uploaded_file)

        st.success("PDF uploaded successfully!")

    # ---------------------- SIMPLIFY BUTTON ----------------------
    if st.button("✨ Simplify PDF", disabled=not api_key):
        with st.spinner("Summarizing using Gemini..."):

            prompt = f"""
Generate a detailed summary of this PDF in PURE BULLET POINTS ONLY.

RULES:
- Use "-" for every bullet.
- Each bullet MUST be 2–3 lines long.
- No headings.
- No sections.
- No numbering.
- Only use content from the PDF.

PDF CONTENT:
{st.session_state.raw_text}
"""

            try:
                model = genai.GenerativeModel(MODEL_NAME)
                output = model.generate_content(prompt)
                summary = output.text.strip()

                st.markdown("<div class='card'>", unsafe_allow_html=True)
                st.subheader("📌 Detailed Summary")
                st.markdown(summary)
                st.markdown("</div>", unsafe_allow_html=True)

                # PDF Download
                pdf_file = generate_pdf(summary)
                st.download_button(
                    "📥 Download Summary PDF",
                    data=pdf_file,
                    file_name="PDF_Summary.pdf",
                    mime="application/pdf"
                )

            except Exception as e:
                st.error(f"Error during summarization: {e}")

# ---------------------- LAYOUT: PREVIEW + CHAT ----------------------
col_pdf, col_chat = st.columns([2, 1])

# ---------------------- PDF PREVIEW ----------------------
with col_pdf:
    st.markdown("<div class='card'>", unsafe_allow_html=True)
    st.subheader("📝 Document Preview")

    if st.session_state.uploaded_file_obj:
        st.session_state.uploaded_file_obj.seek(0)
        pdf_bytes = st.session_state.uploaded_file_obj.read()
        base64_pdf = base64.b64encode(pdf_bytes).decode("utf-8")

        embed = f"""
        <iframe src="data:application/pdf;base64,{base64_pdf}"
                width="100%" height="800px">
        </iframe>
        """

        st.components.v1.html(embed, height=800)

    else:
        st.info("Upload a PDF to preview.")

    st.markdown("</div>", unsafe_allow_html=True)

# ---------------------- CHAT WITH PDF ----------------------
with col_chat:
    st.markdown("<div class='card'>", unsafe_allow_html=True)
    st.subheader("💬 Chat With PDF")

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
Answer the user's question ONLY using the PDF content.

RULES:
- If question is "Explain / Describe / What is": give a short paragraph.
- If question is "List / Features / Types / Advantages": answer ONLY in bullet points.
- No extra information outside the PDF.

PDF CONTENT:
{st.session_state.raw_text}

QUESTION:
{question}

If answer not found in the PDF:
"Sorry, this information is not available in the PDF."
"""

            try:
                model = genai.GenerativeModel(MODEL_NAME)
                result = model.generate_content(chat_prompt)
                st.session_state.chat_answer = result.text

            except Exception as e:
                st.error(f"Chat error: {e}")

    if st.session_state.chat_answer:
        st.write("### 🧠 Answer:")
        st.markdown(st.session_state.chat_answer)

    st.markdown("</div>", unsafe_allow_html=True)
