import csv
import io
import sqlite3
from typing import Optional

import pytest
from fastapi.testclient import TestClient

from backend.main import app
from backend.routers.export import (
    CSV_HEADER,
    CSVExportAdapter,
    PMISAdapter,
    format_csv_rows,
    query_approved_actuals_for_export,
)
from backend.shared.auth import UserProfile, get_current_user


class SQLitePsycopgAdapter:
    def __init__(self, conn: sqlite3.Connection):
        self.conn = conn

    def execute(self, query: str, params=None):
        clean_q = query.replace("%s", "?")
        cur = self.conn.cursor()
        if params is not None:
            cur.execute(clean_q, params)
        else:
            cur.execute(clean_q)
        return cur


def create_test_db() -> SQLitePsycopgAdapter:
    conn = sqlite3.connect(":memory:")
    conn.row_factory = sqlite3.Row
    conn.execute(
        """
        CREATE TABLE approved_actuals (
            actual_id TEXT PRIMARY KEY,
            decision_id TEXT NOT NULL,
            event_id TEXT NOT NULL,
            schedule_id TEXT NOT NULL,
            activity_id TEXT NOT NULL,
            actual_start TEXT,
            actual_finish TEXT,
            actual_pct_complete REAL,
            actual_quantity REAL,
            exported_at TEXT,
            created_at TEXT DEFAULT (datetime('now')),
            UNIQUE (schedule_id, activity_id)
        )
        """
    )
    return SQLitePsycopgAdapter(conn)


# =========================================================================
# 1. Endpoint Registration
# =========================================================================

def test_endpoint_registration():
    routes = list(app.openapi()["paths"].keys())
    assert "/api/v1/export/csv" in routes, "GET /api/v1/export/csv not registered"


# =========================================================================
# 2. Supervisor Authorization & 3. Unauthorized Access Behavior
# =========================================================================

def test_unauthenticated_request_rejected():
    client = TestClient(app)
    resp = client.get("/api/v1/export/csv")
    assert resp.status_code == 401, f"Expected 401, got {resp.status_code}"


def test_invalid_token_rejected():
    client = TestClient(app)
    resp = client.get(
        "/api/v1/export/csv",
        headers={"Authorization": "Bearer invalid.mock.jwt"},
    )
    assert resp.status_code == 401, f"Expected 401, got {resp.status_code}"


def test_site_engineer_forbidden():
    """
    SITE_ENGINEER must be rejected with 403 Forbidden. Only SUPERVISOR allowed.
    """
    client = TestClient(app)
    engineer_user = UserProfile(
        id="11111111-1111-1111-1111-111111111111",
        full_name="Alice Engineer",
        role="SITE_ENGINEER",
    )
    app.dependency_overrides[get_current_user] = lambda: engineer_user
    try:
        resp = client.get(
            "/api/v1/export/csv",
            headers={"Authorization": "Bearer mocked-engineer-token"},
        )
        assert resp.status_code == 403, f"Expected 403 for SITE_ENGINEER, got {resp.status_code}"
    finally:
        app.dependency_overrides.clear()


def test_supervisor_authorized(monkeypatch):
    """
    SUPERVISOR role is authorized to export CSV.
    """
    client = TestClient(app)
    supervisor_user = UserProfile(
        id="22222222-2222-2222-2222-222222222222",
        full_name="Bob Supervisor",
        role="SUPERVISOR",
    )
    app.dependency_overrides[get_current_user] = lambda: supervisor_user

    # Mock query function to avoid requiring a live Postgres DB during HTTP endpoint test
    monkeypatch.setattr(
        "backend.routers.export.query_approved_actuals_for_export",
        lambda schedule_id=None: [
            {
                "activity_id": "CIV-001",
                "actual_start": "2026-08-01",
                "actual_finish": "2026-08-10",
                "actual_pct_complete": 100.0,
                "actual_quantity": 40.0,
            }
        ],
    )

    try:
        resp = client.get(
            "/api/v1/export/csv",
            headers={"Authorization": "Bearer mocked-supervisor-token"},
        )
        assert resp.status_code == 200
        assert "text/csv" in resp.headers["content-type"]
        assert 'filename="approved_actuals.csv"' in resp.headers["content-disposition"]
        content = resp.text
        lines = content.strip().split("\r\n")
        assert len(lines) == 2
        assert lines[0] == "activity_id,actual_start,actual_finish,actual_pct_complete,actual_quantity"
        assert lines[1] == "CIV-001,2026-08-01,2026-08-10,100,40"
    finally:
        app.dependency_overrides.clear()


# =========================================================================
# 4. Exact CSV Header, 5. Exactly 5 Visible Columns, 12. No schedule_id, 13. No ActualDuration
# =========================================================================

def test_exact_csv_header_and_column_count():
    assert CSV_HEADER == [
        "activity_id",
        "actual_start",
        "actual_finish",
        "actual_pct_complete",
        "actual_quantity",
    ]
    assert len(CSV_HEADER) == 5
    assert "schedule_id" not in CSV_HEADER
    assert "decision_id" not in CSV_HEADER
    assert "event_id" not in CSV_HEADER
    assert "exported_at" not in CSV_HEADER
    assert "ActualDuration" not in CSV_HEADER


