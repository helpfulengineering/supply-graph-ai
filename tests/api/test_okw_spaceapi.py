"""Publishing a facility outward to Maps of Making.

Two things are being pinned here. The document must carry what MoM actually
reads — capabilities in ``knowsAbout``, not only in an extension key nothing
consumes — and it must carry nothing the owner has not chosen to publish.

The visibility gate is deliberately stricter than the sibling reads: ``public``
only, where ``GET /okw/{id}`` accepts anything ``is_shareable``. That helper
also admits ``followers``, and records predating Slice 4 resolve to
``followers`` through LEGACY_VISIBILITY — including the seeded dataset, which
writes straight to storage. The looser gate would hand that entire seed to a
live third-party map on behalf of people who never made that choice.
"""

from __future__ import annotations

import os
import sys
from unittest.mock import AsyncMock, MagicMock
from uuid import UUID

import httpx
import pytest
from fastapi import FastAPI

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../../")))

from src.core.models.okw import (  # noqa: E402
    Address,
    Agent,
    FacilityStatus,
    Location,
    ManufacturingFacility,
)
from src.core.models.visibility import VisibilityLevel  # noqa: E402

FACILITY_ID = UUID("33333333-3333-4333-8333-333333333333")

STREET = "12 Rue Secret"
POSTCODE = "33000"
EMAIL = "private-person@example.org"


def fixture(**overrides) -> ManufacturingFacility:
    """A facility carrying details that must not reach the map."""
    values = dict(
        id=FACILITY_ID,
        name="Atelier Bordeaux",
        location=Location(
            address=Address(
                street=STREET, city="Bordeaux", country="France", postcode=POSTCODE
            ),
            gps_coordinates="44.8378, -0.5792",
        ),
        facility_status=FacilityStatus.ACTIVE,
        owner=Agent(name="Assoc", website="https://atelier.example"),
        description="A community workshop.",
        opening_hours="Mo-Fr 09:00-18:00",
        manufacturing_processes=[
            "https://en.wikipedia.org/wiki/Laser_cutting",
            "3D printing",
        ],
    )
    values.update(overrides)
    return ManufacturingFacility(**values)


def _app() -> tuple[FastAPI, FastAPI]:
    from src.core.main import api_v1

    app = FastAPI()
    app.mount("/v1", api_v1)
    return app, api_v1


async def _get(visibility: VisibilityLevel | None, facility=...) -> httpx.Response:
    from src.core.api.routes.okw import get_okw_service

    app, api_v1 = _app()
    svc = MagicMock()
    svc.get = AsyncMock(return_value=fixture() if facility is ... else facility)
    svc.get_visibility = AsyncMock(return_value=visibility)
    api_v1.dependency_overrides[get_okw_service] = lambda: svc
    try:
        transport = httpx.ASGITransport(app=app)
        async with httpx.AsyncClient(
            transport=transport, base_url="http://testserver"
        ) as client:
            return await client.get(f"/v1/api/okw/{FACILITY_ID}/spaceapi")
    finally:
        api_v1.dependency_overrides.clear()


# --- The document ----------------------------------------------------------


@pytest.mark.unit
def test_capabilities_land_in_the_key_mom_reads() -> None:
    """MoM builds its specialty chips from knowsAbout, kebab-cased.

    Emitting process detail only under ext_fablab would put the facility on the
    map untagged — discarding the one thing OHM knows that a directory does not.
    """
    doc = fixture().to_spaceapi_json()
    assert doc["knowsAbout"] == ["laser-cutting", "3d-printing"]
    assert doc["ext_fablab"]["capabilities"] == [
        "https://en.wikipedia.org/wiki/Laser_cutting",
        "3D printing",
    ]


@pytest.mark.unit
def test_unrecognized_processes_are_dropped_from_the_tags() -> None:
    doc = fixture(manufacturing_processes=["utter nonsense"]).to_spaceapi_json()
    assert "knowsAbout" not in doc
    # Still carried losslessly in the extension, which nothing joins on.
    assert doc["ext_fablab"]["capabilities"] == ["utter nonsense"]


