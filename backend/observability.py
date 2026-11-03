"""In-process operational metrics that intentionally exclude request payloads."""

from __future__ import annotations

from collections import Counter
from threading import Lock
from time import monotonic
from typing import Any

STARTED_AT = monotonic()
_LOCK = Lock()
_REQUEST_COUNT = 0
_TOTAL_DURATION_MS = 0.0
_STATUS_CLASSES: Counter[str] = Counter()
_ENDPOINTS: Counter[str] = Counter()


def record_request(method: str, path: str, status_code: int, duration_ms: float) -> None:
    """Record bounded request metadata for the current process."""
    global _REQUEST_COUNT, _TOTAL_DURATION_MS
    with _LOCK:
        _REQUEST_COUNT += 1
        _TOTAL_DURATION_MS += duration_ms
        _STATUS_CLASSES[f"{status_code // 100}xx"] += 1
        _ENDPOINTS[f"{method} {path}"] += 1


def snapshot() -> dict[str, Any]:
    """Return a copy of operational metrics safe for an internal dashboard."""
    with _LOCK:
        request_count = _REQUEST_COUNT
        total_duration_ms = _TOTAL_DURATION_MS
        return {
            "uptime_seconds": round(monotonic() - STARTED_AT, 2),
            "request_count": request_count,
            "average_duration_ms": (
                round(total_duration_ms / request_count, 2) if request_count else 0.0
            ),
            "status_classes": dict(_STATUS_CLASSES),
            "endpoints": dict(_ENDPOINTS),
        }
