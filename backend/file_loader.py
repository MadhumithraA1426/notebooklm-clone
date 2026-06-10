from pypdf import PdfReader
from docx import Document


def load_pdf(file_path):
    text = ""

    reader = PdfReader(file_path)

    for page in reader.pages:
        page_text = page.extract_text()

        if page_text:
            text += page_text + "\n"

    return text


def load_docx(file_path):
    doc = Document(file_path)

    text = "\n".join(
        para.text for para in doc.paragraphs
    )

    return text


def load_txt(file_path):
    with open(file_path, "r", encoding="utf-8") as f:
        return f.read()