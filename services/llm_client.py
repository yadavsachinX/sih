"""
Pluggable LLM client. Provide a real implementation for Google Gemini
(or OpenAI) by filling in GEMINI_* env vars. For hackathon, a local
fallback method is included (simple templates / heuristics).
"""

import os
import requests
from typing import Dict

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")  # optional
GEMINI_ENDPOINT = os.getenv("GEMINI_ENDPOINT")  # optional - user must set if using Gemini

def llm_fact_check(text: str) -> Dict:
    """
    If GEMINI_* env vars set, call Gemini via HTTP (user must provide endpoint & key).
    Otherwise run a heuristic fallback.
    """
    if GEMINI_API_KEY and GEMINI_ENDPOINT:
        # NOTE: user must configure endpoint & headers according to their Gemini / Vertex AI setup.
        headers = {"Authorization": f"Bearer {GEMINI_API_KEY}", "Content-Type": "application/json"}
        payload = {"prompt": f"Fact-check this statement and provide verdict + concise reason: {text}", "max_output_tokens": 256}
        try:
            r = requests.post(GEMINI_ENDPOINT, headers=headers, json=payload, timeout=15)
            r.raise_for_status()
            return r.json()
        except Exception as e:
            return {"error": "gemini_call_failed", "detail": str(e)}
    # fallback simple heuristics
    t = text.lower()
    if "boil" in t or "boiling" in t:
        return {"verdict": "likely_true", "explanation": "Boiling water kills most pathogens."}
    if "drink sewage" in t or "drink raw sewage" in t:
        return {"verdict": "false", "explanation": "Drinking sewage is unsafe."}
    return {"verdict": "unknown", "explanation": "Insufficient info - escalate to LLM."}
