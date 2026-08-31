"""A handler that promises a dict must not return the envelope object (#439).

``create_success_response`` returns a ``SuccessResponse`` model. FastAPI
validates whatever a handler returns against the response model it declares, so
handing that object back where a *dict* was promised fails validation and the
route answers 500 — after computing the entire payload. Nothing about it looks
wrong at the call site, and the failure is invisible until someone calls the
route.

It has happened twice:

- ``POST /api/match`` (#439). The handler is annotated ``-> dict[str, Any]``,
  which FastAPI uses as the response model when none is declared, and its
  nested branch returned ``_format_nested_response(...)`` — a helper itself
  annotated ``-> dict`` that returned the envelope object. Every nested request
  500'd, and nothing exercised that branch.
- Six ``/api/package`` routes, which declared ``response_model=Dict[str, Any]``
  and returned the object. Three were called by the UI. Two routes in the same
  file already called ``.model_dump(mode="json")`` for exactly this reason, so
  the file carried the bug and its own remedy side by side.

Both fixes are one line, and neither is discoverable. This is the check that
makes the third occurrence impossible.

**Direction.** It fails in one direction only: a *dict* promise met with an
envelope object. Returning the object where a ``SuccessResponse`` subclass is
declared is correct and is not flagged; so is returning a dict anywhere.

**Limit.** It reads the declaration, so an unannotated helper with no
``response_model`` is invisible to it. That is deliberate — the check stays
exact rather than guessing — and it is why the two historical bugs are both
caught: each declared a dict somewhere.
"""

from __future__ import annotations

import ast
from pathlib import Path

ROUTES = Path(__file__).resolve().parents[2] / "src" / "core" / "api" / "routes"

ENVELOPE_BUILDERS = {"create_success_response", "create_error_response"}


def _is_dict_annotation(node: ast.expr | None) -> bool:
    """``dict``, ``Dict``, ``dict[str, Any]``, ``Dict[str, Any]`` — nothing else."""
    if node is None:
        return False
    if isinstance(node, ast.Name):
        return node.id in {"dict", "Dict"}
    if isinstance(node, ast.Subscript):
        return _is_dict_annotation(node.value)
    if isinstance(node, ast.Attribute):  # typing.Dict
        return node.attr in {"dict", "Dict"}
    return False


def _declares_a_dict(func: ast.FunctionDef | ast.AsyncFunctionDef) -> str | None:
    """Why this function promises a dict, or None if it does not."""
    if _is_dict_annotation(func.returns):
        return "its return annotation"

    for decorator in func.decorator_list:
        if not isinstance(decorator, ast.Call):
            continue
        for keyword in decorator.keywords:
            if keyword.arg == "response_model" and _is_dict_annotation(keyword.value):
                return "response_model"
    return None


def _returns_a_bare_envelope(func: ast.AST) -> list[int]:
    """Lines returning ``create_*_response(...)`` without dumping it to a dict.

    Only a bare call counts. ``...model_dump(mode="json")`` is an Attribute
    call on the result, not the call itself, which is exactly the fix.
    """
    offenders: list[int] = []
    for node in ast.walk(func):
        if not isinstance(node, ast.Return) or not isinstance(node.value, ast.Call):
            continue
        called = node.value.func
        if isinstance(called, ast.Name) and called.id in ENVELOPE_BUILDERS:
            offenders.append(node.lineno)
    return offenders


def test_no_handler_returns_an_envelope_object_where_a_dict_is_declared() -> None:
    offenders: dict[str, list[str]] = {}

    for path in sorted(ROUTES.glob("*.py")):
        tree = ast.parse(path.read_text(), filename=str(path))
        for node in ast.walk(tree):
            if not isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                continue
            reason = _declares_a_dict(node)
            if reason is None:
                continue
            lines = _returns_a_bare_envelope(node)
            if lines:
                offenders.setdefault(path.name, []).append(
                    f"{node.name} (promises a dict via {reason}) at line(s) {lines}"
                )

    assert not offenders, (
        "Handlers return the envelope object where a dict is declared:\n"
        + "\n".join(
            f"    {f}:\n" + "\n".join(f"        {o}" for o in os)
            for f, os in offenders.items()
        )
        + "\n-> FastAPI validates the return against the declared model, and a "
        "SuccessResponse is not a dict, so this route answers 500 for every "
        "caller after building the whole payload.\n"
        '-> Fix: append .model_dump(mode="json"), or declare a real '
        "SuccessResponse subclass as the response_model and return the object."
    )
