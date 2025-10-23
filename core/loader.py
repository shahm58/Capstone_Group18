# core/loader.py
from pathlib import Path

# default input folder (no dependency on utils)
PDF_DIR = Path("data") / "pdfs"

def list_pdfs(folder: str | Path = PDF_DIR) -> list[Path]:
    folder = Path(folder)
    return sorted([p for p in folder.glob("*.pdf") if p.is_file()])
