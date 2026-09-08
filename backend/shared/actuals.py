import logging
import uuid
from datetime import date
from typing import Any, Optional, Union

from backend.shared.db import get_connection

logger = logging.getLogger(__name__)


def get_approved_actual(
    schedule_id: str,
    activity_id: str,
) -> Optional[dict]:
    """
    Return the latest approved actual for an activity.

    Approved actuals are the authoritative progress values.
    """
    with get_connection() as conn:
        row = conn.execute(
            """
            SELECT
                actual_id,
                decision_id,
                event_id,
                schedule_id,
                activity_id,
                actual_start,
                actual_finish,
                actual_pct_complete,
                actual_quantity,
                exported_at,
                created_at
            FROM approved_actuals
            WHERE schedule_id = %s
              AND activity_id = %s
            """,
            (schedule_id, activity_id),
        ).fetchone()

    return dict(row) if row else None


def get_approved_pct(
    schedule_id: str,
    activity_id: str,
) -> float:
    """
    Return approved percentage complete.

    Returns 0.0 when no approved actual exists.
    """
    actual = get_approved_actual(schedule_id, activity_id)

    if not actual:
        return 0.0

    return float(actual["actual_pct_complete"] or 0.0)


def _dispatch_adapters(actual: dict) -> dict:
    """
    Phase 1 adapter boundary hook.
    Establishes the shared actuals boundary required by subsequent phases.
    Later phases will invoke CSVExportAdapter and P6RestAdapter here.
    This hook is strictly non-blocking and isolated.
    """
    return {
        "csv_export": "not_implemented_phase1",
        "p6_rest": "not_implemented_phase1",
    }


