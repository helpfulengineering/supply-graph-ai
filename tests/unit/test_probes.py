"""Unit tests for production probe modules (mocked HTTP)."""

from __future__ import annotations

from unittest.mock import patch

import pytest

from harness.config import HarnessConfig, ModuleConfig
from harness.modules.probe_cache import ProbeCacheLoop, _routes_with_cache_decorator
from harness.modules.probe_match import ProbeMatchLoop, run_match_attempts
from harness.modules.probe_okh_files import ProbeOkhFilesLoop, _check_file_url
from harness.probes.http import HttpResult
from harness.probes.okh import first_okh_id_from_list_body
from harness.probes.proposal import proposal_markdown, write_probe_proposals
from harness.protocol import Finding, FindingKind, Severity

pytestmark = pytest.mark.unit


@pytest.fixture(autouse=True)
def _probe_assumes_api_reachable():
    """Unit tests mock HTTP; do not require a live API on api_health_url."""
    with patch("harness.probes.base.check_api_reachable", return_value=True):
        yield


def _cfg(module: str = "probe_match", **options) -> HarnessConfig:
    """Probe module config for unit tests (no live API required)."""
    options.setdefault("skip_if_unreachable", False)
    return HarnessConfig(
        modules={
            module: ModuleConfig(enabled=True, options=options),
        }
    )


def test_first_okh_id_from_paginated_response():
    body = {"items": [{"id": "okh-123", "title": "Test"}]}
    assert first_okh_id_from_list_body(body) == "okh-123"


def test_first_okh_id_from_nested_data():
    body = {"data": {"items": [{"okh_id": "nested-1"}]}}
    assert first_okh_id_from_list_body(body) == "nested-1"


@patch("harness.modules.probe_match.api_request")
def test_probe_match_flags_503_rate(mock_api):
    mock_api.side_effect = [
        HttpResult("GET", "u", 200, 50, body={"items": [{"id": "x"}]}),
        HttpResult(
            "POST",
            "u",
            503,
            100,
            body={"detail": "timeout"},
            headers={"x-request-id": "r1"},
        ),
        HttpResult("POST", "u", 200, 500, body={"status": "success"}),
        HttpResult("POST", "u", 503, 100, body={}, headers={"x-request-id": "r2"}),
        HttpResult("POST", "u", 200, 400, body={"status": "success"}),
        HttpResult("POST", "u", 200, 350, body={"status": "success"}),
    ]
    mod = ProbeMatchLoop(_cfg(attempts=5, max_503_rate=0.0))
    report = mod.run()
    assert not report.ok
    titles = [f.title for f in report.findings]
    assert any("503" in t for t in titles)


def test_run_match_attempts_returns_diagnostics():
    with patch("harness.modules.probe_match.api_request") as mock_api:
        mock_api.return_value = HttpResult(
            "POST",
            "http://localhost/match",
            503,
            1200.5,
            body={"detail": "init timeout"},
            headers={"x-request-id": "abc"},
        )
        samples = run_match_attempts(
            base_url="http://localhost:8001",
            api_path_prefix="/v1/api",
            okh_id="okh-1",
            attempts=1,
            timeout=30,
        )
    assert samples[0]["status"] == 503
    assert samples[0]["request_id"] == "abc"
    assert "timeout" in samples[0]["detail"]


@patch("harness.modules.probe_latency.api_request")
def test_probe_latency_exceeds_error_slo(mock_api):
    from harness.modules.probe_latency import ProbeLatencyLoop

    mock_api.return_value = HttpResult("GET", "u", 200, 15000, body={"items": []})
    mod = ProbeLatencyLoop(
        _cfg(
            "probe_latency",
            checks=[
                {
                    "name": "slow",
                    "method": "GET",
                    "path": "/okh?page=1",
                    "warn_ms": 1000,
                    "error_ms": 5000,
                }
            ],
        )
    )
    report = mod.run()
    assert not report.ok
    assert report.findings[0].severity == Severity.ERROR


@patch("harness.modules.probe_cache.api_request")
def test_probe_cache_flags_ineffective_paths(mock_api):
    mock_api.side_effect = [
        HttpResult("GET", "u", 200, 1000, body={}),
        HttpResult("GET", "u", 200, 950, body={}),
    ]
    mod = ProbeCacheLoop(
        _cfg("probe_cache", probe_paths=["/okh?page=1&page_size=5"]),
    )
    report = mod.run()
    assert not report.ok
    assert any("No effective cache" in f.title for f in report.findings)


def test_routes_with_cache_decorator_finds_utility_domains():
    routes = _routes_with_cache_decorator()
    assert any("utility" in r for r in routes)


@patch("harness.modules.probe_okh_files.api_request")
def test_probe_okh_files_flags_relative_paths(mock_api):
    mock_api.side_effect = [
        HttpResult("GET", "u", 200, 50, body={"items": [{"id": "m1"}]}),
        HttpResult(
            "GET",
            "u",
            200,
            80,
            body={
                "data": {
                    "id": "m1",
                    "design_files": [{"path": "docs/plan.pdf", "title": "Plan"}],
                }
            },
        ),
    ]
    mod = ProbeOkhFilesLoop(_cfg("probe_okh_files"))
    report = mod.run()
    assert not report.ok
    assert any("not API-proxied" in f.title for f in report.findings)


def test_check_file_url_relative_path():
    result = _check_file_url("relative/path.stl")
    assert result["reachable"] is False
    assert result["reason"] == "relative_path_no_api_proxy"


def test_write_probe_proposals_creates_markdown(tmp_path):
    finding = Finding(
        module="probe_match",
        kind=FindingKind.BUG,
        severity=Severity.ERROR,
        title="Match returned 503",
        evidence={"503_rate": 0.4, "recommendation": "Fix init"},
        suggested_state="ready-for-human",
    )
    written = write_probe_proposals([finding], tmp_path)
    assert len(written) == 1
    text = written[0].read_text(encoding="utf-8")
    assert "Match returned 503" in text
    assert proposal_markdown(finding)
