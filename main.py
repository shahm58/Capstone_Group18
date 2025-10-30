# main.py
from pathlib import Path
from core.loader import list_pdfs
from core.extractor import extract_text, extract_tables
from core.cleaner import clean_text
from core.storage import save_raw_text, save_clean_text, save_tables_as_csv
from core.utils import ts, LOGS_DIR
import csv

# --------------------
# Save run log
# --------------------
def save_run_log(results: list[dict]):
    log_file = LOGS_DIR / "run_log.csv"
    file_exists = log_file.exists()

    with open(log_file, "a", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)

        # Write header if file is new
        if not file_exists:
            writer.writerow([
                "file", "method", "pages", "chars", "clean_chars",
                "is_blank", "tables", "timestamp"
            ])

        for r in results:
            writer.writerow([
                r["file"],
                r["method"],
                r["pages"],
                r["chars"],
                r["clean_chars"],
                r["is_blank"],
                r["tables"],
                ts()
            ])

# --------------------
# Process One: Scraping
# --------------------
def process_one(pdf_path: Path) -> dict:
    print(f"\n→ Processing: {pdf_path.name}")

    info = extract_text(pdf_path)
    print(f"   text: method={info['method']} pages={info['pages']} chars={info['chars']}")
    # Extracts the contents from the PDF and displays method, pages, and char count

    raw_text = info["text"]
    save_raw_text(pdf_path, raw_text, {
        "source_file": str(pdf_path),
        "extracted_at": ts(),
        "method": info["method"],
        "pages": info["pages"],
        "chars": info["chars"],
    })
    # Saves raw extracted text + metadata

    cleaned = clean_text(raw_text)
    save_clean_text(pdf_path, cleaned)
    print(f"   clean: chars={len(cleaned)} blank={len(cleaned.strip()) == 0}")
    # Cleans text and prints cleaned char count

    tables = extract_tables(pdf_path)
    print(f"   tables detected: {len(tables)}")
    n_tables = save_tables_as_csv(pdf_path, tables)
    print(f"   tables saved: {n_tables}")
    # Detects and saves tables

    return {
        "file": pdf_path.name,                # PDF name
        "method": info["method"],              # Extraction method
        "pages": info["pages"],                # Total pages
        "chars": info["chars"],                # Raw character count
        "clean_chars": len(cleaned),           # Cleaned character count
        "is_blank": len(cleaned.strip()) == 0, # Blank text flag
        "tables": n_tables                     # Tables saved
    }
    # Returns processing summary

# --------------------
# Main Function
# --------------------
def main():
    print("PDF Processor starting …")

    pdfs = list_pdfs()
    print(f"Found {len(pdfs)} PDF(s) in data/pdfs")

    if not pdfs:
        print("No PDFs found in data/pdfs/. Drop files there and rerun.")
        return
    # Loads and lists PDFs in directory

    results = []
    for p in pdfs:
        try:
            res = process_one(p)
            results.append(res)  # add this result to list for logging
        except Exception as e:
            print(f"✗ {p.name} failed: {e}")
    # Process each PDF & collect results

    blanks = sum(1 for r in results if r["is_blank"])
    print(f"\nDone. {len(results)} file(s) processed. {blanks} blank/likely scanned.")
    # Summary

    # ✅ Save logs only if results exist
    if results:
        save_run_log(results)
        print(f"✓ Run logged to {LOGS_DIR / 'run_log.csv'}")
    else:
        print("⚠️ No results to log.")

# --------------------
# Execute
# --------------------
if __name__ == "__main__":
    main()
