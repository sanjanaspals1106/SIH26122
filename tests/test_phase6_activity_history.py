import sqlite3
from typing import Any

from fastapi.testclient import TestClient

from backend.main import app
from backend.routers.activities import query_activity_history
from backend.shared.auth import UserProfile, get_current_user


class SQLitePsycopgAdapter:
    """
    Lightweight DB connection adapter for deterministic in-memory testing.
    Translates Postgres query patterns (%s) to SQLite (?).
    """

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

    def commit(self):
        self.conn.commit()


def create_test_db() -> SQLitePsycopgAdapter:
    conn = sqlite3.connect(":memory:")
    conn.row_factory = sqlite3.Row

    conn.execute(
        """
        CREATE TABLE execution_events (
            event_id TEXT PRIMARY KEY,
            document_id TEXT,
            schedule_id TEXT NOT NULL,
            event_date TEXT NOT NULL,
            raw_claim_text TEXT NOT NULL,
            input_channel TEXT NOT NULL,
            language_detected TEXT,
            reported_activity_id TEXT,
            matched_activity_id TEXT,
            discipline TEXT,
            action TEXT,
            event_type TEXT,
            claim_mode TEXT DEFAULT 'CUMULATIVE_PCT',
            asset_tag TEXT,
            location TEXT,
            claimed_quantity REAL,
            claimed_uom TEXT,
            claimed_pct REAL,
            delay_reason TEXT,
            supervisor_id TEXT,
            photo_path TEXT,
            status TEXT DEFAULT 'EXTRACTED',
            created_at TEXT
        )
        """
    )
    conn.execute(
        """
        CREATE TABLE source_references (
            reference_id TEXT PRIMARY KEY,
            event_id TEXT NOT NULL,
            file_name TEXT,
            sheet_name TEXT,
            row_cell_ref TEXT,
            message_id TEXT,
            raw_snippet TEXT NOT NULL
        )
        """
    )
    conn.execute(
        """
        CREATE TABLE planner_decisions (
            decision_id TEXT PRIMARY KEY,
            event_id TEXT NOT NULL,
            selected_activity_id TEXT NOT NULL,
            action TEXT,
            approved_pct REAL,
            approved_qty REAL,
            planner_id TEXT NOT NULL,
            justification TEXT NOT NULL,
            decided_at TEXT
        )
        """
    )
    return SQLitePsycopgAdapter(conn)


# =========================================================================
# Test 1 — Endpoint Registration
# =========================================================================

def test_endpoint_is_registered():
    routes = [r.path for r in app.routes]
    assert "/api/v1/activities/{activity_id}/history" in routes, (
        "GET /api/v1/activities/{activity_id}/history not registered on app"
    )


# =========================================================================
# Test 2 — Activity Filtering (No Cross-Activity Leakage)
# =========================================================================

def test_activity_filtering_no_leakage():
    db = create_test_db()
    # Event 1 for A1000
    db.execute(
        """
        INSERT INTO execution_events (event_id, schedule_id, event_date, raw_claim_text, input_channel, matched_activity_id, created_at)
        VALUES ('EV-1', 'SCH-1', '2026-08-01', 'Claim for A1000', 'whatsapp', 'A1000', '2026-08-01 10:00:00')
        """
    )
    # Event 2 for A1001
    db.execute(
        """
        INSERT INTO execution_events (event_id, schedule_id, event_date, raw_claim_text, input_channel, matched_activity_id, created_at)
        VALUES ('EV-2', 'SCH-1', '2026-08-02', 'Claim for A1001', 'whatsapp', 'A1001', '2026-08-02 10:00:00')
        """
    )

    data = query_activity_history("A1000", conn=db)
    assert data["activity_id"] == "A1000"
    assert len(data["timeline"]) == 1
    assert data["timeline"][0]["event_id"] == "EV-1"

    # Querying A1001 returns only A1001
    data_1001 = query_activity_history("A1001", conn=db)
    assert data_1001["activity_id"] == "A1001"
    assert len(data_1001["timeline"]) == 1
    assert data_1001["timeline"][0]["event_id"] == "EV-2"


# =========================================================================
# Test 3 — Execution Events Included
# =========================================================================

