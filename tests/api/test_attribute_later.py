"""An owner attributes an existing record once they hold an affiliation (#589)."""

from __future__ import annotations

from uuid import UUID

import pytest

from src.core.federation.catalog import manifest_content_hash
from src.core.models.provenance import Credit, RecordProvenance, verify_provenance
from src.core.models.visibility import VisibilityLevel
from src.core.services.base import ServiceStatus
from src.core.services.okh_service import OKHService
from src.core.services.okw_service import OKWService
from tests.api.test_affiliation_required import (
    FACILITY,
    MINIMAL,
    _FakeStorageService,
    _ada,
    _auth,
    _client,
)


def _records():
    okh = OKHService()
    okh.storage = _FakeStorageService()
    okh.status = ServiceStatus.ACTIVE
    return okh


@pytest.mark.asyncio
async def test_an_owner_attributes_an_existing_design_without_changing_its_hash(
    tmp_path, monkeypatch
):
    from src.core.api.routes.okh import get_okh_service

    service = _auth(tmp_path)
    ada, grace, space, ada_key = await _ada(service)
    await service.affiliate(grace.did, space.did, ada.did)
    okh = _records()
    manifest = dict(MINIMAL)
    await okh.create(
        manifest,
        created_by=ada.account_id,
        created_by_did=ada.did,
        provenance=service.sign_provenance_if_possible(
            RecordProvenance(
                authored_by=[Credit(subject_did=ada.did, role="author")],
                published_by=ada.did,
            )
        ),
    )
    before = manifest_content_hash((await okh.get(UUID(manifest["id"]))).to_dict())

    async with _client(
        monkeypatch, service, overrides={get_okh_service: lambda: okh}
    ) as client:
        resp = await client.put(
            f"/v1/api/okh/{manifest['id']}/attribution",
            headers={"Authorization": f"Bearer {ada_key.token}"},
            json={"on_behalf_of": space.did},
        )

    assert resp.status_code == 200, resp.text
    body = RecordProvenance.model_validate(resp.json())
    assert body.on_behalf_of == space.did
    assert body.space_claim is not None
    assert body.space_claim.admin_did == grace.did
    assert body.affiliation is not None
    assert body.affiliation.subject_did == ada.did
    assert "publish" in body.affiliation.permissions
    assert verify_provenance(body)
    after = manifest_content_hash((await okh.get(UUID(manifest["id"]))).to_dict())
    assert after == before


@pytest.mark.asyncio
async def test_an_owner_without_the_affiliation_is_refused(tmp_path, monkeypatch):
    from src.core.api.routes.okh import get_okh_service

    service = _auth(tmp_path)
    ada, _grace, space, ada_key = await _ada(service)
    okh = _records()
    manifest = dict(MINIMAL)
    await okh.create(
        manifest,
        created_by=ada.account_id,
        created_by_did=ada.did,
        provenance=service.sign_provenance_if_possible(
            RecordProvenance(
                authored_by=[Credit(subject_did=ada.did, role="author")],
                published_by=ada.did,
            )
        ),
    )

    async with _client(
        monkeypatch, service, overrides={get_okh_service: lambda: okh}
    ) as client:
        resp = await client.put(
            f"/v1/api/okh/{manifest['id']}/attribution",
            headers={"Authorization": f"Bearer {ada_key.token}"},
            json={"on_behalf_of": space.did},
        )

    assert resp.status_code == 403, resp.text
    assert "not yet" in resp.text
    stored = await okh.get_provenance(UUID(manifest["id"]))
    assert stored is not None
    assert stored.on_behalf_of is None


@pytest.mark.asyncio
async def test_someone_else_cannot_attribute_the_record(tmp_path, monkeypatch):
    from src.core.api.routes.okh import get_okh_service
    from src.core.models.auth import APIKeyCreate
    from src.core.models.identity import IdentityKind
    from uuid import uuid4

    service = _auth(tmp_path)
    ada, grace, space, _ada_key = await _ada(service)
    await service.affiliate(grace.did, space.did, ada.did)
    bob_account = uuid4()
    bob = await service.create_identity(bob_account, IdentityKind.PERSON, "Bob")
    await service.affiliate(grace.did, space.did, bob.did)
    bob_key = await service.create_api_key(
        APIKeyCreate(name="bob", permissions=["write"], account_id=bob_account)
    )
    okh = _records()
    manifest = dict(MINIMAL)
    await okh.create(
        manifest,
        created_by=ada.account_id,
        created_by_did=ada.did,
    )

    async with _client(
        monkeypatch, service, overrides={get_okh_service: lambda: okh}
    ) as client:
        resp = await client.put(
            f"/v1/api/okh/{manifest['id']}/attribution",
            headers={"Authorization": f"Bearer {bob_key.token}"},
            json={"on_behalf_of": space.did},
        )

    assert resp.status_code == 403, resp.text
    assert "write access" in resp.text
    assert await okh.get_provenance(UUID(manifest["id"])) is None


