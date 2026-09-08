"""
Owner: M2. Others: read-only. If you need a new field returned from this
router, ask M2 — don't edit this file directly.

Changes in this version, per PRD v5:
  - Role-gated: SITE_ENGINEER required (via shared/auth.py's require_role()).
    NOTE: shared/auth.py is currently M2's temporary local stub, not M6's
    real implementation — see the big warning at the top of that file.
  - uploader_id/supervisor_id are no longer accepted from the request body
    (PRD v5 6.2: "User identity must never be accepted as a free-form
    request-body field"). They're derived from the authenticated user.
  - Postgres via psycopg2 instead of SQLite.
"""
import hashlib
import io
import os
import uuid
from datetime import date, datetime
from pathlib import Path
from typing import List, Optional

from fastapi import APIRouter, Depends, File, Form, HTTPException, Query, UploadFile

from backend.shared.auth import UserProfile as CurrentUser, require_role
from backend.shared.db import get_db
from backend.shared.llm_extraction import extract_claim_fields
from backend.shared.schemas import (
    ClaimMode,
    ClaimResponse,
    Discipline,
    EventType,
    InputChannel,
    TextClaimRequest,
    UploadPurpose,
)

router = APIRouter(prefix="/api/v1", tags=["intake"])

# Where evidence photos land on disk (SCANNED_DIARY images never get saved
# here -- they're OCR'd and discarded, per the purpose contract below).
UPLOAD_DIR = Path(
    os.getenv("UPLOAD_DIR") or (Path(__file__).resolve().parents[1] / "uploads")
)

IMAGE_EXTENSIONS = {".jpg", ".jpeg", ".png"}

_DISCIPLINE_ALIASES = {
    "civil": Discipline.CIVIL.value,
    "piping": Discipline.PIPING.value,
    "static/rotating equipment": Discipline.STATIC_ROTATING_EQUIPMENT.value,
    "static rotating equipment": Discipline.STATIC_ROTATING_EQUIPMENT.value,
    "electrical": Discipline.ELECTRICAL.value,
    "instrumentation": Discipline.INSTRUMENTATION.value,
    "hse": Discipline.HSE.value,
}


def _normalize_discipline(raw: Optional[str]) -> Optional[str]:
    if not raw:
        return None
    key = raw.strip().lower()
    if key in _DISCIPLINE_ALIASES:
        return _DISCIPLINE_ALIASES[key]
    upper = raw.strip().upper().replace(" ", "_").replace("/", "_")
    return upper or None


def _extract_text_from_file(filename: str, contents: bytes) -> str:
    """
    Extracts plain text from a non-image file intake (#2): .txt read
    directly, .pdf via PyMuPDF, .csv/.xlsx via pandas -- the resulting text
    is fed into the same LLM extraction step any typed claim goes through.
    """
    ext = Path(filename or "").suffix.lower()

    if ext == ".txt":
        return contents.decode("utf-8", errors="replace")

    if ext == ".pdf":
        import pymupdf as fitz

        doc = fitz.open(stream=contents, filetype="pdf")
        try:
            return "\n".join(page.get_text() for page in doc)
        finally:
            doc.close()

    if ext == ".csv":
        import pandas as pd

        df = pd.read_csv(io.BytesIO(contents))
        return df.to_string(index=False)

    if ext in (".xlsx", ".xls"):
        import pandas as pd

        df = pd.read_excel(io.BytesIO(contents))
        return df.to_string(index=False)

    raise HTTPException(
        status_code=415,
        detail=f"Unsupported file type '{ext}'. Accepted: .pdf, .xlsx, .csv, .txt, .jpg, .png",
    )


def _run_ocr(contents: bytes) -> str:
    """
    pytesseract by default, per the shared context's OCR decision -- no
    vision-LLM call in the default path. Never raises: a malformed/blank
    scan just yields empty text, which the caller falls back on.
    """
    try:
        import pytesseract
        from PIL import Image

        image = Image.open(io.BytesIO(contents))
        text = pytesseract.image_to_string(image)
        return (text or "").strip()
    except Exception:
        return ""


@router.get("/intake/health")
def health():
    return {"status": "ok"}


