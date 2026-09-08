"""
Shared request/response models (doc Section 3: "One shared request/response
schema file"). Additive only — add a new model for your own endpoint, never
edit a model another member's code already depends on without flagging the
team first.
"""
from __future__ import annotations
from datetime import date, datetime
from enum import Enum
from typing import Optional
from pydantic import BaseModel, Field


# ---------- shared enums (used across M2/M3/M4) ----------

class Discipline(str, Enum):
    CIVIL = "CIVIL"
    PIPING = "PIPING"
    STATIC_ROTATING_EQUIPMENT = "STATIC_ROTATING_EQUIPMENT"
    ELECTRICAL = "ELECTRICAL"
    INSTRUMENTATION = "INSTRUMENTATION"
    HSE = "HSE"


class EventType(str, Enum):
    ACTUAL_START = "ACTUAL_START"
    ACTUAL_FINISH = "ACTUAL_FINISH"
    PROGRESS_UPDATE = "PROGRESS_UPDATE"
    DELAY = "DELAY"
    BLOCKER = "BLOCKER"


class ClaimMode(str, Enum):
    CUMULATIVE_PCT = "CUMULATIVE_PCT"
    INCREMENTAL_QUANTITY = "INCREMENTAL_QUANTITY"


class DelayReason(str, Enum):
    MATERIAL = "MATERIAL"
    EQUIPMENT = "EQUIPMENT"
    LABOUR = "LABOUR"
    ACCESS = "ACCESS"
    WEATHER = "WEATHER"
    REWORK = "REWORK"
    OTHER = "OTHER"


class InputChannel(str, Enum):
    FILE_UPLOAD = "FILE_UPLOAD"
    SCANNED_OCR = "SCANNED_OCR"
    TYPED_TEXT = "TYPED_TEXT"
    VOICE = "VOICE"
    SCHEDULE_EXPORT = "SCHEDULE_EXPORT"


class UploadPurpose(str, Enum):
    EVIDENCE_PHOTO = "EVIDENCE_PHOTO"
    SCANNED_DIARY = "SCANNED_DIARY"


# ---------- M2: extraction output shape (this is the LLM's strict JSON contract) ----------

class ExtractedClaimFields(BaseModel):
    """Exact shape the LLM must return. Missing/malformed fields -> null, never crash."""
    event_date: Optional[date] = None
    reported_activity_id: Optional[str] = None
    discipline: Optional[Discipline] = None
    action: Optional[str] = None
    event_type: Optional[EventType] = None
    claim_mode: ClaimMode = ClaimMode.CUMULATIVE_PCT
    asset_tag: Optional[str] = None
    location: Optional[str] = None
    claimed_quantity: Optional[float] = None
    claimed_uom: Optional[str] = None
    claimed_pct: Optional[float] = Field(default=None, ge=0, le=100)
    delay_reason: Optional[DelayReason] = None
    language_detected: Optional[str] = None


# ---------- M2: request/response models for the intake endpoints ----------

class TextClaimRequest(BaseModel):
    """
    Per PRD v5 Section 6.2: "User identity must never be accepted as a
    free-form request-body field." uploader_id/supervisor_id no longer come
    from the client — the router derives them from the authenticated user
    (require_role("SITE_ENGINEER") -> CurrentUser.id) instead.
    """
    raw_claim_text: str
    input_channel: InputChannel = InputChannel.TYPED_TEXT
    schedule_id: Optional[str] = None  # if omitted, defaults to most recently uploaded schedule


class ClaimResponse(BaseModel):
    event_id: str
    document_id: Optional[str] = None
    schedule_id: str
    event_date: date
    raw_claim_text: str
    input_channel: InputChannel
    language_detected: Optional[str] = None
    reported_activity_id: Optional[str] = None
    matched_activity_id: Optional[str] = None
    discipline: Optional[str] = None
    action: Optional[str] = None
    event_type: Optional[str] = None
    claim_mode: str
    asset_tag: Optional[str] = None
    location: Optional[str] = None
    claimed_quantity: Optional[float] = None
    claimed_uom: Optional[str] = None
    claimed_pct: Optional[float] = None
    delay_reason: Optional[str] = None
    supervisor_id: Optional[str] = None
    photo_path: Optional[str] = None
    status: str
    created_at: datetime
