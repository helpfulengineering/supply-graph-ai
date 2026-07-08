"""Playwright synthetic smoke runner for the harness."""

from __future__ import annotations

import json
import subprocess
import urllib.error
import urllib.request
from dataclasses import dataclass, field
from typing import Any, Sequence

DEFAULT_JOURNEY_SPECS: tuple[str, ...] = (
    "e2e/smoke.spec.ts",
    "e2e/dashboard.spec.ts",
    "e2e/okh-catalog.spec.ts",
    "e2e/match.spec.ts",
    "e2e/network.spec.ts",
)


@dataclass
class SmokeFailure:
    spec: str
    title: str
    status: str
    error: str = ""


@dataclass
class SmokeRunResult:
    exit_code: int
    duration_ms: float
    passed: int = 0
    failed: int = 0
    skipped: int = 0
    failures: list[SmokeFailure] = field(default_factory=list)
    stdout: str = ""
    stderr: str = ""
    parse_error: str | None = None


_PLAYWRIGHT_LAUNCH_PROBE = """
const { chromium } = require("@playwright/test");
chromium.launch({ headless: true })
  .then((browser) => browser.close())
  .then(() => process.exit(0))
  .catch(() => process.exit(1));
"""


def check_playwright_chromium_ready(
    frontend_dir: str, *, timeout: float = 60.0
) -> bool:
    """Return True when Playwright can launch headless Chromium.

    Uses a real launch probe — ``playwright install --dry-run`` always prints
    download URLs even when browsers are already installed, so it is not a
    reliable readiness signal.
    """
    proc = subprocess.run(
        ["node", "-e", _PLAYWRIGHT_LAUNCH_PROBE],
        cwd=frontend_dir,
        capture_output=True,
        text=True,
        timeout=timeout,
        check=False,
    )
    return proc.returncode == 0


def check_api_health(health_url: str, *, timeout: float = 5.0) -> bool:
    """Return True when the API health endpoint responds with HTTP 2xx."""
    req = urllib.request.Request(health_url, method="GET")
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return 200 <= resp.status < 300
    except (urllib.error.URLError, TimeoutError, OSError):
        return False


def parse_playwright_json(payload: dict[str, Any]) -> dict[str, Any]:
    """Extract pass/fail counts and failure records from a Playwright JSON report."""
    stats = dict(payload.get("stats") or {})
    failures: list[SmokeFailure] = []

    def walk_suites(suites: list[dict[str, Any]], spec_file: str = "") -> None:
        for suite in suites:
            file = suite.get("file") or spec_file
            for spec in suite.get("specs") or []:
                title = str(spec.get("title") or "unknown")
                for test in spec.get("tests") or []:
                    for result in test.get("results") or []:
                        status = str(result.get("status") or "unknown")
                        if status in {"passed", "skipped"}:
                            continue
                        error_msg = ""
                        err = result.get("error")
                        if isinstance(err, dict):
                            error_msg = str(err.get("message") or "")
                        failures.append(
                            SmokeFailure(
                                spec=file or "unknown",
                                title=title,
                                status=status,
                                error=error_msg,
                            )
                        )
            walk_suites(list(suite.get("suites") or []), file)

    walk_suites(list(payload.get("suites") or []))

    expected = int(stats.get("expected") or 0)
    unexpected = int(stats.get("unexpected") or 0)
    skipped = int(stats.get("skipped") or 0)
    duration_ms = float(stats.get("duration") or 0.0)

    return {
        "passed": expected,
        "failed": unexpected,
        "skipped": skipped,
        "duration_ms": duration_ms,
        "failures": failures,
    }


def run_playwright_smoke(
    *,
    frontend_dir: str,
    lane: str,
    journey_specs: Sequence[str],
    timeout_seconds: float = 300.0,
) -> SmokeRunResult:
    """Run Playwright journeys and parse the JSON report from stdout."""
    specs = list(journey_specs) or list(DEFAULT_JOURNEY_SPECS)
    cmd = [
        "npx",
        "playwright",
        "test",
        "--project",
        lane,
        "--reporter=json",
        *specs,
    ]
    proc = subprocess.run(
        cmd,
        cwd=frontend_dir,
        capture_output=True,
        text=True,
        timeout=timeout_seconds,
        check=False,
    )
    result = SmokeRunResult(
        exit_code=proc.returncode,
        duration_ms=0.0,
        stdout=proc.stdout,
        stderr=proc.stderr,
    )
    if not proc.stdout.strip():
        result.parse_error = "Playwright produced no JSON report on stdout"
        if proc.returncode != 0:
            result.failed = 1
        return result

    try:
        payload = json.loads(proc.stdout)
    except json.JSONDecodeError as exc:
        result.parse_error = f"Invalid Playwright JSON: {exc}"
        result.failed = max(1, result.failed)
        return result

    parsed = parse_playwright_json(payload)
    result.passed = int(parsed["passed"])
    result.failed = int(parsed["failed"])
    result.skipped = int(parsed["skipped"])
    result.duration_ms = float(parsed["duration_ms"])
    result.failures = list(parsed["failures"])
    return result
