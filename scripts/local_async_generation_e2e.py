#!/usr/bin/env python3
"""Localhost end-to-end checks for async generate-from-url + LLM credential gates.

Exercises the Compose stack (API + Redis + worker) without printing secrets.
Exit nonzero on the first failure.

Usage (API must already be healthy on :8001):

    uv run python scripts/local_async_generation_e2e.py
"""

from __future__ import annotations

import json
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

BASE = "http://localhost:8001/v1"
REPO = "https://github.com/blooop/Hello-World"


def _req(
    method: str,
    path: str,
    body: Optional[dict] = None,
    headers: Optional[Dict[str, str]] = None,
) -> Tuple[int, Any]:
    data = None if body is None else json.dumps(body).encode()
    hdrs = {"Accept": "application/json"}
    if body is not None:
        hdrs["Content-Type"] = "application/json"
    if headers:
        hdrs.update(headers)
    request = urllib.request.Request(
        f"{BASE}{path}", data=data, headers=hdrs, method=method
    )
    try:
        with urllib.request.urlopen(request, timeout=60) as resp:
            raw = resp.read().decode()
            return resp.status, json.loads(raw) if raw else None
    except urllib.error.HTTPError as exc:
        raw = exc.read().decode()
        try:
            parsed = json.loads(raw) if raw else None
        except json.JSONDecodeError:
            parsed = raw
        return exc.code, parsed


def _ok(label: str) -> None:
    print(f"  ✓ {label}")


def _fail(label: str, detail: Any = None) -> None:
    print(f"  ✗ {label}")
    if detail is not None:
        print(f"    {detail}")
    sys.exit(1)


def _load_api_key() -> Optional[str]:
    env_path = Path(__file__).resolve().parents[1] / ".env"
    if not env_path.is_file():
        return None
    for line in env_path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, _, value = line.partition("=")
        if key.strip() != "API_KEYS":
            continue
        value = value.strip().strip('"').strip("'")
        return value.split(",")[0].strip() or None
    return None


def check_readiness() -> None:
    print("→ readiness")
    request = urllib.request.Request("http://localhost:8001/health/readiness")
    with urllib.request.urlopen(request, timeout=30) as resp:
        body = json.loads(resp.read().decode())
        code = resp.status
    if code != 200 or body.get("status") != "ready":
        _fail("API readiness", body)
    _ok("API ready")


def check_openapi_surface() -> None:
    print("→ openapi surface")
    request = urllib.request.Request("http://localhost:8001/v1/openapi.json")
    with urllib.request.urlopen(request, timeout=30) as resp:
        paths = json.loads(resp.read().decode())["paths"]
    needed = [
        "/api/okh/generate-from-url/jobs",
        "/api/okh/generate-from-url/jobs/{job_id}",
        "/api/okh/generate-from-url/jobs/{job_id}/revoke",
        "/api/llm/credentials",
        "/api/llm/credentials/{provider}",
    ]
    missing = [p for p in needed if p not in paths]
    if missing:
        _fail("openapi paths missing", missing)
    _ok("job + credential routes present")


def check_job_progress_and_success() -> None:
    print("→ async job progress → SUCCESS")
    code, body = _req(
        "POST",
        "/api/okh/generate-from-url/jobs",
        {
            "urls": [REPO],
            "no_llm": True,
            "skip_review": True,
            "verbose": False,
            "clone": True,
        },
    )
    if code != 202:
        _fail("submit jobs", (code, body))
    job_id = body["jobs"][0]["job_id"]
    _ok(f"submitted job {job_id[:8]}…")

    samples: List[Tuple[str, Optional[str], Optional[float]]] = []
    deadline = time.time() + 180
    final = None
    while time.time() < deadline:
        code, st = _req("GET", f"/api/okh/generate-from-url/jobs/{job_id}")
        if code != 200:
            _fail("poll job", (code, st))
        samples.append((st.get("state"), st.get("stage"), st.get("fraction")))
        if st.get("state") in {"SUCCESS", "FAILURE", "REVOKED"}:
            final = st
            break
        time.sleep(0.2)

    if final is None:
        _fail("job did not finish within 180s", samples[-5:])
    if final.get("state") != "SUCCESS":
        _fail("job not SUCCESS", final)
    if not final.get("manifest"):
        _fail("SUCCESS without manifest")
    progress = [s for s in samples if s[0] == "PROGRESS"]
    if not progress:
        _fail("never observed PROGRESS state (worker/progress wiring?)")
    fracs = [f for _, _, f in progress if isinstance(f, (int, float))]
    if fracs != sorted(fracs):
        _fail("progress fractions not monotonic", fracs)
    stages = sorted({s for _, s, _ in progress if s})
    _ok(f"PROGRESS stages={stages} → SUCCESS with manifest")


def check_revoke() -> None:
    print("→ job revoke")
    code, body = _req(
        "POST",
        "/api/okh/generate-from-url/jobs",
        {"urls": [REPO], "no_llm": True, "skip_review": True},
    )
    if code != 202:
        _fail("submit for revoke", (code, body))
    job_id = body["jobs"][0]["job_id"]
    code, revoked = _req("POST", f"/api/okh/generate-from-url/jobs/{job_id}/revoke")
    if code != 200:
        _fail("revoke call", (code, revoked))
    if revoked.get("state") != "REVOKED":
        _fail("revoke state", revoked)
    _ok("revoke returns REVOKED")


def check_llm_credential_auth() -> None:
    print("→ LLM credential admin gate")
    code, body = _req("GET", "/api/llm/credentials")
    if code != 401:
        _fail("anonymous list credentials should 401", (code, body))
    _ok("anonymous credentials → 401")

    api_key = _load_api_key()
    if not api_key:
        print("  · skip authenticated credential list (no API_KEYS in .env)")
        return
    code, body = _req(
        "GET",
        "/api/llm/credentials",
        headers={"Authorization": f"Bearer {api_key}"},
    )
    if code != 200:
        _fail("admin list credentials", (code, body))
    creds = body.get("credentials") if isinstance(body, dict) else None
    if not isinstance(creds, list):
        _fail("credentials list shape", body)
    _ok("admin credentials list OK")


def check_sync_endpoint_still_works() -> None:
    print("→ sync generate-from-url still works")
    code, body = _req(
        "POST",
        "/api/okh/generate-from-url",
        {
            "url": REPO,
            "no_llm": True,
            "skip_review": True,
            "clone": True,
        },
    )
    if code != 200:
        _fail("sync generate", (code, body))
    if not body.get("manifest"):
        _fail("sync generate missing manifest", body)
    _ok("sync path still returns a manifest")


def main() -> None:
    print("Local async-generation e2e against", BASE)
    check_readiness()
    check_openapi_surface()
    check_job_progress_and_success()
    check_revoke()
    check_llm_credential_auth()
    check_sync_endpoint_still_works()
    print("\n✓ local async-generation e2e passed")


if __name__ == "__main__":
    main()
