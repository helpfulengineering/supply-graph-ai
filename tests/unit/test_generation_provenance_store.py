"""The generation sidecar round-trips without becoming part of a manifest."""

import pytest

from src.core.models.generation_provenance import GenerationProvenanceRecord
from src.core.storage.generation_provenance_store import GenerationProvenanceStore


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


def _record() -> dict:
    return {
        "schema": "ohm-generation-provenance/v1",
        "source_url": "https://github.com/example/widget",
        "note": "kept",
        "stages": [{"seq": 1, "stage": "extract", "fraction": 1}],
        "fields": {
            "title": {
                "layer": "direct",
                "method": "metadata_name",
                "confidence": 0.9,
                "source": "metadata.name",
            }
        },
    }


@pytest.mark.asyncio
async def test_generation_provenance_round_trip_keeps_extra_keys():
    store = GenerationProvenanceStore(_FakeStorageService())
    await store.save("rec-1", _record())
    loaded = await store.load("rec-1")
    assert loaded is not None
    assert loaded["note"] == "kept"
    parsed = GenerationProvenanceRecord.model_validate(loaded)
    dumped = parsed.model_dump(mode="json", by_alias=True)
    assert dumped["note"] == "kept"
    assert dumped["schema"] == "ohm-generation-provenance/v1"


@pytest.mark.asyncio
async def test_generation_provenance_missing_returns_none():
    store = GenerationProvenanceStore(_FakeStorageService())
    assert await store.load("nope") is None
