import sqlite3
import pytest
from fastapi import HTTPException

from backend.routers.graph import build_activity_graph
from backend.routers.schedule import query_impact_preview
from tests.test_phase5_knowledge_graph import create_test_db


def setup_overlapping_schedules():
    """
    Create two independent schedules (SCHED_A and SCHED_B) with deliberately
    identical/reused activity IDs (ACT-001) but distinct graph structures and data.
    """
    db = create_test_db()

    # --- SCHEDULE A ---
    # ACT-001 -> ACT-002 (FS, 0 lag)
    db.execute(
        """
        INSERT INTO schedule_activities (activity_id, schedule_id, activity_name, discipline, location, planned_start, planned_finish, total_float, is_critical)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        ("ACT-001", "SCHED_A", "Excavation Sched A", "CIVIL", "Zone A", "2026-09-01", "2026-09-10", 0.0, 1),
    )
    db.execute(
        """
        INSERT INTO schedule_activities (activity_id, schedule_id, activity_name, discipline, location, planned_start, planned_finish, total_float, is_critical)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        ("ACT-002", "SCHED_A", "Foundation Sched A", "CIVIL", "Zone A", "2026-09-11", "2026-09-20", 0.0, 1),
    )
    db.execute(
        """
        INSERT INTO schedule_dependencies (dependency_id, schedule_id, predecessor_activity_id, successor_activity_id, relationship_type, lag_days)
        VALUES (?, ?, ?, ?, ?, ?)
        """,
        ("DEP-A1", "SCHED_A", "ACT-001", "ACT-002", "FS", 0.0),
    )
    db.execute(
        """
        INSERT INTO execution_events (event_id, schedule_id, event_date, raw_claim_text, input_channel, matched_activity_id, status)
        VALUES (?, ?, ?, ?, ?, ?, ?)
        """,
        ("EVT-A1", "SCHED_A", "2026-09-02", "Claim A1", "TYPED_TEXT", "ACT-001", "APPROVED"),
    )
    db.execute(
        """
        INSERT INTO planner_decisions (decision_id, event_id, selected_activity_id, action, approved_pct, planner_id, justification)
        VALUES (?, ?, ?, ?, ?, ?, ?)
        """,
        ("DEC-A1", "EVT-A1", "ACT-001", "APPROVE", 50.0, "PLN-A", "Justification A1"),
    )
    db.execute(
        """
        INSERT INTO approved_actuals (actual_id, decision_id, event_id, schedule_id, activity_id, actual_start, actual_pct_complete)
        VALUES (?, ?, ?, ?, ?, ?, ?)
        """,
        ("ACTL-A1", "DEC-A1", "EVT-A1", "SCHED_A", "ACT-001", "2026-09-02", 50.0),
    )

    # --- SCHEDULE B ---
    # ACT-001 -> ACT-003 (FS, 2 lag)
    db.execute(
        """
        INSERT INTO schedule_activities (activity_id, schedule_id, activity_name, discipline, location, planned_start, planned_finish, total_float, is_critical)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        ("ACT-001", "SCHED_B", "Welding Sched B", "PIPING", "Zone B", "2026-09-01", "2026-09-10", 5.0, 0),
    )
    db.execute(
        """
        INSERT INTO schedule_activities (activity_id, schedule_id, activity_name, discipline, location, planned_start, planned_finish, total_float, is_critical)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        ("ACT-003", "SCHED_B", "Hydrotest Sched B", "PIPING", "Zone B", "2026-09-13", "2026-09-25", 5.0, 0),
    )
    db.execute(
        """
        INSERT INTO schedule_dependencies (dependency_id, schedule_id, predecessor_activity_id, successor_activity_id, relationship_type, lag_days)
        VALUES (?, ?, ?, ?, ?, ?)
        """,
        ("DEP-B1", "SCHED_B", "ACT-001", "ACT-003", "FS", 2.0),
    )
    db.execute(
        """
        INSERT INTO execution_events (event_id, schedule_id, event_date, raw_claim_text, input_channel, matched_activity_id, status)
        VALUES (?, ?, ?, ?, ?, ?, ?)
        """,
        ("EVT-B1", "SCHED_B", "2026-09-03", "Claim B1", "TYPED_TEXT", "ACT-001", "APPROVED"),
    )
    db.execute(
        """
        INSERT INTO planner_decisions (decision_id, event_id, selected_activity_id, action, approved_pct, planner_id, justification)
        VALUES (?, ?, ?, ?, ?, ?, ?)
        """,
        ("DEC-B1", "EVT-B1", "ACT-001", "APPROVE", 30.0, "PLN-B", "Justification B1"),
    )
    db.execute(
        """
        INSERT INTO approved_actuals (actual_id, decision_id, event_id, schedule_id, activity_id, actual_start, actual_pct_complete)
        VALUES (?, ?, ?, ?, ?, ?, ?)
        """,
        ("ACTL-B1", "DEC-B1", "EVT-B1", "SCHED_B", "ACT-001", "2026-09-03", 30.0),
    )

    return db


