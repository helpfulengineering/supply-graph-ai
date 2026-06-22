"""Unit tests for OKHService.import_repair_doc merge logic — GAP-4."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import List, Optional
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from src.core.models.okh import Component, OKHManifest

# ---------------------------------------------------------------------------
# Minimal stand-ins
# ---------------------------------------------------------------------------


@dataclass
class _Component:
    name: str
    part_number: Optional[str] = None
    consumable: bool = False
    replaceable: bool = False
    salvageable: bool = False
    diagnostic_codes: List[str] = field(default_factory=list)
    failure_modes: List[str] = field(default_factory=list)
    repair_notes: Optional[str] = None


@dataclass
class _Result:
    components: List[_Component] = field(default_factory=list)
    repair_guides: list = field(default_factory=list)
    source_files: List[str] = field(default_factory=list)
    llm_enhanced: bool = False
    notes: List[str] = field(default_factory=list)


def _manifest_with_components(*comps) -> OKHManifest:
    m = OKHManifest.from_dict(
        {
            "title": "Test Device",
            "version": "1.0.0",
            "license": {"hardware": "CERN-OHL-S-2.0"},
            "licensor": "Test",
            "documentation_language": "en",
            "function": "test",
        }
    )
    m.components = list(comps)
    return m


# ---------------------------------------------------------------------------
# Helper: run import_repair_doc without real storage
# ---------------------------------------------------------------------------


async def _run_import(service, result, manifest=None, title=None):
    """Patch get/create/update on the service so we can test merge logic."""
    from uuid import uuid4

    mid = uuid4() if manifest else None
    if manifest:
        manifest.id = mid

    with (
        patch.object(service, "get", new=AsyncMock(return_value=manifest)),
        patch.object(
            service,
            "update",
            new=AsyncMock(side_effect=lambda _id, d: OKHManifest.from_dict(d)),
        ),
        patch.object(
            service,
            "create",
            new=AsyncMock(side_effect=lambda d: OKHManifest.from_dict(d)),
        ),
        patch.object(service, "ensure_initialized", new=AsyncMock()),
    ):
        return await service.import_repair_doc(result, manifest_id=mid, title=title)


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_new_components_default_to_conservative_flags():
    """Newly imported components must always start with replaceable=False, salvageable=False."""
    from src.core.services.okh_service import OKHService

    svc = OKHService.__new__(OKHService)
    result = _Result(
        components=[
            _Component(name="Blood pump", part_number="BP-01", replaceable=True),
            _Component(name="Filter", consumable=True, replaceable=True),
        ],
        source_files=["manual.pdf"],
    )
    manifest = await _run_import(svc, result, title="New Device")
    comp_map = {c.name: c for c in manifest.components}

    assert comp_map["Blood pump"].replaceable is False
    assert comp_map["Blood pump"].salvageable is False
    assert comp_map["Filter"].replaceable is False
    assert comp_map["Filter"].salvageable is False


@pytest.mark.asyncio
async def test_existing_component_flags_preserved():
    """Components already in the manifest keep their flags even if extractor says otherwise."""
    from src.core.services.okh_service import OKHService

    svc = OKHService.__new__(OKHService)
    existing_comp = Component(
        name="Blood pump", replaceable=True, salvageable=True, part_number="BP-01"
    )
    manifest = _manifest_with_components(existing_comp)

    result = _Result(
        components=[
            # Extractor re-found it — flags should be ignored for existing
            _Component(name="Blood pump", replaceable=False, salvageable=False)
        ],
        source_files=["manual.pdf"],
    )
    out = await _run_import(svc, result, manifest=manifest)
    pump = next(c for c in out.components if c.name == "Blood pump")
    assert pump.replaceable is True
    assert pump.salvageable is True


@pytest.mark.asyncio
async def test_part_number_filled_when_missing():
    """Part number is updated on an existing component only when it was previously unset."""
    from src.core.services.okh_service import OKHService

    svc = OKHService.__new__(OKHService)
    existing_comp = Component(name="Pump", part_number=None)
    manifest = _manifest_with_components(existing_comp)

    result = _Result(
        components=[_Component(name="Pump", part_number="PN-42")],
        source_files=["parts.pdf"],
    )
    out = await _run_import(svc, result, manifest=manifest)
    pump = next(c for c in out.components if c.name == "Pump")
    assert pump.part_number == "PN-42"


@pytest.mark.asyncio
async def test_existing_part_number_not_overwritten():
    """Part number already set on a manifest component must not be overwritten."""
    from src.core.services.okh_service import OKHService

    svc = OKHService.__new__(OKHService)
    existing_comp = Component(name="Pump", part_number="ORIGINAL-PN")
    manifest = _manifest_with_components(existing_comp)

    result = _Result(
        components=[_Component(name="Pump", part_number="NEW-PN")],
        source_files=["parts.pdf"],
    )
    out = await _run_import(svc, result, manifest=manifest)
    pump = next(c for c in out.components if c.name == "Pump")
    assert pump.part_number == "ORIGINAL-PN"


@pytest.mark.asyncio
async def test_new_diagnostic_codes_merged():
    """Diagnostic codes from extraction are appended to existing component, no duplicates."""
    from src.core.services.okh_service import OKHService

    svc = OKHService.__new__(OKHService)
    existing_comp = Component(name="Motor", diagnostic_codes=["E01"])
    manifest = _manifest_with_components(existing_comp)

    result = _Result(
        components=[_Component(name="Motor", diagnostic_codes=["E01", "E02"])],
        source_files=["guide.pdf"],
    )
    out = await _run_import(svc, result, manifest=manifest)
    motor = next(c for c in out.components if c.name == "Motor")
    assert "E01" in motor.diagnostic_codes
    assert "E02" in motor.diagnostic_codes
    assert motor.diagnostic_codes.count("E01") == 1  # no duplicates


@pytest.mark.asyncio
async def test_deduplication_is_case_insensitive():
    """A component named 'Blood Pump' matches existing 'blood pump' (case-insensitive)."""
    from src.core.services.okh_service import OKHService

    svc = OKHService.__new__(OKHService)
    existing_comp = Component(name="blood pump", replaceable=True)
    manifest = _manifest_with_components(existing_comp)

    result = _Result(
        components=[_Component(name="Blood Pump", replaceable=False)],
        source_files=["parts.pdf"],
    )
    out = await _run_import(svc, result, manifest=manifest)
    assert len(out.components) == 1
    assert out.components[0].replaceable is True  # existing flag preserved


@pytest.mark.asyncio
async def test_create_mode_missing_title_raises():
    """Calling without manifest_id and without title must raise ValueError."""
    from src.core.services.okh_service import OKHService

    svc = OKHService.__new__(OKHService)
    result = _Result(components=[], source_files=[])

    with pytest.raises(ValueError, match="title is required"):
        with patch.object(svc, "ensure_initialized", new=AsyncMock()):
            await svc.import_repair_doc(result, manifest_id=None, title=None)
