"""Contract tests for POST /api/rfq/generate.

Covers the cooking-domain branch (recipe + kitchen) added alongside the
existing manufacturing-domain branch (OKH design + facility), and guards
against the manufacturing default regressing when `domain` is omitted.
"""

from __future__ import annotations

import os
import sys

import httpx
import pytest
from fastapi import FastAPI

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../../")))


def _get_app() -> FastAPI:
    from src.core.main import api_v1

    app = FastAPI()
    app.mount("/v1", api_v1)
    return app


def _solution(**overrides) -> dict:
    data = {
        "facility_id": "kitchen-1",
        "facility_name": "Test Kitchen",
        "confidence": 0.65,
        "score": 0.65,
        "rank": 1,
        "tree": {},
        "facility": {"location": {"city": "Portland", "country": "US"}},
    }
    data.update(overrides)
    return data


@pytest.mark.asyncio
@pytest.mark.contract
async def test_generate_rfq_cooking_domain_uses_recipe_fields():
    app = _get_app()
    payload = {
        "domain": "cooking",
        "recipe_id": "recipe-1",
        "recipe_title": "Chocolate Chip Cookies",
        "recipe": {
            "ingredients": ["flour", "sugar", "chocolate chips"],
            "equipment": ["oven", "spatula"],
        },
        "quantity": 3,
        "solutions": [
            _solution(explanation_human="✓ Test Kitchen MATCHED (confidence: 65%)")
        ],
    }

    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(
        transport=transport, base_url="http://testserver"
    ) as client:
        resp = await client.post("/v1/api/rfq/generate", json=payload)

    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["data"]["total_rfqs"] == 1
    assert body["data"]["recipe_id"] == "recipe-1"
    assert body["data"]["recipe_title"] == "Chocolate Chip Cookies"

    doc = body["data"]["rfqs"][0]
    assert doc["facility_name"] == "Test Kitchen"
    assert doc["quantity"] == 3
    assert "Chocolate Chip Cookies" in doc["text"]
    assert "flour, sugar, chocolate chips" in doc["text"]
    assert "oven, spatula" in doc["text"]
    assert "✓ Test Kitchen MATCHED (confidence: 65%)" in doc["text"]
    # Cooking RFQs never carry an OKH manifest.
    assert doc["okh_manifest"] is None


@pytest.mark.asyncio
@pytest.mark.contract
async def test_generate_rfq_manufacturing_domain_is_default():
    app = _get_app()
    payload = {
        "okh_id": "okh-1",
        "okh_title": "Widget",
        "quantity": 1,
        "solutions": [_solution()],
    }

    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(
        transport=transport, base_url="http://testserver"
    ) as client:
        resp = await client.post("/v1/api/rfq/generate", json=payload)

    assert resp.status_code == 200, resp.text
    body = resp.json()
    doc = body["data"]["rfqs"][0]
    assert "Widget" in doc["text"]
    assert "Manufacturing Quotation Request" in doc["text"]


@pytest.mark.asyncio
@pytest.mark.contract
async def test_generate_rfq_cooking_domain_falls_back_without_explanation():
    app = _get_app()
    payload = {
        "domain": "cooking",
        "recipe_id": "recipe-2",
        "recipe_title": "Snickerdoodles",
        "quantity": 1,
        "solutions": [_solution(confidence=0.42, rank=2)],
    }

    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(
        transport=transport, base_url="http://testserver"
    ) as client:
        resp = await client.post("/v1/api/rfq/generate", json=payload)

    assert resp.status_code == 200, resp.text
    doc = resp.json()["data"]["rfqs"][0]
    assert "Match confidence: 42%" in doc["text"]
    assert "Match rank:       #2" in doc["text"]


# --- The contact block, which is the point of the document (#501) ----------

_FULL_CONTACT_FACILITY = {
    "name": "Bristol Fab Lab",
    "location": {"city": "Bristol", "country": "United Kingdom"},
    "contact": {
        "name": "Bristol Makers CIC",
        "contact_person": "Ada Okafor",
        "website": "https://bristolfablab.example",
        "mailing_list": "makers@bristolfablab.example",
        "contact": {
            "email": "ada@bristolfablab.example",
            "landline": "+44 117 000 0000",
            "mobile": "+44 7700 900000",
            "whatsapp": "+44 7700 900001",
        },
    },
}


async def _rfq_text(facility: dict) -> str:
    app = _get_app()
    payload = {
        "okh_id": "okh-1",
        "okh_title": "Widget",
        "quantity": 1,
        "solutions": [_solution(facility=facility)],
    }
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(
        transport=transport, base_url="http://testserver"
    ) as client:
        resp = await client.post("/v1/api/rfq/generate", json=payload)
    assert resp.status_code == 200, resp.text
    return resp.json()["data"]["rfqs"][0]["text"]


