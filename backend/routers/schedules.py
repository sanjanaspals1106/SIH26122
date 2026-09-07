"""M1 Schedule API layer.

Thin FastAPI wrapper over the Phase 1 parser/validator
(backend.shared.schedule) and Phase 2 repository (backend.shared.schedule_repository):

    POST /api/v1/schedules                                   request -> parser -> repository -> PostgreSQL -> active FAISS index
    GET  /api/v1/schedules                                    list schedules from PostgreSQL
    GET  /api/v1/schedules/{schedule_id}                       one schedule from PostgreSQL
    GET  /api/v1/schedules/{schedule_id}/activities             a schedule's activities from PostgreSQL
    GET  /api/v1/schedules/{schedule_id}/activities/{activity_id}  one activity from PostgreSQL
    GET  /api/v1/schedules/{schedule_id}/dependencies            a schedule's dependency pairs from PostgreSQL

No matching (EXACT_ID/EXACT_ASSET/HYBRID_FALLBACK/tiering), embeddings-as-a-
service, OCR, or LLM extraction here — those belong to later phases.
"""

from __future__ import annotations

import logging
from datetime import date
from typing import Optional

from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel

from backend.shared import schedule_index
from backend.shared.schedule import parse_schedule_csv
from backend.shared.schedule_repository import (
    ScheduleAlreadyExistsError,
    SchedulePersistenceError,
    get_schedule,
    get_schedule_activity,
    list_schedule_activities,
    list_schedule_dependencies,
    list_schedules,
    save_schedule,
)
from backend.shared.schemas import Schedule, ScheduleActivity, ScheduleDependency

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/schedules", tags=["schedules"])


@router.get("/health")
def health():
    return {"router": "schedules", "status": "ok"}


class ScheduleCreateRequest(BaseModel):
    schedule_id: str
    project_name: str
    data_date: Optional[date] = None
    source_format: Optional[str] = "csv"
    csv_content: str


class ScheduleCreateResponse(BaseModel):
    schedule_id: str
    project_name: str
    data_date: Optional[date] = None
    source_format: Optional[str] = None
    activity_count: int
    dependency_count: int
    indexed: bool
    index_error: Optional[str] = None


def _parse_errors_detail(message: str, errors) -> dict:
    return {
        "message": message,
        "errors": [
            {
                "row": e.row_number,
                "field": e.field_name,
                "message": e.message,
                "activity_id": e.activity_id,
            }
            for e in errors
        ],
    }


@router.post("", response_model=ScheduleCreateResponse, status_code=status.HTTP_201_CREATED)
def create_schedule(request: ScheduleCreateRequest) -> ScheduleCreateResponse:
    parse_result = parse_schedule_csv(request.csv_content, schedule_id=request.schedule_id)

    if not parse_result.is_valid:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=_parse_errors_detail("schedule CSV failed validation", parse_result.errors),
        )

    if not parse_result.activities:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=_parse_errors_detail("schedule CSV contains no activities", []),
        )

    schedule = Schedule(
        schedule_id=request.schedule_id,
        project_name=request.project_name,
        data_date=request.data_date,
        source_format=request.source_format,
    )

    try:
        activity_count = save_schedule(schedule, parse_result)
    except ScheduleAlreadyExistsError as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc
    except SchedulePersistenceError as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(exc)
        ) from exc

    # PostgreSQL is authoritative and already committed at this point.
    # FAISS indexing is best-effort: a failure here must not undo the
    # successful persistence, so it is reported back rather than raised.
    # On success, this schedule becomes the single active (in-memory) FAISS
    # index, replacing whichever schedule was active before — see
    # backend.shared.schedule_index for the single-active-schedule contract.
    indexed = False
    index_error: Optional[str] = None
    try:
        schedule_index.build_index(schedule.schedule_id)
        indexed = True
    except Exception as exc:  # noqa: BLE001 - deliberately broad: any indexing failure must surface, not crash the request
        index_error = str(exc)
        logger.error(
            "FAISS indexing failed for schedule_id=%s after successful persistence: %s",
            schedule.schedule_id, exc,
        )

    return ScheduleCreateResponse(
        schedule_id=schedule.schedule_id,
        project_name=schedule.project_name,
        data_date=schedule.data_date,
        source_format=schedule.source_format,
        activity_count=activity_count,
        dependency_count=len(parse_result.dependencies),
        indexed=indexed,
        index_error=index_error,
    )


@router.get("", response_model=list[Schedule])
def get_schedules() -> list[Schedule]:
    return list_schedules()


@router.get("/{schedule_id}", response_model=Schedule)
def get_schedule_by_id(schedule_id: str) -> Schedule:
    schedule = get_schedule(schedule_id)
    if schedule is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"schedule_id {schedule_id!r} not found",
        )
    return schedule


@router.get("/{schedule_id}/activities", response_model=list[ScheduleActivity])
def get_activities_for_schedule(schedule_id: str) -> list[ScheduleActivity]:
    schedule = get_schedule(schedule_id)
    if schedule is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"schedule_id {schedule_id!r} not found",
        )
    return list_schedule_activities(schedule_id)


@router.get("/{schedule_id}/activities/{activity_id}", response_model=ScheduleActivity)
def get_activity_by_id(schedule_id: str, activity_id: str) -> ScheduleActivity:
    schedule = get_schedule(schedule_id)
    if schedule is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"schedule_id {schedule_id!r} not found",
        )

    activity = get_schedule_activity(schedule_id, activity_id)
    if activity is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"activity_id {activity_id!r} not found in schedule_id {schedule_id!r}",
        )
    return activity


@router.get("/{schedule_id}/dependencies", response_model=list[ScheduleDependency])
def get_dependencies_for_schedule(schedule_id: str) -> list[ScheduleDependency]:
    schedule = get_schedule(schedule_id)
    if schedule is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"schedule_id {schedule_id!r} not found",
        )
    return list_schedule_dependencies(schedule_id)
