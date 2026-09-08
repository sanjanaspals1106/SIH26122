"""Unit tests for M1 schedule persistence (backend.shared.schedule_repository).

These test only the guard/validation logic that runs before any database
connection is opened, so they require no live database and no DATABASE_URL.
For tests that actually hit PostgreSQL, see
backend/shared/test_schedule_repository_integration.py (opt-in).

Run directly:
    python backend/shared/test_schedule_repository.py
"""

from backend.shared.schedule import ScheduleParseResult, ScheduleValidationError, parse_schedule_csv
from backend.shared.schedule_repository import save_schedule
from backend.shared.schemas import Schedule

_VALID_CSV = (
    "L1,L2,L3,L4,L5 Activity ID,L6 Task ID,Discipline,Activity,Unit,"
    "Planned Qty,Baseline Start,Baseline Finish,Prior Actual,Today Actual,"
    "Cumulative Actual,Progress Pct,Status\n"
    "North Field Utility Corridor,Pump Station 3 Tie In,Civil Works,"
    "Trench and Foundations,CIV-PS3-TR-0180,CIV-PS3-TR-0180-01,Civil,"
    "Excavate utility trench CH 0+180 to CH 0+220,m,40,2026-08-14,2026-08-14,"
    "0,40,40,100.0,Complete\n"
)


def _valid_parse_result(schedule_id: str = "SCH-001") -> ScheduleParseResult:
    result = parse_schedule_csv(_VALID_CSV, schedule_id=schedule_id)
    assert result.is_valid, [e.describe() for e in result.errors]
    return result


def test_rejects_schedule_id_mismatch():
    parse_result = _valid_parse_result(schedule_id="SCH-001")
    schedule = Schedule(schedule_id="SCH-DIFFERENT", project_name="North Field Utility Corridor")

    try:
        save_schedule(schedule, parse_result)
        raised = False
    except ValueError as exc:
        raised = True
        assert "does not match" in str(exc)

    assert raised

    print("✓ schedule_id mismatch between Schedule and ScheduleParseResult is rejected")


def test_rejects_invalid_parse_result():
    parse_result = ScheduleParseResult(
        schedule_id="SCH-001",
        activities=[],
        errors=[ScheduleValidationError(2, "activity_id", "is required and cannot be empty")],
    )
    schedule = Schedule(schedule_id="SCH-001", project_name="North Field Utility Corridor")

    try:
        save_schedule(schedule, parse_result)
        raised = False
    except ValueError as exc:
        raised = True
        assert "validation errors" in str(exc)

    assert raised

    print("✓ a parse_result with validation errors is rejected before touching the database")


def test_rejects_empty_activities():
    parse_result = ScheduleParseResult(schedule_id="SCH-001", activities=[], errors=[])
    schedule = Schedule(schedule_id="SCH-001", project_name="North Field Utility Corridor")

    try:
        save_schedule(schedule, parse_result)
        raised = False
    except ValueError as exc:
        raised = True
        assert "zero activities" in str(exc)

    assert raised

    print("✓ a parse_result with zero activities is rejected before touching the database")


if __name__ == "__main__":
    test_rejects_schedule_id_mismatch()
    test_rejects_invalid_parse_result()
    test_rejects_empty_activities()

    print("\nM1 schedule persistence unit tests passed (no database required).")
