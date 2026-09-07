from datetime import date, datetime
from typing import Optional

from pydantic import BaseModel, Field


class Schedule(BaseModel):
    schedule_id: str
    project_name: str
    data_date: Optional[date] = None
    source_format: Optional[str] = None


class ScheduleActivity(BaseModel):
    schedule_id: str
    activity_id: str
    activity_name: str
    wbs_code: Optional[str] = None
    discipline: str
    location: str
    asset_tag: Optional[str] = None
    planned_start: date
    planned_finish: date
    planned_quantity: Optional[float] = None
    uom: Optional[str] = None
    baseline_pct_complete: float = Field(default=0.0, ge=0.0, le=100.0)


class ExecutionClaim(BaseModel):
    event_id: str
    schedule_id: str
    event_date: date
    raw_claim_text: str
    input_channel: str
    language_detected: Optional[str] = None
    reported_activity_id: Optional[str] = None
    discipline: Optional[str] = None
    action: Optional[str] = None
    event_type: Optional[str] = None
    claim_mode: str = "CUMULATIVE_PCT"
    asset_tag: Optional[str] = None
    location: Optional[str] = None
    claimed_quantity: Optional[float] = None
    claimed_uom: Optional[str] = None
    claimed_pct: Optional[float] = Field(default=None, ge=0.0, le=100.0)
    delay_reason: Optional[str] = None
    supervisor_id: Optional[str] = None
    photo_path: Optional[str] = None


class CandidateMatch(BaseModel):
    candidate_id: str
    event_id: str
    schedule_id: str
    activity_id: str
    rank_order: int = Field(ge=1, le=3)
    match_tier: Optional[str] = None
    composite_confidence: float = Field(ge=0.0, le=1.0)
    semantic_score: Optional[float] = None
    fuzzy_score: Optional[float] = None
    location_score: Optional[float] = None
    discipline_score: Optional[float] = None
    supporting_signals: Optional[str] = None
    disqualifying_signals: Optional[str] = None


class ValidationIssue(BaseModel):
    issue_id: str
    event_id: str
    rule_code: Optional[str] = None
    severity: Optional[str] = None
    description: str


class PlannerDecision(BaseModel):
    decision_id: str
    event_id: str
    selected_activity_id: str
    action: Optional[str] = None
    approved_pct: Optional[float] = Field(default=None, ge=0.0, le=100.0)
    approved_qty: Optional[float] = None
    planner_id: str
    justification: str
    decided_at: Optional[datetime] = None


class ApprovedActual(BaseModel):
    actual_id: str
    decision_id: str
    event_id: str
    schedule_id: str
    activity_id: str
    actual_start: Optional[date] = None
    actual_finish: Optional[date] = None
    actual_pct_complete: Optional[float] = Field(
        default=None,
        ge=0.0,
        le=100.0,
    )
    actual_quantity: Optional[float] = None
    exported_at: Optional[datetime] = None
