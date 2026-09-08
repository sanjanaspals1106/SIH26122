from fastapi import FastAPI

from backend.shared.db import init_db
from backend.routers import schedules
from backend.routers import intake
from backend.routers import matching
from backend.routers import checks
from backend.routers import decisions
from backend.routers import export
from backend.routers import auth
from backend.routers import dashboard

init_db()


app = FastAPI(
    title="SIH26122 Infrastructure Progress Tracking API",
    version="0.1.0",
)


@app.get("/health")
def health():
    return {"status": "ok"}


app.include_router(schedules.router)
app.include_router(intake.router)
app.include_router(matching.router)
app.include_router(checks.router)
app.include_router(decisions.router)
app.include_router(export.router)
app.include_router(auth.router)
app.include_router(dashboard.router)
