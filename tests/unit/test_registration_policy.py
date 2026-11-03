"""The public security policy reports who may register (#568)."""

import httpx
import pytest

from src.config import settings
from src.core.auth.registration import Registration, save


@pytest.mark.asyncio
async def test_the_public_policy_reports_a_closed_registration(tmp_path, monkeypatch):
    monkeypatch.setattr(settings, "OHM_FEDERATION_DATA_DIR", str(tmp_path))
    save(Registration.CLOSED)

    from src.core.main import api_v1
    from fastapi import FastAPI

    app = FastAPI()
    app.mount("/v1", api_v1)
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(
        transport=transport, base_url="http://testserver"
    ) as client:
        resp = await client.get("/v1/api/identity/security-policy")

    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["registration"] == "closed"
    # The mode knob stays. Recovery still follows it, and a closed peacetime
    # node has not switched to shielded.
    assert body["open_registration"] is True


@pytest.mark.asyncio
async def test_anonymous_cannot_change_registration(tmp_path, monkeypatch):
    monkeypatch.setattr(settings, "OHM_FEDERATION_DATA_DIR", str(tmp_path))

    from fastapi import FastAPI

    from src.core.main import api_v1

    app = FastAPI()
    app.mount("/v1", api_v1)
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(
        transport=transport, base_url="http://testserver"
    ) as client:
        resp = await client.put(
            "/v1/api/identity/registration",
            json={"registration": "closed"},
        )

    assert resp.status_code == 401


@pytest.mark.asyncio
async def test_an_admin_sets_registration_and_the_policy_reports_it(
    tmp_path, monkeypatch
):
    monkeypatch.setattr(settings, "OHM_FEDERATION_DATA_DIR", str(tmp_path))
    from uuid import uuid4

    from fastapi import FastAPI

    from src.core.api.dependencies import require_admin_strict
    from src.core.main import api_v1
    from src.core.models.auth import AuthenticatedUser

    admin = AuthenticatedUser(
        key_id=uuid4(),
        name="admin",
        permissions=["admin"],
        account_id=uuid4(),
    )
    app = FastAPI()
    app.mount("/v1", api_v1)
    api_v1.dependency_overrides[require_admin_strict] = lambda: admin
    try:
        transport = httpx.ASGITransport(app=app)
        async with httpx.AsyncClient(
            transport=transport, base_url="http://testserver"
        ) as client:
            updated = await client.put(
                "/v1/api/identity/registration",
                json={"registration": "invite"},
            )
            assert updated.status_code == 200, updated.text
            assert updated.json() == {"registration": "invite"}
            policy = await client.get("/v1/api/identity/security-policy")
    finally:
        api_v1.dependency_overrides.pop(require_admin_strict, None)

    assert policy.status_code == 200, policy.text
    assert policy.json()["registration"] == "invite"
    assert policy.json()["open_registration"] is True
