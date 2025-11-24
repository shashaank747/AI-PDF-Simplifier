import pdfplumber
import os

def extract_pdf_text(file_path):
    """
    Extracts text from a PDF file using pdfplumber.
    Returns the extracted text as a string.
    """
    text = ""
    try:
        with pdfplumber.open(file_path) as pdf:
            for page in pdf.pages:
                content = page.extract_text()
                if content:
                    text += content + "\n"
    except Exception as e:
        print(f"Error extracting text from PDF: {e}")
        return None
    return text


if __name__ == "__main__":
    print("=== PDF TEXT EXTRACTOR ===")
    file_path = input("Enter the path to your PDF file: ")

    if not os.path.exists(file_path):
        print("❌ File not found. Please check the path.")
        exit()

    text = extract_pdf_text(file_path)

    if text is None:
        print("❌ Could not extract text.")
        exit()

    # Save extracted text
    output_file = os.path.splitext(file_path)[0] + "_extracted.txt"

    try:
        with open(output_file, "w", encoding="utf-8") as f:
            f.write(text)
        print(f"✅ Text successfully saved to: {output_file}")
    except Exception as e:
        print(f"Error saving text file: {e}")

    # Preview
    print("\n--- Preview (first 500 characters) ---")
    preview = text[:500].strip()
    if len(text) > 500:
        preview += "..."
    print(preview)
    print("\nDone!")
