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
    }
)

#: Every route allowed to authorize nothing, for whatever reason.
DECLARED = UNAUTHENTICATED_DEBT | set(ANONYMOUS_BY_DESIGN)


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
