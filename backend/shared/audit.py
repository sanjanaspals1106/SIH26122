import hashlib
import json
from typing import Any, Dict, List, Optional, Tuple

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
    normalized_before = _normalize_state(before_state)
    normalized_after = _normalize_state(after_state)
    current_payload_hash = payload_hash(normalized_before, normalized_after)

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
                before_state=normalized_before,
                after_state=normalized_after,
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
                    canonical_json(normalized_before)
                    if normalized_before is not None
                    else None,
                    canonical_json(normalized_after)
                    if normalized_after is not None
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


def _normalize_state(val: Any) -> Any:
    """Normalize state from database row or caller into native deserialized structure for consistent hashing."""
    if val is None:
        return None
    if isinstance(val, str):
        try:
            return json.loads(val)
        except Exception:
            return val
    return val


def verify_audit_chain(
    logs: List[Dict[str, Any]],
    expected_genesis: str = GENESIS_HASH,
    allow_subchain: bool = False,
) -> Tuple[bool, Optional[str]]:
    """
    Verify full cryptographic audit chain integrity over a sequence of audit logs.

    Verifies:
    1. payload_hash recomputation from before_state + after_state.
    2. current_hash recomputation using compute_hash.
    3. previous_hash linkage:
       - For the first entry: previous_hash == expected_genesis (or matches expected start hash if allow_subchain).
       - For entry i > 0: previous_hash == logs[i-1]["current_hash"].
    4. Monotonic sequence ordering: log_id strictly increases.
    5. Entity / metadata integrity.

    Returns:
      (True, None) if completely valid.
      (False, failure_reason) if tampered or invalid.
    """
    if not logs:
        return True, None

    for i, log in enumerate(logs):
        log_id = log.get("log_id")

        # 1. Sequence order check
        if i > 0 and log_id is not None and logs[i - 1].get("log_id") is not None:
            if log_id <= logs[i - 1]["log_id"]:
                return False, f"Sequence order violation at index {i}: log_id {log_id} <= previous {logs[i-1]['log_id']}"

        # 2. Previous hash linkage check
        prev_hash = log.get("previous_hash")
        if i == 0:
            if not allow_subchain and prev_hash != expected_genesis:
                return False, f"Genesis/start linkage violation at index 0: expected {expected_genesis}, got {prev_hash}"
        else:
            expected_prev = logs[i - 1].get("current_hash")
            if prev_hash != expected_prev:
                return False, f"Chain linkage violation at index {i}: expected previous_hash '{expected_prev}', got '{prev_hash}'"

        # 3. Verify payload_hash
        before = _normalize_state(log.get("before_state"))
        after = _normalize_state(log.get("after_state"))
        recomputed_payload_hash = payload_hash(before, after)
        if log.get("payload_hash") != recomputed_payload_hash:
            return False, f"Payload hash mismatch at index {i} (log_id={log_id}): stored '{log.get('payload_hash')}', recomputed '{recomputed_payload_hash}'"

        # 4. Verify current_hash
        recomputed_curr_hash = compute_hash(
            entity_type=log.get("entity_type", ""),
            entity_id=str(log.get("entity_id", "")),
            action=log.get("action", ""),
            actor_id=str(log.get("actor_id", "")),
            before_state=before,
            after_state=after,
            payload_hash=log.get("payload_hash", ""),
            previous_hash=prev_hash or "",
        )
        if log.get("current_hash") != recomputed_curr_hash:
            return False, f"Current hash mismatch at index {i} (log_id={log_id}): stored '{log.get('current_hash')}', recomputed '{recomputed_curr_hash}'"

    return True, None


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
        is_valid, reason = verify_audit_chain(logs, allow_subchain=True)

        return {
            "entity_id": entity_id,
            "chain_valid": is_valid,
            "verification_detail": reason,
            "logs": logs,
        }
