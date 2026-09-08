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


def _parse_date(val: Any) -> Optional[date]:
    """
    Safely parse date from date, datetime, or ISO date string (YYYY-MM-DD).
    Returns None if value is None, empty, or unparseable.
    """
    if val is None:
        return None
    if isinstance(val, date) and not isinstance(val, datetime):
        return val
    if isinstance(val, datetime):
        return val.date()
    if isinstance(val, str):
        val = val.strip()
        if not val:
            return None
        try:
            return date.fromisoformat(val[:10])
        except (ValueError, TypeError):
            return None
    return None


def _calculate_duration_days(start_val: Any, finish_val: Any) -> Optional[int]:
    """
    Calculate duration in days between start and finish dates.
    Returns None if either date is missing or invalid.
    """
    start = _parse_date(start_val)
    finish = _parse_date(finish_val)
    if start is not None and finish is not None:
        return (finish - start).days
    return None


def _calculate_variance_days(
    planned_duration: Optional[int],
    actual_duration: Optional[int],
) -> Optional[int]:
    """
    Calculate variance in days: actual_duration - planned_duration.
    Positive variance indicates completion took longer than planned (delay).
    Negative variance indicates completion ahead of schedule.
    Returns None if either planned or actual duration is missing.
    """
    if planned_duration is not None and actual_duration is not None:
        return actual_duration - planned_duration
    return None


def query_institutional_memory(
    discipline: Optional[str] = None,
    conn: Optional[Any] = None,
) -> dict:
    """
    Query schedule_activities joined with approved_actuals to provide
    historical comparison of planned duration vs actual duration.

    Core business rules:
    1. Canonical join on (schedule_id, activity_id).
    2. Planned duration = planned_finish - planned_start (in days).
    3. Actual duration = actual_finish - actual_start (in days) from approved_actuals only.
    4. Missing or incomplete actuals produce null actual_duration and null variance_days.
    5. Filterable by discipline (case-insensitive).
    6. Deterministic ordering: activity_id ASC, schedule_id ASC.
    """
    query = """
        SELECT
            sa.activity_id,
            sa.discipline,
            sa.planned_start,
            sa.planned_finish,
            aa.actual_start,
            aa.actual_finish
        FROM schedule_activities sa
        LEFT JOIN approved_actuals aa
            ON aa.schedule_id = sa.schedule_id
           AND aa.activity_id = sa.activity_id
    """
    params = []

    if discipline is not None and discipline.strip():
        query += " WHERE UPPER(TRIM(sa.discipline)) = %s"
        params.append(discipline.strip().upper())

    query += " ORDER BY sa.activity_id ASC, sa.schedule_id ASC"

    if conn is not None:
        rows = conn.execute(query, tuple(params) if params else None).fetchall()
    else:
        with get_connection() as c:
            rows = c.execute(query, tuple(params) if params else None).fetchall()

    activities: List[dict] = []
    for row in rows:
        planned_dur = _calculate_duration_days(row["planned_start"], row["planned_finish"])
        actual_dur = _calculate_duration_days(row["actual_start"], row["actual_finish"])
        variance = _calculate_variance_days(planned_dur, actual_dur)

        activities.append(
            {
                "activity_id": str(row["activity_id"]),
                "discipline": str(row["discipline"]),
                "planned_duration": planned_dur,
                "actual_duration": actual_dur,
                "variance_days": variance,
            }
        )

    return {
        "activities": activities,
        "total_activities": len(activities),
    }


@router.get("/institutional-memory")
def get_institutional_memory(
    discipline: Optional[str] = Query(
        default=None,
        description="Filter activities by discipline (e.g. CIVIL, PIPING)",
    ),
    current_user: UserProfile = Depends(require_role("SUPERVISOR")),
):
    """
    Historical comparison of planned vs actual duration per activity.
    Filterable by discipline.
    Restricted to SUPERVISOR role.
    """
    try:
        return query_institutional_memory(discipline=discipline)
    except Exception as e:
        logger.error("Failed to query institutional memory: %s", e)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve institutional memory",
        )


def _calculate_historical_ratio_for_discipline(
    discipline: str,
    target_activity_id: Optional[str] = None,
    conn: Optional[Any] = None,
) -> Optional[float]:
    """
    Calculate the average historical actual_duration / planned_duration ratio
    for completed activities matching the specified discipline.

    Rules:
    - Only activities with valid planned_start and planned_finish (planned_duration > 0).
    - Only activities with valid approved_actuals actual_start and actual_finish (actual_duration >= 0).
    - Excludes target_activity_id from history to prevent self-contamination.
    - No division by zero.
    - Returns None if no qualifying historical completed activities exist.
    """
    query = """
        SELECT
            sa.activity_id,
            sa.planned_start,
            sa.planned_finish,
            aa.actual_start,
            aa.actual_finish
        FROM schedule_activities sa
        JOIN approved_actuals aa
            ON aa.schedule_id = sa.schedule_id
           AND aa.activity_id = sa.activity_id
        WHERE UPPER(TRIM(sa.discipline)) = %s
          AND aa.actual_start IS NOT NULL
          AND aa.actual_finish IS NOT NULL
    """
    disc_norm = discipline.strip().upper()
    if conn is not None:
        rows = conn.execute(query, (disc_norm,)).fetchall()
    else:
        with get_connection() as c:
            rows = c.execute(query, (disc_norm,)).fetchall()

    ratios: List[float] = []
    for row in rows:
        act_id = str(row["activity_id"])
        if target_activity_id and act_id == str(target_activity_id):
            continue

        p_dur = _calculate_duration_days(row["planned_start"], row["planned_finish"])
        a_dur = _calculate_duration_days(row["actual_start"], row["actual_finish"])

        if p_dur is not None and a_dur is not None and p_dur > 0 and a_dur >= 0:
            ratios.append(a_dur / p_dur)

    if not ratios:
        return None

    return sum(ratios) / len(ratios)


