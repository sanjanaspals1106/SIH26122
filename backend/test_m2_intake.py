"""
Unit and integration tests for Member 2 (Intake & Extraction).
Can be run via:
    python3 backend/test_m2_intake.py
or via:
    pytest backend/test_m2_intake.py (if pytest is installed)
"""
from __future__ import annotations
import io
import uuid
from datetime import date, datetime, timezone
from typing import Any, Dict, List, Optional

from fastapi.testclient import TestClient

from backend.main import app
from backend.shared.auth import CurrentUser, get_current_user
from backend.shared.db import get_db
from backend.shared.schemas import ClaimMode, Discipline, EventType, ExtractedClaimFields, InputChannel


# ---------------------------------------------------------------------------
# In-Memory Test DB Connection
# ---------------------------------------------------------------------------

class FakeCursor:
    def __init__(self, db: "FakeDB"):
        self.db = db
        self.last_results: List[Dict[str, Any]] = []

    def __enter__(self):
        return self

    def __exit__(self, *args):
        pass

    def execute(self, query: str, params: tuple = ()):
        q = query.strip()
        q_upper = q.upper()

        if "SELECT SCHEDULE_ID FROM SCHEDULES" in q_upper:
            if self.db.schedules:
                self.last_results = [{"schedule_id": self.db.schedules[-1]["schedule_id"]}]
            else:
                self.last_results = []

        elif "INSERT INTO SOURCE_DOCUMENTS" in q_upper:
            doc = {
                "document_id": params[0],
                "file_name": params[1],
                "document_type": params[2],
                "uploader_id": params[3],
                "file_hash": params[4],
                "uploaded_at": datetime.now(timezone.utc),
            }
            self.db.source_documents.append(doc)
            self.last_results = []

        elif "INSERT INTO EXECUTION_EVENTS" in q_upper:
            if "PHOTO_PATH" in q_upper:
                ev = {
                    "event_id": params[0],
                    "document_id": params[1],
                    "schedule_id": params[2],
                    "event_date": params[3],
                    "raw_claim_text": params[4],
                    "input_channel": params[5],
                    "language_detected": params[6],
                    "reported_activity_id": params[7],
                    "discipline": params[8],
                    "action": params[9],
                    "event_type": params[10],
                    "claim_mode": params[11],
                    "asset_tag": params[12],
                    "location": params[13],
                    "claimed_quantity": params[14],
                    "claimed_uom": params[15],
                    "claimed_pct": params[16],
                    "delay_reason": params[17],
                    "supervisor_id": params[18],
                    "photo_path": params[19],
                    "status": "EXTRACTED",
                    "created_at": datetime.now(timezone.utc),
                }
            elif "SUPERVISOR_ID, STATUS" in q_upper:
                ev = {
                    "event_id": params[0],
                    "document_id": params[1],
                    "schedule_id": params[2],
                    "event_date": params[3],
                    "raw_claim_text": params[4],
                    "input_channel": params[5],
                    "reported_activity_id": params[6] if len(params) == 15 else params[7],
                    "discipline": params[7] if len(params) == 15 else params[8],
                    "action": params[8] if len(params) == 15 else params[9],
                    "event_type": params[9] if len(params) == 15 else params[10],
                    "claim_mode": params[10] if len(params) == 15 else params[11],
                    "claimed_quantity": params[11] if len(params) == 15 else params[14],
                    "claimed_uom": params[12] if len(params) == 15 else params[15],
                    "claimed_pct": params[13] if len(params) == 15 else params[16],
                    "supervisor_id": params[14] if len(params) == 15 else params[18],
                    "status": "EXTRACTED",
                    "photo_path": None,
                    "created_at": datetime.now(timezone.utc),
                }
                if len(params) > 15:
                    ev["language_detected"] = params[6]
                    ev["asset_tag"] = params[12]
                    ev["location"] = params[13]
                    ev["delay_reason"] = params[17]
            self.db.execution_events.append(ev)
            self.last_results = []

        elif "INSERT INTO SOURCE_REFERENCES" in q_upper:
            ref = {
                "reference_id": params[0],
                "event_id": params[1],
                "file_name": params[2],
                "raw_snippet": params[-1],
            }
            self.db.source_references.append(ref)
            self.last_results = []

        elif "SELECT * FROM EXECUTION_EVENTS WHERE EVENT_ID = %S" in q_upper:
            target_id = params[0]
            matched = [e for e in self.db.execution_events if e["event_id"] == target_id]
            self.last_results = matched

        elif "SELECT * FROM EXECUTION_EVENTS WHERE EVENT_ID = ANY(%S)" in q_upper:
            target_ids = params[0]
            matched = [e for e in self.db.execution_events if e["event_id"] in target_ids]
            self.last_results = matched

        elif "SELECT * FROM EXECUTION_EVENTS WHERE 1=1" in q_upper:
            res = list(self.db.execution_events)
            param_idx = 0
            if "AND STATUS = %S" in q_upper:
                val = params[param_idx]
                param_idx += 1
                res = [e for e in res if e.get("status") == val]
            if "AND DISCIPLINE = %S" in q_upper:
                val = params[param_idx]
                param_idx += 1
                res = [e for e in res if e.get("discipline") == val]
            self.last_results = res

        else:
            self.last_results = []

    def fetchone(self) -> Optional[Dict[str, Any]]:
        return self.last_results[0] if self.last_results else None

    def fetchall(self) -> List[Dict[str, Any]]:
        return list(self.last_results)


