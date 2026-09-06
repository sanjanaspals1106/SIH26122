import hashlib
import json
from typing import Any, Optional

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


def payload_hash(payload: Any) -> str:
    return hashlib.sha256(
        canonical_json(payload).encode("utf-8")
    ).hexdigest()


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
    payload: Any,
) -> int:
    previous_hash = get_previous_hash()
    current_payload_hash = payload_hash(payload)

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

    with get_connection() as conn:
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
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                entity_type,
                entity_id,
                action,
                actor_id,
                canonical_json(before_state) if before_state is not None else None,
                canonical_json(after_state) if after_state is not None else None,
                current_payload_hash,
                previous_hash,
                current_hash,
            ),
        )
        conn.commit()

        return cursor.lastrowid
