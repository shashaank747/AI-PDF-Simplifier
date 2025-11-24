import os
import streamlit as st
import pdfplumber
import google.generativeai as genai
from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas
from io import BytesIO
import textwrap
import base64 

st.markdown("""
    <style>
        html, body, [data-testid="stAppViewContainer"], [data-testid="stHeader"] {
            background-color: #f4f7fb !important;
            color: #000 !important;
        }
    </style>
""", unsafe_allow_html=True)

# ----------------------------------------------
# CONFIG
# ----------------------------------------------
# NOTE: In a real environment, the API key should be securely loaded,
# e.g., using st.secrets or environment variables.
# Secure API Key Handling
api_key = ""

# 1. Use Streamlit Secrets in deployment
if "GOOGLE_API_KEY" in st.secrets:
    api_key = st.secrets["GOOGLE_API_KEY"]

# 2. Use environment variable in local development (optional)
elif os.environ.get("GOOGLE_API_KEY"):
    api_key = os.environ.get("GOOGLE_API_KEY")

# Configure Gemini
genai.configure(api_key=api_key)
 
MODEL_NAME = "models/gemini-2.5-flash"

st.set_page_config(
    page_title="AI PDF Simplifier + Chat",
    layout="wide", # <-- Changed layout to wide for better side-by-side view
    page_icon="📄"
)

