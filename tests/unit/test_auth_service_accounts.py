"""Unit tests for AuthenticationService account + attribution behavior (Slice 1)."""

import pytest

from src.config import settings
from src.core.models.account import ROOT_ACCOUNT_ID, AccountCreate, AccountKind
from src.core.models.auth import APIKeyCreate
from src.core.services.auth_service import AuthenticationService
from src.core.storage.account_storage import AccountStorage
from src.core.storage.auth_storage import AuthStorage


class _InMemoryManager:
    def __init__(self) -> None:
        self._objects: dict[str, bytes] = {}

    async def put_object(self, key, data, content_type=None, metadata=None):
        self._objects[key] = data

    async def get_object(self, key):
        return self._objects[key]

    async def list_objects(self, prefix=None):
        for key, data in list(self._objects.items()):
            if prefix is None or key.startswith(prefix):
                yield {"key": key, "data": data}


class _FakeStorageService:
    def __init__(self) -> None:
        self.manager = _InMemoryManager()


@pytest.fixture
def service() -> AuthenticationService:
    svc = AuthenticationService()
    storage = _FakeStorageService()
    svc._auth_storage = AuthStorage(storage)
    svc._account_storage = AccountStorage(storage)
    svc._initialized = True
    return svc


@pytest.mark.asyncio
async def test_account_crud(service):
    created = await service.create_account(
        AccountCreate(display_name="MIT FabLab", kind=AccountKind.SPACE)
    )
    accounts = await service.list_accounts()
    assert [a.id for a in accounts] == [created.id]

    disabled = await service.disable_account(created.id)
    assert disabled.disabled is True


@pytest.mark.asyncio
async def test_key_bound_to_account_and_attributed(service):
    account = await service.create_account(AccountCreate(display_name="Ada"))
    resp = await service.create_api_key(
        APIKeyCreate(name="ada-key", permissions=["write"], account_id=account.id)
    )
    assert resp.token is not None  # token returned only on creation

    user = await service.validate_api_key(resp.token)
    assert user.account_id == account.id
    assert "write" in user.permissions


@pytest.mark.asyncio
async def test_list_keys_never_returns_tokens(service):
    await service.create_api_key(APIKeyCreate(name="k", permissions=["read"]))
    listed = await service.list_api_keys()
    assert listed and all(k.token is None for k in listed)


@pytest.mark.asyncio
async def test_key_defaults_to_root_account(service):
    resp = await service.create_api_key(APIKeyCreate(name="rootless"))
    user = await service.validate_api_key(resp.token)
    assert user.account_id == ROOT_ACCOUNT_ID


@pytest.mark.asyncio
async def test_env_key_maps_to_root_account(service, monkeypatch):
    monkeypatch.setattr(settings, "API_KEYS", ["env-secret-token"], raising=False)
    user = await service.validate_api_key("env-secret-token")
    assert user.account_id == ROOT_ACCOUNT_ID
    assert "admin" in user.permissions
