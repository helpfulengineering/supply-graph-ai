"""Apply persisted LLM credentials to a running LLMService."""

from __future__ import annotations

from typing import Optional

from src.config.llm_config import LLMProvider

from ..storage.llm_credential_store import LLMCredentialStore
from .provider_selection import get_provider_selector
from .providers.base import LLMProviderConfig, LLMProviderType
from .service import LLMService


def _to_provider_type(provider: LLMProvider) -> LLMProviderType:
    return LLMProviderType(provider.value)


async def apply_stored_credential(
    llm_service: LLMService,
    store: LLMCredentialStore,
    provider: LLMProvider,
    *,
    model: Optional[str] = None,
    set_active: bool = True,
) -> bool:
    """Load a stored key and hot-swap it into ``llm_service``.

    Returns True when the provider was added (and optionally activated).
    Invalidates the provider-selector availability cache so subsequent
    selection sees the new key without a process restart.
    """
    api_key = await store.load(provider)
    if not api_key:
        return False

    provider_type = _to_provider_type(provider)
    if provider_type in llm_service._providers:
        await llm_service.remove_provider(provider_type)

    config = LLMProviderConfig(
        provider_type=provider_type,
        api_key=api_key,
        model=model or llm_service.config.default_model,
    )
    added = await llm_service.add_provider(config)
    if not added:
        return False

    if set_active:
        await llm_service.set_active_provider(provider_type)

    get_provider_selector().invalidate_availability_cache()
    return True