# Registered before GET /claims/{event_id} below -- Starlette matches routes
# in registration order, so this literal path must be added first or every
# request to it would instead match the dynamic route with event_id="health".
@router.get("/claims/health")
def claims_health():
    return {"router": "intake", "status": "ok"}


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
        input_channel=row["input_channel"],
        language_detected=row["language_detected"],
        reported_activity_id=row["reported_activity_id"],
        matched_activity_id=row["matched_activity_id"],
        discipline=row["discipline"],
        action=row["action"],
        event_type=row["event_type"],
        claim_mode=row["claim_mode"],
        asset_tag=row["asset_tag"],
        location=row["location"],
        claimed_quantity=row["claimed_quantity"],
        claimed_uom=row["claimed_uom"],
        claimed_pct=row["claimed_pct"],
        delay_reason=row["delay_reason"],
        supervisor_id=str(row["supervisor_id"]) if row["supervisor_id"] else None,
        photo_path=row["photo_path"],
        status=row["status"],
        created_at=row["created_at"],
    )


@router.post("/claims/text", response_model=ClaimResponse)
def create_text_claim(
    payload: TextClaimRequest,
    conn=Depends(get_db),
    current_user: CurrentUser = Depends(require_role("SITE_ENGINEER")),
):
    """
    Handles both TYPED_TEXT and VOICE (voice already arrives as text from the
    browser's Web Speech API — no audio processing happens here).
    """
    schedule_id = payload.schedule_id or _get_active_schedule_id(conn)
    if not schedule_id:
        raise HTTPException(
            status_code=409,
            detail="No schedule uploaded yet — a schedule must exist before claims can be created.",
        )

    # 1. Hash the raw text itself (no file exists for typed/voice claims) and
    #    log it as a source_document for audit-trail consistency with
    #    file-based claims. file_name is NOT NULL in the schema, so use the
    #    input_channel as a synthetic placeholder for text-based claims
    #    rather than violating the constraint or loosening it unilaterally.
    text_hash = hashlib.sha256(payload.raw_claim_text.encode("utf-8")).hexdigest()
    document_id = str(uuid.uuid4())

    with conn.cursor() as cur:
        cur.execute(
            """INSERT INTO source_documents (document_id, file_name, document_type, uploader_id, file_hash)
               VALUES (%s, %s, %s, %s, %s)""",
            (document_id, f"[{payload.input_channel.value}]", "CHAT_LOG", current_user.id, text_hash),
        )

        # 2. Run extraction.
        extracted = extract_claim_fields(payload.raw_claim_text)

        # 3. Insert the claim at EXTRACTED (the only status M2 is allowed to write).
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

        # Provenance (feature #2's "Provenance" requirement): for typed/voice
        # claims there's no source file, so the raw claim text itself is the
        # snippet -- kept consistent with the file-intake endpoints below,
        # which record source_references the same way.
        cur.execute(
            """INSERT INTO source_references (reference_id, event_id, file_name, sheet_name, row_cell_ref, message_id, raw_snippet)
               VALUES (%s, %s, %s, %s, %s, %s, %s)""",
            (str(uuid.uuid4()), event_id, None, None, None, None, payload.raw_claim_text[:2000]),
        )

        conn.commit()

        cur.execute("SELECT * FROM execution_events WHERE event_id = %s", (event_id,))
        row = cur.fetchone()

    return _row_to_claim_response(row)


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


