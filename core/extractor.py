from pathlib import Path
import json
import pdfplumber
import fitz  # PyMuPDF

def _extract_text_pdfplumber(pdf_path: Path) -> str:
    text_parts = []
    with pdfplumber.open(pdf_path) as pdf:
        for page in pdf.pages:
            text_parts.append(page.extract_text() or "")
    return "\n".join(text_parts).strip()

def _fast_text_pymupdf(pdf_path: Path) -> str:
    text_parts = []
    with fitz.open(pdf_path) as doc:
        for page in doc:
            text_parts.append(page.get_text() or "")
    return "\n".join(text_parts).strip()

def extract_text(pdf_path: Path) -> dict:
    """
    Returns dict with: {"text": str, "method": "pdfplumber"|"pymupdf", "chars": int, "pages": int}
    """
    # Try pdfplumber first (often cleaner line breaks), fallback to PyMuPDF
    text = _extract_text_pdfplumber(pdf_path)
    method = "pdfplumber"
    if len(text.strip()) == 0:
        text = _fast_text_pymupdf(pdf_path)
        method = "pymupdf"

    # Basic metadata
    pages = 0
    try:
        with fitz.open(pdf_path) as doc:
            pages = len(doc)
    except Exception:
        pass

    return {
        "text": text,
        "method": method,
        "chars": len(text),
        "pages": pages,
    }
