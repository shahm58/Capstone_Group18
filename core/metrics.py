# core/metrics.py
import re
from typing import Dict, Optional

# very simple number pattern (e.g., 12,345.67)
NUMBER = r"(-?\d[\d,]*\.?\d*)"

# we'll look for these units near the values (not strict; just to reduce random matches)
UNITS = r"(tCO2e|tonnes CO2e|tons CO2e|t CO2e|metric tons CO2e|MtCO2e|ktCO2e)?"

SCOPE_1_PATTERN = re.compile(r"scope\s*1[^0-9\-+]*" + NUMBER + r"\s*" + UNITS,
                             re.IGNORECASE)
SCOPE_2_PATTERN = re.compile(r"scope\s*2[^0-9\-+]*" + NUMBER + r"\s*" + UNITS,
                             re.IGNORECASE)

def extract_scope_metrics(text: str) -> Dict[str, Optional[str]]:
    """
    Super basic Bronze-level extractor:
    - Scan cleaned text for the first occurrence of 'Scope 1' and 'Scope 2'
      followed by a number (and optional unit).
    - Return them as plain strings.
    """
    if not text:
        return {"Scope 1": None, "Scope 2": None}

    scope1 = None
    scope2 = None

    m1 = SCOPE_1_PATTERN.search(text)
    if m1:
        scope1 = m1.group(1)  # captured number

    m2 = SCOPE_2_PATTERN.search(text)
    if m2:
        scope2 = m2.group(1)

    return {"Scope 1": scope1, "Scope 2": scope2}
