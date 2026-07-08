"""Probe: API response cache configuration and effectiveness."""

from __future__ import annotations

import ast
from typing import Any

from harness.config import repo_root
from harness.probes.base import ProbeModule
from harness.probes.http import api_request
from harness.protocol import Finding, FindingKind, Inventory, Observations, Severity

# Routes we expect to benefit from read caching in production.
DEFAULT_PROBE_PATHS: tuple[str, ...] = (
    "/okh?page=1&page_size=5",
    "/utility/domains",
)


def _routes_with_cache_decorator() -> list[str]:
    """Static scan: functions decorated with @cache_response in API routes."""
    routes: list[str] = []
    root = repo_root() / "src" / "core" / "api" / "routes"
    for path in root.glob("*.py"):
        text = path.read_text(encoding="utf-8")
        if "@cache_response" not in text:
            continue
        try:
            tree = ast.parse(text)
        except SyntaxError:
            continue
        for node in ast.walk(tree):
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                for dec in node.decorator_list:
                    src = ast.get_source_segment(text, dec) or ""
                    if "cache_response" in src:
                        routes.append(f"{path.name}:{node.name}")
    return routes


def _read_cache_settings() -> dict[str, Any]:
    try:
        from src.config import settings as cfg

        return {
            "CACHE_ENABLED": getattr(cfg, "CACHE_ENABLED", None),
            "CACHE_MAX_SIZE": getattr(cfg, "CACHE_MAX_SIZE", None),
            "CACHE_CLEANUP_INTERVAL": getattr(cfg, "CACHE_CLEANUP_INTERVAL", None),
        }
    except Exception as exc:  # noqa: BLE001
        return {"error": str(exc)}


class ProbeCacheLoop(ProbeModule):
    name = "probe_cache"

    def discover(self) -> Inventory:
        return Inventory(
            items={
                "cache_settings": _read_cache_settings(),
                "cache_decorated_handlers": _routes_with_cache_decorator(),
                "probe_paths": list(
                    self.module_config.options.get("probe_paths") or DEFAULT_PROBE_PATHS
                ),
                "note": (
                    "CacheService is in-memory LRU (single-replica); ACA multi-replica "
                    "needs shared cache (Redis) for hit rate across instances."
                ),
            },
            notes=[
                "Behavioral probe: two identical GETs; second should show _cached or be much faster",
            ],
        )

    def observe(self) -> Observations:
        paths = list(
            self.module_config.options.get("probe_paths") or DEFAULT_PROBE_PATHS
        )
        min_speedup_ratio = float(
            self.module_config.options.get("min_speedup_ratio", 0.5)
        )
        behavioral: list[dict[str, Any]] = []

        for path in paths:
            r1 = api_request(
                base_url=self.config.api_base_url,
                api_path_prefix=self._api_path_prefix(),
                path=path,
                timeout=60,
            )
            r2 = api_request(
                base_url=self.config.api_base_url,
                api_path_prefix=self._api_path_prefix(),
                path=path,
                timeout=60,
            )
            cached_flag = False
            if isinstance(r2.body, dict):
                cached_flag = bool(r2.body.get("_cached"))
            speedup = (
                (r1.duration_ms - r2.duration_ms) / r1.duration_ms
                if r1.duration_ms > 0
                else 0.0
            )
            behavioral.append(
                {
                    "path": path,
                    "first_ms": round(r1.duration_ms, 1),
                    "second_ms": round(r2.duration_ms, 1),
                    "second_cached_flag": cached_flag,
                    "speedup_ratio": round(speedup, 3),
                    "effective_cache": cached_flag or speedup >= min_speedup_ratio,
                    "first_status": r1.status,
                    "second_status": r2.status,
                }
            )

        return Observations(
            data={
                "behavioral": behavioral,
                "cache_settings": _read_cache_settings(),
                "cache_decorated_handlers": _routes_with_cache_decorator(),
            },
            notes=[
                f"{b['path']}: cached={b['second_cached_flag']} "
                f"{b['first_ms']}ms -> {b['second_ms']}ms"
                for b in behavioral
            ],
        )

    def judge(self, observations: Observations) -> list[Finding]:
        findings: list[Finding] = []
        settings = observations.data.get("cache_settings") or {}
        behavioral = list(observations.data.get("behavioral") or [])
        decorated = list(observations.data.get("cache_decorated_handlers") or [])

        if settings.get("CACHE_ENABLED") is False:
            findings.append(
                Finding(
                    module=self.name,
                    kind=FindingKind.GAP,
                    severity=Severity.ERROR,
                    title="CACHE_ENABLED is false",
                    evidence={
                        "cache_settings": settings,
                        "recommendation": (
                            "Enable response caching for hot read endpoints or "
                            "document intentional disable; on ACA enable shared "
                            "Redis-backed cache for multi-replica deployments."
                        ),
                    },
                    suggested_state="ready-for-human",
                )
            )

        ineffective = [b for b in behavioral if not b.get("effective_cache")]
        if ineffective:
            findings.append(
                Finding(
                    module=self.name,
                    kind=FindingKind.GAP,
                    severity=Severity.ERROR,
                    title=(
                        f"No effective cache on {len(ineffective)} hot read path(s)"
                    ),
                    evidence={
                        "ineffective_paths": ineffective,
                        "cache_decorated_handlers": decorated,
                        "recommendation": (
                            "Add @cache_response to OKH list/detail, OKW search, and "
                            "match result caching by manifest hash; export cache hit "
                            "metrics on /utility/metrics; plan Redis for ACA."
                        ),
                    },
                    suggested_state="ready-for-human",
                )
            )

        if len(decorated) <= 1:
            findings.append(
                Finding(
                    module=self.name,
                    kind=FindingKind.GAP,
                    severity=Severity.WARN,
                    title="Very few API handlers use @cache_response",
                    evidence={
                        "cache_decorated_handlers": decorated,
                        "recommendation": (
                            "Audit hot read endpoints and apply cache_response or "
                            "CDN/storage-layer caching strategy."
                        ),
                    },
                    suggested_state="needs-triage",
                )
            )
        return findings