def test_graph_isolation_sched_a():
    """Graph query for Schedule A contains ONLY Schedule A nodes/edges, zero Schedule B records."""
    db = setup_overlapping_schedules()
    graph_a = build_activity_graph("ACT-001", depth=1, schedule_id="SCHED_A", conn=db)

    node_ids = {n["id"] for n in graph_a["nodes"]}
    assert "activity:SCHED_A:ACT-001" in node_ids
    assert "activity:SCHED_A:ACT-002" in node_ids
    assert "event:EVT-A1" in node_ids
    assert "decision:DEC-A1" in node_ids
    assert "actual:ACTL-A1" in node_ids

    # Zero Schedule B leakage
    assert "activity:SCHED_B:ACT-001" not in node_ids
    assert "activity:SCHED_B:ACT-003" not in node_ids
    assert "event:EVT-B1" not in node_ids
    assert "decision:DEC-B1" not in node_ids
    assert "actual:ACTL-B1" not in node_ids

    # Edge checks with explicit edge IDs
    edges = graph_a["edges"]
    assert all("SCHED_B" not in e["source"] and "SCHED_B" not in e["target"] for e in edges)
    assert any(e["id"] == "dependency:activity:SCHED_A:ACT-001->activity:SCHED_A:ACT-002" for e in edges)


def test_graph_isolation_sched_b():
    """Graph query for Schedule B contains ONLY Schedule B nodes/edges, zero Schedule A records."""
    db = setup_overlapping_schedules()
    graph_b = build_activity_graph("ACT-001", depth=1, schedule_id="SCHED_B", conn=db)

    node_ids = {n["id"] for n in graph_b["nodes"]}
    assert "activity:SCHED_B:ACT-001" in node_ids
    assert "activity:SCHED_B:ACT-003" in node_ids
    assert "event:EVT-B1" in node_ids
    assert "decision:DEC-B1" in node_ids
    assert "actual:ACTL-B1" in node_ids

    # Zero Schedule A leakage
    assert "activity:SCHED_A:ACT-001" not in node_ids
    assert "activity:SCHED_A:ACT-002" not in node_ids
    assert "event:EVT-A1" not in node_ids
    assert "decision:DEC-A1" not in node_ids
    assert "actual:ACTL-A1" not in node_ids


def test_graph_ambiguity_raises_409():
    """Querying graph for an ambiguous activity ID without schedule_id raises HTTP 409 Conflict."""
    db = setup_overlapping_schedules()
    with pytest.raises(HTTPException) as exc_info:
        build_activity_graph("ACT-001", depth=1, schedule_id=None, conn=db)
    assert exc_info.value.status_code == 409
    assert "exists in multiple schedules" in exc_info.value.detail


def test_impact_isolation_sched_a():
    """Impact preview for Schedule A propagates to ACT-002 only, completely isolated from Schedule B."""
    db = setup_overlapping_schedules()
    impact_a = query_impact_preview("ACT-001", delay_days=5, schedule_id="SCHED_A", conn=db)

    assert impact_a["schedule_id"] == "SCHED_A"
    assert len(impact_a["impacts"]) == 1
    succ_impact = impact_a["impacts"][0]
    assert succ_impact["successor_activity_id"] == "ACT-002"
    # Zero influence from Schedule B's ACT-003
    assert all(i["successor_activity_id"] != "ACT-003" for i in impact_a["impacts"])


def test_impact_isolation_sched_b():
    """Impact preview for Schedule B propagates to ACT-003 only, completely isolated from Schedule A."""
    db = setup_overlapping_schedules()
    impact_b = query_impact_preview("ACT-001", delay_days=5, schedule_id="SCHED_B", conn=db)

    assert impact_b["schedule_id"] == "SCHED_B"
    assert len(impact_b["impacts"]) == 1
    succ_impact = impact_b["impacts"][0]
    assert succ_impact["successor_activity_id"] == "ACT-003"
    # Zero influence from Schedule A's ACT-002
    assert all(i["successor_activity_id"] != "ACT-002" for i in impact_b["impacts"])


def test_impact_ambiguity_raises_409():
    """Querying impact preview for an ambiguous activity ID without schedule_id raises HTTP 409 Conflict."""
    db = setup_overlapping_schedules()
    with pytest.raises(HTTPException) as exc_info:
        query_impact_preview("ACT-001", delay_days=5, schedule_id=None, conn=db)
    assert exc_info.value.status_code == 409
    assert "exists in multiple schedules" in exc_info.value.detail
