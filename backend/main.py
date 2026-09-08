from contextlib import asynccontextmanager

from fastapi import FastAPI

from backend.routers import (
    schedules,
    intake,
    matching,
    checks,
    decisions,
    export,
    auth,
    dashboard,
    activities,
    schedule_ll,
    mock_p6,
)
from backend.shared.db import init_db


@asynccontextmanager
async def lifespan(app: FastAPI):
    try:
        init_db()
    except Exception as e:
        print(f"Warning: Database initialization skipped on startup ({e})")
    yield


app = FastAPI(
    title="SIH26122 Infrastructure Progress Tracking API",
    version="0.1.0",
    lifespan=lifespan,
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
app.include_router(activities.router)
app.include_router(schedule_ll.router)
app.include_router(mock_p6.router)