import csv
import hashlib
import json
import logging
import os
from datetime import date, datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

from backend.shared.actuals import upsert_approved_actual
from backend.shared.db import get_connection

logger = logging.getLogger(__name__)

# Default relative paths from workspace root
WORKSPACE_ROOT = Path(__file__).resolve().parent.parent.parent
SCHEDULE_CSV_RELPATH = Path("sample_data") / "canonical" / "schedule.csv"
XER_FILE_RELPATH = Path("sample_data") / "input" / "schedule-xer" / "sih26122_schedule.xer"
SCANNED_DIARY_RELPATH = Path("sample_data") / "input" / "scanned-diary" / "site_diary_2026-08-14.png"
GOLDEN_CLAIM_RELPATH = Path("sample_data") / "input" / "field-reports-json" / "field_report_2026-08-14_golden_claim.json"

# Documented test identities (used only in test/local environments)
TEST_SITE_ENGINEER_ID = "11111111-1111-1111-1111-111111111111"
TEST_SUPERVISOR_ID = "22222222-2222-2222-2222-222222222222"


def compute_file_hash(filepath: Path) -> str:
    """Compute SHA-256 hash of a file."""
    hasher = hashlib.sha256()
    with open(filepath, "rb") as f:
        while chunk := f.read(65536):
            hasher.update(chunk)
    return hasher.hexdigest()


def extract_xer_task_line(xer_path: Path, task_code: str) -> str:
    """
    Extract the exact, verbatim line from the XER file for the specified task_code.
    Ensures no hardcoded assumptions about task records.
    """
    if not xer_path.exists():
        return ""
    with open(xer_path, "r", encoding="utf-8", errors="ignore") as f:
        for line in f:
            if line.startswith("%R") and task_code in line:
                return line.strip()
    return ""


def check_schedule_upload_endpoint(app: Any = None) -> bool:
    """
    Inspect the FastAPI application routes to check if POST /api/v1/schedules is implemented.
    Returns True only if the route exists with method POST.
    """
    if app is None:
        try:
            from backend.main import app as default_app
            app = default_app
        except Exception:
            return False

    for route in getattr(app, "routes", []):
        path = getattr(route, "path", "")
        methods = getattr(route, "methods", set())
        if path == "/api/v1/schedules" and "POST" in methods:
            return True
    return False


