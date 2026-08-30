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
                           (``None`` = no frontend API usage declared). A
                           prefix is not coverage: it is satisfied by one call
                           to one endpoint under that tag. Per-endpoint
                           coverage is ``UNCALLED_ENDPOINTS``, below.
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
    Area(
        "asset",
        "asset",
        "asset",
        "asset",
        "aligned",
        fe_routes=("/assets",),
        fe_api_prefixes=("/api/asset",),
    ),
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
        fe_api_prefixes=("/api/convert",),
    ),
    Area(
        "taxonomy",
        None,
        "taxonomy",
        "taxonomy",
        "exposed",
        note="No taxonomy_service module; logic lives under src/core/taxonomy/. "
        "FacilityForm ProcessTaxonomyPicker calls /api/taxonomy.",
        fe_api_prefixes=("/api/taxonomy",),
    ),
    Area(
        "file-types",
        None,
        "file-types",
        "file-types",
        "exposed",
        note="No file_types_service module; logic lives under src/core/taxonomy/file_type_taxonomy.py.",
        fe_api_prefixes=("/api/file-types",),
    ),
    Area(
        "federation",
        None,
        "federation",
        "federation",
        "exposed",
        note="No federation_service module; logic lives under src/core/federation/. "
        "Settings → Federation (F6) calls /api/federation.",
        fe_api_prefixes=("/api/federation",),
    ),
    Area(
        "llm",
        None,
        "llm",
        "llm",
        "exposed",
        note="No llm_service module; logic lives under src/core/llm/. CLI group "
        "is conditionally registered when LLM deps are available. Admin "
        "credential management is under Settings → LLM providers "
        "(fe_routes owned by the identity Area).",
        fe_api_prefixes=("/api/llm",),
    ),
    Area(
        "utility",
        None,
        "utility",
        "utility",
        "exposed",
        note=(
            "Catch-all maintenance endpoints; backs scaffold/cleanup services. "
            "Also owns /help and /icons, static frontend pages that call no "
            "service and so have no backend counterpart — declared here "
            "rather than left undeclared so the route gate stays meaningful. "
            "/help is the sitemap, keyboard shortcuts and accessibility notes, "
            "generated from the nav and shortcut data files. /icons is an "
            "unlisted internal gallery of every glyph the app ships and the "
            "process each one is wired to; nothing links to it and it is not "
            "access-controlled, because everything on it is already in the "
            "client bundle."
        ),
        fe_routes=("/", "/help", "/icons"),
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
        fe_routes=("/visualization", "/solutions"),
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
        "notes/federated-identity-spec.md Slices 1-8. Frontend Track F: Settings "
        "(admin) under /settings; F3–F6 panels landed. F8 adds self-service "
        "registration at /register and the signed-in visitor's own page at "
        "/account — Settings stays admin-only, so a registered non-admin needs "
        "somewhere that is theirs.",
        fe_routes=("/settings", "/register", "/account"),
        fe_api_prefixes=("/api/identity",),
    ),
    # --- Frontend-only surfaces: no service, no API, no CLI ---------------
    Area(
        "site-layer",
        None,
        None,
        None,
        "internal",
        note="Optional site layer (visitor gate, telemetry, whitelabel, Operator "
        "Tools) backed by Supabase ohmgr_* and OFF by default. Frontend-only "
        "by design: it is the SITE layer, never an authorization source, so it "
        "has no Python service, API tag, or CLI group. Application permissions "
        "stay with the identity area's whoami. See "
        "docs/architecture/site-layer.md.",
        fe_routes=("/operator-tools",),
    ),
    # --- Internal services: no API and no CLI by design -------------------
    Area(
        "maps-of-making",
        None,
        None,
        None,
        "internal",
        note="Bidirectional Maps of Making bridge, backed by "
        "src/core/services/mom_bridge.py. Declared rather than left silent: "
        "inventory.py globs *_service.py, so this module was invisible to the "
        "gate and passed by omission rather than by decision. No tag or group "
        "of its own on purpose — inbound (SPARQL pull, 24h cache) surfaces "
        "through the okw area's GET /api/okw/spaces and the match candidate "
        "pool; outbound is okw's GET /api/okw/{id}/spaceapi plus "
        "`ohm okw spaceapi`, which serve one facility as the SpaceAPI document "
        "MoM polls. Rename candidate (mom_bridge -> maps_of_making_service) if "
        "it ever earns its own surface.",
    ),
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


