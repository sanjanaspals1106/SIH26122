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
import uuid
from datetime import date, datetime
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query

from backend.shared.auth import CurrentUser, require_role
from backend.shared.db import get_db
from backend.shared.llm_extraction import extract_claim_fields
from backend.shared.schemas import ClaimResponse, InputChannel, TextClaimRequest

router = APIRouter(prefix="/api/v1", tags=["intake"])


@router.get("/intake/health")
def health():
    return {"status": "ok"}


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


# ---------------------------------------------------------------------------
# TODO (build next, in this order):
#   1. POST /claims/file        -- purpose=EVIDENCE_PHOTO | SCANNED_DIARY
#   2. POST /claims/schedule-export  -- parses P6/MSP file directly, no LLM
# ---------------------------------------------------------------------------
