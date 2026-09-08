import logging
from datetime import date, datetime, timedelta
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status

from backend.shared.auth import UserProfile, require_role
from backend.shared.db import get_connection

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/schedule", tags=["schedule"])


@router.get("/health")
def health():
    return {"router": "schedule", "status": "ok"}


def _parse_date(val: Any) -> Optional[date]:
    """Parse a date from string, date, or datetime object."""
    if val is None:
        return None
    if isinstance(val, datetime):
        return val.date()
    if isinstance(val, date):
        return val
    try:
        return datetime.strptime(str(val)[:10], "%Y-%m-%d").date()
    except (ValueError, TypeError):
        return None


def query_impact_preview(
    activity_id: str,
    delay_days: int,
    conn: Optional[Any] = None,
) -> dict:
    """
    Lightweight, one-level downstream impact preview for an activity and hypothetical delay.

    Rules:
    1. Validate delay_days >= 0.
    2. Look up target activity in schedule_activities to verify existence and resolve schedule_id.
       If not found, raise 404 Not Found.
    3. Traverse schedule_dependencies exactly ONE level for direct successors where:
       - sd.schedule_id = target_schedule_id
       - sd.predecessor_activity_id = activity_id
       - UPPER(TRIM(sd.relationship_type)) = 'FS'
    4. Join schedule_activities to retrieve successor planned_start.
    5. Calculate shifted_earliest_start = planned_start + delay_days.
    6. Order deterministically by sd.successor_activity_id ASC.
    7. No schedule modification; purely hypothetical computation.
    """
    if delay_days is None or delay_days < 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="delay_days must be a non-negative integer",
        )

    target_query = """
        SELECT activity_id, schedule_id, activity_name, planned_start, planned_finish
        FROM schedule_activities
        WHERE activity_id = %s
    """

    if conn is not None:
        target_row = conn.execute(target_query, (activity_id,)).fetchone()
    else:
        with get_connection() as c:
            target_row = c.execute(target_query, (activity_id,)).fetchone()

    if not target_row:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Activity '{activity_id}' not found",
        )

    schedule_id = target_row["schedule_id"]

    successors_query = """
        SELECT DISTINCT
            sd.successor_activity_id,
            sd.relationship_type,
            sa.planned_start AS successor_planned_start
        FROM schedule_dependencies sd
        JOIN schedule_activities sa
            ON sd.schedule_id = sa.schedule_id
            AND sd.successor_activity_id = sa.activity_id
        WHERE sd.schedule_id = %s
          AND sd.predecessor_activity_id = %s
          AND UPPER(TRIM(sd.relationship_type)) = 'FS'
        ORDER BY sd.successor_activity_id ASC
    """

    if conn is not None:
        succ_rows = conn.execute(successors_query, (schedule_id, activity_id)).fetchall()
    else:
        with get_connection() as c:
            succ_rows = c.execute(successors_query, (schedule_id, activity_id)).fetchall()

    impacts: List[Dict[str, Any]] = []

    for row in succ_rows:
        succ_act_id = str(row["successor_activity_id"])
        rel_type = str(row["relationship_type"]).strip().upper() if row["relationship_type"] else "FS"
        orig_start_date = _parse_date(row["successor_planned_start"])

        if orig_start_date is None:
            continue

        shifted_start_date = orig_start_date + timedelta(days=delay_days)

        impacts.append({
            "successor_activity_id": succ_act_id,
            "dependency_type": rel_type,
            "original_earliest_start": orig_start_date.isoformat(),
            "shifted_earliest_start": shifted_start_date.isoformat(),
        })

    return {
        "activity_id": activity_id,
        "delay_days": delay_days,
        "impacts": impacts,
    }


@router.get("/{activity_id}/impact-preview")
def get_impact_preview(
    activity_id: str,
    delay_days: int = Query(..., ge=0, description="Hypothetical delay in days"),
    current_user: UserProfile = Depends(require_role("SUPERVISOR")),
):
    """
    Downstream schedule impact preview for an activity and hypothetical delay.
    One-level traversal of direct FS successors with shifted earliest-start estimate.
    Restricted to SUPERVISOR role.
    """
    try:
        return query_impact_preview(activity_id=activity_id, delay_days=delay_days)
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Failed to generate impact preview for '%s': %s", activity_id, e)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to generate impact preview for '{activity_id}'",
        )
