"""Contract tests for GET /api/okh/recipes and GET /api/okw/kitchens.

Regression guard: both routes must be registered ahead of their sibling
``/{id}`` GET route, otherwise "recipes"/"kitchens" is parsed as a UUID path
parameter and the request 422s instead of listing.
"""

from __future__ import annotations

import os
import sys
from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

import httpx
import pytest
from fastapi import FastAPI

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../../")))

from src.core.domains.cooking.models import KitchenCapability, Recipe


def _get_app() -> tuple[FastAPI, FastAPI]:
    from src.core.main import api_v1

    app = FastAPI()
    app.mount("/v1", api_v1)
    return app, api_v1


def _recipe() -> Recipe:
    return Recipe.from_dict(
        {
            "id": str(uuid4()),
            "name": "Sourdough Bread",
            "ingredients": ["flour", "water", "salt"],
            "instructions": ["Mix", "Bake"],
            "equipment": ["oven"],
        }
    )


def _kitchen() -> KitchenCapability:
    return KitchenCapability.from_dict(
        {
            "id": str(uuid4()),
            "name": "Test Kitchen",
            "appliances": ["oven"],
            "tools": ["knife"],
            "ingredients": [],
        }
    )


@pytest.mark.asyncio
@pytest.mark.contract
async def test_list_recipes_returns_paginated_recipes():
    from src.core.api.routes.okh import get_okh_service

    app, api_v1 = _get_app()
    svc = MagicMock()
    svc.list_recipes = AsyncMock(return_value=[_recipe(), _recipe()])
    api_v1.dependency_overrides[get_okh_service] = lambda: svc

    try:
        transport = httpx.ASGITransport(app=app)
        async with httpx.AsyncClient(
            transport=transport, base_url="http://testserver"
        ) as client:
            resp = await client.get("/v1/api/okh/recipes")

        assert resp.status_code == 200, resp.text
        body = resp.json()
        assert body["pagination"]["total_items"] == 2
        assert len(body["items"]) == 2
        assert body["items"][0]["ingredients"] == ["flour", "water", "salt"]
    finally:
        api_v1.dependency_overrides.clear()


@pytest.mark.asyncio
@pytest.mark.contract
async def test_list_kitchens_returns_paginated_kitchens():
    from src.core.api.routes.okw import get_okw_service

    app, api_v1 = _get_app()
    svc = MagicMock()
    svc.list_kitchens = AsyncMock(return_value=[_kitchen()])
    api_v1.dependency_overrides[get_okw_service] = lambda: svc

    try:
        transport = httpx.ASGITransport(app=app)
        async with httpx.AsyncClient(
            transport=transport, base_url="http://testserver"
        ) as client:
            resp = await client.get("/v1/api/okw/kitchens")

        assert resp.status_code == 200, resp.text
        body = resp.json()
        assert body["pagination"]["total_items"] == 1
        assert body["items"][0]["name"] == "Test Kitchen"
    finally:
        api_v1.dependency_overrides.clear()
