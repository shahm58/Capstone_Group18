import re

def clean_text(raw: str) -> str:
    if not raw:
        return ""
    # Remove excessive blank lines and trailing spaces
    txt = re.sub(r"[ \t]+", " ", raw)
    txt = re.sub(r"\n{3,}", "\n\n", txt)
    # Optional: remove common page headers/footers numbers
    txt = re.sub(r"\n?\s*-?\s*Page \d+\s*-?\s*\n?", "\n", txt, flags=re.IGNORECASE)
    txt = txt.strip()
    return txt
