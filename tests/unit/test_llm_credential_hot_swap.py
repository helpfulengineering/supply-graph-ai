"""Stored credentials can be hot-swapped into a running LLMService."""

from __future__ import annotations

from typing import List

import pytest
from cryptography.fernet import Fernet

from src.config.llm_config import CredentialManager, LLMProvider
from src.core.llm.credentials import apply_stored_credential
from src.core.llm.providers.base import BaseLLMProvider, LLMProviderType
from src.core.llm.service import LLMService, LLMServiceConfig
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


class _FakeProvider(BaseLLMProvider):
    """Minimal provider that connects without network I/O."""

    async def connect(self) -> None:
        self._connected = True

    async def disconnect(self) -> None:
        self._connected = False

    async def generate(self, request):
        raise NotImplementedError

    async def health_check(self) -> bool:
        return self._connected

    def get_available_models(self) -> List[str]:
        return [self.config.model]

    def estimate_cost(self, request) -> float:
        return 0.0


@pytest.mark.asyncio
async def test_apply_stored_credential_registers_and_activates_provider():
    store = LLMCredentialStore(
        _FakeStorageService(),
        CredentialManager(encryption_key=Fernet.generate_key().decode()),
    )
    await store.save(LLMProvider.ANTHROPIC, "sk-live-key", model="claude-test")

    svc = LLMService(
        "test-llm-hot-swap",
        LLMServiceConfig(name="test-llm-hot-swap", providers={}),
    )
    # Skip real Anthropic init; register a fake class for the test.
    svc._provider_classes = {LLMProviderType.ANTHROPIC: _FakeProvider}
    svc._providers = {}
    svc._provider_configs = {}
    svc._active_provider = None

    ok = await apply_stored_credential(
        svc, store, LLMProvider.ANTHROPIC, model="claude-test"
    )
    assert ok is True
    assert LLMProviderType.ANTHROPIC in svc._providers
    assert svc._active_provider == LLMProviderType.ANTHROPIC
    assert svc._provider_configs[LLMProviderType.ANTHROPIC].api_key == "sk-live-key"
    assert svc._provider_configs[LLMProviderType.ANTHROPIC].model == "claude-test"
