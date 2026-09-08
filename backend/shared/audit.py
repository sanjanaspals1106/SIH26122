import hashlib
import json
from typing import Any, Dict, List, Optional

from backend.shared.db import get_connection

GENESIS_HASH = "0" * 64


def canonical_json(data: Any) -> str:
    return json.dumps(
        data,
        sort_keys=True,
        separators=(",", ":"),
        default=str,
    )


def compute_hash(
    entity_type: str,
    entity_id: str,
    action: str,
    actor_id: str,
    before_state: Optional[Any],
    after_state: Optional[Any],
    payload_hash: str,
    previous_hash: str,
) -> str:
    payload = canonical_json(
        {
            "entity_type": entity_type,
            "entity_id": entity_id,
            "action": action,
            "actor_id": actor_id,
            "before_state": before_state,
            "after_state": after_state,
            "payload_hash": payload_hash,
            "previous_hash": previous_hash,
        }
    )

    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def payload_hash(before_state: Optional[Any], after_state: Optional[Any]) -> str:
    before_str = canonical_json(before_state) if before_state is not None else ""
    after_str = canonical_json(after_state) if after_state is not None else ""
    return hashlib.sha256((before_str + after_str).encode("utf-8")).hexdigest()


def get_previous_hash() -> str:
    with get_connection() as conn:
        row = conn.execute(
            """
            SELECT current_hash
            FROM audit_logs
            ORDER BY log_id DESC
            LIMIT 1
            """
        ).fetchone()

    return row["current_hash"] if row else GENESIS_HASH


def write_audit_log(
    entity_type: str,
    entity_id: str,
    action: str,
    actor_id: str,
    before_state: Optional[Any],
    after_state: Optional[Any],
    payload: Any = None,
) -> int:
    current_payload_hash = payload_hash(before_state, after_state)

    with get_connection() as conn:
        with conn.transaction():
            cursor = conn.execute(
                """
                SELECT current_hash
                FROM audit_logs
                ORDER BY log_id DESC
                LIMIT 1
                FOR UPDATE
                """
            )
            row = cursor.fetchone()
            previous_hash = row["current_hash"] if row else GENESIS_HASH

            current_hash = compute_hash(
                entity_type=entity_type,
                entity_id=entity_id,
                action=action,
                actor_id=actor_id,
                before_state=before_state,
                after_state=after_state,
                payload_hash=current_payload_hash,
                previous_hash=previous_hash,
            )

            cursor = conn.execute(
                """
                INSERT INTO audit_logs (
                    entity_type,
                    entity_id,
                    action,
                    actor_id,
                    before_state,
                    after_state,
                    payload_hash,
                    previous_hash,
                    current_hash
                )
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
                RETURNING log_id
                """,
                (
                    entity_type,
                    entity_id,
                    action,
                    actor_id,
                    canonical_json(before_state)
                    if before_state is not None
                    else None,
                    canonical_json(after_state)
                    if after_state is not None
                    else None,
                    current_payload_hash,
                    previous_hash,
                    current_hash,
                ),
            )

            row = cursor.fetchone()
            return row["log_id"]


def list_recent_audit_logs(limit: int = 20) -> List[Dict[str, Any]]:
    """Most recent audit_logs rows, newest first -- read-only convenience
    for a general activity feed (e.g. Activity History's audit trail card),
    as distinct from get_audit_trail()'s per-entity chain view."""
    safe_limit = max(1, min(limit, 200))
    with get_connection() as conn:
        rows = conn.execute(
            """
            SELECT * FROM audit_logs
            ORDER BY log_id DESC
            LIMIT %s
            """,
            (safe_limit,),
        ).fetchall()
        return [dict(r) for r in rows]


def get_audit_trail(entity_id: str) -> Dict[str, Any]:
    with get_connection() as conn:
        rows = conn.execute(
            """
            SELECT * FROM audit_logs
            WHERE entity_id = %s
            ORDER BY log_id ASC
            """,
            (entity_id,),
        ).fetchall()

        logs = [dict(r) for r in rows]
        is_valid = True
        for i, log in enumerate(logs):
            before_str = log["before_state"] or ""
            after_str = log["after_state"] or ""
            expected_payload_hash = hashlib.sha256(
                (before_str + after_str).encode("utf-8")
            ).hexdigest()
            if log["payload_hash"] != expected_payload_hash:
                is_valid = False
                break

        return {
            "entity_id": entity_id,
            "chain_valid": is_valid,
            "logs": logs,
        }
