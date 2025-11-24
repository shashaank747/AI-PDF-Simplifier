import os
import streamlit as st
import pdfplumber
import google.generativeai as genai
from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas
from io import BytesIO
import textwrap
import base64 # <-- FIX: Moved 'import base64' back to the top

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
if api_key:
    genai.configure(api_key=api_key)
else:
    # If key is missing, configure with a placeholder to prevent immediate crash 
    try:
        genai.configure(api_key="placeholder")
    except:
        pass


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
        # We assume the file object is already seeked to 0 before calling this function
        # But for robustness, we seek here too.
        uploaded_file.seek(0)
        with pdfplumber.open(uploaded_file) as pdf:
            for page in pdf.pages:
                content = page.extract_text()
                if content:
                    text += content + "\n"
        # Reset pointer for subsequent reads (like display or other functions)
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

# ---------------------- API KEY CHECK ----------------------
if not api_key:
    st.error("🚨 **API Key Missing!** Please set the `GOOGLE_API_KEY` in Streamlit secrets or as an environment variable to use the chat and simplification features.")

# ---------------------- FILE UPLOADER ----------------------
uploaded_file = st.file_uploader("Upload your PDF", type="pdf")

if uploaded_file:
    # Check if a new file was uploaded or if it's the first time
    if st.session_state.uploaded_file_obj is None or st.session_state.uploaded_file_obj.name != uploaded_file.name:

        st.session_state.uploaded_file_obj = uploaded_file
        text = extract_pdf_text(uploaded_file)
        st.session_state.raw_text = text

        st.success("PDF uploaded successfully!")

    # ---------------------- SIMPLIFY BUTTON ----------------------
    # Only enable simplify if API key is present
    if st.button("✨ Simplify PDF", disabled=not api_key):
        if not api_key:
             st.error("Cannot simplify: API Key is required.")
        else:
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
                    st.error(f"Error during simplification: {e}")

# ---------------------- LAYOUT: PREVIEW + CHAT ----------------------
col_pdf, col_chat = st.columns([2, 1])

# ---------------------- PDF PREVIEW (STABLE EMBED) ----------------------
with col_pdf:
    st.markdown("<div class='card'>", unsafe_allow_html=True)
    st.subheader("📝 Document Preview")

    if st.session_state.uploaded_file_obj:
        
        # Ensure the file pointer is at the beginning before reading the full file bytes
        st.session_state.uploaded_file_obj.seek(0)
        pdf_bytes = st.session_state.uploaded_file_obj.read()

        # Generate Base64 string
        base64_pdf = base64.b64encode(pdf_bytes).decode("utf-8")

        pdf_display = f"""
            <iframe src="data:application/pdf;base64,{base64_pdf}"
                     width="100%" height="800px" type="application/pdf">
            </iframe>
        """
        
        # Use st.components.v1.html for more robust embedding
        try:
             import streamlit.components.v1 as components
             components.html(pdf_display, height=800)
        except Exception as e:
             # This error is usually the Chrome block even for 1MB files if the
             # Streamlit server sends a slightly corrupt Base64 string.
             st.error(f"PDF Embed Error: {e}. If the PDF doesn't display, please try refreshing the page or using a different PDF file. (The file is only 1MB, so this is likely a browser/Streamlit rendering issue.)")


    else:
        st.info("Upload a PDF file to preview it.")

    st.markdown("</div>", unsafe_allow_html=True)


# ---------------------- CHAT WITH PDF ----------------------
with col_chat:
    st.markdown("<div class='card'>", unsafe_allow_html=True)
    st.subheader("💬 Chat With PDF")

    if not st.session_state.raw_text:
        st.warning("Upload a PDF first to enable chat.")

    # Disable chat components if API key is missing
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

            # --- USING THE ENHANCED CHAT PROMPT ---
            chat_prompt = f"""
You are an expert teacher and document summarizer. Your goal is to provide a comprehensive, educational, and high-quality answer to the user's question, strictly based on the provided PDF content.

**Answer Formatting Rules:**

1.  **Detail and Length:** Do not limit the length of your response. Provide a detailed answer that fully addresses the question.
2.  **Educational Style:** Use clear, simple language suitable for a student. Break down complex topics into digestible parts.
3.  **Structure (Mandatory):**
    * **Start** with a clear, concise introductory summary.
    * **Use bold subheadings** (e.g., **Key Features**, **In Simple Terms**, **Example**) to structure the body of your response.
    * **Use Markdown bullet points (-) or numbered lists (1.)** for any lists, types, steps, or features.
4.  **Analogy/Example:** For any concept or definition, actively try to provide a simple, real-world analogy or example to aid understanding.

**Source Constraint:**
- You MUST only use the PDF content provided below.
- Do NOT output headings like "Answer:" or similar.
- Do NOT copy messy formatting from the PDF.

PDF CONTENT:
{st.session_state.raw_text}

QUESTION:
{question}

If the answer is not found in the PDF, reply: 
"Sorry, this specific information is not available in the document you provided."
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
