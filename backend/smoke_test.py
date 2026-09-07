from backend.shared.db import get_connection
from backend.shared.audit import payload_hash
from backend.shared.actuals import get_approved_actual


EXPECTED_TABLES = {
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


if __name__ == "__main__":
    test_database_connection()
    test_database_schema()
    test_audit_hashing()
    test_approved_actuals_lookup()

    print("\nSmoke test passed.")
