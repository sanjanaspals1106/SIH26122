"""API tests for the M1 Schedule API layer (backend.routers.schedules).

These drive the FastAPI app through fastapi.testclient.TestClient and
exercise the full path for each M1 endpoint:

    POST /api/v1/schedules -> parser -> repository -> PostgreSQL -> active FAISS index
    GET  /api/v1/schedules, /{schedule_id}, /{schedule_id}/activities,
         /{schedule_id}/activities/{activity_id}, /{schedule_id}/dependencies -> PostgreSQL

They require a reachable DATABASE_URL (see backend/.env.example) and are
skipped automatically (when run via `python -m` directly) when the database
is not reachable — the same pattern used by
backend/shared/test_schedule_repository_integration.py.

Each test uses a schedule_id namespaced under "m1-api-test-" and deletes
everything it wrote (database rows, including any dependencies) in a
`finally` block, so runs never leave residue in the database whether or not
they pass. The active FAISS index (in-memory only, see
backend.shared.schedule_index) needs no cleanup — it is simply replaced by
the next schedule that gets indexed.

Run directly (requires a reachable DATABASE_URL):
    python backend/routers/test_schedules.py
"""

import uuid

from fastapi.testclient import TestClient

from backend.main import app
from backend.shared.db import get_connection

client = TestClient(app)

_CSV_TEMPLATE = (
    "L1,L2,L3,L4,L5 Activity ID,L6 Task ID,Discipline,Activity,Unit,"
    "Planned Qty,Baseline Start,Baseline Finish,Prior Actual,Today Actual,"
    "Cumulative Actual,Progress Pct,Status\n"
    "North Field Utility Corridor,Pump Station 3 Tie In,Civil Works,"
    "Trench and Foundations,CIV-PS3-TR-0180,{activity_id}-01,Civil,"
    "Excavate utility trench CH 0+180 to CH 0+220,m,40,2026-08-14,2026-08-14,"
    "0,40,40,100.0,Complete\n"
    "North Field Utility Corridor,Pump Station 3 Tie In,Piping Works,"
    "Above Ground Piping,PIP-PS3-WLD-024,{activity_id}-02,Piping,"
    "Complete field weld joints for utility header,joints,24,2026-08-11,"
    "2026-08-15,20,2,22,91.7,Ongoing\n"
)

_INVALID_CSV = (
    "L1,L2,L3,L4,L5 Activity ID,L6 Task ID,Discipline,Activity,Unit,"
    "Planned Qty,Baseline Start,Baseline Finish,Prior Actual,Today Actual,"
    "Cumulative Actual,Progress Pct,Status\n"
    ",,Civil Works,Trench and Foundations,CIV-PS3-TR-0180,,Civil,"
    "Excavate utility trench CH 0+180 to CH 0+220,m,40,2026-08-14,2026-08-14,"
    "0,40,40,100.0,Complete\n"
)


def _new_schedule_id() -> str:
    return f"m1-api-test-{uuid.uuid4().hex[:12]}"


def _database_available() -> bool:
    try:
        with get_connection() as conn:
            conn.execute("SELECT 1")
        return True
    except Exception as exc:  # connection/auth/network failure
        print(f"  (database unavailable: {exc})")
        return False


def _cleanup(schedule_id: str) -> None:
    with get_connection() as conn:
        conn.execute("DELETE FROM schedule_dependencies WHERE schedule_id = %s", (schedule_id,))
        conn.execute("DELETE FROM schedule_activities WHERE schedule_id = %s", (schedule_id,))
        conn.execute("DELETE FROM schedules WHERE schedule_id = %s", (schedule_id,))
        conn.commit()


def test_create_and_read_schedule_end_to_end():
    schedule_id = _new_schedule_id()
    csv_content = _CSV_TEMPLATE.format(activity_id=schedule_id)

    try:
        create_resp = client.post(
            "/api/v1/schedules",
            json={
                "schedule_id": schedule_id,
                "project_name": "North Field Utility Corridor",
                "data_date": "2026-08-14",
                "source_format": "csv",
                "csv_content": csv_content,
            },
        )
        assert create_resp.status_code == 201, create_resp.text
        body = create_resp.json()
        assert body["schedule_id"] == schedule_id
        assert body["project_name"] == "North Field Utility Corridor"
        assert body["data_date"] == "2026-08-14"
        assert body["source_format"] == "csv"
        assert body["activity_count"] == 2
        assert body["dependency_count"] == 0
        assert body["indexed"] is True
        assert body["index_error"] is None

        list_resp = client.get("/api/v1/schedules")
        assert list_resp.status_code == 200
        assert any(s["schedule_id"] == schedule_id for s in list_resp.json())

        get_resp = client.get(f"/api/v1/schedules/{schedule_id}")
        assert get_resp.status_code == 200
        assert get_resp.json()["project_name"] == "North Field Utility Corridor"

        activities_resp = client.get(f"/api/v1/schedules/{schedule_id}/activities")
        assert activities_resp.status_code == 200
        activities = activities_resp.json()
        assert len(activities) == 2
        activity_ids = {a["activity_id"] for a in activities}
        assert activity_ids == {f"{schedule_id}-01", f"{schedule_id}-02"}

        one_resp = client.get(f"/api/v1/schedules/{schedule_id}/activities/{schedule_id}-01")
        assert one_resp.status_code == 200
        one = one_resp.json()
        assert one["discipline"] == "Civil"
        assert one["planned_quantity"] == 40

        deps_resp = client.get(f"/api/v1/schedules/{schedule_id}/dependencies")
        assert deps_resp.status_code == 200
        assert deps_resp.json() == []  # no dependency columns in this CSV
    finally:
        _cleanup(schedule_id)

    print("✓ POST creates a schedule end-to-end and GET endpoints retrieve it from PostgreSQL")