# --- Frontend API coverage ------------------------------------------------
#
# `Area.fe_api_prefixes` answers "does the frontend touch this tag at all". It
# cannot answer "does the frontend touch this endpoint", and the gap between
# those two questions was 91 of the API's 158 paths: declaring
# fe_api_prefixes=("/api/supply-tree",) is satisfied by a single call to
# /api/supply-tree/solutions while nineteen siblings go uncalled, and the gate
# stays green. Whole routers — asset, convert, file-types, match/rules — had
# never had a caller and had never failed anything.
#
# This is the per-path answer, and it is the same convention commit 32b2f15
# established for hero crumbs: a dead term is a decision and not an omission.
# Every path the versioned app serves is either called by frontend app code
# (inventory.fe_api_call_sites) or has a row here saying why not. There is no
# third state, and no prefix that can stand in for one.
#
# Granularity is the path, not the operation. 19 paths carry more than one
# method, so "the UI calls GET /api/okw/{id} but never DELETE" reads as
# covered. Deliberate: it matches the altitude of the rows above, and the
# upgrade is additive — the typed client already encodes the verb, while the
# island's get/post helpers do not, and half a signal is worse than none.

ENDPOINT_STATUSES: frozenset[str] = frozenset(
    {
        # No browser will ever call it. The row is the decision.
        "never",
        # A UI is intended. The row is the backlog, and the commit that wires
        # the call DELETES it rather than editing it — which is what makes this
        # table shrink instead of accrete.
        "planned",
        # The UI does call it; the scanner cannot see the URL because it is
        # composed across statements. `evidence` and `anchor` are mandatory and
        # are checked, so the escape hatch cannot become a blanket exemption.
        "ui_indirect",
    }
)

ENDPOINT_REASONS: frozenset[str] = frozenset(
    {
        "peer",  # another OHM node calls it, over the federation protocol
        "machine",  # a non-browser client: a poller, a probe, an orchestrator
        "operator",  # destructive with no undo; belongs behind a shell
        "cli",  # the surface is `ohm ...`; no browser equivalent planned
        "superseded",  # a different endpoint is what the UI calls instead
        "blocked",  # wanted, but the UI cannot supply what the path needs
        "composed",  # ui_indirect only: URL built from a base plus a suffix
        "backlog",  # planned only: nothing blocks it, nobody has built it
    }
)


@dataclass(frozen=True)
class Endpoint:
    """One API path and why the frontend does not (visibly) call it."""

    path: str  # exact OpenAPI path, params included: "/api/okh/{id}"
    status: str  # one of ENDPOINT_STATUSES
    reason: str  # one of ENDPOINT_REASONS
    note: str  # who DOES call it, or what has to land first
    # ui_indirect only: "<repo-relative file>:<line>" of the composed call, and
    # the substring the test greps for. Without these a ui_indirect row is an
    # unfalsifiable claim, which is the shape of every row that ever rotted.
    evidence: Optional[str] = None
    anchor: Optional[str] = None


def _decision(status: str, reason: str, note: str, *paths: str) -> tuple[Endpoint, ...]:
    """Expand ONE decision over the paths it covers.

    The unit a reader holds is the decision, not the row: the federation peer
    protocol is one decision over eight paths, and grouping it here makes this
    table sixteen paragraphs rather than ninety-one lines.

    Paths are still spelled out individually, deliberately. A prefix
    ("/api/federation/*") would re-create the exact hole this table exists to
    close — a new endpoint under that prefix would be swallowed silently
    instead of failing until someone classified it.
    """
    return tuple(Endpoint(p, status, reason, note) for p in paths)


