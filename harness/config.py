"""Harness configuration loader.

Project-specific values live in ``harness.config.json`` at the repo root so
modules stay free of hard-coded OHM paths/URLs.
"""

from __future__ import annotations

import json
import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Optional

_REPO_ROOT = Path(__file__).resolve().parent.parent
_DEFAULT_CONFIG = _REPO_ROOT / "harness.config.json"


@dataclass(frozen=True)
class ModuleConfig:
    """Per-module enablement and thresholds."""

    enabled: bool = True
    options: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class HarnessConfig:
    """Top-level harness config."""

    api_base_url: str = "http://localhost:8001"
    api_health_url: str = "http://localhost:8001/health"
    api_path_prefix: str = "/v1/api"
    openapi_url: str = "http://localhost:8001/v1/openapi.json"
    frontend_url: str = "http://localhost:5173"
    frontend_dir: str = "frontend"
    committed_schema: str = "frontend/src/api/generated/schema.d.ts"
    modules: dict[str, ModuleConfig] = field(default_factory=dict)

    def module(self, name: str) -> ModuleConfig:
        return self.modules.get(name, ModuleConfig(enabled=True))


_BASE_URL_ENV = "OHM_HARNESS_API_BASE_URL"


def _target_base_url(raw: dict[str, Any]) -> str:
    """The API the harness points at, overridable without editing tracked config.

    ``harness.config.json`` pins the deployed node, which is what you want by
    default and exactly wrong when the thing you need to check is a stack you
    just started locally.
    """
    override = os.environ.get(_BASE_URL_ENV)
    if override:
        return override.rstrip("/")
    return str(raw.get("api_base_url", HarnessConfig.api_base_url))


def _derived(raw: dict[str, Any], key: str, base_url: str, suffix: str) -> str:
    """A URL that follows the base unless it was overridden on its own.

    Without this, pointing the harness at localhost would leave it probing the
    deployed node's health and schema — reporting on one system while claiming
    to describe another.
    """
    if os.environ.get(_BASE_URL_ENV):
        return f"{base_url}{suffix}"
    return str(raw.get(key, getattr(HarnessConfig, key)))


def load_config(path: Optional[Path] = None) -> HarnessConfig:
    """Load ``harness.config.json``; missing file yields defaults with all modules enabled."""
    cfg_path = path or _DEFAULT_CONFIG
    if not cfg_path.is_file():
        loop_names = ("parity", "red", "synthetic_smoke", "client_drift")
        probe_names = (
            "probe_match",
            "probe_latency",
            "probe_cache",
            "probe_okh_files",
        )
        modules = {name: ModuleConfig(enabled=True) for name in loop_names}
        modules.update({name: ModuleConfig(enabled=False) for name in probe_names})
        return HarnessConfig(modules=modules)

    raw = json.loads(cfg_path.read_text(encoding="utf-8"))
    modules_raw = raw.get("modules") or {}
    modules = {
        name: ModuleConfig(
            enabled=bool(body.get("enabled", True)),
            options=dict(body.get("options") or {}),
        )
        for name, body in modules_raw.items()
    }
    # Ensure known modules always appear even if omitted from JSON.
    for name in ("parity", "red", "synthetic_smoke", "client_drift"):
        modules.setdefault(name, ModuleConfig(enabled=True))
    for name in (
        "probe_match",
        "probe_latency",
        "probe_cache",
        "probe_okh_files",
    ):
        modules.setdefault(name, ModuleConfig(enabled=False))

    base_url = _target_base_url(raw)
    return HarnessConfig(
        api_base_url=base_url,
        api_health_url=_derived(raw, "api_health_url", base_url, "/health"),
        api_path_prefix=str(raw.get("api_path_prefix", HarnessConfig.api_path_prefix)),
        openapi_url=_derived(raw, "openapi_url", base_url, "/v1/openapi.json"),
        frontend_url=str(raw.get("frontend_url", HarnessConfig.frontend_url)),
        frontend_dir=str(raw.get("frontend_dir", HarnessConfig.frontend_dir)),
        committed_schema=str(
            raw.get("committed_schema", HarnessConfig.committed_schema)
        ),
        modules=modules,
    )


def repo_root() -> Path:
    return _REPO_ROOT
