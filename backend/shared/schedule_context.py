"""
The one canonical active-schedule resolution rule for every schedule-scoped
router (PRD v6 Section 2 / ISS-02 / ISS-05: "there must be a single
authoritative way for the application to determine active_schedule_id").

Any endpoint that needs "the current schedule" and isn't anchored to a
specific entity (an activity_id, an event_id -- those resolve schedule
identity from the entity itself, see routers/graph.py and routers/schedule.py)
calls resolve_schedule_id() instead of guessing or hardcoding an id:

  - no schedule_id given -> the one canonical active schedule
    (backend.shared.schedule_repository.get_active_schedule)
  - schedule_id given -> validated to actually exist
  - either way, an unresolvable schedule is a 404, never a silent fallback
    to a stale/guessed id.
"""
from __future__ import annotations

from typing import Optional

from fastapi import HTTPException, status

from backend.shared.schedule_repository import get_active_schedule, get_schedule


def resolve_schedule_id(schedule_id: Optional[str]) -> str:
    if schedule_id:
        if get_schedule(schedule_id) is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Schedule '{schedule_id}' not found",
            )
        return schedule_id
    active = get_active_schedule()
    if active is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No active schedule exists",
        )
    return active.schedule_id
