"""
Main entry point for Capstone Group 18 Sustainability Report Extractor
---------------------------------------------------------------------
This script orchestrates the full pipeline:
  1. Loads all PDF reports from data/pdfs/
  2. Extracts text and tables using the extractor module
  3. Cleans and preprocesses text using the cleaner module
  4. Saves intermediate data using the storage module
  5. Extracts basic Scope 1 and Scope 2 metrics (Bronze-level)
  6. Outputs summary CSVs for verification
"""
import json
from core.ai import run_ai_for_document
import csv
from pathlib import Path
from datetime import datetime

# Core modules
from core.loader import list_pdfs
from core.extractor import extract_text_from_pdf, extract_tables_from_pdf, extract_text_by_page # <--- IMPORT NEW FUNCTION
from core.cleaner import clean_text
from core.storage import save_raw_text, save_clean_text, save_tables_as_csv
from core.metrics import extract_scope_metrics  # ✅ NEW: import rule-based metric extractor
from core.utils import LOGS_DIR, OUTPUT_DIR, ts

# -----------------------------------------------------------
# Utility Functions
# -----------------------------------------------------------

def save_run_log(results: list[dict]):
    """
    Saves a detailed log of all processed files (PDF name, extraction status, etc.)
    This ensures traceability and quick debugging.
    """
    log_path = LOGS_DIR / f"run_log_{ts()}.csv"
    with open(log_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=results[0].keys())
        writer.writeheader()
        writer.writerows(results)
    print(f"✓ Run log saved: {log_path}")


def save_scope_summary(results: list[dict]):
    """
    Create/append to data/output/scope_summary.csv with:
    file, scope1, scope2
    This is your Bronze-level deliverable file showing extracted metrics.
    """

    # 🟡 Debugging information to trace the issue
    print(f"[DEBUG] save_scope_summary() called with {len(results)} results")
    if len(results) > 0:
        print(f"[DEBUG] Keys in first result: {list(results[0].keys())}")

    summary_path = OUTPUT_DIR / "scope_summary.csv"
    print(f"[DEBUG] Writing to: {summary_path.resolve()}")

    file_exists = summary_path.exists()

    with open(summary_path, "a", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        if not file_exists:
            writer.writerow(["file", "scope1", "scope2"])
        for r in results:
            writer.writerow([
                r["file"],
                r.get("scope1"),
                r.get("scope2"),
            ])
    print(f"✓ Scope summary saved to {summary_path}")


# -----------------------------------------------------------
# Core Processing
# -----------------------------------------------------------

def process_one(pdf_path: Path):
    """
    Orchestrates the full extraction process for a single PDF file.
    """
    print(f"\n🚀 Processing {pdf_path.name} ...")

    # 1. Extract text
    text, info = extract_text_from_pdf(pdf_path)
    print(f"   • Extracted text ({info['pages']} pages, {info['chars']} chars)")

    # 2. Clean text
    cleaned = clean_text(text)
    
    # 3. Save raw + cleaned
    save_raw_text(pdf_path, text)
    save_clean_text(pdf_path, cleaned)

    # 4. Extract tables
    tables = extract_tables_from_pdf(pdf_path)
    n_tables = len(tables)
    save_tables_as_csv(pdf_path, tables)
    print(f"   • Extracted and saved {n_tables} tables")

    # 5. Prepare JSON for AI (CORRECTED STRUCTURE)
    extracted_dir = Path("data/extracted")
    extracted_dir.mkdir(parents=True, exist_ok=True)
    extracted_json_path = extracted_dir / f"{pdf_path.stem}.json"

    # Get text page-by-page
    raw_pages = extract_text_by_page(pdf_path)
    
    pages_payload = []
    for i, page_text in enumerate(raw_pages):
        # Basic cleaning for the AI input
        lines = [ln.strip() for ln in page_text.splitlines() if ln.strip()]
        if not lines: 
            continue
            
        pages_payload.append({
            "page": i + 1,
            "lines": lines,
            # We leave tables empty or minimal since you confirmed they are garbage
            "tables": [] 
        })

    extracted_payload = {"pages": pages_payload}

    with open(extracted_json_path, "w", encoding="utf-8") as f:
        json.dump(extracted_payload, f, ensure_ascii=False, indent=2)

    # 6. Run AI and CAPTURE the results
    scope1 = None
    scope2 = None
    ai_metrics_count = 0

    try:
        print("   • 🤖 Invoking AI extraction...")
        ai_result = run_ai_for_document(pdf_path.stem, extracted_json_path)
        metrics = ai_result.get("metrics", [])
        ai_metrics_count = len(metrics)
        
        # Extract Scope 1
        s1 = next((m for m in metrics if m["name"] == "Scope 1"), None)
        if s1: scope1 = s1["value"]

        # Extract Scope 2 (Prefer Market, then Location)
        s2 = next((m for m in metrics if m["name"] == "Scope 2 (market)"), None)
        if not s2:
            s2 = next((m for m in metrics if m["name"] == "Scope 2 (location)"), None)
        if s2: scope2 = s2["value"]

        print(f"   • AI found: Scope 1={scope1}, Scope 2={scope2}")

    except Exception as e:
        print(f"   • AI step failed: {e}")

    # 7. Fallback to Regex ONLY if AI failed (Optional - currently disabled to prevent bad data)
    if scope1 is None and scope2 is None:
        print("   • AI found no metrics. Skipping regex fallback to avoid false positives.")
        # If you really want regex fallback, uncomment below:
        # scope = extract_scope_metrics(cleaned)
        # scope1 = scope.get("Scope 1")
        # scope2 = scope.get("Scope 2")

    return {
        "file": pdf_path.name,
        "method": info["method"],
        "pages": info["pages"],
        "chars": info["chars"],
        "clean_chars": len(cleaned),
        "is_blank": len(cleaned.strip()) == 0,
        "tables": n_tables,
        "scope1": scope1,
        "scope2": scope2,
        "ai_metrics": ai_metrics_count,
    }


def main():
    """
    Main function: runs pipeline for all PDFs under data/pdfs/
    Generates:
      - Cleaned text files
      - Extracted tables
      - Scope summary CSV (Bronze)
      - Run log CSV
    """
    print("\n===============================")
    print(" CAPSTONE GROUP 18: PDF Extractor ")
    print("===============================")
    print(f"Run started at {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")

    pdfs = list_pdfs()
    if not pdfs:
        print("⚠️ No PDFs found in data/pdfs/. Please add your sustainability reports first.")
        return

    results = []
    for pdf in pdfs:
        try:
            res = process_one(pdf)
            results.append(res)
        except Exception as e:
            print(f"❌ Failed to process {pdf.name}: {e}")
            results.append({
                "file": pdf.name,
                "method": "error",
                "pages": 0,
                "chars": 0,
                "clean_chars": 0,
                "is_blank": True,
                "tables": 0,
                "scope1": None,
                "scope2": None,
            })

    if results:
        print(f"\n[DEBUG] Results collected: {len(results)} items")
        print(f"[DEBUG] Example entry keys: {list(results[0].keys())}")

        save_run_log(results)
        save_scope_summary(results)

        print(f"\n✅ All processing complete. {len(results)} files processed.")
        print(f"   Logs: {LOGS_DIR}")
        print(f"   Outputs: {OUTPUT_DIR}")
        print("   You can now open scope_summary.csv to view extracted metrics.")


if __name__ == "__main__":
    main()
