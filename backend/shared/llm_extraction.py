"""
M2's extraction engine. Takes raw claim text (any language, any messiness)
and returns a validated ExtractedClaimFields object. Used by every intake
path (text, voice, file, scanned-diary-after-OCR).

PRD v5: default provider is Groq's free tier (OpenAI-compatible
endpoint), not paid OpenAI. Gemini free tier is the documented fallback,
also reachable via an OpenAI-compatible endpoint, so both providers use the
exact same `openai` SDK client code — only base_url/api_key/model differ.
Switch providers with the LLM_PROVIDER env var, no code change needed.
"""
import json
import os
from typing import Optional
from openai import OpenAI

from backend.shared.schemas import ClaimMode, ExtractedClaimFields

_client: Optional[OpenAI] = None

_PROVIDER_BASE_URLS = {
    "groq": "https://api.groq.com/openai/v1",
    "gemini": "https://generativelanguage.googleapis.com/v1beta/openai/",
}

_PROVIDER_DEFAULT_MODELS = {
    "groq": "llama-3.3-70b-versatile",
    "gemini": "gemini-2.5-flash",
}


def _get_client() -> Optional[OpenAI]:
    global _client
    api_key = os.environ.get("LLM_API_KEY")
    if not api_key:
        return None
    if _client is None:
        provider = os.environ.get("LLM_PROVIDER", "groq").lower()
        base_url = _PROVIDER_BASE_URLS.get(provider)
        if base_url is None:
            raise ValueError(f"Unknown LLM_PROVIDER '{provider}' — expected 'groq' or 'gemini'")
        _client = OpenAI(api_key=api_key, base_url=base_url)
    return _client


def _get_model() -> str:
    provider = os.environ.get("LLM_PROVIDER", "groq").lower()
    return os.environ.get("LLM_MODEL", _PROVIDER_DEFAULT_MODELS.get(provider, "llama-3.3-70b-versatile"))


SYSTEM_PROMPT = """You are a field-report extraction engine for a construction \
project tracking system. You will receive raw text from a site report — it may \
be in English, Hindi, or a mix of both, and may be informal or messy.

Your job: read and understand the text (in whatever language it's in), then \
output ONLY a single JSON object with these fields, with all string values in \
English/normalized form:

{
  "event_date": "YYYY-MM-DD or null",
  "reported_activity_id": "string or null — ONLY populate if the text explicitly \
names or strongly implies a specific schedule activity ID (e.g. 'Activity A-1042 \
started'). If no ID is mentioned, leave this null — do not guess.",
  "discipline": "one of CIVIL, PIPING, STATIC_ROTATING_EQUIPMENT, ELECTRICAL, \
INSTRUMENTATION, HSE, or null",
  "action": "short string describing what was done",
  "event_type": "one of ACTUAL_START, ACTUAL_FINISH, PROGRESS_UPDATE, DELAY, \
BLOCKER",
  "claim_mode": "CUMULATIVE_PCT if this reports the activity's total completion \
so far, or INCREMENTAL_QUANTITY if this reports one partial/countable \
contribution (e.g. 'welded joint 3 of 10'). Default to CUMULATIVE_PCT unless \
the text clearly describes a partial/countable contribution.",
  "asset_tag": "string or null",
  "location": "string or null",
  "claimed_quantity": "number or null — only if claim_mode is INCREMENTAL_QUANTITY",
  "claimed_uom": "string or null — only if claim_mode is INCREMENTAL_QUANTITY",
  "claimed_pct": "number 0-100 or null — only if claim_mode is CUMULATIVE_PCT",
  "delay_reason": "one of MATERIAL, EQUIPMENT, LABOUR, ACCESS, WEATHER, REWORK, \
OTHER, or null — only if event_type is DELAY or BLOCKER",
  "language_detected": "the language of the original input, e.g. 'English', \
'Hindi', 'Hindi-English mixed'"
}

Rules:
- Output ONLY the JSON object. No preamble, no markdown fences, no explanation.
- If a field cannot be determined from the text, use null (except claim_mode,
  which defaults to CUMULATIVE_PCT).
- claimed_pct and claimed_quantity/claimed_uom are mutually exclusive based on
  claim_mode — never populate both.
- event_date: if the text doesn't state a date, use null (the caller will fall
  back to today's date).
"""


def extract_claim_fields(raw_text: str) -> ExtractedClaimFields:
    """
    Calls the LLM with the strict extraction prompt, validates the response
    against ExtractedClaimFields. Never raises on malformed LLM output —
    falls back to an all-null ExtractedClaimFields() so the caller can still
    create the claim row (extraction failure should never block intake).
    """
    try:
        client = _get_client()
        if not client:
            print("[llm_extraction] LLM_API_KEY not configured, falling back to basic defaults")
            return ExtractedClaimFields(action=raw_text.strip()[:150] if raw_text else None)

        response = client.chat.completions.create(
            model=_get_model(),
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": raw_text},
            ],
            response_format={"type": "json_object"},
            temperature=0,
        )
        raw = response.choices[0].message.content or "{}"
        data = json.loads(raw)
        result = ExtractedClaimFields(**data)

        # Enforce mutual exclusivity invariant
        if result.claim_mode == ClaimMode.CUMULATIVE_PCT:
            result.claimed_quantity = None
            result.claimed_uom = None
        elif result.claim_mode == ClaimMode.INCREMENTAL_QUANTITY:
            result.claimed_pct = None

        return result
    except Exception as e:
        print(f"[llm_extraction] extraction failed, falling back to nulls: {e}")
        return ExtractedClaimFields(action=raw_text.strip()[:150] if raw_text else None)
