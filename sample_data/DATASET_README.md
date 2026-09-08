# SIH26122 Benchmark Dataset — User Guide & Architecture Manual

## 1. Dataset Purpose
This benchmark dataset is created for the **SIH26122** project: *Heterogeneous construction and project-progress data ingestion, normalization, activity matching, conflict detection, progress calculation, and roll-up*.

The dataset provides a **small, clean, realistic, and internally consistent** ground-truth foundation designed specifically around the application processing pipeline:

```text
Raw Heterogeneous Inputs (XER, PDF, TXT, XLSX, CSV, Scanned Diary, JSON)
       │
       ▼
Extraction / OCR & Normalization
       │
       ▼
Activity Matching (Exact ID, Asset Tag, Semantic, Ambiguous, Unmatched)
       │
       ▼
Confidence Scoring & Planner Review Routing
       │
       ▼
Conflict Detection & Discrepancy Flagging
       │
       ▼
Progress Calculation & Child-to-Parent Roll-up
       │
       ▼
Approved Baseline Schedule Update
```

---

## 2. Directory Architecture

```text
D:\SIH26122\sample_data\
│
├── canonical/
│   ├── schedule.csv                  # SINGLE SOURCE OF TRUTH (Ground Truth Baseline - 45 activities)
│   └── activity_master.csv           # Detailed lookup: roles, inspection hold points, safety criticality
│
├── input/
│   ├── schedule-xer/
│   │   └── sih26122_schedule.xer     # Input P6 XER representation resolving 1-to-1 to canonical schedule
│   ├── daily-report-txt/             # 6 plain-text DPRs (11, 13, 14, 15, 19, 21-Aug)
│   ├── daily-report-pdf/             # 4 machine-readable PDF DPRs (12, 14, 18, 21-Aug)
│   ├── discipline-report-xlsx/       # 3 multi-sheet Excel discipline reports with formulas (14, 18, 20-Aug)
│   ├── progress-report-csv/          # 10 tabular daily progress CSV tracking sheets (11 to 22-Aug)
│   ├── scanned-diary/                # 2 handwritten supervisor log scans (14, 21-Aug)
│   └── field-reports-json/           # 4 structured site execution events / field claims (12, 14, 19, 22-Aug)
│
├── test-cases/
│   ├── matching/                     # 5 dedicated matching scenario payloads (MATCH-001 to MATCH-005)
│   ├── conflicts/                    # 2 conflicting claims on PIP-PS3-WLD-024 (2 vs 3 joints on 14-Aug)
│   ├── rollup/                       # Child claim on PIP-PS3-HDR-100-B testing roll-up into PIP-PS3-HDR-100
│   └── edge-cases/                   # 4 edge case scenarios (Delayed, No-Progress, Over-Qty, Cross-Source)
│
├── expected/
│   ├── matching_results.json         # Ground truth expected matching outcomes and confidence tiers
│   ├── conflict_results.json         # Ground truth expected conflict flags, source files, and variances
│   └── rollup_results.json           # Ground truth expected parent quantity and progress percentage roll-ups
│
├── ignore/
│   ├── public-reference-files/       # sample_schedule_borouge4_reference.xer (Public P6 demo file)
│   ├── source-notes/
│   │   └── README.md                 # Detailed public provenance, schema derivation, and synthetic notes
│   ├── generation-scripts/           # Python generators and automated validation suite
│   ├── intermediate-files/           # Temporary staging or OCR artifacts
│   └── old-versions/                 # Original/superseded raw files and byte-for-byte 14-Aug backup
│
├── dataset_manifest.json             # Machine-readable inventory with file hashes, sizes, and categories
└── DATASET_README.md                 # This benchmark documentation manual
```

---

