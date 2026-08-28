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


# --- Per-endpoint frontend coverage --------------------------------------
#
# `actual_fe_api_prefixes` above answers "does the frontend touch this tag at
# all". It cannot answer "does the frontend touch this endpoint", and the gap
# between those two questions was most of the API: declaring
# fe_api_prefixes=("/api/supply-tree",) is satisfied by one call and says
# nothing about the other nineteen paths under that tag.
#
# The scan below answers the per-path question. It scans for the POSITIVE —
# what the frontend calls — because the negative is declared in manifest.py,
# where the reasons live. A hand-written list of *called* endpoints would be
# the thing under test: delete a feature and its row stays behind, green.

# A path parameter as it appears in frontend source. Deliberately not
# "any identifier": a bare-word wildcard makes "/api/supply-tree/{id}" match
# the literal "/api/supply-tree/solutions", crediting a sibling endpoint with a
# call it never receives.
_PARAM = r"(?:\$\{[^}`'\"]*\}|\{[a-zA-Z_][a-zA-Z0-9_]*\}|:[A-Za-z_]+)"

# What may sit immediately before a path: a quote, or `}` — the close of an
# interpolation, which is how the raw-fetch call sites are written
# (`${apiBaseUrl}/api/okw/spaces`). Without `}` the scan misses them entirely.
_BEFORE = r"""(?:["'`]|\})"""

# What may sit immediately after: a quote; a trailing slash then a quote; a
# query string; or `${` — an interpolation glued to the tail of the last
# literal segment, which is the `/api/identity/bindings${q}` shape.
_AFTER = r"""(?:["'`]|/["'`]|\?[^"'`]*["'`]|\$\{)"""

# The untyped client (src/api/client.ts) prefixes every path with /v1/api, so
# its call sites spell "/api/package/list" as "/package/list". Resolved by
# import rather than hardcoded: a fourth island module should be picked up
# without editing this file.
_ISLAND_CLIENT = ("frontend", "src", "api", "client.ts")

# Directories whose mention of a path proves nothing about the app calling it.
_SCAN_EXCLUDED = (
    # Generated from the spec — every path appears whether called or not.
    "src/api/generated/",
    # A mock is not a caller. handlers.ts alone names 40+ paths.
    "src/test/",
    # The demo world's (method, pathname) -> fixture table, same reason.
    "src/lib/demo/",
    # Catch-all proxies. They forward everything and prove nothing about any
    # one endpoint.
    "app/v1/",
    "app/docs/",
)


def _scan_sources(roots: list[Path]) -> list[tuple[str, str, bool]]:
    """(relative path, text, is-island-caller) for frontend app sources."""
    out: list[tuple[str, str, bool]] = []
    for root in roots:
        if not root.is_dir():
            continue
        for path in sorted(root.rglob("*")):
            if path.suffix not in {".ts", ".tsx"}:
                continue
            rel = path.relative_to(_REPO_ROOT).as_posix()
            scan_rel = path.relative_to(root.parent).as_posix()
            if any(scan_rel.startswith(skip) for skip in _SCAN_EXCLUDED):
                continue
            if ".test." in rel or ".spec." in rel:
                continue
            text = path.read_text(encoding="utf-8", errors="ignore")
            out.append((rel, text, _imports_island_client(path, text)))
    return out


def _imports_island_client(path: Path, text: str) -> bool:
    """Does this file import the untyped /v1/api client?

    Resolved rather than pattern-matched, because `from "./client"` means
    src/api/client.ts in src/api/rfq.ts and src/api/ohm/client.ts — a different
    module, with a different prefix — one directory down.
    """
    island = _REPO_ROOT.joinpath(*_ISLAND_CLIENT)
    for spec in re.findall(r"""from\s+["']([^"']+)["']""", text):
        if spec.startswith("@/"):
            resolved = _REPO_ROOT / "frontend" / "src" / spec[2:]
        elif spec.startswith("."):
            resolved = (path.parent / spec).resolve()
        else:
            continue
        if resolved.with_suffix(".ts") == island:
            return True
    return False


def _call_site_patterns(api_path: str) -> list[re.Pattern[str]]:
    """Regexes matching how `api_path` can be spelled at a call site.

    Two spellings, because the app has two clients: the typed one writes the
    OpenAPI path verbatim, optionally behind /v1; the island strips /api.
    """

    def compile_for(literal: str) -> re.Pattern[str]:
        body = "".join(
            _PARAM if seg.startswith("{") and seg.endswith("}") else re.escape(seg)
            for seg in re.split(r"(\{[^}]+\})", literal)
            if seg
        )
        return re.compile(f"{_BEFORE}(?:/v1)?{body}{_AFTER}")

    patterns = [compile_for(api_path)]
    if api_path.startswith("/api/"):
        patterns.append(compile_for(api_path[len("/api") :]))
    return patterns


def fe_api_call_sites(roots: list[Path] | None = None) -> dict[str, str]:
    """Map each OpenAPI path the frontend calls to the ``file:line`` proving it.

    Evidence rather than a bare set, so a failure can name the call site instead
    of leaving the reader to grep for it.
    """
    frontend = _REPO_ROOT / "frontend"
    sources = _scan_sources(roots or [frontend / "src", frontend / "app"])
    found: dict[str, str] = {}
    for api_path in openapi_paths():
        typed, *island = _call_site_patterns(api_path)
        for rel, text, is_island in sources:
            match = typed.search(text) or (
                island[0].search(text) if island and is_island else None
            )
            if match:
                line = text.count("\n", 0, match.start()) + 1
                found[api_path] = f"{rel}:{line}"
                break
    return found


def fe_called_api_paths(roots: list[Path] | None = None) -> set[str]:
    """OpenAPI paths with at least one frontend call site."""
    return set(fe_api_call_sites(roots))


def fe_calls(needle: str) -> bool:
    """Does frontend app code reach ``needle``?

    Two shapes, because SiteDoc rows carry both. A prefix ("/api/okh") is a
    substring question. An exact path ("/api/rfq/generate") is a coverage
    question, and asking it as a substring gets the wrong answer: the island
    strips /api, so that endpoint is spelled "/rfq/generate" at its call site
    and a substring search would report a shipped feature as unbuilt.
    """
    if needle in fe_called_api_paths():
        return True
    frontend = _REPO_ROOT / "frontend"
    return any(
        needle in text
        for _, text, _ in _scan_sources([frontend / "src", frontend / "app"])
    )


def openapi_paths() -> set[str]:
    """Paths served by the versioned FastAPI app.

    Read from the live app rather than frontend/src/api/generated/schema.d.ts:
    that file is a lagging artifact, and reading it would exempt every endpoint
    shipped since the last regeneration from the gate — the opposite of a
    ratchet. ``openapi()`` also normalizes FastAPI's converters, so
    "{content_hash:path}" arrives as "{content_hash}", matching declared rows.
    """
    from src.core.main import api_v1

    return set(api_v1.openapi()["paths"])


def schema_d_ts_paths(schema: Path | None = None) -> set[str]:
    """Paths present in the committed typed-client schema."""
    target = schema or (
        _REPO_ROOT / "frontend" / "src" / "api" / "generated" / "schema.d.ts"
    )
    text = target.read_text(encoding="utf-8")
    return set(re.findall(r'^\s{4}"(/[^"]*)":', text, re.MULTILINE))


def layer_diff(expected: set[str], actual: set[str]) -> dict[str, list[str]]:
    """Compare declared manifest inventory to live enumeration."""
    return {
        "undeclared": sorted(actual - expected),
        "missing": sorted(expected - actual),
        "shared": sorted(actual & expected),
    }
