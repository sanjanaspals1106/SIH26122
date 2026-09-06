from backend.shared.db import get_connection
from backend.shared.schemas import (
    ScheduleActivity,
    ExecutionClaim,
    CandidateMatch,
    ValidationIssue,
    PlannerDecision,
    ApprovedActual,
)
from backend.shared.audit import payload_hash
from backend.shared.actuals import get_approved_pct


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


def check_database():
    with get_connection() as conn:
        rows = conn.execute(
            """
            SELECT name
            FROM sqlite_master
            WHERE type = 'table'
            """
        ).fetchall()

    actual_tables = {row["name"] for row in rows}

    missing = EXPECTED_TABLES - actual_tables

    assert not missing, f"Missing database tables: {sorted(missing)}"

    print("✓ database schema")


def check_shared_models():
    models = [
        ScheduleActivity,
        ExecutionClaim,
        CandidateMatch,
        ValidationIssue,
        PlannerDecision,
        ApprovedActual,
    ]

    assert all(model is not None for model in models)

    print("✓ shared Pydantic schemas")


def check_audit():
    value = payload_hash({"test": "payload"})

    assert len(value) == 64
    assert all(c in "0123456789abcdef" for c in value)

    print("✓ audit hashing")


def check_actuals():
    pct = get_approved_pct(
        "smoke-test-schedule",
        "smoke-test-activity",
    )

    assert pct == 0.0

    print("✓ approved actuals lookup")


if __name__ == "__main__":
    check_database()
    check_shared_models()
    check_audit()
    check_actuals()

    print("\nSmoke test passed.")
