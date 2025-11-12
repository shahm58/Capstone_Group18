# core/ai_extractor.py
# Single-file "AI in the middle": extracted -> (AI mapping, validate/repair) -> data/output

import os, re, json, csv, time, uuid, requests
from pathlib import Path
from typing import List, Optional, Literal, Dict, Any

########################################
# 0) Configuration (env-driven)
########################################
PROVIDER = os.getenv("PROVIDER", "openai-compatible")
API_BASE = os.getenv("API_BASE", "https://api.openai.com")  # e.g., https://api.openai.com or http://localhost:1234
API_KEY  = os.getenv("API_KEY",  "YOUR_API_KEY_HERE")
MODEL    = os.getenv("MODEL",    "gpt-4.1-mini")            # e.g., "gpt-4.1-mini" or "command-r" / "command-r-plus"

# Where to read the Stage-1 extraction and where to write final outputs
DATA_DIR      = Path(os.getenv("DATA_DIR",      "data"))
EXTRACTED_DIR = Path(os.getenv("EXTRACTED_DIR", str(DATA_DIR / "extracted")))
OUTPUT_DIR    = Path(os.getenv("OUTPUT_DIR",    str(DATA_DIR / "output")))
LOG_DIR       = Path(os.getenv("LOG_DIR",       "logs"))
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
LOG_DIR.mkdir(parents=True, exist_ok=True)

########################################
# 1) Schema 
########################################
MetricName = Literal["Scope 1", "Scope 2 (location)", "Scope 2 (market)", "Scope 3"]
AllowedUnits = Literal["tCO2e", "ktCO2e", "MtCO2e"]

SCHEMA: Dict[str, Any] = {
  "type": "object",
  "required": ["metrics"],
  "properties": {
    "metrics": {
      "type": "array",
      "items": {
        "type": "object",
        "required": ["name", "value", "unit", "year", "page"],
        "properties": {
          "name": { "enum": ["Scope 1", "Scope 2 (location)", "Scope 2 (market)", "Scope 3"] },
          "value": { "type": "number" },
          "unit":  { "enum": ["tCO2e", "ktCO2e", "MtCO2e"] },
          "year":  { "type": "integer", "minimum": 1990, "maximum": 2100 },
          "page":  { "type": "integer", "minimum": 1 },
          "snippet":    { "type": "string" },
          "confidence": { "type": "number", "minimum": 0, "maximum": 1 }
        }
      }
    }
  }
}

def _is_valid_metric(m: dict) -> Optional[str]:
    """Lightweight validator for one metric dict. Returns None if valid, else error string."""
    try:
        if m.get("name") not in ["Scope 1","Scope 2 (location)","Scope 2 (market)","Scope 3"]:
            return "invalid name"
        if not isinstance(m.get("value"), (int,float)):
            return "value must be number"
        if m.get("unit") not in ["tCO2e","ktCO2e","MtCO2e"]:
            return "invalid unit"
        y = m.get("year")
        if not isinstance(y, int) or y < 1990 or y > 2100:
            return "invalid year"
        p = m.get("page")
        if not isinstance(p, int) or p < 1:
            return "invalid page"
        c = m.get("confidence", None)
        if c is not None and (not isinstance(c,(int,float)) or c < 0 or c > 1):
            return "invalid confidence"
        # snippet can be missing or any string
        return None
    except Exception as e:
        return f"exception: {e}"

def _validate_payload(payload: dict) -> List[str]:
    errs = []
    if not isinstance(payload, dict):
        return ["payload is not an object"]
    metrics = payload.get("metrics")
    if not isinstance(metrics, list):
        return ["metrics must be an array"]
    for idx, m in enumerate(metrics):
        if not isinstance(m, dict):
            errs.append(f"metrics[{idx}] not an object")
            continue
        e = _is_valid_metric(m)
        if e:
            errs.append(f"metrics[{idx}] {e}")
    return errs