## 3. Canonical Schedule (Ground Truth)
The ground truth baseline is established in [`canonical/schedule.csv`](file:///D:/SIH26122/sample_data/canonical/schedule.csv) and enriched in [`canonical/activity_master.csv`](file:///D:/SIH26122/sample_data/canonical/activity_master.csv).

- **Total Activities**: **45 activities**
- **Project**: North Field Utility Corridor (Pump Station 3 Tie-In)
- **Schedule ID**: `SIH26122_NFU`
- **Data Date**: 2026-08-10 to 2026-08-22

### Discipline Breakdown:
| Discipline | Activity Count | Primary Work Scope | Key Asset Tags |
| :--- | :---: | :--- | :--- |
| **Civil** | 8 | Utility corridor trench excavation, blinding, pump foundation rebar/pour, road crossing duct banks, drainage channels, trench backfill | `TR-0180`, `TR-0220`, `FND-P101`, `DRN-001`, `RD-001`, `BKF-001` |
| **Piping** | 10 | Utility header welding, header fabrication (Parent roll-up + 3 Child sections), firewater spooling, hydrotesting, gate valves, pipe supports, tie-in spools | `P-102`, `HDR-100`, `HDR-100-A/B/C`, `FW-SPO-015`, `FW-LOOP-01`, `VLV-12-005`, `SPT-030`, `M-01` |
| **Static/Rotating Equipment** | 7 | Dewatering pump relocation, crude pump baseplate grouting, crude pump rigging & laser alignment, sump tank inspection, chemical skid positioning, air receiver vessel erection, diesel generator | `DWP-003`, `P-101`, `P-102`, `TK-01`, `SK-02`, `V-103`, `DG-01` |
| **Electrical** | 8 | Cable trench bedding at MCC-02 and MCC-01, 11kV MV cable pulling, 415V LV auxiliary cables, cable tray installation Tier 2, earth pit grid, high mast lighting, 11kV switchgear | `MCC-02`, `MCC-01`, `MV-CBL-01`, `LV-CBL-02`, `TR-005`, `EAR-001`, `LGT-002`, `SWG-001` |
| **Instrumentation** | 7 | SS316 junction boxes, instrument cable trays, signal & thermocouple cables, pressure transmitter impulse tubing, ultrasonic flowmeters, fire & gas detectors, control valve calibration | `JB-101`, `ITR-002`, `INS-CBL-04`, `PT-1021`, `FT-201`, `FGS-001`, `FCV-101` |
| **HSE** | 5 | Daily safety inductions/toolbox talks, deep excavation hard barricading, confined space multi-gas monitoring, hazardous waste storage/manifests, weekly environmental compliance audits | `HSE-IND`, `HSE-BAR`, `HSE-GAS`, `HSE-WST`, `HSE-AUD` |

---

## 4. Multi-Date Heterogeneous Reporting Matrix
Progress is recorded across 10 reporting dates with realistic format diversity:

| Date | TXT DPR | PDF DPR | XLSX Report | CSV Progress | Scanned Diary | JSON Field Claim | Key Milestone / Events |
| :---: | :---: | :---: | :---: | :---: | :---: | :---: | :--- |
| **11-Aug-2026** | Yes | - | - | Yes | - | - | Blinding started; header root pass welding started |
| **12-Aug-2026** | - | Yes | - | Yes | - | Yes | Pump base blinding 45m3; Section A spool fit-up |
| **13-Aug-2026** | Yes | - | - | Yes | - | - | Pump blinding 100% complete; header 20 joints VT accepted |
| **14-Aug-2026** | **Yes** | **Yes** | **Yes** | **Yes** | **Yes** | **Yes** | **GOLDEN INTEGRATION CASE** (Preserved byte-for-byte) |
| **15-Aug-2026** | Yes | - | - | Yes | - | - | Header welding 100% complete (24 joints); MCC-02 bedding 100% |
| **18-Aug-2026** | - | Yes | Yes | Yes | - | - | Pump plinth rebar 100%; Tier 2 cable tray erection |
| **19-Aug-2026** | Yes | - | - | Yes | - | Yes | Pump foundation concrete pour; Section B 18m (Rollup test) |
| **20-Aug-2026** | - | - | **Yes** | **Yes** | - | - | **EDGE-004 Cross-format mismatch** (CSV 60% vs XLSX 70%) |
| **21-Aug-2026** | Yes | Yes | - | **Yes** | **Yes** | - | **EDGE-003 Over-quantity** (Pipe supports 108%); P-102 laser alignment |
| **22-Aug-2026** | - | - | - | Yes | - | Yes | Close of reporting period; DG-01 positioned; audit closed |

---

## 5. Golden Integration Baseline (14-Aug-2026)
The files for **14-Aug-2026** are the primary multi-source golden integration test:
- `input/daily-report-pdf/daily_progress_report_2026-08-14.pdf`
- `input/daily-report-txt/daily_progress_report_2026-08-14.txt`
- `input/discipline-report-xlsx/discipline_progress_2026-08-14.xlsx`
- `input/progress-report-csv/daily_progress_2026-08-14.csv`
- `input/scanned-diary/site_diary_2026-08-14.png`

**Hard Rule Compliance**:
These files were preserved **byte-for-byte** without modification and backed up in `ignore/old-versions/golden_14aug_backup/`. All four reported activities (`CIV-PS3-TR-0180`, `PIP-PS3-WLD-024`, `ELE-PS3-CT-011`, and `MECH-PS3-DWP-003`) are canonically mapped and validated.

---

## 6. Pipeline Test Scenarios & Ground Truth Expectations

### A. Matching Benchmark (`test-cases/matching/` -> `expected/matching_results.json`)
1. **MATCH-001 (Exact ID Match)**:
   - Claim: `"PIP-PS3-WLD-024: Two field weld joints completed on utility header..."`
   - Expected: `PIP-PS3-WLD-024` | Confidence: `1.0` | `review_required: false`.
2. **MATCH-002 (Asset / Tag Match)**:
   - Claim: `"P-102 discharge line welding completed. Two field joints cleared by inspection team."` (No Activity ID provided).
   - Expected: `PIP-PS3-WLD-024` (via Asset Tag `P-102`) | Confidence: `0.92` | `review_required: false`.
3. **MATCH-003 (Semantic / Description Match)**:
   - Claim: `"Two field weld joints completed on utility header."` (No ID, no tag).
   - Expected: `PIP-PS3-WLD-024` | Confidence: `0.86` | `review_required: false`.
4. **MATCH-004 (Ambiguous Match)**:
   - Claim: `"Utility trench excavation from approximately CH 0+200 to CH 0+240 completed."`
   - Real Ambiguity: Spans both `CIV-PS3-TR-0180` (CH 0+180–0+220) and `CIV-PS3-TR-0220` (CH 0+220–0+260).
   - Expected: Status: `AMBIGUOUS` | Candidates: `["CIV-PS3-TR-0180", "CIV-PS3-TR-0220"]` | `review_required: true`.
5. **MATCH-005 (Unmatched Field Activity)**:
   - Claim: `"Temporary rain shelter installed at laydown area."`
   - Expected: Status: `UNMATCHED` | Confidence: `0.12` | `review_required: true`.

### B. Conflict Detection Benchmark (`test-cases/conflicts/` -> `expected/conflict_results.json`)
- **CONF-001**: Activity `PIP-PS3-WLD-024` on 14-Aug-2026:
  - Source A (`input/daily-report-txt/daily_progress_report_2026-08-14.txt`): 2 joints completed today (cumulative 22/24).
  - Source B (`test-cases/conflicts/conf_001_source_b_field_claim.json`): 3 joints completed today (cumulative 23/24).
  - Expected: `conflict: true` | Variance: 1 joint (4.17%) | Status: `OPEN` | `review_required: true`.

### C. Child-to-Parent Roll-up Benchmark (`test-cases/rollup/` -> `expected/rollup_results.json`)
- **ROLLUP-001**: Parent `PIP-PS3-HDR-100` (planned 100 m):
  - Child A (`PIP-PS3-HDR-100-A`): Planned 40 m.
  - Child B (`PIP-PS3-HDR-100-B`): Planned 30 m.
  - Child C (`PIP-PS3-HDR-100-C`): Planned 30 m.
  - Test Input: Field report for Child B reporting 18 m completed (60.0% of Child B).
  - Expected Roll-up: Parent completed = 18 m | Parent progress = 18.0% | Status: `VALIDATED`.

### D. Edge Cases Benchmark (`test-cases/edge-cases/`)
1. **EDGE-001 (Delayed Activity)**:
   - Activity: `ELE-PS3-CBL-001` (11kV MV Cable Pulling).
   - Planned finish: 18-Aug-2026. Reporting date: 20-Aug-2026. Cumulative progress: 60.0% (< 100%).
   - Expected: Status: `DELAYED` | Slippage: 2 days | `review_required: true`.
2. **EDGE-002 (No Progress Reported)**:
   - Activity: `INS-PS3-FGS-001` (Fire & Gas Detector Mounting).
   - Planned start: 18-Aug-2026. Zero field claims across all sources in the reporting period.
   - Expected: Status: `NO_PROGRESS_REPORTED` | `review_required: false`.
3. **EDGE-003 (Quantity Exceeds Plan / Anomaly)**:
   - Activity: `PIP-PS3-SPT-030` (Pipe Support Secondary Steel).
   - Planned baseline: 100 ea. Reported cumulative in 21-Aug CSV & diary: 108 ea (108.0%).
   - Expected: Status: `ANOMALY` | Excess: 8 ea (+8.0%) | `review_required: true`.
4. **EDGE-004 (Cross-Format Mismatch)**:
   - Activity: `ELE-PS3-TR-005` on 20-Aug-2026.
   - `input/progress-report-csv/daily_progress_2026-08-20.csv`: 120 m / 200 m (60.0%).
   - `input/discipline-report-xlsx/discipline_progress_2026-08-20.xlsx`: 140 m / 200 m (70.0%).
   - Expected: Status: `SOURCE_MISMATCH` | Variance: 10.0 percentage points | `review_required: true`.

---

## 7. Public Source Provenance & Synthetic Data Notice
- **Public Sources Consulted**:
  - Oracle Primavera P6 EPPM XER Import/Export Data Map Guide (tables: `PROJECT`, `PROJWBS`, `TASK`, `TASKPRED`).
  - Industry standard construction daily progress reporting schemas (CII / FIDIC).
  - OSHA 1926 & ISO 45001 safety metrics.
- **Reference File**:
  - `ignore/public-reference-files/sample_schedule_borouge4_reference.xer` is a reference file from a public demo (`BOROUGE4_DEMO`).
- **Synthetic Demonstration Data**:
  - All project records, activity descriptions, supervisor names, quantities, and claims are synthetic data created strictly for testing and demonstrating the SIH26122 system.
  - **No confidential OIL data was used or disclosed.**

---

## 8. Validation & Verification
All benchmark data can be automatically validated at any time using:
```bash
python D:\SIH26122\sample_data\ignore\generation-scripts\validate_dataset.py
```
This script asserts:
1. Exact canonical 45-activity count and 6-discipline distribution.
2. 100% byte-for-byte fidelity of the 14-Aug Golden Integration Case against original backup.
3. 100% referential integrity of Activity IDs and Asset Tags across all inputs.
4. Monotonicity of cumulative quantities over time (no regressions).
5. Exact mathematical roll-up calculation.
6. Deliberate detection of conflict, anomaly, mismatch, and delay edge cases.
