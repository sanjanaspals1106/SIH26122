from typing import Optional

from backend.shared.db import get_connection


def get_approved_actual(
    schedule_id: str,
    activity_id: str,
) -> Optional[dict]:
    """
    Return the latest approved actual for an activity.

    Approved actuals are the authoritative progress values.
    """
    with get_connection() as conn:
        row = conn.execute(
            """
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
                exported_at,
                created_at
            FROM approved_actuals
            WHERE schedule_id = ?
              AND activity_id = ?
            """,
            (schedule_id, activity_id),
        ).fetchone()

    return dict(row) if row else None


def get_approved_pct(
    schedule_id: str,
    activity_id: str,
) -> float:
    """
    Return approved percentage complete.

    Returns 0.0 when no approved actual exists.
    """
    actual = get_approved_actual(schedule_id, activity_id)

    if not actual:
        return 0.0

    return float(actual["actual_pct_complete"] or 0.0)
