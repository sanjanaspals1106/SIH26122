import math
import os
import uuid
from datetime import datetime
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException

from backend.shared.audit import get_audit_trail, write_audit_log
from backend.shared.db import get_connection

try:
    from backend.shared.auth import require_role
    _supervisor_dep = [Depends(require_role("SUPERVISOR"))]
except Exception:
    _supervisor_dep = []

SYSTEM_ACTOR_M4 = "SYSTEM:M4"

router = APIRouter(prefix="/api/v1", tags=["checks"])


@router.get("/claims/checks/health")
def health():
    return {"router": "checks", "status": "ok"}


def _convert_to_degrees(value) -> float:
    d = float(value.values[0].num) / float(value.values[0].den)
    m = float(value.values[1].num) / float(value.values[1].den)
    s = float(value.values[2].num) / float(value.values[2].den)
    return d + (m / 60.0) + (s / 3600.0)


def haversine_distance_km(
    lat1: float, lon1: float, lat2: float, lon2: float
) -> float:
    R = 6371.0
    dlat = math.radians(lat2 - lat1)
    dlon = math.radians(lon2 - lon1)
    a = (
        math.sin(dlat / 2) ** 2
        + math.cos(math.radians(lat1))
        * math.cos(math.radians(lat2))
        * math.sin(dlon / 2) ** 2
    )
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
    return R * c


def _parse_exif(photo_path: str) -> Dict[str, Any]:
    exif_data = {}
    if not os.path.exists(photo_path):
        return exif_data

    try:
        import exifread

        with open(photo_path, "rb") as f:
            tags = exifread.process_file(f, details=False)
            if "EXIF DateTimeOriginal" in tags:
                exif_data["datetime_original"] = str(
                    tags["EXIF DateTimeOriginal"]
                )
            elif "Image DateTime" in tags:
                exif_data["datetime_original"] = str(tags["Image DateTime"])

            lat_tag = tags.get("GPS GPSLatitude")
            lon_tag = tags.get("GPS GPSLongitude")
            lat_ref = tags.get("GPS GPSLatitudeRef")
            lon_ref = tags.get("GPS GPSLongitudeRef")

            if lat_tag and lon_tag:
                exif_data["has_gps"] = True
                lat = _convert_to_degrees(lat_tag)
                if lat_ref and str(lat_ref.values).upper() == "S":
                    lat = -lat
                lon = _convert_to_degrees(lon_tag)
                if lon_ref and str(lon_ref.values).upper() == "W":
                    lon = -lon
                exif_data["lat"] = lat
                exif_data["lon"] = lon
    except Exception:
        pass

    return exif_data


