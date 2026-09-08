"""
Owner: M2. Others: read-only.
Features owned:
  #2 Multi-format claim ingestion
  #3 LLM extraction
  #4 Conversational typed intake (backend)
  #5 Voice input (backend)
  #6 Multi-language support
  #21 Scanned diary / OCR ingestion
  #22 Schedule-export claims (parsing half)
  #23 Start/finish event capture (extraction schema half)

Endpoints:
  - GET  /api/v1/intake/health
  - GET  /api/v1/claims/health
  - POST /api/v1/claims/text
  - POST /api/v1/claims/file
  - POST /api/v1/claims/schedule-export
  - GET  /api/v1/claims/{event_id}
  - GET  /api/v1/claims
"""
from __future__ import annotations
import hashlib
import io
import os
import uuid
from datetime import date, datetime
from pathlib import Path
from typing import Optional

from fastapi import APIRouter, Depends, File, Form, HTTPException, Query, UploadFile

from backend.shared.auth import CurrentUser, require_role
from backend.shared.db import get_db
from backend.shared.llm_extraction import extract_claim_fields
from backend.shared.schemas import (
    ClaimMode,
    ClaimResponse,
    EventType,
    InputChannel,
    TextClaimRequest,
    UploadPurpose,
)

router = APIRouter(prefix="/api/v1", tags=["intake"])

UPLOAD_DIR = Path(__file__).resolve().parents[2] / "uploads"
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)


@router.get("/intake/health")
def health():
    return {"router": "intake", "status": "ok"}


@router.get("/claims/health")
def claims_health():
    return {"router": "claims", "status": "ok"}


def _get_active_schedule_id(conn) -> Optional[str]:
    with conn.cursor() as cur:
        cur.execute("SELECT schedule_id FROM schedules ORDER BY created_at DESC LIMIT 1")
        row = cur.fetchone()
    return row["schedule_id"] if row else None


def _row_to_claim_response(row) -> ClaimResponse:
    return ClaimResponse(
        event_id=row["event_id"],
        document_id=row["document_id"],
        schedule_id=row["schedule_id"],
        event_date=row["event_date"],
        raw_claim_text=row["raw_claim_text"],
        input_channel=InputChannel(row["input_channel"]),
        language_detected=row.get("language_detected"),
        reported_activity_id=row.get("reported_activity_id"),
        matched_activity_id=row.get("matched_activity_id"),
        discipline=row.get("discipline"),
        action=row.get("action"),
        event_type=row.get("event_type"),
        claim_mode=row.get("claim_mode", "CUMULATIVE_PCT"),
        asset_tag=row.get("asset_tag"),
        location=row.get("location"),
        claimed_quantity=row.get("claimed_quantity"),
        claimed_uom=row.get("claimed_uom"),
        claimed_pct=row.get("claimed_pct"),
        delay_reason=row.get("delay_reason"),
        supervisor_id=str(row["supervisor_id"]) if row.get("supervisor_id") else None,
        photo_path=row.get("photo_path"),
        status=row.get("status", "EXTRACTED"),
        created_at=row["created_at"],
    )


# ---------------------------------------------------------------------------
# Feature 4 & 5: Typed and Voice Intake
# ---------------------------------------------------------------------------