def test_execution_events_included():
    db = create_test_db()
    db.execute(
        """
        INSERT INTO execution_events (
            event_id, schedule_id, event_date, raw_claim_text, input_channel,
            matched_activity_id, claimed_pct, created_at
        )
        VALUES ('EV-SINGLE', 'SCH-1', '2026-08-01', 'Initial excavation claim', 'typed', 'ACT-SINGLE', 40.0, '2026-08-01 08:00:00')
        """
    )

    data = query_activity_history("ACT-SINGLE", conn=db)
    assert data["activity_id"] == "ACT-SINGLE"
    assert len(data["timeline"]) == 1
    ev = data["timeline"][0]
    assert ev["type"] == "execution_event"
    assert ev["event_id"] == "EV-SINGLE"
    assert ev["claimed_pct"] == 40.0
    assert ev["raw_claim_text"] == "Initial excavation claim"


# =========================================================================
# Test 4 — Multiple Execution Events
# =========================================================================

def test_multiple_execution_events():
    db = create_test_db()
    for i in range(1, 4):
        db.execute(
            """
            INSERT INTO execution_events (event_id, schedule_id, event_date, raw_claim_text, input_channel, matched_activity_id, claimed_pct, created_at)
            VALUES (?, 'SCH-1', ?, ?, 'typed', 'ACT-MULTI', ?, ?)
            """,
            (f"EV-{i}", f"2026-08-0{i}", f"Claim {i}", i * 25.0, f"2026-08-0{i} 08:00:00"),
        )

    data = query_activity_history("ACT-MULTI", conn=db)
    assert data["activity_id"] == "ACT-MULTI"
    assert len(data["timeline"]) == 3
    event_ids = [item["event_id"] for item in data["timeline"]]
    assert event_ids == ["EV-1", "EV-2", "EV-3"]


# =========================================================================
# Test 5 — Source References Included
# =========================================================================

def test_source_references_included():
    db = create_test_db()
    db.execute(
        """
        INSERT INTO execution_events (event_id, schedule_id, event_date, raw_claim_text, input_channel, matched_activity_id, created_at)
        VALUES ('EV-SREF', 'SCH-1', '2026-08-01', 'Foundation claim', 'typed', 'ACT-SREF', '2026-08-01 10:00:00')
        """
    )
    db.execute(
        """
        INSERT INTO source_references (reference_id, event_id, file_name, raw_snippet)
        VALUES ('REF-1', 'EV-SREF', 'report.pdf', 'Foundations poured')
        """
    )

    data = query_activity_history("ACT-SREF", conn=db)
    assert len(data["timeline"]) == 1
    assert len(data["timeline"][0]["source_references"]) == 1
    assert data["timeline"][0]["source_references"][0]["reference_id"] == "REF-1"
    assert data["timeline"][0]["source_references"][0]["file_name"] == "report.pdf"


# =========================================================================
# Test 6 — Multiple Source References
# =========================================================================

def test_multiple_source_references():
    db = create_test_db()
    db.execute(
        """
        INSERT INTO execution_events (event_id, schedule_id, event_date, raw_claim_text, input_channel, matched_activity_id, created_at)
        VALUES ('EV-REF', 'SCH-1', '2026-08-01', 'Piping inspection complete', 'typed', 'ACT-REFS', '2026-08-01 10:00:00')
        """
    )
    # Insert 3 source references for EV-REF
    db.execute(
        """
        INSERT INTO source_references (reference_id, event_id, file_name, sheet_name, row_cell_ref, raw_snippet)
        VALUES ('REF-1', 'EV-REF', 'site_diary.xlsx', 'Civil', 'B12', 'Piping test passed')
        """
    )
    db.execute(
        """
        INSERT INTO source_references (reference_id, event_id, file_name, message_id, raw_snippet)
        VALUES ('REF-2', 'EV-REF', 'whatsapp_log.txt', 'MSG-999', 'Foreman: test completed')
        """
    )
    db.execute(
        """
        INSERT INTO source_references (reference_id, event_id, file_name, raw_snippet)
        VALUES ('REF-3', 'EV-REF', 'site_photo.jpg', 'Visual inspection passed')
        """
    )

    data = query_activity_history("ACT-REFS", conn=db)
    assert len(data["timeline"]) == 1
    event_entry = data["timeline"][0]
    assert event_entry["type"] == "execution_event"
    assert len(event_entry["source_references"]) == 3

    ref_ids = [r["reference_id"] for r in event_entry["source_references"]]
    assert "REF-1" in ref_ids
    assert "REF-2" in ref_ids
    assert "REF-3" in ref_ids

    ref1 = next(r for r in event_entry["source_references"] if r["reference_id"] == "REF-1")
    assert ref1["file_name"] == "site_diary.xlsx"
    assert ref1["sheet_name"] == "Civil"
    assert ref1["row_cell_ref"] == "B12"