@pytest.mark.asyncio
@pytest.mark.contract
async def test_rfq_carries_every_way_to_reach_the_facility():
    """An RFQ exists to be sent to someone, so it must say how to reach them.

    Email was absent until #501: the contact block read `landline` and `mobile`
    and skipped `email`, `whatsapp` and `mailing_list`, so the channel most
    people would answer on was missing from a document addressed to them.
    """
    text = await _rfq_text(_FULL_CONTACT_FACILITY)
    assert "Email:        ada@bristolfablab.example" in text
    assert "WhatsApp:     +44 7700 900001" in text
    assert "Mailing list: makers@bristolfablab.example" in text
    assert "Contact:      Ada Okafor" in text
    assert "Organisation: Bristol Makers CIC" in text
    assert "Phone:        +44 117 000 0000" in text
    assert "Mobile:       +44 7700 900000" in text
    assert "Location:     Bristol, United Kingdom" in text


@pytest.mark.asyncio
@pytest.mark.contract
async def test_a_facility_with_no_contact_details_still_renders():
    """Calibration: the assertions above detect content, not a template constant.

    Without this a block that hard-coded every label would satisfy them.
    """
    text = await _rfq_text({"name": "Quiet Lab"})
    assert "Manufacturing Quotation Request" in text
    assert "Email:" not in text
    assert "Location:     Location not specified" in text


# --- The bundle: an email a workshop can actually answer (#498) -------------


@pytest.mark.asyncio
@pytest.mark.contract
async def test_bundle_returns_one_document_per_facility():
    """The zip is what gets attached to an email, so its shape is the contract."""
    import io
    import zipfile

    app = _get_app()
    payload = {
        "okh_id": "okh-1",
        "okh_title": "Open Source Ventilator",
        "quantity": 25,
        "solutions": [
            _solution(facility_id="f1", facility_name="Bristol Fab Lab"),
            _solution(facility_id="f2", facility_name="Rotterdam Precision Works"),
        ],
    }
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(
        transport=transport, base_url="http://testserver"
    ) as client:
        resp = await client.post("/v1/api/rfq/bundle", json=payload)

    assert resp.status_code == 200, resp.text
    assert resp.headers["content-type"] == "application/zip"
    assert "rfq-open-source-ventilator-" in resp.headers["content-disposition"]

    names = zipfile.ZipFile(io.BytesIO(resp.content)).namelist()
    assert len(names) == 2, names
    assert any("bristol-fab-lab" in n for n in names)
    assert any("rotterdam-precision-works" in n for n in names)


@pytest.mark.asyncio
@pytest.mark.contract
async def test_bundle_names_the_package_it_encloses():
    """The RFQ must name the file actually in the zip, not one someone hoped for.

    Patched at the resolver rather than building a real package: the property
    under test is that the rendered text and the archive agree, and a genuine
    build would prove that no better while taking a network round trip per
    asset.
    """
    import io
    import zipfile
    from unittest.mock import AsyncMock, patch

    app = _get_app()
    payload = {
        "okh_id": "okh-1",
        "okh_title": "Widget",
        "quantity": 1,
        "solutions": [_solution()],
    }
    transport = httpx.ASGITransport(app=app)
    with patch(
        "src.core.api.routes.rfq._resolve_design_package",
        new=AsyncMock(return_value=(b"tarball-bytes", "acme-widget-1.0.0.tar.gz")),
    ):
        async with httpx.AsyncClient(
            transport=transport, base_url="http://testserver"
        ) as client:
            resp = await client.post("/v1/api/rfq/bundle", json=payload)

    assert resp.status_code == 200, resp.text
    archive = zipfile.ZipFile(io.BytesIO(resp.content))
    assert "acme-widget-1.0.0.tar.gz" in archive.namelist()
    rfq_text = next(
        archive.read(n).decode() for n in archive.namelist() if n.endswith(".txt")
    )
    assert "Attached:     acme-widget-1.0.0.tar.gz" in rfq_text


@pytest.mark.asyncio
@pytest.mark.contract
async def test_bundle_without_a_package_still_sends_the_documents():
    """Calibration, and the degradation that matters.

    Without this the test above would pass against a bundle that always
    attached something. It also pins the behaviour: the RFQs are the part that
    cannot be reconstructed by hand, so a missing package must not cost them.
    """
    import io
    import zipfile

    app = _get_app()
    payload = {
        "okh_id": "not-a-manifest-id",
        "okh_title": "Widget",
        "quantity": 1,
        "solutions": [_solution()],
    }
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(
        transport=transport, base_url="http://testserver"
    ) as client:
        resp = await client.post("/v1/api/rfq/bundle", json=payload)

    assert resp.status_code == 200, resp.text
    archive = zipfile.ZipFile(io.BytesIO(resp.content))
    assert all(n.endswith(".txt") for n in archive.namelist())
    text = archive.read(archive.namelist()[0]).decode()
    assert "The design package is sent alongside this request." in text


@pytest.mark.asyncio
@pytest.mark.contract
async def test_the_rfq_never_tells_the_reader_to_call_an_api():
    """The recipient is a workshop that has never heard of OHM.

    This is the property the redesign exists for, so it is asserted directly
    rather than inferred from the section that used to break it.
    """
    text = await _rfq_text(_FULL_CONTACT_FACILITY)
    assert "/v1/api/" not in text
    assert "POST " not in text
    assert "GET  " not in text
