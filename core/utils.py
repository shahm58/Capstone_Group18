# core/utils.py
from pathlib import Path
from datetime import datetime

# -----------------------------------------------------------
# PATH SETUP
# -----------------------------------------------------------

# Always resolve paths relative to the project root
ROOT_DIR = Path(__file__).resolve().parents[1]
DATA_DIR = ROOT_DIR / "data"

PDF_DIR = DATA_DIR / "pdfs"
EXTRACTED_DIR = DATA_DIR / "extracted"
CLEANED_DIR = DATA_DIR / "cleaned"
OUTPUT_DIR = DATA_DIR / "output"
LOGS_DIR = DATA_DIR / "logs"

# Create all necessary directories if they don’t exist
for p in [PDF_DIR, EXTRACTED_DIR, CLEANED_DIR, OUTPUT_DIR, LOGS_DIR]:
    p.mkdir(parents=True, exist_ok=True)

# -----------------------------------------------------------
# UTILITY FUNCTIONS
# -----------------------------------------------------------

def ts() -> str:
    """
    Return a Windows-safe timestamp for filenames.
    Example: 2025-11-11_15-22-07
    """
    return datetime.now().strftime("%Y-%m-%d_%H-%M-%S")


def stem_safe(pdf_path: Path) -> str:
    """
    Generate a safe file stem (base name without extension) for a PDF.
    Example:
        Input:  data/pdfs/RBC-2024-sustainability-report.pdf
        Output: RBC-2024-sustainability-report
    """
    return pdf_path.stem.replace(" ", "_").replace(":", "_")
