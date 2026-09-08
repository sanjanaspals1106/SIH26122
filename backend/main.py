import os
from contextlib import asynccontextmanager

from dotenv import load_dotenv

# Must run before any backend module import below, since shared/db.py and
# others read DATABASE_URL/SUPABASE_*/LLM_* from the environment at import
# time (module-level `os.getenv(...)` calls) — loading .env after those
# imports would leave them permanently unset for the life of the process.
load_dotenv()

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

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
    schedule,
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

_cors_origins = os.getenv("CORS_ORIGINS", "http://localhost:5173,http://127.0.0.1:5173")
app.add_middleware(
    CORSMiddleware,
    allow_origins=[origin.strip() for origin in _cors_origins.split(",") if origin.strip()],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
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
app.include_router(schedule.router)
app.include_router(mock_p6.router)