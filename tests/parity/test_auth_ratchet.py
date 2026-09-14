"""Every mutating route must authorize, or be listed here with a reason (#479).

`#478` was found by hand: the whole ``/v1/api/package`` surface — including
``DELETE`` — reaches its handler with no ``Authorization`` header, in every
security mode, with ``API_KEYS`` set. Nothing in the build was watching, so
nothing objected. This is the watcher, and it found that packages were three
surfaces short of the whole story: assets, supply-trees and saved solutions,
taxonomy reload, scaffold, rules and rfq are unauthenticated too.

This is a **ratchet, not a cleanup**, in the shape of ``test_response_models.py``
(#374). It ships with the routes that are unauthenticated *today* already
declared, so the gate can land before the fixes do — and each fix then finishes
by **deleting rows**, rather than by someone asserting the work is done.

It fails in **both** directions, because the assertion is set equality:

  * a mutating route that is unauthenticated and undeclared fails the build, so
    the class cannot quietly reopen through a new endpoint; and
  * a declared route that has since been protected fails the build, so the list
    shrinks as the work lands instead of rotting.

A row in ``UNAUTHENTICATED_DEBT`` is a debt, not an exemption. Do not add one to
make a build pass — that is the whole failure this exists to prevent. Routes
that are anonymous *by design* go in ``ANONYMOUS_BY_DESIGN`` instead, and each
one there cites the source that says so.

**Why "mutating" is by HTTP method.** It is a proxy, and an imperfect one: this
API uses ``POST`` for computation as well as for writes, so some rows below are
almost certainly stateless request/response endpoints that need no credential.
They are still listed rather than pre-cleared, because clearing one means
asserting that a handler does not persist, and that assertion has to be *made*
against the code rather than guessed from the route name. Failing closed and
requiring the check is the point.

**Why the app is introspected rather than the route files parsed.** A dependency
can be declared on the route, on the ``APIRouter``, or on the parent app.
``routes/package.py`` uses none of the three, so an AST pass over route files
would have to model all three to be correct. Walking the built app's dependant
tree asks the question the way the server answers it.
``test_viewer_scope_ratchet.py`` parses source for a different question (a
call-site argument) and is a precedent for ratchet shape, not for this
detection.
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
#: identity of name — which is also why matching on the qualname catches any
#: future inline ``require_permission("…")`` for free.
AUTH_DEPENDENCY_QUALNAMES = frozenset(
    {
        "require_permission.<locals>.dependency",
        "require_admin_strict",
        "get_current_user",
    }
)

#: Anonymous on purpose, each with the source that says so.
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

#: Mutating routes that authorize nothing today. Every row is a debt.
#:
#: Tracked by #478 (the package surface) and #344 (the decision on whether
#: unauthenticated nodes are a supported mode at all). The rows here that are
#: neither package nor okh are the surfaces those two issues did not know about:
#: asset, supply-tree, taxonomy, scaffold, rules and rfq.
UNAUTHENTICATED_DEBT: frozenset[tuple[str, str]] = frozenset(
    {
        ("POST", "/v1/api/asset/"),
        ("POST", "/v1/api/asset/salvage-match"),
        ("DELETE", "/v1/api/asset/{id}"),
        ("PUT", "/v1/api/asset/{id}"),
        ("POST", "/v1/api/asset/{id}/claim-component"),
        ("POST", "/v1/api/asset/{id}/triage"),
        ("POST", "/v1/api/convert/from-datasheet"),
        ("POST", "/v1/api/convert/from-okh-losh"),
        ("POST", "/v1/api/convert/to-datasheet"),
        ("POST", "/v1/api/match"),
        ("POST", "/v1/api/match/detect-domain"),
        ("POST", "/v1/api/match/facility"),
        ("POST", "/v1/api/match/rules/"),
        ("POST", "/v1/api/match/rules/compare"),
        ("POST", "/v1/api/match/rules/export"),
        ("POST", "/v1/api/match/rules/import"),
        ("POST", "/v1/api/match/rules/reset"),
        ("POST", "/v1/api/match/rules/validate"),
        ("DELETE", "/v1/api/match/rules/{domain}/{rule_id}"),
        ("PUT", "/v1/api/match/rules/{domain}/{rule_id}"),
        ("POST", "/v1/api/match/simulate"),
        ("POST", "/v1/api/match/upload"),
        ("POST", "/v1/api/match/validate"),
        ("POST", "/v1/api/okh/diff-collection"),
        ("POST", "/v1/api/okh/extract"),
        ("POST", "/v1/api/okh/extract-repair-docs"),
        ("POST", "/v1/api/okh/from-storage"),
        ("POST", "/v1/api/okh/generate-from-url"),
        ("POST", "/v1/api/okh/generate-from-url/jobs"),
        ("POST", "/v1/api/okh/generate-from-url/jobs/{job_id}/revoke"),
        ("POST", "/v1/api/okh/harvest-parts"),
        ("POST", "/v1/api/okh/import-collection"),
        ("POST", "/v1/api/okh/import-repair-doc"),
        ("POST", "/v1/api/okh/scaffold"),
        ("POST", "/v1/api/okh/scaffold/cleanup"),
        ("POST", "/v1/api/okh/upload"),
        ("POST", "/v1/api/okh/validate"),
        ("POST", "/v1/api/okw/extract"),
        ("POST", "/v1/api/okw/upload"),
        ("POST", "/v1/api/okw/validate"),
        ("POST", "/v1/api/package/build"),
        ("POST", "/v1/api/package/build/{manifest_id}"),
        ("POST", "/v1/api/package/download-zip"),
        ("POST", "/v1/api/package/pull"),
        ("POST", "/v1/api/package/push"),
        ("DELETE", "/v1/api/package/{org}/{project}/{version}"),
        ("POST", "/v1/api/package/{org}/{project}/{version}/pin"),
        ("POST", "/v1/api/rfq/generate"),
        ("POST", "/v1/api/supply-tree/create"),
        ("POST", "/v1/api/supply-tree/solution/load"),
        ("DELETE", "/v1/api/supply-tree/solution/{solution_id}"),
        ("POST", "/v1/api/supply-tree/solution/{solution_id}/extend"),
        ("POST", "/v1/api/supply-tree/solution/{solution_id}/save"),
        ("POST", "/v1/api/supply-tree/solutions/cleanup"),
        ("DELETE", "/v1/api/supply-tree/{id}"),
        ("PUT", "/v1/api/supply-tree/{id}"),
        ("POST", "/v1/api/supply-tree/{id}/optimize"),
        ("POST", "/v1/api/supply-tree/{id}/validate"),
        ("POST", "/v1/api/taxonomy/reload"),
    }
)


def _dependency_calls(dependant) -> list[object]:
    """Every callable in a route's dependency tree, at any depth."""
    found: list[object] = []
    for sub in dependant.dependencies:
        if sub.call is not None:
            found.append(sub.call)
        found.extend(_dependency_calls(sub))
    return found


