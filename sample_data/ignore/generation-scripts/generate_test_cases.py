import os
import json

BASE_DIR = r"D:\SIH26122\sample_data"
TEST_CASES_DIR = os.path.join(BASE_DIR, "test-cases")
EXPECTED_DIR = os.path.join(BASE_DIR, "expected")

MATCH_DIR = os.path.join(TEST_CASES_DIR, "matching")
CONF_DIR = os.path.join(TEST_CASES_DIR, "conflicts")
ROLLUP_DIR = os.path.join(TEST_CASES_DIR, "rollup")
EDGE_DIR = os.path.join(TEST_CASES_DIR, "edge-cases")

for d in [MATCH_DIR, CONF_DIR, ROLLUP_DIR, EDGE_DIR, EXPECTED_DIR]:
    os.makedirs(d, exist_ok=True)

# -------------------------------------------------------------
# 1. MATCHING BENCHMARK CASES
# -------------------------------------------------------------
MATCH_CASES = [
    {
        "file": "match_001_exact_id.json",
        "claim": {
            "case_id": "MATCH-001",
            "scenario": "EXACT_ID",
            "event_id": "EVT-TEST-M01",
            "schedule_id": "SIH26122_NFU",
            "event_date": "2026-08-14",
            "raw_claim_text": "PIP-PS3-WLD-024: Two field weld joints completed on utility header; visual testing accepted.",
            "input_channel": "DAILY_REPORT_TXT",
            "reported_activity_id": "PIP-PS3-WLD-024",
            "asset_tag": None,
            "discipline": "Piping",
            "claimed_quantity": 2.0,
            "claimed_uom": "joints"
        },
        "expected": {
            "case_id": "MATCH-001",
            "input_file": "test-cases/matching/match_001_exact_id.json",
            "scenario": "EXACT_ID",
            "matched_activity_id": "PIP-PS3-WLD-024",
            "match_tier": "TIER_1_EXACT_ID",
            "confidence_score": 1.0,
            "expected_status": "MATCHED",
            "review_required": False,
            "candidate_activities": ["PIP-PS3-WLD-024"]
        }
    },
    {
        "file": "match_002_asset_tag.json",
        "claim": {
            "case_id": "MATCH-002",
            "scenario": "ASSET_TAG_MATCH",
            "event_id": "EVT-TEST-M02",
            "schedule_id": "SIH26122_NFU",
            "event_date": "2026-08-14",
            "raw_claim_text": "P-102 discharge line welding completed. Two field joints cleared by inspection team.",
            "input_channel": "FIELD_NOTE",
            "reported_activity_id": None,
            "asset_tag": "P-102",
            "discipline": "Piping",
            "claimed_quantity": 2.0,
            "claimed_uom": "joints"
        },
        "expected": {
            "case_id": "MATCH-002",
            "input_file": "test-cases/matching/match_002_asset_tag.json",
            "scenario": "ASSET_TAG_MATCH",
            "matched_activity_id": "PIP-PS3-WLD-024",
            "match_tier": "TIER_2_ASSET_TAG",
            "confidence_score": 0.92,
            "expected_status": "MATCHED",
            "review_required": False,
            "candidate_activities": ["PIP-PS3-WLD-024"],
            "resolution_path": "Asset Tag P-102 maps to PIP-PS3-WLD-024"
        }
    },
    {
        "file": "match_003_semantic.json",
        "claim": {
            "case_id": "MATCH-003",
            "scenario": "SEMANTIC_MATCH",
            "event_id": "EVT-TEST-M03",
            "schedule_id": "SIH26122_NFU",
            "event_date": "2026-08-14",
            "raw_claim_text": "Two field weld joints completed on utility header.",
            "input_channel": "VOICE_TRANSCRIPT",
            "reported_activity_id": None,
            "asset_tag": None,
            "discipline": "Piping",
            "claimed_quantity": 2.0,
            "claimed_uom": "joints"
        },
        "expected": {
            "case_id": "MATCH-003",
            "input_file": "test-cases/matching/match_003_semantic.json",
            "scenario": "SEMANTIC_MATCH",
            "matched_activity_id": "PIP-PS3-WLD-024",
            "match_tier": "TIER_3_SEMANTIC",
            "confidence_score": 0.86,
            "expected_status": "MATCHED",
            "review_required": False,
            "candidate_activities": ["PIP-PS3-WLD-024"]
        }
    },
    {
        "file": "match_004_ambiguous.json",
        "claim": {
            "case_id": "MATCH-004",
            "scenario": "AMBIGUOUS_MATCH",
            "event_id": "EVT-TEST-M04",
            "schedule_id": "SIH26122_NFU",
            "event_date": "2026-08-15",
            "raw_claim_text": "Utility trench excavation from approximately CH 0+200 to CH 0+240 completed.",
            "input_channel": "SUPERVISOR_NOTE",
            "reported_activity_id": None,
            "asset_tag": None,
            "discipline": "Civil",
            "claimed_quantity": 40.0,
            "claimed_uom": "m"
        },
        "expected": {
            "case_id": "MATCH-004",
            "input_file": "test-cases/matching/match_004_ambiguous.json",
            "scenario": "AMBIGUOUS_MATCH",
            "matched_activity_id": None,
            "match_tier": "TIER_4_AMBIGUOUS",
            "confidence_score": 0.52,
            "expected_status": "AMBIGUOUS",
            "review_required": True,
            "candidate_activities": [
                "CIV-PS3-TR-0180",
                "CIV-PS3-TR-0220"
            ],
            "ambiguity_reason": "Claim chainage CH 0+200 to CH 0+240 overlaps both CIV-PS3-TR-0180 (CH 0+180 to 0+220) and CIV-PS3-TR-0220 (CH 0+220 to 0+260)"
        }
    },
    {
        "file": "match_005_unmatched.json",
        "claim": {
            "case_id": "MATCH-005",
            "scenario": "UNMATCHED",
            "event_id": "EVT-TEST-M05",
            "schedule_id": "SIH26122_NFU",
            "event_date": "2026-08-16",
            "raw_claim_text": "Temporary rain shelter installed at laydown area.",
            "input_channel": "FIELD_NOTE",
            "reported_activity_id": None,
            "asset_tag": None,
            "discipline": "General Works",
            "claimed_quantity": 1.0,
            "claimed_uom": "each"
        },
        "expected": {
            "case_id": "MATCH-005",
            "input_file": "test-cases/matching/match_005_unmatched.json",
            "scenario": "UNMATCHED",
            "matched_activity_id": None,
            "match_tier": "UNMATCHED",
            "confidence_score": 0.12,
            "expected_status": "UNMATCHED",
            "review_required": True,
            "candidate_activities": [],
            "unmatched_reason": "Temporary rain shelter at laydown area has no matching activity in canonical baseline schedule"
        }
    }
]

