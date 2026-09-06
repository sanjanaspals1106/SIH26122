from fastapi import APIRouter

router = APIRouter(prefix="/api/v1/claims", tags=["matching"])


@router.get("/matching/health")
def health():
    return {"router": "matching", "status": "ok"}