def _composed(
    note: str, evidence: str, anchor: str, *paths: str
) -> tuple[Endpoint, ...]:
    """A ui_indirect decision: the UI calls these, the scanner cannot see it."""
    return tuple(
        Endpoint(p, "ui_indirect", "composed", note, evidence=evidence, anchor=anchor)
        for p in paths
    )


UNCALLED_ENDPOINTS: tuple[Endpoint, ...] = (
    # --- Never: another node is the client --------------------------------
    *_decision(
        "never",
        "peer",
        "Federation wire protocol. The client is another OHM node's "
        "FederationService, authenticated by followed-peer DID and rate-limited "
        "per peer — a browser has no peer DID and would be refused, and "
        "/packages/blobs additionally requires an X-OHM-Peer-DID header naming "
        "a followed peer. The catalog and records endpoints serve the "
        "deliberately redacted projection this node offers peers; the browser "
        "already has the unredacted view at /okh and /facilities, so rendering "
        "the projection would show an operator a knowingly lossy copy of data "
        "they can see whole. The UI's federation surface is the LOCAL half — "
        "/status, /peers, /sync/run, /okw/sync/run — which it calls.",
        "/api/federation/identify",
        "/api/federation/catalog",
        "/api/federation/records/{content_hash}",
        "/api/federation/sync/digest",
        "/api/federation/okw/catalog",
        "/api/federation/okw/records/{content_hash}",
        "/api/federation/okw/sync/digest",
        "/api/federation/packages/blobs/{bundle_hash}",
    ),
    *_decision(
        "never",
        "machine",
        "Machine clients that are not peers. /api/federation/health is an "
        "orchestrator's readiness probe; the UI reads /api/federation/status, "
        "which carries the sync metrics a human wants. /api/okw/{id}/spaceapi "
        "serves one facility as a SpaceAPI document for Maps of Making's "
        "poller — the outbound half of the maps-of-making capability, whose "
        "SiteDoc row already declines to assert a frontend call for this "
        "reason.",
        "/api/federation/health",
        "/api/okw/{id}/spaceapi",
    ),
    # --- Never: destructive, or a footgun behind a button ------------------
    *_decision(
        "never",
        "operator",
        "Bulk-destructive with no undo and no per-record review. "
        "/api/supply-tree/solutions/cleanup sweeps stale solutions "
        "instance-wide with no owner filter, across every caller's saved work; "
        "/api/okh/scaffold/cleanup deletes scaffolded directories by age. Both "
        "have a shell equivalent, which is where an operation nobody can undo "
        "belongs. Contrast /api/taxonomy/reload, which looks similar and is "
        "not: it fails safe, keeping the current taxonomy when the new file "
        "does not validate, so it gets a button in /settings/matching.",
        "/api/supply-tree/solutions/cleanup",
        "/api/okh/scaffold/cleanup",
    ),
    *_decision(
        "never",
        "cli",
        "Writes a directory to the SERVER's filesystem and returns its "
        "filesystem_path. A browser cannot reach the artifact it produces, so "
        "the CLI is the only caller that can do anything with the result.",
        "/api/okh/scaffold",
    ),
    # --- Never: the UI calls something else instead ------------------------
    *_decision(
        "never",
        "superseded",
        "Aliases and older shapes of endpoints the UI already calls. "
        "/api/okh/from-storage is a POST alias for GET /api/okh/{id}; "
        "/api/okh/manifests/ is an alias for /api/okh/create, and "
        "/api/okh/manifests/{id} says in its own docstring that it exists for "
        "integration-test cleanup; bare /api/okw is superseded by "
        "/api/okw/search, which is what the network view calls; "
        "/api/package/build takes a manifest dictionary, where the UI holds a "
        "stored id and calls /api/package/build/{manifest_id}.",
        "/api/okh/from-storage",
        "/api/okh/manifests/",
        "/api/okh/manifests/{id}",
        "/api/okw",
        "/api/package/build",
    ),
    *_decision(
        "never",
        "superseded",
        "The visualization bundle already carries this data. "
        "/api/supply-tree/solution/{id}/visualization returns production_"
        "sequence, dependency_graph and the KPI dashboard in one payload, and "
        "supplyTreeAdapter.ts renders all three from it under unit test. "
        "Calling these would give one picture two sources of truth. "
        "/component/{component_id} and /facility/{facility_id} are server-side "
        "filters of /trees, which the Trees table filters client-side.",
        "/api/supply-tree/solution/{solution_id}/dependencies",
        "/api/supply-tree/solution/{solution_id}/production-sequence",
        "/api/supply-tree/solution/{solution_id}/summary",
        "/api/supply-tree/solution/{solution_id}/component/{component_id}",
        "/api/supply-tree/solution/{solution_id}/facility/{facility_id}",
    ),
    *_decision(
        "never",
        "superseded",
        "Matching already saves. runMatch sends save_solution: true, so every "
        "solution the UI holds was persisted when it was produced; a second "
        "save button would be a control for something that already happened.",
        "/api/supply-tree/solution/{solution_id}/save",
    ),
    *_decision(
        "never",
        "cli",
        "Returns the JSON Schema for the format, not a record in it. Developer "
        "reference, and the OpenAPI page at /v1/docs already serves it. Note "
        "/api/okw/export and /api/okw/schema are literally the same handler — "
        "two decorators on one function in routes/okw.py.",
        "/api/okh/export",
        "/api/okw/export",
        "/api/okw/schema",
    ),
    # --- Never: the UI cannot supply what the path needs -------------------
    *_decision(
        "never",
        "blocked",
        "An id-space mismatch, not a value judgement. These take a SUPPLY-TREE "
        "id; every id the frontend holds is a SOLUTION id — /solutions, "
        "/visualization/[solutionId], and save_solution all speak solutions. "
        "Nothing in the UI has a supply-tree id to pass. The honest fix is a "
        "solution-scoped variant on the backend, not a frontend workaround.",
        "/api/supply-tree",
        "/api/supply-tree/create",
        "/api/supply-tree/{id}",
        "/api/supply-tree/{id}/export",
        "/api/supply-tree/{id}/optimize",
        "/api/supply-tree/{id}/validate",
        "/api/supply-tree/solution/load",
    ),
    *_decision(
        "never",
        "machine",
        "Developer probes for the matching engine's internals. "
        "/detect-domain takes two raw dicts and returns a confidence score for "
        "the detection heuristic — anything a user wants from it, POST "
        "/api/match already does implicitly, and the domain selector makes the "
        "override explicit. /domains/{name}/health returns Python class names "
        "and the string 'available': a registry smoke test, not a fact about "
        "the system anyone can act on.",
        "/api/match/detect-domain",
        "/api/match/domains/{domain_name}/health",
    ),
    *_decision(
        "never",
        "superseded",
        "The browser does this better. js-yaml is already a dependency, so a "
        "dropped manifest is parsed client-side and handed to the existing "
        "inline-manifest path — which gives the user a review step in "
        "TieredEditor before matching, something a multipart upload endpoint "
        "cannot. Choosing the endpoint would mean choosing the worse flow.",
        "/api/match/upload",
    ),
    *_decision(
        "never",
        "superseded",
        "Returns quality levels for a domain — the ids behind the three System "
        "Modes. Not wired, because the modes are a CURATED preset over "
        "(quality_level, strict_mode) with hand-written explanations of what "
        "each trades away, and this returns ids with server-generated labels "
        "and no strict_mode at all: it would replace three good explanations "
        "with three worse ones and leave half the hardcode standing. REVISIT "
        "when the domain selector ships and a caller can be in `cooking`, "
        "whose contexts (home/commercial/professional) the three-preset model "
        "cannot express — at that point this becomes the right source.",
        "/api/utility/contexts",
    ),
    # --- Called by the UI; the scanner cannot see the URL ------------------
    *_composed(
        "The supply-tree artifact links build one base and hang suffixes off "
        "it, so no source literal contains a whole path. Following that needs "
        "expression evaluation rather than a regex; recording it is cheaper "
        "and, unlike a looser regex, cannot go quietly wrong.",
        "frontend/src/features/visualization/ArtifactLinks.tsx:25",
        "/v1/api/supply-tree/solution/${solutionId}",
        "/api/supply-tree/solution/{solution_id}/report",
        "/api/supply-tree/solution/{solution_id}/export",
    ),
    # --- Planned: the backlog, deleted by the commit that wires the call ---
    *_decision(
        "planned",
        "backlog",
        "Calls asset_service.salvage_match and enriches a design's components "
        "with fleet availability, so it belongs to the /assets section rather "
        "than to the design catalogue — the salvage surface is where a reader "
        "is already asking which parts exist and where.",
        "/api/okh/harvest-parts",
    ),
    *_decision(
        "planned",
        "backlog",
        "Returns what GET /api/match/rules/ already carries for every rule, so "
        "the settings panel reads the list rather than fetching one at a time. "
        "A per-rule editor would want it; nothing does yet.",
        "/api/match/rules/{domain}/{rule_id}",
    ),
    *_decision(
        "planned",
        "backlog",
        "File upload as an entry method, and the repair-doc pair. /okh/upload "
        "and /okw/upload validate AND store in one step, which is the wrong "
        "shape for the guided flow — /api/convert is what the create page uses "
        "instead, because it returns a manifest without saving it. Upload "
        "earns a surface once there is a bulk path that wants it. "
        "extract-repair-docs and import-repair-doc are a genuine "
        "preview-then-commit pair worth building: the merge is deliberately "
        "conservative (new components land replaceable=false, salvageable="
        "false for a human to annotate) and the UI has to say so or the "
        "semantics go invisible.",
        "/api/okh/upload",
        "/api/okh/extract-repair-docs",
        "/api/okh/import-repair-doc",
        "/api/okw/upload",
    ),
    *_decision(
        "planned",
        "backlog",
        "The filterable index into the graph — trees by component, facility, "
        "depth and confidence. Deliberately not wired to DRIVE the graph, "
        "which is built from the visualization bundle: two sources for one "
        "picture is two truths. A table beside it is the honest pairing, and "
        "it is the next thing this page wants.",
        "/api/supply-tree/solution/{solution_id}/trees",
    ),
    *_decision(
        "never",
        "superseded",
        "One domain's detail. GET /api/match/domains already returns status, "
        "version and supported input types for every domain, which is the "
        "whole of what the selector shows — fetching one at a time would be a "
        "request per option for data already in hand.",
        "/api/match/domains/{domain_name}",
    ),
    *_decision(
        "planned",
        "backlog",
        "Both take a supply tree, so they belong on /visualization rather than "
        "on Match — validate reuses the ValidationPanel the design page "
        "already renders, and simulate projects a completion time from a start "
        "date. Next thing that page wants after the Trees table.",
        "/api/match/validate",
        "/api/match/simulate",
    ),
    *_decision(
        "planned",
        "backlog",
        "An admin read of one space's claim. The spaces panel lists spaces but "
        "cannot show the claim behind any of them.",
        "/api/identity/spaces/{space_did}/claim",
    ),
)


