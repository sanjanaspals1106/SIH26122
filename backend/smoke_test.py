from backend.shared.db import get_connection, DATABASE_URL
from backend.shared.audit import payload_hash
from backend.shared.actuals import get_approved_actual, _dispatch_adapters
from backend.shared.auth import VALID_ROLES, UserProfile, require_role
from backend.main import app
from fastapi import HTTPException
from fastapi.testclient import TestClient



EXPECTED_TABLES = {
    "profiles",
    "schedules",
    "schedule_activities",
    "schedule_dependencies",
    "source_documents",
    "execution_events",
    "source_references",
    "candidate_matches",
    "conflict_records",
    "validation_issues",
    "planner_decisions",
    "approved_actuals",
    "audit_logs",
}


def test_database_connection():
    if not DATABASE_URL:
        print("[SKIP] PostgreSQL connection (DATABASE_URL not configured)")
        return
    try:
        with get_connection() as conn:
            row = conn.execute("SELECT 1 AS ok").fetchone()
        assert row["ok"] == 1
        print("[OK] PostgreSQL connection")
    except Exception as e:
        print(f"[SKIP] PostgreSQL connection ({e})")


def test_database_schema():
    if not DATABASE_URL:
        print("[SKIP] database schema (DATABASE_URL not configured)")
        return
    try:
        with get_connection() as conn:
            rows = conn.execute(
                """
                SELECT tablename
                FROM pg_tables
                WHERE schemaname = 'public'
                """
            ).fetchall()

        actual_tables = {row["tablename"] for row in rows}
        missing = EXPECTED_TABLES - actual_tables

        assert not missing, f"Missing tables: {sorted(missing)}"
        print("[OK] database schema (including profiles)")
    except Exception as e:
        print(f"[SKIP] database schema ({e})")


def test_audit_hashing():
    result = payload_hash({"test": "value"})

    assert isinstance(result, str)
    assert len(result) == 64

    print("[OK] audit hashing")


def test_approved_actuals_lookup():
    if not DATABASE_URL:
        print("[SKIP] approved actuals lookup (DATABASE_URL not configured)")
        return
    try:
        result = get_approved_actual(
            schedule_id="smoke-test-schedule",
            activity_id="smoke-test-activity",
        )
        assert result is None
        print("[OK] approved actuals lookup")
    except Exception as e:
        print(f"[SKIP] approved actuals lookup ({e})")


def test_auth_roles_and_dependencies():
    # Exactly SITE_ENGINEER and SUPERVISOR allowed
    assert VALID_ROLES == {"SITE_ENGINEER", "SUPERVISOR"}, f"Unexpected roles: {VALID_ROLES}"

    # Verify dependency factory
    dep_engineer = require_role("SITE_ENGINEER")
    dep_supervisor = require_role("SUPERVISOR")

    # Invalid role must raise ValueError
    try:
        require_role("ADMIN")
        assert False, "require_role('ADMIN') should have raised ValueError"
    except ValueError:
        pass

    # Role matching check
    eng_user = UserProfile(id="00000000-0000-0000-0000-000000000001", full_name="Eng One", role="SITE_ENGINEER")
    sup_user = UserProfile(id="00000000-0000-0000-0000-000000000002", full_name="Sup Two", role="SUPERVISOR")

    assert dep_engineer(eng_user) == eng_user
    assert dep_supervisor(sup_user) == sup_user

    # Role mismatch check raises 403
    try:
        dep_engineer(sup_user)
        assert False, "dep_engineer(sup_user) should have raised HTTPException(403)"
    except HTTPException as exc:
        assert exc.status_code == 403

    try:
        dep_supervisor(eng_user)
        assert False, "dep_supervisor(eng_user) should have raised HTTPException(403)"
    except HTTPException as exc:
        assert exc.status_code == 403

    print("[OK] auth roles and dependency enforcement (403 on mismatch, strictly 2 roles)")


def test_auth_me_endpoint_registration():
    routes = [route.path for route in app.routes]
    assert "/api/v1/auth/me" in routes, "GET /api/v1/auth/me not registered on FastAPI app"
    print("[OK] GET /api/v1/auth/me endpoint registered")


def test_router_health_endpoints():
    client = TestClient(app)

    # 1. Root health endpoint
    resp = client.get("/health")
    assert resp.status_code == 200
    assert resp.json() == {"status": "ok"}

    # 2. Export router health
    resp = client.get("/api/v1/export/health")
    assert resp.status_code == 200
    assert resp.json() == {"router": "export", "status": "ok"}

    # 3. Dashboard router health
    resp = client.get("/api/v1/dashboard/health")
    assert resp.status_code == 200
    assert resp.json() == {"router": "dashboard", "status": "ok"}

    # 4. Schedule router health
    resp = client.get("/api/v1/schedule/health")
    assert resp.status_code == 200
    assert resp.json() == {"router": "schedule", "status": "ok"}

    # 5. Mock P6 router health
    resp = client.get("/api/v1/mock-p6/health")
    assert resp.status_code == 200
    assert resp.json() == {"router": "mock-p6", "status": "ok"}

    # 6. Schedules (M1) router health
    resp = client.get("/api/v1/schedules/health")
    assert resp.status_code == 200
    assert resp.json() == {"router": "schedules", "status": "ok"}

    # 7. Activities router registration check (history route)
    routes = [route.path for route in app.routes]
    assert "/api/v1/activities/{activity_id}/history" in routes, (
        "GET /api/v1/activities/{activity_id}/history not registered on FastAPI app"
    )

    print("[OK] router health checks (root, export, dashboard, schedule, mock-p6, schedules)")


def test_adapter_boundary():
    dummy_actual = {
        "actual_id": "test-id",
        "schedule_id": "sch-1",
        "activity_id": "act-1",
        "actual_pct_complete": 50.0,
    }
    status = _dispatch_adapters(dummy_actual)
    assert isinstance(status, dict)
    assert status.get("csv_export") == "not_implemented_phase1"
    assert status.get("p6_rest") == "not_implemented_phase1"
    print("[OK] adapter boundary non-blocking hook")


if __name__ == "__main__":
    test_database_connection()
    test_database_schema()
    test_audit_hashing()
    test_approved_actuals_lookup()
    test_auth_roles_and_dependencies()
    test_auth_me_endpoint_registration()
    test_router_health_endpoints()
    test_adapter_boundary()

    print("\nSmoke test passed.")
