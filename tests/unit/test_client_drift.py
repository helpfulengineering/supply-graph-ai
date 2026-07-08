"""Tests for client_drift OpenAPI ↔ schema.d.ts operation inventory."""

from __future__ import annotations

from pathlib import Path

import pytest

from harness.config import HarnessConfig, ModuleConfig
from harness.modules.client_drift import (
    ClientDriftLoop,
    diff_operations,
    operations_from_openapi,
    operations_from_schema_dts,
)
from harness.protocol import FindingKind, LoopStatus, Severity

pytestmark = pytest.mark.unit

_REPO_ROOT = Path(__file__).resolve().parents[2]

_SAMPLE_SCHEMA = """\
export interface paths {
    "/api/match": {
        get?: never;
        post: operations["match_post"];
        delete?: never;
    };
    "/api/okh/{id}": {
        get: operations["get_okh"];
        put: operations["update_okh"];
        delete: operations["delete_okh"];
        post?: never;
    };
}
"""

_SAMPLE_OPENAPI = {
    "paths": {
        "/api/match": {"post": {"summary": "match"}},
        "/api/okh/{id}": {
            "get": {},
            "put": {},
            "delete": {},
            "parameters": [],  # ignored
        },
        "/api/new-endpoint": {"get": {}},
    }
}


def test_operations_from_openapi_extracts_method_path_pairs():
    ops = operations_from_openapi(_SAMPLE_OPENAPI)
    assert ops == {
        "POST /api/match",
        "GET /api/okh/{id}",
        "PUT /api/okh/{id}",
        "DELETE /api/okh/{id}",
        "GET /api/new-endpoint",
    }


def test_operations_from_schema_dts_skips_never_stubs():
    ops = operations_from_schema_dts(_SAMPLE_SCHEMA)
    assert ops == {
        "POST /api/match",
        "GET /api/okh/{id}",
        "PUT /api/okh/{id}",
        "DELETE /api/okh/{id}",
    }
    assert "GET /api/match" not in ops


def test_diff_operations_separates_missing_and_extra():
    live = {"POST /api/match", "GET /api/new"}
    committed = {"POST /api/match", "GET /api/stale"}
    diff = diff_operations(live=live, committed=committed)
    assert diff["missing_from_client"] == ["GET /api/new"]
    assert diff["extra_in_client"] == ["GET /api/stale"]
    assert diff["shared"] == ["POST /api/match"]


def test_committed_schema_and_live_openapi_share_core_ops():
    """Smoke that parsers agree on the real repo inventories."""
    schema = (_REPO_ROOT / "frontend/src/api/generated/schema.d.ts").read_text(
        encoding="utf-8"
    )
    from harness.modules.client_drift import load_live_openapi

    live = operations_from_openapi(load_live_openapi())
    committed = operations_from_schema_dts(schema)
    assert len(committed) > 50
    assert len(live) > 50
    shared = live & committed
    assert "POST /api/match" in shared
    assert len(shared) > 40


def test_client_drift_loop_reports_missing_as_error_finding():
    cfg = HarnessConfig(
        committed_schema="frontend/src/api/generated/schema.d.ts",
        modules={"client_drift": ModuleConfig(enabled=True)},
    )
    loop = ClientDriftLoop(config=cfg, module_config=cfg.module("client_drift"))
    assert loop.status == LoopStatus.ONLINE

    # Inject a synthetic observation rather than hitting the full app import path.
    from harness.protocol import Observations

    obs = Observations(
        data={
            "live_count": 3,
            "committed_count": 2,
            "shared_count": 2,
            "missing_from_client": ["GET /api/brand-new"],
            "extra_in_client": ["GET /api/removed"],
        }
    )
    findings = loop.judge(obs)
    kinds = {(f.kind, f.severity) for f in findings}
    assert (FindingKind.GAP, Severity.ERROR) in kinds
    assert (FindingKind.GAP, Severity.WARN) in kinds
    assert any("brand-new" in str(f.evidence) for f in findings)


def test_client_drift_loop_clean_when_inventories_match(monkeypatch, tmp_path):
    schema_path = tmp_path / "schema.d.ts"
    schema_path.write_text(_SAMPLE_SCHEMA, encoding="utf-8")
    matching_openapi = {
        "paths": {
            "/api/match": {"post": {}},
            "/api/okh/{id}": {"get": {}, "put": {}, "delete": {}},
        }
    }
    monkeypatch.setattr(
        "harness.modules.client_drift.load_live_openapi",
        lambda: matching_openapi,
    )
    monkeypatch.setattr(
        "harness.modules.client_drift.repo_root",
        lambda: tmp_path,
    )
    cfg = HarnessConfig(
        committed_schema="schema.d.ts",
        modules={"client_drift": ModuleConfig(enabled=True)},
    )
    report = ClientDriftLoop(config=cfg, module_config=cfg.module("client_drift")).run()
    assert report.status == LoopStatus.ONLINE
    assert report.ok is True
    assert report.findings == []
    assert report.observations is not None
    assert report.observations.data["shared_count"] == 4
