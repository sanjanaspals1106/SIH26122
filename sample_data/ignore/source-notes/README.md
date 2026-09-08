# SIH26122 Data Provenance & Methodology Notes

## 1. Project Context & Problem Statement
This benchmark dataset is created for the **SIH26122** problem statement: *Heterogeneous construction and project-progress data ingestion, normalization, activity matching, conflict detection, progress calculation, and parent/child roll-up*.

The dataset serves as an authoritative benchmark for validating the complete ingestion and analytical pipeline:
```text
Raw Sources (PDF, TXT, XLSX, CSV, Scanned Diary, JSON, XER)
    ↓
Extraction / OCR / Parsing
    ↓
Normalization
    ↓
Activity Matching (Exact ID, Asset/Tag, Semantic, Ambiguous, Unmatched)
    ↓
Confidence Scoring & Human Review Routing
    ↓
Conflict Detection
    ↓
Progress Calculation & Parent-Child Roll-up
    ↓
Final Project Status & Schedule Updates
```

---

## 2. Public Sources Consulted & Derived Conventions

Before generating any project-specific synthetic data, established public industry standards were researched and utilized strictly for **schemas, field nomenclature, terminology, and formatting conventions**:

1. **Oracle Primavera P6 EPPM XER Specifications**:
   - *Source*: Oracle Primavera P6 EPPM XER Import/Export Data Map Guide.
   - *Usage*: Derived the standard tab-delimited relational table structure (`%T PROJECT`, `%T PROJWBS`, `%T TASK`, `%T TASKPRED`, `%E`), column headers (`task_id`, `proj_id`, `wbs_id`, `task_code`, `task_name`, `status_code`, etc.), and relationship codes (`PR_FS`, `PR_SS`, `PR_FF`).
   - *Public Reference File*: `ignore/public-reference-files/sample_schedule_borouge4_reference.xer` is preserved exclusively as a reference P6 file from a public demo project (`BOROUGE4_DEMO`).

2. **Standard Construction Daily Progress Reporting (DPR) Formats**:
   - *Source*: Industry standard DPR and shift reporting templates (FIDIC / CII / PMI standards).
   - *Usage*: Standard multi-discipline breakdown, weather logging, manpower headcount, plant and equipment utilization, inspection hold points, quality evidence sign-offs, look-ahead plans.

3. **Discipline Categorization & Work Breakdown Structure (WBS)**:
   - Standard WBS hierarchy:
     1. Civil (`1.01`)
     2. Piping (`1.02`)
     3. Static/Rotating Equipment (`1.03`)
     4. Electrical (`1.04`)
     5. Instrumentation (`1.05`)
     6. Health, Safety & Environment (HSE) (`1.06`)

4. **Occupational Safety & Health (OSHA) & ISO 45001 Construction HSE Indicators**:
   - *Usage*: Standard metric definitions for daily toolbox talks, deep excavation barricading, confined space atmospheric multi-gas monitoring (LEL, O2, H2S, CO), and hazardous waste manifesting.

---

## 3. Strict Provenance & Synthetic Data Disclaimer

> **IMPORTANT DISCLAIMER**:
> Public sources were used exclusively for schema, terminology, table structures, and format conventions. All SIH26122 project-specific records (including activities, dates, quantities, supervisor notes, progress percentages, and test claims) are **synthetic demonstration data** created specifically for testing and benchmarking the SIH26122 application pipeline.
>
> **No confidential OIL data was accessed, utilized, or disclosed.**

---

## 4. File Classification Inventory

| Directory | Role in Pipeline | Provenance |
| :--- | :--- | :--- |
| `canonical/schedule.csv` | Single source of truth baseline schedule (45 activities) | SIH26122 Synthetic Ground Truth |
| `canonical/activity_master.csv` | Detailed activity attributes, roles, and hold points | SIH26122 Synthetic Lookup Master |
| `input/schedule-xer/sih26122_schedule.xer` | XER input representation resolving to canonical | Synthetic P6 export matching canonical |
| `input/daily-report-pdf/` | Machine-readable PDF DPRs (12, 14, 18, 21-Aug) | 14-Aug: Preserved Golden Case; 12, 18, 21: Synthetic |
| `input/daily-report-txt/` | Structured plain text DPRs (11, 13, 14, 15, 19, 21-Aug) | 14-Aug: Preserved Golden Case; Others: Synthetic |
| `input/discipline-report-xlsx/` | Multi-sheet Excel progress reports with formulas (14, 18, 20-Aug) | 14-Aug: Preserved Golden Case; 18, 20: Synthetic |
| `input/progress-report-csv/` | Tabular progress tracking sheets (11 to 22-Aug) | 14-Aug: Preserved Golden Case; Others: Synthetic |
| `input/scanned-diary/` | Scanned supervisor notebook pages (14, 21-Aug) | 14-Aug: Preserved Golden Case; 21-Aug: Synthetic |
| `input/field-reports-json/` | JSON field execution events (12, 14, 19, 22-Aug) | SIH26122 Synthetic Field Claims |
| `test-cases/` | Dedicated pipeline test payloads (matching, conflicts, rollup, edges) | SIH26122 Synthetic Test Suite |
| `expected/` | Ground truth expected JSON results for validation | SIH26122 Synthetic Benchmark Truth |
| `ignore/public-reference-files/` | `sample_schedule_borouge4_reference.xer` | Public demonstration reference XER |
| `ignore/old-versions/` | Superseded files & byte-for-byte backup of Golden 14-Aug set | Internal Archive |

---

## 5. Golden Integration Baseline (14-Aug-2026)
The files for **14-Aug-2026** across PDF, TXT, XLSX, CSV, and PNG diary represent the multi-source **Golden Integration Case**. They are preserved byte-for-byte from the initial dataset. All 4 activities in this golden set (`CIV-PS3-TR-0180`, `PIP-PS3-WLD-024`, `ELE-PS3-CT-011`, `MECH-PS3-DWP-003`) are canonically defined in `canonical/schedule.csv` with matching planned quantities, units, and baseline dates.
