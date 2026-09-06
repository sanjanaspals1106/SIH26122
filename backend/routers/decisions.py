from fastapi import APIRouter

router = APIRouter(prefix="/api/v1/decisions", tags=["decisions"])


@router.get("/health")
def health():
    return {"router": "decisions", "status": "ok"}
