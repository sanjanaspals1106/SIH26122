"""
Test-only fixtures for backend/test_m2_intake.py. Provides `client` and
`fake_db`, which the test file references as bare parameters but never
declares itself (no @pytest.fixture in that file).

The auth override here is TEST-ONLY -- it reads X-Dev-User-Id/X-Dev-Role
headers and hands back a UserProfile directly, so intake.py's real
require_role()/get_current_user() role-gating logic still runs unmodified
against it. This does not touch backend/shared/auth.py or change any
production authentication behavior.
"""
import pytest
from fastapi import HTTPException, Request
from fastapi.testclient import TestClient

from backend.main import app
from backend.shared.auth import UserProfile, get_current_user
from backend.shared.db import get_db
from backend.test_m2_intake import FakeDB


def _override_get_current_user(request: Request) -> UserProfile:
    user_id = request.headers.get("X-Dev-User-Id")
    role = request.headers.get("X-Dev-Role")
    if not user_id or not role:
        raise HTTPException(
            status_code=401,
            detail="Missing X-Dev-User-Id/X-Dev-Role test auth headers.",
        )
    return UserProfile(id=user_id, full_name=user_id, role=role)


@pytest.fixture
def fake_db():
    return FakeDB()


@pytest.fixture
def client(fake_db):
    def _override_get_db():
        yield fake_db

    app.dependency_overrides[get_db] = _override_get_db
    app.dependency_overrides[get_current_user] = _override_get_current_user
    try:
        yield TestClient(app)
    finally:
        app.dependency_overrides.pop(get_db, None)
        app.dependency_overrides.pop(get_current_user, None)
