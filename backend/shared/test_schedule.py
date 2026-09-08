"""Focused tests for M1 baseline schedule ingestion (backend.shared.schedule).

Uses small synthetic CSV fixtures defined inline (matching the column layout
observed in the read-only M6 reference export, see backend/shared/schedule.py
docstring). These are test fixtures only, not project sample data, and are
unrelated to sample_data/schedule.csv or any M6-owned sample data file.

Run directly (matches the existing backend/smoke_test.py convention):
    python backend/shared/test_schedule.py
"""

import uuid

from backend.shared.schedule import parse_schedule_csv

_HEADER = (
    "L1,L2,L3,L4,L5 Activity ID,L6 Task ID,Discipline,Activity,Unit,"
    "Planned Qty,Baseline Start,Baseline Finish,Prior Actual,Today Actual,"
    "Cumulative Actual,Progress Pct,Status"
)


def _row(
    l1="North Field Utility Corridor",
    l2="Pump Station 3 Tie In",
    l3="Civil Works",
    l4="Trench and Foundations",
    wbs="CIV-PS3-TR-0180",
    activity_id="CIV-PS3-TR-0180-01",
    discipline="Civil",
    activity="Excavate utility trench CH 0+180 to CH 0+220",
    unit="m",
    qty="40",
    start="2026-08-14",
    finish="2026-08-14",
    prior="0",
    today="40",
    cumulative="40",
    progress_pct="100.0",
    status="Complete",
) -> str:
    return ",".join(
        [
            l1, l2, l3, l4, wbs, activity_id, discipline, activity, unit,
            qty, start, finish, prior, today, cumulative, progress_pct, status,
        ]
    )


def _csv(*rows: str) -> str:
    return "\n".join([_HEADER, *rows]) + "\n"


def test_parses_valid_rows():
    csv_text = _csv(
        _row(),
        _row(
            wbs="PIP-PS3-WLD-024",
            activity_id="PIP-PS3-WLD-024-01",
            discipline="Piping",
            activity="Complete field weld joints for utility header",
            unit="joints",
            qty="24",
            start="2026-08-11",
            finish="2026-08-15",
        ),
    )

    result = parse_schedule_csv(csv_text, schedule_id="SCH-001")

    assert result.is_valid, [e.describe() for e in result.errors]
    assert len(result.activities) == 2

    first = result.activities[0]
    assert first.schedule_id == "SCH-001"
    assert first.activity_id == "CIV-PS3-TR-0180-01"
    assert first.wbs_code == "CIV-PS3-TR-0180"
    assert first.activity_name == "Excavate utility trench CH 0+180 to CH 0+220"
    assert first.discipline == "Civil"
    assert first.location == "North Field Utility Corridor / Pump Station 3 Tie In"
    assert first.uom == "m"
    assert first.planned_quantity == 40.0
    assert str(first.planned_start) == "2026-08-14"
    assert str(first.planned_finish) == "2026-08-14"
    assert first.baseline_pct_complete == 0.0  # not present in source; existing model default
    assert first.asset_tag is None

    print("✓ parses valid rows into canonical ScheduleActivity records")


def test_required_field_missing_produces_error():
    csv_text = _csv(_row(activity=""))

    result = parse_schedule_csv(csv_text, schedule_id="SCH-001")

    assert not result.is_valid
    assert not result.activities
    assert any(e.field_name == "activity_name" for e in result.errors)

    print("✓ missing required field (activity_name) is rejected")


def test_empty_activity_id_rejected():
    csv_text = _csv(_row(activity_id="  "))

    result = parse_schedule_csv(csv_text, schedule_id="SCH-001")

    assert not result.is_valid
    assert not result.activities
    assert any(e.field_name == "activity_id" for e in result.errors)

    print("✓ empty activity_id is rejected")


