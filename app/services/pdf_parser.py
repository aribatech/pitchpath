import pdfplumber
from fastapi import UploadFile
import tempfile
import os


async def extract_text_from_pdf(file: UploadFile) -> str:
    content = await file.read()
    with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as tmp:
        tmp.write(content)
        tmp_path = tmp.name

    try:
        text_parts = []
        with pdfplumber.open(tmp_path) as pdf:
            for page in pdf.pages:
                page_text = page.extract_text()
                if page_text:
                    text_parts.append(page_text)
        return "\n".join(text_parts)
    finally:
        os.unlink(tmp_path)
