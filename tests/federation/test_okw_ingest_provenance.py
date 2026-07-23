"""OKW federation ingest stamps synced provenance for the UI banner."""

from __future__ import annotations

from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest

from src.core.federation.identity import generate_identity
from src.core.federation.okw_catalog import OkwCatalogRecord, SignedOkwRecord
from src.core.federation.store import FederationStore


@pytest.mark.unit
@pytest.mark.asyncio
async def test_okw_ingest_stamps_synced_from_provenance(tmp_path) -> None:
    publisher = generate_identity("Seed Peer")
    facility_id = uuid4()
    facility = {"id": str(facility_id), "name": "Seed Lab"}
    catalog = OkwCatalogRecord(
        facility_id=facility_id,
        content_hash="sha256:abc",
        name="Seed Lab",
        updated_at=datetime.now(timezone.utc),
        publisher_did=publisher.did,
        visibility="followers",
        signature="00" * 64,
    )
    signed = SignedOkwRecord(
        catalog_record=catalog,
        facility=facility,
        facility_signature="00" * 64,
    )
    store = FederationStore(tmp_path)
    store.set_followed(publisher.did, True)
    okw = AsyncMock()
    okw.get = AsyncMock(return_value=None)
    okw.create = AsyncMock(return_value=MagicMock())

    with patch(
        "src.core.federation.okw_ingest.verify_signed_okw_record",
        return_value=None,
    ):
        from src.core.federation.okw_ingest import verify_and_store_okw

        result = await verify_and_store_okw(
            signed,
            publisher_did=publisher.did,
            store=store,
            okw_service=okw,
            local_content_hashes=set(),
        )

    assert result.action == "stored"
    _args, kwargs = okw.create.await_args
    prov = kwargs["provenance"]
    assert prov.published_by == publisher.did
    assert prov.authored_by[0].role == "synced_from"
    assert prov.authored_by[0].subject_did == publisher.did
