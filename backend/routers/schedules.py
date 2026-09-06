from fastapi import APIRouter

router = APIRouter(prefix="/api/v1/schedules", tags=["schedules"])


@router.get("/health")
def health():
    return {"router": "schedules", "status": "ok"}
