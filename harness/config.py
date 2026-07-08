"""Harness configuration loader.

Project-specific values live in ``harness.config.json`` at the repo root so
modules stay free of hard-coded OHM paths/URLs.
"""

from __future__ import annotations

import json
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
    openapi_url: str = "http://localhost:8001/v1/openapi.json"
    frontend_url: str = "http://localhost:5173"
    frontend_dir: str = "frontend"
    committed_schema: str = "frontend/src/api/generated/schema.d.ts"
    modules: dict[str, ModuleConfig] = field(default_factory=dict)

    def module(self, name: str) -> ModuleConfig:
        return self.modules.get(name, ModuleConfig(enabled=True))


def load_config(path: Optional[Path] = None) -> HarnessConfig:
    """Load ``harness.config.json``; missing file yields defaults with all modules enabled."""
    cfg_path = path or _DEFAULT_CONFIG
    if not cfg_path.is_file():
        return HarnessConfig(
            modules={
                name: ModuleConfig(enabled=True)
                for name in ("parity", "red", "synthetic_smoke", "client_drift")
            }
        )

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

    return HarnessConfig(
        api_base_url=str(raw.get("api_base_url", HarnessConfig.api_base_url)),
        api_health_url=str(raw.get("api_health_url", HarnessConfig.api_health_url)),
        openapi_url=str(raw.get("openapi_url", HarnessConfig.openapi_url)),
        frontend_url=str(raw.get("frontend_url", HarnessConfig.frontend_url)),
        frontend_dir=str(raw.get("frontend_dir", HarnessConfig.frontend_dir)),
        committed_schema=str(
            raw.get("committed_schema", HarnessConfig.committed_schema)
        ),
        modules=modules,
    )


def repo_root() -> Path:
    return _REPO_ROOT
