import csv
import io
import sqlite3
from typing import List, Optional
from unittest.mock import MagicMock, patch

import pytest

from backend.routers.export import (
    CSV_HEADER,
    CSVExportAdapter,
    get_default_csv_adapter,
    set_default_csv_adapter,
    trigger_auto_export,
)
from backend.shared.actuals import upsert_approved_actual


class SQLitePsycopgAdapter:
    """
    Lightweight DB connection adapter for deterministic in-memory testing.
    Translates Postgres-specific query patterns (%s, FOR UPDATE) to SQLite syntax.
    """

    def __init__(self, conn: sqlite3.Connection):
        self.conn = conn
        self.commit_count = 0

    def execute(self, query: str, params=None):
        clean_q = query.replace("FOR UPDATE", "")
        clean_q = clean_q.replace("%s", "?")
        cur = self.conn.cursor()
        if params is not None:
            cur.execute(clean_q, params)
        else:
            cur.execute(clean_q)
        return cur

    def commit(self):
        self.commit_count += 1
        self.conn.commit()


def create_test_db() -> SQLitePsycopgAdapter:
    conn = sqlite3.connect(":memory:")
    conn.row_factory = sqlite3.Row

    conn.execute(
        """
        CREATE TABLE execution_events (
            event_id TEXT PRIMARY KEY,
            schedule_id TEXT NOT NULL,
            event_date TEXT,
            claim_mode TEXT DEFAULT 'CUMULATIVE_PCT',
            event_type TEXT,
            claimed_quantity REAL,
            claimed_pct REAL,
            matched_activity_id TEXT
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
            decided_at TEXT DEFAULT (datetime('now'))
        )
        """
    )
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
# Phase 3 Tests: Auto-Export Integration (Feature #26)
# =========================================================================

def test_approve_and_edit_trigger_auto_export():
    """
    Test A & B:
    - APPROVE -> approved_actuals committed -> CSV regenerated.
    - EDIT -> approved_actuals committed -> CSV regenerated.
    """
    db = create_test_db()
    sch_id = "SCH-AUTO-1"
    act_id = "CIV-100"

    # Setup custom adapter to verify generated CSV content
    adapter = CSVExportAdapter()
    set_default_csv_adapter(adapter)

    # 1. APPROVE flow
    res_approve = upsert_approved_actual(
        schedule_id=sch_id,
        activity_id=act_id,
        event_id="EV-APP-1",
        decision_id="DEC-APP-1",
        action="APPROVE",
        claim_mode="CUMULATIVE_PCT",
        approved_pct=45.0,
        actual_start="2026-08-01",
        conn=db,
    )

    assert res_approve is not None
    assert res_approve["actual_pct_complete"] == 45.0

    # Verify CSV was automatically regenerated
    csv_out = adapter.generate_csv()
    lines = csv_out.strip().split("\r\n")
    assert lines[0] == "activity_id,actual_start,actual_finish,actual_pct_complete,actual_quantity"
    assert len(lines) == 2
    assert lines[1] == "CIV-100,2026-08-01,,45,"

    # 2. EDIT flow (updating percentage and adding finish date)
    res_edit = upsert_approved_actual(
        schedule_id=sch_id,
        activity_id=act_id,
        event_id="EV-EDIT-1",
        decision_id="DEC-EDIT-1",
        action="EDIT",
        claim_mode="CUMULATIVE_PCT",
        approved_pct=85.0,
        actual_finish="2026-08-15",
        conn=db,
    )

    assert res_edit is not None
    assert res_edit["actual_pct_complete"] == 85.0
    assert res_edit["actual_start"] == "2026-08-01"
    assert res_edit["actual_finish"] == "2026-08-15"

    # Verify CSV was automatically regenerated reflecting EDIT
    csv_edit_out = adapter.generate_csv()
    lines_edit = csv_edit_out.strip().split("\r\n")
    assert len(lines_edit) == 2
    assert lines_edit[1] == "CIV-100,2026-08-01,2026-08-15,85,"


def test_reject_and_hold_do_not_trigger_export():
    """
    Requirement 9:
    Ensure REJECT and HOLD do NOT create an approved_actual and therefore do not trigger export.
    """
    db = create_test_db()
    sch_id = "SCH-REJ-1"
    act_id = "PIP-200"

    adapter = CSVExportAdapter()
    set_default_csv_adapter(adapter)

    # 1. HOLD action
    res_hold = upsert_approved_actual(
        schedule_id=sch_id,
        activity_id=act_id,
        event_id="EV-HOLD-1",
        decision_id="DEC-HOLD-1",
        action="HOLD",
        claim_mode="CUMULATIVE_PCT",
        approved_pct=50.0,
        conn=db,
    )
    assert res_hold is None

    # No approved_actuals created
    row = db.execute(
        "SELECT COUNT(*) AS c FROM approved_actuals WHERE schedule_id = ? AND activity_id = ?",
        (sch_id, act_id),
    ).fetchone()
    assert row["c"] == 0
    # No CSV generated
    assert len(adapter.records) == 0

    # 2. REJECT action
    res_reject = upsert_approved_actual(
        schedule_id=sch_id,
        activity_id=act_id,
        event_id="EV-REJ-1",
        decision_id="DEC-REJ-1",
        action="REJECT",
        claim_mode="CUMULATIVE_PCT",
        approved_pct=50.0,
        conn=db,
    )
    assert res_reject is None

    row_rej = db.execute(
        "SELECT COUNT(*) AS c FROM approved_actuals WHERE schedule_id = ? AND activity_id = ?",
        (sch_id, act_id),
    ).fetchone()
    assert row_rej["c"] == 0
    assert len(adapter.records) == 0


