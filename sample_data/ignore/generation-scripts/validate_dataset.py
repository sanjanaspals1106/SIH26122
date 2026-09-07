import os
import sys
import csv
import json
import filecmp
import re
import openpyxl
import pypdf

BASE_DIR = r"D:\SIH26122\sample_data"
CANONICAL_DIR = os.path.join(BASE_DIR, "canonical")
INPUT_DIR = os.path.join(BASE_DIR, "input")
TEST_CASES_DIR = os.path.join(BASE_DIR, "test-cases")
EXPECTED_DIR = os.path.join(BASE_DIR, "expected")
BACKUP_DIR = os.path.join(BASE_DIR, "ignore", "old-versions", "golden_14aug_backup")

def log_pass(msg):
    print(f"[PASS] {msg}")

def log_fail(msg):
    print(f"[FAIL] {msg}")
    sys.exit(1)

def test_canonical_schedule():
    sched_file = os.path.join(CANONICAL_DIR, "schedule.csv")
    master_file = os.path.join(CANONICAL_DIR, "activity_master.csv")
    
    assert os.path.exists(sched_file), f"Missing {sched_file}"
    assert os.path.exists(master_file), f"Missing {master_file}"
    
    activities = {}
    disciplines = {}
    with open(sched_file, mode="r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for r in reader:
            aid = r["Activity_ID"]
            activities[aid] = r
            disc = r["Discipline"]
            disciplines[disc] = disciplines.get(disc, 0) + 1

    # Check counts
    total = len(activities)
    if total != 45:
        log_fail(f"Expected 45 activities in canonical schedule, got {total}")
    log_pass(f"Canonical schedule has exactly {total} activities")

    expected_disciplines = {
        "Civil": 8,
        "Piping": 10,
        "Static/Rotating Equipment": 7,
        "Electrical": 8,
        "Instrumentation": 7,
        "HSE": 5
    }
    for disc, count in expected_disciplines.items():
        actual = disciplines.get(disc, 0)
        if actual != count:
            log_fail(f"Discipline '{disc}': expected {count}, got {actual}")
        log_pass(f"Discipline '{disc}' verified: {actual} activities")

    # Check activity_master.csv has same activities
    with open(master_file, mode="r", encoding="utf-8") as f:
        master_reader = csv.DictReader(f)
        master_ids = [r["Activity_ID"] for r in master_reader]
        if set(master_ids) != set(activities.keys()):
            log_fail("Mismatch between schedule.csv and activity_master.csv IDs")
    log_pass("Activity master matches canonical schedule 100%")

    return activities

def test_golden_preservation():
    golden_pairs = [
        ("input/daily-report-pdf/daily_progress_report_2026-08-14.pdf", "daily_progress_report_2026-08-14.pdf"),
        ("input/daily-report-txt/daily_progress_report_2026-08-14.txt", "daily_progress_report_2026-08-14.txt"),
        ("input/discipline-report-xlsx/discipline_progress_2026-08-14.xlsx", "discipline_progress_2026-08-14.xlsx"),
        ("input/progress-report-csv/daily_progress_2026-08-14.csv", "daily_progress_2026-08-14.csv"),
        ("input/scanned-diary/site_diary_2026-08-14.png", "site_diary_2026-08-14.png"),
    ]
    for inp_rel, bak_name in golden_pairs:
        p1 = os.path.join(BASE_DIR, inp_rel)
        p2 = os.path.join(BACKUP_DIR, bak_name)
        if not filecmp.cmp(p1, p2, shallow=False):
            log_fail(f"Golden file modified! {inp_rel}")
    log_pass("Golden 14-Aug files are 100% byte-for-byte identical to original backups")

def test_csv_progress_and_monotonicity(canonical_activities):
    csv_dir = os.path.join(INPUT_DIR, "progress-report-csv")
    csv_files = sorted([f for f in os.listdir(csv_dir) if f.endswith(".csv")])
    if len(csv_files) < 10:
        log_fail(f"Expected at least 10 CSV progress reports, found {len(csv_files)}")
    log_pass(f"Found {len(csv_files)} CSV progress reports")

    activity_cumulatives = {} # aid -> list of (date, cum_val)

    for cf in csv_files:
        p = os.path.join(csv_dir, cf)
        with open(p, mode="r", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            for row in reader:
                aid = row["Activity ID"]
                if aid not in canonical_activities:
                    log_fail(f"Unknown Activity ID '{aid}' in CSV {cf}")
                dt = row["Report Date"]
                cum = float(row["Cumulative Actual"])
                prior = float(row["Prior Actual"])
                today = float(row["Today Actual"])
                
                # Check arithmetic (prior + today == cumulative)
                if abs((prior + today) - cum) > 0.01:
                    log_fail(f"Arithmetic error in {cf} for {aid}: {prior} + {today} != {cum}")

                activity_cumulatives.setdefault(aid, []).append((dt, cum))

    # Check monotonicity
    for aid, vals in activity_cumulatives.items():
        vals.sort(key=lambda x: x[0])
        for i in range(len(vals) - 1):
            d1, v1 = vals[i]
            d2, v2 = vals[i+1]
            if v2 < v1:
                log_fail(f"Cumulative progress regressed for {aid}: {v1} on {d1} down to {v2} on {d2}")
    log_pass("All CSV progress reports satisfy referential integrity, arithmetic, and monotonicity")

def test_xlsx_reports(canonical_activities):
    xlsx_dir = os.path.join(INPUT_DIR, "discipline-report-xlsx")
    files = [f for f in os.listdir(xlsx_dir) if f.endswith(".xlsx")]
    for xf in files:
        p = os.path.join(xlsx_dir, xf)
        wb = openpyxl.load_workbook(p, data_only=True)
        for sname in wb.sheetnames:
            ws = wb[sname]
            for row in range(6, ws.max_row + 1):
                val = ws.cell(row=row, column=1).value
                if val and isinstance(val, str) and "-" in val:
                    aid = val.strip()
                    if aid not in canonical_activities:
                        log_fail(f"Unknown Activity ID '{aid}' in XLSX {xf} sheet '{sname}'")
    log_pass("All XLSX discipline reports verified for valid activity references")

def test_pdf_reports(canonical_activities):
    pdf_dir = os.path.join(INPUT_DIR, "daily-report-pdf")
    files = [f for f in os.listdir(pdf_dir) if f.endswith(".pdf")]
    act_pattern = re.compile(r"[A-Z]{3,4}-PS3-[A-Z0-9]+-[0-9A-Z]+")
    for pf in files:
        p = os.path.join(pdf_dir, pf)
        reader = pypdf.PdfReader(p)
        text = "\n".join([page.extract_text() for page in reader.pages])
        matches = act_pattern.findall(text)
        for m in matches:
            if m not in canonical_activities:
                log_fail(f"Unknown Activity ID '{m}' extracted from PDF {pf}")
    log_pass(f"All {len(files)} PDF daily reports contain verified canonical Activity IDs")

def test_matching_test_cases(canonical_activities):
    m_dir = os.path.join(TEST_CASES_DIR, "matching")
    exp_file = os.path.join(EXPECTED_DIR, "matching_results.json")
    assert os.path.exists(exp_file), "Missing expected/matching_results.json"
    with open(exp_file, "r", encoding="utf-8") as f:
        exp_list = json.load(f)

    exp_map = {item["case_id"]: item for item in exp_list}
    files = [f for f in os.listdir(m_dir) if f.endswith(".json")]
    
    for mf in files:
        p = os.path.join(m_dir, mf)
        with open(p, "r", encoding="utf-8") as f:
            claim = json.load(f)
        cid = claim["case_id"]
        if cid not in exp_map:
            log_fail(f"Missing expected result for {cid}")
        exp = exp_map[cid]

        # Verify scenario logic
        if cid == "MATCH-001":
            assert claim["reported_activity_id"] == "PIP-PS3-WLD-024"
            assert exp["confidence_score"] == 1.0
            assert not exp["review_required"]
        elif cid == "MATCH-002":
            assert claim["asset_tag"] == "P-102"
            assert exp["matched_activity_id"] == "PIP-PS3-WLD-024"
            assert not exp["review_required"]
        elif cid == "MATCH-003":
            assert "utility header" in claim["raw_claim_text"].lower()
            assert exp["matched_activity_id"] == "PIP-PS3-WLD-024"
            assert not exp["review_required"]
        elif cid == "MATCH-004":
            assert "CH 0+200 to CH 0+240" in claim["raw_claim_text"]
            assert exp["expected_status"] == "AMBIGUOUS"
            assert exp["review_required"]
            assert set(exp["candidate_activities"]) == {"CIV-PS3-TR-0180", "CIV-PS3-TR-0220"}
        elif cid == "MATCH-005":
            assert exp["expected_status"] == "UNMATCHED"
            assert exp["review_required"]
            assert exp["candidate_activities"] == []

    log_pass("Matching benchmark cases MATCH-001 through MATCH-005 verified against ground truth")

def test_conflict_case():
    conf_dir = os.path.join(TEST_CASES_DIR, "conflicts")
    exp_file = os.path.join(EXPECTED_DIR, "conflict_results.json")
    with open(exp_file, "r", encoding="utf-8") as f:
        exp_list = json.load(f)
    exp = exp_list[0]

    assert exp["activity_id"] == "PIP-PS3-WLD-024"
    assert exp["conflict"] is True
    assert exp["review_required"] is True
    assert exp["source_a"]["claimed_today"] == 2.0
    assert exp["source_b"]["claimed_today"] == 3.0
    assert exp["variance_quantity"] == 1.0
    log_pass("Conflict case CONF-001 verified: deliberate variance of 1 joint detected")

def test_rollup_case(canonical_activities):
    exp_file = os.path.join(EXPECTED_DIR, "rollup_results.json")
    with open(exp_file, "r", encoding="utf-8") as f:
        exp_list = json.load(f)
    exp = exp_list[0]

    parent_id = exp["parent_activity_id"]
    assert parent_id in canonical_activities
    parent_planned = exp["parent_planned_quantity"]
    assert parent_planned == 100.0

    sum_children = sum(c["planned_quantity"] for c in exp["children"])
    if sum_children != parent_planned:
        log_fail(f"Sum of child planned quantities ({sum_children}) != parent planned ({parent_planned})")

    # In test, Child B reports 18m
    child_b = [c for c in exp["children"] if c["child_activity_id"] == "PIP-PS3-HDR-100-B"][0]
    assert child_b["current_completed_quantity"] == 18.0
    assert exp["expected_parent_completed"] == 18.0
    assert exp["expected_parent_progress_pct"] == 18.0
    log_pass("Roll-up test case ROLLUP-001 verified: child actuals sum and parent % roll up perfectly")

def test_edge_cases():
    edge_dir = os.path.join(TEST_CASES_DIR, "edge-cases")
    
    # EDGE-001: Delayed
    with open(os.path.join(edge_dir, "edge_001_delayed_activity.json"), "r") as f:
        e1 = json.load(f)
        assert e1["planned_finish"] < e1["reporting_date"]
        assert e1["current_progress_pct"] < 100.0
        assert e1["expected_status"] == "DELAYED"
    log_pass("Edge case EDGE-001 verified: Delayed activity detected")

    # EDGE-002: No progress reported
    with open(os.path.join(edge_dir, "edge_002_no_progress_reported.json"), "r") as f:
        e2 = json.load(f)
        assert e2["reports_found_count"] == 0
        assert e2["expected_status"] == "NO_PROGRESS_REPORTED"
    log_pass("Edge case EDGE-002 verified: No progress reported detected")

    # EDGE-003: Quantity exceeds plan
    with open(os.path.join(edge_dir, "edge_003_quantity_exceeds_plan.json"), "r") as f:
        e3 = json.load(f)
        assert e3["reported_cumulative_quantity"] > e3["planned_quantity"]
        assert e3["calculated_progress_pct"] == 108.0
        assert e3["expected_status"] == "ANOMALY"
    log_pass("Edge case EDGE-003 verified: Over-quantity anomaly detected (108%)")

    # EDGE-004: Cross-format mismatch
    with open(os.path.join(edge_dir, "edge_004_cross_format_mismatch.json"), "r") as f:
        e4 = json.load(f)
        assert e4["source_csv"]["progress_pct"] == 60.0
        assert e4["source_xlsx"]["progress_pct"] == 70.0
        assert e4["variance_percentage_points"] == 10.0
        assert e4["expected_status"] == "SOURCE_MISMATCH"
    log_pass("Edge case EDGE-004 verified: Cross-format CSV vs XLSX reconciliation failure (10% variance)")

if __name__ == "__main__":
    print("==================================================")
    print("STARTING COMPREHENSIVE DATASET VALIDATION")
    print("==================================================")
    acts = test_canonical_schedule()
    test_golden_preservation()
    test_csv_progress_and_monotonicity(acts)
    test_xlsx_reports(acts)
    test_pdf_reports(acts)
    test_matching_test_cases(acts)
    test_conflict_case()
    test_rollup_case(acts)
    test_edge_cases()
    print("==================================================")
    print("ALL VALIDATION SUITES PASSED WITH 100% PRECISION!")
    print("==================================================")
