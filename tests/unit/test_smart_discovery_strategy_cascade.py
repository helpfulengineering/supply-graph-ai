"""Tests for SmartFileDiscovery strategy cascade behaviour.

The cascade should only advance to the next strategy when the current one
raises an exception (i.e. storage is unavailable / broken).  An empty result
from strategy 1 (prefix-listing ``okh/``) means "no OKH files exist" and is a
valid terminal answer — it must NOT trigger the full-bucket strategies (metadata
scan and content-validation), which would download every blob in the container
and hang under load.
"""

from __future__ import annotations

import asyncio
import json
from datetime import datetime
from typing import Any, AsyncIterator, Dict, Optional
from unittest.mock import AsyncMock, call

import pytest

from src.core.storage.smart_discovery import SmartFileDiscovery


# ---------------------------------------------------------------------------
# Fake storage managers
# ---------------------------------------------------------------------------


class _EmptyPrefixManager:
    """list_objects returns empty for the okh/ prefix but would return items
    for a full-bucket walk.  get_object should never be called."""

    def __init__(self):
        self.list_calls: list[Optional[str]] = []
        self.get_calls: list[str] = []

    async def list_objects(
        self, prefix: Optional[str] = None, **_kwargs: Any
    ) -> AsyncIterator[Dict[str, Any]]:
        self.list_calls.append(prefix)
        if prefix == "okh/":
            return
            yield  # make it an async generator that yields nothing
        # Full-bucket walk — expensive; should not be reached.
        for i in range(50):
            yield {
                "key": f"supply-trees/item-{i}.json",
                "size": 100,
                "last_modified": datetime.now(),
                "metadata": {},
            }

    async def get_object(self, key: str) -> bytes:
        self.get_calls.append(key)
        # Simulate slow download; if this is ever awaited the test will hang.
        await asyncio.sleep(60)
        return b"{}"


class _BrokenPrefixManager:
    """list_objects raises an exception for the okh/ prefix, but succeeds for
    a no-prefix (full-bucket) walk that has one tagged OKH object."""

    _OKH_PAYLOAD = json.dumps(
        {
            "title": "Test",
            "version": "1.0",
            "license": {"hardware": "MIT"},
            "licensor": "Alice",
            "documentation_language": "en",
            "function": "something",
            "id": "00000000-0000-0000-0000-000000000001",
        }
    ).encode()

    def __init__(self):
        self.list_calls: list[Optional[str]] = []

    async def list_objects(
        self, prefix: Optional[str] = None, **_kwargs: Any
    ) -> AsyncIterator[Dict[str, Any]]:
        self.list_calls.append(prefix)
        if prefix == "okh/":
            raise RuntimeError("Prefix listing unavailable")
        # Metadata strategy walk — has one tagged OKH object.
        yield {
            "key": "misc/test-okh.json",
            "size": len(self._OKH_PAYLOAD),
            "last_modified": datetime.now(),
            "metadata": {"domain": "okh"},
        }

    async def get_object(self, key: str) -> bytes:
        return self._OKH_PAYLOAD


class _SuccessfulPrefixManager:
    """list_objects finds one OKH file under okh/ on the first call."""

    _OKH_PAYLOAD = json.dumps(
        {
            "title": "Found",
            "version": "1.0",
            "license": {"hardware": "MIT"},
            "licensor": "Alice",
            "documentation_language": "en",
            "function": "something",
            "id": "00000000-0000-0000-0000-000000000002",
        }
    ).encode()

    def __init__(self):
        self.list_calls: list[Optional[str]] = []

    async def list_objects(
        self, prefix: Optional[str] = None, **_kwargs: Any
    ) -> AsyncIterator[Dict[str, Any]]:
        self.list_calls.append(prefix)
        if prefix == "okh/":
            yield {
                "key": "okh/found-abcd1234-okh.json",
                "size": len(self._OKH_PAYLOAD),
                "last_modified": datetime.now(),
                "metadata": {},
            }
        else:
            # Full-bucket walk — should never be reached after a successful prefix hit.
            for i in range(50):
                yield {
                    "key": f"supply-trees/item-{i}.json",
                    "size": 100,
                    "last_modified": datetime.now(),
                    "metadata": {},
                }

    async def get_object(self, key: str) -> bytes:
        return self._OKH_PAYLOAD


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_empty_prefix_does_not_cascade_to_full_bucket_strategies() -> None:
    """When okh/ prefix listing succeeds but is empty, discover_files must
    return [] immediately — it must NOT fall through to the metadata-scan or
    content-validation strategies that do full-bucket walks."""
    manager = _EmptyPrefixManager()
    discovery = SmartFileDiscovery(manager)

    # Give ample time for a fast path; content-validation would need minutes.
    result = await asyncio.wait_for(discovery.discover_files("okh"), timeout=3.0)

    assert result == [], "Expected empty list when no OKH files exist under okh/"
    # Only the directory-structure strategy should have run (one list call with prefix).
    assert manager.list_calls == [
        "okh/"
    ], f"Expected exactly one list call with prefix='okh/', got: {manager.list_calls}"
    # No blob downloads should have been attempted.
    assert (
        manager.get_calls == []
    ), "get_object should not be called when prefix listing returns empty"


@pytest.mark.asyncio
async def test_exception_in_prefix_strategy_does_cascade_to_metadata_strategy() -> None:
    """When the directory-structure strategy raises (storage error), the cascade
    should advance to the next strategy and find the file via metadata tags."""
    manager = _BrokenPrefixManager()
    discovery = SmartFileDiscovery(manager)

    result = await asyncio.wait_for(discovery.discover_files("okh"), timeout=3.0)

    assert (
        len(result) == 1
    ), "Expected metadata strategy to find the one tagged OKH file"
    assert result[0].key == "misc/test-okh.json"
    # Directory strategy (prefix="okh/") ran first, then metadata strategy (prefix=None).
    assert "okh/" in manager.list_calls
    assert None in manager.list_calls


@pytest.mark.asyncio
async def test_files_found_in_strategy1_stops_cascade() -> None:
    """When the directory-structure strategy returns at least one file, the
    cascade must stop — strategies 2/3/4 must not run."""
    manager = _SuccessfulPrefixManager()
    discovery = SmartFileDiscovery(manager)

    result = await asyncio.wait_for(discovery.discover_files("okh"), timeout=3.0)

    assert len(result) == 1
    assert result[0].key == "okh/found-abcd1234-okh.json"
    # Only the prefix listing should have been called — no full-bucket walk.
    assert manager.list_calls == ["okh/"], (
        f"Full-bucket strategies should not run after a successful prefix hit, "
        f"got list_calls={manager.list_calls}"
    )
