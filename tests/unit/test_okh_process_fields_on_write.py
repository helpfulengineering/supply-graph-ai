"""Local writes store derived process copies; a peer's record is stored as sent (#562).

Federation ingest is the exception because the record is the publisher's,
signed and hashed by them: rewriting it would make the next ingest see a
divergent copy of the same id.
"""

import json
from unittest.mock import AsyncMock
from uuid import uuid4

import pytest

from src.core.models.okh import OKHManifest
from src.core.services.okh_service import OKHService


def _inconsistent() -> dict:
    return {
        "okhv": "1.0",
        "id": str(uuid4()),
        "title": "Frugal IoT sensor",
        "version": "0.2",
        "license": {"hardware": "CERN-OHL-S-2.0"},
        "licensor": "Mitra",
        "documentation_language": "en",
        "function": "Sensor board",
        "manufacturing_processes": ["PCB Fabrication"],
        "manufacturing_specs": {
            "process_requirements": [
                {"process_name": "PCB Fabrication"},
                {"process_name": "Sheet Metal Forming"},
            ]
        },
        "tsdc": ["PCB", "SHEET"],
    }


class _CapturingManager:
    def __init__(self) -> None:
        self.written: dict[str, bytes] = {}

    async def put_object(self, key, data, *args, **kwargs):
        self.written[key] = data


class _FakeStorage:
    def __init__(self) -> None:
        self.manager = _CapturingManager()


def _service():
    svc = OKHService()
    svc.storage = _FakeStorage()
    svc.ensure_initialized = AsyncMock()
    return svc


def _stored(svc) -> dict:
    key = next(k for k in svc.storage.manager.written if k.startswith("okh/"))
    return json.loads(svc.storage.manager.written[key])


def _process_names(stored: dict) -> list[str]:
    return [
        r["process_name"] for r in stored["manufacturing_specs"]["process_requirements"]
    ]


@pytest.mark.asyncio
async def test_create_stores_the_derived_copies():
    svc = _service()

    await svc.create(_inconsistent())

    stored = _stored(svc)
    assert _process_names(stored) == ["PCB Fabrication"]
    assert stored["tsdc"] == ["PCB"]


@pytest.mark.asyncio
async def test_create_derives_from_a_parsed_manifest_too():
    svc = _service()

    await svc.create(OKHManifest.from_dict(_inconsistent()))

    assert _stored(svc)["tsdc"] == ["PCB"]


@pytest.mark.asyncio
async def test_update_stores_the_derived_copies():
    svc = _service()
    manifest = _inconsistent()
    svc._find_key_for_id = AsyncMock(return_value=f"okh/{manifest['id']}.json")

    await svc.update(manifest["id"], manifest)

    stored = _stored(svc)
    assert _process_names(stored) == ["PCB Fabrication"]
    assert stored["tsdc"] == ["PCB"]


@pytest.mark.asyncio
async def test_a_verbatim_create_stores_the_record_as_sent():
    svc = _service()

    await svc.create(_inconsistent(), verbatim=True)

    stored = _stored(svc)
    assert "Sheet Metal Forming" in _process_names(stored)
    assert stored["tsdc"] == ["PCB", "SHEET"]
