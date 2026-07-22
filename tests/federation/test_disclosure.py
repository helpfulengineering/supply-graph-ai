"""Unit tests for OKW disclosure profiles and projection."""

from __future__ import annotations

import pytest

from src.core.models.disclosure import (
    DisclosureAudience,
    DisclosureGroup,
    AudienceDisclosure,
    DisclosureProfile,
    default_disclosure_profile,
    groups_for_audience,
    project_facility,
)

FACILITY = {
    "id": "aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee",
    "name": "Fab Lab",
    "facility_status": "Active",
    "description": "A lab",
    "location": {"address": {"city": "Secret City", "street": "1 CNC Rd"}},
    "equipment": [{"equipment_type": "cnc", "manufacturer": "Haas"}],
    "opening_hours": "9-5",
    "typical_products": ["widgets"],
}


def test_default_profile_is_identity_only() -> None:
    profile = default_disclosure_profile()
    groups = groups_for_audience(profile, DisclosureAudience.FOLLOWERS)
    assert groups == {DisclosureGroup.IDENTITY}


def test_project_fail_closed_strips_location_and_equipment() -> None:
    groups = {DisclosureGroup.IDENTITY}
    out = project_facility(FACILITY, groups=groups)
    assert out["name"] == "Fab Lab"
    assert "location" not in out
    assert "equipment" not in out
    assert "opening_hours" not in out
    assert "typical_products" not in out


def test_project_with_location_group() -> None:
    groups = {DisclosureGroup.IDENTITY, DisclosureGroup.LOCATION}
    out = project_facility(FACILITY, groups=groups)
    assert "location" in out
    assert "equipment" not in out


def test_groups_for_audience_always_includes_identity() -> None:
    profile = DisclosureProfile(
        followers=AudienceDisclosure(groups=[DisclosureGroup.LOCATION]),
        public=AudienceDisclosure(groups=[]),
    )
    groups = groups_for_audience(profile, DisclosureAudience.FOLLOWERS)
    assert DisclosureGroup.IDENTITY in groups
    assert DisclosureGroup.LOCATION in groups


@pytest.mark.asyncio
async def test_preview_disclosure_exported_flag() -> None:
    from unittest.mock import AsyncMock, MagicMock
    from uuid import uuid4

    from src.core.models.visibility import VisibilityLevel
    from src.core.services.okw_service import OKWService

    facility_id = uuid4()
    facility = MagicMock()
    facility.id = facility_id
    facility.to_dict.return_value = FACILITY

    svc = OKWService.__new__(OKWService)
    svc.ensure_initialized = AsyncMock()
    svc.get = AsyncMock(return_value=facility)
    svc.get_visibility = AsyncMock(return_value=VisibilityLevel.PRIVATE)
    svc.get_disclosure = AsyncMock(return_value=default_disclosure_profile())

    preview = await svc.preview_disclosure(facility_id, DisclosureAudience.FOLLOWERS)
    assert preview["exported"] is False
    assert "location" not in preview["facility"]
    assert preview["facility"]["name"] == "Fab Lab"

    svc.get_visibility = AsyncMock(return_value=VisibilityLevel.FOLLOWERS)
    svc.get_disclosure = AsyncMock(
        return_value=DisclosureProfile(
            followers=AudienceDisclosure(
                groups=[DisclosureGroup.IDENTITY, DisclosureGroup.LOCATION]
            ),
            public=AudienceDisclosure(groups=[DisclosureGroup.IDENTITY]),
        )
    )
    preview2 = await svc.preview_disclosure(facility_id, DisclosureAudience.FOLLOWERS)
    assert preview2["exported"] is True
    assert "location" in preview2["facility"]
