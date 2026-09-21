"""
Deterministic, dependency-free claim extraction used ONLY as an opt-in fallback
(EXTRACTION_FALLBACK=rules) when the LLM provider is unavailable -- quota
exhausted, network down, no key. PRD v6 Section 21: the application shall retain a
deterministic fallback/demo path when external services are unavailable.

It is intentionally conservative: it fills only what plain patterns can support and
leaves everything else null, so Feature 29's clarification gate (missing event_type /
discipline / progress) still asks the Site Engineer instead of guessing. Every claim
still goes through matching, deterministic checks and Supervisor review.
"""
from __future__ import annotations

import re
from typing import Optional

from backend.shared.schemas import ExtractedClaimFields

_DISCIPLINE_KEYWORDS = [
    ("HSE", ("hse", "safety", "toolbox", "induction", "barricad", "audit", "confined space")),
    ("INSTRUMENTATION", ("instrument", "transmitter", "junction box", "flowmeter", "calibration", "detector")),
    ("ELECTRICAL", ("cable", "electrical", "switchgear", "earth pit", "lighting", "tray installation", "mcc")),
    ("STATIC_ROTATING_EQUIPMENT", ("pump", "generator", "compressor", "vessel", "skid", "tank", "grouting", "baseplate")),
    ("PIPING", ("piping", "pipe", "weld", "spool", "header", "fabricat", "valve", "hydro", "tie-in", "flange")),
    ("CIVIL", ("civil", "excavat", "trench", "concrete", "foundation", "rebar", "backfill", "formwork", "blinding")),
]
_UOMS = r"(m3|cu\.?\s?m|m|meters?|metres?|t|tons?|tonnes?|joints?|ea|nos|pits?|poles?|panels?|bins?|checks?|days?)"
_ID_RE = re.compile(r"\b([A-Z]{2,5}(?:-[A-Z0-9]{1,6}){2,4})\b")
_DELAY_KEYWORDS = [
    ("WEATHER", ("rain", "monsoon", "flood", "storm", "weather")),
    ("MATERIAL", ("material", "delivery", "drum", "shortage", "supply")),
    ("EQUIPMENT", ("breakdown", "equipment failure", "crane", "machine")),
    ("LABOUR", ("labour", "labor", "manpower", "workers absent")),
    ("ACCESS", ("access", "permit", "blocked road", "restricted")),
    ("REWORK", ("rework", "redo", "re-do", "reset")),
]


def _language(text: str) -> str:
    if re.search(r"[ఀ-౿]", text):
        return "Telugu"
    if re.search(r"[ऀ-ॿ]", text):
        return "Hindi"
    return "English"


def extract_with_rules(text: str) -> ExtractedClaimFields:
    low = text.lower()
    data: dict = {"language_detected": _language(text), "action": text.strip()[:120] or None}

    scoring_text = re.sub(r"\b(pump|tank|generator|control room|waste storage)\s+(station|area|bay|yard)\b", " ", low)
    best, best_hits = None, 0
    for disc, words in _DISCIPLINE_KEYWORDS:  # highest keyword count wins; ties keep list order
        hits = sum(1 for w in words if w in scoring_text)
        if hits > best_hits:
            best, best_hits = disc, hits
    if best:
        data["discipline"] = best

    if re.search(r"\b(finish|finished|complete[d]?|done|handed over)\b", low) and (
        re.search(r"100\s*%", low) or not re.search(r"\d", low)
    ):
        data["event_type"] = "ACTUAL_FINISH"
    elif re.search(r"\b(start(ed)?|commenc\w+|mobili[sz]ed)\b", low) and not re.search(r"\d\s*%|\d\s*(m|t)\b", low):
        data["event_type"] = "ACTUAL_START"
    elif re.search(r"\b(delay(ed)?|behind|waiting)\b", low):
        data["event_type"] = "DELAY"
    elif re.search(r"\b(blocked|blocker|stopped|halted)\b", low):
        data["event_type"] = "BLOCKER"
    elif re.search(r"\d", low):
        data["event_type"] = "PROGRESS_UPDATE"

    pct = re.search(r"(\d+(?:\.\d+)?)\s*(?:%|percent|per cent)", low)
    qty = re.search(rf"(\d+(?:\.\d+)?)\s*{_UOMS}\b", low)
    if pct and (float(pct.group(1)) <= 100):
        data["claim_mode"] = "CUMULATIVE_PCT"
        data["claimed_pct"] = float(pct.group(1))
    elif qty:
        data["claim_mode"] = "INCREMENTAL_QUANTITY"
        data["claimed_quantity"] = float(qty.group(1))
        uom = re.sub(r"\s", "", qty.group(2)).rstrip("s")
        data["claimed_uom"] = {"cum": "m3", "cu.m": "m3", "meter": "m", "metre": "m", "ton": "t", "tonne": "t"}.get(uom, uom)
    elif data.get("event_type") == "ACTUAL_FINISH":
        data["claim_mode"] = "CUMULATIVE_PCT"
        data["claimed_pct"] = 100.0

    m = _ID_RE.search(text)
    if m:
        data["reported_activity_id"] = m.group(1)
    loc = re.search(r"\b(?:at|in|near)\s+((?:[A-Z][\w-]*\s?){1,4}\d*)", text)
    if loc:
        data["location"] = loc.group(1).strip()
    for reason, words in _DELAY_KEYWORDS:
        if any(w in low for w in words):
            data["delay_reason"] = reason
            break
    return ExtractedClaimFields(**data)


def fallback_enabled() -> bool:
    import os
    return os.environ.get("EXTRACTION_FALLBACK", "").strip().lower() == "rules"
