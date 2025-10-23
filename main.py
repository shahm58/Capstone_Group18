# main.py
from pathlib import Path
from core.loader import list_pdfs
from core.extractor import extract_text, extract_tables
from core.cleaner import clean_text
from core.storage import save_raw_text, save_clean_text, save_tables_as_csv
from core.utils import ts

def process_one(pdf_path: Path) -> dict:
    print(f"\n→ Processing: {pdf_path.name}")

    info = extract_text(pdf_path)
    print(f"   text: method={info['method']} pages={info['pages']} chars={info['chars']}")

    raw_text = info["text"]
    save_raw_text(pdf_path, raw_text, {
        "source_file": str(pdf_path),
        "extracted_at": ts(),
        "method": info["method"],
        "pages": info["pages"],
        "chars": info["chars"],
    })

    cleaned = clean_text(raw_text)
    save_clean_text(pdf_path, cleaned)
    print(f"   clean: chars={len(cleaned)} blank={len(cleaned.strip()) == 0}")

    tables = extract_tables(pdf_path)
    print(f"   tables detected: {len(tables)}")
    n_tables = save_tables_as_csv(pdf_path, tables)
    print(f"   tables saved: {n_tables}")

    return {
        "file": str(pdf_path.name),
        "method": info["method"],
        "pages": info["pages"],
        "chars": info["chars"],
        "clean_chars": len(cleaned),
        "is_blank": len(cleaned.strip()) == 0,
        "tables": n_tables
    }

def main():
    print("PDF Processor starting …")
    pdfs = list_pdfs()
    print(f"Found {len(pdfs)} PDF(s) in data/pdfs")

    if not pdfs:
        print("No PDFs found in data/pdfs/. Drop files there and rerun.")
        return

    results = []
    for p in pdfs:
        try:
            res = process_one(p)
            results.append(res)
        except Exception as e:
            print(f"✗ {p.name} failed: {e}")

    blanks = sum(1 for r in results if r["is_blank"])
    print(f"\nDone. {len(results)} file(s) processed. {blanks} blank/likely scanned.")

if __name__ == "__main__":
    main()
