"""
Member 5's backend surface — the human Approve/Edit/Reject/Hold review
action. This is the pipeline's core principle in code: a field report is a
claim, not a fact, and nothing reaches approved_actuals/export/P6 without
passing through this endpoint.

Every decision creates exactly one planner_decisions row (never from
viewing/matching/checking a claim). Only APPROVE and EDIT additionally
write to approved_actuals, via M6's upsert_approved_actual(). REJECT and
HOLD still get their planner_decisions row (the record a decision was
made) but never touch approved_actuals. A single event_id can accumulate
several planner_decisions rows over time (the HOLD-reopen loop) --
execution_events.status always reflects the most recently submitted
action.
"""

import logging
import uuid
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from backend.shared.actuals import upsert_approved_actual
from backend.shared.audit import write_audit_log
from backend.shared.auth import UserProfile, require_role
from backend.shared.db import get_connection
from backend.shared.schemas import DecisionRequest

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1", tags=["decisions"])

VALID_ACTIONS = {"APPROVE", "EDIT", "REJECT", "HOLD"}
# execution_events.status may only be entered from these states per the
# shared status-ownership rule -- VALIDATED/REVIEW_REQUIRED (first review)
# or HOLD (reopened, can be re-decided any number of times).
ELIGIBLE_SOURCE_STATUSES = {"VALIDATED", "REVIEW_REQUIRED", "HOLD"}
ACTION_TO_STATUS = {
    "APPROVE": "APPROVED",
    "EDIT": "EDITED",
    "REJECT": "REJECTED",
    "HOLD": "HOLD",
}
BULK_APPROVE_JUSTIFICATION = (
    "Bulk-approved: no open flags, confidence above threshold"
)


@router.get("/decisions/health")
def health():
    return {"router": "decisions", "status": "ok"}


def _fetch_claim(cur, event_id: str) -> Optional[dict]:
    cur.execute(
        "SELECT * FROM execution_events WHERE event_id = %s",
        (event_id,),
    )
    row = cur.fetchone()
    return dict(row) if row else None


def _record_decision(
    event_id: str,
    action: str,
    planner_id: str,
    justification: str,
    selected_activity_id: Optional[str],
    approved_pct: Optional[float],
    approved_qty: Optional[float],
) -> Dict[str, Any]:
    """
    Shared core for POST /decisions and POST /digest/bulk-approve: inserts
    exactly one planner_decisions row, updates execution_events.status,
    calls write_audit_log(), and (APPROVE/EDIT only) calls
    upsert_approved_actual(). Raises HTTPException on a genuine failure so
    callers can decide how to surface it (bulk-approve catches this
    per-claim; the single-decision endpoint lets it propagate).
    """
    action = action.upper()
    if action not in VALID_ACTIONS:
        raise HTTPException(
            status_code=422,
            detail=f"Invalid action '{action}'. Must be one of {sorted(VALID_ACTIONS)}.",
        )

    with get_connection() as conn:
        with conn.cursor() as cur:
            claim = _fetch_claim(cur, event_id)
            if not claim:
                raise HTTPException(
                    status_code=404,
                    detail=f"Claim '{event_id}' not found.",
                )

            if claim.get("status") not in ELIGIBLE_SOURCE_STATUSES:
                raise HTTPException(
                    status_code=409,
                    detail=(
                        f"Claim '{event_id}' has status "
                        f"'{claim.get('status')}', which is not eligible for "
                        f"a decision (must be one of {sorted(ELIGIBLE_SOURCE_STATUSES)})."
                    ),
                )

            # M5 pre-fills with matched_activity_id; planner may override
            # with any top-3 candidate or a typed ID.
            resolved_activity_id = selected_activity_id or claim.get("matched_activity_id")
            if not resolved_activity_id:
                raise HTTPException(
                    status_code=422,
                    detail=(
                        f"Claim '{event_id}' has no matched_activity_id and "
                        "no selected_activity_id was provided."
                    ),
                )

            decision_id = str(uuid.uuid4())
            before_state = dict(claim)

            cur.execute(
                """
                INSERT INTO planner_decisions (
                    decision_id, event_id, selected_activity_id, action,
                    approved_pct, approved_qty, planner_id, justification
                ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                """,
                (
                    decision_id,
                    event_id,
                    resolved_activity_id,
                    action,
                    approved_pct,
                    approved_qty,
                    planner_id,
                    justification,
                ),
            )

            new_status = ACTION_TO_STATUS[action]
            cur.execute(
                "UPDATE execution_events SET status = %s WHERE event_id = %s",
                (new_status, event_id),
            )

        conn.commit()

    try:
        write_audit_log(
            entity_type="execution_event",
            entity_id=event_id,
            action=action,
            actor_id=planner_id,
            before_state=before_state,
            after_state={
                "status": new_status,
                "selected_activity_id": resolved_activity_id,
                "decision_id": decision_id,
            },
            payload={"justification": justification},
        )
    except Exception as e:
        # Per the shared audit contract, a logging failure must not be
        # allowed to look like the decision itself failed -- the
        # planner_decisions row above is already committed.
        logger.error("write_audit_log failed for decision %s: %s", decision_id, e)

    approved_actual = None
    if action in ("APPROVE", "EDIT"):
        try:
            approved_actual = upsert_approved_actual(
                schedule_id=claim["schedule_id"],
                activity_id=resolved_activity_id,
                event_id=event_id,
                decision_id=decision_id,
            )
        except Exception as e:
            # The decision itself (planner_decisions + status) is already
            # committed above -- an actuals/export/P6 hiccup downstream
            # must not turn a recorded decision into a failed request.
            logger.error(
                "upsert_approved_actual failed for decision %s: %s",
                decision_id,
                e,
            )

    return {
        "decision_id": decision_id,
        "event_id": event_id,
        "action": action,
        "status": new_status,
        "selected_activity_id": resolved_activity_id,
        "approved_actual": approved_actual,
    }