# =========================================================================
# Test 7 — Final Planner Decision Included
# =========================================================================

def test_final_planner_decision_included():
    db = create_test_db()
    db.execute(
        """
        INSERT INTO execution_events (event_id, schedule_id, event_date, raw_claim_text, input_channel, matched_activity_id, created_at)
        VALUES ('EV-DEC', 'SCH-1', '2026-08-01', 'Claim ready for decision', 'typed', 'ACT-DEC', '2026-08-01 09:00:00')
        """
    )
    db.execute(
        """
        INSERT INTO planner_decisions (decision_id, event_id, selected_activity_id, action, approved_pct, planner_id, justification, decided_at)
        VALUES ('DEC-FINAL', 'EV-DEC', 'ACT-DEC', 'APPROVE', 100.0, 'P-01', 'Approved per inspection', '2026-08-01 17:00:00')
        """
    )

    data = query_activity_history("ACT-DEC", conn=db)
    # Timeline should have execution_event, followed by planner_decision
    assert len(data["timeline"]) == 2
    assert data["timeline"][0]["type"] == "execution_event"
    assert data["timeline"][1]["type"] == "planner_decision"
    dec = data["timeline"][1]
    assert dec["decision_id"] == "DEC-FINAL"
    assert dec["action"] == "APPROVE"
    assert dec["approved_pct"] == 100.0
    assert dec["justification"] == "Approved per inspection"


# =========================================================================
# Test 8 — Earlier Decision Does Not Replace Final Decision
# =========================================================================

def test_earlier_decision_does_not_replace_final():
    db = create_test_db()
    db.execute(
        """
        INSERT INTO execution_events (event_id, schedule_id, event_date, raw_claim_text, input_channel, matched_activity_id, created_at)
        VALUES ('EV-REV', 'SCH-1', '2026-08-01', 'Trenching claim', 'typed', 'ACT-REV', '2026-08-01 08:00:00')
        """
    )
    # Earlier decision: HOLD at 10:00
    db.execute(
        """
        INSERT INTO planner_decisions (decision_id, event_id, selected_activity_id, action, approved_pct, planner_id, justification, decided_at)
        VALUES ('DEC-EARLY', 'EV-REV', 'ACT-REV', 'HOLD', 0.0, 'P-01', 'Need photo proof', '2026-08-01 10:00:00')
        """
    )
    # Later final decision: EDIT at 16:00
    db.execute(
        """
        INSERT INTO planner_decisions (decision_id, event_id, selected_activity_id, action, approved_pct, planner_id, justification, decided_at)
        VALUES ('DEC-LATEST', 'EV-REV', 'ACT-REV', 'EDIT', 60.0, 'P-01', 'Photo confirmed 60%', '2026-08-01 16:00:00')
        """
    )

    data = query_activity_history("ACT-REV", conn=db)
    decisions_in_timeline = [item for item in data["timeline"] if item["type"] == "planner_decision"]
    # Only the single final planner decision appears
    assert len(decisions_in_timeline) == 1
    assert decisions_in_timeline[0]["decision_id"] == "DEC-LATEST"
    assert decisions_in_timeline[0]["action"] == "EDIT"
    assert decisions_in_timeline[0]["approved_pct"] == 60.0


# =========================================================================
# Test 9 — Chronological Ordering
# =========================================================================

