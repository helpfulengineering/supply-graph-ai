"""Unit tests for the triage harness protocol and runner."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from harness.base import BaseLoopModule
from harness.config import HarnessConfig, ModuleConfig, load_config
from harness.modules import instantiate, known_modules
from harness.protocol import LoopStatus, Severity
from harness.runner import main, run_modules

pytestmark = pytest.mark.unit

_REPO_ROOT = Path(__file__).resolve().parents[2]


def test_known_modules_are_the_four_early_adoption_loops():
    assert known_modules() == [
        "parity",
        "red",
        "synthetic_smoke",
        "client_drift",
    ]


def test_load_default_config_from_repo_root():
    cfg = load_config(_REPO_ROOT / "harness.config.json")
    assert cfg.api_base_url.startswith("http")
    assert set(cfg.modules) >= set(known_modules())
    assert cfg.module("parity").enabled is True


def test_each_module_instantiates_and_runs():
    cfg = load_config(_REPO_ROOT / "harness.config.json")
    expected_status = {
        "parity": LoopStatus.STUB,
        "red": LoopStatus.STUB,
        "synthetic_smoke": LoopStatus.STUB,
        "client_drift": LoopStatus.ONLINE,
    }
    for name in known_modules():
        mod = instantiate(name, cfg)
        assert isinstance(mod, BaseLoopModule)
        report = mod.run()
        assert report.module == name
        assert report.status == expected_status[name]
        assert report.error is None
        # Stubs always ok; online modules ok only if no ERROR findings.
        if report.status == LoopStatus.STUB:
            assert report.ok is True


def test_disabled_module_is_skipped():
    modules = {n: ModuleConfig(enabled=(n != "parity")) for n in known_modules()}
    cfg = HarnessConfig(modules=modules)
    report = instantiate("parity", cfg).run()
    assert report.status == LoopStatus.SKIPPED
    assert report.ok is True


def test_run_modules_subset():
    result = run_modules(names=["parity"])
    assert len(result.reports) == 1
    assert result.reports[0].module == "parity"
    assert result.ok is True
    assert result.to_dict()["stub_count"] == 1


def test_parity_discover_loads_manifest_areas():
    cfg = load_config(_REPO_ROOT / "harness.config.json")
    inv = instantiate("parity", cfg).discover()
    assert inv.items.get("count", 0) > 0
    assert "okh" in inv.items["areas"]


def test_client_drift_discover_sees_committed_schema():
    cfg = load_config(_REPO_ROOT / "harness.config.json")
    inv = instantiate("client_drift", cfg).discover()
    assert inv.items["committed_schema_exists"] is True
    assert inv.items["committed_schema_bytes"] > 0


def test_runner_list_and_json(capsys):
    assert main(["--list"]) == 0
    listed = capsys.readouterr().out.strip().splitlines()
    assert listed == known_modules()

    assert main(["--json", "--modules", "red"]) == 0
    payload = json.loads(capsys.readouterr().out)
    assert payload["ok"] is True
    assert payload["modules"][0]["module"] == "red"
    assert payload["modules"][0]["status"] == "stub"


def test_unknown_module_exits():
    with pytest.raises(SystemExit):
        run_modules(names=["not_a_real_loop"])


def test_finding_to_dict_uses_enum_values():
    from harness.protocol import Finding, FindingKind

    f = Finding(
        module="red",
        kind=FindingKind.PERF,
        severity=Severity.WARN,
        title="p95 elevated",
        evidence={"p95_ms": 3000},
    )
    d = f.to_dict()
    assert d["kind"] == "perf"
    assert d["severity"] == "warn"
    assert d["suggested_state"] == "needs-triage"
