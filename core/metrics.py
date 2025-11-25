# core/metrics.py
import re
from typing import Dict, Optional, List
import pandas as pd

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

# ============================================================
# NEW FUNCTIONALITY (TABLE EXTRACTION + NUMBER CLEANING)
# ============================================================

# Clean numeric strings like "12,345" → 12345.0
def safe_float(value) -> Optional[float]:
    if value is None:
        return None
    if isinstance(value, (int, float)):
        return float(value)
    try:
        cleaned = str(value).replace(",", "").strip()
        return float(cleaned)
    except:
        return None


# Extract the FIRST number in a row
def extract_number_from_row(row) -> Optional[float]:
    for item in row:
        # Try raw numeric
        if isinstance(item, (int, float)):
            return float(item)

        if isinstance(item, str):
            cleaned = item.replace(",", "")
            match = re.search(r"-?\d+(\.\d+)?", cleaned)
            if match:
                try:
                    return float(match.group())
                except:
                    pass
    return None


# Detect and extract Scope 1 & 2 from table dataframes
def extract_scope_from_tables(tables: List[Dict]) -> (Optional[float], Optional[float]):
    scope1 = None
    scope2 = None

    for t in tables:
        df = t.get("df")
        if df is None:
            continue

        # Normalize to lowercase strings
        df = df.astype(str).apply(lambda col: col.str.lower())

        # Look for Scope 1 rows
        mask1 = df.apply(lambda row: row.str.contains("scope 1").any(), axis=1)
        if mask1.any():
            row = df[mask1].iloc[0]
            val = extract_number_from_row(row)
            if val is not None:
                scope1 = val

        # Look for Scope 2 rows
        mask2 = df.apply(lambda row: row.str.contains("scope 2").any(), axis=1)
        if mask2.any():
            row = df[mask2].iloc[0]
            val = extract_number_from_row(row)
            if val is not None:
                scope2 = val

    return scope1, scope2


# ============================================================
# COMBINED INTERFACE (TABLES → TEXT FALLBACK)
# ============================================================

def extract_scope_combined(text: str, tables: List[Dict]) -> Dict[str, Optional[float]]:
    """
    1. Try tables first (most reliable)
    2. Fallback to regex text extraction (old bronze logic)
    """

    # Try tables
    scope1_t, scope2_t = extract_scope_from_tables(tables)

    # Fallback regex (old extractor)
    text_res = extract_scope_metrics(text)
    scope1_f = safe_float(text_res.get("Scope 1"))
    scope2_f = safe_float(text_res.get("Scope 2"))

    # Final merged values
    scope1 = scope1_t if scope1_t is not None else scope1_f
    scope2 = scope2_t if scope2_t is not None else scope2_f

    return {
        "Scope 1": scope1,
        "Scope 2": scope2
    }
