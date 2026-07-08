"""Unit tests for synthetic smoke runner and harness loop."""

from __future__ import annotations

import json

import pytest

from harness.config import HarnessConfig, ModuleConfig
from harness.modules.smoke_runner import (
    check_api_health,
    check_playwright_chromium_ready,
    parse_playwright_json,
    run_playwright_smoke,
)
from harness.modules.synthetic_smoke import SyntheticSmokeLoop
from harness.protocol import FindingKind, LoopStatus, Severity

pytestmark = pytest.mark.unit

_SAMPLE_REPORT = {
    "stats": {
        "expected": 1,
        "unexpected": 1,
        "skipped": 0,
        "duration": 1500.5,
    },
    "suites": [
        {
            "file": "smoke.spec.ts",
            "specs": [
                {
                    "title": "home page renders the app shell",
                    "tests": [
                        {
                            "results": [
                                {"status": "passed"},
                            ]
                        }
                    ],
                },
                {
                    "title": "home page has no serious accessibility violations",
                    "tests": [
                        {
                            "results": [
                                {
                                    "status": "failed",
                                    "error": {"message": "Timeout 5000ms"},
                                }
                            ]
                        }
                    ],
                },
            ],
        }
    ],
}


def test_parse_playwright_json_extracts_failures():
    parsed = parse_playwright_json(_SAMPLE_REPORT)
    assert parsed["passed"] == 1
    assert parsed["failed"] == 1
    assert len(parsed["failures"]) == 1
    assert parsed["failures"][0].title == (
        "home page has no serious accessibility violations"
    )


def test_synthetic_smoke_skips_when_api_unreachable(monkeypatch):
    monkeypatch.setattr(
        "harness.modules.synthetic_smoke.check_api_health",
        lambda _url: False,
    )
    cfg = HarnessConfig(
        api_health_url="http://localhost:8001/health",
        modules={
            "synthetic_smoke": ModuleConfig(
                enabled=True,
                options={"skip_if_unreachable": True},
            )
        },
    )
    report = SyntheticSmokeLoop(
        config=cfg, module_config=cfg.module("synthetic_smoke")
    ).run()
    assert report.status == LoopStatus.SKIPPED
    assert report.ok is True


def test_synthetic_smoke_skips_when_playwright_unavailable(monkeypatch):
    monkeypatch.setattr(
        "harness.modules.synthetic_smoke.check_api_health",
        lambda _url: True,
    )
    monkeypatch.setattr(
        "harness.modules.synthetic_smoke.check_playwright_chromium_ready",
        lambda _dir: False,
    )
    cfg = HarnessConfig(
        modules={"synthetic_smoke": ModuleConfig(enabled=True)},
    )
    report = SyntheticSmokeLoop(
        config=cfg, module_config=cfg.module("synthetic_smoke")
    ).run()
    assert report.status == LoopStatus.SKIPPED
    assert report.ok is True


def test_synthetic_smoke_reports_journey_failures(monkeypatch):
    monkeypatch.setattr(
        "harness.modules.synthetic_smoke.check_api_health",
        lambda _url: True,
    )
    monkeypatch.setattr(
        "harness.modules.synthetic_smoke.check_playwright_chromium_ready",
        lambda _dir: True,
    )

    class FakeResult:
        exit_code = 1
        duration_ms = 1200.0
        passed = 1
        failed = 1
        skipped = 0
        parse_error = None
        failures = [
            type(
                "F",
                (),
                {
                    "spec": "smoke.spec.ts",
                    "title": "home page renders the app shell",
                    "status": "failed",
                    "error": "boom",
                },
            )()
        ]
        stdout = ""
        stderr = ""

    monkeypatch.setattr(
        "harness.modules.synthetic_smoke.run_playwright_smoke",
        lambda **_: FakeResult(),
    )
    cfg = HarnessConfig(
        modules={"synthetic_smoke": ModuleConfig(enabled=True)},
    )
    report = SyntheticSmokeLoop(
        config=cfg, module_config=cfg.module("synthetic_smoke")
    ).run()
    assert report.status == LoopStatus.ONLINE
    assert report.ok is False
    assert report.findings[0].kind == FindingKind.BUG
    assert report.findings[0].severity == Severity.ERROR


def test_run_playwright_smoke_parses_json_stdout(monkeypatch, tmp_path):
    report = {
        "stats": {"expected": 2, "unexpected": 0, "skipped": 0, "duration": 99},
        "suites": [],
    }

    class FakeProc:
        returncode = 0
        stdout = json.dumps(report)
        stderr = ""

    monkeypatch.setattr(
        "harness.modules.smoke_runner.subprocess.run",
        lambda *args, **kwargs: FakeProc(),
    )
    result = run_playwright_smoke(
        frontend_dir=str(tmp_path),
        lane="real-api",
        journey_specs=["e2e/smoke.spec.ts"],
    )
    assert result.exit_code == 0
    assert result.passed == 2
    assert result.failed == 0


def test_check_playwright_chromium_ready_uses_launch_probe(monkeypatch, tmp_path):
    monkeypatch.setattr(
        "harness.modules.smoke_runner.subprocess.run",
        lambda *args, **kwargs: type("Proc", (), {"returncode": 0})(),
    )
    assert check_playwright_chromium_ready(str(tmp_path)) is True

    monkeypatch.setattr(
        "harness.modules.smoke_runner.subprocess.run",
        lambda *args, **kwargs: type("Proc", (), {"returncode": 1})(),
    )
    assert check_playwright_chromium_ready(str(tmp_path)) is False


def test_check_api_health_false_on_connection_error(monkeypatch):
    def _boom(*_args, **_kwargs):
        raise OSError("connection refused")

    monkeypatch.setattr("harness.modules.smoke_runner.urllib.request.urlopen", _boom)
    assert check_api_health("http://localhost:9999/health") is False
