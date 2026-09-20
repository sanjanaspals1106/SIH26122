"""
Regression test suite for Priority 1: Decision -> approved_actual Atomicity.

Verifies:
1. Happy path: APPROVE persists planner_decisions, execution_events status, and approved_actuals atomically.
2. Failure injection in upsert: Rollback ensures NO partial state (no decision created, status unchanged, no actuals row).
3. Downstream adapter isolation: Post-commit adapter failure (P6 / CSV export) does not compromise or roll back approved_actuals.
"""

import uuid
import pytest
from unittest.mock import patch

from backend.shared.db import get_connection
from backend.routers.decisions import _record_decision


@pytest.fixture
def clean_db():
    with get_connection() as conn:
        with conn.transaction():
            with conn.cursor() as cur:
                # Clean up previous test runs if any
                cur.execute("DELETE FROM approved_actuals WHERE schedule_id LIKE 'ATOM-%'")
                cur.execute("DELETE FROM planner_decisions WHERE event_id IN (SELECT event_id FROM execution_events WHERE schedule_id LIKE 'ATOM-%')")
                cur.execute("DELETE FROM execution_events WHERE schedule_id LIKE 'ATOM-%'")
                cur.execute("DELETE FROM schedule_activities WHERE schedule_id LIKE 'ATOM-%'")
                cur.execute("DELETE FROM schedules WHERE schedule_id LIKE 'ATOM-%'")
    yield
    with get_connection() as conn:
        with conn.transaction():
            with conn.cursor() as cur:
                cur.execute("DELETE FROM approved_actuals WHERE schedule_id LIKE 'ATOM-%'")
                cur.execute("DELETE FROM planner_decisions WHERE event_id IN (SELECT event_id FROM execution_events WHERE schedule_id LIKE 'ATOM-%')")
                cur.execute("DELETE FROM execution_events WHERE schedule_id LIKE 'ATOM-%'")
                cur.execute("DELETE FROM schedule_activities WHERE schedule_id LIKE 'ATOM-%'")
                cur.execute("DELETE FROM schedules WHERE schedule_id LIKE 'ATOM-%'")


def _setup_schedule_and_claim(sched_id: str, act_id: str, event_id: str):
    with get_connection() as conn:
        with conn.transaction():
            with conn.cursor() as cur:
                cur.execute(
                    """
                    INSERT INTO schedules (schedule_id, project_name, data_date, source_format)
                    VALUES (%s, 'Atomicity Test Project', '2026-01-01', 'P6_CSV')
                    ON CONFLICT (schedule_id) DO NOTHING
                    """,
                    (sched_id,),
                )
                cur.execute(
                    """
                    INSERT INTO schedule_activities (
                        schedule_id, activity_id, activity_name, discipline, location,
                        planned_start, planned_finish
                    )
                    VALUES (%s, %s, 'Foundation Pouring', 'CIVIL', 'BLOCK_A', '2026-03-01', '2026-03-15')
                    ON CONFLICT (schedule_id, activity_id) DO NOTHING
                    """,
                    (sched_id, act_id),
                )
                cur.execute(
                    """
                    INSERT INTO execution_events (
                        event_id, schedule_id, matched_activity_id, event_date,
                        raw_claim_text, input_channel, event_type, claim_mode, claimed_pct, status
                    )
                    VALUES (%s, %s, %s, '2026-03-05', 'Foundation pour 45 pct', 'TYPED_TEXT', 'PROGRESS_UPDATE', 'CUMULATIVE_PCT', 45.0, 'VALIDATED')
                    """,
                    (event_id, sched_id, act_id),
                )


