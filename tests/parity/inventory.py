"""Live enumeration helpers for parity gates (service / API / CLI / frontend)."""

from __future__ import annotations

import re
from pathlib import Path

from tests.parity.manifest import TOP_LEVEL_CLI

_REPO_ROOT = Path(__file__).resolve().parents[2]

_ROUTE_PATH_RE = re.compile(r'<Route\s+[^>]*\bpath="([^"]+)"')
_ROUTE_INDEX_RE = re.compile(r"<Route\s+index\b")
_API_PREFIX_RE = re.compile(
    r"""['"`](?:/v1)?(/api/[a-z][a-z0-9-]*)|['"`](/(?:package|rfq)(?:/|$))"""
)


def _api_prefix_from_match(
    api_match: str | None, legacy_match: str | None
) -> str | None:
    if api_match:
        return api_match
    if legacy_match:
        segment = legacy_match.strip("/").split("/")[0]
        return f"/api/{segment}"
    return None


def actual_services() -> set[str]:
    """Service stems from ``src/core/services/*_service.py``."""
    pattern = _REPO_ROOT / "src" / "core" / "services" / "*_service.py"
    return {
        path.name[: -len("_service.py")] for path in pattern.parent.glob(pattern.name)
    }


def actual_api_tags() -> set[str]:
    """Router tags actually mounted on the versioned FastAPI app."""
    from src.core.main import api_v1

    tags: set[str] = set()
    for route in api_v1.routes:
        for tag in getattr(route, "tags", None) or []:
            tags.add(tag)
    return tags


def actual_cli_groups() -> set[str]:
    """Click groups actually registered on the CLI, minus top-level utilities."""
    from src.cli.main import cli

    return set(cli.commands.keys()) - TOP_LEVEL_CLI


def normalize_fe_route(path: str) -> str | None:
    """Collapse parameterized routes to their first path segment."""
    if path in {"*", ""}:
        return None
    if not path.startswith("/"):
        path = f"/{path}"
    parts = [p for p in path.split("/") if p]
    if not parts:
        return "/"
    return f"/{parts[0]}"


def _fe_routes_from_app_dir(app_dir: Path) -> set[str]:
    """Route prefixes from the Next App Router tree (``app/**/page.tsx``).

    Route handlers (``route.ts`` — the docs tree and the /v1 proxy) are
    deployment surface, not product routes, and are deliberately excluded.
    """
    routes: set[str] = set()
    for page in app_dir.rglob("page.tsx"):
        rel = page.parent.relative_to(app_dir)
        segments = [s for s in rel.parts if not (s.startswith("(") and s.endswith(")"))]
        path = "/" + "/".join(segments)
        normalized = normalize_fe_route(path)
        if normalized:
            routes.add(normalized)
    return routes


def actual_fe_routes(
    app_tsx: Path | None = None, app_dir: Path | None = None
) -> set[str]:
    """Route prefixes declared by the frontend router.

    Next App Router tree (``frontend/app``) when present; an explicit
    ``app_tsx`` opts into regex-scraping ``<Route path>`` out of a
    react-router ``App.tsx`` instead.
    """
    resolved_app_dir = app_dir or (_REPO_ROOT / "frontend" / "app")
    if app_tsx is None and resolved_app_dir.is_dir():
        return _fe_routes_from_app_dir(resolved_app_dir)
    app_path = app_tsx or (_REPO_ROOT / "frontend" / "src" / "App.tsx")
    text = app_path.read_text(encoding="utf-8")
    routes: set[str] = set()
    if _ROUTE_INDEX_RE.search(text):
        routes.add("/")
    for match in _ROUTE_PATH_RE.finditer(text):
        normalized = normalize_fe_route(match.group(1))
        if normalized:
            routes.add(normalized)
    return routes


def actual_fe_api_prefixes(frontend_src: Path | None = None) -> set[str]:
    """``/api/<tag>`` prefixes referenced by frontend app code (not tests)."""
    src_root = frontend_src or (_REPO_ROOT / "frontend" / "src")
    prefixes: set[str] = set()
    for path in src_root.rglob("*"):
        if path.suffix not in {".ts", ".tsx"}:
            continue
        rel = path.relative_to(src_root).as_posix()
        if rel.startswith("api/generated/"):
            continue
        if ".test." in rel or rel.startswith("test/"):
            continue
        text = path.read_text(encoding="utf-8")
        for match in _API_PREFIX_RE.finditer(text):
            prefix = _api_prefix_from_match(match.group(1), match.group(2))
            if prefix:
                prefixes.add(prefix)
    return prefixes


def layer_diff(expected: set[str], actual: set[str]) -> dict[str, list[str]]:
    """Compare declared manifest inventory to live enumeration."""
    return {
        "undeclared": sorted(actual - expected),
        "missing": sorted(expected - actual),
        "shared": sorted(actual & expected),
    }