def _execute_upsert(
    conn: Any,
    schedule_id: str,
    activity_id: str,
    event_id: str,
    decision_id: str,
    **fields: Any,
) -> Optional[dict]:
    """
    Internal transactional implementation of upsert_approved_actual.
    """
    # 1. Inspect planner_decisions if present to verify authority and action
    dec_row = conn.execute(
        """
        SELECT decision_id, event_id, selected_activity_id, action, approved_pct, approved_qty
        FROM planner_decisions
        WHERE decision_id = %s
        """,
        (decision_id,),
    ).fetchone()

    pd_action = dec_row["action"] if dec_row else None
    pd_selected_activity = dec_row["selected_activity_id"] if dec_row else None
    pd_approved_pct = dec_row["approved_pct"] if dec_row else None
    pd_approved_qty = dec_row["approved_qty"] if dec_row else None

    # Authority: After planner review, planner_decisions.selected_activity_id is authoritative
    if pd_selected_activity:
        activity_id = pd_selected_activity

    action = fields.get("action") or pd_action
    if action in ("HOLD", "REJECT"):
        # REJECT and HOLD do not write to approved_actuals
        return None

    # 2. Inspect execution_events for claim metadata if present
    ev_row = conn.execute(
        """
        SELECT event_id, schedule_id, event_date, event_type, claim_mode,
               claimed_quantity, claimed_pct, matched_activity_id
        FROM execution_events
        WHERE event_id = %s
        """,
        (event_id,),
    ).fetchone()

    claim_mode = (
        fields.get("claim_mode")
        or (ev_row["claim_mode"] if ev_row else None)
        or "CUMULATIVE_PCT"
    )
    event_type = fields.get("event_type") or (ev_row["event_type"] if ev_row else None)
    event_date = fields.get("event_date") or (ev_row["event_date"] if ev_row else None)
    ev_claimed_pct = ev_row["claimed_pct"] if ev_row else None

    # 3. Lock and retrieve existing approved_actuals row for (schedule_id, activity_id)
    existing_row = conn.execute(
        """
        SELECT
            actual_id,
            decision_id,
            event_id,
            schedule_id,
            activity_id,
            actual_start,
            actual_finish,
            actual_pct_complete,
            actual_quantity,
            exported_at,
            created_at
        FROM approved_actuals
        WHERE schedule_id = %s
          AND activity_id = %s
        FOR UPDATE
        """,
        (schedule_id, activity_id),
    ).fetchone()

    existing = dict(existing_row) if existing_row else None

    # 4. Start/Finish date merging (Rule B)
    # Never erase existing start when updating finish; never erase finish when updating start
    incoming_start = fields.get("actual_start")
    incoming_finish = fields.get("actual_finish")

    if incoming_start is None and event_type == "ACTUAL_START":
        incoming_start = event_date
    if incoming_finish is None and event_type == "ACTUAL_FINISH":
        incoming_finish = event_date

    final_start = (
        incoming_start
        if incoming_start is not None
        else (existing["actual_start"] if existing else None)
    )
    final_finish = (
        incoming_finish
        if incoming_finish is not None
        else (existing["actual_finish"] if existing else None)
    )

    # 5. Cumulative percentage (Rule C)
    # Replaces the previous actual_pct_complete; does not add percentages
    if claim_mode == "CUMULATIVE_PCT" or "approved_pct" in fields or "actual_pct_complete" in fields:
        pct_candidate = None
        if fields.get("approved_pct") is not None:
            pct_candidate = fields["approved_pct"]
        elif pd_approved_pct is not None:
            pct_candidate = pd_approved_pct
        elif fields.get("actual_pct_complete") is not None:
            pct_candidate = fields["actual_pct_complete"]
        elif fields.get("claimed_pct") is not None:
            pct_candidate = fields["claimed_pct"]
        elif ev_claimed_pct is not None:
            pct_candidate = ev_claimed_pct

        if pct_candidate is not None:
            final_pct = float(pct_candidate)
            final_pct = max(0.0, min(100.0, final_pct))
        else:
            final_pct = (
                float(existing["actual_pct_complete"])
                if existing and existing["actual_pct_complete"] is not None
                else None
            )
    else:
        final_pct = (
            float(existing["actual_pct_complete"])
            if existing and existing["actual_pct_complete"] is not None
            else fields.get("actual_pct_complete")
        )

    # 6. Incremental quantity (Rule D)
    # Recalculate from database source rows using canonical PRD v5 query
    if claim_mode == "INCREMENTAL_QUANTITY":
        recalc_row = conn.execute(
            """
            SELECT COALESCE(SUM(COALESCE(pd.approved_qty, ee.claimed_quantity)), 0.0) AS total_qty
            FROM execution_events ee
            JOIN planner_decisions pd ON pd.event_id = ee.event_id
            WHERE ee.schedule_id = %s
              AND pd.selected_activity_id = %s
              AND pd.action IN ('APPROVE', 'EDIT')
              AND pd.decision_id = (
                SELECT pd2.decision_id FROM planner_decisions pd2
                WHERE pd2.event_id = ee.event_id
                ORDER BY pd2.decided_at DESC, pd2.decision_id DESC
                LIMIT 1
              )
            """,
            (schedule_id, activity_id),
        ).fetchone()

        recalculated_qty = (
            float(recalc_row["total_qty"])
            if recalc_row and recalc_row["total_qty"] is not None
            else 0.0
        )

        if recalculated_qty > 0.0:
            final_quantity = recalculated_qty
        elif fields.get("actual_quantity") is not None:
            final_quantity = float(fields["actual_quantity"])
        elif fields.get("approved_qty") is not None:
            final_quantity = float(fields["approved_qty"])
        elif pd_approved_qty is not None:
            final_quantity = float(pd_approved_qty)
        else:
            final_quantity = recalculated_qty
    else:
        final_quantity = (
            float(fields["actual_quantity"])
            if fields.get("actual_quantity") is not None
            else (
                float(existing["actual_quantity"])
                if existing and existing["actual_quantity"] is not None
                else None
            )
        )

    # 7. Write to approved_actuals (Rule A & Rule F)
    if existing:
        saved_row = conn.execute(
            """
            UPDATE approved_actuals
            SET
                decision_id = %s,
                event_id = %s,
                actual_start = %s,
                actual_finish = %s,
                actual_pct_complete = %s,
                actual_quantity = %s
            WHERE schedule_id = %s
              AND activity_id = %s
            RETURNING
                actual_id,
                decision_id,
                event_id,
                schedule_id,
                activity_id,
                actual_start,
                actual_finish,
                actual_pct_complete,
                actual_quantity,
                exported_at,
                created_at
            """,
            (
                decision_id,
                event_id,
                final_start,
                final_finish,
                final_pct,
                final_quantity,
                schedule_id,
                activity_id,
            ),
        ).fetchone()
    else:
        new_actual_id = str(uuid.uuid4())
        saved_row = conn.execute(
            """
            INSERT INTO approved_actuals (
                actual_id,
                decision_id,
                event_id,
                schedule_id,
                activity_id,
                actual_start,
                actual_finish,
                actual_pct_complete,
                actual_quantity
            )
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
            ON CONFLICT (schedule_id, activity_id) DO UPDATE SET
                decision_id = EXCLUDED.decision_id,
                event_id = EXCLUDED.event_id,
                actual_start = COALESCE(EXCLUDED.actual_start, approved_actuals.actual_start),
                actual_finish = COALESCE(EXCLUDED.actual_finish, approved_actuals.actual_finish),
                actual_pct_complete = COALESCE(EXCLUDED.actual_pct_complete, approved_actuals.actual_pct_complete),
                actual_quantity = COALESCE(EXCLUDED.actual_quantity, approved_actuals.actual_quantity)
            RETURNING
                actual_id,
                decision_id,
                event_id,
                schedule_id,
                activity_id,
                actual_start,
                actual_finish,
                actual_pct_complete,
                actual_quantity,
                exported_at,
                created_at
            """,
            (
                new_actual_id,
                decision_id,
                event_id,
                schedule_id,
                activity_id,
                final_start,
                final_finish,
                final_pct,
                final_quantity,
            ),
        ).fetchone()

    result = dict(saved_row) if saved_row else None
    return result


