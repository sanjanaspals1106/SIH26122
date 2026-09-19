import logging
import os
from datetime import date, datetime
from typing import Any, Dict, List, Optional, Union

import httpx

from backend.routers.export import PMISAdapter

logger = logging.getLogger(__name__)


def _format_iso_date(val: Any) -> Optional[str]:
    if val is None:
        return None
    if isinstance(val, (datetime, date)):
        return val.strftime("%Y-%m-%d")
    s = str(val).strip()
    if not s:
        return None
    return s[:10]


class P6RestAdapter(PMISAdapter):
    """
    Canonical P6 EPPM REST API write-back adapter per PRD v5 Feature 27 and Appendix B.
    """

    def __init__(
        self,
        base_url: Optional[str] = None,
        timeout: float = 5.0,
        http_client: Optional[Any] = None,
    ):
        self.base_url = (base_url if base_url is not None else os.getenv("P6_BASE_URL", "")).strip()
        self.timeout = timeout
        self.http_client = http_client

    def format_payload(
        self,
        activity_id: str,
        actual_start: Optional[Union[date, str]] = None,
        actual_finish: Optional[Union[date, str]] = None,
        actual_pct_complete: Optional[float] = None,
        actual_quantity: Optional[float] = None,
    ) -> Dict[str, Any]:
        """
        Produce canonical P6 payload:
        {
            "Id": activity_id,
            "StartDate": "YYYY-MM-DD",
            "FinishDate": "YYYY-MM-DD",
            "PercentComplete": float
        }
        Quantity is intentionally dropped.
        ActualDuration is strictly excluded.
        """
        payload: Dict[str, Any] = {
            "Id": str(activity_id),
        }
        start_str = _format_iso_date(actual_start)
        if start_str is not None:
            payload["StartDate"] = start_str

        finish_str = _format_iso_date(actual_finish)
        if finish_str is not None:
            payload["FinishDate"] = finish_str

        if actual_pct_complete is not None:
            try:
                payload["PercentComplete"] = float(actual_pct_complete)
            except (ValueError, TypeError):
                pass

        return payload

    def push_actual(
        self,
        activity_id: str,
        actual_start: Optional[Union[date, str]] = None,
        actual_finish: Optional[Union[date, str]] = None,
        actual_pct_complete: Optional[float] = None,
        actual_quantity: Optional[float] = None,
    ) -> bool:
        """
        Pushes actuals to P6 EPPM REST endpoint.
        Option A: If base_url is unset/empty, returns False without raising.
        """
        if not self.base_url:
            logger.info("P6_BASE_URL is not configured; P6 actuals push skipped.")
            return False

        payload = self.format_payload(
            activity_id=activity_id,
            actual_start=actual_start,
            actual_finish=actual_finish,
            actual_pct_complete=actual_pct_complete,
            actual_quantity=actual_quantity,
        )

        url = f"{self.base_url.rstrip('/')}/activities/{activity_id}"

        try:
            if self.http_client is not None:
                resp = self.http_client.post(url, json=payload, timeout=self.timeout)
                return 200 <= resp.status_code < 300
            else:
                with httpx.Client(timeout=self.timeout) as client:
                    resp = client.post(url, json=payload)
                    return 200 <= resp.status_code < 300
        except Exception as e:
            logger.warning("P6 REST push failed for activity '%s' (non-blocking): %s", activity_id, e)
            return False


_default_p6_adapter: Optional[P6RestAdapter] = None


def get_default_p6_adapter() -> P6RestAdapter:
    global _default_p6_adapter
    if _default_p6_adapter is None:
        _default_p6_adapter = P6RestAdapter()
    return _default_p6_adapter


def set_default_p6_adapter(adapter: Optional[P6RestAdapter]) -> None:
    global _default_p6_adapter
    _default_p6_adapter = adapter


def trigger_p6_actual_push(
    actual: dict,
    adapter: Optional[P6RestAdapter] = None,
) -> bool:
    """
    Non-blocking helper to trigger P6 actual push post-commit.
    """
    if not actual:
        return False
    active_adapter = adapter or get_default_p6_adapter()
    return active_adapter.push_actual(
        activity_id=actual.get("activity_id", ""),
        actual_start=actual.get("actual_start"),
        actual_finish=actual.get("actual_finish"),
        actual_pct_complete=actual.get("actual_pct_complete"),
        actual_quantity=actual.get("actual_quantity"),
    )