# =========================================================================
# 6. Data Source from approved_actuals & 7. activity_id Preserved
# =========================================================================

def test_data_from_approved_actuals_and_activity_id_preservation():
    db = create_test_db()
    # Insert rows into approved_actuals with various activity_id string formats
    db.execute(
        """
        INSERT INTO approved_actuals (
            actual_id, decision_id, event_id, schedule_id, activity_id,
            actual_start, actual_finish, actual_pct_complete, actual_quantity
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            "act-uuid-1",
            "dec-1",
            "ev-1",
            "SCHED-01",
            "A1000",
            "2026-08-01",
            "2026-08-15",
            85.5,
            120.0,
        ),
    )
    db.execute(
        """
        INSERT INTO approved_actuals (
            actual_id, decision_id, event_id, schedule_id, activity_id,
            actual_start, actual_finish, actual_pct_complete, actual_quantity
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            "act-uuid-2",
            "dec-2",
            "ev-2",
            "SCHED-01",
            "PIP-PS3-WLD-024",
            "2026-08-05",
            None,
            50.0,
            12.0,
        ),
    )

    rows = query_approved_actuals_for_export(conn=db)
    csv_text = format_csv_rows(rows)
    reader = list(csv.reader(io.StringIO(csv_text)))

    # Header check
    assert reader[0] == CSV_HEADER

    # Activity ID preservation (strings, not UUIDs)
    act_ids = [r[0] for r in reader[1:]]
    assert "A1000" in act_ids
    assert "PIP-PS3-WLD-024" in act_ids
    assert "act-uuid-1" not in act_ids


# =========================================================================
# 8. NULL Values Handled Safely
# =========================================================================

def test_null_values_handling():
    rows = [
        {
            "activity_id": "ACT-NULLS",
            "actual_start": None,
            "actual_finish": None,
            "actual_pct_complete": None,
            "actual_quantity": None,
        }
    ]
    csv_text = format_csv_rows(rows)
    lines = csv_text.strip().split("\r\n")
    assert lines[0] == "activity_id,actual_start,actual_finish,actual_pct_complete,actual_quantity"
    assert lines[1] == "ACT-NULLS,,,,"
    # Ensure "None" is never printed in output
    assert "None" not in csv_text


# =========================================================================
# 9. Multiple Rows Have Deterministic Ordering (ORDER BY activity_id ASC)
# =========================================================================

def test_deterministic_row_ordering():
    db = create_test_db()
    # Insert in reverse order
    for act in ["ZEB-001", "ACT-002", "MID-003"]:
        db.execute(
            """
            INSERT INTO approved_actuals (
                actual_id, decision_id, event_id, schedule_id, activity_id,
                actual_pct_complete
            ) VALUES (?, ?, ?, ?, ?, ?)
            """,
            (f"id-{act}", "dec", "ev", "sch", act, 50.0),
        )

    rows = query_approved_actuals_for_export(conn=db)
    ordered_ids = [r["activity_id"] for r in rows]
    assert ordered_ids == ["ACT-002", "MID-003", "ZEB-001"]


# =========================================================================
# 10. Empty Dataset Returns Header Only (Not Empty Body)
# =========================================================================

def test_empty_dataset_returns_header():
    csv_text = format_csv_rows([])
    assert csv_text == "activity_id,actual_start,actual_finish,actual_pct_complete,actual_quantity\r\n"
    assert len(csv_text.strip().split("\r\n")) == 1


# =========================================================================
# 11. CSV Escaping Correctness
# =========================================================================

def test_csv_escaping_with_special_characters():
    rows = [
        {
            "activity_id": 'ACT "Special", Trench, Sec 1',
            "actual_start": "2026-08-01",
            "actual_finish": None,
            "actual_pct_complete": 25.0,
            "actual_quantity": 10.0,
        }
    ]
    csv_text = format_csv_rows(rows)
    # Parse back using standard csv reader to ensure round-trip integrity
    parsed = list(csv.reader(io.StringIO(csv_text)))
    assert len(parsed) == 2
    assert parsed[1][0] == 'ACT "Special", Trench, Sec 1'
    assert parsed[1][1] == "2026-08-01"
    assert parsed[1][2] == ""
    assert parsed[1][3] == "25"
    assert parsed[1][4] == "10"


# =========================================================================
# 14. CSVExportAdapter Canonical 5-Field Interface
# =========================================================================

def test_csvexportadapter_interface():
    adapter = CSVExportAdapter()
    assert isinstance(adapter, PMISAdapter)

    # push_actual with the canonical 5 fields
    success = adapter.push_actual(
        activity_id="PIP-001",
        actual_start="2026-08-01",
        actual_finish="2026-08-10",
        actual_pct_complete=100.0,
        actual_quantity=55.0,
    )
    assert success is True

    # Check generated CSV
    csv_out = adapter.generate_csv()
    lines = csv_out.strip().split("\r\n")
    assert lines[0] == "activity_id,actual_start,actual_finish,actual_pct_complete,actual_quantity"
    assert lines[1] == "PIP-001,2026-08-01,2026-08-10,100,55"