def uncalled_endpoint_paths() -> set[str]:
    """Paths declared as not-called-by-the-browser, any status."""
    return {e.path for e in UNCALLED_ENDPOINTS}


def endpoints_by_status(status: str) -> tuple[Endpoint, ...]:
    return tuple(e for e in UNCALLED_ENDPOINTS if e.status == status)


# --- Public documentation status ----------------------------------------
#
# The public site (docs-site/) states plainly what works today. That claim must
# come from ONE place, or it rots the way a hand-maintained roadmap does. This
# is that place.
#
# Why a separate table instead of a `doc_status` field on Area: readiness is
# per *capability*, not per code area. The `okh` area is deployed (designs list,
# detail, and create all work in the UI) while importing a design from a repo
# URL is not wired to the frontend at all — one area, two capabilities, two
# honest answers. A single field per Area cannot express that.
#
# `path` is the guides/ page documenting the capability, or None when the
# capability is real enough for users to ask about but has no page yet. Rows
# with path=None still appear on the generated "what's built" page, which is the
# point: a capability with no guide is still one users need to be able to find.

DOC_STATUSES: frozenset[str] = frozenset(
    {"deployed", "in_progress", "roadmap", "non_goal"}
)

# Valid `surface:` values for a guides/ page — which thing the page documents.
# `web` is the only surface the fe_routes check applies to (see R6 in
# tests/parity/test_docs_status.py).
DOC_SURFACES: frozenset[str] = frozenset({"web", "api", "cli", "selfhost"})

