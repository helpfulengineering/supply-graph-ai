"""OKW disclosure profiles — field-group redaction for federation audiences."""

from __future__ import annotations

from enum import Enum
from typing import Any
from uuid import UUID

from pydantic import BaseModel, Field


class DisclosureAudience(str, Enum):
    FOLLOWERS = "followers"
    PUBLIC = "public"


class DisclosureGroup(str, Enum):
    IDENTITY = "identity"
    LOCATION = "location"
    EQUIPMENT = "equipment"
    OPERATIONS = "operations"
    SUPPLY = "supply"


_LOCATION_KEYS = frozenset(
    {
        "location",
        "wheelchair_accessibility",
        "road_access",
        "loading_dock",
    }
)
_EQUIPMENT_KEYS = frozenset({"equipment"})
_OPERATIONS_KEYS = frozenset(
    {
        "opening_hours",
        "access_type",
        "manufacturing_processes",
        "typical_batch_size",
        "floor_size",
        "storage_capacity",
        "certifications",
        "backup_generator",
        "uninterrupted_power_supply",
        "maintenance_schedule",
        "human_capacity",
        "innovation_space",
        "circular_economy",
        "contact",
    }
)
_SUPPLY_KEYS = frozenset({"typical_materials", "typical_products"})
_IDENTITY_KEYS = frozenset(
    {
        "id",
        "name",
        "description",
        "date_founded",
        "facility_status",
        "owner",
        "affiliations",
        "partners_funders",
        "customer_reviews",
        "domain",
        "record_data",
    }
)


class AudienceDisclosure(BaseModel):
    """Which field groups are included for one audience."""

    groups: list[DisclosureGroup] = Field(
        default_factory=lambda: [DisclosureGroup.IDENTITY]
    )


class DisclosureProfile(BaseModel):
    """Per-facility disclosure config for followers and public audiences."""

    followers: AudienceDisclosure = Field(default_factory=AudienceDisclosure)
    public: AudienceDisclosure = Field(default_factory=AudienceDisclosure)


class DisclosureBody(BaseModel):
    """PUT body for disclosure profiles."""

    followers: AudienceDisclosure | None = None
    public: AudienceDisclosure | None = None


class DisclosureResponse(BaseModel):
    id: UUID
    disclosure: DisclosureProfile


class DisclosurePreviewResponse(BaseModel):
    """Redacted facility projection for one federation audience."""

    id: UUID
    audience: DisclosureAudience
    visibility: str
    exported: bool = Field(
        description="True when current visibility would export this audience's projection"
    )
    groups: list[DisclosureGroup]
    facility: dict[str, Any]


def default_disclosure_profile() -> DisclosureProfile:
    return DisclosureProfile(
        followers=AudienceDisclosure(groups=[DisclosureGroup.IDENTITY]),
        public=AudienceDisclosure(groups=[DisclosureGroup.IDENTITY]),
    )


def groups_for_audience(
    profile: DisclosureProfile | None,
    audience: DisclosureAudience,
) -> set[DisclosureGroup]:
    profile = profile or default_disclosure_profile()
    audience_cfg = (
        profile.followers
        if audience == DisclosureAudience.FOLLOWERS
        else profile.public
    )
    groups = set(audience_cfg.groups or [])
    groups.add(DisclosureGroup.IDENTITY)  # always on for any shareable export
    return groups


_GROUP_KEYS: dict[DisclosureGroup, frozenset[str]] = {
    DisclosureGroup.IDENTITY: _IDENTITY_KEYS,
    DisclosureGroup.LOCATION: _LOCATION_KEYS,
    DisclosureGroup.EQUIPMENT: _EQUIPMENT_KEYS,
    DisclosureGroup.OPERATIONS: _OPERATIONS_KEYS,
    DisclosureGroup.SUPPLY: _SUPPLY_KEYS,
}


def project_facility(
    facility: dict[str, Any],
    *,
    groups: set[DisclosureGroup],
) -> dict[str, Any]:
    """Return a redacted facility dict containing only allowed field groups."""
    allowed_keys: set[str] = {"id", "name", "facility_status"}
    for group in groups:
        allowed_keys |= _GROUP_KEYS.get(group, frozenset())
    return {k: v for k, v in facility.items() if k in allowed_keys}
