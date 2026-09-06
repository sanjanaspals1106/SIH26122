from fastapi import APIRouter

router = APIRouter(prefix="/api/v1/export", tags=["export"])


@router.get("/health")
def health():
    return {"router": "export", "status": "ok"}