@router.post("/claims/{event_id}/check")
def check_claim(event_id: str):
    with get_connection() as conn:
        with conn.transaction():
            event_row = conn.execute(
                """
                SELECT * FROM execution_events
                WHERE event_id = %s
                FOR UPDATE
                """,
                (event_id,),
            ).fetchone()

            if not event_row:
                raise HTTPException(
                    status_code=404,
                    detail=f"Claim event {event_id} not found.",
                )

            before_state = dict(event_row)
            incoming_status = event_row.get("status")

            schedule_id = event_row["schedule_id"]
            matched_activity_id = event_row.get("matched_activity_id")
            event_date = event_row["event_date"]
            claimed_pct = event_row.get("claimed_pct")
            claimed_qty = event_row.get("claimed_quantity")
            claimed_uom = event_row.get("claimed_uom")
            photo_path = event_row.get("photo_path")
            claim_mode = event_row.get("claim_mode") or "CUMULATIVE_PCT"
            event_type = event_row.get("event_type")

            activity_row = None
            if matched_activity_id:
                activity_row = conn.execute(
                    """
                    SELECT * FROM schedule_activities
                    WHERE schedule_id = %s AND activity_id = %s
                    """,
                    (schedule_id, matched_activity_id),
                ).fetchone()

            validation_issues: List[Dict[str, Any]] = []
            conflict_records_to_insert: List[Dict[str, Any]] = []

            # 1. Incoming UNMATCHED status check
            if incoming_status == "UNMATCHED":
                validation_issues.append(
                    {
                        "issue_id": str(uuid.uuid4()),
                        "event_id": event_id,
                        "rule_code": "VAL_LOW_MATCH_CONFIDENCE",
                        "severity": "WARNING",
                        "description": "Match confidence fell below matching threshold.",
                    }
                )

            # 2. Granularity Rollup vs Percentage Conflict logic
            if claim_mode == "INCREMENTAL_QUANTITY":
                if claimed_qty is not None and activity_row:
                    planned_qty = activity_row.get("planned_quantity")
                    if planned_qty and planned_qty > 0:
                        prior_qty_row = conn.execute(
                            """
                            SELECT COALESCE(SUM(COALESCE(pd.approved_qty, ee.claimed_quantity)), 0.0) AS total_qty
                            FROM execution_events ee
                            JOIN planner_decisions pd ON pd.event_id = ee.event_id
                            WHERE ee.schedule_id = %s
                              AND ee.matched_activity_id = %s
                              AND pd.action IN ('APPROVE', 'EDIT')
                              AND pd.decision_id = (
                                  SELECT decision_id FROM planner_decisions pd2
                                  WHERE pd2.event_id = ee.event_id
                                  ORDER BY pd2.decided_at DESC LIMIT 1
                              )
                            """,
                            (schedule_id, matched_activity_id),
                        ).fetchone()

                        total_prior = (
                            prior_qty_row["total_qty"] if prior_qty_row else 0.0
                        )
                        total_sum = total_prior + claimed_qty
                        derived_pct = round(
                            (total_sum / planned_qty) * 100.0, 2
                        )
                        claimed_pct = derived_pct

                        if derived_pct > 100.0:
                            validation_issues.append(
                                {
                                    "issue_id": str(uuid.uuid4()),
                                    "event_id": event_id,
                                    "rule_code": "VAL_OVER_100",
                                    "severity": "ERROR",
                                    "description": f"Derived progress percentage ({derived_pct}%) exceeds 100%.",
                                }
                            )

                if claimed_uom and activity_row and activity_row.get("uom"):
                    planned_uom = activity_row["uom"]
                    if (
                        claimed_uom.strip().lower()
                        != planned_uom.strip().lower()
                    ):
                        validation_issues.append(
                            {
                                "issue_id": str(uuid.uuid4()),
                                "event_id": event_id,
                                "rule_code": "VAL_UOM_MISMATCH",
                                "severity": "WARNING",
                                "description": f"Claimed UOM '{claimed_uom}' does not match planned UOM '{planned_uom}'.",
                            }
                        )
            else:
                # CUMULATIVE_PCT
                if claimed_pct is not None and claimed_pct > 100.0:
                    validation_issues.append(
                        {
                            "issue_id": str(uuid.uuid4()),
                            "event_id": event_id,
                            "rule_code": "VAL_OVER_100",
                            "severity": "ERROR",
                            "description": f"Claimed progress percentage ({claimed_pct}%) exceeds 100%.",
                        }
                    )

                # Conflict Detection (CUMULATIVE_PCT only, 7 days window, abs diff > 10, excluding REJECTED)
                if matched_activity_id and event_date:
                    other_events = conn.execute(
                        """
                        SELECT event_id, claimed_pct, event_date FROM execution_events
                        WHERE schedule_id = %s
                          AND matched_activity_id = %s
                          AND event_id != %s
                          AND status IN ('APPROVED', 'EDITED', 'HOLD', 'VALIDATED', 'REVIEW_REQUIRED')
                          AND ABS(event_date - %s) <= 7
                        """,
                        (
                            schedule_id,
                            matched_activity_id,
                            event_id,
                            event_date,
                        ),
                    ).fetchall()

                    for other in other_events:
                        other_id = other["event_id"]
                        val_a = claimed_pct or 0.0
                        val_b = other["claimed_pct"] or 0.0
                        variance_pct = round(abs(val_a - val_b), 2)

                        if variance_pct > 10.0:
                            conflict_id = str(uuid.uuid4())
                            conflict_records_to_insert.append(
                                {
                                    "conflict_id": conflict_id,
                                    "schedule_id": schedule_id,
                                    "activity_id": matched_activity_id,
                                    "reporting_period": event_date,
                                    "event_id_a": event_id,
                                    "event_id_b": other_id,
                                    "value_a": val_a,
                                    "value_b": val_b,
                                    "variance_pct": variance_pct,
                                    "status": "OPEN",
                                }
                            )
                            validation_issues.append(
                                {
                                    "issue_id": str(uuid.uuid4()),
                                    "event_id": event_id,
                                    "rule_code": "CONFLICT_DETECTED",
                                    "severity": "HIGH",
                                    "description": f"Conflicting progress claim with event '{other_id}' (disagreement {variance_pct}% > 10%).",
                                }
                            )

            # 3. VAL_NEGATIVE
            if claimed_pct is not None and claimed_pct < 0.0:
                validation_issues.append(
                    {
                        "issue_id": str(uuid.uuid4()),
                        "event_id": event_id,
                        "rule_code": "VAL_NEGATIVE",
                        "severity": "ERROR",
                        "description": f"Claimed progress percentage ({claimed_pct}%) cannot be negative.",
                    }
                )

            # 4. VAL_OUT_OF_SEQUENCE (ACTUAL_START)
            if event_type == "ACTUAL_START" and matched_activity_id:
                pred_rows = conn.execute(
                    """
                    SELECT predecessor_activity_id FROM schedule_dependencies
                    WHERE schedule_id = %s AND successor_activity_id = %s
                    """,
                    (schedule_id, matched_activity_id),
                ).fetchall()

                for pred in pred_rows:
                    pred_id = pred["predecessor_activity_id"]
                    pred_actual = conn.execute(
                        """
                        SELECT actual_pct_complete FROM approved_actuals
                        WHERE schedule_id = %s AND activity_id = %s
                        """,
                        (schedule_id, pred_id),
                    ).fetchone()

                    pred_pct = (
                        pred_actual["actual_pct_complete"]
                        if (
                            pred_actual
                            and pred_actual.get("actual_pct_complete")
                            is not None
                        )
                        else 0.0
                    )
                    if pred_pct < 100.0:
                        validation_issues.append(
                            {
                                "issue_id": str(uuid.uuid4()),
                                "event_id": event_id,
                                "rule_code": "VAL_OUT_OF_SEQUENCE",
                                "severity": "WARNING",
                                "description": f"Predecessor activity '{pred_id}' progress is {pred_pct}% (< 100%).",
                            }
                        )

            # 5. VAL_REOPENED_COMPLETED_ACTIVITY
            if (
                claim_mode == "CUMULATIVE_PCT"
                and claimed_pct is not None
                and claimed_pct < 100.0
                and matched_activity_id
            ):
                actual_row = conn.execute(
                    """
                    SELECT actual_finish FROM approved_actuals
                    WHERE schedule_id = %s AND activity_id = %s
                    """,
                    (schedule_id, matched_activity_id),
                ).fetchone()

                if actual_row and actual_row.get("actual_finish") is not None:
                    validation_issues.append(
                        {
                            "issue_id": str(uuid.uuid4()),
                            "event_id": event_id,
                            "rule_code": "VAL_REOPENED_COMPLETED_ACTIVITY",
                            "severity": "ERROR",
                            "description": "Claim reported for an activity that was already marked as completed.",
                        }
                    )

            # 6. VAL_EVIDENCE_MISMATCH
            if photo_path:
                if not os.path.exists(photo_path):
                    validation_issues.append(
                        {
                            "issue_id": str(uuid.uuid4()),
                            "event_id": event_id,
                            "rule_code": "VAL_EVIDENCE_MISMATCH",
                            "severity": "ERROR",
                            "description": f"Evidence photo file not found at path '{photo_path}'.",
                        }
                    )
                else:
                    exif_data = _parse_exif(photo_path)
                    if "datetime_original" in exif_data:
                        try:
                            raw_dt = (
                                exif_data["datetime_original"]
                                .split()[0]
                                .replace(":", "-")
                            )
                            exif_date = datetime.strptime(
                                raw_dt, "%Y-%m-%d"
                            ).date()
                            if (
                                event_date
                                and abs((exif_date - event_date).days) > 2
                            ):
                                validation_issues.append(
                                    {
                                        "issue_id": str(uuid.uuid4()),
                                        "event_id": event_id,
                                        "rule_code": "VAL_EVIDENCE_MISMATCH",
                                        "severity": "WARNING",
                                        "description": f"Photo EXIF date ({exif_date}) differs from event date ({event_date}) by > 2 days.",
                                    }
                                )
                        except Exception:
                            pass

                    site_lat = float(os.getenv("PROJECT_SITE_LAT", "27.4728"))
                    site_lon = float(os.getenv("PROJECT_SITE_LON", "95.3547"))
                    site_radius = float(
                        os.getenv("PROJECT_SITE_RADIUS_KM", "5.0")
                    )

                    if exif_data.get("has_gps"):
                        photo_lat = exif_data["lat"]
                        photo_lon = exif_data["lon"]
                        dist = haversine_distance_km(
                            photo_lat, photo_lon, site_lat, site_lon
                        )
                        if dist > site_radius:
                            validation_issues.append(
                                {
                                    "issue_id": str(uuid.uuid4()),
                                    "event_id": event_id,
                                    "rule_code": "VAL_EVIDENCE_MISMATCH",
                                    "severity": "WARNING",
                                    "description": f"Photo GPS location is {round(dist, 2)}km from project site (exceeds {site_radius}km radius).",
                                }
                            )

            # Candidate Match check
            match_row = conn.execute(
                """
                SELECT match_tier FROM candidate_matches
                WHERE event_id = %s AND rank_order = 1
                """,
                (event_id,),
            ).fetchone()
            is_unmatched_tier = False
            if match_row and match_row.get("match_tier") in (
                "UNMATCHED",
                "HARD_MISMATCH",
            ):
                is_unmatched_tier = True

            # Determine Final Status
            has_any_flags = (
                len(validation_issues) > 0 or len(conflict_records_to_insert) > 0
            )

            new_status = "VALIDATED"
            if (
                incoming_status == "UNMATCHED"
                or is_unmatched_tier
                or has_any_flags
            ):
                new_status = "REVIEW_REQUIRED"

            # Update Database Records
            conn.execute(
                """
                UPDATE execution_events
                SET status = %s, claimed_pct = %s
                WHERE event_id = %s
                """,
                (new_status, claimed_pct, event_id),
            )

            conn.execute(
                "DELETE FROM validation_issues WHERE event_id = %s",
                (event_id,),
            )

            conn.execute(
                "DELETE FROM conflict_records WHERE event_id_a = %s OR event_id_b = %s",
                (event_id, event_id),
            )

            for issue in validation_issues:
                conn.execute(
                    """
                    INSERT INTO validation_issues (issue_id, event_id, rule_code, severity, description)
                    VALUES (%s, %s, %s, %s, %s)
                    """,
                    (
                        issue["issue_id"],
                        issue["event_id"],
                        issue["rule_code"],
                        issue["severity"],
                        issue["description"],
                    ),
                )

            for conf in conflict_records_to_insert:
                conn.execute(
                    """
                    INSERT INTO conflict_records (
                        conflict_id, schedule_id, activity_id, reporting_period,
                        event_id_a, event_id_b, value_a, value_b, variance_pct, status
                    )
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                    """,
                    (
                        conf["conflict_id"],
                        conf["schedule_id"],
                        conf["activity_id"],
                        conf["reporting_period"],
                        conf["event_id_a"],
                        conf["event_id_b"],
                        conf["value_a"],
                        conf["value_b"],
                        conf["variance_pct"],
                        conf["status"],
                    ),
                )

            after_state = dict(before_state)
            after_state["status"] = new_status
            after_state["claimed_pct"] = claimed_pct

            # Transactional Audit Log with actor SYSTEM:M4
            write_audit_log(
                entity_type="execution_events",
                entity_id=event_id,
                action="CHECK_CLAIM",
                actor_id=SYSTEM_ACTOR_M4,
                before_state=before_state,
                after_state=after_state,
            )

            return {
                "event_id": event_id,
                "status": new_status,
                "claimed_pct": claimed_pct,
                "validation_issues": validation_issues,
                "conflicts": conflict_records_to_insert,
            }