@router.post("/claims/text", response_model=ClaimResponse)
def create_text_claim(
    payload: TextClaimRequest,
    conn=Depends(get_db),
    current_user: CurrentUser = Depends(require_role("SITE_ENGINEER")),
):
    """
    Handles typed text and voice input (transcribed client-side via Web Speech API).
    """
    schedule_id = payload.schedule_id or _get_active_schedule_id(conn)
    if not schedule_id:
        raise HTTPException(
            status_code=409,
            detail="No schedule uploaded yet — a schedule must exist before claims can be created.",
        )

    # 1. Store source document record for raw text
    text_hash = hashlib.sha256(payload.raw_claim_text.encode("utf-8")).hexdigest()
    document_id = str(uuid.uuid4())

    with conn.cursor() as cur:
        cur.execute(
            """INSERT INTO source_documents (document_id, file_name, document_type, uploader_id, file_hash)
               VALUES (%s, %s, %s, %s, %s)""",
            (document_id, f"[{payload.input_channel.value}]", "CHAT_LOG", current_user.id, text_hash),
        )

        # 2. Run LLM extraction
        extracted = extract_claim_fields(payload.raw_claim_text)

        # 3. Create execution event with status EXTRACTED
        event_id = str(uuid.uuid4())
        event_date = extracted.event_date or date.today()

        cur.execute(
            """INSERT INTO execution_events (
                event_id, document_id, schedule_id, event_date, raw_claim_text,
                input_channel, language_detected, reported_activity_id, discipline,
                action, event_type, claim_mode, asset_tag, location,
                claimed_quantity, claimed_uom, claimed_pct, delay_reason,
                supervisor_id, status
            ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, 'EXTRACTED')""",
            (
                event_id, document_id, schedule_id, event_date, payload.raw_claim_text,
                payload.input_channel.value, extracted.language_detected, extracted.reported_activity_id,
                extracted.discipline.value if extracted.discipline else None,
                extracted.action, extracted.event_type.value if extracted.event_type else None,
                extracted.claim_mode.value, extracted.asset_tag, extracted.location,
                extracted.claimed_quantity, extracted.claimed_uom, extracted.claimed_pct,
                extracted.delay_reason.value if extracted.delay_reason else None,
                current_user.id,
            ),
        )

        # 4. Record source provenance
        reference_id = str(uuid.uuid4())
        cur.execute(
            """INSERT INTO source_references (
                reference_id, event_id, file_name, raw_snippet
            ) VALUES (%s, %s, %s, %s)""",
            (reference_id, event_id, f"[{payload.input_channel.value}]", payload.raw_claim_text[:500]),
        )

        conn.commit()

        cur.execute("SELECT * FROM execution_events WHERE event_id = %s", (event_id,))
        row = cur.fetchone()

    return _row_to_claim_response(row)


# ---------------------------------------------------------------------------
# Feature 2 & 21: Multi-Format File Intake & Scanned Diary OCR
# ---------------------------------------------------------------------------

