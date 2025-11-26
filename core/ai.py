# core/ai.py
# Single-file "AI in the middle": extracted -> (AI mapping, validate/repair) -> data/output

import os
import json
import requests
import re
from pathlib import Path
from typing import List, Optional, Literal, Dict, Any

########################################
# 0) Configuration
########################################
# CHANGE THESE DEFAULTS TO MATCH YOUR LOCAL SETUP
DEFAULT_PROVIDER = "ollama"           # "ollama" or "openai-compatible"
DEFAULT_API_BASE = "http://localhost:11434"
DEFAULT_MODEL    = "llama3.2"           # Make sure you have run: ollama pull llama3

PROVIDER = os.getenv("PROVIDER", DEFAULT_PROVIDER)
API_BASE = os.getenv("API_BASE", DEFAULT_API_BASE)
API_KEY  = os.getenv("API_KEY",  "ignore-if-ollama")
MODEL    = os.getenv("MODEL",    DEFAULT_MODEL)

# Directories
DATA_DIR      = Path(os.getenv("DATA_DIR", "data"))
OUTPUT_DIR    = Path(os.getenv("OUTPUT_DIR", str(DATA_DIR / "output")))
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

########################################
# 1) Schema & Validation
########################################
SCHEMA: Dict[str, Any] = {
  "type": "object",
  "required": ["metrics"],
  "properties": {
    "metrics": {
      "type": "array",
      "items": {
        "type": "object",
        "required": ["name", "value", "unit", "year"],
        "properties": {
          "name": { "enum": ["Scope 1", "Scope 2 (location)", "Scope 2 (market)", "Scope 3"] },
          "value": { "type": "number" },
          "unit":  { "enum": ["tCO2e", "ktCO2e", "MtCO2e"] },
          "year":  { "type": "integer" },
          "page":  { "type": "integer" },
          "snippet": { "type": "string" }
        }
      }
    }
  }
}

########################################
# 2) Pre-filter (Crucial for Local LLMs)
########################################
def shortlist_snippets(extracted: dict, limit:int=40) -> List[str]:
    """
    Filters the massive text down to just lines with keywords + numbers.
    Prevents context window overflow and timeouts.
    """
    out: List[str] = []
    keywords = ["scope 1", "scope 2", "scope 3", "tco2e", "mtco2e", "emissions", "ghg", "tonnes"]
    
    pages = extracted.get("pages", [])
    for page_obj in pages:
        page_no = page_obj.get("page", "?")
        lines = page_obj.get("lines", [])
        
        for ln in lines:
            ln_lower = ln.lower()
            # Heuristic: Must have a keyword AND a digit to be relevant
            if any(k in ln_lower for k in keywords) and any(c.isdigit() for c in ln):
                # Clean up whitespace
                clean_ln = " ".join(ln.split())
                out.append(f"[Page {page_no}] {clean_ln}")
                
    # Return unique lines, capped at limit
    return list(set(out))[:limit]

########################################
# 3) Prompt Building
########################################
def build_system_prompt() -> str:
    return (
        "You are an expert ESG analyst. Extract Scope 1, Scope 2, and Scope 3 emissions data from the provided text snippets. "
        "Return ONLY valid JSON matching the schema. No markdown, no explanations."
    )

def build_user_prompt(snippets: List[str]) -> str:
    example = {
        "metrics": [
            { "name": "Scope 1", "value": 1234.5, "unit": "tCO2e", "year": 2023, "page": 10, "snippet": "Scope 1 emissions: 1,234.5 tCO2e" }
        ]
    }
    context = "\n".join(snippets)
    return (
        f"CONTEXT:\n{context}\n\n"
        f"INSTRUCTIONS:\n"
        f"1. Extract emissions data.\n"
        f"2. Convert all values to numbers (remove commas).\n"
        f"3. Return JSON only.\n\n"
        f"EXAMPLE JSON:\n{json.dumps(example)}"
    )

########################################
# 4) Providers (Robust)
########################################
def _call_ollama(messages: List[dict]) -> str:
    url = f"{API_BASE.rstrip('/')}/api/generate"
    
    # Convert chat messages to a single prompt for Ollama 'generate' endpoint
    # (Simpler than chat endpoint for some models)
    full_prompt = ""
    for m in messages:
        full_prompt += f"{m['role'].upper()}: {m['content']}\n"
    full_prompt += "ASSISTANT: "

    payload = {
        "model": MODEL,
        "prompt": full_prompt,
        "stream": False,
        "options": { "temperature": 0.0, "num_ctx": 4096 },
        "format": "json" # Force JSON mode if supported
    }

    print(f"   👉 Sending request to Ollama ({url}) with model '{MODEL}'...")
    try:
        r = requests.post(url, json=payload, timeout=600) # 10 min timeout
    except requests.exceptions.RequestException as e:
        print(f"   ❌ Connection Failed: {e}")
        return ""

    if r.status_code != 200:
        print(f"   ❌ Ollama Error {r.status_code}: {r.text}")
        return ""

    try:
        data = r.json()
        return data.get("response", "")
    except Exception:
        print(f"   ❌ Failed to parse Ollama response: {r.text[:100]}...")
        return ""

def llm_complete(messages: List[dict]) -> str:
    if PROVIDER == "ollama":
        return _call_ollama(messages)
    else:
        # Fallback to OpenAI-compatible
        url = f"{API_BASE.rstrip('/')}/v1/chat/completions"
        headers = {"Authorization": f"Bearer {API_KEY}"}
        payload = {
            "model": MODEL,
            "messages": messages,
            "temperature": 0.0,
            "response_format": {"type": "json_object"}
        }
        try:
            r = requests.post(url, headers=headers, json=payload, timeout=120)
            if r.status_code != 200:
                print(f"   ❌ API Error {r.status_code}: {r.text}")
                return ""
            return r.json()["choices"][0]["message"]["content"]
        except Exception as e:
            print(f"   ❌ API Exception: {e}")
            return ""

########################################
# 5) Main Logic
########################################
def extract_metrics_from_extracted(extracted: dict) -> dict:
    snippets = shortlist_snippets(extracted, limit=25)
    if not snippets:
        print("   ⚠️ No relevant snippets found in text (keywords missing).")
        return {"metrics": []}

    print(f"   ℹ️  Sending {len(snippets)} snippets to AI...")
    
    sys_msg = {"role": "system", "content": build_system_prompt()}
    user_msg = {"role": "user",   "content": build_user_prompt(snippets)}

    raw_response = llm_complete([sys_msg, user_msg])
    
    if not raw_response:
        raise ValueError("AI returned empty response. Check if Ollama is running and model exists.")

    # Attempt to parse JSON
    try:
        # Clean up markdown code blocks if present
        clean_json = re.sub(r"```json|```", "", raw_response).strip()
        data = json.loads(clean_json)
        return data
    except json.JSONDecodeError:
        print(f"   ❌ Invalid JSON from AI: {raw_response[:100]}...")
        return {"metrics": []}

########################################
# 6) Entrypoint
########################################
def load_extracted_json(path: Path) -> dict:
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)

def run_ai_for_document(stem: str, extracted_json_path: Path) -> dict:
    extracted = load_extracted_json(extracted_json_path)
    result = extract_metrics_from_extracted(extracted)
    
    # Save result
    out_path = OUTPUT_DIR / f"{stem}.json"
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(result, f, indent=2)
        
    return result
