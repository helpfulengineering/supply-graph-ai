"""Freeze a response's shape, so adding a model can be shown to filter nothing.

A ``response_model`` silently drops any field it does not declare, which is the
failure the whole convention in ``docs/architecture/api-response-contracts.md``
exists to prevent. The procedure is: capture the real payload, add the model,
assert the payload is unchanged. This is the "capture" half.

Shape rather than values, because the integration client is session-scoped:
counts, ids and timestamps depend on what else ran, and freezing them makes a
strict-looking test that is really a flaky one. Keys are what a model can drop,
so keys are what this freezes.

Extracted after the third identical copy appeared. Note that
``tests/api/test_filetypes_utility_contract.py`` deliberately keeps its own,
shallower version — its sub-payloads are keyed by things that come and go, so
descending would reintroduce exactly the flakiness above. That one is a
different function that happens to share a name, not a copy of this.
"""

from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any

import pytest

GOLDEN_DIR = Path(__file__).resolve().parent / "api" / "golden"


def structure(node: Any) -> Any:
    """Every key kept, every leaf reduced to a mark; lists merged to one item.

    Merging list items into one is what lets a populated list freeze an item
    *shape* without freezing how many came back.
    """
    if isinstance(node, dict):
        return {k: structure(v) for k, v in sorted(node.items())}
    if isinstance(node, list):
        merged: dict = {}
        for item in node:
            shaped = structure(item)
            if not isinstance(shaped, dict):
                return ["*"]
            for key, value in shaped.items():
                merged.setdefault(key, value)
        return [dict(sorted(merged.items()))] if merged else []
    return "*"


def assert_shape(body: Any, name: str, bless_env: str) -> None:
    """Compare ``body``'s shape to the golden ``name``, or re-bless it.

    ``bless_env`` is the environment variable that re-captures — named per
    suite rather than shared, so re-blessing one contract cannot quietly
    re-bless every other one in the same run.
    """
    golden = GOLDEN_DIR / f"{name}.json"
    shape = structure(body)

    if os.getenv(bless_env):
        golden.parent.mkdir(parents=True, exist_ok=True)
        golden.write_text(json.dumps(shape, indent=2, sort_keys=True) + "\n")
        pytest.skip(f"golden {name} re-blessed")

    assert golden.exists(), (
        f"No golden at {golden}. Capture one with {bless_env}=1 BEFORE adding "
        "a response_model, or it proves nothing."
    )
    assert shape == json.loads(golden.read_text()), (
        f"{name} changed shape. If a response_model was just added, it is "
        "filtering a field the route used to return."
    )
