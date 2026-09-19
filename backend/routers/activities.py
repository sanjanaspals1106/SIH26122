import logging
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException, status

from backend.shared.auth import UserProfile, require_role
from backend.shared.db import get_connection

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/activities", tags=["activities"])


def query_activity_history(
    activity_id: str,
    conn: Optional[Any] = None,
) -> dict:
    """
    Retrieve chronological activity history timeline for an activity.

    Core business rules:
    1. For the specified activity_id, retrieve all linked execution_events:
       - Where the event's latest planner_decision has selected_activity_id = activity_id, OR
       - Where no planner_decision exists, but matched_activity_id or reported_activity_id = activity_id.
    2. For every linked execution_event, retrieve all linked source_references.
    3. Retrieve the single final planner_decision for the activity:
       - Ordered by decided_at DESC, decision_id DESC LIMIT 1.
    4. Assemble a unified timeline ordered chronologically:
       - timestamp ASC
       - type == "execution_event" before "planner_decision"
       - event_id / decision_id deterministic tie-breaker.
    5. Return {"activity_id": activity_id, "timeline": [...]}.
    """
    events_query = """
        SELECT
            ee.event_id,
            ee.document_id,
            ee.schedule_id,
            ee.event_date,
            ee.raw_claim_text,
            ee.input_channel,
            ee.language_detected,
            ee.reported_activity_id,
            ee.matched_activity_id,
            ee.discipline,
            ee.action,
            ee.event_type,
            ee.claim_mode,
            ee.asset_tag,
            ee.location,
            ee.claimed_quantity,
            ee.claimed_uom,
            ee.claimed_pct,
            ee.delay_reason,
            ee.supervisor_id,
            ee.photo_path,
            ee.status,
            ee.created_at
        FROM execution_events ee
        WHERE (
            ee.event_id IN (
                SELECT pd.event_id
                FROM planner_decisions pd
                WHERE pd.selected_activity_id = %s
                  AND pd.decision_id = (
                      SELECT pd2.decision_id
                      FROM planner_decisions pd2
                      WHERE pd2.event_id = pd.event_id
                      ORDER BY pd2.decided_at DESC, pd2.decision_id DESC
                      LIMIT 1
                  )
            )
            OR (
                NOT EXISTS (
                    SELECT 1 FROM planner_decisions pd3 WHERE pd3.event_id = ee.event_id
                )
                AND (ee.matched_activity_id = %s OR ee.reported_activity_id = %s)
            )
        )
        ORDER BY ee.event_date ASC, ee.created_at ASC, ee.event_id ASC
    """

    decision_query = """
        SELECT
            decision_id,
            event_id,
            selected_activity_id,
            action,
            approved_pct,
            approved_qty,
            planner_id,
            justification,
            decided_at
        FROM planner_decisions
        WHERE selected_activity_id = %s
        ORDER BY decided_at DESC, decision_id DESC
        LIMIT 1
    """

    if conn is not None:
        event_rows = conn.execute(events_query, (activity_id, activity_id, activity_id)).fetchall()
        decision_row = conn.execute(decision_query, (activity_id,)).fetchone()
    else:
        with get_connection() as c:
            event_rows = c.execute(events_query, (activity_id, activity_id, activity_id)).fetchall()
            decision_row = c.execute(decision_query, (activity_id,)).fetchone()

    event_ids = [str(r["event_id"]) for r in event_rows]

    refs_by_event: Dict[str, List[dict]] = {}
    if event_ids:
        placeholders = ", ".join(["%s"] * len(event_ids))
        refs_query = f"""
            SELECT
                reference_id,
                event_id,
                file_name,
                sheet_name,
                row_cell_ref,
                message_id,
                raw_snippet
            FROM source_references
            WHERE event_id IN ({placeholders})
            ORDER BY reference_id ASC
        """
        if conn is not None:
            ref_rows = conn.execute(refs_query, tuple(event_ids)).fetchall()
        else:
            with get_connection() as c:
                ref_rows = c.execute(refs_query, tuple(event_ids)).fetchall()

        for ref in ref_rows:
            e_id = str(ref["event_id"])
            if e_id not in refs_by_event:
                refs_by_event[e_id] = []
            refs_by_event[e_id].append(
                {
                    "reference_id": str(ref["reference_id"]),
                    "file_name": ref["file_name"] if ref["file_name"] is not None else None,
                    "sheet_name": ref["sheet_name"] if ref["sheet_name"] is not None else None,
                    "row_cell_ref": ref["row_cell_ref"] if ref["row_cell_ref"] is not None else None,
                    "message_id": ref["message_id"] if ref["message_id"] is not None else None,
                    "raw_snippet": str(ref["raw_snippet"] or ""),
                }
            )

    timeline: List[dict] = []

    for event in event_rows:
        ts = None
        if event["created_at"] is not None:
            ts = str(event["created_at"])
        elif event["event_date"] is not None:
            ts = str(event["event_date"])

        e_id = str(event["event_id"])
        timeline.append(
            {
                "type": "execution_event",
                "event_id": e_id,
                "schedule_id": str(event["schedule_id"]) if event["schedule_id"] is not None else None,
                "event_date": str(event["event_date"]) if event["event_date"] is not None else None,
                "raw_claim_text": str(event["raw_claim_text"] or ""),
                "claim_mode": str(event["claim_mode"]) if event["claim_mode"] is not None else "CUMULATIVE_PCT",
                "claimed_pct": float(event["claimed_pct"]) if event["claimed_pct"] is not None else None,
                "claimed_quantity": float(event["claimed_quantity"]) if event["claimed_quantity"] is not None else None,
                "delay_reason": str(event["delay_reason"]) if event["delay_reason"] is not None else None,
                "status": str(event["status"]) if event["status"] is not None else None,
                "timestamp": ts,
                "source_references": refs_by_event.get(e_id, []),
            }
        )

    if decision_row:
        dec_ts = str(decision_row["decided_at"]) if decision_row["decided_at"] is not None else None
        timeline.append(
            {
                "type": "planner_decision",
                "decision_id": str(decision_row["decision_id"]),
                "event_id": str(decision_row["event_id"]),
                "selected_activity_id": str(decision_row["selected_activity_id"]),
                "action": str(decision_row["action"]),
                "approved_pct": float(decision_row["approved_pct"]) if decision_row["approved_pct"] is not None else None,
                "approved_qty": float(decision_row["approved_qty"]) if decision_row["approved_qty"] is not None else None,
                "justification": str(decision_row["justification"]) if decision_row["justification"] is not None else "",
                "timestamp": dec_ts,
            }
        )

    timeline.sort(
        key=lambda item: (
            str(item.get("timestamp") or ""),
            0 if item.get("type") == "execution_event" else 1,
            str(item.get("event_id") if item.get("type") == "execution_event" else item.get("decision_id")),
        )
    )

    return {
        "activity_id": str(activity_id),
        "timeline": timeline,
    }


@router.get("/{activity_id}/history")
def get_activity_history(
    activity_id: str,
    current_user: UserProfile = Depends(require_role("SUPERVISOR")),
):
    """
    Chronological activity history timeline for an activity.
    Combines linked execution_events, their source_references, and the final planner_decision.
    Restricted to SUPERVISOR role.
    """
    try:
        return query_activity_history(activity_id=activity_id)
    except Exception as e:
        logger.error("Failed to query activity history for '%s': %s", activity_id, e)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to retrieve activity history for '{activity_id}'",
        )
