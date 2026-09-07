"""M1 baseline schedule persistence.

Writes a validated ScheduleParseResult (backend.shared.schedule) and its
Schedule metadata (backend.shared.schemas.Schedule) into the existing
`schedules` and `schedule_activities` tables (backend/models/schema.sql).
Also provides the read-side lookups the M1 Schedule API layer
(backend.routers.schedules) needs to serve baseline schedule data back out
of PostgreSQL.

Reuses backend.shared.db.get_connection() — no second DB abstraction, no ORM.
schedule_dependencies persistence is out of scope for this phase.
"""

from __future__ import annotations

from typing import Optional

import psycopg

from backend.shared.db import get_connection
from backend.shared.schedule import ScheduleParseResult
from backend.shared.schemas import Schedule, ScheduleActivity


class ScheduleAlreadyExistsError(Exception):
    """A schedule_id that already exists in `schedules`.

    Duplicate imports are rejected rather than silently overwritten or
    merged, so an existing schedule's activities can never be silently
    corrupted by a re-import.
    """

    def __init__(self, schedule_id: str) -> None:
        self.schedule_id = schedule_id
        super().__init__(
            f"schedule_id {schedule_id!r} already exists; duplicate schedule "
            "imports are rejected rather than overwritten"
        )


class SchedulePersistenceError(Exception):
    """A database error occurred while persisting a schedule. Nothing was committed."""


_INSERT_SCHEDULE_SQL = """
    INSERT INTO schedules (schedule_id, project_name, data_date, source_format)
    VALUES (%(schedule_id)s, %(project_name)s, %(data_date)s, %(source_format)s)
"""

_INSERT_ACTIVITY_SQL = """
    INSERT INTO schedule_activities (
        schedule_id, activity_id, activity_name, wbs_code, discipline,
        location, asset_tag, planned_start, planned_finish,
        planned_quantity, uom, baseline_pct_complete
    ) VALUES (
        %(schedule_id)s, %(activity_id)s, %(activity_name)s, %(wbs_code)s, %(discipline)s,
        %(location)s, %(asset_tag)s, %(planned_start)s, %(planned_finish)s,
        %(planned_quantity)s, %(uom)s, %(baseline_pct_complete)s
    )
"""


def save_schedule(schedule: Schedule, parse_result: ScheduleParseResult) -> int:
    """Persist a schedule and its activities in a single transaction.

    `parse_result` must already be valid (parse_result.is_valid) — this
    function re-validates nothing; validation is backend.shared.schedule's
    job. All rows are written atomically: if any insert fails (including an
    already-existing schedule_id), nothing is committed.

    Returns the number of activities persisted.

    Raises:
        ValueError: schedule/parse_result mismatch, unvalidated or empty
            parse_result.
        ScheduleAlreadyExistsError: schedule.schedule_id already exists.
        SchedulePersistenceError: any other database error.
    """
    if schedule.schedule_id != parse_result.schedule_id:
        raise ValueError(
            f"schedule.schedule_id ({schedule.schedule_id!r}) does not match "
            f"parse_result.schedule_id ({parse_result.schedule_id!r})"
        )

    if not parse_result.is_valid:
        raise ValueError(
            "cannot persist a schedule with validation errors: "
            f"{[e.describe() for e in parse_result.errors]}"
        )

    if not parse_result.activities:
        raise ValueError("cannot persist a schedule with zero activities")

    try:
        with get_connection() as conn:
            existing = conn.execute(
                "SELECT 1 FROM schedules WHERE schedule_id = %s",
                (schedule.schedule_id,),
            ).fetchone()
            if existing:
                raise ScheduleAlreadyExistsError(schedule.schedule_id)

            conn.execute(_INSERT_SCHEDULE_SQL, schedule.model_dump())

            for activity in parse_result.activities:
                conn.execute(_INSERT_ACTIVITY_SQL, activity.model_dump())

            conn.commit()
    except ScheduleAlreadyExistsError:
        raise
    except psycopg.Error as exc:
        raise SchedulePersistenceError(str(exc)) from exc

    return len(parse_result.activities)


_SELECT_SCHEDULE_SQL = """
    SELECT schedule_id, project_name, data_date, source_format
    FROM schedules
    WHERE schedule_id = %s
"""

_LIST_SCHEDULES_SQL = """
    SELECT schedule_id, project_name, data_date, source_format
    FROM schedules
    ORDER BY schedule_id
"""

_SELECT_ACTIVITY_COLUMNS_SQL = """
    SELECT
        schedule_id, activity_id, activity_name, wbs_code, discipline,
        location, asset_tag, planned_start, planned_finish,
        planned_quantity, uom, baseline_pct_complete
    FROM schedule_activities
"""


def get_schedule(schedule_id: str) -> Optional[Schedule]:
    """Look up one schedule's metadata by schedule_id, or None if it does not exist."""
    with get_connection() as conn:
        row = conn.execute(_SELECT_SCHEDULE_SQL, (schedule_id,)).fetchone()

    return Schedule(**row) if row is not None else None


def list_schedules() -> list[Schedule]:
    """List all schedules, ordered by schedule_id."""
    with get_connection() as conn:
        rows = conn.execute(_LIST_SCHEDULES_SQL).fetchall()

    return [Schedule(**row) for row in rows]


def list_schedule_activities(schedule_id: str) -> list[ScheduleActivity]:
    """List every activity belonging to a schedule, ordered by activity_id.

    Returns an empty list if the schedule has no activities (including if
    the schedule_id itself does not exist) — callers that need to
    distinguish "unknown schedule" from "schedule with no activities" should
    check get_schedule() first.
    """
    with get_connection() as conn:
        rows = conn.execute(
            _SELECT_ACTIVITY_COLUMNS_SQL + " WHERE schedule_id = %s ORDER BY activity_id",
            (schedule_id,),
        ).fetchall()

    return [ScheduleActivity(**row) for row in rows]


def get_schedule_activity(schedule_id: str, activity_id: str) -> Optional[ScheduleActivity]:
    """Look up one activity by (schedule_id, activity_id), or None if it does not exist."""
    with get_connection() as conn:
        row = conn.execute(
            _SELECT_ACTIVITY_COLUMNS_SQL + " WHERE schedule_id = %s AND activity_id = %s",
            (schedule_id, activity_id),
        ).fetchone()

    return ScheduleActivity(**row) if row is not None else None
