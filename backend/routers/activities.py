import logging
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException, status

from backend.shared.auth import UserProfile, require_role
from backend.shared.db import get_connection

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/activities", tags=["activities"])


def _execute(conn: Optional[Any], query: str, params: tuple = ()):
    if conn is not None:
        return conn.execute(query, params)
    with get_connection() as c:
        return c.execute(query, params)


def _resolve_activity(activity_id: str, schedule_id: Optional[str], conn: Optional[Any]) -> Dict[str, Any]:
    """
    ISS-23: activity metadata (and whether the activity exists at all) comes
    from schedule_activities, never inferred only from execution_events -- an
    activity with zero events must still 200 with its real metadata, and a
    genuinely nonexistent activity_id must 404 rather than a silent empty
    timeline. Ambiguity (the same activity_id in more than one schedule, no
    schedule_id given) is a 409, same convention as routers/graph.py and
    routers/schedule.py's impact-preview.
    """
    query = "SELECT * FROM schedule_activities WHERE activity_id = %s"
    params: List[Any] = [activity_id]
    if schedule_id:
        query += " AND schedule_id = %s"
        params.append(schedule_id)

    rows = _execute(conn, query, tuple(params)).fetchall()
    if not rows:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Activity '{activity_id}' not found",
        )
    if not schedule_id and len(rows) > 1:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Activity '{activity_id}' exists in multiple schedules; provide schedule_id.",
        )
    return dict(rows[0])


def query_activity_history(
    activity_id: str,
    schedule_id: Optional[str] = None,
    conn: Optional[Any] = None,
) -> dict:
    """
    Retrieve chronological activity history timeline for an activity.

    Core business rules:
    0. The activity itself must exist in schedule_activities (see
       _resolve_activity) -- 404 for a genuinely unknown activity_id, 409 if
       activity_id is ambiguous across schedules and no schedule_id was given.
       Its schedule_id then scopes every query below, so a same-named
       activity_id in a different schedule can never leak into this timeline.
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
    5. Return activity metadata + {"timeline": [...]} -- an empty timeline is
       a legitimate "no history yet" outcome for a real activity, distinct
       from the activity not existing at all.
    """
    activity_row = _resolve_activity(activity_id, schedule_id, conn)
    resolved_schedule_id = str(activity_row["schedule_id"])

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
        WHERE ee.schedule_id = %s
          AND (
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

    # planner_decisions has no schedule_id column -- scope through its event's
    # schedule_id instead, so a decision on another schedule's same-named
    # activity_id can never appear here.
    decision_query = """
        SELECT
            pd.decision_id,
            pd.event_id,
            pd.selected_activity_id,
            pd.action,
            pd.approved_pct,
            pd.approved_qty,
            pd.planner_id,
            pd.justification,
            pd.decided_at
        FROM planner_decisions pd
        JOIN execution_events ee ON ee.event_id = pd.event_id
        WHERE pd.selected_activity_id = %s AND ee.schedule_id = %s
        ORDER BY pd.decided_at ASC, pd.decision_id ASC
    """

    actuals_query = """
        SELECT
            actual_id,
            decision_id,
            event_id,
            schedule_id,
            activity_id,
            actual_start,
            actual_finish,
            actual_pct_complete,
            actual_quantity,
            created_at
        FROM approved_actuals
        WHERE activity_id = %s AND schedule_id = %s
        ORDER BY created_at ASC, actual_id ASC
    """

    event_rows = _execute(
        conn, events_query, (resolved_schedule_id, activity_id, activity_id, activity_id)
    ).fetchall()
    decision_rows = _execute(conn, decision_query, (activity_id, resolved_schedule_id)).fetchall()
    try:
        actual_rows = _execute(conn, actuals_query, (activity_id, resolved_schedule_id)).fetchall()
    except Exception:
        actual_rows = []


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

    decisions_list: List[dict] = []
    for d in decision_rows:
        dec_ts = str(d["decided_at"]) if d["decided_at"] is not None else None
        d_dict = {
            "type": "planner_decision",
            "decision_id": str(d["decision_id"]),
            "event_id": str(d["event_id"]),
            "selected_activity_id": str(d["selected_activity_id"]),
            "action": str(d["action"]),
            "approved_pct": float(d["approved_pct"]) if d["approved_pct"] is not None else None,
            "approved_qty": float(d["approved_qty"]) if d["approved_qty"] is not None else None,
            "planner_id": str(d["planner_id"]) if d["planner_id"] is not None else None,
            "justification": str(d["justification"]) if d["justification"] is not None else "",
            "timestamp": dec_ts,
        }
        decisions_list.append(d_dict)
        timeline.append(d_dict)

    actuals_list: List[dict] = []
    for a in actual_rows:
        act_ts = str(a["created_at"]) if a["created_at"] is not None else (
            str(a["actual_finish"]) if a["actual_finish"] is not None else (
                str(a["actual_start"]) if a["actual_start"] is not None else None
            )
        )
        a_dict = {
            "type": "approved_actual",
            "actual_id": str(a["actual_id"]),
            "decision_id": str(a["decision_id"]) if a["decision_id"] is not None else None,
            "event_id": str(a["event_id"]) if a["event_id"] is not None else None,
            "schedule_id": str(a["schedule_id"]) if a["schedule_id"] is not None else None,
            "activity_id": str(a["activity_id"]),
            "actual_start": str(a["actual_start"]) if a["actual_start"] is not None else None,
            "actual_finish": str(a["actual_finish"]) if a["actual_finish"] is not None else None,
            "actual_pct_complete": float(a["actual_pct_complete"]) if a["actual_pct_complete"] is not None else None,
            "actual_quantity": float(a["actual_quantity"]) if a["actual_quantity"] is not None else None,
            "timestamp": act_ts,
        }
        actuals_list.append(a_dict)
        timeline.append(a_dict)

    timeline.sort(
        key=lambda item: (
            str(item.get("timestamp") or ""),
            0 if item.get("type") == "execution_event" else (1 if item.get("type") == "planner_decision" else 2),
            str(item.get("event_id") or item.get("decision_id") or item.get("actual_id") or ""),
        )
    )

    return {
        "activity_id": str(activity_id),
        "schedule_id": resolved_schedule_id,
        "activity_name": str(activity_row["activity_name"]) if activity_row.get("activity_name") is not None else None,
        "discipline": str(activity_row["discipline"]) if activity_row.get("discipline") is not None else None,
        "location": str(activity_row["location"]) if activity_row.get("location") is not None else None,
        "wbs_code": str(activity_row["wbs_code"]) if activity_row.get("wbs_code") is not None else None,
        "planned_start": str(activity_row["planned_start"]) if activity_row.get("planned_start") is not None else None,
        "planned_finish": str(activity_row["planned_finish"]) if activity_row.get("planned_finish") is not None else None,
        "timeline": timeline,
    }



@router.get("/{activity_id}/history")
def get_activity_history(
    activity_id: str,
    schedule_id: Optional[str] = None,
    current_user: UserProfile = Depends(require_role("SUPERVISOR")),
):
    """
    Chronological activity history timeline for an activity, plus the
    activity's own metadata (so "exists with zero events" and "does not
    exist" are distinguishable -- see query_activity_history/ISS-23).
    Restricted to SUPERVISOR role.
    """
    try:
        return query_activity_history(activity_id=activity_id, schedule_id=schedule_id)
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Failed to query activity history for '%s': %s", activity_id, e)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to retrieve activity history for '{activity_id}'",
        )
