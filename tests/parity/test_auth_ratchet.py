"""Every mutating route must authorize, or be declared here (#479).

#478 was found by hand: the whole ``/v1/api/package`` surface — including
``DELETE`` — reached its handler with no ``Authorization`` header, in every
security mode, with ``API_KEYS`` set. Nothing in the build was watching. This is
the watcher, and it found that packages were three surfaces short of the whole
story: assets, supply-trees and saved solutions, ``taxonomy/reload``, scaffold,
rules and rfq authorize nothing either.

A **ratchet, not a cleanup**, in the shape of ``test_response_models.py`` (#374).
It ships with today's violators already declared, so it lands before the fixes do
and each fix finishes by **deleting rows** rather than by assertion. The
assertion is set equality, which gives both directions at once: an undeclared
violator fails, and so does a declared route that has since been protected.

A row in ``UNAUTHENTICATED_DEBT`` is a debt, not an exemption. **Adding one to
make a build pass is the failure this exists to prevent.**

The invariant, what each list means, and the procedure for removing a row are in
``docs/architecture/route-authorization.md``. Two things worth knowing before
reading the list: "mutating" keys off the HTTP method, which is a proxy — this
API uses ``POST`` for computation too, so some rows need no credential and are
listed anyway, because clearing one means reading the handler rather than
guessing from its name. And the gate introspects the built app rather than
parsing route files, because a dependency can be declared on the route, the
router, or the parent app, and ``routes/package.py`` used none of the three.
"""

from __future__ import annotations

from fastapi import FastAPI
from fastapi.routing import APIRoute
from starlette.routing import Mount

from src.core.main import app

MUTATING_METHODS = frozenset({"POST", "PUT", "PATCH", "DELETE"})

#: Qualified names of the dependencies that authorize a request.
#:
#: ``require_write`` and ``require_admin`` are closures built by
#: ``require_permission``, so they share a qualname and cannot be told apart by
#: name — which is also why matching on it catches any future inline
#: ``require_permission("…")`` for free.
AUTH_DEPENDENCY_QUALNAMES = frozenset(
    {
        "require_permission.<locals>.dependency",
        "require_admin_strict",
        "get_current_user",
        # Conditional guards count. `require_permission` is itself conditional
        # — it no-ops when SecurityPolicy relaxes writes — so "authorizes" has
        # never meant "always refuses". What matters is that the route made a
        # decision rather than having no guard at all.
        #
        # `require_write_unless_public` lets an operator open one route to
        # uncredentialed callers, and still resolves the caller when they do,
        # so work stays attributable. It composes `require_write` rather than
        # reimplementing it.
        "require_write_unless_public.<locals>.dependency",
        # Same shape again: refuses only when a request would genuinely spend
        # on an LLM, inert otherwise. Formalizes what used to be a plain
        # function called from inside the handler body — invisible to this
        # ratchet and to the OpenAPI schema, since neither inspects a route's
        # code (#344 named this "a second, invisible authorization
        # mechanism"; #485 fixed it here).
        "require_auth_for_llm_spend",
    }
)

#: Anonymous on purpose, each row citing the source that says so.
ANONYMOUS_BY_DESIGN: dict[tuple[str, str], str] = {
    # "The PEER PROTOCOL is anonymous by necessity: a peer identifies itself
    # with a DID it signs for, not with one of our API keys" — routes/federation.py.
    # Bounded by _enforce_peer_rate_limit instead of by a credential.
    ("POST", "/v1/api/federation/sync/digest"): "peer protocol",
    ("POST", "/v1/api/federation/okw/sync/digest"): "peer protocol",
    # "Self-service onboarding — deliberately unauthenticated. A node operator
    # should not be the only way to become someone on a node" — routes/identity.py.
    # Gated by SecurityPolicy.open_registration, not by a credential.
    ("POST", "/v1/api/identity/register"): "self-service onboarding",
    # "Trade a recovery code for a working key — deliberately unauthenticated.
    # The credential this returns is the one the caller lost" — routes/identity.py.
    ("POST", "/v1/api/identity/recover"): "credential recovery",
}

