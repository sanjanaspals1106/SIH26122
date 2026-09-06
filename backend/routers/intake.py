from fastapi import APIRouter

router = APIRouter(prefix="/api/v1/claims", tags=["intake"])


@router.get("/health")
def health():
    return {"router": "intake", "status": "ok"}