@router.post("/claims/file", response_model=ClaimResponse)
def create_file_claim(
    file: UploadFile = File(...),
    raw_claim_text: Optional[str] = Form(None),
    purpose: UploadPurpose = Form(UploadPurpose.EVIDENCE_PHOTO),
    schedule_id: Optional[str] = Form(None),
    conn=Depends(get_db),
    current_user: CurrentUser = Depends(require_role("SITE_ENGINEER")),
):
    """
    Accepts PDF, XLSX, CSV, TXT, or images (evidence photo or scanned diary).
    - purpose=EVIDENCE_PHOTO (default): Proof attached to a claim -> saved to photo_path.
    - purpose=SCANNED_DIARY: Image is the diary entry -> OCR extracts text, feeds LLM.
    """
    active_schedule_id = schedule_id or _get_active_schedule_id(conn)
    if not active_schedule_id:
        raise HTTPException(
            status_code=409,
            detail="No schedule uploaded yet — a schedule must exist before claims can be created.",
        )

    file_bytes = file.file.read()
    file_hash = hashlib.sha256(file_bytes).hexdigest()
    document_id = str(uuid.uuid4())
    saved_filename = f"{document_id}_{file.filename}"
    file_path = UPLOAD_DIR / saved_filename
    file_path.write_bytes(file_bytes)

    lower_name = (file.filename or "").lower()
    input_channel = InputChannel.FILE_UPLOAD
    photo_path: Optional[str] = None
    extracted_text = ""
    document_type = "DPR"

    # Scanned Diary OCR path (Feature 21)
    if purpose == UploadPurpose.SCANNED_DIARY:
        document_type = "SCANNED_DIARY"
        input_channel = InputChannel.SCANNED_OCR
        try:
            import pytesseract
            from PIL import Image

            if lower_name.endswith(".pdf"):
                import pymupdf as fitz
                pdf_doc = fitz.open(stream=file_bytes, filetype="pdf")
                ocr_pages = []
                for page in pdf_doc:
                    pix = page.get_pixmap()
                    img = Image.open(io.BytesIO(pix.tobytes()))
                    ocr_pages.append(pytesseract.image_to_string(img))
                extracted_text = "\n".join(ocr_pages).strip()
            else:
                img = Image.open(io.BytesIO(file_bytes))
                extracted_text = pytesseract.image_to_string(img).strip()
        except Exception as e:
            print(f"[intake] OCR processing note: {e}")
            extracted_text = raw_claim_text or f"Scanned diary record from {file.filename}"

        final_claim_text = extracted_text or raw_claim_text or f"Scanned diary from {file.filename}"

    # Evidence photo or standard document file path (Feature 2)
    else:
        is_image = any(lower_name.endswith(ext) for ext in (".png", ".jpg", ".jpeg", ".bmp", ".webp"))
        if is_image:
            photo_path = str(file_path)
            document_type = "QC_INSPECTION"
            final_claim_text = raw_claim_text or f"Photo evidence submitted: {file.filename}"
        elif lower_name.endswith(".pdf"):
            import pymupdf as fitz
            doc = fitz.open(stream=file_bytes, filetype="pdf")
            extracted_text = "\n".join(page.get_text() for page in doc).strip()
            document_type = "DPR"
            final_claim_text = f"{raw_claim_text}\n\n{extracted_text}".strip() if raw_claim_text else extracted_text
        elif lower_name.endswith((".xlsx", ".xls")):
            import pandas as pd
            df = pd.read_excel(io.BytesIO(file_bytes))
            extracted_text = df.to_string()
            document_type = "MBOOK"
            final_claim_text = f"{raw_claim_text}\n\n{extracted_text}".strip() if raw_claim_text else extracted_text
        elif lower_name.endswith(".csv"):
            import pandas as pd
            df = pd.read_csv(io.BytesIO(file_bytes))
            extracted_text = df.to_string()
            document_type = "DPR"
            final_claim_text = f"{raw_claim_text}\n\n{extracted_text}".strip() if raw_claim_text else extracted_text
        else:
            # Plain text or generic document
            extracted_text = file_bytes.decode("utf-8", errors="replace").strip()
            document_type = "DPR"
            final_claim_text = f"{raw_claim_text}\n\n{extracted_text}".strip() if raw_claim_text else extracted_text

    if not final_claim_text:
        final_claim_text = f"Field claim uploaded from {file.filename}"

    with conn.cursor() as cur:
        # 1. Insert source_documents
        cur.execute(
            """INSERT INTO source_documents (document_id, file_name, document_type, uploader_id, file_hash)
               VALUES (%s, %s, %s, %s, %s)""",
            (document_id, file.filename, document_type, current_user.id, file_hash),
        )

        # 2. Run LLM extraction
        extracted = extract_claim_fields(final_claim_text)

        # 3. Create execution event
        event_id = str(uuid.uuid4())
        event_date = extracted.event_date or date.today()

        cur.execute(
            """INSERT INTO execution_events (
                event_id, document_id, schedule_id, event_date, raw_claim_text,
                input_channel, language_detected, reported_activity_id, discipline,
                action, event_type, claim_mode, asset_tag, location,
                claimed_quantity, claimed_uom, claimed_pct, delay_reason,
                supervisor_id, photo_path, status
            ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, 'EXTRACTED')""",
            (
                event_id, document_id, active_schedule_id, event_date, final_claim_text,
                input_channel.value, extracted.language_detected, extracted.reported_activity_id,
                extracted.discipline.value if extracted.discipline else None,
                extracted.action, extracted.event_type.value if extracted.event_type else None,
                extracted.claim_mode.value, extracted.asset_tag, extracted.location,
                extracted.claimed_quantity, extracted.claimed_uom, extracted.claimed_pct,
                extracted.delay_reason.value if extracted.delay_reason else None,
                current_user.id, photo_path,
            ),
        )

        # 4. Insert source_references
        reference_id = str(uuid.uuid4())
        cur.execute(
            """INSERT INTO source_references (
                reference_id, event_id, file_name, raw_snippet
            ) VALUES (%s, %s, %s, %s)""",
            (reference_id, event_id, file.filename, final_claim_text[:500]),
        )

        conn.commit()

        cur.execute("SELECT * FROM execution_events WHERE event_id = %s", (event_id,))
        row = cur.fetchone()

    return _row_to_claim_response(row)


# ---------------------------------------------------------------------------
# Feature 22: P6/MSP Progress Export Ingestion (Direct Matching, Skips LLM)
# ---------------------------------------------------------------------------