def test_dependencies_are_parsed_persisted_and_retrievable():
    schedule_id = _new_schedule_id()
    csv_content = (
        "L1,L2,L3,L4,L5 Activity ID,L6 Task ID,Discipline,Activity,Unit,"
        "Planned Qty,Baseline Start,Baseline Finish,Predecessor Activity ID,Relationship Type\n"
        "North Field,Pump Station 3,Civil Works,Trench,CIV-TR,{schedule_id}-01,Civil,"
        "Excavate utility trench,m,40,2026-08-14,2026-08-16,,\n"
        "North Field,Pump Station 3,Civil Works,Backfill,CIV-BF,{schedule_id}-02,Civil,"
        "Backfill utility trench,m,40,2026-08-17,2026-08-18,{schedule_id}-01,FS\n"
    ).format(schedule_id=schedule_id)

    try:
        create_resp = client.post(
            "/api/v1/schedules",
            json={
                "schedule_id": schedule_id,
                "project_name": "North Field Utility Corridor",
                "csv_content": csv_content,
            },
        )
        assert create_resp.status_code == 201, create_resp.text
        assert create_resp.json()["dependency_count"] == 1

        deps_resp = client.get(f"/api/v1/schedules/{schedule_id}/dependencies")
        assert deps_resp.status_code == 200
        deps = deps_resp.json()
        assert len(deps) == 1
        assert deps[0]["predecessor_activity_id"] == f"{schedule_id}-01"
        assert deps[0]["successor_activity_id"] == f"{schedule_id}-02"
        assert deps[0]["relationship_type"] == "FS"
        assert deps[0]["schedule_id"] == schedule_id
    finally:
        _cleanup(schedule_id)

    print("✓ dependency columns are parsed, persisted, and retrievable via the dependencies API")


def test_duplicate_schedule_id_returns_409():
    schedule_id = _new_schedule_id()
    payload = {
        "schedule_id": schedule_id,
        "project_name": "North Field Utility Corridor",
        "data_date": "2026-08-14",
        "source_format": "csv",
        "csv_content": _CSV_TEMPLATE.format(activity_id=schedule_id),
    }

    try:
        first = client.post("/api/v1/schedules", json=payload)
        assert first.status_code == 201

        second = client.post("/api/v1/schedules", json=payload)
        assert second.status_code == 409

        with get_connection() as conn:
            row = conn.execute(
                "SELECT COUNT(*) AS n FROM schedule_activities WHERE schedule_id = %s",
                (schedule_id,),
            ).fetchone()
        assert row["n"] == 2  # not duplicated by the rejected second POST
    finally:
        _cleanup(schedule_id)

    print("✓ re-POSTing an existing schedule_id returns 409, not a silent overwrite")


def test_invalid_csv_returns_422_with_row_errors_and_persists_nothing():
    schedule_id = _new_schedule_id()

    resp = client.post(
        "/api/v1/schedules",
        json={
            "schedule_id": schedule_id,
            "project_name": "North Field Utility Corridor",
            "csv_content": _INVALID_CSV,
        },
    )

    assert resp.status_code == 422
    detail = resp.json()["detail"]
    assert detail["errors"]
    assert any(e["field"] == "activity_id" for e in detail["errors"])

    with get_connection() as conn:
        row = conn.execute(
            "SELECT 1 FROM schedules WHERE schedule_id = %s", (schedule_id,)
        ).fetchone()
    assert row is None

    print("✓ invalid CSV rows are rejected with 422 and per-row errors, nothing persisted")


def test_get_unknown_schedule_returns_404():
    resp = client.get("/api/v1/schedules/does-not-exist-m1-api-test")
    assert resp.status_code == 404

    activities_resp = client.get("/api/v1/schedules/does-not-exist-m1-api-test/activities")
    assert activities_resp.status_code == 404

    print("✓ GET on an unknown schedule_id returns 404 for the schedule and its activities")


def test_get_unknown_activity_returns_404():
    schedule_id = _new_schedule_id()

    try:
        client.post(
            "/api/v1/schedules",
            json={
                "schedule_id": schedule_id,
                "project_name": "North Field Utility Corridor",
                "csv_content": _CSV_TEMPLATE.format(activity_id=schedule_id),
            },
        )

        resp = client.get(f"/api/v1/schedules/{schedule_id}/activities/does-not-exist")
        assert resp.status_code == 404
    finally:
        _cleanup(schedule_id)

    print("✓ GET on an unknown activity_id within a real schedule returns 404")


if __name__ == "__main__":
    print("Checking database availability (DATABASE_URL)...")
    if not _database_available():
        print(
            "Skipping M1 Schedule API tests: no reachable database. Configure "
            "DATABASE_URL in the project .env to run them (see backend/.env.example)."
        )
    else:
        test_create_and_read_schedule_end_to_end()
        test_dependencies_are_parsed_persisted_and_retrievable()
        test_duplicate_schedule_id_returns_409()
        test_invalid_csv_returns_422_with_row_errors_and_persists_nothing()
        test_get_unknown_schedule_returns_404()
        test_get_unknown_activity_returns_404()

        print("\nM1 Schedule API tests passed.")
