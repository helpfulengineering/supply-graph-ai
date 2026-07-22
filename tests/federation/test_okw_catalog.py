"""OKW federation catalog builds redacted projections."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock
from uuid import UUID

import pytest

from src.core.federation.identity import generate_identity
from src.core.federation.okw_catalog import build_okw_catalog_index
from src.core.models.disclosure import (
    AudienceDisclosure,
    DisclosureGroup,
    DisclosureProfile,
)
from src.core.models.visibility import VisibilityLevel


@pytest.mark.unit
@pytest.mark.asyncio
async def test_okw_catalog_excludes_private() -> None:
    identity = generate_identity("OKW Cat")
    facility = MagicMock()
    facility.id = UUID("aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee")
    facility.name = "Secret Fab"
    facility.to_dict.return_value = {
        "id": str(facility.id),
        "name": "Secret Fab",
        "facility_status": "Active",
        "location": {"address": {"city": "X"}},
    }

    okw = AsyncMock()
    okw.list.return_value = ([facility], 1)
    okw.get_visibility.return_value = VisibilityLevel.PRIVATE

    index = await build_okw_catalog_index(okw, identity)
    assert index.record_count == 0


@pytest.mark.unit
@pytest.mark.asyncio
async def test_okw_catalog_uses_redacted_projection() -> None:
    identity = generate_identity("OKW Cat")
    facility = MagicMock()
    facility.id = UUID("aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee")
    facility.name = "Fab"
    facility.to_dict.return_value = {
        "id": str(facility.id),
        "name": "Fab",
        "facility_status": "Active",
        "location": {"address": {"city": "X"}},
        "equipment": [],
    }

    okw = AsyncMock()
    okw.list.return_value = ([facility], 1)
    okw.get_visibility.return_value = VisibilityLevel.FOLLOWERS
    okw.project_for_visibility = AsyncMock(
        return_value={
            "id": str(facility.id),
            "name": "Fab",
            "facility_status": "Active",
        }
    )
    okw.get_disclosure.return_value = DisclosureProfile(
        followers=AudienceDisclosure(groups=[DisclosureGroup.IDENTITY]),
        public=AudienceDisclosure(groups=[DisclosureGroup.IDENTITY]),
    )

    index = await build_okw_catalog_index(okw, identity)
    assert index.record_count == 1
    signed = index.get_signed_record(index.records[0].content_hash)
    assert signed is not None
    assert "location" not in signed.facility
    assert signed.facility["name"] == "Fab"