# -------------------------------------------------------------
# 2. CONFLICT TEST CASES
# -------------------------------------------------------------
CONF_CLAIMS = [
    {
        "file": "conf_001_source_a_txt_claim.json",
        "claim": {
            "conflict_case_id": "CONF-001",
            "source_id": "SOURCE_A",
            "source_document": "input/daily-report-txt/daily_progress_report_2026-08-14.txt",
            "reporting_period": "2026-08-14",
            "activity_id": "PIP-PS3-WLD-024",
            "claimed_today_quantity": 2.0,
            "cumulative_quantity": 22.0,
            "planned_quantity": 24.0,
            "uom": "joints",
            "progress_pct": 91.7,
            "raw_snippet": "PIP-PS3-WLD-024 | Piping | Two field weld joints completed; visual testing accepted. Today: 2 joints | Cumulative: 22/24 joints"
        }
    },
    {
        "file": "conf_001_source_b_field_claim.json",
        "claim": {
            "conflict_case_id": "CONF-001",
            "source_id": "SOURCE_B",
            "source_document": "test-cases/conflicts/conf_001_source_b_field_claim.json",
            "reporting_period": "2026-08-14",
            "activity_id": "PIP-PS3-WLD-024",
            "claimed_today_quantity": 3.0,
            "cumulative_quantity": 23.0,
            "planned_quantity": 24.0,
            "uom": "joints",
            "progress_pct": 95.8,
            "raw_snippet": "Welding foreman report: 3 field weld joints completed on 16-inch header line at Pump Station 3 today (cumulative 23 joints)."
        }
    }
]

