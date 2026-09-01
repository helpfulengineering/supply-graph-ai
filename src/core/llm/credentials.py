"""Apply persisted LLM credentials to a running LLMService."""

from __future__ import annotations

from typing import List, Optional

from src.config.llm_config import LLMProvider

from ..storage.llm_credential_store import LLMCredentialStore
from .provider_selection import get_provider_selector
from .providers.base import LLMProviderConfig, LLMProviderType
from .service import LLMService
from ..utils.logging import get_logger

logger = get_logger(__name__)


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


async def activate_stored_credentials(
    llm_service: LLMService,
    store: LLMCredentialStore,
    statuses: Optional[List[dict]] = None,
) -> List[str]:
    """Load every stored provider credential into ``llm_service``.

    Called at startup, because storing a credential and activating it are two
    different lifetimes and only the first was durable. ``apply_stored_credential``
    hot-swaps a key into the *in-process* service, so a credential saved through
    the API was active only in the worker that handled the request — and
    ``/api/llm/health`` reports in-process state. With several gunicorn workers,
    or more than one replica, or after any restart, the key was in storage and
    the node still said "unavailable". The save had worked; the activation had
    not survived.

    Which provider ends up active is a **recorded fact**, not a guess: the
    store keeps an explicit active-provider record, written whenever a
    credential is saved with ``activate`` or a provider is made active. Only
    when there is no record — a node that predates it, or one whose recorded
    provider has since been deleted — does this fall back to the configured
    default, then to the first in a stable order, so two workers reading the
    same store still agree.

    ``statuses`` lets a caller that has already listed the store pass the result
    in rather than paying for a second read.

    Returns the provider names activated. Never raises: an LLM is optional, and
    a node that will not start because a stored key has expired is worse than
    one that logs it and falls back to heuristic extraction.
    """
    activated: List[str] = []

    if statuses is None:
        try:
            statuses = await store.list_status()
        except Exception as exc:  # noqa: BLE001 — startup must not depend on this
            logger.warning("Could not read stored LLM credentials: %s", exc)
            return activated

    for row in sorted(statuses, key=lambda r: str(r.get("provider") or "")):
        name = row.get("provider")
        if not name:
            continue
        try:
            provider = LLMProvider(name)
        except ValueError:
            logger.warning("Ignoring stored credential for unknown provider %r", name)
            continue

        try:
            added = await apply_stored_credential(
                llm_service,
                store,
                provider,
                model=row.get("model"),
                # Activation is decided once, below, rather than by whichever
                # provider happened to be applied last.
                set_active=False,
            )
        except Exception as exc:  # noqa: BLE001 — one bad key must not stop the rest
            # The exception type is logged alongside the message because the
            # message can be empty — InvalidToken carries none, and this line
            # once read "could not be activated: " with nothing after it.
            logger.warning(
                "Stored %s credential could not be activated: %s: %s",
                name,
                type(exc).__name__,
                exc,
            )
            continue

        if added:
            activated.append(name)
        else:
            logger.warning(
                "Stored %s credential did not load; the key may have been "
                "revoked or the encryption material changed.",
                name,
            )

    if not activated:
        return activated

    recorded = await store.get_active()
    if recorded is not None and recorded.value in activated:
        chosen = recorded.value
    else:
        if recorded is not None:
            logger.warning(
                "Recorded active LLM provider %r is not among the stored "
                "credentials; falling back.",
                recorded.value,
            )
        preferred = llm_service.config.default_provider
        chosen = (
            preferred.value
            if preferred is not None and preferred.value in activated
            else activated[0]
        )
    await llm_service.set_active_provider(_to_provider_type(LLMProvider(chosen)))
    logger.info(
        "Activated stored LLM credential(s): %s (active: %s)",
        ", ".join(activated),
        chosen,
    )
    return activated


async def ensure_stored_credentials_loaded(
    llm_service: LLMService,
    store: LLMCredentialStore,
) -> None:
    """Load stored credentials if this process has not managed to yet.

    Startup already tries. This is what makes a failed attempt recoverable
    instead of permanent.

    ``add_provider`` ends in ``provider.connect()`` — a network call. A worker
    that starts before egress is ready, or that hits a transient error, gets
    ``False`` back, logs it, and then never tries again: the node reports
    "unavailable" for a credential sitting valid in storage, and no amount of
    waiting fixes it. Only re-saving the key did, and only for the one worker
    that handled the request.

    Called from the request path, so the retry happens when something actually
    needs an LLM.

    The flag is set on success, or when there is nothing stored to load. It is
    deliberately *not* set on failure: that is the case worth retrying, and it
    is bounded by there being credentials to retry for.
    """
    if getattr(llm_service, "_stored_credentials_loaded", False):
        return

    # Already serving providers — from the environment, or from a startup load
    # that worked. Nothing to do, and no reason to ask storage.
    if llm_service._providers:
        llm_service._stored_credentials_loaded = True
        return

    try:
        stored = await store.list_status()
    except Exception as exc:  # noqa: BLE001 — a read failure is retryable
        logger.warning("Could not read stored LLM credentials: %s", exc)
        return

    if not stored:
        # No credentials is a settled answer, not a failure to retry.
        llm_service._stored_credentials_loaded = True
        return

    # `stored` is passed through rather than re-read: this function has already
    # paid for the listing, and reading storage twice per attempt is a cost the
    # retry path would repeat on every request while it keeps failing.
    activated = await activate_stored_credentials(llm_service, store, statuses=stored)
    if activated:
        llm_service._stored_credentials_loaded = True
        logger.info(
            "Recovered stored LLM credential(s) on demand after an earlier "
            "attempt found none: %s",
            ", ".join(activated),
        )