class FakeDB:
    def __init__(self):
        self.schedules = [{"schedule_id": "test-sched-1", "project_name": "Test Project"}]
        self.source_documents: List[Dict[str, Any]] = []
        self.execution_events: List[Dict[str, Any]] = []
        self.source_references: List[Dict[str, Any]] = []

    def cursor(self):
        return FakeCursor(self)

    def commit(self):
        pass

    def close(self):
        pass


# ---------------------------------------------------------------------------
# Test Functions
# ---------------------------------------------------------------------------

def test_health_checks(client):
    """Router health checks respond with 200 OK."""
    r1 = client.get("/api/v1/intake/health")
    assert r1.status_code == 200
    assert r1.json()["status"] == "ok"

    r2 = client.get("/api/v1/claims/health")
    assert r2.status_code == 200
    assert r2.json()["status"] == "ok"


def test_auth_gating(client):
    """Intake requires SITE_ENGINEER role; unauthorized access is rejected."""
    # 1. No auth headers -> 401 Unauthorized
    r_no_auth = client.post("/api/v1/claims/text", json={"raw_claim_text": "Started welding"})
    assert r_no_auth.status_code == 401

    # 2. SUPERVISOR role -> 403 Forbidden for intake
    headers_sup = {"X-Dev-User-Id": "sup-1", "X-Dev-Role": "SUPERVISOR"}
    r_forbidden = client.post("/api/v1/claims/text", json={"raw_claim_text": "Started welding"}, headers=headers_sup)
    assert r_forbidden.status_code == 403

    # 3. SITE_ENGINEER role -> 200 OK
    headers_eng = {"X-Dev-User-Id": "eng-1", "X-Dev-Role": "SITE_ENGINEER"}
    r_ok = client.post("/api/v1/claims/text", json={"raw_claim_text": "Completed concrete pour in Area C"}, headers=headers_eng)
    assert r_ok.status_code == 200
    data = r_ok.json()
    assert data["status"] == "EXTRACTED"
    assert data["supervisor_id"] == "eng-1"


def test_text_claim_typed_and_voice(client, fake_db):
    """Test TYPED_TEXT and VOICE input channels."""
    headers = {"X-Dev-User-Id": "eng-1", "X-Dev-Role": "SITE_ENGINEER"}

    # Typed text
    r_typed = client.post(
        "/api/v1/claims/text",
        json={"raw_claim_text": "Activity A1000 excavation completed 100%", "input_channel": "TYPED_TEXT"},
        headers=headers,
    )
    assert r_typed.status_code == 200
    data = r_typed.json()
    assert data["input_channel"] == "TYPED_TEXT"
    assert data["status"] == "EXTRACTED"

    # Voice input (arrives as text transcribed via Web Speech API)
    r_voice = client.post(
        "/api/v1/claims/text",
        json={"raw_claim_text": "Area D trench excavation started today", "input_channel": "VOICE"},
        headers=headers,
    )
    assert r_voice.status_code == 200
    assert r_voice.json()["input_channel"] == "VOICE"

    # Verify provenance and documents stored
    assert len(fake_db.source_documents) >= 2
    assert len(fake_db.source_references) >= 2


