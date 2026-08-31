"""Every route the frontend calls must declare a response model.

A route that returns a bare ``dict`` produces no response schema, so
``openapi-typescript`` generates no type for it and the frontend fills the gap
with a hand-written guess the compiler cannot check. That is the mechanism
behind #369: ``root_components`` was typed ``string[]`` against a list of
objects, and rendering it threw React #31 in front of a user.

This is a *ratchet*, not a cleanup. ``ALLOWLIST`` records the routes that are
untyped today so the gate can be added before the work of converting them is
done (#373). It fails in both directions, like ``manifest.py``:

  * a frontend-called route that is untyped and unlisted fails the build, so
    the class cannot quietly reopen through a new endpoint; and
  * a listed route that has since been typed fails the build, so the list
    shrinks as the work lands instead of rotting.

"Frontend-called" is not re-derived here. It comes from
``inventory.fe_api_call_sites``, the same source the API-coverage gate uses, so
there is one definition of the question and failures can name the call site.

The procedure for converting a route is in
``docs/architecture/api-response-contracts.md``. Do not add rows to shorten
that work — a row is a debt, and the golden-capture step exists because
``response_model`` silently filters undeclared fields.
"""

from __future__ import annotations

import json

from .inventory import fe_api_call_sites

HTTP_METHODS = {"get", "post", "put", "delete", "patch"}

# (METHOD, path) pairs that are called by the frontend and still untyped.
# Each row is a debt to be removed by #373, not a permanent exemption.
ALLOWLIST: frozenset[tuple[str, str]] = frozenset(
    {
        # These four stream a file rather than a JSON body — a collection
        # archive, a .docx datasheet, a zip of several packages, and one
        # package's archive. A response model describes a JSON body and there
        # is none to describe: permanent exceptions, not work left undone.
        ("GET", "/api/okh/export-collection"),
        ("POST", "/api/convert/to-datasheet"),
        ("POST", "/api/package/download-zip"),
        ("GET", "/api/package/{org}/{project}/{version}/download"),
        # Cannot be typed as one model: /metrics returns four different shapes
        # depending on its parameters — a Prometheus text body, per-endpoint
        # metrics, a summary, or a detailed breakdown. A single response_model
        # would filter three of them into nonsense. Splitting the route is the
        # real fix, and is not this change.
        ("GET", "/api/utility/metrics"),
    }
)


def _declares_a_response_model(operation: dict) -> bool:
    """Does this operation's success response carry a real schema?

    A declared ``response_model`` renders as a ``$ref`` — directly, or inside
    ``items`` for a list return. Without one FastAPI emits a placeholder with
    only an auto-generated ``title``, or ``additionalProperties: true`` for a
    ``Dict[str, Any]`` annotation. Neither gives codegen anything to name, which
    is the property this gate is about.

    An operation with no JSON success body (204, a file download) has nothing to
    type and is not a debt.
    """
    for code in ("200", "201"):
        response = (operation.get("responses") or {}).get(code) or {}
        schema = ((response.get("content") or {}).get("application/json") or {}).get(
            "schema"
        )
        if schema is None:
            continue
        return "$ref" in json.dumps(schema)
    return True


def _untyped_frontend_routes() -> dict[tuple[str, str], str]:
    """Frontend-called operations with no response model, mapped to a call site."""
    from src.core.main import api_v1

    spec = api_v1.openapi()
    call_sites = fe_api_call_sites()
    found: dict[tuple[str, str], str] = {}
    for path, site in call_sites.items():
        for method, operation in (spec["paths"].get(path) or {}).items():
            if method.lower() not in HTTP_METHODS:
                continue
            if not _declares_a_response_model(operation):
                found[(method.upper(), path)] = site
    return found


def test_no_new_untyped_frontend_route():
    """A frontend-called route without a response model must be declared."""
    untyped = _untyped_frontend_routes()
    undeclared = {
        route: site for route, site in untyped.items() if route not in ALLOWLIST
    }
    assert not undeclared, (
        "These routes are called by the frontend and declare no response_model, "
        "so codegen cannot type them and the client must guess:\n"
        + "\n".join(
            f"  {method} {path}\n      called from {site}"
            for (method, path), site in sorted(undeclared.items())
        )
        + "\n\nAdd a response model — the procedure, including the golden-capture "
        "step that proves the model filters nothing, is in "
        "docs/architecture/api-response-contracts.md.\n"
        "If it genuinely cannot be typed, add a row to ALLOWLIST in "
        "tests/parity/test_response_models.py with the reason."
    )


def test_allowlist_has_no_stale_rows():
    """A row that is now typed, or no longer called, must be removed."""
    stale = ALLOWLIST - set(_untyped_frontend_routes())
    assert not stale, (
        "These ALLOWLIST rows are no longer untyped frontend-called routes — "
        "they have been given a response model, or the frontend stopped calling "
        "them:\n"
        + "\n".join(f"  {method} {path}" for method, path in sorted(stale))
        + "\n\nRemove them. The list is a shrinking debt (#373); leaving a row "
        "behind hides the next regression at that route."
    )