EXPECTED_CONFLICT = [
    {
        "conflict_id": "CONF-001",
        "activity_id": "PIP-PS3-WLD-024",
        "reporting_period": "2026-08-14",
        "conflict": True,
        "review_required": True,
        "source_a": {
            "document": "input/daily-report-txt/daily_progress_report_2026-08-14.txt",
            "claimed_today": 2.0,
            "cumulative": 22.0,
            "uom": "joints",
            "pct": 91.7
        },
        "source_b": {
            "document": "test-cases/conflicts/conf_001_source_b_field_claim.json",
            "claimed_today": 3.0,
            "cumulative": 23.0,
            "uom": "joints",
            "pct": 95.8
        },
        "variance_quantity": 1.0,
        "variance_pct": 4.17,
        "status": "OPEN",
        "planner_action_required": "Resolve quantity mismatch: Source A claims 2 joints vs Source B claims 3 joints on 14-Aug-2026"
    }
]

# -------------------------------------------------------------
# 3. ROLL-UP TEST CASES
# -------------------------------------------------------------
ROLLUP_CLAIM = {
    "file": "rollup_001_child_b_claim.json",
    "claim": {
        "rollup_case_id": "ROLLUP-001",
        "event_id": "EVT-ROLLUP-001",
        "schedule_id": "SIH26122_NFU",
        "event_date": "2026-08-19",
        "reported_activity_id": "PIP-PS3-HDR-100-B",
        "parent_activity_id": "PIP-PS3-HDR-100",
        "raw_claim_text": "PIP-PS3-HDR-100-B: Utility header spool Section B fit-up and erection completed 18 m of 30 m planned.",
        "claimed_completed_quantity": 18.0,
        "claimed_uom": "m",
        "child_progress_pct": 60.0
    }
}

EXPECTED_ROLLUP = [
    {
        "rollup_case_id": "ROLLUP-001",
        "parent_activity_id": "PIP-PS3-HDR-100",
        "parent_activity_name": "Above Ground Utility Header Fabrication",
        "parent_planned_quantity": 100.0,
        "parent_unit": "m",
        "children": [
            {
                "child_activity_id": "PIP-PS3-HDR-100-A",
                "planned_quantity": 40.0,
                "current_completed_quantity": 0.0,
                "progress_pct": 0.0
            },
            {
                "child_activity_id": "PIP-PS3-HDR-100-B",
                "planned_quantity": 30.0,
                "current_completed_quantity": 18.0,
                "progress_pct": 60.0
            },
            {
                "child_activity_id": "PIP-PS3-HDR-100-C",
                "planned_quantity": 30.0,
                "current_completed_quantity": 0.0,
                "progress_pct": 0.0
            }
        ],
        "calculation": {
            "formula": "Parent_Completed = sum(Child_Completed); Parent_Progress = (Parent_Completed / Parent_Planned) * 100",
            "parent_completed_quantity": 18.0,
            "parent_progress_pct": 18.0
        },
        "expected_parent_completed": 18.0,
        "expected_parent_progress_pct": 18.0,
        "status": "VALIDATED"
    }
]