def query_forecast(
    activity_id: Optional[str] = None,
    discipline: Optional[str] = None,
    conn: Optional[Any] = None,
) -> dict:
    """
    Calculate historical-ratio forecast for an activity or a discipline.
    """
    if not activity_id and not discipline:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="At least one of 'activity_id' or 'discipline' must be provided.",
        )

    # Mode 1: Activity-level forecast
    if activity_id:
        target_query = """
            SELECT
                activity_id,
                schedule_id,
                discipline,
                planned_start,
                planned_finish
            FROM schedule_activities
            WHERE activity_id = %s
            ORDER BY schedule_id ASC
            LIMIT 1
        """
        if conn is not None:
            target_row = conn.execute(target_query, (activity_id,)).fetchone()
        else:
            with get_connection() as c:
                target_row = conn.execute(target_query, (activity_id,)).fetchone()

        if not target_row:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Activity '{activity_id}' not found",
            )

        act_discipline = str(target_row["discipline"])
        if discipline and act_discipline.strip().upper() != discipline.strip().upper():
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Activity '{activity_id}' does not match discipline '{discipline}'",
            )

        planned_dur = _calculate_duration_days(target_row["planned_start"], target_row["planned_finish"])
        avg_ratio = _calculate_historical_ratio_for_discipline(
            discipline=act_discipline,
            target_activity_id=activity_id,
            conn=conn,
        )

        if avg_ratio is not None and planned_dur is not None and planned_dur > 0:
            forecast_dur = int(round(planned_dur * avg_ratio))
            hist_ratio = round(avg_ratio, 3)
        else:
            forecast_dur = None
            hist_ratio = None

        return {
            "activity_id": str(target_row["activity_id"]),
            "discipline": act_discipline,
            "planned_duration": planned_dur,
            "historical_ratio": hist_ratio,
            "forecast_duration": forecast_dur,
        }

    # Mode 2: Discipline-level forecast
    disc_norm = discipline.strip().upper()
    avg_ratio = _calculate_historical_ratio_for_discipline(
        discipline=disc_norm,
        conn=conn,
    )

    activities_query = """
        SELECT
            activity_id,
            schedule_id,
            discipline,
            planned_start,
            planned_finish
        FROM schedule_activities
        WHERE UPPER(TRIM(discipline)) = %s
        ORDER BY activity_id ASC, schedule_id ASC
    """
    if conn is not None:
        rows = conn.execute(activities_query, (disc_norm,)).fetchall()
    else:
        with get_connection() as c:
            rows = c.execute(activities_query, (disc_norm,)).fetchall()

    activities: List[dict] = []
    hist_ratio = round(avg_ratio, 3) if avg_ratio is not None else None

    for r in rows:
        p_dur = _calculate_duration_days(r["planned_start"], r["planned_finish"])
        if avg_ratio is not None and p_dur is not None and p_dur > 0:
            f_dur = int(round(p_dur * avg_ratio))
        else:
            f_dur = None

        activities.append(
            {
                "activity_id": str(r["activity_id"]),
                "discipline": str(r["discipline"]),
                "planned_duration": p_dur,
                "historical_ratio": hist_ratio,
                "forecast_duration": f_dur,
            }
        )

    return {
        "discipline": disc_norm,
        "historical_ratio": hist_ratio,
        "activities": activities,
        "total_activities": len(activities),
    }


@router.get("/forecast")
def get_forecast(
    activity_id: Optional[str] = Query(
        default=None,
        description="Target activity ID for forecast",
    ),
    discipline: Optional[str] = Query(
        default=None,
        description="Target discipline for forecast",
    ),
    current_user: UserProfile = Depends(require_role("SUPERVISOR")),
):
    """
    Lightweight historical-ratio forecasting.
    Calculate actual_duration / planned_duration for completed historical activities
    of the same discipline, and apply that ratio to the target activity.
    Restricted to SUPERVISOR role.
    """
    try:
        return query_forecast(activity_id=activity_id, discipline=discipline)
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Failed to calculate forecast: %s", e)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to calculate forecast",
        )


