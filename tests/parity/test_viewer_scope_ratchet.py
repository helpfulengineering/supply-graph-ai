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
SCOPED_SERVICES = ("okh_service", "okw_service")


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