# User-facing surfaces the service/API/CLI parity gate cannot represent as a
# single Area — either because there is no code layer, or because the surface
# spans all of them. Valid `area:` values for a guides/ page all the same.
#
#   selfhost — a Docker image, make targets, and scripts. No service, no route,
#              no CLI group for the parity gate to point at.
#   api      — the HTTP API as a product surface. Every Area contributes routes
#              to it, so no single Area represents it.
DOC_ONLY_AREAS: frozenset[str] = frozenset({"selfhost", "api"})


@dataclass(frozen=True)
class SiteDoc:
    """One user-facing capability and how honestly we can describe it today."""

    area: str  # an Area.name, or a member of DOC_ONLY_AREAS
    label: str  # human-readable, as it appears on the "what's built" page
    status: str  # one of DOC_STATUSES
    path: Optional[str] = None  # guides/ page, relative to docs-site/docs/
    # API path this capability needs the FRONTEND to call, e.g.
    # "/api/okh/generate-from-url". When set and status is "deployed", R9
    # asserts the frontend actually calls it.
    #
    # Why this exists: R6 checks whether the *area* has any frontend route,
    # which is too coarse. The `okh` area has routes (browsing designs), so R6
    # would happily pass a page claiming URL-import is available even though no
    # frontend code calls that endpoint. Status is per capability; this makes
    # the evidence per capability too.
    requires_fe_call: Optional[str] = None


