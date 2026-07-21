"""Unit tests for visibility model + store (Slice 4)."""

import pytest

from src.core.models.visibility import (
    DEFAULT_VISIBILITY,
    VisibilityLevel,
    is_shareable,
)
from src.core.storage.visibility_store import VisibilityStore


def test_default_visibility_is_private():
    assert DEFAULT_VISIBILITY is VisibilityLevel.PRIVATE


def test_is_shareable():
    assert not is_shareable(VisibilityLevel.PRIVATE)
    assert not is_shareable(None)
    assert is_shareable(VisibilityLevel.FOLLOWERS)
    assert is_shareable(VisibilityLevel.PUBLIC)


class _InMemoryManager:
    def __init__(self) -> None:
        self._objects: dict[str, bytes] = {}

    async def put_object(self, key, data, content_type=None, metadata=None):
        self._objects[key] = data

    async def get_object(self, key):
        return self._objects[key]


class _FakeStorageService:
    def __init__(self) -> None:
        self.manager = _InMemoryManager()


@pytest.mark.asyncio
async def test_visibility_store_round_trip():
    store = VisibilityStore(_FakeStorageService())
    await store.save("rec-1", VisibilityLevel.PUBLIC)
    assert await store.load("rec-1") is VisibilityLevel.PUBLIC


@pytest.mark.asyncio
async def test_visibility_store_missing_returns_none():
    store = VisibilityStore(_FakeStorageService())
    assert await store.load("nope") is None
