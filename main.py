from pathlib import Path
from core.loader import list_pdfs
from core.extractor import extract_text
from core.cleaner import clean_text
from core.storage import save_raw_text, save_clean_text
from core.utils import ts

def process_one(pdf_path: Path) -> dict:
    info = extract_text(pdf_path)
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
    return {
        "file": str(pdf_path.name),
        "method": info["method"],
        "pages": info["pages"],
        "chars": info["chars"],
        "clean_chars": len(cleaned),
        "is_blank": len(cleaned.strip()) == 0
    }

def main():
    pdfs = list_pdfs()
    if not pdfs:
        print("No PDFs found in data/pdfs/. Drop files there and rerun.")
        return
    results = []
    print(f"Found {len(pdfs)} PDF(s). Processing...")
    for p in pdfs:
        try:
            res = process_one(p)
            results.append(res)
            print(f"✓ {p.name} | {res['pages']} pages | {res['method']} | {res['clean_chars']} chars")
        except Exception as e:
            print(f"✗ {p.name} failed: {e}")

    # simple run summary
    blanks = sum(1 for r in results if r["is_blank"])
    print(f"\nDone. {len(results)} file(s) processed. {blanks} blank/likely scanned.")

if __name__ == "__main__":
    main()
