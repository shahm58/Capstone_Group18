# core/storage.py
from pathlib import Path
from typing import List, Dict
import json
import csv
from .utils import EXTRACTED_DIR, CLEANED_DIR, OUTPUT_DIR, stem_safe

# -----------------------------------------------------------
# RAW TEXT + METADATA
# -----------------------------------------------------------
def save_raw_text(pdf_path: Path, text: str, meta: dict = None) -> Path:
    """
    Write raw extracted text and a metadata JSON next to it.
    If meta is not provided, creates an empty JSON placeholder.
    """
    base = stem_safe(pdf_path)
    out_txt = EXTRACTED_DIR / f"{base}.txt"
    out_meta = EXTRACTED_DIR / f"{base}.json"

    # Write raw text
    out_txt.write_text(text or "", encoding="utf-8", errors="ignore")

    # If meta provided, write it; otherwise create an empty file
    if meta:
        out_meta.write_text(json.dumps(meta, ensure_ascii=False, indent=2), encoding="utf-8")
    else:
        out_meta.write_text("{}", encoding="utf-8")

    return out_txt


# -----------------------------------------------------------
# CLEANED TEXT
# -----------------------------------------------------------
def save_clean_text(pdf_path: Path, text: str) -> Path:
    """
    Write cleaned text output for downstream processing.
    """
    base = stem_safe(pdf_path)
    out_txt = CLEANED_DIR / f"{base}.txt"
    out_txt.write_text(text or "", encoding="utf-8", errors="ignore")
    return out_txt


# -----------------------------------------------------------
# TABLES
# -----------------------------------------------------------
def save_tables_as_csv(pdf_path: Path, tables: List[Dict]) -> int:
    """
    Save each table DataFrame to CSV:
      data/output/<pdf_stem>/tables/table_p<page>_<idx>.csv
    Returns number of tables saved.
    """
    base = stem_safe(pdf_path)
    out_dir = OUTPUT_DIR / base / "tables"
    out_dir.mkdir(parents=True, exist_ok=True)

    count = 0
    for t in tables:
        page = t.get("page", -1)
        idx = t.get("index", 1)
        df = t.get("df")
        if df is not None:
            out_csv = out_dir / f"table_p{page}_{idx}.csv"
            df.to_csv(out_csv, index=False)
            count += 1
    return count

# -----------------------------------------------------------
# VALIDATED ESG REPORTS
# -----------------------------------------------------------
class StorageManager:
    def __init__(self, output_dir: Path = OUTPUT_DIR):
        self.output_dir = output_dir
        self.output_dir.mkdir(parents=True, exist_ok=True)

    def save_json(self, report_dict: dict, filename: str) -> Path:
        """
        Save a validated ESG report dict as JSON.
        """
        out_path = self.output_dir / f"{filename}.json"
        out_path.write_text(json.dumps(report_dict, ensure_ascii=False, indent=2), encoding="utf-8")
        return out_path

    def save_csv(self, report_dict: dict, filename: str) -> Path:
        """
        Flatten and save a validated ESG report as CSV for easier analysis.
        Only saves top-level metrics.
        """
        out_path = self.output_dir / f"{filename}.csv"
        metrics = report_dict.get("metrics", {})
        row = {
            "company_name": report_dict.get("company_name", ""),
            "report_year": report_dict.get("report_year", ""),
            **metrics
        }

        # Write CSV
        with out_path.open("w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=row.keys())
            writer.writeheader()
            writer.writerow(row)
        return out_path
