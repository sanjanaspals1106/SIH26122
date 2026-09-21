"""
Centralized shared LLM client for Member 2 and downstream members (M6).
Implements team Hard Restriction #16:
"Nobody makes a Groq/Gemini call outside shared/llm_client.py. If a feature
needs an LLM call, it imports the shared function."

Supports:
- Groq (primary, free tier)
- Gemini (fallback, free tier via OpenAI-compatible endpoint)
Controlled by LLM_PROVIDER, LLM_API_KEY, and LLM_MODEL env vars.
"""
import logging
import os
import pathlib
import time
from typing import Optional

import httpx
import openai
from dotenv import load_dotenv
from openai import OpenAI

logger = logging.getLogger(__name__)

_client: Optional[OpenAI] = None

_PROVIDER_BASE_URLS = {
    "groq": "https://api.groq.com/openai/v1",
    "gemini": "https://generativelanguage.googleapis.com/v1beta/openai/",
}

_PROVIDER_DEFAULT_MODELS = {
    "groq": "openai/gpt-oss-20b",
    "gemini": "gemini-3.6-flash",
}

_RETRYABLE_ERRORS = (
    openai.RateLimitError,
    openai.APIConnectionError,
    openai.APITimeoutError,
    openai.InternalServerError,
)
_MAX_RETRIES = 3
_RETRY_BACKOFF_SECONDS = 4.0


def _load_env_if_needed() -> None:
    if "LLM_API_KEY" not in os.environ:
        env_path = pathlib.Path(__file__).resolve().parents[2] / ".env"
        load_dotenv(dotenv_path=env_path, override=False)


def get_llm_provider() -> str:
    _load_env_if_needed()
    return os.environ.get("LLM_PROVIDER", "groq").lower()


def get_default_model(provider: Optional[str] = None) -> str:
    _load_env_if_needed()
    prov = (provider or get_llm_provider()).lower()
    return os.environ.get("LLM_MODEL", _PROVIDER_DEFAULT_MODELS.get(prov, "groq/compound-mini"))


def _get_client() -> Optional[OpenAI]:
    global _client
    _load_env_if_needed()
    api_key = os.environ.get("LLM_API_KEY")
    if not api_key:
        return None

    if _client is None:
        provider = get_llm_provider()
        base_url = _PROVIDER_BASE_URLS.get(provider)
        if base_url is None:
            raise ValueError(f"Unknown LLM_PROVIDER '{provider}' — expected 'groq' or 'gemini'")
        http_client = httpx.Client(timeout=30.0)
        _client = OpenAI(api_key=api_key, base_url=base_url, http_client=http_client)
    return _client


def reset_client() -> None:
    global _client
    _client = None


def call_llm(
    messages: list[dict],
    temperature: float = 0.0,
    response_format: Optional[dict] = None,
    model: Optional[str] = None,
) -> str:
    """
    Central function to make an LLM chat completion call.
    Returns the string content of the response message.

    Includes retry backoff for rate limits, connection errors, and transient 5xx issues.
    If LLM_API_KEY is not configured or all retries fail in test mode, returns
    a graceful fallback string rather than crashing.
    """
    client = _get_client()
    if client is None:
        logger.warning("[llm_client] LLM_API_KEY not configured, returning mock fallback response")
        if response_format and response_format.get("type") == "json_object":
            return "{}"
        return "Could you please specify the activity discipline, event type, and progress percentage for this claim?"

    target_model = model or get_default_model()
    kwargs = {
        "model": target_model,
        "messages": messages,
        "temperature": temperature,
    }
    if response_format:
        kwargs["response_format"] = response_format

    last_error: Optional[Exception] = None
    for attempt in range(_MAX_RETRIES + 1):
        try:
            response = client.chat.completions.create(**kwargs)
            return response.choices[0].message.content or ""
        except _RETRYABLE_ERRORS as e:
            last_error = e
            if attempt < _MAX_RETRIES:
                logger.warning(
                    "LLM request failed (%s), retrying (%d/%d)...",
                    e,
                    attempt + 1,
                    _MAX_RETRIES,
                )
                time.sleep(_RETRY_BACKOFF_SECONDS * (attempt + 1))
        except Exception as e:
            logger.error(f"[llm_client] Non-retryable error during LLM call: {e}")
            if response_format and response_format.get("type") == "json_object":
                return "{}"
            return "Please provide more details on the event type, discipline, and progress for this claim."

    logger.error(f"[llm_client] LLM call failed after retries: {last_error}")
    if response_format and response_format.get("type") == "json_object":
        return "{}"
    return "Could you please clarify the event type, discipline, and progress for this claim?"
