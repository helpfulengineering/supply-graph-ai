"""LLM credential store: encrypted persistence through the public store interface."""

import pytest
from cryptography.fernet import Fernet

from src.config.llm_config import CredentialManager, LLMProvider
from src.core.storage.llm_credential_store import LLMCredentialStore


class _InMemoryManager:
    def __init__(self) -> None:
        self._objects: dict[str, bytes] = {}

    async def put_object(self, key, data, content_type=None, metadata=None):
        self._objects[key] = data

    async def get_object(self, key):
        return self._objects[key]

    async def delete_object(self, key):
        self._objects.pop(key, None)
        return True

    async def list_objects(self, prefix=None):
        for key, data in self._objects.items():
            if prefix is None or key.startswith(prefix):
                yield {"key": key, "data": data}


class _FakeStorageService:
    def __init__(self) -> None:
        self.manager = _InMemoryManager()


@pytest.fixture
def store() -> LLMCredentialStore:
    key = Fernet.generate_key().decode()
    return LLMCredentialStore(
        _FakeStorageService(),
        CredentialManager(encryption_key=key),
    )


@pytest.mark.asyncio
async def test_saved_credential_is_retrievable(store: LLMCredentialStore):
    await store.save(LLMProvider.ANTHROPIC, "sk-test-secret")
    assert await store.load(LLMProvider.ANTHROPIC) == "sk-test-secret"


@pytest.mark.asyncio
async def test_refuses_to_store_under_default_encryption(monkeypatch):
    monkeypatch.delenv("LLM_ENCRYPTION_KEY", raising=False)
    monkeypatch.delenv("LLM_ENCRYPTION_SALT", raising=False)
    monkeypatch.delenv("LLM_ENCRYPTION_PASSWORD", raising=False)
    monkeypatch.setenv("ENVIRONMENT", "development")
    store = LLMCredentialStore(_FakeStorageService(), CredentialManager())
    with pytest.raises(ValueError, match="default encryption"):
        await store.save(LLMProvider.ANTHROPIC, "sk-should-not-persist")
    assert await store.load(LLMProvider.ANTHROPIC) is None


@pytest.mark.asyncio
async def test_missing_credential_is_absent(store: LLMCredentialStore):
    assert await store.load(LLMProvider.OPENAI) is None


@pytest.mark.asyncio
async def test_deleted_credential_is_absent(store: LLMCredentialStore):
    await store.save(LLMProvider.ANTHROPIC, "sk-temp")
    assert await store.delete(LLMProvider.ANTHROPIC) is True
    assert await store.load(LLMProvider.ANTHROPIC) is None


@pytest.mark.asyncio
async def test_status_never_exposes_full_key(store: LLMCredentialStore):
    secret = "sk-ant-api03-SUPER-SECRET-VALUE-123456"
    await store.save(LLMProvider.ANTHROPIC, secret, model="claude-3-sonnet")
    statuses = await store.list_status()
    assert len(statuses) == 1
    status = statuses[0]
    assert status["provider"] == "anthropic"
    assert status["model"] == "claude-3-sonnet"
    assert status["masked_key"].endswith(secret[-4:])
    assert secret not in status["masked_key"]
    assert "encrypted" not in status
    assert "api_key" not in status