########################################
# 2) Pre-filter: shrink context for cost/accuracy
########################################
def shortlist_snippets(extracted: dict, limit:int=30) -> List[str]:
    """
    Input shape expected from Stage-1 extractor:
      {
        "pages": [
          { "page": 1, "lines": ["...","..."], "tables": [ [ ["h1","h2"], ["v1","v2"] ] ] },
          ...
        ]
      }
    We keep a small window of lines around hits, and render table rows as text lines too.
    """
    out: List[str] = []
    pages = extracted.get("pages", [])
    for page_obj in pages:
        page_no = int(page_obj.get("page", 0))
        lines = page_obj.get("lines", []) or []
        # 2a) Lines
        for i, ln in enumerate(lines):
            low = ln.lower()
            if ("scope" in low) or ("co2e" in low) or re.search(r"\b20\d{2}\b", ln) or re.search(r"\b\d[\d,\.]*\s*(tco2e|ktco2e|mtco2e)\b", low):
                window = " ".join(lines[max(0, i-2): i+3]).strip()
                if window:
                    out.append(f"[p{page_no}] {window}")
                    if len(out) >= limit:
                        return out
        # 2b) Tables -> flatten a few rows
        for tbl in page_obj.get("tables", []) or []:
            # Expect list of rows; join cells with spaces
            for row in tbl[:5]:
                row_txt = " ".join(str(c) for c in row if c is not None)
                low = row_txt.lower()
                if ("scope" in low) or ("co2e" in low) or re.search(r"\b20\d{2}\b", row_txt):
                    out.append(f"[p{page_no}] {row_txt}")
                    if len(out) >= limit:
                        return out
    return out[:limit]

########################################
# 3) Prompt building
########################################
def build_system_prompt() -> str:
    return (
        "You extract ESG emissions metrics (Scope 1, Scope 2 location/market, Scope 3). "
        "Return ONLY JSON that validates the provided JSON Schema. "
        "If uncertain about any metric, omit it rather than guessing."
    )

def build_user_prompt(snippets: List[str]) -> str:
    example = {
        "metrics": [
            {
              "name": "Scope 2 (market)",
              "value": 21010.0,
              "unit": "tCO2e",
              "year": 2023,
              "page": 18,
              "snippet": "Purchased electricity (market-based).",
              "confidence": 0.82
            }
        ]
    }
    return (
        "JSON Schema:\n" + json.dumps(SCHEMA, indent=2) +
        "\n\nContext snippets (max 30):\n" + "\n".join(snippets) +
        "\n\nReturn ONLY JSON in the exact schema above. Example format (not ground truth):\n" +
        json.dumps(example, indent=2)
    )

def build_repair_prompt(errors: List[str], last_json: str) -> str:
    return (
        "The previous JSON failed validation with these errors:\n" +
        "\n".join(f"- {e}" for e in errors[:10]) +
        "\nCorrect ONLY the invalid fields so the JSON validates the schema. "
        "Return ONLY corrected JSON.\n\nLast attempt:\n" + last_json
    )

########################################
# 4) Providers
########################################
def _call_openai_compatible(messages: List[dict]) -> str:
    url = f"{API_BASE.rstrip('/')}/v1/chat/completions"
    headers = {"Authorization": f"Bearer {API_KEY}", "Content-Type": "application/json"}
    payload = {
        "model": MODEL,
        "messages": messages,
        "temperature": 0.0,
        "response_format": {"type": "json_object"}  # JSON-only mode where supported
    }
    r = requests.post(url, headers=headers, json=payload, timeout=120)
    r.raise_for_status()
    return r.json()["choices"][0]["message"]["content"]

def _call_cohere(messages: List[dict]) -> str:
    # Minimal Cohere chat wrapper (flatten messages to one string)
    url = f"{API_BASE.rstrip('/')}/v1/chat"
    headers = {"Authorization": f"Bearer {API_KEY}", "Content-Type": "application/json"}
    prompt = "\n".join([f"{m['role'].upper()}: {m['content']}" for m in messages])
    payload = {"model": MODEL, "message": prompt, "temperature": 0.0}
    r = requests.post(url, headers=headers, json=payload, timeout=120)
    r.raise_for_status()
    data = r.json()
    return data.get("text") or data.get("response", {}).get("text") or json.dumps(data)

