"""Unit tests for the Account model + AccountStorage round-trip (Slice 1)."""

import pytest

from src.core.models.account import Account, AccountKind
from src.core.storage.account_storage import AccountStorage


class _InMemoryManager:
    """Minimal StorageService.manager stand-in backed by a dict."""

    def __init__(self) -> None:
        self._objects: dict[str, bytes] = {}

    async def put_object(self, key, data, content_type=None, metadata=None):
        self._objects[key] = data

    async def get_object(self, key):
        return self._objects[key]

    async def list_objects(self, prefix=None):
        for key, data in self._objects.items():
            if prefix is None or key.startswith(prefix):
                yield {"key": key, "data": data}


class _FakeStorageService:
    def __init__(self) -> None:
        self.manager = _InMemoryManager()


@pytest.fixture
def storage() -> AccountStorage:
    return AccountStorage(_FakeStorageService())


@pytest.mark.asyncio
async def test_save_and_load_round_trip(storage):
    account = Account(display_name="MIT FabLab", kind=AccountKind.SPACE)
    await storage.save_account(account)

    loaded = await storage.load_account(account.id)
    assert loaded is not None
    assert loaded.id == account.id
    assert loaded.display_name == "MIT FabLab"
    assert loaded.kind is AccountKind.SPACE
    assert loaded.disabled is False


@pytest.mark.asyncio
async def test_list_accounts(storage):
    a = Account(display_name="Ada")
    b = Account(display_name="Grace")
    await storage.save_account(a)
    await storage.save_account(b)

    names = {acc.display_name for acc in await storage.list_accounts()}
    assert names == {"Ada", "Grace"}


@pytest.mark.asyncio
async def test_disable_persists(storage):
    account = Account(display_name="Temp")
    await storage.save_account(account)

    account.disabled = True
    await storage.save_account(account)

    loaded = await storage.load_account(account.id)
    assert loaded is not None and loaded.disabled is True


@pytest.mark.asyncio
async def test_load_missing_returns_none(storage):
    from uuid import uuid4

    assert await storage.load_account(uuid4()) is None