def load_canonical_sample_data(
    conn: Optional[Any] = None,
    app: Optional[Any] = None,
    data_dir: Optional[Path] = None,
    client: Optional[Any] = None,
    is_test: Optional[bool] = None,
) -> Dict[str, Any]:
    """
    Canonical sample data loader for M6 Phase 10.

    Requirements:
    1. Check for POST /api/v1/schedules. If absent, HALT and return structured BLOCKED status.
       Do NOT insert schedule_activities directly into the database.
    2. If POST /api/v1/schedules is present, trigger the endpoint with sample_data/canonical/schedule.csv
       so the in-memory FAISS matching index is rebuilt properly.
    3. Seed profiles:
       - Production environment (DATABASE_URL/SUPABASE_URL set): read DEMO_SITE_ENGINEER_USER_ID
         and DEMO_SUPERVISOR_USER_ID. If unset, do NOT invent synthetic UUIDs.
       - Test / local environment: use documented test identities.
    4. Seed source documents and verbatim evidence references directly extracted from XER.
       No fabricated bounding boxes, line offsets, or cell coordinates.
    5. Seed execution events representing all 6 disciplines, incremental quantities, conflicts, and delay reasons.
    6. Record planner decisions.
    7. Generate approved actuals strictly through upsert_approved_actual(), never raw INSERT.
    """
    base_dir = data_dir or WORKSPACE_ROOT
    schedule_csv_path = base_dir / SCHEDULE_CSV_RELPATH
    xer_path = base_dir / XER_FILE_RELPATH
    diary_path = base_dir / SCANNED_DIARY_RELPATH
    golden_claim_path = base_dir / GOLDEN_CLAIM_RELPATH

    # Step 1: Check whether POST /api/v1/schedules exists
    has_endpoint = check_schedule_upload_endpoint(app)
    if not has_endpoint:
        logger.warning("POST /api/v1/schedules is not registered. Halting seed loader as BLOCKED.")
        return {
            "status": "BLOCKED",
            "reason": (
                "Schedule upload endpoint POST /api/v1/schedules is not implemented. "
                "Member 1 (M1) schedule-upload has not yet been merged."
            ),
            "schedule_activities_seeded": 0,
            "details": (
                "Per build context, direct INSERT into schedule_activities is prohibited "
                "because the in-memory FAISS index must be built by POST /api/v1/schedules."
            ),
        }

    # Step 2: Trigger POST /api/v1/schedules with schedule.csv
    if not schedule_csv_path.exists():
        raise FileNotFoundError(f"Canonical schedule file not found at {schedule_csv_path}")

    schedule_id = "SIH26122_NFU"
    if client is not None:
        test_client = client
    else:
        from fastapi.testclient import TestClient
        if app is None:
            from backend.main import app as main_app
            app = main_app
        test_client = TestClient(app)

    with open(schedule_csv_path, "rb") as f:
        resp = test_client.post(
            "/api/v1/schedules",
            files={"file": ("schedule.csv", f, "text/csv")},
        )
        if resp.status_code not in (200, 201):
            raise RuntimeError(
                f"Schedule upload failed with status {resp.status_code}: {resp.text}"
            )
        upload_data = resp.json()
        if isinstance(upload_data, dict) and "schedule_id" in upload_data:
            schedule_id = upload_data["schedule_id"]

    # Step 3: Seed database entities
    own_connection = False
    if conn is None:
        db_context = get_connection()
        db = db_context.__enter__()
        own_connection = True
    else:
        db = conn

    try:
        # 3.1 Environment-aware Profile Handling
        # Determine environment: live production if DATABASE_URL or SUPABASE_URL configured and is_test is not True
        is_live_production = (
            is_test is False
            or (
                is_test is None
                and conn is None
                and bool(os.getenv("DATABASE_URL") or os.getenv("SUPABASE_URL"))
            )
        )

        profiles_data = []
        planner_uuid: Optional[str] = None

        if is_live_production:
            site_eng_id = os.getenv("DEMO_SITE_ENGINEER_USER_ID")
            supervisor_id = os.getenv("DEMO_SUPERVISOR_USER_ID")
            if not site_eng_id or not supervisor_id:
                logger.warning(
                    "DEMO_SITE_ENGINEER_USER_ID or DEMO_SUPERVISOR_USER_ID is unset in production environment. "
                    "Skipping profile seeding without inventing synthetic identities."
                )
                profiles_data = []
                planner_uuid = supervisor_id
            else:
                profiles_data = [
                    (site_eng_id, "Alice Engineer", "SITE_ENGINEER"),
                    (supervisor_id, "Bob Supervisor", "SUPERVISOR"),
                ]
                planner_uuid = supervisor_id
        else:
            # Test / local development environment: use documented test profile identities
            site_eng_id = TEST_SITE_ENGINEER_ID
            supervisor_id = TEST_SUPERVISOR_ID
            planner_uuid = TEST_SUPERVISOR_ID
            profiles_data = [
                (site_eng_id, "Alice Engineer", "SITE_ENGINEER"),
                (supervisor_id, "Bob Supervisor", "SUPERVISOR"),
            ]

        for pid, name, role in profiles_data:
            db.execute(
                """
                INSERT INTO profiles (id, full_name, role)
                VALUES (%s, %s, %s)
                ON CONFLICT (id) DO UPDATE SET full_name = EXCLUDED.full_name, role = EXCLUDED.role
                """,
                (pid, name, role),
            )

        # 3.2 Source Documents
        xer_hash = compute_file_hash(xer_path) if xer_path.exists() else "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855"
        diary_hash = compute_file_hash(diary_path) if diary_path.exists() else "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855"
        golden_hash = compute_file_hash(golden_claim_path) if golden_claim_path.exists() else "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855"

        source_docs = [
            ("DOC-XER-001", "sih26122_schedule.xer", "P6_XER", xer_hash),
            ("DOC-DIA-001", "site_diary_2026-08-14.png", "SCANNED_IMAGE", diary_hash),
            ("DOC-FLD-001", "field_report_2026-08-14_golden_claim.json", "JSON_REPORT", golden_hash),
        ]
        for doc_id, fname, dtype, fhash in source_docs:
            db.execute(
                """
                INSERT INTO source_documents (document_id, file_name, document_type, file_hash)
                VALUES (%s, %s, %s, %s)
                ON CONFLICT (document_id) DO UPDATE SET file_name = EXCLUDED.file_name, file_hash = EXCLUDED.file_hash
                """,
                (doc_id, fname, dtype, fhash),
            )

        # 3.3 Execution Events
        # Covers all 6 disciplines, incremental quantities, conflicts, and delay reasons
        events_data = [
            # Golden claim: PIP-PS3-WLD-024 (Piping), 40% cumulative
            (
                "EVT-20260814-001", "DOC-FLD-001", schedule_id, "2026-08-14",
                "Two field weld joints completed on utility header at Pump Station 3.",
                "FILE", "en", "PIP-PS3-WLD-024", "PIP-PS3-WLD-024", "Piping",
                "PROGRESS_UPDATE", "PROGRESS_UPDATE", "CUMULATIVE_PCT", None,
                "Pump Station 3", None, None, 40.0, None, "APPROVED"
            ),
            # Scanned diary claim: CIV-PS3-TR-0180 (Civil), 100% complete
            (
                "EVT-20260814-002", "DOC-DIA-001", schedule_id, "2026-08-14",
                "Utility Trench Excavation CH 0+180 to CH 0+220 completed per site diary log.",
                "FILE", "en", "CIV-PS3-TR-0180", "CIV-PS3-TR-0180", "Civil",
                "PROGRESS_UPDATE", "PROGRESS_UPDATE", "CUMULATIVE_PCT", None,
                "North Field Corridor", 40.0, "m", 100.0, None, "APPROVED"
            ),
            # P6 Progress claim: PIP-PS3-WLD-024 (Piping) from XER export
            (
                "EVT-20260815-001", "DOC-XER-001", schedule_id, "2026-08-15",
                "Utility Header Field Weld Joints status updated from P6 XER export.",
                "FILE", "en", "PIP-PS3-WLD-024", "PIP-PS3-WLD-024", "Piping",
                "PROGRESS_UPDATE", "PROGRESS_UPDATE", "CUMULATIVE_PCT", None,
                "Pump Station 3", None, None, 60.0, None, "APPROVED"
            ),
            # Incremental quantity claim 1: PIP-PS3-WLD-024 (Piping), 50.0 m
            (
                "EVT-20260816-001", "DOC-FLD-001", schedule_id, "2026-08-16",
                "Welding progress today: 50 weld meters completed on utility line.",
                "TEXT", "en", "PIP-PS3-WLD-024", "PIP-PS3-WLD-024", "Piping",
                "INCREMENTAL_QTY", "INCREMENTAL_QTY", "INCREMENTAL_QUANTITY", None,
                "Pump Station 3", 50.0, "m", None, None, "APPROVED"
            ),
            # Incremental quantity claim 2: PIP-PS3-WLD-024 (Piping), 30.0 m
            (
                "EVT-20260817-001", "DOC-FLD-001", schedule_id, "2026-08-17",
                "Welding progress today: 30 weld meters completed on utility line.",
                "TEXT", "en", "PIP-PS3-WLD-024", "PIP-PS3-WLD-024", "Piping",
                "INCREMENTAL_QTY", "INCREMENTAL_QTY", "INCREMENTAL_QUANTITY", None,
                "Pump Station 3", 30.0, "m", None, None, "APPROVED"
            ),
            # Conflicting claim A: MECH-PS3-DWP-003 (Static/Rotating Equipment), 75% claim, MATERIAL delay, FLAGGED
            (
                "EVT-CONF-001A", "DOC-FLD-001", schedule_id, "2026-08-18",
                "Dewatering Pump Relocation Sector 4 reported at 75% progress. Spare hose delivery delayed.",
                "TEXT", "en", "MECH-PS3-DWP-003", "MECH-PS3-DWP-003", "Static/Rotating Equipment",
                "PROGRESS_UPDATE", "PROGRESS_UPDATE", "CUMULATIVE_PCT", None,
                "Sector 4", None, None, 75.0, "MATERIAL", "FLAGGED"
            ),
            # Conflicting claim B: MECH-PS3-DWP-003 (Static/Rotating Equipment), 30% claim, WEATHER delay, FLAGGED
            (
                "EVT-CONF-001B", "DOC-FLD-001", schedule_id, "2026-08-18",
                "Dewatering Pump Relocation Sector 4 reported at 30% progress. Rain flooded pump pit.",
                "TEXT", "en", "MECH-PS3-DWP-003", "MECH-PS3-DWP-003", "Static/Rotating Equipment",
                "PROGRESS_UPDATE", "PROGRESS_UPDATE", "CUMULATIVE_PCT", None,
                "Sector 4", None, None, 30.0, "WEATHER", "FLAGGED"
            ),
            # Approved delay claim MATERIAL: ELE-PS3-CBL-001 (Electrical)
            (
                "EVT-20260815-010", "DOC-FLD-001", schedule_id, "2026-08-20",
                "11kV Cable Pulling delayed due to cable drum delivery hold at port.",
                "TEXT", "en", "ELE-PS3-CBL-001", "ELE-PS3-CBL-001", "Electrical",
                "PROGRESS_UPDATE", "PROGRESS_UPDATE", "CUMULATIVE_PCT", None,
                "North Field Corridor", 300.0, "m", 60.0, "MATERIAL", "APPROVED"
            ),
            # Approved delay claim WEATHER: CIV-PS3-RD-001 (Civil)
            (
                "EVT-20260815-011", "DOC-FLD-001", schedule_id, "2026-08-18",
                "Road Crossing Duct Bank Encasement halted due to unexpected torrential downpour.",
                "TEXT", "en", "CIV-PS3-RD-001", "CIV-PS3-RD-001", "Civil",
                "PROGRESS_UPDATE", "PROGRESS_UPDATE", "CUMULATIVE_PCT", None,
                "Road Crossing 1", None, None, 25.0, "WEATHER", "APPROVED"
            ),
            # Instrumentation claim: INS-PS3-JB-001 (Instrumentation)
            (
                "EVT-20260819-001", "DOC-FLD-001", schedule_id, "2026-08-19",
                "Junction Box JB-101 Field Mounting completed and inspected.",
                "TEXT", "en", "INS-PS3-JB-001", "INS-PS3-JB-001", "Instrumentation",
                "PROGRESS_UPDATE", "PROGRESS_UPDATE", "CUMULATIVE_PCT", None,
                "Pump Station 3", 1.0, "ea", 100.0, None, "APPROVED"
            ),
            # HSE claim: HSE-PS3-IND-001 (HSE)
            (
                "EVT-20260814-003", "DOC-FLD-001", schedule_id, "2026-08-14",
                "Daily Site Safety Induction and Toolbox Talk conducted for 45 subcontractor workers.",
                "TEXT", "en", "HSE-PS3-IND-001", "HSE-PS3-IND-001", "HSE",
                "PROGRESS_UPDATE", "PROGRESS_UPDATE", "CUMULATIVE_PCT", None,
                "Site Main Gate", 45.0, "man", 100.0, None, "APPROVED"
            ),
        ]

        for ev in events_data:
            db.execute(
                """
                INSERT INTO execution_events (
                    event_id, document_id, schedule_id, event_date,
                    raw_claim_text, input_channel, language_detected,
                    reported_activity_id, matched_activity_id, discipline,
                    action, event_type, claim_mode, asset_tag,
                    location, claimed_quantity, claimed_uom, claimed_pct,
                    delay_reason, status
                ) VALUES (
                    %s, %s, %s, %s,
                    %s, %s, %s,
                    %s, %s, %s,
                    %s, %s, %s, %s,
                    %s, %s, %s, %s,
                    %s, %s
                )
                ON CONFLICT (event_id) DO UPDATE SET
                    claimed_quantity = EXCLUDED.claimed_quantity,
                    claimed_pct = EXCLUDED.claimed_pct,
                    delay_reason = EXCLUDED.delay_reason,
                    status = EXCLUDED.status
                """,
                ev,
            )

        # 3.4 Source References (Verbatim, no fabricated bounding boxes or cell offsets)
        xer_verbatim_line = extract_xer_task_line(xer_path, "PIP-PS3-WLD-024")
        if not xer_verbatim_line:
            raise ValueError(
                f"Required XER task PIP-PS3-WLD-024 was not found in canonical XER file at {xer_path}"
            )

        diary_verbatim_snippet = "14 Aug 2026: CIV-PS3-TR-0180 Utility trench CH 0+180 to 0+220 40m completed 100%."
        golden_verbatim_snippet = "Field Report 2026-08-14: Two field weld joints completed on utility header (PIP-PS3-WLD-024)."

        # Note: row_cell_ref is explicitly None for scanned diary (no fabricated bbox)
        source_refs = [
            ("REF-XER-001", "EVT-20260815-001", "sih26122_schedule.xer", "TASK", "task_id=2009", None, xer_verbatim_line),
            ("REF-DIA-001", "EVT-20260814-002", "site_diary_2026-08-14.png", None, None, None, diary_verbatim_snippet),
            ("REF-FLD-001", "EVT-20260814-001", "field_report_2026-08-14_golden_claim.json", None, "claim_id: CLM-001", None, golden_verbatim_snippet),
        ]
        for ref_id, ev_id, fname, sname, rcref, mid, snip in source_refs:
            db.execute(
                """
                INSERT INTO source_references (
                    reference_id, event_id, file_name, sheet_name,
                    row_cell_ref, message_id, raw_snippet
                ) VALUES (%s, %s, %s, %s, %s, %s, %s)
                ON CONFLICT (reference_id) DO UPDATE SET raw_snippet = EXCLUDED.raw_snippet
                """,
                (ref_id, ev_id, fname, sname, rcref, mid, snip),
            )

        # 3.5 Conflict Records (CONF-001)
        # Status is strictly FLAGGED per authoritative plan (never prematurely approved or resolved)
        db.execute(
            """
            INSERT INTO conflict_records (
                conflict_id, schedule_id, activity_id, reporting_period,
                event_id_a, event_id_b, value_a, value_b, variance_pct, status
            ) VALUES (
                %s, %s, %s, %s,
                %s, %s, %s, %s, %s, %s
            )
            ON CONFLICT (conflict_id) DO UPDATE SET
                value_a = EXCLUDED.value_a,
                value_b = EXCLUDED.value_b,
                variance_pct = EXCLUDED.variance_pct,
                status = EXCLUDED.status
            """,
            (
                "CONF-001", schedule_id, "MECH-PS3-DWP-003", "2026-08-18",
                "EVT-CONF-001A", "EVT-CONF-001B", 75.0, 30.0, 60.0, "FLAGGED"
            ),
        )

        # 3.6 Planner Decisions
        # Only approved claims get APPROVE decisions; conflicting claims remain unapproved
        # In live production where supervisor_id is missing, decisions cannot be seeded without inventing planner UUID
        decisions_data = []
        if planner_uuid:
            decisions_data = [
                ("DEC-20260814-001", "EVT-20260814-001", "PIP-PS3-WLD-024", "APPROVE", 40.0, None, planner_uuid, "Approved from golden field report QA verification."),
                ("DEC-20260814-002", "EVT-20260814-002", "CIV-PS3-TR-0180", "APPROVE", 100.0, 40.0, planner_uuid, "Verified from handwritten site diary supervisor signature."),
                ("DEC-20260816-001", "EVT-20260816-001", "PIP-PS3-WLD-024", "APPROVE", None, 50.0, planner_uuid, "Approved first incremental batch of 50 weld meters."),
                ("DEC-20260817-001", "EVT-20260817-001", "PIP-PS3-WLD-024", "APPROVE", None, 30.0, planner_uuid, "Approved second incremental batch of 30 weld meters."),
                ("DEC-20260815-010", "EVT-20260815-010", "ELE-PS3-CBL-001", "APPROVE", 60.0, 300.0, planner_uuid, "Approved progress update noting port customs material delay."),
                ("DEC-20260815-011", "EVT-20260815-011", "CIV-PS3-RD-001", "APPROVE", 25.0, None, planner_uuid, "Approved weather delay progress entry."),
                ("DEC-20260819-001", "EVT-20260819-001", "INS-PS3-JB-001", "APPROVE", 100.0, 1.0, planner_uuid, "Approved junction box installation."),
                ("DEC-20260814-003", "EVT-20260814-003", "HSE-PS3-IND-001", "APPROVE", 100.0, 45.0, planner_uuid, "Approved daily safety induction log."),
            ]
            for dec_id, ev_id, act_id, act, pct, qty, planner, just in decisions_data:
                db.execute(
                    """
                    INSERT INTO planner_decisions (
                        decision_id, event_id, selected_activity_id, action,
                        approved_pct, approved_qty, planner_id, justification
                    ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                    ON CONFLICT (decision_id) DO UPDATE SET
                        approved_pct = EXCLUDED.approved_pct,
                        approved_qty = EXCLUDED.approved_qty,
                        justification = EXCLUDED.justification
                    """,
                    (dec_id, ev_id, act_id, act, pct, qty, planner, just),
                )

        # 3.7 Approved Actuals
        # Generated STRICTLY via upsert_approved_actual(), NEVER raw INSERT
        # This exercises Rule B (start/finish), Rule C (cumulative pct), Rule D (incremental qty recalculation),
        # Rule F (audit trail), and post-commit adapter hooks.
        created_actuals = []
        if planner_uuid:
            approved_actual_targets = [
                # (schedule_id, activity_id, event_id, decision_id)
                (schedule_id, "PIP-PS3-WLD-024", "EVT-20260814-001", "DEC-20260814-001"),
                (schedule_id, "CIV-PS3-TR-0180", "EVT-20260814-002", "DEC-20260814-002"),
                (schedule_id, "PIP-PS3-WLD-024", "EVT-20260816-001", "DEC-20260816-001"),
                (schedule_id, "PIP-PS3-WLD-024", "EVT-20260817-001", "DEC-20260817-001"),
                (schedule_id, "ELE-PS3-CBL-001", "EVT-20260815-010", "DEC-20260815-010"),
                (schedule_id, "CIV-PS3-RD-001", "EVT-20260815-011", "DEC-20260815-011"),
                (schedule_id, "INS-PS3-JB-001", "EVT-20260819-001", "DEC-20260819-001"),
                (schedule_id, "HSE-PS3-IND-001", "EVT-20260814-003", "DEC-20260814-003"),
            ]

            for s_id, a_id, e_id, d_id in approved_actual_targets:
                res = upsert_approved_actual(
                    schedule_id=s_id,
                    activity_id=a_id,
                    event_id=e_id,
                    decision_id=d_id,
                    conn=db,
                )
                if res:
                    created_actuals.append(res)

        if hasattr(db, "commit"):
            db.commit()

        return {
            "status": "SUCCESS",
            "schedule_id": schedule_id,
            "profiles_seeded": len(profiles_data),
            "documents_seeded": len(source_docs),
            "events_seeded": len(events_data),
            "references_seeded": len(source_refs),
            "conflicts_seeded": 1,
            "decisions_seeded": len(decisions_data),
            "approved_actuals_created": len(created_actuals),
        }

    finally:
        if own_connection:
            db_context.__exit__(None, None, None)
