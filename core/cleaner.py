# core/cleaner.py
import re

def clean_text(raw: str) -> str:
    if not raw:
        return ""

    txt = raw

    # Join lines that were broken mid-paragraph (single char then next line)
    # Safe rule: if a line ends with no punctuation and next line is lowercase, merge.
    txt = re.sub(r"(?<![.\?!:])\n(?=[a-z0-9])", " ", txt)

    # Normalise bullet lines like "• something"
    # - collapse isolated bullet lines ("•\ntext" -> "• text")
    txt = re.sub(r"\n?^\s*•\s*\n\s*", "\n• ", txt, flags=re.MULTILINE)

    # Collapse multiple spaces/tabs
    txt = re.sub(r"[ \t]+", " ", txt)

    # Collapse 3+ blank lines to 2
    txt = re.sub(r"\n{3,}", "\n\n", txt)

    # Remove common page labels like "Page 12"
    txt = re.sub(r"\n?\s*-?\s*Page\s+\d+\s*-?\s*\n?", "\n", txt, flags=re.IGNORECASE)

    return txt.strip()
