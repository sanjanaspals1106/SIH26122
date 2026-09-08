import logging
from datetime import date, datetime
from typing import Any, List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status

from backend.shared.auth import UserProfile, require_role
from backend.shared.db import get_connection

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/dashboard", tags=["dashboard"])


def query_delay_reason_aggregates(conn: Optional[Any] = None) -> dict:
    """
    Query execution_events joined with planner_decisions to aggregate delay reasons
    for approved claims.

    Core business rules:
    1. For every execution_event, find its latest planner_decisions row using:
       decided_at DESC, decision_id DESC
    2. Only APPROVE and EDIT count. REJECT and HOLD do not count.
    3. Exclude NULL, empty string, and whitespace-only delay reasons.
    4. Group using TRIM(delay_reason).
    5. Sort by count DESC, delay_reason ASC.
    """
    query = """
        SELECT
            TRIM(ee.delay_reason) AS delay_reason,
            COUNT(*) AS count
        FROM execution_events ee
        JOIN planner_decisions pd ON pd.event_id = ee.event_id
        WHERE pd.decision_id = (
            SELECT pd2.decision_id
            FROM planner_decisions pd2
            WHERE pd2.event_id = ee.event_id
            ORDER BY pd2.decided_at DESC, pd2.decision_id DESC
            LIMIT 1
        )
        AND pd.action IN ('APPROVE', 'EDIT')
        AND ee.delay_reason IS NOT NULL
        AND TRIM(ee.delay_reason) != ''
        GROUP BY TRIM(ee.delay_reason)
        ORDER BY count DESC, delay_reason ASC
    """

    if conn is not None:
        rows = conn.execute(query).fetchall()
    else:
        with get_connection() as c:
            rows = c.execute(query).fetchall()

    delay_reasons: List[dict] = [
        {
            "delay_reason": str(row["delay_reason"]),
            "count": int(row["count"]),
        }
        for row in rows
    ]

    total = sum(item["count"] for item in delay_reasons)

    return {
        "delay_reasons": delay_reasons,
        "total_approved_delay_claims": total,
    }


@router.get("/health")
def health():
    return {"router": "dashboard", "status": "ok"}


@router.get("/delay-reasons")
def get_delay_reasons(
    current_user: UserProfile = Depends(require_role("SUPERVISOR")),
):
    """
    Aggregate execution_events.delay_reason across APPROVED/EDIT claims.
    Restricted to SUPERVISOR role.
    """
    try:
        return query_delay_reason_aggregates()
    except Exception as e:
        logger.error("Failed to query delay reasons for dashboard: %s", e)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve delay reasons",
        )
