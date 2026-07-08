"""HTTP helpers for production probes against a live OHM API."""

from __future__ import annotations

import json
import os
import time
import urllib.error
import urllib.request
from dataclasses import dataclass, field
from typing import Any, Mapping, Optional


@dataclass
class HttpResult:
    """One HTTP round-trip with timing and parsed JSON when possible."""

    method: str
    url: str
    status: int
    duration_ms: float
    headers: dict[str, str] = field(default_factory=dict)
    body: Any = None
    raw_text: str = ""
    error: Optional[str] = None

    @property
    def ok(self) -> bool:
        return self.error is None and 200 <= self.status < 300


def _auth_headers() -> dict[str, str]:
    """Optional API key from OHM_API_KEY (same env as deploy clients)."""
    key = os.environ.get("OHM_API_KEY") or os.environ.get("API_KEY")
    if not key:
        return {}
    return {"Authorization": f"Bearer {key}"}


def api_url(base_url: str, api_path_prefix: str, path: str) -> str:
    """Build a versioned API URL. ``path`` is e.g. ``/okh`` or ``/match``."""
    base = base_url.rstrip("/")
    prefix = api_path_prefix.rstrip("/")
    if not path.startswith("/"):
        path = f"/{path}"
    return f"{base}{prefix}{path}"


def check_api_reachable(health_url: str, *, timeout: float = 5.0) -> bool:
    req = urllib.request.Request(health_url, method="GET")
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return 200 <= resp.status < 300
    except (urllib.error.URLError, TimeoutError, OSError):
        return False


def api_request(
    *,
    base_url: str,
    api_path_prefix: str,
    path: str,
    method: str = "GET",
    json_body: Optional[Mapping[str, Any]] = None,
    timeout: float = 120.0,
    extra_headers: Optional[dict[str, str]] = None,
) -> HttpResult:
    """Issue one request to the OHM API and capture status, timing, and body."""
    url = api_url(base_url, api_path_prefix, path)
    headers = {
        "Accept": "application/json",
        **_auth_headers(),
        **(extra_headers or {}),
    }
    data: bytes | None = None
    if json_body is not None:
        headers["Content-Type"] = "application/json"
        data = json.dumps(dict(json_body)).encode("utf-8")

    req = urllib.request.Request(url, data=data, headers=headers, method=method.upper())
    t0 = time.perf_counter()
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            raw = resp.read().decode("utf-8", errors="replace")
            duration_ms = (time.perf_counter() - t0) * 1000.0
            resp_headers = {k.lower(): v for k, v in resp.headers.items()}
            parsed: Any = None
            if raw:
                try:
                    parsed = json.loads(raw)
                except json.JSONDecodeError:
                    parsed = None
            return HttpResult(
                method=method.upper(),
                url=url,
                status=resp.status,
                duration_ms=duration_ms,
                headers=resp_headers,
                body=parsed,
                raw_text=raw,
            )
    except urllib.error.HTTPError as exc:
        raw = exc.read().decode("utf-8", errors="replace")
        duration_ms = (time.perf_counter() - t0) * 1000.0
        parsed: Any = None
        if raw:
            try:
                parsed = json.loads(raw)
            except json.JSONDecodeError:
                parsed = None
        return HttpResult(
            method=method.upper(),
            url=url,
            status=exc.code,
            duration_ms=duration_ms,
            headers={k.lower(): v for k, v in exc.headers.items()},
            body=parsed,
            raw_text=raw,
            error=str(exc),
        )
    except (urllib.error.URLError, TimeoutError, OSError) as exc:
        duration_ms = (time.perf_counter() - t0) * 1000.0
        return HttpResult(
            method=method.upper(),
            url=url,
            status=0,
            duration_ms=duration_ms,
            error=str(exc),
        )


def extract_detail(body: Any) -> str:
    """Best-effort error detail from OHM JSON error envelopes."""
    if not isinstance(body, dict):
        return ""
    for key in ("detail", "message", "error"):
        val = body.get(key)
        if isinstance(val, str) and val.strip():
            return val
    return json.dumps(body)[:500]