@router.post("/claims/schedule-export", response_model=list[ClaimResponse])
def create_schedule_export_claims(
    file: UploadFile = File(...),
    schedule_id: Optional[str] = Form(None),
    conn=Depends(get_db),
    current_user: CurrentUser = Depends(require_role("SITE_ENGINEER")),
):
    """
    Ingests subcontractor P6/MSP progress export files.
    Extracts structured rows directly with reported_activity_id and skips LLM extraction.
    Status is created as EXTRACTED.
    """
    active_schedule_id = schedule_id or _get_active_schedule_id(conn)
    if not active_schedule_id:
        raise HTTPException(
            status_code=409,
            detail="No schedule uploaded yet — a schedule must exist before claims can be created.",
        )

    file_bytes = file.file.read()
    file_hash = hashlib.sha256(file_bytes).hexdigest()
    document_id = str(uuid.uuid4())
    saved_filename = f"{document_id}_{file.filename}"
    file_path = UPLOAD_DIR / saved_filename
    file_path.write_bytes(file_bytes)

    # Parse spreadsheet or CSV
    import pandas as pd
    lower_name = (file.filename or "").lower()
    if lower_name.endswith((".xlsx", ".xls")):
        df = pd.read_excel(io.BytesIO(file_bytes))
    else:
        df = pd.read_csv(io.BytesIO(file_bytes))

    # Standardize column lookups
    col_map = {str(c).strip().lower(): c for c in df.columns}

    def _find_col(*candidates: str) -> Optional[str]:
        for cand in candidates:
            c_low = cand.lower()
            if c_low in col_map:
                return col_map[c_low]
        return None

    col_activity_id = _find_col("activity id", "l6 task id", "task id", "activity_id", "id")
    col_wbs = _find_col("wbs", "l5 activity id", "wbs code", "wbs_code")
    col_name = _find_col("activity", "activity name", "activity_name", "work description", "description")
    col_discipline = _find_col("discipline")
    col_uom = _find_col("unit", "uom")
    col_pct = _find_col("progress pct", "physical % complete", "% complete", "actual % complete", "actual_pct", "progress %")
    col_today_qty = _find_col("today actual", "actual qty", "actual quantity", "actual_qty", "qty")
    col_cum_qty = _find_col("cumulative actual", "cum actual")
    col_act_start = _find_col("actual start", "start date", "start")
    col_act_finish = _find_col("actual finish", "finish date", "finish")
    col_date = _find_col("report date", "date", "data date")

    if not col_activity_id:
        raise HTTPException(
            status_code=400,
            detail="Could not find an Activity ID or L6 Task ID column in the uploaded schedule export.",
        )

    created_event_ids: list[str] = []

    with conn.cursor() as cur:
        # 1. Insert source document
        cur.execute(
            """INSERT INTO source_documents (document_id, file_name, document_type, uploader_id, file_hash)
               VALUES (%s, %s, %s, %s, %s)""",
            (document_id, file.filename, "SCHEDULE_EXPORT_PROGRESS", current_user.id, file_hash),
        )

        for index, row in df.iterrows():
            raw_id = row[col_activity_id]
            if pd.isna(raw_id) or str(raw_id).strip() == "":
                continue

            activity_id_str = str(raw_id).strip()
            activity_name = str(row[col_name]).strip() if col_name and not pd.isna(row[col_name]) else None
            discipline = str(row[col_discipline]).strip().upper() if col_discipline and not pd.isna(row[col_discipline]) else None
            uom = str(row[col_uom]).strip() if col_uom and not pd.isna(row[col_uom]) else None

            pct_val = None
            if col_pct and not pd.isna(row[col_pct]):
                try:
                    pct_val = float(str(row[col_pct]).replace("%", "").strip())
                except ValueError:
                    pct_val = None

            qty_val = None
            if col_today_qty and not pd.isna(row[col_today_qty]):
                try:
                    qty_val = float(row[col_today_qty])
                except ValueError:
                    qty_val = None
            elif col_cum_qty and not pd.isna(row[col_cum_qty]):
                try:
                    qty_val = float(row[col_cum_qty])
                except ValueError:
                    qty_val = None

            act_start = str(row[col_act_start]).strip() if col_act_start and not pd.isna(row[col_act_start]) else None
            act_finish = str(row[col_act_finish]).strip() if col_act_finish and not pd.isna(row[col_act_finish]) else None

            # Skip rows with no reported progress
            has_progress = (
                (pct_val is not None and pct_val > 0)
                or (qty_val is not None and qty_val > 0)
                or act_start is not None
                or act_finish is not None
            )
            if not has_progress:
                continue

            # Determine event date
            event_date = date.today()
            if col_date and not pd.isna(row[col_date]):
                try:
                    parsed_d = pd.to_datetime(row[col_date]).date()
                    event_date = parsed_d
                except Exception:
                    pass

            # Determine event type
            if act_finish:
                event_type = EventType.ACTUAL_FINISH.value
            elif act_start and (pct_val is None or pct_val == 0):
                event_type = EventType.ACTUAL_START.value
            else:
                event_type = EventType.PROGRESS_UPDATE.value

            # Determine claim mode
            if qty_val is not None and pct_val is None:
                claim_mode = ClaimMode.INCREMENTAL_QUANTITY.value
                claimed_pct = None
                claimed_quantity = qty_val
                claimed_uom = uom
            else:
                claim_mode = ClaimMode.CUMULATIVE_PCT.value
                claimed_pct = pct_val
                claimed_quantity = None
                claimed_uom = None

            raw_claim_text = (
                f"Schedule progress export for {activity_id_str}: "
                f"{activity_name or ''} "
                f"progress={claimed_pct if claimed_pct is not None else claimed_quantity} "
                f"{claimed_uom or ''}"
            ).strip()

            event_id = str(uuid.uuid4())

            cur.execute(
                """INSERT INTO execution_events (
                    event_id, document_id, schedule_id, event_date, raw_claim_text,
                    input_channel, reported_activity_id, discipline,
                    action, event_type, claim_mode,
                    claimed_quantity, claimed_uom, claimed_pct,
                    supervisor_id, status
                ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, 'EXTRACTED')""",
                (
                    event_id, document_id, active_schedule_id, event_date, raw_claim_text,
                    InputChannel.SCHEDULE_EXPORT.value, activity_id_str, discipline,
                    activity_name or activity_id_str, event_type, claim_mode,
                    claimed_quantity, claimed_uom, claimed_pct,
                    current_user.id,
                ),
            )

            reference_id = str(uuid.uuid4())
            cur.execute(
                """INSERT INTO source_references (
                    reference_id, event_id, file_name, row_cell_ref, raw_snippet
                ) VALUES (%s, %s, %s, %s, %s)""",
                (reference_id, event_id, file.filename, f"row_{index + 2}", raw_claim_text[:500]),
            )

            created_event_ids.append(event_id)

        conn.commit()

        if not created_event_ids:
            return []

        cur.execute(
            "SELECT * FROM execution_events WHERE event_id = ANY(%s) ORDER BY created_at ASC",
            (created_event_ids,),
        )
        rows = cur.fetchall()

    return [_row_to_claim_response(r) for r in rows]