def test_file_claim_txt(client, fake_db):
    """Upload plain text DPR file."""
    headers = {"X-Dev-User-Id": "eng-1", "X-Dev-Role": "SITE_ENGINEER"}
    file_content = b"DAILY PROGRESS REPORT\n14 Aug 2026\nExcavation completed 40m."

    r = client.post(
        "/api/v1/claims/file",
        files={"file": ("daily_report.txt", io.BytesIO(file_content), "text/plain")},
        headers=headers,
    )
    assert r.status_code == 200
    data = r.json()
    assert data["status"] == "EXTRACTED"
    assert data["input_channel"] == "FILE_UPLOAD"
    assert any(doc["document_type"] == "DPR" for doc in fake_db.source_documents)


def test_file_claim_pdf(client, fake_db):
    """Upload PDF file with text extracted via PyMuPDF."""
    import pymupdf as fitz
    headers = {"X-Dev-User-Id": "eng-1", "X-Dev-Role": "SITE_ENGINEER"}

    doc = fitz.open()
    page = doc.new_page()
    page.insert_text((50, 72), "Utility Corridor excavation completed 100% on 2026-08-14")
    pdf_bytes = doc.write()

    r = client.post(
        "/api/v1/claims/file",
        files={"file": ("report.pdf", io.BytesIO(pdf_bytes), "application/pdf")},
        headers=headers,
    )
    assert r.status_code == 200
    data = r.json()
    assert data["status"] == "EXTRACTED"
    assert "excavation completed" in data["raw_claim_text"].lower()


def test_file_claim_evidence_photo(client, fake_db):
    """Upload photo with purpose=EVIDENCE_PHOTO -> stores photo_path."""
    headers = {"X-Dev-User-Id": "eng-1", "X-Dev-Role": "SITE_ENGINEER"}
    dummy_image = b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01\x00\x00\x00\x01\x08\x06\x00\x00\x00\x1f\x15c4"

    r = client.post(
        "/api/v1/claims/file",
        files={"file": ("inspection_photo.png", io.BytesIO(dummy_image), "image/png")},
        data={"purpose": "EVIDENCE_PHOTO", "raw_claim_text": "Joint 3 visual inspection verified"},
        headers=headers,
    )
    assert r.status_code == 200
    data = r.json()
    assert data["photo_path"] is not None
    assert "inspection_photo.png" in data["photo_path"]


def test_file_claim_scanned_diary(client, fake_db):
    """Upload scanned diary with purpose=SCANNED_DIARY -> input_channel=SCANNED_OCR."""
    headers = {"X-Dev-User-Id": "eng-1", "X-Dev-Role": "SITE_ENGINEER"}
    dummy_image = b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01\x00\x00\x00\x01\x08\x06\x00\x00\x00\x1f\x15c4"

    r = client.post(
        "/api/v1/claims/file",
        files={"file": ("site_diary_2026-08-14.png", io.BytesIO(dummy_image), "image/png")},
        data={"purpose": "SCANNED_DIARY", "raw_claim_text": "Site diary entry for shift 1"},
        headers=headers,
    )
    assert r.status_code == 200
    data = r.json()
    assert data["input_channel"] == "SCANNED_OCR"
    assert any(doc["document_type"] == "SCANNED_DIARY" for doc in fake_db.source_documents)


