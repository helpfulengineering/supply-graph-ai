"""Contract: file-type and utility payloads are frozen before they gain models.

Same reasoning as the taxonomy contract, one router over: these returned bare
``SuccessResponse`` values annotated ``-> Any``, so codegen emitted nothing and
the frontend guessed. ``response_model`` filters, so the goldens are captured
BEFORE the models and the models are correct exactly when they still pass.

``/api/utility/domains`` is the route behind #369: the frontend bound a
selector to the display name because nothing told it there was an ``id``.

``/api/utility/metrics`` is frozen STRUCTURALLY rather than by value: it is a
counter payload, and its nested cache stats (hits, misses, size) move with
whatever else has run in the same session. Freezing those made the golden
order-dependent — it passed alone and failed inside the full suite. Keys are
what a response model can drop, so keys are what this freezes.

``/api/utility/metrics`` also deliberately carries no response model: it returns four different shapes depending on its parameters — a
Prometheus text body, per-endpoint metrics, a summary, or a detailed breakdown
— and one model would filter three of them into nonsense. Freezing it anyway is
worth it: the capture is what a later change splitting the route would be
written against, and until then this notices if its shape moves.

To change a contract deliberately:
    BLESS_FILETYPES_UTILITY_CONTRACT=1 .venv/bin/python -m pytest \
        tests/api/test_filetypes_utility_contract.py
"""

from __future__ import annotations

import json
import os
import re
from pathlib import Path

import httpx
import pytest
from fastapi import FastAPI

GOLDEN_DIR = Path(__file__).parent / "golden"
REPO_ROOT = Path(__file__).resolve().parents[2]

ROUTES = [
    ("/v1/api/file-types", "file_types_index"),
    ("/v1/api/file-types/validate", "file_types_validate"),
    ("/v1/api/utility/domains", "utility_domains"),
    ("/v1/api/utility/metrics", "utility_metrics"),
]

#: Counters and clocks that move between two calls in the same run. Frozen so
#: the test fails on a contract change rather than on the passage of time.
VOLATILE_KEYS = {
    "timestamp",
    "request_id",
    "uptime_seconds",
    "total_requests",
    "recent_requests_1h",
    "processing_time",
    "memory_usage_mb",
    "cpu_percent",
}


async def _app() -> FastAPI:
    """The mounted app, with domains registered as startup would.

    Without this the registry is empty and /domains returns `domains: []` —
    a golden that pins the envelope and says nothing about the item shape,
    which is the half most worth freezing. The frontend bug in #369 was in an
    item field.
    """
    from src.core.main import api_v1, register_domain_components

    await register_domain_components()
    app = FastAPI()
    app.mount("/v1", api_v1)
    return app


def _freeze(node):
    """Replace values that legitimately differ run to run, at any depth."""
    if isinstance(node, dict):
        return {
            k: ("<volatile>" if k in VOLATILE_KEYS else _freeze(v))
            for k, v in node.items()
        }
    if isinstance(node, list):
        return [_freeze(v) for v in node]
    return node


#: Routes whose values legitimately move between runs; only their keys are
#: frozen. Everything else is compared exactly.
SHAPE_ONLY = {"utility_metrics"}


def _structure(node: dict) -> dict:
    """The top-level key set, and nothing below it.

    Deliberately shallow. The sub-payloads here are keyed by things that come
    and go — error codes seen, endpoints touched, cache entries — so descending
    would make the signature depend on what else ran, which is the flakiness
    this is meant to remove. The top-level keys are what a response model could
    drop, and they are what a client reads.
    """
    return {k: "*" for k in sorted(node)}


def _normalise(payload: dict, name: str) -> dict:
    text = re.sub(re.escape(str(REPO_ROOT)), "<repo>", json.dumps(payload))
    body = json.loads(text)
    return _structure(body) if name in SHAPE_ONLY else _freeze(body)


@pytest.mark.asyncio
@pytest.mark.contract
@pytest.mark.parametrize("path,name", ROUTES)
async def test_payload_is_field_identical_to_the_golden(path, name):
    app = await _app()
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.get(path)

    assert response.status_code == 200, response.text
    body = _normalise(response.json(), name)

    golden = GOLDEN_DIR / f"{name}.json"
    if os.getenv("BLESS_FILETYPES_UTILITY_CONTRACT"):
        GOLDEN_DIR.mkdir(parents=True, exist_ok=True)
        golden.write_text(json.dumps(body, indent=2, sort_keys=True) + "\n")
        pytest.skip(f"golden re-blessed: {golden.name}")

    assert golden.exists(), (
        f"No golden at {golden}. Capture one with "
        "BLESS_FILETYPES_UTILITY_CONTRACT=1 BEFORE adding a response_model."
    )
    assert body == json.loads(golden.read_text()), (
        f"GET {path} changed shape. If a response_model was just added, it is "
        "filtering a field the route used to return."
    )