# ---------------------------------------------------------------------------
# Claim Retrieval
# ---------------------------------------------------------------------------

@router.get("/claims/{event_id}", response_model=ClaimResponse)
def get_claim(
    event_id: str,
    conn=Depends(get_db),
    current_user: CurrentUser = Depends(require_role("SITE_ENGINEER", "SUPERVISOR")),
):
    with conn.cursor() as cur:
        cur.execute("SELECT * FROM execution_events WHERE event_id = %s", (event_id,))
        row = cur.fetchone()
    if not row:
        raise HTTPException(status_code=404, detail="Claim not found")
    return _row_to_claim_response(row)


@router.get("/claims", response_model=list[ClaimResponse])
def list_claims(
    status: Optional[str] = Query(default=None),
    discipline: Optional[str] = Query(default=None),
    conn=Depends(get_db),
    current_user: CurrentUser = Depends(require_role("SITE_ENGINEER", "SUPERVISOR")),
):
    query = "SELECT * FROM execution_events WHERE 1=1"
    params = []
    if status:
        query += " AND status = %s"
        params.append(status)
    if discipline:
        query += " AND discipline = %s"
        params.append(discipline)
    query += " ORDER BY created_at DESC"
    with conn.cursor() as cur:
        cur.execute(query, params)
        rows = cur.fetchall()
    return [_row_to_claim_response(r) for r in rows]
