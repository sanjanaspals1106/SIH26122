from backend.shared.db import get_connection
from backend.shared.audit import payload_hash
from backend.shared.actuals import get_approved_actual, _dispatch_adapters
from backend.shared.auth import VALID_ROLES, UserProfile, require_role
from backend.main import app
from fastapi import HTTPException


EXPECTED_TABLES = {
    "profiles",
    "schedules",
    "schedule_activities",
    "schedule_dependencies",
    "source_documents",
    "execution_events",
    "source_references",
    "candidate_matches",
    "audit_log",
    "planner_decisions",
    "compliance_checks",
    "claim_intake_batches",
    "approved_actuals",
}


def test_database_connection():
    with get_connection() as conn:
        row = conn.execute("SELECT 1 AS ok").fetchone()

    assert row["ok"] == 1

    print("✓ PostgreSQL connection")


def test_database_schema():
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

    print("✓ database schema")


def test_audit_hashing():
    result = payload_hash({"test": "value"})

    assert isinstance(result, str)
    assert len(result) == 64

    print("✓ audit hashing")


def test_approved_actuals_lookup():
    result = get_approved_actual(
        schedule_id="smoke-test-schedule",
        activity_id="smoke-test-activity",
    )

    assert result is None

    print("✓ approved actuals lookup")


def test_auth_roles_and_dependencies():
    assert VALID_ROLES == {"SITE_ENGINEER", "SUPERVISOR"}, f"Unexpected roles: {VALID_ROLES}"

    dep_engineer = require_role("SITE_ENGINEER")
    dep_supervisor = require_role("SUPERVISOR")

    try:
        require_role("ADMIN")
        assert False, "require_role('ADMIN') should have raised ValueError"
    except ValueError:
        pass

    eng_user = UserProfile(id="00000000-0000-0000-0000-000000000001", full_name="Eng One", role="SITE_ENGINEER")
    sup_user = UserProfile(id="00000000-0000-0000-0000-000000000002", full_name="Sup Two", role="SUPERVISOR")

    assert dep_engineer(eng_user) == eng_user
    assert dep_supervisor(sup_user) == sup_user

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
    test_adapter_boundary()

    print("\nSmoke test passed.")