@router.post("/decisions")
def create_decision(
    request: DecisionRequest,
    current_user: UserProfile = Depends(require_role("SUPERVISOR")),
):
    """
    POST /api/v1/decisions
    Record Approve/Edit/Reject/Hold with justification. Internally calls
    both write_audit_log() and upsert_approved_actual().
    """
    return _record_decision(
        event_id=request.event_id,
        action=request.action,
        planner_id=current_user.id,
        justification=request.justification,
        selected_activity_id=request.selected_activity_id,
        approved_pct=request.approved_pct,
        approved_qty=request.approved_qty,
    )


@router.get("/decisions")
def list_decisions(
    limit: int = 10,
    current_user: UserProfile = Depends(require_role("SUPERVISOR")),
):
    """
    GET /api/v1/decisions?limit=N
    Most recent planner_decisions rows, newest first -- read-only convenience
    for the Dashboard's "recent decisions" view. Not spec-required as a
    named endpoint, but planner_decisions is spec's own action log, so this
    is just a read over an already-existing table.
    """
    safe_limit = max(1, min(limit, 100))
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT * FROM planner_decisions
                ORDER BY decided_at DESC, decision_id DESC
                LIMIT %s
                """,
                (safe_limit,),
            )
            rows = [dict(r) for r in cur.fetchall()]
    return rows


@router.get("/digest")
def get_digest(
    date: Optional[str] = None,
    current_user: UserProfile = Depends(require_role("SUPERVISOR")),
):
    """
    GET /api/v1/digest?date=...
    Claims for a given day, flat and unfiltered by status -- the frontend
    groups by discipline and derives its own per-status counts (review
    queue vs. already-decided) client-side from this one list, the same way
    it already renders the Review Workspace queue. VALIDATED/REVIEW_REQUIRED/
    HOLD are the ones actually actionable from here; APPROVED/EDITED/
    REJECTED are included too so the day's full picture (KPI counts) is
    visible, not just the open queue.
    """
    with get_connection() as conn:
        with conn.cursor() as cur:
            if date:
                cur.execute(
                    """
                    SELECT * FROM execution_events
                    WHERE event_date = %s
                    ORDER BY discipline ASC, created_at ASC
                    """,
                    (date,),
                )
            else:
                cur.execute(
                    """
                    SELECT * FROM execution_events
                    ORDER BY discipline ASC, created_at ASC
                    """
                )
            rows = [dict(r) for r in cur.fetchall()]

    return rows


class BulkApproveRequest(BaseModel):
    event_ids: Optional[List[str]] = None


@router.post("/digest/bulk-approve")
def bulk_approve(
    request: BulkApproveRequest = BulkApproveRequest(),
    current_user: UserProfile = Depends(require_role("SUPERVISOR")),
):
    """
    POST /api/v1/digest/bulk-approve
    Approve multiple eligible claims at once. Only VALIDATED claims are
    eligible (no open flags, confidence above threshold -- both already
    guaranteed by M4's /check only ever producing VALIDATED when clean).
    If event_ids is omitted, every currently-VALIDATED claim is attempted.

    Failure behavior: independent per-claim commits, not atomic. One bad
    claim does not roll back the others.
    """
    with get_connection() as conn:
        with conn.cursor() as cur:
            if request.event_ids is not None:
                cur.execute(
                    """
                    SELECT event_id FROM execution_events
                    WHERE status = 'VALIDATED' AND event_id = ANY(%s)
                    """,
                    (request.event_ids,),
                )
            else:
                cur.execute(
                    "SELECT event_id FROM execution_events WHERE status = 'VALIDATED'"
                )
            candidate_ids = [r["event_id"] for r in cur.fetchall()]

    # Report any explicitly-requested ids that weren't eligible, alongside
    # per-claim failures encountered while processing eligible ones.
    approved: List[str] = []
    failed: List[Dict[str, str]] = []

    if request.event_ids is not None:
        ineligible = set(request.event_ids) - set(candidate_ids)
        for event_id in ineligible:
            failed.append({
                "event_id": event_id,
                "error": "Not eligible for bulk-approve (status is not VALIDATED).",
            })

    for event_id in candidate_ids:
        try:
            _record_decision(
                event_id=event_id,
                action="APPROVE",
                planner_id=current_user.id,
                justification=BULK_APPROVE_JUSTIFICATION,
                selected_activity_id=None,
                approved_pct=None,
                approved_qty=None,
            )
            approved.append(event_id)
        except HTTPException as e:
            failed.append({"event_id": event_id, "error": str(e.detail)})
        except Exception as e:
            failed.append({"event_id": event_id, "error": str(e)})

    return {"approved": approved, "failed": failed}