@pytest.mark.asyncio
async def test_the_owner_can_remove_an_attribution(tmp_path, monkeypatch):
    from src.core.api.routes.okh import get_okh_service

    service = _auth(tmp_path)
    ada, grace, space, ada_key = await _ada(service)
    grant = await service.affiliate(grace.did, space.did, ada.did)
    okh = _records()
    manifest = dict(MINIMAL)
    await okh.create(
        manifest,
        created_by=ada.account_id,
        created_by_did=ada.did,
        provenance=service.sign_provenance_if_possible(
            RecordProvenance(
                authored_by=[Credit(subject_did=ada.did, role="author")],
                published_by=ada.did,
            )
        ),
    )
    before = manifest_content_hash((await okh.get(UUID(manifest["id"]))).to_dict())

    async with _client(
        monkeypatch, service, overrides={get_okh_service: lambda: okh}
    ) as client:
        added = await client.put(
            f"/v1/api/okh/{manifest['id']}/attribution",
            headers={"Authorization": f"Bearer {ada_key.token}"},
            json={"on_behalf_of": space.did},
        )
        assert added.status_code == 200, added.text
        await service.revoke_grant(grant.grant_id)
        removed = await client.put(
            f"/v1/api/okh/{manifest['id']}/attribution",
            headers={"Authorization": f"Bearer {ada_key.token}"},
            json={"on_behalf_of": None},
        )

    assert removed.status_code == 200, removed.text
    body = RecordProvenance.model_validate(removed.json())
    assert body.on_behalf_of is None
    assert body.space_claim is None
    assert body.affiliation is None
    assert body.published_by == ada.did
    assert verify_provenance(body)
    after = manifest_content_hash((await okh.get(UUID(manifest["id"]))).to_dict())
    assert after == before


@pytest.mark.asyncio
async def test_an_owner_attributes_an_existing_facility_without_changing_its_hash(
    tmp_path, monkeypatch
):
    from src.core.api.routes.okw import get_okw_service

    service = _auth(tmp_path)
    ada, grace, space, ada_key = await _ada(service)
    await service.affiliate(grace.did, space.did, ada.did)
    okw = OKWService()
    okw.storage = _FakeStorageService()
    okw.status = ServiceStatus.ACTIVE
    facility = await okw.create(
        dict(FACILITY),
        created_by=ada.account_id,
        created_by_did=ada.did,
        provenance=service.sign_provenance_if_possible(
            RecordProvenance(
                authored_by=[Credit(subject_did=ada.did, role="author")],
                published_by=ada.did,
            )
        ),
    )
    before = manifest_content_hash(facility.to_dict())

    async with _client(
        monkeypatch, service, overrides={get_okw_service: lambda: okw}
    ) as client:
        resp = await client.put(
            f"/v1/api/okw/{facility.id}/attribution",
            headers={"Authorization": f"Bearer {ada_key.token}"},
            json={"on_behalf_of": space.did},
        )

    assert resp.status_code == 200, resp.text
    body = RecordProvenance.model_validate(resp.json())
    assert body.on_behalf_of == space.did
    assert verify_provenance(body)
    assert body.space_claim is not None and body.affiliation is not None
    after = manifest_content_hash((await okw.get(facility.id)).to_dict())
    assert after == before


@pytest.mark.asyncio
async def test_an_owner_attributes_several_designs_at_once(tmp_path, monkeypatch):
    from uuid import uuid4

    from src.core.api.routes.okh import get_okh_service

    service = _auth(tmp_path)
    ada, grace, space, ada_key = await _ada(service)
    await service.affiliate(grace.did, space.did, ada.did)
    okh = _records()
    mine = dict(MINIMAL)
    theirs = dict(MINIMAL)
    theirs["id"] = str(uuid4())
    theirs["title"] = "Someone else's"
    await okh.create(mine, created_by=ada.account_id, created_by_did=ada.did)
    await okh.create(theirs, created_by=str(uuid4()), created_by_did="did:key:zBob")
    await okh.set_visibility(UUID(theirs["id"]), VisibilityLevel.PUBLIC)
    before = manifest_content_hash((await okh.get(UUID(mine["id"]))).to_dict())

    async with _client(
        monkeypatch, service, overrides={get_okh_service: lambda: okh}
    ) as client:
        resp = await client.post(
            "/v1/api/okh/attribution",
            headers={"Authorization": f"Bearer {ada_key.token}"},
            json={"ids": [mine["id"], theirs["id"]], "on_behalf_of": space.did},
        )

    assert resp.status_code == 200, resp.text
    by_id = {row["id"]: row for row in resp.json()["results"]}
    assert by_id[mine["id"]]["outcome"] == "changed"
    assert by_id[mine["id"]]["on_behalf_of"] == space.did
    assert by_id[theirs["id"]]["outcome"] == "not_yours"
    stored = await okh.get_provenance(UUID(mine["id"]))
    assert stored is not None and verify_provenance(stored)
    assert await okh.get_provenance(UUID(theirs["id"])) is None
    after = manifest_content_hash((await okh.get(UUID(mine["id"]))).to_dict())
    assert after == before