#: Reads that happen to use a mutating method, because the query needs a body.
#:
#: Distinct from ``ANONYMOUS_BY_DESIGN``, which is for routes that must *never*
#: authenticate. These simply are not writes, and a write permission on a read
#: would be theatre. Each row names the ``GET`` that serves the same data, so
#: the claim is checkable rather than asserted.
#:
#: A row asserts two things, both verified against the handler rather than
#: inferred from the route name: that **nothing is persisted**, and that the
#: route **discloses nothing the caller is not already entitled to**. Two shapes
#: satisfy the second, and the row's value says which:
#:
#: * *a named ``GET``* — the same data is served by that route under the same
#:   access control. Public-and-public is fine; scoped-and-identically-scoped is
#:   fine. A guarded ``GET`` beside an unguarded twin is not a read, it is a
#:   hole, and needs the guard its twin has.
#: * *``none``* — the route is a pure function of its request body. It reads no
#:   storage at all, so it can only hand back a rearrangement of what the caller
#:   already had.
#:
#: The definition has been widened twice by real cases, both times because it
#: was too narrow rather than too loose. It started as "the equivalent GET is
#: public", which #493 broke: scoping ``GET /v1/api/asset`` did not turn its
#: POST twin into a hole, because the twin was scoped in the same commit. It
#: then required *some* equivalent GET, which #498 broke: a pure formatter has
#: no server-side data to have a twin for.
#:
#: What governs *reads* is scope, not authentication —
#: ``test_viewer_scope_ratchet.py``. It covers ``okh_service`` and
#: ``okw_service`` only, so a surface outside those two has nothing watching
#: the breadth of what it returns.
READS_EXPRESSED_AS_POST: dict[tuple[str, str], str] = {
    # Reads through AssetService.list(viewer=...) and persists nothing. Scoped
    # to the caller's own assets, identically to GET /v1/api/asset (#493).
    ("POST", "/v1/api/asset/salvage-match"): "GET /v1/api/asset",
    # A pure formatter: takes selected match results in the body and returns
    # them as CSV or JSON. Reads no storage — verified, contact_export.py has
    # no imports from it — so it can only return a rearrangement of what the
    # caller sent. Requiring a write permission to reformat your own data would
    # be theatre (#498).
    ("POST", "/v1/api/match/export/contacts"): "none",
    # #486: reads OKW facilities and ranks them against a design, exactly like
    # GET /api/okw would if it took a request body. Scoped to the caller since
    # #503/#504 — the private-facility hole this route used to have is closed,
    # so declaring it here is now an honest claim rather than a wish.
    ("POST", "/v1/api/match"): "GET /v1/api/okw (scoped identically, #503/#504)",
    # Same read, addressed by facility instead of by design. Also scoped since
    # #503/#504 — a private facility 404s here exactly as GET /api/okw/{id}
    # does.
    ("POST", "/v1/api/match/facility"): "GET /v1/api/okw/{id}",
    # Loads a design by id and validates it against a supply tree — a read,
    # scoped to the design's visibility exactly as GET /api/okh/{id} is
    # (#486). Persists nothing: it renders a ValidationResult, it does not
    # write one.
    ("POST", "/v1/api/match/validate"): "GET /v1/api/okh/{id}",
    # A pure function of its request body: classifies which domain a posted
    # requirements payload belongs to. No storage read, no storage write.
    ("POST", "/v1/api/match/detect-domain"): "none",
    # Simulates executing a supply tree the caller posted. The tree is in the
    # request body, not loaded from storage, and nothing is persisted.
    ("POST", "/v1/api/match/simulate"): "none",
    # /import is not entirely a tombstone, which is why it is not in
    # REMOVED_ANSWERING_501: dry_run=True with file_content is the supported
    # comparison path #457/#459 kept, and it genuinely returns 200. The other
    # two branches (no file_content; dry_run=False) refuse with 501 before
    # reaching any of this. Reads no storage either way — the comparison runs
    # against rule sets already loaded in memory.
    ("POST", "/v1/api/match/rules/import"): "none",
    ("POST", "/v1/api/match/rules/validate"): "none",
    ("POST", "/v1/api/match/rules/compare"): "none",
    # Serializes the running node's current in-memory rule sets. A read of
    # process state, not of storage — and the process state it reads was
    # itself loaded from files shipped in the image, never written by a
    # caller.
    ("POST", "/v1/api/match/rules/export"): "none",
    # #485: validates the OKH content posted in the body against domain
    # rules. `okh_service` is injected but never called — verified by
    # reading the handler — so there is no storage access of any kind to
    # scope, identically to match/rules/validate above.
    ("POST", "/v1/api/okh/validate"): "none",
    # #485: extracts process requirements from the OKH content posted in the
    # body via `okh_service.extract_requirements(request.content)` — a pure
    # function of what the caller sent, not a lookup by id.
    ("POST", "/v1/api/okh/extract"): "none",
    # #485: already correctly scoped — reads the caller's own visible OKH
    # collection via `okh_service.list(viewer=await viewer_scope(user))` to
    # diff against an uploaded archive, and returns only the diff, never the
    # manifests themselves.
    ("POST", "/v1/api/okh/diff-collection"): "GET /api/okh (scoped identically)",
    # #513: loads one manifest by id and returns it — a read, scoped to the
    # manifest's visibility exactly as GET /api/okh/{id} is. #485 gated this
    # with require_write as a stopgap while the actual gap (no visibility
    # check at all, so an authenticated stranger read the same private
    # content an anonymous one could) was tracked separately; this is that
    # fix landing.
    ("POST", "/v1/api/okh/from-storage"): "GET /api/okh/{id}",
    # #513: same fix, applied per id in a batch — see from-storage above.
    ("POST", "/v1/api/okh/harvest-parts"): "GET /api/okh/{id}",
    # #487: builds an OKHManifest from the request body and streams back a
    # generated .docx — no storage access on any path, verified by reading
    # the handler.
    ("POST", "/v1/api/convert/to-datasheet"): "none",
    # #487: parses an uploaded .toml file in-request and returns JSON — no
    # storage access.
    ("POST", "/v1/api/convert/from-okh-losh"): "none",
    # #487: parses an uploaded .docx file in-request and returns JSON — no
    # storage access.
    ("POST", "/v1/api/convert/from-datasheet"): "none",
    # #487: runs the manufacturing extractor on `request.content` — mirrors
    # okh/extract exactly (#485), no storage access.
    ("POST", "/v1/api/okw/extract"): "none",
    # #487: `okw_service` is injected but never called in the body — mirrors
    # okh/validate exactly (#485), no storage access.
    ("POST", "/v1/api/okw/validate"): "none",
    # #487: renders RFQ documents purely from `request.solutions` and other
    # body fields — no storage access.
    ("POST", "/v1/api/rfq/generate"): "none",
}

