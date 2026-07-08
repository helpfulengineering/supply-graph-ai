"""RED metrics loading and threshold judgement for the harness."""

from __future__ import annotations

import json
import urllib.error
import urllib.request
from typing import Any


def _latency_ms(raw: float) -> float:
    """Normalize latency to milliseconds.

    MetricsTracker stores processing times in seconds; API JSON keys are
    suffixed ``_ms`` but often carry the same second-scale values.
    """
    if raw <= 0:
        return 0.0
    return raw * 1000.0 if raw < 100 else raw


def _error_rate(endpoint: dict[str, Any]) -> float:
    total = int(endpoint.get("total_requests") or 0)
    if total <= 0:
        return 0.0
    failed = endpoint.get("failed_requests")
    if failed is not None:
        return float(failed) / total
    success_rate = float(endpoint.get("success_rate") or 100.0)
    return max(0.0, min(1.0, (100.0 - success_rate) / 100.0))


def judge_endpoints(
    endpoints: dict[str, dict[str, Any]],
    *,
    error_rate_warn: float,
    p95_ms_warn: float,
    min_requests: int = 1,
) -> list[dict[str, Any]]:
    """Return per-endpoint threshold breaches (empty when all clean)."""
    breaches: list[dict[str, Any]] = []
    for key, endpoint in sorted(endpoints.items()):
        total = int(endpoint.get("total_requests") or 0)
        if total < min_requests:
            continue
        err = _error_rate(endpoint)
        p95_raw = endpoint.get("p95_processing_time_ms")
        if p95_raw is None:
            p95_raw = endpoint.get("avg_processing_time_ms", 0.0)
        p95_ms = _latency_ms(float(p95_raw or 0.0))
        issues: list[str] = []
        if err > error_rate_warn:
            issues.append("error_rate")
        if p95_ms > p95_ms_warn:
            issues.append("latency")
        if issues:
            breaches.append(
                {
                    "endpoint": key,
                    "total_requests": total,
                    "error_rate": round(err, 4),
                    "p95_ms": round(p95_ms, 2),
                    "issues": issues,
                }
            )
    return breaches


def load_metrics_in_process() -> dict[str, Any]:
    """Detailed metrics from the in-process MetricsTracker."""
    from src.core.errors.metrics import get_metrics_tracker

    tracker = get_metrics_tracker()
    brief = tracker.get_endpoint_metrics()
    endpoints: dict[str, dict[str, Any]] = {}
    for key in brief:
        method, path = key.split(" ", 1)
        full = tracker.get_endpoint_metrics(method=method, path=path)
        if full:
            endpoints[key] = full
    return {"summary": tracker.get_summary(), "endpoints": endpoints}


def load_metrics_http(
    base_url: str,
    metrics_path: str,
    *,
    timeout: float = 10.0,
) -> dict[str, Any]:
    """Fetch detailed metrics JSON from a running API."""
    url = f"{base_url.rstrip('/')}{metrics_path}?summary=false&format=json"
    req = urllib.request.Request(url, headers={"Accept": "application/json"})
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            body = resp.read().decode("utf-8")
    except urllib.error.URLError as exc:
        raise ConnectionError(f"Could not fetch metrics from {url}: {exc}") from exc
    payload = json.loads(body)
    if not isinstance(payload, dict):
        raise ValueError(f"Unexpected metrics payload type: {type(payload)}")
    return payload


def load_metrics(
    *,
    source: str,
    base_url: str,
    metrics_path: str,
) -> dict[str, Any]:
    if source == "http":
        return load_metrics_http(base_url, metrics_path)
    if source == "in-process":
        return load_metrics_in_process()
    raise ValueError(f"Unknown RED metrics source: {source!r}")
