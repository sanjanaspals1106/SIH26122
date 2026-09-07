"""M1 baseline schedule ingestion: parsing, validation, normalization.

Turns raw baseline-schedule CSV text into canonical ScheduleActivity records
(backend.shared.schemas.ScheduleActivity), the representation later phases
persist to PostgreSQL and index in FAISS.

Column mapping
--------------
sample_data/schedule.csv (the only M1-owned sample file) is currently empty,
so the source column layout below was derived by inspecting the read-only
reference export at sample_data/progress-report-csv/sih26122_canonical_schedule.csv
(M6-owned; never modified, copied, or used as M1 sample data). Its observed
headers were:

    L1, L2, L3, L4, L5 Activity ID, L6 Task ID, Discipline, Activity, Unit,
    Planned Qty, Baseline Start, Baseline Finish, Prior Actual, Today Actual,
    Cumulative Actual, Progress Pct, Status

Mapping to the canonical ScheduleActivity fields:

    L6 Task ID          -> activity_id           (finest-grain code, unique per row)
    L5 Activity ID       -> wbs_code              (WBS/activity grouping code)
    Activity              -> activity_name
    Discipline            -> discipline           (passed through as-is; not
                                                    forced into the PRD's six
                                                    conceptual disciplines, since
                                                    at least one observed value
                                                    ("Mechanical") has no
                                                    unambiguous mapping onto that
                                                    list)
    Unit                  -> uom
    Planned Qty            -> planned_quantity
    Baseline Start          -> planned_start
    Baseline Finish          -> planned_finish
    L1, L2                    -> location (joined "L1 / L2"; these are the
                                            physical area / tie-in point levels
                                            of the WBS hierarchy)

Deliberately NOT mapped:
    L3, L4                        - work-category WBS levels that overlap with
                                     discipline/activity_name; no canonical
                                     field exists to hold them without
                                     inventing one.
    Prior/Today/Cumulative Actual,
    Progress Pct, Status          - actual/executed progress data, owned by
                                     later M1-adjacent phases (event/matching),
                                     not baseline schedule ingestion.
    asset_tag                     - no source column observed; stays None
                                     (Optional in the canonical model).
    baseline_pct_complete         - no source column observed; falls back to
                                     the default already declared on
                                     ScheduleActivity (0.0). A "baseline pct
                                     complete" column is still recognized if a
                                     future source provides one (see
                                     _BASELINE_PCT_COLUMN).
    schedule_id                   - not a per-row column; it identifies the
                                     import batch and is supplied by the
                                     caller of parse_schedule_csv().
"""

from __future__ import annotations

import csv
import io
from dataclasses import dataclass, field
from datetime import date
from typing import Optional

from pydantic import ValidationError

from backend.shared.schemas import ScheduleActivity


class ScheduleValidationError(Exception):
    """A single invalid field on a single schedule row.

    Carries enough context (row number, activity_id if known, field name)
    for the caller to report an actionable error rather than a bare
    exception message.
    """

    def __init__(
        self,
        row_number: int,
        field_name: str,
        message: str,
        activity_id: Optional[str] = None,
    ) -> None:
        self.row_number = row_number
        self.field_name = field_name
        self.message = message
        self.activity_id = activity_id
        super().__init__(self.describe())

    def describe(self) -> str:
        location = f"row {self.row_number}"
        if self.activity_id:
            location += f" (activity_id={self.activity_id!r})"
        return f"{location}: {self.field_name}: {self.message}"


@dataclass
class ScheduleParseResult:
    """Outcome of parsing one baseline schedule CSV."""

    schedule_id: str
    activities: list[ScheduleActivity] = field(default_factory=list)
    errors: list[ScheduleValidationError] = field(default_factory=list)

    @property
    def is_valid(self) -> bool:
        return not self.errors


# Source column names are matched case-insensitively with collapsed
# whitespace (see _normalize_key), so this map uses lower-cased keys.
_ACTIVITY_ID_COLUMN = "l6 task id"
_WBS_CODE_COLUMN = "l5 activity id"
_ACTIVITY_NAME_COLUMN = "activity"
_DISCIPLINE_COLUMN = "discipline"
_UOM_COLUMN = "unit"
_PLANNED_QUANTITY_COLUMN = "planned qty"
_PLANNED_START_COLUMN = "baseline start"
_PLANNED_FINISH_COLUMN = "baseline finish"
_LOCATION_COLUMNS = ("l1", "l2")

# Not present in the observed reference export; recognized for forward
# compatibility if a future source provides a genuine baseline S-curve figure.
_BASELINE_PCT_COLUMN = "baseline pct complete"


def _normalize_key(key: str) -> str:
    return " ".join(key.strip().lower().split())


def _clean(value: Optional[str]) -> Optional[str]:
    """Strip whitespace and turn empty strings into None. Never invents data."""
    if value is None:
        return None
    stripped = value.strip()
    return stripped or None


def _parse_date(
    raw: Optional[str],
    row_number: int,
    field_name: str,
    activity_id: str,
    errors: list[ScheduleValidationError],
) -> Optional[date]:
    cleaned = _clean(raw)
    if cleaned is None:
        errors.append(
            ScheduleValidationError(row_number, field_name, "is required", activity_id)
        )
        return None
    try:
        return date.fromisoformat(cleaned)
    except ValueError:
        errors.append(
            ScheduleValidationError(
                row_number,
                field_name,
                f"could not parse date {cleaned!r} (expected YYYY-MM-DD)",
                activity_id,
            )
        )
        return None