SITE_DOCS: tuple[SiteDoc, ...] = (
    # --- Working today ---------------------------------------------------
    SiteDoc(
        "okw",
        "Browse the facility network",
        "deployed",
        path="guides/find-your-space.md",
        requires_fe_call="/api/okw/spaces",
    ),
    SiteDoc(
        "okw",
        "Publish a facility to Maps of Making",
        "deployed",
        path="guides/publish-to-maps-of-making.md",
        # No requires_fe_call: the surface is the public endpoint plus
        # `ohm okw spaceapi`. Nothing in the frontend calls it, and MoM's
        # poller is the consumer — asserting a frontend call would be asserting
        # the wrong evidence.
    ),
    SiteDoc(
        "okw",
        "List or enrich a facility",
        "deployed",
        path="guides/list-or-enrich-your-facility.md",
    ),
    SiteDoc(
        "okh",
        "Browse and add designs",
        "deployed",
        path="guides/add-a-design.md",
        requires_fe_call="/api/okh",
    ),
    SiteDoc(
        "match",
        "Match a design to facilities",
        "deployed",
        path="guides/find-who-can-build-it.md",
        requires_fe_call="/api/match",
    ),
    SiteDoc(
        "package",
        "Build and download design packages",
        "deployed",
        path="guides/share-as-a-package.md",
        requires_fe_call="/api/package",
    ),
    SiteDoc("supply-tree", "Visualize a supply tree", "deployed"),
    SiteDoc("federation", "Follow peers and sync catalogs", "deployed"),
    SiteDoc(
        "identity",
        "Accounts, API keys, and record visibility",
        "deployed",
        path="guides/who-can-see-your-data.md",
        requires_fe_call="/api/identity",
    ),
    SiteDoc(
        "convert",
        "Convert OKH-LOSH TOML and MSF datasheets",
        "deployed",
        requires_fe_call="/api/convert",
        path="guides/bring-your-collection.md",
    ),
    SiteDoc(
        "llm",
        "Configure an LLM provider",
        "deployed",
        path="guides/configure-an-llm.md",
    ),
    SiteDoc(
        "utility",
        "Enable the site layer",
        "deployed",
        path="guides/enable-the-site-layer.md",
    ),
    SiteDoc(
        "selfhost",
        "Run your own node",
        "deployed",
        path="guides/run-your-own-node.md",
    ),
    SiteDoc(
        "selfhost",
        "Deploy a node on Azure",
        "deployed",
        path="guides/deploy-a-node-on-azure.md",
    ),
    SiteDoc(
        "selfhost",
        "Deploy a cooking-domain instance",
        "deployed",
        path="guides/deploy-a-cooking-domain-instance.md",
    ),
    SiteDoc(
        "identity",
        "Get a write key",
        "deployed",
        path="guides/get-a-write-key.md",
    ),
    SiteDoc(
        "api",
        "Use the OHM API from your own software",
        "deployed",
        path="guides/use-the-api.md",
    ),
    SiteDoc(
        "okh",
        "Generate a design from a repository URL",
        "deployed",
        path="guides/import-from-a-url.md",
        requires_fe_call="/api/okh/generate-from-url",
    ),
    # Backend + CLI exist (GET /api/okh/recipes, GET /api/okw/kitchens); the
    # frontend browse views land separately. Flip to "deployed" once the
    # frontend actually calls these endpoints (R9 checks this).
    SiteDoc(
        "okh",
        "Browse recipes",
        "in_progress",
        requires_fe_call="/api/okh/recipes",
    ),
    SiteDoc(
        "okw",
        "Browse kitchens",
        "in_progress",
        requires_fe_call="/api/okw/kitchens",
    ),
    SiteDoc(
        "rfq",
        "Generate requests for quotation",
        "deployed",
        requires_fe_call="/api/rfq/generate",
    ),
    SiteDoc(
        "convert",
        "Bulk-import a design collection",
        "deployed",
        requires_fe_call="/api/okh/import-collection",
    ),
    # --- Named so users can ask, not built yet ----------------------------
    #
    # This block said "Not reachable from the web app yet" and had stopped
    # being true of its own contents: the row directly beneath it was
    # `deployed` with frontend evidence, and RFQ — which ships with a nav row,
    # a `g r` chord and a handoff from Match — sat here claiming `roadmap`.
    # A section header that means nothing teaches the next reader to skip it,
    # so this one now says only what the rows below actually have in common.
    SiteDoc("okw", "Search facilities by name", "roadmap"),
    SiteDoc("okw", "Search facilities by material and thickness", "roadmap"),
)


def doc_areas() -> set[str]:
    """Area names a guides/ page may legitimately declare."""
    return {a.name for a in AREAS} | set(DOC_ONLY_AREAS)


def site_doc_paths() -> set[str]:
    """guides/ page paths declared by SITE_DOCS."""
    return {d.path for d in SITE_DOCS if d.path is not None}


def site_doc_for_path(path: str) -> Optional[SiteDoc]:
    """The SiteDoc row documenting ``path``, or None if undeclared."""
    for doc in SITE_DOCS:
        if doc.path == path:
            return doc
    return None


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