def test_chronological_ordering():
    db = create_test_db()
    # Insert in reverse order
    db.execute(
        """
        INSERT INTO execution_events (event_id, schedule_id, event_date, raw_claim_text, input_channel, matched_activity_id, created_at)
        VALUES ('EV-DAY3', 'SCH-1', '2026-08-03', 'Third event', 'typed', 'ACT-TIME', '2026-08-03 12:00:00')
        """
    )
    db.execute(
        """
        INSERT INTO execution_events (event_id, schedule_id, event_date, raw_claim_text, input_channel, matched_activity_id, created_at)
        VALUES ('EV-DAY1', 'SCH-1', '2026-08-01', 'First event', 'typed', 'ACT-TIME', '2026-08-01 09:00:00')
        """
    )
    db.execute(
        """
        INSERT INTO execution_events (event_id, schedule_id, event_date, raw_claim_text, input_channel, matched_activity_id, created_at)
        VALUES ('EV-DAY2', 'SCH-1', '2026-08-02', 'Second event', 'typed', 'ACT-TIME', '2026-08-02 11:00:00')
        """
    )
    # Decision after day 3
    db.execute(
        """
        INSERT INTO planner_decisions (decision_id, event_id, selected_activity_id, action, planner_id, justification, decided_at)
        VALUES ('DEC-FINAL', 'EV-DAY3', 'ACT-TIME', 'APPROVE', 'P-01', 'Approved', '2026-08-03 18:00:00')
        """
    )

    data = query_activity_history("ACT-TIME", conn=db)
    timeline_ids = [
        item["decision_id"] if item["type"] == "planner_decision" else item["event_id"]
        for item in data["timeline"]
    ]
    assert timeline_ids == ["EV-DAY1", "EV-DAY2", "EV-DAY3", "DEC-FINAL"]


# =========================================================================
# Test 10 — Deterministic Tie Handling
# =========================================================================

def test_deterministic_tie_handling():
    db = create_test_db()
    # Two events with identical timestamps
    db.execute(
        """
        INSERT INTO execution_events (event_id, schedule_id, event_date, raw_claim_text, input_channel, matched_activity_id, created_at)
        VALUES ('EV-B', 'SCH-1', '2026-08-01', 'Event B', 'typed', 'ACT-TIE', '2026-08-01 10:00:00')
        """
    )
    db.execute(
        """
        INSERT INTO execution_events (event_id, schedule_id, event_date, raw_claim_text, input_channel, matched_activity_id, created_at)
        VALUES ('EV-A', 'SCH-1', '2026-08-01', 'Event A', 'typed', 'ACT-TIE', '2026-08-01 10:00:00')
        """
    )
    # Decision at same timestamp
    db.execute(
        """
        INSERT INTO planner_decisions (decision_id, event_id, selected_activity_id, action, planner_id, justification, decided_at)
        VALUES ('DEC-TIE', 'EV-A', 'ACT-TIE', 'APPROVE', 'P-01', 'Tied decision', '2026-08-01 10:00:00')
        """
    )

    data = query_activity_history("ACT-TIE", conn=db)
    # Events come first (ordered by event_id: EV-A, EV-B), followed by decision
    timeline_ids = [
        item["decision_id"] if item["type"] == "planner_decision" else item["event_id"]
        for item in data["timeline"]
    ]
    assert timeline_ids == ["EV-A", "EV-B", "DEC-TIE"]


# =========================================================================
# Test 11 — Empty History Handled Safely
# =========================================================================

def test_empty_history_handled_safely():
    db = create_test_db()
    data = query_activity_history("ACT-NO-HISTORY", conn=db)
    assert data["activity_id"] == "ACT-NO-HISTORY"
    assert data["timeline"] == []


# =========================================================================
# Test 12 — Unknown Activity Returns 200 with Empty Timeline
# =========================================================================

def test_unknown_activity_returns_empty_timeline():
    db = create_test_db()
    data = query_activity_history("NONEXISTENT-ACT-9999", conn=db)
    assert isinstance(data, dict)
    assert data == {
        "activity_id": "NONEXISTENT-ACT-9999",
        "timeline": [],
    }


# =========================================================================
# Test 13 — Authorization (Supervisor 200, Site Engineer 403, Unauth 401)
# =========================================================================

