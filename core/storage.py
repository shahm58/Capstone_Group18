# core/storage.py
from pathlib import Path
import json
from .utils import EXTRACTED_DIR, CLEANED_DIR, stem_safe

def save_raw_text(pdf_path: Path, text: str, meta: dict) -> Path:
    base = stem_safe(pdf_path)
    out_txt = EXTRACTED_DIR / f"{base}.txt"
    out_meta = EXTRACTED_DIR / f"{base}.json"
    out_txt.write_text(text or "", encoding="utf-8", errors="ignore")
    out_meta.write_text(json.dumps(meta, ensure_ascii=False, indent=2), encoding="utf-8")
    return out_txt

def save_clean_text(pdf_path: Path, text: str) -> Path:
    base = stem_safe(pdf_path)
    out_txt = CLEANED_DIR / f"{base}.txt"
    out_txt.write_text(text or "", encoding="utf-8", errors="ignore")
    return out_txt
