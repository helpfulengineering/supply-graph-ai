"""OKHService.list_recipes() — mirrors OKWService.list_kitchens() but scans okh/.

Follows the fake-storage pattern from test_okh_catalog_performance.py.
"""

from __future__ import annotations

import json
from datetime import datetime, timedelta
from unittest.mock import patch
from uuid import uuid4

import pytest

from src.core.services.okh_service import OKHService
from src.core.storage.smart_discovery import FileInfo


def recipe_dict(recipe_id: str, name: str = "Sourdough Bread") -> dict:
    return {
        "id": recipe_id,
        "name": name,
        "ingredients": ["flour", "water", "salt"],
        "instructions": ["Mix", "Bake"],
        "equipment": ["oven"],
    }


def manifest_dict(manifest_id: str, title: str = "Widget") -> dict:
    return {
        "id": manifest_id,
        "title": title,
        "version": "1.0.0",
        "license": {"hardware": "MIT"},
        "function": "Does a thing",
    }


class FakeStorageManager:
    def __init__(self, objects: dict[str, dict]):
        self.objects = objects

    async def get_object(self, key: str) -> bytes:
        return json.dumps(self.objects[key]).encode("utf-8")


class FakeStorage:
    def __init__(self, manager):
        self.manager = manager


def file_info(key: str, minutes_old: int = 0) -> FileInfo:
    return FileInfo(
        key=key,
        file_type="okh",
        size=100,
        last_modified=datetime(2026, 1, 1) - timedelta(minutes=minutes_old),
        metadata={},
    )


def build_service(objects: dict[str, dict]):
    service = OKHService()
    service.storage = FakeStorage(FakeStorageManager(objects))
    service._initialized = True
    return service


async def run_list_recipes(service, keys):
    async def fake_discover(_prefix):
        return keys

    with (
        patch("src.core.services.okh_service.SmartFileDiscovery") as Discovery,
        patch.object(service, "ensure_initialized", return_value=None),
    ):
        Discovery.return_value.discover_files = fake_discover
        return await service.list_recipes()


@pytest.mark.asyncio
class TestListRecipes:
    async def test_returns_only_recipe_shaped_files(self):
        recipe_id = str(uuid4())
        manifest_id = str(uuid4())
        objects = {
            "okh/recipe.json": recipe_dict(recipe_id),
            "okh/manifest.json": manifest_dict(manifest_id),
        }
        service = build_service(objects)
        keys = [file_info(k) for k in objects]

        recipes = await run_list_recipes(service, keys)

        assert len(recipes) == 1
        assert str(recipes[0].id) == recipe_id

    async def test_deduplicates_by_id_keeping_newest(self):
        shared = str(uuid4())
        objects = {
            "okh/old.json": recipe_dict(shared, name="Old"),
            "okh/new.json": recipe_dict(shared, name="New"),
        }
        service = build_service(objects)
        keys = [file_info("okh/old.json", minutes_old=60), file_info("okh/new.json")]

        recipes = await run_list_recipes(service, keys)

        assert len(recipes) == 1
        assert recipes[0].name == "New"

    async def test_unparseable_files_are_skipped_not_fatal(self):
        good = str(uuid4())
        objects = {
            "okh/good.json": recipe_dict(good),
            "okh/bad.json": {"ingredients": []},  # recipe-shaped but no id/name
        }
        service = build_service(objects)
        keys = [file_info("okh/good.json"), file_info("okh/bad.json")]

        recipes = await run_list_recipes(service, keys)

        assert len(recipes) == 1
        assert str(recipes[0].id) == good

    async def test_no_storage_returns_empty(self):
        service = OKHService()
        service.storage = None
        service._initialized = True

        with patch.object(service, "ensure_initialized", return_value=None):
            recipes = await service.list_recipes()

        assert recipes == []