def test_duplicate_activity_ids_rejected():
    csv_text = _csv(_row(activity_id="DUP-01"), _row(activity_id="DUP-01"))

    result = parse_schedule_csv(csv_text, schedule_id="SCH-001")

    assert len(result.activities) == 1
    assert any("duplicate activity_id" in e.message for e in result.errors)

    print("✓ duplicate activity_id within a schedule is rejected")


def test_malformed_date_rejected():
    csv_text = _csv(_row(start="14-08-2026"))

    result = parse_schedule_csv(csv_text, schedule_id="SCH-001")

    assert not result.is_valid
    assert not result.activities
    error = next(e for e in result.errors if e.field_name == "planned_start")
    assert "could not parse date" in error.message

    print("✓ malformed date is rejected with a clear message")


def test_start_after_finish_rejected():
    csv_text = _csv(_row(start="2026-08-20", finish="2026-08-10"))

    result = parse_schedule_csv(csv_text, schedule_id="SCH-001")

    assert not result.is_valid
    assert not result.activities
    assert any(e.field_name == "planned_finish" for e in result.errors)

    print("✓ planned_start after planned_finish is rejected")


def test_invalid_quantity_rejected():
    csv_text = _csv(_row(qty="forty"))

    result = parse_schedule_csv(csv_text, schedule_id="SCH-001")

    assert not result.is_valid
    assert not result.activities
    error = next(e for e in result.errors if e.field_name == "planned_quantity")
    assert "not numeric" in error.message

    print("✓ non-numeric planned_quantity is rejected")


def test_invalid_baseline_pct_rejected():
    csv_text = "\n".join(
        [
            _HEADER.replace("Status", "Status,Baseline Pct Complete"),
            _row() + ",150",
        ]
    ) + "\n"

    result = parse_schedule_csv(csv_text, schedule_id="SCH-001")

    assert not result.is_valid
    assert not result.activities
    error = next(e for e in result.errors if e.field_name == "baseline_pct_complete")
    assert "between 0 and 100" in error.message

    print("✓ out-of-range baseline_pct_complete is rejected")


def test_normalization_trims_whitespace_and_empty_strings():
    csv_text = _csv(_row(activity="  Excavate utility trench  ", unit=""))

    result = parse_schedule_csv(csv_text, schedule_id="SCH-001")

    assert result.is_valid, [e.describe() for e in result.errors]
    activity = result.activities[0]
    assert activity.activity_name == "Excavate utility trench"
    assert activity.uom is None  # empty string normalized to null, not invented

    print("✓ whitespace is trimmed and empty strings normalize to null")


def test_missing_schedule_id_raises():
    csv_text = _csv(_row())

    try:
        parse_schedule_csv(csv_text, schedule_id="")
        raised = False
    except ValueError:
        raised = True

    assert raised

    print("✓ missing schedule_id raises a clear error")


def test_error_messages_identify_row_and_field():
    csv_text = _csv(_row(activity_id="ROW-CTX-01", qty="not-a-number"))

    result = parse_schedule_csv(csv_text, schedule_id="SCH-001")

    error = next(e for e in result.errors if e.field_name == "planned_quantity")
    description = error.describe()

    assert "row 2" in description
    assert "ROW-CTX-01" in description
    assert "planned_quantity" in description

    print("✓ validation errors identify the row number, activity_id, and field")


_DEP_HEADER = _HEADER + ",Predecessor Activity ID,Relationship Type"


def test_valid_dependency_is_parsed():
    csv_text = (
        _DEP_HEADER + "\n"
        + _row(activity_id="A-1") + ",,\n"
        + _row(activity_id="A-2", activity="Backfill trench") + ",A-1,SS\n"
    )

    result = parse_schedule_csv(csv_text, schedule_id="SCH-DEP")

    assert result.is_valid, [e.describe() for e in result.errors]
    assert len(result.dependencies) == 1
    dep = result.dependencies[0]
    assert dep.predecessor_activity_id == "A-1"
    assert dep.successor_activity_id == "A-2"
    assert dep.relationship_type == "SS"
    assert dep.schedule_id == "SCH-DEP"
    parsed_id = uuid.UUID(dep.dependency_id, version=4)  # system-generated uuid4, not a composite string
    assert str(parsed_id) == dep.dependency_id  # canonical lowercase form

    print("✓ a row with predecessor + relationship type columns produces a ScheduleDependency with a generated uuid4 dependency_id")


