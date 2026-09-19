import logging
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/mock-p6", tags=["mock-p6"])

_received_payloads: List[Dict[str, Any]] = []


def get_received_payloads() -> List[Dict[str, Any]]:
    return list(_received_payloads)


def clear_received_payloads() -> None:
    global _received_payloads
    _received_payloads.clear()


@router.get("/health")
def health():
    return {"router": "mock-p6", "status": "ok"}


class P6ActivityPayload(BaseModel):
    Id: str
    StartDate: Optional[str] = None
    FinishDate: Optional[str] = None
    PercentComplete: Optional[float] = None


@router.post("/activities/{activity_id}")
def update_activity(activity_id: str, payload: P6ActivityPayload):
    """
    Local mock endpoint standing in for a real P6 EPPM REST API server.
    Accepts canonical P6 request shape: {"Id", "StartDate", "FinishDate", "PercentComplete"}.
    Validates that body Id matches path activity_id.
    """
    if payload.Id != activity_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Payload Id '{payload.Id}' does not match path activity_id '{activity_id}'",
        )

    payload_dict = payload.model_dump(exclude_unset=True)
    _received_payloads.append(payload_dict)

    return {
        "status": "success",
        "activity_id": activity_id,
        "p6_id": payload.Id,
        "message": "Activity actuals updated in mock P6 EPPM",
    }
