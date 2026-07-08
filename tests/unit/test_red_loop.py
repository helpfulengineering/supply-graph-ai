"""Unit tests for RED metrics loading and harness red loop."""

from __future__ import annotations

import pytest

from harness.config import HarnessConfig, ModuleConfig
from harness.modules.red import RedLoop
from harness.modules.red_metrics import judge_endpoints, load_metrics_in_process
from harness.protocol import FindingKind, LoopStatus, Severity

pytestmark = pytest.mark.unit


def test_judge_endpoints_flags_error_rate_and_latency():
    endpoints = {
        "GET /api/okh": {
            "total_requests": 10,
            "failed_requests": 2,
            "success_rate": 80.0,
            "p95_processing_time_ms": 0.5,  # 500ms after conversion
        },
        "POST /api/match": {
            "total_requests": 5,
            "failed_requests": 0,
            "success_rate": 100.0,
            "p95_processing_time_ms": 5.0,  # 5000ms after conversion
        },
        "GET /api/utility/metrics": {
            "total_requests": 1,
            "failed_requests": 0,
            "success_rate": 100.0,
            "p95_processing_time_ms": 0.01,
        },
    }
    breaches = judge_endpoints(
        endpoints,
        error_rate_warn=0.05,
        p95_ms_warn=2000,
        min_requests=1,
    )
    by_endpoint = {b["endpoint"]: b for b in breaches}
    assert "error_rate" in by_endpoint["GET /api/okh"]["issues"]
    assert "latency" in by_endpoint["POST /api/match"]["issues"]
    assert "GET /api/utility/metrics" not in by_endpoint


def test_judge_endpoints_skips_low_traffic():
    endpoints = {
        "GET /api/okh": {
            "total_requests": 0,
            "failed_requests": 0,
            "p95_processing_time_ms": 99.0,
        }
    }
    assert (
        judge_endpoints(
            endpoints,
            error_rate_warn=0.05,
            p95_ms_warn=2000,
            min_requests=1,
        )
        == []
    )


def test_red_loop_clean_with_empty_tracker(monkeypatch):
    monkeypatch.setattr(
        "harness.modules.red.load_metrics",
        lambda **_: {"summary": {}, "endpoints": {}},
    )
    cfg = HarnessConfig(modules={"red": ModuleConfig(enabled=True)})
    report = RedLoop(config=cfg, module_config=cfg.module("red")).run()
    assert report.status == LoopStatus.ONLINE
    assert report.ok is True
    assert report.findings == []


def test_red_loop_reports_threshold_breaches(monkeypatch):
    monkeypatch.setattr(
        "harness.modules.red.load_metrics",
        lambda **_: {
            "summary": {"total_requests": 10},
            "endpoints": {
                "GET /api/okh": {
                    "total_requests": 10,
                    "failed_requests": 5,
                    "success_rate": 50.0,
                    "p95_processing_time_ms": 0.1,
                }
            },
        },
    )
    cfg = HarnessConfig(
        modules={
            "red": ModuleConfig(
                enabled=True,
                options={"error_rate_warn": 0.05, "p95_ms_warn": 2000},
            )
        }
    )
    report = RedLoop(config=cfg, module_config=cfg.module("red")).run()
    assert report.ok is True  # WARN findings do not fail the harness
    assert len(report.findings) == 1
    assert report.findings[0].kind == FindingKind.BUG
    assert report.findings[0].severity == Severity.WARN


def test_load_metrics_in_process_returns_endpoints_shape():
    payload = load_metrics_in_process()
    assert "summary" in payload
    assert "endpoints" in payload
    assert isinstance(payload["endpoints"], dict)