#: Routes that were removed and answer **501** to say so, rather than 404.
#:
#: A tombstone is neither a read nor a write: it reaches no storage, returns no
#: data, and does nothing a credential could authorize. Requiring one would be
#: ceremony on a route whose entire body raises.
#:
#: Unlike the other two lists, this one is **verified rather than trusted** —
#: ``test_removed_routes_actually_answer_501`` checks each declared route really
#: is a 501, so a row cannot quietly outlive the removal it records or be added
#: to a live route to dodge the gate.
REMOVED_ANSWERING_501: frozenset[tuple[str, str]] = frozenset(
    {
        # #498: saved supply-tree solutions stopped being durable objects. Kept
        # as 501 because each had an in-repo caller; #499 deletes them once the
        # access logs show whether anything outside still calls them.
        ("POST", "/v1/api/supply-tree/solutions/cleanup"),
        ("DELETE", "/v1/api/supply-tree/solution/{solution_id}"),
        ("POST", "/v1/api/supply-tree/solution/{solution_id}/save"),
        ("POST", "/v1/api/supply-tree/solution/{solution_id}/extend"),
        # #486: a rule written here would live in one worker's process memory.
        # CapabilityRuleManager.add_rule_set is `self.rule_sets[domain] =
        # rule_set` on a module-level singleton — nothing in
        # capability_rules.py writes rules to disk at all. Same defect #457
        # described and #459 refused for applying an import and for reset;
        # these three CRUD routes did the identical thing through a different
        # door and #459 never reached them.
        ("POST", "/v1/api/match/rules/"),
        ("PUT", "/v1/api/match/rules/{domain}/{rule_id}"),
        ("DELETE", "/v1/api/match/rules/{domain}/{rule_id}"),
        # #459's own refusal, now declaring the status code on the route
        # (rather than only raising it in the body) so this verification test
        # can see it too.
        ("POST", "/v1/api/match/rules/reset"),
    }
)