# -------------------------------------------------------------
# 4. EDGE CASES
# -------------------------------------------------------------
EDGE_CASES = [
    {
        "file": "edge_001_delayed_activity.json",
        "data": {
            "case_id": "EDGE-001",
            "edge_case_type": "DELAYED_ACTIVITY",
            "activity_id": "ELE-PS3-CBL-001",
            "activity_name": "11kV Medium Voltage Cable Pulling",
            "planned_start": "2026-08-12",
            "planned_finish": "2026-08-18",
            "reporting_date": "2026-08-20",
            "planned_quantity": 500.0,
            "cumulative_actual": 300.0,
            "current_progress_pct": 60.0,
            "unit": "m",
            "delay_reason": "Cable drum delivery delayed at port",
            "expected_status": "DELAYED",
            "expected_slippage_days": 2,
            "review_required": True
        }
    },
    {
        "file": "edge_002_no_progress_reported.json",
        "data": {
            "case_id": "EDGE-002",
            "edge_case_type": "NO_PROGRESS_REPORTED",
            "activity_id": "INS-PS3-FGS-001",
            "activity_name": "Fire & Gas Detector Mounting",
            "planned_start": "2026-08-18",
            "planned_finish": "2026-08-22",
            "planned_quantity": 16.0,
            "unit": "ea",
            "reporting_period": "2026-08-18 to 2026-08-22",
            "reports_found_count": 0,
            "expected_status": "NO_PROGRESS_REPORTED",
            "review_required": False
        }
    },
    {
        "file": "edge_003_quantity_exceeds_plan.json",
        "data": {
            "case_id": "EDGE-003",
            "edge_case_type": "QUANTITY_EXCEEDS_PLAN",
            "activity_id": "PIP-PS3-SPT-030",
            "activity_name": "Pipe Support Secondary Steel Erection",
            "reporting_date": "2026-08-21",
            "source_document": "input/progress-report-csv/daily_progress_2026-08-21.csv",
            "planned_quantity": 100.0,
            "reported_cumulative_quantity": 108.0,
            "calculated_progress_pct": 108.0,
            "unit": "ea",
            "excess_quantity": 8.0,
            "excess_percentage": 8.0,
            "expected_status": "ANOMALY",
            "review_required": True,
            "anomaly_reason": "Reported cumulative quantity (108 ea) exceeds planned baseline quantity (100 ea) by 8 ea (8.0%)"
        }
    },
    {
        "file": "edge_004_cross_format_mismatch.json",
        "data": {
            "case_id": "EDGE-004",
            "edge_case_type": "CROSS_FORMAT_MISMATCH",
            "activity_id": "ELE-PS3-TR-005",
            "activity_name": "Cable Tray Installation Piperack Tier 2",
            "reporting_date": "2026-08-20",
            "planned_quantity": 200.0,
            "unit": "m",
            "source_csv": {
                "file": "input/progress-report-csv/daily_progress_2026-08-20.csv",
                "cumulative_actual": 120.0,
                "progress_pct": 60.0
            },
            "source_xlsx": {
                "file": "input/discipline-report-xlsx/discipline_progress_2026-08-20.xlsx",
                "sheet": "Electrical",
                "cumulative_actual": 140.0,
                "progress_pct": 70.0
            },
            "variance_percentage_points": 10.0,
            "variance_quantity": 20.0,
            "expected_status": "SOURCE_MISMATCH",
            "review_required": True,
            "mismatch_reason": "Cross-format reconciliation failure: CSV reports 120 m (60.0%) while XLSX reports 140 m (70.0%) for same reporting date 20-Aug-2026"
        }
    }
]

def generate_test_case_files():
    # 1. Matching
    expected_matches = []
    for item in MATCH_CASES:
        p = os.path.join(MATCH_DIR, item["file"])
        with open(p, "w", encoding="utf-8") as f:
            json.dump(item["claim"], f, indent=2)
        print(f"Generated Matching test case: {p}")
        expected_matches.append(item["expected"])

    match_exp_file = os.path.join(EXPECTED_DIR, "matching_results.json")
    with open(match_exp_file, "w", encoding="utf-8") as f:
        json.dump(expected_matches, f, indent=2)
    print(f"Generated Expected Matching Results: {match_exp_file}")

    # 2. Conflicts
    for item in CONF_CLAIMS:
        p = os.path.join(CONF_DIR, item["file"])
        with open(p, "w", encoding="utf-8") as f:
            json.dump(item["claim"], f, indent=2)
        print(f"Generated Conflict test claim: {p}")

    conf_exp_file = os.path.join(EXPECTED_DIR, "conflict_results.json")
    with open(conf_exp_file, "w", encoding="utf-8") as f:
        json.dump(EXPECTED_CONFLICT, f, indent=2)
    print(f"Generated Expected Conflict Results: {conf_exp_file}")

    # 3. Rollup
    p = os.path.join(ROLLUP_DIR, ROLLUP_CLAIM["file"])
    with open(p, "w", encoding="utf-8") as f:
        json.dump(ROLLUP_CLAIM["claim"], f, indent=2)
    print(f"Generated Rollup test claim: {p}")

    rollup_exp_file = os.path.join(EXPECTED_DIR, "rollup_results.json")
    with open(rollup_exp_file, "w", encoding="utf-8") as f:
        json.dump(EXPECTED_ROLLUP, f, indent=2)
    print(f"Generated Expected Rollup Results: {rollup_exp_file}")

    # 4. Edge cases
    for item in EDGE_CASES:
        p = os.path.join(EDGE_DIR, item["file"])
        with open(p, "w", encoding="utf-8") as f:
            json.dump(item["data"], f, indent=2)
        print(f"Generated Edge Case test: {p}")

if __name__ == "__main__":
    generate_test_case_files()