def test_dependency_defaults_to_fs_when_relationship_type_omitted():
    csv_text = (
        _DEP_HEADER + "\n"
        + _row(activity_id="A-1") + ",,\n"
        + _row(activity_id="A-2", activity="Backfill trench") + ",A-1,\n"
    )

    result = parse_schedule_csv(csv_text, schedule_id="SCH-DEP")

    assert result.is_valid, [e.describe() for e in result.errors]
    assert result.dependencies[0].relationship_type == "FS"

    print("✓ relationship_type defaults to FS when the column is blank")


def test_dependency_referencing_unknown_activity_is_rejected():
    csv_text = (
        _DEP_HEADER + "\n"
        + _row(activity_id="A-1") + ",DOES-NOT-EXIST,FS\n"
    )

    result = parse_schedule_csv(csv_text, schedule_id="SCH-DEP")

    assert not result.is_valid
    assert not result.dependencies
    assert any(e.field_name == "predecessor_activity_id" for e in result.errors)

    print("✓ a dependency referencing an activity_id outside this import is rejected, not silently created")


def test_dependency_with_invalid_relationship_type_is_rejected():
    csv_text = (
        _DEP_HEADER + "\n"
        + _row(activity_id="A-1") + ",,\n"
        + _row(activity_id="A-2", activity="Backfill trench") + ",A-1,NOT_A_TYPE\n"
    )

    result = parse_schedule_csv(csv_text, schedule_id="SCH-DEP")

    assert not result.is_valid
    assert any(e.field_name == "relationship_type" for e in result.errors)

    print("✓ an unrecognized relationship_type (not FS/SS/FF/SF) is rejected")


def test_self_dependency_is_rejected():
    csv_text = (
        _DEP_HEADER + "\n"
        + _row(activity_id="A-1") + ",A-1,FS\n"
    )

    result = parse_schedule_csv(csv_text, schedule_id="SCH-DEP")

    assert not result.is_valid
    assert any("cannot depend on itself" in e.message for e in result.errors)

    print("✓ an activity cannot be its own predecessor")


def test_activity_id_is_preserved_verbatim_in_dependency():
    csv_text = (
        _DEP_HEADER + "\n"
        + _row(activity_id="A1000") + ",,\n"
        + _row(activity_id="A1001", activity="Backfill trench") + ",A1000,FS\n"
    )

    result = parse_schedule_csv(csv_text, schedule_id="SCH-DEP")

    assert result.is_valid, [e.describe() for e in result.errors]
    assert {a.activity_id for a in result.activities} == {"A1000", "A1001"}
    assert result.dependencies[0].predecessor_activity_id == "A1000"
    assert result.dependencies[0].successor_activity_id == "A1001"

    print("✓ source activity_ids (e.g. 'A1000') flow verbatim into dependency records, never a generated UUID")


if __name__ == "__main__":
    test_parses_valid_rows()
    test_required_field_missing_produces_error()
    test_empty_activity_id_rejected()
    test_duplicate_activity_ids_rejected()
    test_malformed_date_rejected()
    test_start_after_finish_rejected()
    test_invalid_quantity_rejected()
    test_invalid_baseline_pct_rejected()
    test_normalization_trims_whitespace_and_empty_strings()
    test_missing_schedule_id_raises()
    test_error_messages_identify_row_and_field()
    test_valid_dependency_is_parsed()
    test_dependency_defaults_to_fs_when_relationship_type_omitted()
    test_dependency_referencing_unknown_activity_is_rejected()
    test_dependency_with_invalid_relationship_type_is_rejected()
    test_self_dependency_is_rejected()
    test_activity_id_is_preserved_verbatim_in_dependency()

    print("\nM1 schedule ingestion tests passed.")
