# 📄 AI PDF Simplifier + Chat Assistant  
### Powered by Google Gemini 2.5 Flash — Built with Streamlit

This project is an AI-powered web application that simplifies complex PDF documents, generates structured notes, and lets users **chat directly with the PDF content**.

---

# 🚀 Live Demo
👉 **Streamlit App:** [pdf-guru-ai](https://pdf-guru-ai.streamlit.app/)  

---

# 🧠 Features

### ✅ PDF Upload  
Upload any text-based PDF. Clean text is extracted using `pdfplumber`.

### ✅ AI-Based Simplification  
Automatically generates:
- **Simplified Notes**
- **Bullet Points Summary**
- **Glossary Section**

### ✅ Chat With PDF  
Ask questions directly from the uploaded document:

AI answers using only the PDF content:
- **Paragraph format** for explanation-based questions  
- **Bullet points** for list-based questions  

### ✅ Downloadable Notes  
A neatly formatted PDF is generated using `reportlab`.

### ✅ Clean Modern UI  
Premium light theme with neumorphic cards.  
Fully mobile-responsive.

---

# 📦 Project Structure

```

AI-PDF-Simplifier/
│
├── app.py                     # Main Streamlit App
├── pdf_text_extractor.py      # Standalone PDF-to-Text tool
├── requirements.txt           # Python dependencies
├── README.md                  # Documentation
│
└── .streamlit/
└── config.toml          # Theme configuration (light mode)

````

---

# 🛠 Tech Stack

### **AI**
- Google Gemini 2.5 Flash  
- google-generativeai Python SDK  

### **Backend / Processing**
- Python  
- pdfplumber (PDF extraction)  
- reportlab (PDF generation)

### **Frontend**
- Streamlit  

### **Deployment**
- GitHub  
- Streamlit Cloud  
- Streamlit Secrets (API key protection)

---

# 📥 Installation & Running Locally

### **1. Clone the repository**
```bash
git clone [https://github.com/YOUR-USERNAME/AI-PDF-Simplifier.git](https://github.com/shashaank747/AI-PDF-Simplifier.git)
cd AI-PDF-Simplifier
````

---

### **2. Create a virtual environment (optional but recommended)**

#### **Windows**

```bash
python -m venv venv
venv\Scripts\activate
```

#### **Mac/Linux**

```bash
python3 -m venv venv
source venv/bin/activate
```

---

### **3. Install all dependencies**

```bash
pip install -r requirements.txt
```

---

### **4. Set your Gemini API key**

#### **Windows**

```bash
set GOOGLE_API_KEY=YOUR_API_KEY
```

#### **Mac/Linux**

```bash
export GOOGLE_API_KEY=YOUR_API_KEY
```

---

### **5. Run the application**

```bash
streamlit run app.py
```

---

# 🌐 Deployment Guide (Streamlit Cloud)

### **1. Push project to GitHub**

Upload these files:

* `app.py`
* `requirements.txt`
* `.streamlit/config.toml`
* `pdf_text_extractor.py`
* `README.md`

---

### **2. Go to Streamlit Cloud**

🔗 [https://share.streamlit.io](https://share.streamlit.io)

---

### **3. Create New App**

* Select GitHub repo
* Branch → `main`
* File → `app.py`

---

### **4. Add API Key via Streamlit Secrets**

Open:

```
Settings → Secrets → Add secret
```

Add:

```bash
GOOGLE_API_KEY="YOUR_API_KEY_HERE"
```

---

### **5. Deploy 🚀**

Your app will start in **10–20 seconds**.
A public link will be generated automatically.

---

# 🧪 How to Use

1. Upload a **non-scanned PDF**.
2. Click **✨ Simplify PDF** to generate:

   * Simplified notes
   * Bullet points
   * Glossary
3. Use **Chat With PDF** to ask questions.
4. Download your simplified notes as a PDF file.

---

# 🧰 Extra Tool Included: PDF Text Extractor

Standalone script for text extraction:

```
pdf_text_extractor.py
```

Run it locally:

```bash
python pdf_text_extractor.py
```

This extracts all text from any PDF and saves it as a **.txt** file.

---

# 📸 Screenshots (Optional)

Add images inside a `/screenshots` folder:

```markdown
![Upload Screen](screenshots/upload.png)
![Simplified Notes](screenshots/simplified.png)
![Chat Section](screenshots/chat.png)
```

---

# 🙌 Author

**Shashaank Sajjanar**

AI Developer & Student

---

# 📄 License

This project is open-source and free to use.