def test_authorization(monkeypatch):
    client = TestClient(app)

    # 1. Unauthenticated -> 401
    resp = client.get("/api/v1/activities/ACT-1/history")
    assert resp.status_code == 401

    # 2. SITE_ENGINEER -> 403
    engineer = UserProfile(id="11111111-1111-1111-1111-111111111111", full_name="Alice", role="SITE_ENGINEER")
    app.dependency_overrides[get_current_user] = lambda: engineer
    try:
        resp = client.get(
            "/api/v1/activities/ACT-1/history",
            headers={"Authorization": "Bearer mock-token"},
        )
        assert resp.status_code == 403
    finally:
        app.dependency_overrides.clear()

    # 3. SUPERVISOR -> 200
    supervisor = UserProfile(id="22222222-2222-2222-2222-222222222222", full_name="Bob", role="SUPERVISOR")
    app.dependency_overrides[get_current_user] = lambda: supervisor
    monkeypatch.setattr(
        "backend.routers.activities.query_activity_history",
        lambda activity_id, conn=None: {"activity_id": activity_id, "timeline": []},
    )
    try:
        resp = client.get(
            "/api/v1/activities/ACT-1/history",
            headers={"Authorization": "Bearer mock-token"},
        )
        assert resp.status_code == 200
        assert resp.json()["activity_id"] == "ACT-1"
    finally:
        app.dependency_overrides.clear()


# =========================================================================
# Test 14 — Response Contract
# =========================================================================

def test_response_contract():
    db = create_test_db()
    db.execute(
        """
        INSERT INTO execution_events (event_id, schedule_id, event_date, raw_claim_text, input_channel, matched_activity_id, created_at)
        VALUES ('EV-CONTRACT', 'SCH-1', '2026-08-01', 'Verified concrete footing', 'typed', 'ACT-C', '2026-08-01 10:00:00')
        """
    )
    db.execute(
        """
        INSERT INTO source_references (reference_id, event_id, file_name, raw_snippet)
        VALUES ('REF-C', 'EV-CONTRACT', 'diary.pdf', 'Footing verified')
        """
    )
    db.execute(
        """
        INSERT INTO planner_decisions (decision_id, event_id, selected_activity_id, action, approved_pct, planner_id, justification, decided_at)
        VALUES ('DEC-C', 'EV-CONTRACT', 'ACT-C', 'APPROVE', 100.0, 'P-01', 'Passed', '2026-08-01 14:00:00')
        """
    )

    data = query_activity_history("ACT-C", conn=db)
    assert set(data.keys()) == {"activity_id", "timeline"}
    assert isinstance(data["timeline"], list)
    assert len(data["timeline"]) == 2

    # Verify event entry
    ev_item = data["timeline"][0]
    assert ev_item["type"] == "execution_event"
    assert ev_item["event_id"] == "EV-CONTRACT"
    assert isinstance(ev_item["source_references"], list)
    assert len(ev_item["source_references"]) == 1
    ref_item = ev_item["source_references"][0]
    assert ref_item["reference_id"] == "REF-C"

    # Verify decision entry
    dec_item = data["timeline"][1]
    assert dec_item["type"] == "planner_decision"
    assert dec_item["decision_id"] == "DEC-C"
    assert dec_item["action"] == "APPROVE"


# =========================================================================
# Test 15 — Planner Override Activity Routing
# =========================================================================

def test_planner_override_activity_routing():
    """
    If machine matched an event to ACT-A, but the planner decided on ACT-B,
    the event belongs to ACT-B's history, NOT ACT-A.
    """
    db = create_test_db()
    db.execute(
        """
        INSERT INTO execution_events (event_id, schedule_id, event_date, raw_claim_text, input_channel, matched_activity_id, created_at)
        VALUES ('EV-OVERRIDE', 'SCH-1', '2026-08-01', 'Claim misclassified by AI', 'typed', 'ACT-A', '2026-08-01 10:00:00')
        """
    )
    db.execute(
        """
        INSERT INTO planner_decisions (decision_id, event_id, selected_activity_id, action, approved_pct, planner_id, justification, decided_at)
        VALUES ('DEC-OVERRIDE', 'EV-OVERRIDE', 'ACT-B', 'APPROVE', 80.0, 'P-01', 'Reassigned to ACT-B', '2026-08-01 12:00:00')
        """
    )

    # Under ACT-A: Timeline is empty (reassigned)
    data_a = query_activity_history("ACT-A", conn=db)
    assert data_a["timeline"] == []

    # Under ACT-B: Timeline contains the event and decision
    data_b = query_activity_history("ACT-B", conn=db)
    assert len(data_b["timeline"]) == 2
    assert data_b["timeline"][0]["event_id"] == "EV-OVERRIDE"
    assert data_b["timeline"][1]["decision_id"] == "DEC-OVERRIDE"