def _authorizes(route: APIRoute) -> bool:
    qualnames = {
        getattr(call, "__qualname__", "") for call in _dependency_calls(route.dependant)
    }
    return bool(qualnames & AUTH_DEPENDENCY_QUALNAMES)


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
    actual = {
        (method, path)
        for method, path, route in _mutating_routes(app)
        if not _authorizes(route)
    }
    declared = UNAUTHENTICATED_DEBT | set(ANONYMOUS_BY_DESIGN)

    undeclared = actual - declared
    assert not undeclared, (
        "These mutating routes authorize nothing and are not declared.\n"
        "Add an auth dependency — do NOT add a row to make this pass:\n"
        f"{_format(undeclared)}"
    )

    fixed = declared - actual
    assert not fixed, (
        "These routes now authorize but are still declared as unauthenticated.\n"
        "Delete their rows — the list shrinks as the work lands:\n"
        f"{_format(fixed)}"
    )


def test_no_route_documents_a_401_it_cannot_return() -> None:
    """A schema advertising unenforced auth is its own defect (#344).

    Derived from the same declaration, so it cannot drift independently: as auth
    lands and rows are deleted, these 401 documentations become true rather than
    needing a second cleanup.
    """
    declared = UNAUTHENTICATED_DEBT | set(ANONYMOUS_BY_DESIGN)
    offenders = {
        (method, path)
        for method, path, route in _mutating_routes(app)
        if not _authorizes(route)
        and (method, path) not in declared
        and "401" in {str(code) for code in (route.responses or {})}
    }
    assert not offenders, (
        "These routes document a 401 they can never return:\n" f"{_format(offenders)}"
    )
