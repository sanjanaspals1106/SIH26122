import csv
import io
import logging
from abc import ABC, abstractmethod
from datetime import date
from typing import Any, List, Optional, Union

from fastapi import APIRouter, Depends, HTTPException, Query, Response, status

from backend.shared.auth import UserProfile, require_role
from backend.shared.db import get_connection

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/export", tags=["export"])

CSV_HEADER = [
    "activity_id",
    "actual_start",
    "actual_finish",
    "actual_pct_complete",
    "actual_quantity",
]


class PMISAdapter(ABC):
    """
    Canonical PMIS adapter interface per PRD v5 Appendix B.
    """

    @abstractmethod
    def push_actual(
        self,
        activity_id: str,
        actual_start: Optional[Union[date, str]] = None,
        actual_finish: Optional[Union[date, str]] = None,
        actual_pct_complete: Optional[float] = None,
        actual_quantity: Optional[float] = None,
    ) -> bool:
        """
        Canonical 5-field write interface for PMIS integration.
        """
        pass


def format_csv_rows(rows: List[dict]) -> str:
    """
    Format approved actuals records into RFC 4180 compliant CSV text.
    Visible columns are strictly:
        activity_id, actual_start, actual_finish, actual_pct_complete, actual_quantity
    NULL values are rendered as empty strings.
    """
    output = io.StringIO()
    writer = csv.writer(output, lineterminator="\r\n")
    writer.writerow(CSV_HEADER)

    for row in rows:
        pct_val = row.get("actual_pct_complete")
        qty_val = row.get("actual_quantity")

        writer.writerow(
            [
                row.get("activity_id") if row.get("activity_id") is not None else "",
                str(row.get("actual_start")) if row.get("actual_start") is not None else "",
                str(row.get("actual_finish")) if row.get("actual_finish") is not None else "",
                f"{float(pct_val):g}" if pct_val is not None else "",
                f"{float(qty_val):g}" if qty_val is not None else "",
            ]
        )

    return output.getvalue()


class CSVExportAdapter(PMISAdapter):
    """
    Canonical CSV Export Adapter per PRD v5 Feature 26 and Appendix B.
    Receives approved actuals and outputs the canonical 5-column CSV format.
    """

    def __init__(self, output_file: Optional[str] = None):
        self.output_file = output_file
        self.records: List[dict] = []

    def push_actual(
        self,
        activity_id: str,
        actual_start: Optional[Union[date, str]] = None,
        actual_finish: Optional[Union[date, str]] = None,
        actual_pct_complete: Optional[float] = None,
        actual_quantity: Optional[float] = None,
    ) -> bool:
        """
        Accepts the canonical five fields and records them.
        """
        record = {
            "activity_id": str(activity_id),
            "actual_start": actual_start,
            "actual_finish": actual_finish,
            "actual_pct_complete": actual_pct_complete,
            "actual_quantity": actual_quantity,
        }
        self.records.append(record)

        if self.output_file:
            try:
                csv_content = self.generate_csv()
                with open(self.output_file, "w", encoding="utf-8", newline="") as f:
                    f.write(csv_content)
            except Exception as e:
                logger.warning(f"Failed to write CSV export to file '{self.output_file}': {e}")
                return False

        return True

    def generate_csv(self) -> str:
        """
        Generate CSV content from collected records.
        """
        return format_csv_rows(self.records)


def query_approved_actuals_for_export(
    conn: Optional[Any] = None,
    schedule_id: Optional[str] = None,
) -> List[dict]:
    """
    Query approved_actuals table for export with deterministic ordering.
    """
    query = """
        SELECT
            activity_id,
            actual_start,
            actual_finish,
            actual_pct_complete,
            actual_quantity
        FROM approved_actuals
    """
    params = []

    if schedule_id:
        query += " WHERE schedule_id = %s"
        params.append(schedule_id)

    query += " ORDER BY activity_id ASC"

    if conn is not None:
        rows = conn.execute(query, tuple(params) if params else None).fetchall()
        return [dict(r) for r in rows]

    with get_connection() as c:
        rows = c.execute(query, tuple(params) if params else None).fetchall()
        return [dict(r) for r in rows]


@router.get("/health")
def health():
    return {"router": "export", "status": "ok"}


@router.get("/csv")
def export_csv(
    schedule_id: Optional[str] = Query(
        default=None,
        description="Optional filter by schedule_id",
    ),
    current_user: UserProfile = Depends(require_role("SUPERVISOR")),
):
    """
    Export approved actuals to canonical 5-column CSV.
    Restricted to SUPERVISOR role.
    Columns: activity_id, actual_start, actual_finish, actual_pct_complete, actual_quantity
    """
    try:
        rows = query_approved_actuals_for_export(schedule_id=schedule_id)
    except Exception as e:
        logger.error(f"Error querying approved_actuals for CSV export: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to generate CSV export",
        )

    csv_data = format_csv_rows(rows)

    return Response(
        content=csv_data,
        media_type="text/csv; charset=utf-8",
        headers={
            "Content-Disposition": 'attachment; filename="approved_actuals.csv"',
            "Content-Type": "text/csv; charset=utf-8",
        },
    )