def test_post_commit_ordering_db_before_export():
    """
    Test C: Verify ordering:
    DB commit MUST occur before CSV generation.
    """
    db = create_test_db()
    sch_id = "SCH-ORDER-1"
    act_id = "ELE-300"

    call_order = []

    original_commit = db.commit

    def tracked_commit():
        call_order.append("COMMIT")
        original_commit()

    db.commit = tracked_commit

    adapter = CSVExportAdapter()
    original_regenerate = adapter.regenerate_from_db

    def tracked_regenerate(*args, **kwargs):
        # At the time CSV regeneration runs, COMMIT must have already happened
        call_order.append("GENERATE_CSV")
        # And the row must already be committed and visible in DB
        return original_regenerate(*args, **kwargs)

    adapter.regenerate_from_db = tracked_regenerate
    set_default_csv_adapter(adapter)

    res = upsert_approved_actual(
        schedule_id=sch_id,
        activity_id=act_id,
        event_id="EV-ORD-1",
        decision_id="DEC-ORD-1",
        action="APPROVE",
        approved_pct=70.0,
        conn=db,
    )

    assert res is not None
    assert call_order == ["COMMIT", "GENERATE_CSV"], f"Incorrect execution order: {call_order}"


def test_export_failure_is_non_blocking():
    """
    Test D: Simulate CSV/export failure:
    - export raises/fails
    - approved_actuals remains committed
    - approval operation does not roll back.
    """
    db = create_test_db()
    sch_id = "SCH-FAIL-1"
    act_id = "MEC-400"

    adapter = CSVExportAdapter()

    def failing_regenerate(*args, **kwargs):
        raise IOError("Disk full: unable to write CSV export file")

    adapter.regenerate_from_db = failing_regenerate
    set_default_csv_adapter(adapter)

    # Function must not raise; must return successful approval dict
    res = upsert_approved_actual(
        schedule_id=sch_id,
        activity_id=act_id,
        event_id="EV-FAIL-1",
        decision_id="DEC-FAIL-1",
        action="APPROVE",
        approved_pct=90.0,
        actual_quantity=150.0,
        conn=db,
    )

    assert res is not None
    assert res["activity_id"] == act_id
    assert res["actual_pct_complete"] == 90.0
    assert res["actual_quantity"] == 150.0

    # approved_actuals MUST remain committed in DB despite adapter failure
    row = db.execute(
        "SELECT * FROM approved_actuals WHERE schedule_id = ? AND activity_id = ?",
        (sch_id, act_id),
    ).fetchone()
    assert row is not None
    assert row["actual_pct_complete"] == 90.0
    assert row["actual_quantity"] == 150.0


def test_full_dataset_regeneration_canonical_columns():
    """
    Test E & Requirement 11:
    - Ensure CSV regeneration uses the complete current approved_actuals dataset
      rather than blindly appending a single event.
    - Verify the generated CSV contains exactly the canonical five columns.
    - No schedule_id, decision_id, event_id, exported_at, ActualDuration.
    """
    db = create_test_db()
    sch_id = "SCH-FULL-1"

    adapter = CSVExportAdapter()
    set_default_csv_adapter(adapter)

    # 1. First approval for ACT-02
    upsert_approved_actual(
        schedule_id=sch_id,
        activity_id="ACT-02",
        event_id="EV-1",
        decision_id="DEC-1",
        action="APPROVE",
        approved_pct=30.0,
        conn=db,
    )

    # 2. Second approval for ACT-01 (alphabetically earlier)
    upsert_approved_actual(
        schedule_id=sch_id,
        activity_id="ACT-01",
        event_id="EV-2",
        decision_id="DEC-2",
        action="APPROVE",
        approved_pct=60.0,
        conn=db,
    )

    csv_text = adapter.generate_csv()
    parsed = list(csv.reader(io.StringIO(csv_text)))

    # Exact canonical 5 columns
    assert parsed[0] == CSV_HEADER
    assert parsed[0] == [
        "activity_id",
        "actual_start",
        "actual_finish",
        "actual_pct_complete",
        "actual_quantity",
    ]
    assert len(parsed[0]) == 5
    for forbidden in ["schedule_id", "decision_id", "event_id", "exported_at", "ActualDuration"]:
        assert forbidden not in parsed[0]

    # Full dataset regenerated (not just ACT-01, both ACT-01 and ACT-02 exist)
    assert len(parsed) == 3
    # Deterministic sorting by activity_id ASC
    assert parsed[1][0] == "ACT-01"
    assert parsed[1][3] == "60"
    assert parsed[2][0] == "ACT-02"
    assert parsed[2][3] == "30"
