# core/utils.py
from pathlib import Path
from datetime import datetime

DATA_DIR = Path("data")
PDF_DIR = DATA_DIR / "pdfs"
EXTRACTED_DIR = DATA_DIR / "extracted"
CLEANED_DIR = DATA_DIR / "cleaned"
OUTPUT_DIR = DATA_DIR / "output"
LOGS_DIR = DATA_DIR / "logs"

# make sure folders exist
for d in [PDF_DIR, EXTRACTED_DIR, CLEANED_DIR, OUTPUT_DIR, LOGS_DIR]:
    d.mkdir(parents=True, exist_ok=True)

def ts() -> str:
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")

def stem_safe(path: Path) -> str:
    return path.stem[:120]
