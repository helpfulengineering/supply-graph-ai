"""Unit tests for FederationService initialization."""

from __future__ import annotations

import pytest

from src.config import settings
from src.core.federation.service import FederationService


@pytest.fixture(autouse=True)
def _clear_federation_singleton() -> None:
    FederationService._instances.clear()
    yield
    FederationService._instances.clear()


@pytest.mark.unit
@pytest.mark.asyncio
async def test_federation_service_disabled_by_default(monkeypatch) -> None:
    monkeypatch.setattr(settings, "OHM_FEDERATION_ENABLED", False)

    service = await FederationService.get_instance()
    assert service.enabled is False
    assert service.identity is None


@pytest.mark.unit
@pytest.mark.asyncio
async def test_federation_service_loads_identity_when_enabled(
    monkeypatch, tmp_path
) -> None:
    monkeypatch.setattr(settings, "OHM_FEDERATION_ENABLED", True)
    monkeypatch.setattr(settings, "OHM_FEDERATION_DATA_DIR", str(tmp_path))
    monkeypatch.setattr(settings, "OHM_FEDERATION_NODE_NAME", "Test Peer")
    monkeypatch.setattr(settings, "OHM_FEDERATION_NODE_ROLE", "peer")

    service = await FederationService.get_instance()
    assert service.enabled is True
    assert service.identity is not None
    assert service.identity.display_name == "Test Peer"
    assert service.identity.did.startswith("did:key:")
