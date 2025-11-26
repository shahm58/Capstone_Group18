# core/extractor.py
from pathlib import Path
import fitz  # PyMuPDF
import pdfplumber
import pandas as pd
import re

_digit_re = re.compile(r"\d")

def _digit_ratio(s: str) -> float:
    if not s:
        return 0.0
    s = str(s)
    digits = sum(ch.isdigit() for ch in s)
    return digits / max(len(s), 1)

def _is_table_like(df: pd.DataFrame, min_cols=3, min_rows=2, min_digit_ratio=0.15) -> bool:
    if df is None or df.shape[0] < min_rows or df.shape[1] < min_cols:
        return False
    df = df.dropna(how="all").dropna(axis=1, how="all")
    if df.shape[0] < min_rows or df.shape[1] < min_cols:
        return False

    sample = df.astype(str).stack().tolist()
    if not sample:
        return False
    sample = sample[:200]
    ratio = sum(_digit_re.search(x) is not None for x in sample) / len(sample)
    avg_len = sum(len(x.strip()) for x in sample) / len(sample)
    return (ratio >= min_digit_ratio) and (avg_len >= 2)


def _text_via_pdfplumber(pdf_path: Path) -> str:
    parts = []
    with pdfplumber.open(pdf_path) as pdf:
        for page in pdf.pages:
            txt = page.extract_text(x_tolerance=2, y_tolerance=2) or ""
            parts.append(txt)
    return "\n".join(parts).strip()


def _text_via_pymupdf_words(pdf_path: Path) -> str:
    lines_out = []
    with fitz.open(pdf_path) as doc:
        for page in doc:
            words = page.get_text("words")
            lines = {}
            for (x0, y0, x1, y1, w, block, line, wno) in words:
                lines.setdefault((block, line), []).append((x0, w))
            for key in sorted(lines.keys()):
                items = sorted(lines[key], key=lambda t: t[0])
                text_line = " ".join(w for _, w in items).strip()
                if text_line:
                    lines_out.append(text_line)
            lines_out.append("")
    return "\n".join(lines_out).strip()


def extract_text(pdf_path: Path) -> dict:
    """
    Extracts text from a PDF using pdfplumber first; if fragmented, uses PyMuPDF.
    Returns a dict with keys: text, method, chars, pages.
    """
    text = _text_via_pdfplumber(pdf_path)
    method = "pdfplumber"

    def looks_fragmented(s: str) -> bool:
        lines = [ln for ln in s.splitlines() if ln.strip()]
        if not lines:
            return True
        short = sum(1 for ln in lines if len(ln.strip()) <= 2)
        return (short / len(lines)) > 0.25

    if looks_fragmented(text):
        text = _text_via_pymupdf_words(pdf_path)
        method = "pymupdf_words"

    pages = 0
    try:
        with fitz.open(pdf_path) as doc:
            pages = len(doc)
    except Exception:
        pass

    return {"text": text, "method": method, "chars": len(text), "pages": pages}


# ---------------- TABLES ----------------
def _tables_via_pdfplumber(pdf_path: Path) -> list[dict]:
    """
    Returns: list of dicts: {"page": int, "index": int, "df": pandas.DataFrame}
    Strategy: try line-based detection first; then a text-based fallback.
    """
    out: list[dict] = []
    with pdfplumber.open(pdf_path) as pdf:
        for pageno, page in enumerate(pdf.pages, start=1):
            # 1) Lines strategy (good for ruled tables)
            try:
                tbls = page.find_tables(
                    table_settings={
                        "vertical_strategy": "lines",
                        "horizontal_strategy": "lines",
                        "intersection_x_tolerance": 5,
                        "intersection_y_tolerance": 5,
                    }
                ) or []
            except Exception:
                tbls = []

            # If none detected, fallback to text-based extraction
            if not tbls:
                try:
                    tbls = page.find_tables(
                        table_settings={
                            "vertical_strategy": "text",
                            "horizontal_strategy": "text",
                            "text_x_tolerance": 3,
                            "text_y_tolerance": 3,
                        }
                    ) or []
                except Exception:
                    tbls = []

            for idx, tbl in enumerate(tbls, start=1):
                data = tbl.extract() or []
                if not data or all((not any(row) for row in data)):
                    continue
                df = pd.DataFrame(data)

                # Heuristic: if first row looks like headers, set as columns
                if not df.empty:
                    first = df.iloc[0]
                    non_null = first[first.notna()].astype(str)
                    if len(non_null) >= 2 and len(non_null.unique()) == len(non_null):
                        df.columns = df.iloc[0]
                        df = df[1:].reset_index(drop=True)

                df = df.dropna(how="all").dropna(axis=1, how="all")
                if df.shape[0] == 0 or df.shape[1] == 0:
                    continue

                if not _is_table_like(df):
                    continue

                out.append({"page": pageno, "index": idx, "df": df})
    return out


def _tables_via_camelot(pdf_path: Path) -> list[dict]:
    """
    Optional: uses Camelot if installed (better on many financial PDFs).
    """
    try:
        import camelot  # type: ignore
    except Exception:
        return []

    out: list[dict] = []
    for flavor in ("lattice", "stream"):
        try:
            tables = camelot.read_pdf(str(pdf_path), pages="all", flavor=flavor)
            for i, t in enumerate(tables, start=1):
                df = t.df
                df = df.dropna(how="all").dropna(axis=1, how="all")
                if df.shape[0] and df.shape[1]:
                    page_no = t.parsing_report.get("page", None)
                if not _is_table_like(df):
                    continue

                out.append({"page": page_no or -1, "index": i, "df": df})
            if out:
                break
        except Exception:
            continue
    return out


def extract_tables(pdf_path: Path) -> list[dict]:
    """
    Returns list of {"page": int, "index": int, "df": DataFrame}.
    Order: pdfplumber first; if nothing found and Camelot installed, use Camelot.
    """
    tables = _tables_via_pdfplumber(pdf_path)
    if not tables:
        camelot_tbls = _tables_via_camelot(pdf_path)
        if camelot_tbls:
            tables = camelot_tbls
    return tables


# --------------------------------------------------------------
# ✅ Wrapper functions for main.py compatibility
# --------------------------------------------------------------

def extract_text_from_pdf(pdf_path: Path):
    """
    Wrapper around extract_text() so main.py can import this safely.
    Returns (text, info_dict)
    """
    result = extract_text(pdf_path)
    return result["text"], {
        "method": result["method"],
        "chars": result["chars"],
        "pages": result["pages"],
    }


def extract_tables_from_pdf(pdf_path: Path):
    """
    Wrapper around extract_tables() so main.py can import this safely.
    """
    return extract_tables(pdf_path)

# ADD THIS NEW FUNCTION TO RETURN TEXT PER PAGE
def extract_text_by_page(pdf_path: Path) -> list[str]:
    """
    Extracts text page-by-page.
    Returns a list of strings, where index 0 is Page 1, etc.
    """
    pages_text = []
    
    # Try pdfplumber first (better layout preservation)
    try:
        with pdfplumber.open(pdf_path) as pdf:
            for page in pdf.pages:
                txt = page.extract_text(x_tolerance=2, y_tolerance=2) or ""
                pages_text.append(txt)
    except Exception:
        pages_text = []

    # If pdfplumber failed or returned empty strings, try PyMuPDF
    if not pages_text or all(not p.strip() for p in pages_text):
        pages_text = []
        with fitz.open(pdf_path) as doc:
            for page in doc:
                # "blocks" is usually better than "words" for keeping lines together
                text = page.get_text("text") 
                pages_text.append(text)
                
    return pages_text