def _parse_float(
    raw: Optional[str],
    row_number: int,
    field_name: str,
    activity_id: str,
    errors: list[ScheduleValidationError],
) -> Optional[float]:
    cleaned = _clean(raw)
    if cleaned is None:
        return None
    try:
        return float(cleaned)
    except ValueError:
        errors.append(
            ScheduleValidationError(
                row_number, field_name, f"is not numeric: {cleaned!r}", activity_id
            )
        )
        return None


def _build_location(
    row: dict[str, Optional[str]],
    row_number: int,
    activity_id: str,
    errors: list[ScheduleValidationError],
) -> Optional[str]:
    parts = [_clean(row.get(column)) for column in _LOCATION_COLUMNS]
    parts = [part for part in parts if part]
    if not parts:
        errors.append(
            ScheduleValidationError(
                row_number,
                "location",
                f"is required (no value in source columns {_LOCATION_COLUMNS})",
                activity_id,
            )
        )
        return None
    return " / ".join(parts)


def parse_schedule_csv(csv_text: str, schedule_id: str) -> ScheduleParseResult:
    """Parse baseline schedule CSV text into canonical ScheduleActivity records.

    Every row is validated independently; a row with any invalid field is
    excluded from `activities` and its errors are collected in `errors`
    rather than raising, so a single malformed row does not abort ingestion
    of the rest of the schedule.
    """
    if not schedule_id or not schedule_id.strip():
        raise ValueError("schedule_id is required to parse a schedule")

    reader = csv.DictReader(io.StringIO(csv_text))
    if not reader.fieldnames:
        return ScheduleParseResult(
            schedule_id=schedule_id,
            errors=[ScheduleValidationError(1, "header", "CSV has no header row")],
        )

    activities: list[ScheduleActivity] = []
    errors: list[ScheduleValidationError] = []
    first_seen_at: dict[str, int] = {}

    for row_number, raw_row in enumerate(reader, start=2):  # header is row 1
        row = {
            _normalize_key(key): value
            for key, value in raw_row.items()
            if key is not None
        }

        activity_id = _clean(row.get(_ACTIVITY_ID_COLUMN))
        if not activity_id:
            errors.append(
                ScheduleValidationError(
                    row_number, "activity_id", "is required and cannot be empty"
                )
            )
            continue

        if activity_id in first_seen_at:
            errors.append(
                ScheduleValidationError(
                    row_number,
                    "activity_id",
                    f"duplicate activity_id (first seen at row {first_seen_at[activity_id]})",
                    activity_id,
                )
            )
            continue
        first_seen_at[activity_id] = row_number

        row_errors: list[ScheduleValidationError] = []

        activity_name = _clean(row.get(_ACTIVITY_NAME_COLUMN))
        if not activity_name:
            row_errors.append(
                ScheduleValidationError(row_number, "activity_name", "is required", activity_id)
            )

        discipline = _clean(row.get(_DISCIPLINE_COLUMN))
        if not discipline:
            row_errors.append(
                ScheduleValidationError(row_number, "discipline", "is required", activity_id)
            )

        location = _build_location(row, row_number, activity_id, row_errors)

        wbs_code = _clean(row.get(_WBS_CODE_COLUMN))
        uom = _clean(row.get(_UOM_COLUMN))

        planned_start = _parse_date(
            row.get(_PLANNED_START_COLUMN), row_number, "planned_start", activity_id, row_errors
        )
        planned_finish = _parse_date(
            row.get(_PLANNED_FINISH_COLUMN), row_number, "planned_finish", activity_id, row_errors
        )
        if planned_start is not None and planned_finish is not None and planned_start > planned_finish:
            row_errors.append(
                ScheduleValidationError(
                    row_number,
                    "planned_finish",
                    f"planned_finish ({planned_finish}) is before planned_start ({planned_start})",
                    activity_id,
                )
            )

        planned_quantity = _parse_float(
            row.get(_PLANNED_QUANTITY_COLUMN), row_number, "planned_quantity", activity_id, row_errors
        )

        baseline_pct_raw = _clean(row.get(_BASELINE_PCT_COLUMN))
        if baseline_pct_raw is None:
            baseline_pct_complete = ScheduleActivity.model_fields["baseline_pct_complete"].default
        else:
            parsed_pct = _parse_float(
                baseline_pct_raw, row_number, "baseline_pct_complete", activity_id, row_errors
            )
            if parsed_pct is not None and not (0.0 <= parsed_pct <= 100.0):
                row_errors.append(
                    ScheduleValidationError(
                        row_number,
                        "baseline_pct_complete",
                        f"must be between 0 and 100, got {parsed_pct}",
                        activity_id,
                    )
                )
            baseline_pct_complete = parsed_pct if parsed_pct is not None else 0.0

        if row_errors:
            errors.extend(row_errors)
            continue

        try:
            activity = ScheduleActivity(
                schedule_id=schedule_id,
                activity_id=activity_id,
                activity_name=activity_name,
                wbs_code=wbs_code,
                discipline=discipline,
                location=location,
                asset_tag=None,
                planned_start=planned_start,
                planned_finish=planned_finish,
                planned_quantity=planned_quantity,
                uom=uom,
                baseline_pct_complete=baseline_pct_complete,
            )
        except ValidationError as exc:
            for detail in exc.errors():
                field_name = ".".join(str(part) for part in detail["loc"])
                errors.append(
                    ScheduleValidationError(row_number, field_name, detail["msg"], activity_id)
                )
            continue

        activities.append(activity)

    return ScheduleParseResult(schedule_id=schedule_id, activities=activities, errors=errors)