@router.post("/claims/file", response_model=ClaimResponse)
def create_file_claim(
    file: UploadFile = File(...),
    purpose: UploadPurpose = Form(UploadPurpose.EVIDENCE_PHOTO),
    raw_claim_text: Optional[str] = Form(None),
    conn=Depends(get_db),
    current_user: CurrentUser = Depends(require_role("SITE_ENGINEER")),
):
    """
    File intake (#2): .pdf/.xlsx/.csv/.txt, or an image disambiguated by
    `purpose`. EVIDENCE_PHOTO (default) is proof attached to a claim --
    saved to disk, its path recorded in photo_path for M4's evidence
    check. SCANNED_DIARY (#21) means the image IS the claim -- routed
    through pytesseract OCR instead, never written to photo_path.
    """
    schedule_id = _get_active_schedule_id(conn)
    if not schedule_id:
        raise HTTPException(
            status_code=409,
            detail="No schedule uploaded yet — a schedule must exist before claims can be created.",
        )

    contents = file.file.read()
    if not contents:
        raise HTTPException(status_code=422, detail="Uploaded file is empty.")

    ext = Path(file.filename or "").suffix.lower()
    file_hash = hashlib.sha256(contents).hexdigest()

    photo_path: Optional[str] = None
    document_type = "DPR"
    input_channel = InputChannel.FILE_UPLOAD

    if ext in IMAGE_EXTENSIONS:
        if purpose == UploadPurpose.SCANNED_DIARY:
            document_type = "SCANNED_DIARY"
            input_channel = InputChannel.SCANNED_OCR
            ocr_text = _run_ocr(contents)
            # A poor/degraded scan can legitimately OCR to nothing --
            # fall back to an accompanying raw_claim_text rather than
            # hard-failing the whole intake, since OCR here is explicitly
            # not required to be production-grade.
            text_content = ocr_text or (raw_claim_text or "")
        else:  # EVIDENCE_PHOTO
            document_type = "QC_INSPECTION"
            if not raw_claim_text:
                raise HTTPException(
                    status_code=422,
                    detail=(
                        "raw_claim_text is required when purpose=EVIDENCE_PHOTO "
                        "-- the photo is evidence attached to a claim, not the "
                        "claim itself."
                    ),
                )
            text_content = raw_claim_text
            UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
            saved_name = f"{uuid.uuid4()}_{file.filename}"
            saved_path = UPLOAD_DIR / saved_name
            saved_path.write_bytes(contents)
            photo_path = str(saved_path)
    else:
        text_content = _extract_text_from_file(file.filename or "upload", contents)
        if raw_claim_text:
            text_content = f"{text_content}\n\n{raw_claim_text}"

    if not text_content or not text_content.strip():
        raise HTTPException(
            status_code=422,
            detail="No extractable text content in uploaded file.",
        )

    document_id = str(uuid.uuid4())

    with conn.cursor() as cur:
        cur.execute(
            """INSERT INTO source_documents (document_id, file_name, document_type, uploader_id, file_hash)
               VALUES (%s, %s, %s, %s, %s)""",
            (document_id, file.filename, document_type, current_user.id, file_hash),
        )

        extracted = extract_claim_fields(text_content)
        event_id = str(uuid.uuid4())
        event_date = extracted.event_date or date.today()

        if photo_path is not None:
            cur.execute(
                """INSERT INTO execution_events (
                    event_id, document_id, schedule_id, event_date, raw_claim_text,
                    input_channel, language_detected, reported_activity_id, discipline,
                    action, event_type, claim_mode, asset_tag, location,
                    claimed_quantity, claimed_uom, claimed_pct, delay_reason,
                    supervisor_id, photo_path, status
                ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, 'EXTRACTED')""",
                (
                    event_id, document_id, schedule_id, event_date, text_content,
                    input_channel.value, extracted.language_detected, extracted.reported_activity_id,
                    extracted.discipline.value if extracted.discipline else None,
                    extracted.action, extracted.event_type.value if extracted.event_type else None,
                    extracted.claim_mode.value, extracted.asset_tag, extracted.location,
                    extracted.claimed_quantity, extracted.claimed_uom, extracted.claimed_pct,
                    extracted.delay_reason.value if extracted.delay_reason else None,
                    current_user.id, photo_path,
                ),
            )
        else:
            cur.execute(
                """INSERT INTO execution_events (
                    event_id, document_id, schedule_id, event_date, raw_claim_text,
                    input_channel, language_detected, reported_activity_id, discipline,
                    action, event_type, claim_mode, asset_tag, location,
                    claimed_quantity, claimed_uom, claimed_pct, delay_reason,
                    supervisor_id, status
                ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, 'EXTRACTED')""",
                (
                    event_id, document_id, schedule_id, event_date, text_content,
                    input_channel.value, extracted.language_detected, extracted.reported_activity_id,
                    extracted.discipline.value if extracted.discipline else None,
                    extracted.action, extracted.event_type.value if extracted.event_type else None,
                    extracted.claim_mode.value, extracted.asset_tag, extracted.location,
                    extracted.claimed_quantity, extracted.claimed_uom, extracted.claimed_pct,
                    extracted.delay_reason.value if extracted.delay_reason else None,
                    current_user.id,
                ),
            )

        cur.execute(
            """INSERT INTO source_references (reference_id, event_id, file_name, sheet_name, row_cell_ref, message_id, raw_snippet)
               VALUES (%s, %s, %s, %s, %s, %s, %s)""",
            (str(uuid.uuid4()), event_id, file.filename, None, None, None, text_content[:2000]),
        )

        conn.commit()

        cur.execute("SELECT * FROM execution_events WHERE event_id = %s", (event_id,))
        row = cur.fetchone()

    return _row_to_claim_response(row)


