"""Contract tests for POST /api/rfq/generate.

Covers the cooking-domain branch (recipe + kitchen) added alongside the
existing manufacturing-domain branch (OKH design + facility), and guards
against the manufacturing default regressing when `domain` is omitted.
"""

from __future__ import annotations

import os
import sys

import httpx
import pytest
from fastapi import FastAPI

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../../")))


def _get_app() -> FastAPI:
    from src.core.main import api_v1

    app = FastAPI()
    app.mount("/v1", api_v1)
    return app


def _solution(**overrides) -> dict:
    data = {
        "facility_id": "kitchen-1",
        "facility_name": "Test Kitchen",
        "confidence": 0.65,
        "score": 0.65,
        "rank": 1,
        "tree": {},
        "facility": {"location": {"city": "Portland", "country": "US"}},
    }
    data.update(overrides)
    return data


@pytest.mark.asyncio
@pytest.mark.contract
async def test_generate_rfq_cooking_domain_uses_recipe_fields():
    app = _get_app()
    payload = {
        "domain": "cooking",
        "recipe_id": "recipe-1",
        "recipe_title": "Chocolate Chip Cookies",
        "recipe": {
            "ingredients": ["flour", "sugar", "chocolate chips"],
            "equipment": ["oven", "spatula"],
        },
        "quantity": 3,
        "solutions": [
            _solution(explanation_human="✓ Test Kitchen MATCHED (confidence: 65%)")
        ],
    }

    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(
        transport=transport, base_url="http://testserver"
    ) as client:
        resp = await client.post("/v1/api/rfq/generate", json=payload)

    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["data"]["total_rfqs"] == 1
    assert body["data"]["recipe_id"] == "recipe-1"
    assert body["data"]["recipe_title"] == "Chocolate Chip Cookies"

    doc = body["data"]["rfqs"][0]
    assert doc["facility_name"] == "Test Kitchen"
    assert doc["quantity"] == 3
    assert "Chocolate Chip Cookies" in doc["text"]
    assert "flour, sugar, chocolate chips" in doc["text"]
    assert "oven, spatula" in doc["text"]
    assert "✓ Test Kitchen MATCHED (confidence: 65%)" in doc["text"]
    # Cooking RFQs never carry an OKH manifest.
    assert doc["okh_manifest"] is None


@pytest.mark.asyncio
@pytest.mark.contract
async def test_generate_rfq_manufacturing_domain_is_default():
    app = _get_app()
    payload = {
        "okh_id": "okh-1",
        "okh_title": "Widget",
        "quantity": 1,
        "solutions": [_solution()],
    }

    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(
        transport=transport, base_url="http://testserver"
    ) as client:
        resp = await client.post("/v1/api/rfq/generate", json=payload)

    assert resp.status_code == 200, resp.text
    body = resp.json()
    doc = body["data"]["rfqs"][0]
    assert "Widget" in doc["text"]
    assert "Manufacturing Quotation Request" in doc["text"]


@pytest.mark.asyncio
@pytest.mark.contract
async def test_generate_rfq_cooking_domain_falls_back_without_explanation():
    app = _get_app()
    payload = {
        "domain": "cooking",
        "recipe_id": "recipe-2",
        "recipe_title": "Snickerdoodles",
        "quantity": 1,
        "solutions": [_solution(confidence=0.42, rank=2)],
    }

    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(
        transport=transport, base_url="http://testserver"
    ) as client:
        resp = await client.post("/v1/api/rfq/generate", json=payload)

    assert resp.status_code == 200, resp.text
    doc = resp.json()["data"]["rfqs"][0]
    assert "Match confidence: 42%" in doc["text"]
    assert "Match rank:       #2" in doc["text"]
