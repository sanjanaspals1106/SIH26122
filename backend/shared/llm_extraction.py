"""
M2's extraction engine. Takes raw claim text (any language, any messiness)
and returns a validated ExtractedClaimFields object. Used by every intake
path (text, voice, file, scanned-diary-after-OCR) — build and test this once,
in isolation, before wiring it into any endpoint.

PRD v5 change: default provider is Groq's free tier (OpenAI-compatible
endpoint), not paid OpenAI. Gemini free tier is the documented fallback,
also reachable via an OpenAI-compatible endpoint, so both providers use the
exact same `openai` SDK client code — only base_url/api_key/model differ.
Switch providers with the LLM_PROVIDER env var, no code change needed.
"""
import json
import os
import httpx
from openai import OpenAI

from backend.shared.schemas import ExtractedClaimFields

_client = None

_PROVIDER_BASE_URLS = {
    "groq": "https://api.groq.com/openai/v1",
    "gemini": "https://generativelanguage.googleapis.com/v1beta/openai/",
}

_PROVIDER_DEFAULT_MODELS = {
    "groq": "groq/compound-mini",
    "gemini": "gemini-2.5-flash",
}


def _get_client() -> OpenAI:
    global _client
    if _client is None:
        # If the key is not already in the environment (e.g. server was started
        # before .env was populated), try loading .env from the project root now.
        if "LLM_API_KEY" not in os.environ:
            import pathlib
            from dotenv import load_dotenv
            env_path = pathlib.Path(__file__).resolve().parents[2] / ".env"
            load_dotenv(dotenv_path=env_path, override=False)
        provider = os.environ.get("LLM_PROVIDER", "groq").lower()
        base_url = _PROVIDER_BASE_URLS.get(provider)
        if base_url is None:
            raise ValueError(f"Unknown LLM_PROVIDER '{provider}' — expected 'groq' or 'gemini'")
        api_key = os.environ.get("LLM_API_KEY")
        if not api_key:
            raise RuntimeError(
                "LLM_API_KEY is not set. Add it to .env or export it before starting the server."
            )
        http_client = httpx.Client(timeout=30.0)
        _client = OpenAI(api_key=api_key, base_url=base_url, http_client=http_client)
    return _client


def _get_model() -> str:
    provider = os.environ.get("LLM_PROVIDER", "groq").lower()
    return os.environ.get("LLM_MODEL", _PROVIDER_DEFAULT_MODELS.get(provider, "groq/compound-mini"))


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
        response = client.chat.completions.create(
            model=_get_model(),
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": raw_text},
            ],
            response_format={"type": "json_object"},
            temperature=0,
        )
        raw = response.choices[0].message.content
        data = json.loads(raw)
        return ExtractedClaimFields(**data)
    except Exception as e:
        # Extraction failure (network error, bad key, malformed JSON, etc.)
        # -> still return a valid (mostly-null) object rather than raising.
        # The claim still gets created at EXTRACTED status; a human will see
        # blank fields in the review workspace rather than the claim vanishing.
        print(f"[llm_extraction] extraction failed, falling back to nulls: {e}")
        return ExtractedClaimFields()