@router.post("/claims/schedule-export", response_model=List[ClaimResponse])
def create_schedule_export_claims(
    file: UploadFile = File(...),
    conn=Depends(get_db),
    current_user: CurrentUser = Depends(require_role("SITE_ENGINEER")),
):
    """
    Schedule-export claims (#22, parsing half): a second P6/MSP-format file
    used as a *source of progress claims*, not a new baseline. Since each
    row already carries a real activity_id, these skip LLM extraction
    entirely and go straight to M3's matching as EXACT_ID candidates. Only
    rows with actual progress data produce a claim -- an empty/not-started
    row is not a progress report.
    """
    schedule_id = _get_active_schedule_id(conn)
    if not schedule_id:
        raise HTTPException(
            status_code=409,
            detail="No schedule uploaded yet — a schedule must exist before claims can be created.",
        )

    contents = file.file.read()
    if not contents:
        raise HTTPException(status_code=422, detail="Uploaded file is empty.")

    import pandas as pd

    ext = Path(file.filename or "").suffix.lower()
    try:
        if ext in (".xlsx", ".xls"):
            df = pd.read_excel(io.BytesIO(contents))
        else:
            df = pd.read_csv(io.BytesIO(contents))
    except Exception as e:
        raise HTTPException(
            status_code=422, detail=f"Could not parse schedule-export file: {e}"
        )

    df.columns = [str(c).strip() for c in df.columns]
    col_map = {c.lower(): c for c in df.columns}

    def _col(*names: str) -> Optional[str]:
        for n in names:
            if n in col_map:
                return col_map[n]
        return None

    activity_col = _col("activity id", "l6 task id")
    name_col = _col("activity name", "work description", "activity")
    discipline_col = _col("discipline")
    qty_col = _col("today actual")
    pct_col = _col("progress pct", "cumulative pct", "% complete")
    status_col = _col("status")
    date_col = _col("report date", "date", "data date")

    if activity_col is None:
        raise HTTPException(
            status_code=422,
            detail="Schedule-export file has no 'Activity ID' column.",
        )

    def _to_float(value) -> Optional[float]:
        if value is None:
            return None
        text = str(value).strip()
        if not text or text.lower() == "nan":
            return None
        try:
            return float(text)
        except ValueError:
            return None

    file_hash = hashlib.sha256(contents).hexdigest()
    document_id = str(uuid.uuid4())
    claim_rows: List[dict] = []

    with conn.cursor() as cur:
        cur.execute(
            """INSERT INTO source_documents (document_id, file_name, document_type, uploader_id, file_hash)
               VALUES (%s, %s, %s, %s, %s)""",
            (document_id, file.filename, "SCHEDULE_EXPORT_PROGRESS", current_user.id, file_hash),
        )

        for _, row in df.iterrows():
            activity_id = str(row.get(activity_col) or "").strip()
            if not activity_id or activity_id.lower() == "nan":
                continue

            pct = _to_float(row.get(pct_col)) if pct_col else None
            qty = _to_float(row.get(qty_col)) if qty_col else None

            has_progress_data = (pct is not None and pct > 0) or (qty is not None and qty > 0)
            if not has_progress_data:
                continue

            name = str(row.get(name_col) or "").strip() if name_col else ""
            discipline_raw = str(row.get(discipline_col) or "").strip() if discipline_col else ""
            status_val = str(row.get(status_col) or "").strip() if status_col else ""

            event_date = date.today()
            if date_col:
                try:
                    event_date = pd.to_datetime(row.get(date_col)).date()
                except Exception:
                    pass

            event_type = (
                EventType.ACTUAL_FINISH.value
                if pct is not None and pct >= 100
                else EventType.PROGRESS_UPDATE.value
            )

            event_id = str(uuid.uuid4())
            raw_text = f"Schedule export progress update for {activity_id}: {name} — {status_val}".strip()

            cur.execute(
                """INSERT INTO execution_events (
                    event_id, document_id, schedule_id, event_date, raw_claim_text,
                    input_channel, reported_activity_id, discipline,
                    action, event_type, claim_mode, claimed_quantity, claimed_uom, claimed_pct,
                    supervisor_id, status
                ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, 'EXTRACTED')""",
                (
                    event_id, document_id, schedule_id, event_date, raw_text,
                    InputChannel.SCHEDULE_EXPORT.value, activity_id, _normalize_discipline(discipline_raw),
                    name, event_type, ClaimMode.CUMULATIVE_PCT.value, None, None, pct,
                    current_user.id,
                ),
            )

            cur.execute(
                """INSERT INTO source_references (reference_id, event_id, file_name, sheet_name, row_cell_ref, message_id, raw_snippet)
                   VALUES (%s, %s, %s, %s, %s, %s, %s)""",
                (str(uuid.uuid4()), event_id, file.filename, None, None, None, str(row.to_dict())[:2000]),
            )

            cur.execute("SELECT * FROM execution_events WHERE event_id = %s", (event_id,))
            claim_rows.append(cur.fetchone())

        conn.commit()

    return [_row_to_claim_response(r) for r in claim_rows]