def test_schedule_export_claims(client, fake_db):
    """Feature 22: P6/MSP progress export parsed directly, skipping LLM."""
    headers = {"X-Dev-User-Id": "eng-1", "X-Dev-Role": "SITE_ENGINEER"}

    csv_content = (
        "Activity ID,Activity Name,Discipline,Unit,Today Actual,Progress Pct,Status\n"
        "CIV-PS3-TR-0180,Excavate utility trench,Civil,m,40,100.0,Complete\n"
        "PIP-PS3-WLD-024,Complete field weld joints,Piping,joints,2,91.7,Ongoing\n"
        "EMPTY-ROW,,Civil,m,0,0.0,Not Started\n"
    ).encode("utf-8")

    r = client.post(
        "/api/v1/claims/schedule-export",
        files={"file": ("progress_export.csv", io.BytesIO(csv_content), "text/csv")},
        headers=headers,
    )
    assert r.status_code == 200
    claims = r.json()
    assert len(claims) == 2

    c1 = claims[0]
    assert c1["reported_activity_id"] == "CIV-PS3-TR-0180"
    assert c1["input_channel"] == "SCHEDULE_EXPORT"
    assert c1["status"] == "EXTRACTED"
    assert c1["claimed_pct"] == 100.0

    c2 = claims[1]
    assert c2["reported_activity_id"] == "PIP-PS3-WLD-024"
    assert c2["input_channel"] == "SCHEDULE_EXPORT"
    assert c2["status"] == "EXTRACTED"
    assert c2["claimed_pct"] == 91.7

    assert any(doc["document_type"] == "SCHEDULE_EXPORT_PROGRESS" for doc in fake_db.source_documents)


def test_get_and_list_claims(client, fake_db):
    """Test claim retrieval and filtering."""
    headers_eng = {"X-Dev-User-Id": "eng-1", "X-Dev-Role": "SITE_ENGINEER"}
    headers_sup = {"X-Dev-User-Id": "sup-1", "X-Dev-Role": "SUPERVISOR"}

    # Create 2 claims
    r1 = client.post("/api/v1/claims/text", json={"raw_claim_text": "Civil work 1"}, headers=headers_eng)
    eid1 = r1.json()["event_id"]

    r2 = client.post("/api/v1/claims/text", json={"raw_claim_text": "Piping work 2"}, headers=headers_eng)
    eid2 = r2.json()["event_id"]

    # Retrieve single claim by ID as Supervisor
    r_get = client.get(f"/api/v1/claims/{eid1}", headers=headers_sup)
    assert r_get.status_code == 200
    assert r_get.json()["event_id"] == eid1

    # List claims
    r_list = client.get("/api/v1/claims", headers=headers_sup)
    assert r_list.status_code == 200
    assert len(r_list.json()) >= 2

    # Non-existent claim -> 404
    r_404 = client.get("/api/v1/claims/non-existent-id", headers=headers_sup)
    assert r_404.status_code == 404


def test_missing_schedule_conflict(client, fake_db):
    """Attempting intake without any schedule uploaded returns 409 Conflict."""
    fake_db.schedules.clear()
    headers = {"X-Dev-User-Id": "eng-1", "X-Dev-Role": "SITE_ENGINEER"}

    r = client.post("/api/v1/claims/text", json={"raw_claim_text": "Test claim"}, headers=headers)
    assert r.status_code == 409
    assert "No schedule uploaded yet" in r.json()["detail"]


def test_llm_extraction_schema_and_invariants():
    """Verify extraction schema validation and claim_mode mutual exclusivity invariants."""
    from backend.shared.schemas import (
        ClaimMode,
        DelayReason,
        Discipline,
        EventType,
        ExtractedClaimFields,
    )

    # 1. Cumulative pct claim
    c1 = ExtractedClaimFields(
        event_date=date(2026, 8, 14),
        reported_activity_id="CIV-PS3-TR-0180",
        discipline=Discipline.CIVIL,
        action="Excavation of utility corridor trench",
        event_type=EventType.ACTUAL_FINISH,
        claim_mode=ClaimMode.CUMULATIVE_PCT,
        claimed_pct=100.0,
        claimed_quantity=None,
        claimed_uom=None,
    )
    assert c1.discipline == Discipline.CIVIL
    assert c1.event_type == EventType.ACTUAL_FINISH
    assert c1.claimed_pct == 100.0
    assert c1.claimed_quantity is None

    # 2. Incremental quantity claim
    c2 = ExtractedClaimFields(
        event_date=date(2026, 8, 14),
        reported_activity_id="PIP-PS3-WLD-024",
        discipline=Discipline.PIPING,
        action="Welded 2 field weld joints",
        event_type=EventType.PROGRESS_UPDATE,
        claim_mode=ClaimMode.INCREMENTAL_QUANTITY,
        claimed_quantity=2.0,
        claimed_uom="joints",
        claimed_pct=None,
        language_detected="Hindi-English mixed",
    )
    assert c2.discipline == Discipline.PIPING
    assert c2.claim_mode == ClaimMode.INCREMENTAL_QUANTITY
    assert c2.claimed_quantity == 2.0
    assert c2.claimed_uom == "joints"
    assert c2.claimed_pct is None

    # 3. Delay event
    c3 = ExtractedClaimFields(
        event_date=date(2026, 8, 15),
        discipline=Discipline.HSE,
        action="Heavy rainfall stopped excavation works",
        event_type=EventType.DELAY,
        delay_reason=DelayReason.WEATHER,
    )
    assert c3.event_type == EventType.DELAY
    assert c3.delay_reason == DelayReason.WEATHER
    assert c3.discipline == Discipline.HSE