@router.get("/claims/{event_id}/conflicts", dependencies=_supervisor_dep)
def get_claim_conflicts(event_id: str):
    with get_connection() as conn:
        rows = conn.execute(
            """
            SELECT * FROM conflict_records
            WHERE event_id_a = %s OR event_id_b = %s
            ORDER BY reporting_period DESC
            """,
            (event_id, event_id),
        ).fetchall()
        return {"event_id": event_id, "conflicts": [dict(r) for r in rows]}


@router.get("/claims/{event_id}/validation", dependencies=_supervisor_dep)
def get_claim_validation(event_id: str):
    with get_connection() as conn:
        rows = conn.execute(
            """
            SELECT * FROM validation_issues
            WHERE event_id = %s
            """,
            (event_id,),
        ).fetchall()
        return {
            "event_id": event_id,
            "validation_issues": [dict(r) for r in rows],
        }


@router.get("/activities/{activity_id}/rollup", dependencies=_supervisor_dep)
def get_activity_rollup(activity_id: str, schedule_id: Optional[str] = None):
    with get_connection() as conn:
        if not schedule_id:
            sched_row = conn.execute(
                "SELECT schedule_id FROM schedules ORDER BY created_at DESC LIMIT 1"
            ).fetchone()
            schedule_id = sched_row["schedule_id"] if sched_row else None

        planned_quantity = 0.0
        if schedule_id:
            act_row = conn.execute(
                """
                SELECT planned_quantity, uom FROM schedule_activities
                WHERE schedule_id = %s AND activity_id = %s
                """,
                (schedule_id, activity_id),
            ).fetchone()
            if act_row:
                planned_quantity = act_row.get("planned_quantity") or 0.0

        # Sum APPROVED/EDITED incremental quantities using latest decision
        qty_row = conn.execute(
            """
            SELECT COALESCE(SUM(COALESCE(pd.approved_qty, ee.claimed_quantity)), 0.0) AS total_approved_qty
            FROM execution_events ee
            JOIN planner_decisions pd ON pd.event_id = ee.event_id
            WHERE (%s IS NULL OR ee.schedule_id = %s)
              AND ee.matched_activity_id = %s
              AND pd.action IN ('APPROVE', 'EDIT')
              AND pd.decision_id = (
                  SELECT decision_id FROM planner_decisions pd2
                  WHERE pd2.event_id = ee.event_id
                  ORDER BY pd2.decided_at DESC LIMIT 1
              )
            """,
            (schedule_id, schedule_id, activity_id),
        ).fetchone()

        sum_qty = qty_row["total_approved_qty"] if qty_row else 0.0
        derived_pct = 0.0
        if planned_quantity > 0:
            derived_pct = min(
                round((sum_qty / planned_quantity) * 100.0, 2), 100.0
            )

        # Full claim history for context
        claims_rows = conn.execute(
            """
            SELECT ee.*, pd.action AS latest_decision_action, pd.approved_qty
            FROM execution_events ee
            LEFT JOIN planner_decisions pd ON pd.event_id = ee.event_id
              AND pd.decision_id = (
                  SELECT decision_id FROM planner_decisions pd2
                  WHERE pd2.event_id = ee.event_id
                  ORDER BY pd2.decided_at DESC LIMIT 1
              )
            WHERE (%s IS NULL OR ee.schedule_id = %s)
              AND (ee.matched_activity_id = %s OR ee.reported_activity_id = %s)
            ORDER BY ee.event_date DESC, ee.created_at DESC
            """,
            (schedule_id, schedule_id, activity_id, activity_id),
        ).fetchall()

        return {
            "activity_id": activity_id,
            "schedule_id": schedule_id,
            "planned_quantity": planned_quantity,
            "summed_approved_quantity": sum_qty,
            "derived_pct_complete": derived_pct,
            "claim_history": [dict(r) for r in claims_rows],
        }


