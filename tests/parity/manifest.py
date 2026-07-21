"""Declared contract between the Service, API, and CLI layers.

This file is the single source of truth for *which feature areas exist and how
they are exposed*. The parity test (``test_parity.py``) enumerates the real
codebase and asserts it matches what is declared here, in both directions:

  * a NEW service / route / CLI group that isn't declared here fails the build
    (you must consciously classify it), and
  * a declared mapping that no longer exists fails the build (catches renames
    and deletions).

It is a *ratchet*, not a cleanup: the rows below encode today's reality,
drift and all. Misalignments are recorded as explicit rows with a ``note`` so
they are visible and reviewed rather than silently rotting. The ``note`` fields
marked REVIEW / TODO are the prioritised backlog for any future normalisation
pass — fix them by changing the code, then update the row.

Each slot is the *real* identifier in that layer, or ``None`` when the area
intentionally has no presence there:

  * ``service``   -> stem of ``src/core/services/<stem>_service.py`` (the
                     ``_service`` suffix is dropped). ``None`` means no service
                     module follows the convention for this area.
  * ``api_tag``   -> FastAPI router ``tags=[...]`` value mounted in
                     ``src/core/main.py``.
  * ``cli_group`` -> click group name registered in ``src/cli/main.py``.
  * ``fe_routes``   -> top-level React Router path prefixes the UI exposes
                       (``None`` = no frontend surface for this area).
  * ``fe_api_prefixes`` -> ``/api/<tag>`` path prefixes the frontend calls
                           (``None`` = no frontend API usage declared).
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Optional


@dataclass(frozen=True)
class Area:
    """One feature area and how it is (or isn't) exposed across the layers."""

    name: str
    service: Optional[str]
    api_tag: Optional[str]
    cli_group: Optional[str]
    status: str  # aligned | exposed | partial | internal | review
    note: str = ""
    fe_routes: Optional[tuple[str, ...]] = None
    fe_api_prefixes: Optional[tuple[str, ...]] = None


# Click commands that are intentionally top-level utilities, not feature areas.
TOP_LEVEL_CLI = {"config", "version"}


AREAS: tuple[Area, ...] = (
    # --- Fully aligned: service + API + CLI all present -------------------
    Area(
        "okh",
        "okh",
        "okh",
        "okh",
        "aligned",
        fe_routes=("/okh",),
        fe_api_prefixes=("/api/okh",),
    ),
    Area(
        "okw",
        "okw",
        "okw",
        "okw",
        "aligned",
        fe_routes=("/facilities",),
        fe_api_prefixes=("/api/okw",),
    ),
    Area("asset", "asset", "asset", "asset", "aligned"),
    Area(
        "package",
        "package",
        "package",
        "package",
        "aligned",
        fe_routes=("/packages",),
        fe_api_prefixes=("/api/package",),
    ),
    Area(
        "match",
        "matching",
        "match",
        "match",
        "aligned",
        note="REVIEW: service is 'matching_service' while API/CLI use 'match'. "
        "Internal rename candidate (matching_service -> match_service).",
        fe_routes=("/match",),
        fe_api_prefixes=("/api/match",),
    ),
    # --- Exposed via API + CLI but no conventionally-named service --------
    Area(
        "convert",
        None,
        "convert",
        "convert",
        "exposed",
        note="REVIEW: backed by src/core/services/datasheet_converter.py, which "
        "does not follow the *_service.py convention. Rename candidate "
        "(datasheet_converter -> convert_service).",
    ),
    Area(
        "taxonomy",
        None,
        "taxonomy",
        "taxonomy",
        "exposed",
        note="No taxonomy_service module; logic lives under src/core/taxonomy/.",
    ),
    Area(
        "file-types",
        None,
        "file-types",
        "file-types",
        "exposed",
        note="No file_types_service module; logic lives under src/core/taxonomy/file_type_taxonomy.py.",
    ),
    Area(
        "federation",
        None,
        "federation",
        "federation",
        "exposed",
        note="No federation_service module; logic lives under src/core/federation/.",
    ),
    Area(
        "llm",
        None,
        "llm",
        "llm",
        "exposed",
        note="No llm_service module; logic lives under src/core/llm/. CLI group "
        "is conditionally registered when LLM deps are available.",
    ),
    Area(
        "utility",
        None,
        "utility",
        "utility",
        "exposed",
        note="Catch-all maintenance endpoints; backs scaffold/cleanup services.",
        fe_routes=("/",),
        fe_api_prefixes=("/api/utility",),
    ),
    Area(
        "supply-tree",
        None,
        "supply-tree",
        "solution",
        "exposed",
        note="REVIEW: NAME MISMATCH — API tag is 'supply-tree' but the CLI group "
        "is 'solution'. Pick one name (external surface; needs deprecation "
        "cycle, not a bare rename).",
        fe_routes=("/visualization",),
        fe_api_prefixes=("/api/supply-tree",),
    ),
    # --- Partial exposure -------------------------------------------------
    Area(
        "storage",
        "storage",
        None,
        "storage",
        "partial",
        note="Service + CLI for storage management; no public API surface "
        "(intentional — internal/admin operation).",
    ),
    Area(
        "rfq",
        None,
        "rfq",
        None,
        "partial",
        note="TODO: API only, no CLI group yet. Add a 'rfq' CLI group if this "
        "should be operable from the command line.",
        fe_routes=("/rfq",),
        fe_api_prefixes=("/api/rfq",),
    ),
    Area(
        "rules",
        None,
        "rules",
        None,
        "partial",
        note="API only (mounted under /api/match/rules). No dedicated CLI group.",
    ),
    Area(
        "system",
        None,
        None,
        "system",
        "partial",
        note="CLI-only diagnostics/admin group. No API surface by design.",
    ),
    # --- Identity: AuthenticationService exposed via the unified surface ---
    Area(
        "identity",
        "auth",
        "identity",
        "identity",
        "aligned",
        note="AuthenticationService (service stem 'auth') exposed via the unified "
        "'identity' API tag + CLI group — API keys, accounts, identities (did:key), "
        "capability grants, space claims, edge bootstrap, attestations, domain/OAuth "
        "bindings, trust-on-follow directory, and security-policy status. See "
        "notes/federated-identity-spec.md Slices 1-8.",
    ),
    # --- Internal services: no API and no CLI by design -------------------
    Area("cache", "cache", None, None, "internal", note="Caching internals."),
    Area(
        "rate_limit",
        "rate_limit",
        None,
        None,
        "internal",
        note="Rate-limiting internals.",
    ),
    Area(
        "domain",
        "domain",
        None,
        None,
        "internal",
        note="Domain registry/orchestration internals.",
    ),
    Area(
        "bom_resolution",
        "bom_resolution",
        None,
        None,
        "internal",
        note="BOM resolution internals; consumed by matching/supply-tree.",
    ),
    Area(
        "project_audit",
        "project_audit",
        None,
        None,
        "internal",
        note="Internal project audit tooling.",
    ),
    Area(
        "visualization",
        "visualization",
        None,
        None,
        "internal",
        note="REVIEW: visualization_service — confirm whether this should have a "
        "public API/CLI surface or is purely internal.",
    ),
    Area(
        "scaffold",
        "scaffold",
        None,
        None,
        "internal",
        note="REVIEW: scaffold_service is exercised via the 'utility' API "
        "endpoints (see tests/api/test_scaffold_cleanup_endpoint.py) rather "
        "than a dedicated 'scaffold' tag. Classified internal for now.",
    ),
    Area(
        "cleanup",
        "cleanup",
        None,
        None,
        "internal",
        note="REVIEW: cleanup_service is exercised via the 'utility' API "
        "endpoints rather than a dedicated tag. Classified internal for now.",
    ),
)


def expected_services() -> set[str]:
    """Service stems the manifest declares to exist."""
    return {a.service for a in AREAS if a.service is not None}


def expected_api_tags() -> set[str]:
    """API router tags the manifest declares to exist."""
    return {a.api_tag for a in AREAS if a.api_tag is not None}


def expected_cli_groups() -> set[str]:
    """CLI group names the manifest declares to exist (excluding top-level)."""
    return {a.cli_group for a in AREAS if a.cli_group is not None}


def expected_fe_routes() -> set[str]:
    """Frontend route prefixes the manifest declares."""
    routes: set[str] = set()
    for area in AREAS:
        if area.fe_routes:
            routes.update(area.fe_routes)
    return routes


def expected_fe_api_prefixes() -> set[str]:
    """Frontend API path prefixes the manifest declares."""
    prefixes: set[str] = set()
    for area in AREAS:
        if area.fe_api_prefixes:
            prefixes.update(area.fe_api_prefixes)
    return prefixes