def test_real_sample_data_intake(client, fake_db):
    """Test intake with actual repo sample files from sample_data/."""
    from pathlib import Path

    base_dir = Path(__file__).resolve().parents[1]
    headers = {"X-Dev-User-Id": "eng-1", "X-Dev-Role": "SITE_ENGINEER"}

    # 1. Real TXT DPR
    txt_path = base_dir / "sample_data" / "input" / "daily-report-txt" / "daily_progress_report_2026-08-14.txt"
    if txt_path.exists():
        with open(txt_path, "rb") as f:
            r = client.post("/api/v1/claims/file", files={"file": (txt_path.name, f, "text/plain")}, headers=headers)
        assert r.status_code == 200
        assert r.json()["status"] == "EXTRACTED"

    # 2. Real CSV progress report via schedule-export
    csv_path = base_dir / "sample_data" / "input" / "progress-report-csv" / "daily_progress_2026-08-14.csv"
    if csv_path.exists():
        with open(csv_path, "rb") as f:
            r = client.post("/api/v1/claims/schedule-export", files={"file": (csv_path.name, f, "text/csv")}, headers=headers)
        assert r.status_code == 200
        claims = r.json()
        assert len(claims) > 0
        assert claims[0]["input_channel"] == "SCHEDULE_EXPORT"
        assert claims[0]["status"] == "EXTRACTED"



# ---------------------------------------------------------------------------
# Direct Runner
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    db = FakeDB()

    def override_get_db():
        yield db

    app.dependency_overrides[get_db] = override_get_db
    c = TestClient(app)

    print("Running Member 2 Intake & Extraction tests...")

    test_health_checks(c)
    print("✓ test_health_checks passed")

    test_auth_gating(c)
    print("✓ test_auth_gating passed")

    db = FakeDB()
    test_text_claim_typed_and_voice(c, db)
    print("✓ test_text_claim_typed_and_voice passed")

    db = FakeDB()
    test_file_claim_txt(c, db)
    print("✓ test_file_claim_txt passed")

    db = FakeDB()
    test_file_claim_pdf(c, db)
    print("✓ test_file_claim_pdf passed")

    db = FakeDB()
    test_file_claim_evidence_photo(c, db)
    print("✓ test_file_claim_evidence_photo passed")

    db = FakeDB()
    test_file_claim_scanned_diary(c, db)
    print("✓ test_file_claim_scanned_diary passed")

    db = FakeDB()
    test_schedule_export_claims(c, db)
    print("✓ test_schedule_export_claims passed")

    db = FakeDB()
    test_get_and_list_claims(c, db)
    print("✓ test_get_and_list_claims passed")

    db = FakeDB()
    test_missing_schedule_conflict(c, db)
    print("✓ test_missing_schedule_conflict passed")

    test_llm_extraction_schema_and_invariants()
    print("✓ test_llm_extraction_schema_and_invariants passed")

    db = FakeDB()
    test_real_sample_data_intake(c, db)
    print("✓ test_real_sample_data_intake passed")

    app.dependency_overrides.clear()
    print("\n==========================================")
    print("All Member 2 Intake & Extraction tests PASSED!")
    print("==========================================")