#: Mutating routes that authorize nothing today. Empty as of #478 — the last
#: surface (package: build, build/{manifest_id}, download-zip, push, pull,
#: delete, pin) now resolves require_write like every other write route.
#: #344 (anonymous writes when API_KEYS is unset) is a separate policy-layer
#: question, not a route missing a dependency, so it has no row here.
UNAUTHENTICATED_DEBT: frozenset[tuple[str, str]] = frozenset()

#: Every route allowed to authorize nothing, for whatever reason.
DECLARED = (
    UNAUTHENTICATED_DEBT
    | set(ANONYMOUS_BY_DESIGN)
    | set(READS_EXPRESSED_AS_POST)
    | REMOVED_ANSWERING_501
)


def _dependency_qualnames(dependant) -> set[str]:
    """Qualified names of every callable in a route's dependency tree."""
    names: set[str] = set()
    for sub in dependant.dependencies:
        if sub.call is not None:
            names.add(getattr(sub.call, "__qualname__", ""))
        names |= _dependency_qualnames(sub)
    return names


def _authorizes(route: APIRoute) -> bool:
    return bool(_dependency_qualnames(route.dependant) & AUTH_DEPENDENCY_QUALNAMES)


def _mutating_routes(
    application: FastAPI, prefix: str = ""
) -> list[tuple[str, str, APIRoute]]:
    """(method, full path, route) for every mutating route, including sub-apps.

    The v1 API is a ``FastAPI`` mounted on the root app, so the prefix has to be
    carried down or every path comes out missing its ``/v1``.
    """
    rows: list[tuple[str, str, APIRoute]] = []
    for route in application.routes:
        if isinstance(route, APIRoute):
            for method in sorted((route.methods or set()) & MUTATING_METHODS):
                rows.append((method, prefix + route.path, route))
        elif isinstance(route, Mount) and isinstance(route.app, FastAPI):
            rows.extend(_mutating_routes(route.app, prefix + route.path))
    return rows


def _format(rows: set[tuple[str, str]]) -> str:
    return "\n".join(f"    {method:6} {path}" for method, path in sorted(rows))


def test_every_mutating_route_authorizes_or_is_declared() -> None:
    """Set equality, so the declaration can only shrink as the work lands."""
    unauthenticated = {
        (method, path)
        for method, path, route in _mutating_routes(app)
        if not _authorizes(route)
    }

    undeclared = unauthenticated - DECLARED
    assert not undeclared, (
        "These mutating routes authorize nothing and are not declared.\n"
        "Add an auth dependency — do NOT add a row to make this pass:\n"
        f"{_format(undeclared)}"
    )

    fixed = DECLARED - unauthenticated
    assert not fixed, (
        "These routes now authorize but are still declared as unauthenticated.\n"
        "Delete their rows — the list shrinks as the work lands:\n"
        f"{_format(fixed)}"
    )


def test_removed_routes_actually_answer_501() -> None:
    """A tombstone row must name a route that is really a tombstone.

    The other declarations are claims a reader has to take on trust. This one
    is checkable, so it is checked: a row that outlived its removal, or one
    added to a working route to get past the gate, fails here.
    """
    by_key = {(method, path): route for method, path, route in _mutating_routes(app)}
    not_removed = {
        key
        for key in REMOVED_ANSWERING_501
        if key not in by_key or by_key[key].status_code != 501
    }
    assert not not_removed, (
        "Declared as removed, but not answering 501:\n" f"{_format(not_removed)}"
    )