# ----------------------------------------------
# Premium Light Theme (CSS)
# ----------------------------------------------
st.markdown("""
<style>
body, .main {
    background-color: #f4f7fb !important;
}

/* Ensure the main container takes full width when layout='wide' */
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

# ----------------------------------------------
# SESSION STATE FIXES
# ----------------------------------------------
if "raw_text" not in st.session_state:
    st.session_state.raw_text = ""

# Store the uploaded file object itself to use for the viewer
if "uploaded_file_obj" not in st.session_state:
    st.session_state.uploaded_file_obj = None

if "chat_answer" not in st.session_state:
    st.session_state.chat_answer = ""

# ----------------------------------------------
# PDF TEXT EXTRACTION
# ----------------------------------------------
def extract_pdf_text(uploaded_file):
    text = ""
    try:
        # Reset the pointer to the beginning of the file object before opening
        uploaded_file.seek(0)
        with pdfplumber.open(uploaded_file) as pdf:
            for page in pdf.pages:
                content = page.extract_text()
                if content:
                    text += content + "\n"
        # Reset the pointer again for Streamlit to handle the file display if needed
        uploaded_file.seek(0)
    except Exception as e:
        st.error(f"Error extracting text from PDF: {e}")
        return ""
    return text

# ----------------------------------------------
# PDF GENERATION
# ----------------------------------------------
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
        # Handle both Markdown list format ('- item') and simple line breaks
        list_items = [line.strip() for line in text.split("\n") if line.strip()]
        
        for item in list_items:
            # Clean up potential markdown list markers if present
            clean_item = item.lstrip("*- ").strip()
            
            wrapped = textwrap.wrap(clean_item, 95)
            
            # Start of the list item (indented)
            if y < 60:
                c.showPage()
                y = height - 50
            
            c.drawString(55, y, f"• {wrapped[0]}")
            y -= line_height
            
            # Subsequent lines for wrapped text (further indented)
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

# ----------------------------------------------
# TITLE & UPLOAD SECTION
# ----------------------------------------------

# Main title card
st.markdown("<div class='card'><h2 style='text-align:center;'>📄 AI PDF Simplifier + Chat</h2></div>", unsafe_allow_html=True)

# Upload section sits outside the main columns
uploaded_file = st.file_uploader("Upload your PDF", type="pdf")

if uploaded_file:
    # Check if a new file has been uploaded
    if st.session_state.uploaded_file_obj is None or st.session_state.uploaded_file_obj.name != uploaded_file.name:
        
        # Store the file object in session state
        st.session_state.uploaded_file_obj = uploaded_file

        # Extract text for RAG (Gemini)
        raw_text = extract_pdf_text(uploaded_file)
        st.session_state.raw_text = raw_text
        
        st.success("PDF uploaded successfully! You can now simplify or chat with the content.")

    # ------------------------------------------
    # Simplify Button (placed below upload, above columns)
    # ------------------------------------------
    if st.button("✨ Simplify PDF", key="simplify", help="Generate simplified notes", type="primary"):
        with st.spinner("Simplifying using Gemini..."):

            prompt = f"""
Read the PDF content below and rewrite it into EXACTLY THREE SECTIONS.

=== SECTION 1: SIMPLIFIED TEXT ===
Write 2–4 detailed paragraphs. The language should be simple, clear, and student-friendly.

=== SECTION 2: BULLET POINT SUMMARY ===
Write 5–10 comprehensive bullet points that cover the main topics.

=== SECTION 3: GLOSSARY ===
Create a list of 5–10 key terms from the document with short, clear definitions. Format each entry as:
**Term**: Meaning

PDF CONTENT:
{st.session_state.raw_text}
"""
            try:
                model = genai.GenerativeModel(MODEL_NAME)
                response = model.generate_content(prompt)
                output = response.text

                # CLEAN SPLITTING
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

                # Download PDF
                pdf_file = generate_pdf(simplified, bullets, glossary)
                st.download_button("📥 Download Simplified PDF", data=pdf_file, file_name="Simplified.pdf", mime="application/pdf")

            except Exception as e:
                st.error(f"An error occurred during simplification: {e}")

# ----------------------------------------------
# SIDE-BY-SIDE LAYOUT
# ----------------------------------------------

# Create two columns with PDF wider than the chat (2:1 ratio)
col_pdf, col_chat = st.columns([2, 1])

with col_pdf:
    # --- START: PDF PREVIEW SECTION ---
    st.markdown("<div class='card'>", unsafe_allow_html=True)
    st.subheader("📝 Document Preview")
    
    if st.session_state.uploaded_file_obj:
        # Read the file data into bytes for viewing
        st.session_state.uploaded_file_obj.seek(0)
        pdf_data_bytes = st.session_state.uploaded_file_obj.read()
        
        # Create a data URI for the iframe
        base64_pdf = base64.b64encode(pdf_data_bytes).decode('utf-8')
        # Increased height to 800px for a more prominent preview
        pdf_display = f'<iframe src="data:application/pdf;base64,{base64_pdf}" width="100%" height="800" type="application/pdf"></iframe>'
        
        st.markdown(pdf_display, unsafe_allow_html=True)
    else:
        st.info("Upload a PDF file to see its preview here.")
    st.markdown("</div>", unsafe_allow_html=True)
    # --- END: PDF PREVIEW SECTION ---

with col_chat:
    # ----------------------------------------------
    # CHAT WITH PDF
    # ----------------------------------------------
    st.markdown("<div class='card'>", unsafe_allow_html=True)
    st.subheader("💬 Chat With PDF")
    
    # Display a warning if no PDF text is loaded
    if not st.session_state.raw_text:
        st.warning("Upload a PDF file first to enable the chat feature.")

    question = st.text_input("Ask something about the PDF:", disabled=not st.session_state.raw_text)

    # Use nested columns for the buttons
    col1_chat, col2_chat = st.columns(2)
    with col1_chat:
        # Disable ask button if no raw text is present
        ask = st.button("Ask ✨", key="ask_button", disabled=not st.session_state.raw_text)
    with col2_chat:
        clear = st.button("Clear ❌", key="clear_button")

    if clear:
        st.session_state.chat_answer = ""
        st.rerun() 

    if ask and question.strip():
        if not st.session_state.raw_text:
            st.error("Please upload a PDF before asking a question.")
            ask = False # Prevent execution below
        
        if ask:
            with st.spinner("Thinking..."):
                model = genai.GenerativeModel(MODEL_NAME)

                # --- ENHANCED CHAT PROMPT ---
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
                    reply = model.generate_content(chat_prompt)
                    st.session_state.chat_answer = reply.text
                except Exception as e:
                    st.error(f"An error occurred while chatting with the model: {e}")


    if st.session_state.chat_answer:
        st.write("### 🧠 Answer:")
        # Use st.markdown for proper rendering of bolding and bullet points
        st.markdown(st.session_state.chat_answer)


    st.markdown("</div>", unsafe_allow_html=True)
