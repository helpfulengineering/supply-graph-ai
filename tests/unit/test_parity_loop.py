"""Unit tests for parity inventory helpers and harness parity loop."""

from __future__ import annotations

from pathlib import Path

import pytest

from harness.config import HarnessConfig, ModuleConfig
from harness.modules.parity import ParityLoop
from harness.protocol import LoopStatus, Severity
from tests.parity.inventory import (
    actual_fe_api_prefixes,
    actual_fe_routes,
    layer_diff,
    normalize_fe_route,
)

pytestmark = pytest.mark.unit

_REPO_ROOT = Path(__file__).resolve().parents[2]

_SAMPLE_APP = """\
<Routes>
  <Route index element={<Home />} />
  <Route path="okh" element={<Okh />} />
  <Route path="okh/:id" element={<Okh />} />
  <Route path="*" element={<Navigate to="/" />} />
</Routes>
"""


def test_normalize_fe_route_collapses_params():
    assert normalize_fe_route("/okh/:id") == "/okh"
    assert normalize_fe_route("/") == "/"
    assert normalize_fe_route("*") is None


def test_actual_fe_routes_from_app_tsx(tmp_path: Path):
    app = tmp_path / "App.tsx"
    app.write_text(_SAMPLE_APP, encoding="utf-8")
    assert actual_fe_routes(app) == {"/", "/okh"}


def test_layer_diff_reports_undeclared_and_missing():
    diff = layer_diff({"a", "b"}, {"b", "c"})
    assert diff["undeclared"] == ["c"]
    assert diff["missing"] == ["a"]
    assert diff["shared"] == ["b"]


def test_actual_fe_api_prefixes_includes_legacy_package_and_rfq(tmp_path: Path):
    src = tmp_path / "src"
    (src / "api").mkdir(parents=True)
    (src / "api" / "package.ts").write_text(
        'export const x = get("/package/list");\n', encoding="utf-8"
    )
    (src / "api" / "rfq.ts").write_text(
        'export const y = post("/rfq/generate", {});\n', encoding="utf-8"
    )
    assert actual_fe_api_prefixes(src) == {"/api/package", "/api/rfq"}


def test_parity_loop_clean_on_real_repo():
    cfg = HarnessConfig(
        frontend_dir="frontend",
        modules={"parity": ModuleConfig(enabled=True)},
    )
    report = ParityLoop(config=cfg, module_config=cfg.module("parity")).run()
    assert report.status == LoopStatus.ONLINE
    assert report.ok is True, report.findings
    assert report.observations is not None
    assert report.observations.data["fe_route"]["undeclared"] == []


def test_parity_loop_flags_undeclared_fe_route(tmp_path: Path, monkeypatch):
    app_dir = tmp_path / "frontend" / "src"
    app_dir.mkdir(parents=True)
    (app_dir / "App.tsx").write_text(
        '<Route index /><Route path="mystery" />', encoding="utf-8"
    )
    monkeypatch.setattr("harness.modules.parity.repo_root", lambda: tmp_path)
    monkeypatch.setattr(
        "harness.modules.parity.actual_services",
        lambda: set(),
    )
    monkeypatch.setattr(
        "harness.modules.parity.actual_api_tags",
        lambda: set(),
    )
    monkeypatch.setattr(
        "harness.modules.parity.actual_cli_groups",
        lambda: set(),
    )
    monkeypatch.setattr(
        "harness.modules.parity.expected_services",
        lambda: set(),
    )
    monkeypatch.setattr(
        "harness.modules.parity.expected_api_tags",
        lambda: set(),
    )
    monkeypatch.setattr(
        "harness.modules.parity.expected_cli_groups",
        lambda: set(),
    )
    monkeypatch.setattr(
        "harness.modules.parity.expected_fe_routes",
        lambda: {"/"},
    )
    monkeypatch.setattr(
        "harness.modules.parity.expected_fe_api_prefixes",
        lambda: set(),
    )
    monkeypatch.setattr(
        "harness.modules.parity.actual_fe_api_prefixes",
        lambda _src=None: set(),
    )

    cfg = HarnessConfig(
        frontend_dir="frontend",
        modules={"parity": ModuleConfig(enabled=True)},
    )
    report = ParityLoop(config=cfg, module_config=cfg.module("parity")).run()
    assert report.status == LoopStatus.ONLINE
    assert report.ok is False
    fe_route = (report.observations or {}).data.get("fe_route", {})
    assert "/mystery" in fe_route.get("undeclared", [])
    assert any(f.severity == Severity.ERROR for f in report.findings)
