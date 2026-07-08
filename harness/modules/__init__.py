"""Loadable triage loop and production probe modules."""

from __future__ import annotations

from typing import TYPE_CHECKING

from harness.modules.client_drift import ClientDriftLoop
from harness.modules.parity import ParityLoop
from harness.modules.probe_cache import ProbeCacheLoop
from harness.modules.probe_latency import ProbeLatencyLoop
from harness.modules.probe_match import ProbeMatchLoop
from harness.modules.probe_okh_files import ProbeOkhFilesLoop
from harness.modules.red import RedLoop
from harness.modules.synthetic_smoke import SyntheticSmokeLoop

if TYPE_CHECKING:
    from harness.base import BaseLoopModule
    from harness.config import HarnessConfig

# Verification loops (inventory, drift, RED, smoke)
LOOP_MODULES: dict[str, type] = {
    "parity": ParityLoop,
    "red": RedLoop,
    "synthetic_smoke": SyntheticSmokeLoop,
    "client_drift": ClientDriftLoop,
}

# Targeted production probes (behavioral diagnosis)
PROBE_MODULES: dict[str, type] = {
    "probe_match": ProbeMatchLoop,
    "probe_latency": ProbeLatencyLoop,
    "probe_cache": ProbeCacheLoop,
    "probe_okh_files": ProbeOkhFilesLoop,
}

MODULE_REGISTRY: dict[str, type] = {**LOOP_MODULES, **PROBE_MODULES}


def known_modules() -> list[str]:
    return list(MODULE_REGISTRY.keys())


def known_loops() -> list[str]:
    return list(LOOP_MODULES.keys())


def known_probes() -> list[str]:
    return list(PROBE_MODULES.keys())


def instantiate(name: str, config: "HarnessConfig") -> "BaseLoopModule":
    try:
        cls = MODULE_REGISTRY[name]
    except KeyError as exc:
        raise KeyError(
            f"Unknown harness module {name!r}. Known: {known_modules()}"
        ) from exc
    return cls(config=config, module_config=config.module(name))
