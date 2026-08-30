"""Contract: the taxonomy routes are shape-frozen before they gain response models.

Each of these returned a bare ``SuccessResponse`` annotated ``-> Any``, so
FastAPI inferred no schema, ``openapi-typescript`` emitted no type, and the
frontend had nothing to check a hand-written one against (#369, #373).

Adding ``response_model`` is what fixes that, and it is also what makes this
test necessary: ``response_model`` FILTERS. Any field the model does not
declare is silently dropped from the JSON, so a model written by reading the
route can delete a field a client reads — the same class of bug, introduced by
its own fix.

So the payloads are frozen against goldens captured from the routes BEFORE the
models existed. The models are correct exactly when this test still passes.

To change a contract deliberately:
    BLESS_TAXONOMY_CONTRACT=1 .venv/bin/python -m pytest \
        tests/api/test_taxonomy_contract.py
and commit the regenerated golden with the reason in the message.
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
    ("get", "/v1/api/taxonomy", "taxonomy_index"),
    ("post", "/v1/api/taxonomy/reload", "taxonomy_reload"),
    ("get", "/v1/api/taxonomy/validate", "taxonomy_validate"),
]


def _app() -> FastAPI:
    from src.core.main import api_v1

    app = FastAPI()
    app.mount("/v1", api_v1)
    return app


def _normalise(payload: dict) -> dict:
    """Drop what legitimately differs between runs and between machines.

    ``timestamp`` and ``request_id`` are per-request. ``source`` is an absolute
    path to the YAML on this checkout, so freezing it would pin the golden to
    one developer's directory layout.
    """
    text = json.dumps(payload)
    text = re.sub(re.escape(str(REPO_ROOT)), "<repo>", text)
    body = json.loads(text)
    body.pop("timestamp", None)
    body.pop("request_id", None)
    return body


@pytest.mark.asyncio
@pytest.mark.contract
@pytest.mark.parametrize("method,path,name", ROUTES)
async def test_payload_is_field_identical_to_the_golden(method, path, name):
    app = _app()
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.request(method, path)

    assert response.status_code == 200, response.text
    body = _normalise(response.json())

    golden = GOLDEN_DIR / f"{name}.json"
    if os.getenv("BLESS_TAXONOMY_CONTRACT"):
        GOLDEN_DIR.mkdir(parents=True, exist_ok=True)
        golden.write_text(json.dumps(body, indent=2, sort_keys=True) + "\n")
        pytest.skip(f"golden re-blessed: {golden.name}")

    assert golden.exists(), (
        f"No golden at {golden}. Capture one with BLESS_TAXONOMY_CONTRACT=1 "
        "BEFORE adding a response_model."
    )
    assert body == json.loads(golden.read_text()), (
        f"{method.upper()} {path} changed shape. If a response_model was just "
        "added, it is filtering a field the route used to return."
    )
