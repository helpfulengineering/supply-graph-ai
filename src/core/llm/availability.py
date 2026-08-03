"""Resolve, once per run, whether an LLM is actually usable.

Generation used to answer this question twice, differently. The gate that
decides whether the LLM layer joins the stack looked only at process
environment variables, while the service that would have run it reads the
encrypted credential store first. The gate wins, so a key configured through
**Settings → LLM providers** caused the layer to be dropped *before* the
service was ever constructed — the store worked, but nothing reached it.

There is one answer now, produced here. It is resolved **asynchronously at the
entry point** (reading the store awaits storage) and then carried as plain
values on ``LayerConfig``, which the synchronous gate reads. That kills both the
duplicate resolution and the sync/async mismatch that caused it, and it means
the answer cannot change midway through a run — so the progress stages and the
enabled-layer stack always agree.

Availability here means **declared configuration**: a key present in the
credential store or the process environment. Whether the key is *valid* is not
knowable without spending money, so a run that fails at call time degrades and
is reported as such.
"""

from __future__ import annotations

import logging
import os
from dataclasses import dataclass
from typing import List, Optional

logger = logging.getLogger(__name__)

# Tried in order when no provider is named. Deliberately excludes LOCAL/ollama:
# it has no credential to detect and its client falls back to localhost, so
# including it here would make every node believe a local model is available.
# Ollama is opt-in only — see OLLAMA_BASE_URL below.
PROVIDER_PREFERENCE: List[str] = ["anthropic", "openai", "azure_openai"]

# Ollama authenticates with nothing, so "is a key present" cannot answer whether
# it is usable. It counts only when explicitly named as the default provider, or
# when its base URL is set — never inferred from the client's localhost default.
OLLAMA_PROVIDER = "local"
OLLAMA_BASE_URL_ENV = "OLLAMA_BASE_URL"

# Environment variable holding each provider's key, checked when the credential
# store has nothing. Keeps the local `.env` workflow working unchanged.
PROVIDER_ENV_KEYS = {
    "anthropic": "ANTHROPIC_API_KEY",
    "openai": "OPENAI_API_KEY",
    "azure_openai": "AZURE_OPENAI_API_KEY",
    "aws_bedrock": "AWS_BEDROCK_API_KEY",
    "google": "GOOGLE_APPLICATION_CREDENTIALS",
}


class LLMUnavailableReason:
    """Why no LLM will run. Surfaced to users by #315."""

    NOT_REQUESTED = "not_requested"
    DISABLED = "disabled"
    NOT_CONFIGURED = "not_configured"


@dataclass(frozen=True)
class LLMAvailability:
    """The single answer to "will an LLM run, and which one?"."""

    available: bool
    provider: Optional[str] = None
    source: Optional[str] = None  # "credential_store" | "environment"
    reason: Optional[str] = None  # set when unavailable

    @classmethod
    def unavailable(cls, reason: str) -> "LLMAvailability":
        return cls(available=False, reason=reason)


async def _stored_key(provider: str) -> Optional[str]:
    """Key from the encrypted credential store, or None if absent/unreadable."""
    try:
        from src.config.llm_config import CredentialManager, LLMProvider

        from ..services.storage_service import StorageService
        from ..storage.llm_credential_store import LLMCredentialStore

        storage = await StorageService.get_instance()
        store = LLMCredentialStore(storage, CredentialManager())
        return await store.load(LLMProvider(provider))
    except Exception as exc:  # storage down, provider unknown, undecryptable
        logger.debug("No stored credential for %s: %s", provider, exc)
        return None


def _configured_ollama_url() -> Optional[str]:
    """An explicitly configured ollama endpoint, or None."""
    value = os.getenv(OLLAMA_BASE_URL_ENV, "").strip()
    return value or None


def _ollama_base_url(*, explicitly_chosen: bool) -> Optional[str]:
    """Where ollama is, or None if it was not opted into.

    Two ways in, both deliberate: setting the base URL, or naming ollama as the
    provider (which falls back to its client's localhost default). Never
    inferred from that default alone — a node that merely has the library
    installed would otherwise claim a local model it does not have.
    """
    return _configured_ollama_url() or (
        "http://localhost:11434" if explicitly_chosen else None
    )


def _env_key(provider: str) -> Optional[str]:
    name = PROVIDER_ENV_KEYS.get(provider)
    value = os.getenv(name, "").strip() if name else ""
    return value or None


async def resolve_llm_availability(
    *,
    requested: bool = True,
    preferred_provider: Optional[str] = None,
) -> LLMAvailability:
    """Decide whether an LLM will run for this generation, and which provider.

    Args:
        requested: False when the caller explicitly opted out (``no_llm``).
        preferred_provider: An explicitly chosen provider; tried alone rather
            than falling back, so an explicit choice never silently becomes a
            different provider.

    Resolution order per provider: the credential store first (what the Settings
    UI writes), then the process environment (what a local ``.env`` provides).
    """
    if not requested:
        return LLMAvailability.unavailable(LLMUnavailableReason.NOT_REQUESTED)

    from src.config.schema import get_settings

    settings = get_settings()
    if not settings.llm_enabled:
        logger.info("LLM disabled by configuration (LLM_ENABLED=false)")
        return LLMAvailability.unavailable(LLMUnavailableReason.DISABLED)

    chosen = preferred_provider or settings.llm_default_provider
    if chosen:
        # An explicit choice is tried ALONE. Falling back would silently serve a
        # different provider than the one asked for, which is worse than failing.
        candidates = [chosen]
    else:
        # Ollama joins auto-selection only when its base URL is set, which is a
        # deliberate act. It is never reached via its client's localhost
        # default, which every node would otherwise appear to satisfy.
        candidates = list(PROVIDER_PREFERENCE)
        if _configured_ollama_url():
            candidates.append(OLLAMA_PROVIDER)

    for provider in candidates:
        if provider == OLLAMA_PROVIDER:
            base_url = _ollama_base_url(explicitly_chosen=bool(chosen))
            if base_url:
                logger.info("LLM available: ollama at %s", base_url)
                return LLMAvailability(
                    available=True, provider=provider, source="ollama"
                )
            continue

        if await _stored_key(provider):
            logger.info("LLM available: %s (stored credential)", provider)
            return LLMAvailability(
                available=True, provider=provider, source="credential_store"
            )
        if _env_key(provider):
            logger.info("LLM available: %s (environment)", provider)
            return LLMAvailability(
                available=True, provider=provider, source="environment"
            )

    logger.info(
        "No LLM provider configured (tried: %s); generation will run without one",
        ", ".join(candidates),
    )
    return LLMAvailability.unavailable(LLMUnavailableReason.NOT_CONFIGURED)
