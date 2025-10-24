# main.py
from pathlib import Path
from core.loader import list_pdfs
from core.extractor import extract_text, extract_tables
from core.cleaner import clean_text
from core.storage import save_raw_text, save_clean_text, save_tables_as_csv
from core.utils import ts

# --------------------
# Process One: Scraping
# --------------------
def process_one(pdf_path: Path) -> dict:
    print(f"\n→ Processing: {pdf_path.name}")

    info = extract_text(pdf_path)
    print(f"   text: method={info['method']} pages={info['pages']} chars={info['chars']}")
    # Extracts the contents from the PDF and puts them in a dictionary
    # Prints the method, pages and number of chars in the pdf

    raw_text = info["text"]
    save_raw_text(pdf_path, raw_text, {
        "source_file": str(pdf_path),
        "extracted_at": ts(),
        "method": info["method"],
        "pages": info["pages"],
        "chars": info["chars"],
    })
    # Saves the raw text from the PDF in the extractor folder

    cleaned = clean_text(raw_text)
    save_clean_text(pdf_path, cleaned)
    print(f"   clean: chars={len(cleaned)} blank={len(cleaned.strip()) == 0}")
    # Cleans the raw extracted data and saves it to the cleaned folder
    # Prints how many charcters were cleaned

    tables = extract_tables(pdf_path)
    print(f"   tables detected: {len(tables)}")
    # Extracts and prints the number of tables within the PDF
    n_tables = save_tables_as_csv(pdf_path, tables)
    print(f"   tables saved: {n_tables}")
    # Saves those extracted tables into a CSV file

    return {
        "file": str(pdf_path.name),             # PDF name
        "method": info["method"],               # Extraction method used
        "pages": info["pages"],                 # Total pages
        "chars": info["chars"],                 # Number of raw characters
        "clean_chars": len(cleaned),            # Numbe of cleaned characters
        "is_blank": len(cleaned.strip()) == 0,  # True if text was blank
        "tables": n_tables                      # Number of tables saved
    }
    # Return function for the summary dictionary about the processed PDF


# --------------------
# Function: Main
# --------------------
def main():
    print("PDF Processor starting …")

    pdfs = list_pdfs()
    print(f"Found {len(pdfs)} PDF(s) in data/pdfs")

    if not pdfs:
        print("No PDFs found in data/pdfs/. Drop files there and rerun.")
        return
    # Finds and lists PDFs within the directory

    results = []
    for p in pdfs:
        try:
            res = process_one(p) 
            results.append(res) # Scraping is done and results are returned
        except Exception as e:
            print(f"✗ {p.name} failed: {e}")
    # For all the PDFs within the dir, process one is done
    # If any error occurs print which file failed but continue in processing other PDFs

    blanks = sum(1 for r in results if r["is_blank"])
    print(f"\nDone. {len(results)} file(s) processed. {blanks} blank/likely scanned.")
    # Summarize how many PDFs were processed and how many of them were blank

if __name__ == "__main__":
    main()
