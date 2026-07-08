"""Loadable triage loop modules."""

from __future__ import annotations

from typing import TYPE_CHECKING

from harness.modules.client_drift import ClientDriftLoop
from harness.modules.parity import ParityLoop
from harness.modules.red import RedLoop
from harness.modules.synthetic_smoke import SyntheticSmokeLoop

if TYPE_CHECKING:
    from harness.base import BaseLoopModule
    from harness.config import HarnessConfig

MODULE_REGISTRY: dict[str, type] = {
    "parity": ParityLoop,
    "red": RedLoop,
    "synthetic_smoke": SyntheticSmokeLoop,
    "client_drift": ClientDriftLoop,
}


def known_modules() -> list[str]:
    return list(MODULE_REGISTRY.keys())


def instantiate(name: str, config: "HarnessConfig") -> "BaseLoopModule":
    try:
        cls = MODULE_REGISTRY[name]
    except KeyError as exc:
        raise KeyError(
            f"Unknown harness module {name!r}. Known: {known_modules()}"
        ) from exc
    return cls(config=config, module_config=config.module(name))
