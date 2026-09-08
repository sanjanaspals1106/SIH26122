from datetime import date
import os
import sys
from unittest.mock import MagicMock, patch

# Ensure root directory is on sys.path
sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)))

from fastapi.testclient import TestClient

from backend.main import app
from backend.routers.matching import (
    EXACT_ASSET,
    EXACT_ID,
    HARD_MISMATCH,
    HYBRID_FALLBACK,
    calculate_discipline_score,
    calculate_fuzzy_score,
    calculate_hybrid_score,
    calculate_location_score,
    evaluate_hard_mismatch,
    generate_hybrid_candidates,
    match_claim,
    match_exact_asset,
    match_exact_id,
    rank_and_explain_candidates,
)
from backend.shared.schemas import ExecutionClaim, ScheduleActivity


def run_final_verification():
    print("==========================================================")
    print("       M3 MATCHING ENGINE — FINAL VERIFICATION           ")
    print("==========================================================")

    results = {}

    # Sample Activities
    act_a1000 = ScheduleActivity(
        schedule_id="SCH-001",
        activity_id="A1000",
        activity_name="Foundation Excavation Zone A",
        discipline="Civil",
        location="Zone A",
        asset_tag="EXC-01",
        planned_start=date(2026, 8, 1),
        planned_finish=date(2026, 8, 15),
        baseline_pct_complete=0.0,
    )

    act_pump = ScheduleActivity(
        schedule_id="SCH-001",
        activity_id="ACT-PUMP-99",
        activity_name="Water Pump Installation",
        discipline="Piping",
        location="Zone A",
        asset_tag="PUMP-99",
        planned_start=date(2026, 8, 1),
        planned_finish=date(2026, 8, 15),
        baseline_pct_complete=0.0,
    )

    act_concrete = ScheduleActivity(
        schedule_id="SCH-001",
        activity_id="ACT-CONCRETE",
        activity_name="Concrete Pouring Zone B",
        discipline="Civil",
        location="Zone B",
        asset_tag=None,
        planned_start=date(2026, 8, 16),
        planned_finish=date(2026, 8, 30),
        baseline_pct_complete=0.0,
    )

    activities = [act_a1000, act_pump, act_concrete]

    # Check 1: EXACT_ID matching and confidence 1.00
    try:
        claim_1 = ExecutionClaim(
            event_id="EVT-1",
            schedule_id="SCH-001",
            event_date=date(2026, 8, 14),
            raw_claim_text="Reported A1000",
            input_channel="DAILY_REPORT",
            reported_activity_id="A1000",
        )
        res1 = match_exact_id(claim_1, activities)
        assert (
            res1 is not None
            and res1.match_tier == EXACT_ID
            and res1.composite_confidence == 1.00
        )
        results["Check 1 — EXACT_ID Matching & Confidence 1.00"] = "PASS"
    except Exception as e:
        results["Check 1 — EXACT_ID Matching & Confidence 1.00"] = (
            f"FAIL ({e})"
        )

    # Check 2: EXACT_ASSET matching and confidence rules
    try:
        claim_2 = ExecutionClaim(
            event_id="EVT-2",
            schedule_id="SCH-001",
            event_date=date(2026, 8, 14),
            raw_claim_text="Installed PUMP-99",
            input_channel="DAILY_REPORT",
            asset_tag="PUMP-99",
            discipline="Piping",
            location="Zone A",
        )
        res2 = match_exact_asset(claim_2, activities)
        assert (
            len(res2) > 0
            and res2[0].match_tier == EXACT_ASSET
            and res2[0].composite_confidence == 0.95
        )
        results["Check 2 — EXACT_ASSET Matching & Confidence Rules"] = "PASS"
    except Exception as e:
        results["Check 2 — EXACT_ASSET Matching & Confidence Rules"] = (
            f"FAIL ({e})"
        )

    # Check 3: HYBRID_FALLBACK scoring using semantic, fuzzy, location, discipline signals
    try:
        sem_score = 0.80
        fuz_score = calculate_fuzzy_score(
            "Foundation Excavation Zone A", "Foundation Excavation Zone A"
        )
        loc_score = calculate_location_score("Zone A", "Zone A")
        disc_score = calculate_discipline_score("Civil", "Civil")
        comp = calculate_hybrid_score(
            sem_score, fuz_score, loc_score, disc_score
        )
        expected_comp = (
            0.50 * 0.80 + 0.25 * 1.0 + 0.15 * 1.0 + 0.10 * 1.0
        )  # 0.40 + 0.25 + 0.15 + 0.10 = 0.90
        assert abs(comp - expected_comp) < 1e-5
        results["Check 3 — HYBRID_FALLBACK Composite Scoring"] = "PASS"
    except Exception as e:
        results["Check 3 — HYBRID_FALLBACK Composite Scoring"] = f"FAIL ({e})"

    # Check 4: HARD_MISMATCH for genuine conflicts
    try:
        claim_conflict = ExecutionClaim(
            event_id="EVT-4",
            schedule_id="SCH-001",
            event_date=date(2026, 8, 14),
            raw_claim_text="Electrical wiring done",
            input_channel="DAILY_REPORT",
            discipline="Electrical",
            location="Zone A",
        )
        res4 = evaluate_hard_mismatch(claim_conflict, act_a1000)
        assert (
            res4 is not None
            and res4.match_tier == HARD_MISMATCH
            and res4.composite_confidence <= 0.40
        )
        results["Check 4 — HARD_MISMATCH Conflict Evaluation"] = "PASS"
    except Exception as e:
        results["Check 4 — HARD_MISMATCH Conflict Evaluation"] = f"FAIL ({e})"

    # Check 5: Correct cascade order EXACT_ID -> EXACT_ASSET -> HYBRID_FALLBACK -> HARD_MISMATCH
    try:
        # EXACT_ID priority
        cascade_1 = match_claim(claim_1, activities)
        assert cascade_1[0].match_tier == EXACT_ID

        # EXACT_ASSET priority when EXACT_ID missing
        cascade_2 = match_claim(claim_2, activities)
        assert cascade_2[0].match_tier == EXACT_ASSET

        # HYBRID_FALLBACK when exact missing
        claim_hybrid = ExecutionClaim(
            event_id="EVT-H",
            schedule_id="SCH-001",
            event_date=date(2026, 8, 14),
            raw_claim_text="Foundation Excavation Zone A",
            input_channel="DAILY_REPORT",
            discipline="Civil",
            location="Zone A",
        )
        cascade_3 = match_claim(claim_hybrid, activities)
        assert cascade_3[0].match_tier == HYBRID_FALLBACK

        # HARD_MISMATCH when conflict exists
        cascade_4 = match_claim(claim_conflict, [act_a1000])
        assert cascade_4[0].match_tier == HARD_MISMATCH

        results["Check 5 — 4-Tier Cascade Priority Order"] = "PASS"
    except Exception as e:
        results["Check 5 — 4-Tier Cascade Priority Order"] = f"FAIL ({e})"

    # Check 6: Top-3 ranking is deterministic
    try:
        hybrid_cands = generate_hybrid_candidates(claim_hybrid, activities)
        ranked = rank_and_explain_candidates(hybrid_cands)
        assert len(ranked) <= 3
        assert ranked[0].rank_order == 1
        assert ranked[0].composite_confidence >= ranked[1].composite_confidence
        results["Check 6 — Deterministic Top-3 Ranking"] = "PASS"
    except Exception as e:
        results["Check 6 — Deterministic Top-3 Ranking"] = f"FAIL ({e})"

    # Check 7: Candidate explanations/signals are populated
    try:
        top_cand = ranked[0]
        assert (
            top_cand.supporting_signals is not None
            and len(top_cand.supporting_signals) > 0
        )
        results["Check 7 — Candidate Explanation Signals Populated"] = "PASS"
    except Exception as e:
        results["Check 7 — Candidate Explanation Signals Populated"] = (
            f"FAIL ({e})"
        )

    # Check 8: activity_id remains the external schedule activity_id string
    try:
        assert top_cand.activity_id == "A1000"
        results["Check 8 — Unchanged Source activity_id String"] = "PASS"
    except Exception as e:
        results["Check 8 — Unchanged Source activity_id String"] = f"FAIL ({e})"

    # Check 9: Unmatched claims remain unmatched when no valid candidate exists
    try:
        claim_unmatchable = ExecutionClaim(
            event_id="EVT-UNMATCH",
            schedule_id="SCH-001",
            event_date=date(2026, 8, 14),
            raw_claim_text="Plumbing repairs",
            input_channel="DAILY_REPORT",
            discipline="Plumbing",
        )
        res_unmatched = match_claim(claim_unmatchable, [act_a1000])
        assert (
            res_unmatched[0].match_tier == HARD_MISMATCH
            or res_unmatched[0].composite_confidence <= 0.40
        )
        results["Check 9 — Unmatched Claim Handling"] = "PASS"
    except Exception as e:
        results["Check 9 — Unmatched Claim Handling"] = f"FAIL ({e})"

    # Check 10: Rematch function behavior using mocked/in-memory data
    try:
        client = TestClient(app)
        mock_event = {
            "event_id": "EVT-TEST-10",
            "document_id": "DOC-10",
            "schedule_id": "SCH-001",
            "event_date": date(2026, 8, 14),
            "raw_claim_text": "Foundation Excavation Zone A",
            "input_channel": "DAILY_REPORT",
            "reported_activity_id": None,
            "matched_activity_id": None,
            "discipline": "Civil",
            "action": None,
            "event_type": None,
            "claim_mode": "CUMULATIVE_PCT",
            "asset_tag": None,
            "location": "Zone A",
            "claimed_quantity": None,
            "claimed_uom": None,
            "claimed_pct": 100.0,
            "delay_reason": None,
            "supervisor_id": None,
            "photo_path": None,
            "status": "UNMATCHED",
            "created_at": None,
        }

        with patch("backend.routers.matching.get_connection") as mock_get_conn:
            mock_conn = MagicMock()
            mock_cur = MagicMock()
            mock_get_conn.return_value.__enter__.return_value = mock_conn
            mock_conn.cursor.return_value.__enter__.return_value = mock_cur

            mock_cur.fetchone.return_value = mock_event
            mock_cur.fetchall.return_value = [
                {
                    "schedule_id": "SCH-001",
                    "activity_id": "A1000",
                    "activity_name": "Foundation Excavation Zone A",
                    "wbs_code": "1.1",
                    "discipline": "Civil",
                    "location": "Zone A",
                    "asset_tag": None,
                    "planned_start": date(2026, 8, 1),
                    "planned_finish": date(2026, 8, 15),
                    "planned_quantity": 100.0,
                    "uom": "m3",
                    "baseline_pct_complete": 0.0,
                }
            ]

            response = client.post("/api/v1/claims/EVT-TEST-10/rematch")
            assert response.status_code == 200
            data = response.json()
            assert data["status"] == "MATCHED"
            assert data["matched_activity_id"] == "A1000"

        results["Check 10 — Rematch Function Execution"] = "PASS"
    except Exception as e:
        results["Check 10 — Rematch Function Execution"] = f"FAIL ({e})"

    # Check 11: No duplicate candidate generation in matching logic
    try:
        with patch("backend.routers.matching.get_connection") as mock_get_conn:
            mock_conn = MagicMock()
            mock_cur = MagicMock()
            mock_get_conn.return_value.__enter__.return_value = mock_conn
            mock_conn.cursor.return_value.__enter__.return_value = mock_cur

            mock_cur.fetchone.return_value = mock_event
            mock_cur.fetchall.return_value = [
                {
                    "schedule_id": "SCH-001",
                    "activity_id": "A1000",
                    "activity_name": "Foundation Excavation Zone A",
                    "wbs_code": "1.1",
                    "discipline": "Civil",
                    "location": "Zone A",
                    "asset_tag": None,
                    "planned_start": date(2026, 8, 1),
                    "planned_finish": date(2026, 8, 15),
                    "planned_quantity": 100.0,
                    "uom": "m3",
                    "baseline_pct_complete": 0.0,
                }
            ]

            client.post("/api/v1/claims/EVT-TEST-10/match")
            sqls = [call[0][0] for call in mock_cur.execute.call_args_list]
            delete_called = any(
                "DELETE FROM candidate_matches" in s for s in sqls
            )
            assert delete_called

        results["Check 11 — Duplicate Candidate Elimination"] = "PASS"
    except Exception as e:
        results["Check 11 — Duplicate Candidate Elimination"] = f"FAIL ({e})"

    # Check 12: Verify both route definitions exist in matching.py
    try:
        registered_paths = [r.path for r in app.routes if hasattr(r, "path")]
        assert "/api/v1/claims/{event_id}/match" in registered_paths
        assert "/api/v1/claims/{event_id}/rematch" in registered_paths
        results[
            "Check 12 — Route Definitions /match & /rematch Registered"
        ] = "PASS"
    except Exception as e:
        results[
            "Check 12 — Route Definitions /match & /rematch Registered"
        ] = f"FAIL ({e})"

    # Output Summary
    print("\n------------------- VERIFICATION RESULTS -------------------")
    all_passed = True
    for check_name, status in results.items():
        print(f"[{status}] {check_name}")
        if not status.startswith("PASS"):
            all_passed = False

    print("------------------------------------------------------------")
    if all_passed:
        print("OVERALL VERIFICATION: PASS (12/12 CHECKS PASSED)")
    else:
        print("OVERALL VERIFICATION: FAIL")


if __name__ == "__main__":
    run_final_verification()