def test_decision_atomicity_happy_path(clean_db):
    sched_id = f"ATOM-{uuid.uuid4().hex[:6]}"
    act_id = "ACT-100"
    event_id = f"EV-{uuid.uuid4().hex[:6]}"
    _setup_schedule_and_claim(sched_id, act_id, event_id)

    planner_uuid = str(uuid.uuid4())
    res = _record_decision(
        event_id=event_id,
        action="APPROVE",
        planner_id=planner_uuid,
        justification="Verified progress on site",
        selected_activity_id=act_id,
        approved_pct=45.0,
        approved_qty=None,
    )

    assert res["status"] == "APPROVED"
    assert res["approved_actual"] is not None

    with get_connection() as conn:
        with conn.cursor() as cur:
            # 1. Verify planner_decisions
            cur.execute("SELECT * FROM planner_decisions WHERE event_id = %s", (event_id,))
            dec_row = cur.fetchone()
            assert dec_row is not None
            assert dec_row["action"] == "APPROVE"
            assert float(dec_row["approved_pct"]) == 45.0

            # 2. Verify execution_events
            cur.execute("SELECT status FROM execution_events WHERE event_id = %s", (event_id,))
            ev_row = cur.fetchone()
            assert ev_row["status"] == "APPROVED"

            # 3. Verify approved_actuals
            cur.execute("SELECT * FROM approved_actuals WHERE schedule_id = %s AND activity_id = %s", (sched_id, act_id))
            act_row = cur.fetchone()
            assert act_row is not None
            assert act_row["decision_id"] == dec_row["decision_id"]
            assert float(act_row["actual_pct_complete"]) == 45.0


def test_decision_atomicity_rollback_on_upsert_failure(clean_db):
    sched_id = f"ATOM-{uuid.uuid4().hex[:6]}"
    act_id = "ACT-100"
    event_id = f"EV-{uuid.uuid4().hex[:6]}"
    _setup_schedule_and_claim(sched_id, act_id, event_id)

    # Mock _execute_upsert to raise an error mid-transaction
    planner_uuid = str(uuid.uuid4())
    with patch("backend.routers.decisions._execute_upsert", side_effect=RuntimeError("Simulated DB failure during actuals upsert")):
        with pytest.raises(RuntimeError, match="Simulated DB failure during actuals upsert"):
            _record_decision(
                event_id=event_id,
                action="APPROVE",
                planner_id=planner_uuid,
                justification="Should roll back",
                selected_activity_id=act_id,
                approved_pct=50.0,
                approved_qty=None,
            )

    # Verify complete rollback: NO decision, status remains VALIDATED, NO approved_actual
    with get_connection() as conn:
        with conn.cursor() as cur:
            # 1. Verify planner_decisions has no record
            cur.execute("SELECT * FROM planner_decisions WHERE event_id = %s", (event_id,))
            assert cur.fetchone() is None

            # 2. Verify execution_events status is STILL 'VALIDATED'
            cur.execute("SELECT status FROM execution_events WHERE event_id = %s", (event_id,))
            ev_row = cur.fetchone()
            assert ev_row["status"] == "VALIDATED"

            # 3. Verify approved_actuals has no record
            cur.execute("SELECT * FROM approved_actuals WHERE schedule_id = %s AND activity_id = %s", (sched_id, act_id))
            assert cur.fetchone() is None


def test_decision_atomicity_adapter_failure_isolation(clean_db):
    sched_id = f"ATOM-{uuid.uuid4().hex[:6]}"
    act_id = "ACT-100"
    event_id = f"EV-{uuid.uuid4().hex[:6]}"
    _setup_schedule_and_claim(sched_id, act_id, event_id)

    # Downstream adapters failing must NOT roll back the committed decision or approved_actual
    planner_uuid = str(uuid.uuid4())
    with patch("backend.routers.export.trigger_auto_export", side_effect=RuntimeError("CSV Export service down")), \
         patch("backend.shared.p6.trigger_p6_actual_push", side_effect=RuntimeError("P6 gateway timeout")):
        res = _record_decision(
            event_id=event_id,
            action="APPROVE",
            planner_id=planner_uuid,
            justification="Adapters failing downstream must not abort commit",
            selected_activity_id=act_id,
            approved_pct=60.0,
            approved_qty=None,
        )

    assert res["status"] == "APPROVED"
    assert res["approved_actual"] is not None

    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute("SELECT * FROM planner_decisions WHERE event_id = %s", (event_id,))
            assert cur.fetchone() is not None

            cur.execute("SELECT status FROM execution_events WHERE event_id = %s", (event_id,))
            assert cur.fetchone()["status"] == "APPROVED"

            cur.execute("SELECT * FROM approved_actuals WHERE schedule_id = %s AND activity_id = %s", (sched_id, act_id))
            act_row = cur.fetchone()
            assert act_row is not None
            assert float(act_row["actual_pct_complete"]) == 60.0