@router.get("/audit/{entity_id}", dependencies=_supervisor_dep)
def get_audit(entity_id: str):
    return get_audit_trail(entity_id)


@router.get("/alerts/silent-activities", dependencies=_supervisor_dep)
@router.get("/claims/silent-activities", dependencies=_supervisor_dep)
@router.get("/claims/checks/silent-activities", dependencies=_supervisor_dep)
def get_silent_activities(schedule_id: Optional[str] = None):
    with get_connection() as conn:
        query = """
            SELECT sa.activity_id, sa.schedule_id, sa.activity_name, sa.discipline,
                   sa.location, sa.planned_start, sa.planned_finish, sa.baseline_pct_complete
            FROM schedule_activities sa
            LEFT JOIN approved_actuals aa ON sa.schedule_id = aa.schedule_id AND sa.activity_id = aa.activity_id
            WHERE sa.planned_start <= CURRENT_DATE
              AND (aa.actual_pct_complete IS NULL OR aa.actual_pct_complete < 100.0)
              AND NOT EXISTS (
                  SELECT 1 FROM execution_events ee
                  WHERE ee.schedule_id = sa.schedule_id
                    AND ee.matched_activity_id = sa.activity_id
                    AND ee.created_at >= CURRENT_DATE - INTERVAL '3 days'
              )
        """
        params = []
        if schedule_id:
            query += " AND sa.schedule_id = %s"
            params.append(schedule_id)

        query += " ORDER BY sa.planned_start ASC"

        rows = conn.execute(query, params).fetchall()
        return {"silent_activities": [dict(r) for r in rows]}
