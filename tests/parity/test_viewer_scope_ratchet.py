"""Every request handler that lists records must say whose view it is (#403).

``list(viewer=None)`` is unscoped and returns private records — correct for the
federation catalogue builder and the CLI, catastrophic in a request handler,
where it serves every private record on the node to anyone who asks.

The default has to stay permissive for those internal callers, so this is the
thing that stops a new route from inheriting it silently. It fails in one
direction only: a route that lists without a scope.
"""

from __future__ import annotations

import ast
from pathlib import Path

ROUTES = Path(__file__).resolve().parents[2] / "src" / "core" / "api" / "routes"

# Services whose list() is visibility-scoped. A service added here without the
# parameter will fail loudly at import, which is the intended order of events.
SCOPED_SERVICES = ("okh_service", "okw_service", "asset_service")


def _list_calls_missing_a_viewer(tree: ast.AST) -> list[int]:
    offenders: list[int] = []
    for node in ast.walk(tree):
        if not isinstance(node, ast.Call):
            continue
        func = node.func
        if not isinstance(func, ast.Attribute) or func.attr != "list":
            continue
        receiver = func.value
        name = receiver.id if isinstance(receiver, ast.Name) else None
        if name not in SCOPED_SERVICES:
            continue
        if not any(kw.arg == "viewer" for kw in node.keywords):
            offenders.append(node.lineno)
    return offenders


def test_no_route_lists_records_without_a_viewer_scope() -> None:
    offenders: dict[str, list[int]] = {}
    for path in sorted(ROUTES.glob("*.py")):
        tree = ast.parse(path.read_text(), filename=str(path))
        lines = _list_calls_missing_a_viewer(tree)
        if lines:
            offenders[path.name] = lines

    assert not offenders, (
        "Route handlers call a scoped service's list() without viewer=:\n"
        + "\n".join(f"    {f}: line(s) {ls}" for f, ls in offenders.items())
        + "\n-> pass viewer=await viewer_scope(user). Without it the handler "
        "returns every private record on the node to any caller."
    )


def test_the_ratchet_can_actually_fail() -> None:
    """A guard nobody has seen fail is a guard nobody knows works."""
    bad = ast.parse("async def r(): await okh_service.list(page=1, page_size=10)")
    assert _list_calls_missing_a_viewer(bad) == [1]

    good = ast.parse("async def r(): await okh_service.list(page=1, viewer=v)")
    assert _list_calls_missing_a_viewer(good) == []


# ---------------------------------------------------------------------------
# The same question, one frame lower (#503)
# ---------------------------------------------------------------------------

SERVICES = Path(__file__).resolve().parents[2] / "src" / "core" / "services"

#: ``<file>.<method>`` that calls its own ``list()`` without passing a viewer,
#: and why that is correct.
#:
#: A row is a claim that every caller is a trusted unscoped one. ``CLAUDE.md``
#: names exactly two — the federation catalogue builder and the CLI — so a row
#: naming anything else should not be believed without evidence.
UNSCOPED_BY_DESIGN: dict[str, str] = {
    "okh_service.py.list_manifests": "CLI only (src/cli/okh.py)",
    "okh_service.py.backfill_manufacturing_processes": "CLI only (src/cli/okh.py)",
    "okw_service.py.list_facilities": "CLI only (src/cli/okw.py)",
}


def _self_list_calls_missing_a_viewer(tree: ast.AST) -> dict[str, list[int]]:
    """``self.list(...)`` without ``viewer=``, keyed by enclosing method."""
    offenders: dict[str, list[int]] = {}
    for parent in ast.walk(tree):
        if not isinstance(parent, (ast.AsyncFunctionDef, ast.FunctionDef)):
            continue
        for node in ast.walk(parent):
            if not isinstance(node, ast.Call):
                continue
            func = node.func
            if not isinstance(func, ast.Attribute) or func.attr != "list":
                continue
            receiver = func.value
            if not (isinstance(receiver, ast.Name) and receiver.id == "self"):
                continue
            if any(kw.arg == "viewer" for kw in node.keywords):
                continue
            offenders.setdefault(parent.name, []).append(node.lineno)
    return offenders


def test_no_service_lists_its_own_records_without_a_viewer() -> None:
    """The gap #503 went through.

    The route-level check above is the one that existed, and it could not see
    this: ``POST /api/match`` reached ``OKWService.list()`` through two service
    helpers, so no route file contained an unscoped call. A private facility was
    matchable by anyone, and the match response carried the whole record.

    Passing ``viewer=None`` explicitly still satisfies this. That is the point —
    the author has to decide and write it down, rather than inheriting a default
    that happens to mean "show everything".
    """
    offenders: dict[str, list[int]] = {}
    # Only the services whose list() is visibility-scoped. StorageService has a
    # list() of its own — object keys, not records — and it is not this
    # question; scanning it would report noise and train people to ignore this.
    for stem in SCOPED_SERVICES:
        path = SERVICES / f"{stem}.py"
        if not path.exists():
            continue
        tree = ast.parse(path.read_text(), filename=str(path))
        for method, lines in _self_list_calls_missing_a_viewer(tree).items():
            if f"{path.name}.{method}" in UNSCOPED_BY_DESIGN:
                continue
            offenders[f"{path.name}.{method}"] = lines

    assert not offenders, (
        "A scoped service calls its own list() without viewer=:\n"
        + "\n".join(f"    {k}: line(s) {v}" for k, v in offenders.items())
        + "\n-> thread the caller's scope through, or declare it in "
        "UNSCOPED_BY_DESIGN with the trusted callers named."
    )


def test_declared_unscoped_methods_still_exist() -> None:
    """Fails in the other direction, so the list shrinks rather than rotting."""
    stale = []
    for key in UNSCOPED_BY_DESIGN:
        filename, method = key.rsplit(".", 1)
        path = SERVICES / filename
        if not path.exists():
            stale.append(key)
            continue
        tree = ast.parse(path.read_text(), filename=str(path))
        if method not in _self_list_calls_missing_a_viewer(tree):
            stale.append(key)
    assert not stale, (
        "Declared as unscoped by design, but no longer calling list() "
        f"without a viewer: {stale}. Delete the row."
    )