def upsert_approved_actual(
    schedule_id: str,
    activity_id: str,
    event_id: str,
    decision_id: str,
    **fields: Any,
) -> Optional[dict]:
    """
    Canonical approved-actual upsert according to PRD v5 Section 15.

    - Merges start/finish dates without erasing existing values.
    - Replaces cumulative percentages (does not add).
    - Recalculates incremental quantities from latest APPROVE/EDIT planner decisions.
    - Honors selected_activity_id from planner_decisions as authoritative.
    - Safely skips write for HOLD and REJECT actions.
    - Commits approved_actuals database transaction before triggering adapters.
    - Dispatches isolated, non-blocking auto-export hook post-commit.
    """
    fields_copy = dict(fields)
    external_conn = fields_copy.pop("conn", None)

    if external_conn is not None:
        result = _execute_upsert(
            external_conn,
            schedule_id,
            activity_id,
            event_id,
            decision_id,
            **fields_copy,
        )
        if result is None:
            return None

        if hasattr(external_conn, "commit"):
            external_conn.commit()

        try:
            from backend.routers.export import trigger_auto_export
            trigger_auto_export(conn=external_conn, schedule_id=schedule_id)
        except Exception as e:
            logger.warning("Auto-triggered CSV export error (non-blocking): %s", e)

        return result

    with get_connection() as conn:
        result = _execute_upsert(
            conn,
            schedule_id,
            activity_id,
            event_id,
            decision_id,
            **fields_copy,
        )
        if result is None:
            return None

        conn.commit()

        try:
            from backend.routers.export import trigger_auto_export
            trigger_auto_export(conn=conn, schedule_id=schedule_id)
        except Exception as e:
            logger.warning("Auto-triggered CSV export error (non-blocking): %s", e)

        return result