@pytest.mark.unit
def test_no_street_address_or_contact_is_published() -> None:
    """The document reaches a store we do not control, so it carries less.

    `location` is a single disclosure group, so a profile cannot presently keep
    coordinates while withholding the street — the address is simply not sent.
    """
    import json

    blob = json.dumps(fixture().to_spaceapi_json())
    for secret in (STREET, POSTCODE, EMAIL):
        assert secret not in blob


@pytest.mark.unit
def test_country_code_is_alpha2_and_omitted_when_unknown() -> None:
    assert fixture().to_spaceapi_json()["location"]["country_code"] == "FR"

    unknown = fixture(
        location=Location(
            address=Address(country="Atlantis"), gps_coordinates="1.0, 2.0"
        )
    )
    assert "country_code" not in unknown.to_spaceapi_json()["location"]


@pytest.mark.unit
def test_spaceapi_conformance_is_not_claimed() -> None:
    """api_compatibility declares conformance we do not meet.

    The v15 schema requires `logo` and `contact` alongside it, and we publish
    neither; mapall.space and other SpaceAPI consumers are entitled to believe
    the declaration.
    """
    assert "api_compatibility" not in fixture().to_spaceapi_json()


@pytest.mark.unit
def test_lifecycle_status_does_not_masquerade_as_realtime_state() -> None:
    """`state.open` is "is the door open now" — OHM has no such signal.

    The long-term lifecycle OKW does record belongs in MoM's separate field.
    """
    for status, expected in (
        (FacilityStatus.ACTIVE, "active"),
        (FacilityStatus.PLANNED, "dormant"),
        (FacilityStatus.TEMPORARY_CLOSURE, "dormant"),
        (FacilityStatus.CLOSED, "closed"),
    ):
        doc = fixture(facility_status=status).to_spaceapi_json()
        assert doc["state"] == {"open": None}
        assert doc["mom:operationalState"] == expected


# --- The gate --------------------------------------------------------------


@pytest.mark.asyncio
@pytest.mark.contract
async def test_public_facility_is_served() -> None:
    resp = await _get(VisibilityLevel.PUBLIC)
    assert resp.status_code == 200, resp.text
    assert resp.json()["space"] == "Atelier Bordeaux"


@pytest.mark.asyncio
@pytest.mark.contract
@pytest.mark.parametrize(
    "visibility",
    [VisibilityLevel.PRIVATE, VisibilityLevel.FOLLOWERS],
)
async def test_only_public_is_published(visibility: VisibilityLevel) -> None:
    """`followers` 404s here while it is served by GET /okw/{id}.

    That is the whole distinction: followers means follow-gated federation sync,
    where the receiving node decides what to re-share. An open map is broader.
    """
    resp = await _get(visibility)
    assert resp.status_code == 404, resp.text
    assert "Atelier Bordeaux" not in resp.text


@pytest.mark.asyncio
@pytest.mark.contract
async def test_unknown_id_404s() -> None:
    resp = await _get(None, facility=None)
    assert resp.status_code == 404


@pytest.mark.asyncio
@pytest.mark.contract
async def test_document_is_served_bare() -> None:
    """MoM's validator reads SpaceAPI keys at the root, not inside an envelope."""
    body = (await _get(VisibilityLevel.PUBLIC)).json()
    assert "space" in body
    assert "data" not in body and "message" not in body


@pytest.mark.asyncio
@pytest.mark.contract
async def test_signing_in_does_not_unlock_an_unpublished_record() -> None:
    """The endpoint takes no viewer: what it publishes cannot vary by caller."""
    from src.core.api.routes.okw import get_okw_service

    app, api_v1 = _app()
    svc = MagicMock()
    svc.get = AsyncMock(return_value=fixture())
    svc.get_visibility = AsyncMock(return_value=VisibilityLevel.PRIVATE)
    api_v1.dependency_overrides[get_okw_service] = lambda: svc
    try:
        transport = httpx.ASGITransport(app=app)
        async with httpx.AsyncClient(
            transport=transport, base_url="http://testserver"
        ) as client:
            resp = await client.get(
                f"/v1/api/okw/{FACILITY_ID}/spaceapi",
                headers={"Authorization": "Bearer whatever"},
            )
        assert resp.status_code == 404, resp.text
    finally:
        api_v1.dependency_overrides.clear()
