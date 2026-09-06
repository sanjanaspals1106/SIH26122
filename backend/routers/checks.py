from fastapi import APIRouter

router = APIRouter(prefix="/api/v1/claims", tags=["checks"])


@router.get("/checks/health")
def health():
    return {"router": "checks", "status": "ok"}