def _call_ollama(messages: List[dict], model: str) -> str:
    """
    Call a local Ollama server (http://localhost:11434) using /api/chat.
    We request JSON-only output via {"format":"json"} (works with most instruct models).
    """
    url = f"{API_BASE.rstrip('/')}/api/chat"  # e.g., http://localhost:11434/api/chat
    headers = {"Content-Type": "application/json"}
    # Ollama accepts OpenAI-style {role, content} messages directly.
    payload = {
        "model": model,
        "messages": messages,
        "stream": False,
        "format": "json"  # ask for strict JSON if the model supports it
    }
    r = requests.post(url, headers=headers, json=payload, timeout=180)
    r.raise_for_status()
    data = r.json()
    # Response shape: {"message":{"role":"assistant","content":"<text/json>"},"done":true,...}
    return data["message"]["content"]


def llm_complete(messages: List[dict]) -> str:
    if PROVIDER == "openai-compatible":
        return _call_openai_compatible(messages)
    elif PROVIDER == "cohere":
        return _call_cohere(messages)
    elif PROVIDER == "ollama":
        return _call_ollama(messages, MODEL)
    else:
        raise RuntimeError(f"Unknown PROVIDER: {PROVIDER}")


########################################
# 5) Closed-loop extraction
########################################
def extract_metrics_from_extracted(extracted: dict, max_repairs:int=2) -> dict:
    snippets = shortlist_snippets(extracted, limit=30)
    sys_msg = {"role": "system", "content": build_system_prompt()}
    user_msg = {"role": "user",   "content": build_user_prompt(snippets)}

    raw = llm_complete([sys_msg, user_msg])
    last = raw
    attempts = 0
    while True:
        try:
            payload = json.loads(last)
        except json.JSONDecodeError as e:
            if attempts >= max_repairs:
                raise
            errs = [f"json decode error: {e}"]
            repair = {"role":"user","content": build_repair_prompt(errs, last)}
            last = llm_complete([sys_msg, user_msg, repair]); attempts += 1
            continue

        errors = _validate_payload(payload)
        if not errors:
            return payload
        if attempts >= max_repairs:
            # Return best-effort (drop invalid metrics) rather than fail hard
            payload["metrics"] = [m for m in payload.get("metrics", []) if not _is_valid_metric(m)]
            return payload

        # Repair loop
        repair = {"role":"user","content": build_repair_prompt(errors, json.dumps(payload))}
        last = llm_complete([sys_msg, user_msg, repair]); attempts += 1

########################################
# 6) I/O helpers
########################################
def load_extracted_json(extracted_path: Path) -> dict:
    with open(extracted_path, "r", encoding="utf-8") as f:
        return json.load(f)

def save_outputs(doc_stem: str, payload: dict):
    # Final JSON
    out_json = OUTPUT_DIR / f"{doc_stem}.json"
    with open(out_json, "w", encoding="utf-8") as f:
        json.dump({"doc": f"{doc_stem}.pdf", **payload}, f, ensure_ascii=False, indent=2)

    # CSV (doc,name,value,unit,year,page,snippet,confidence)
    out_csv = OUTPUT_DIR / f"{doc_stem}.csv"
    fields = ["doc","name","value","unit","year","page","snippet","confidence"]
    with open(out_csv, "w", encoding="utf-8", newline="") as f:
        w = csv.writer(f)
        w.writerow(fields)
        for m in payload.get("metrics", []):
            w.writerow([
                f"{doc_stem}.pdf",
                m.get("name",""),
                m.get("value",""),
                m.get("unit",""),
                m.get("year",""),
                m.get("page",""),
                m.get("snippet",""),
                m.get("confidence","")
            ])

def append_log(doc_stem: str, event: dict):
    log_path = LOG_DIR / f"{doc_stem}.ndjson"
    with open(log_path, "a", encoding="utf-8") as f:
        f.write(json.dumps({"ts": time.time(), **event}, ensure_ascii=False) + "\n")

########################################
# 7) Public entrypoint you call from main.py
########################################
def run_ai_for_document(stem: str, extracted_json_path: Path) -> dict:
    """
    Reads Stage-1 extracted JSON, calls the AI closed-loop mapper, validates/repairs,
    writes final JSON/CSV, and returns the final payload.
    """
    run_id = str(uuid.uuid4())
    append_log(stem, {"run_id": run_id, "event": "start", "provider": PROVIDER, "model": MODEL})

    extracted = load_extracted_json(extracted_json_path)
    payload   = extract_metrics_from_extracted(extracted, max_repairs=2)
    save_outputs(stem, payload)

    append_log(stem, {"run_id": run_id, "event": "done", "metrics_count": len(payload.get("metrics", []))})
    return payload
