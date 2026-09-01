"""Encrypted LLM provider credential persistence.

Mirrors :class:`AuthStorage`: one JSON object per provider under a shared
prefix. Plaintext keys are encrypted with :class:`CredentialManager` before
write and decrypted only on load for hot-swap into ``LLMService``.
"""

from __future__ import annotations

import json
import logging
from typing import Any, Dict, List, Optional

from src.config.llm_config import CredentialManager, LLMProvider

from ..services.storage_service import StorageService
from .constants import LLM_CREDENTIALS_PREFIX, STORAGE_OBJECT_TYPE_LLM_CREDENTIAL

logger = logging.getLogger(__name__)


def mask_api_key(api_key: str) -> str:
    """Return a display form that never includes enough of the key to reuse it."""
    if len(api_key) <= 4:
        return "****"
    return f"****{api_key[-4:]}"


class LLMCredentialStore:
    """Persist encrypted LLM provider API keys."""

    def __init__(
        self,
        storage_service: StorageService,
        credential_manager: CredentialManager,
    ) -> None:
        self.storage_service = storage_service
        self.credential_manager = credential_manager
        self._storage_prefix = LLM_CREDENTIALS_PREFIX

    def _storage_key(self, provider: LLMProvider) -> str:
        return f"{self._storage_prefix}/{provider.value}.json"

    @property
    def _active_key(self) -> str:
        """Where the active provider is recorded.

        A separate object rather than a flag on each credential: with a flag,
        two payloads can both claim to be active and nothing decides between
        them. One object has one answer.
        """
        return f"{self._storage_prefix}/_active.json"

    async def set_active(self, provider: LLMProvider) -> None:
        """Record which stored provider a node should use.

        Durable on purpose. Activation used to live only in the process that
        received the request, so which provider was active depended on which
        worker answered — and after a restart, on nothing at all.
        """
        await self.storage_service.manager.put_object(
            key=self._active_key,
            data=json.dumps({"provider": provider.value}).encode("utf-8"),
            content_type="application/json",
        )
        logger.info("Active LLM provider set to %s", provider.value)

    async def get_active(self) -> Optional[LLMProvider]:
        """The recorded active provider, or None if none was ever chosen.

        None is a real answer, not an error: nodes that predate this, and nodes
        that have never had a credential, both legitimately have no record.
        """
        try:
            data = await self.storage_service.manager.get_object(self._active_key)
        except Exception:
            return None
        try:
            name = json.loads(data.decode("utf-8")).get("provider")
        except (UnicodeDecodeError, json.JSONDecodeError, AttributeError):
            logger.warning("Active LLM provider record is unreadable; ignoring it")
            return None
        try:
            return LLMProvider(name) if name else None
        except ValueError:
            logger.warning("Active LLM provider record names unknown %r", name)
            return None

    async def clear_active(self) -> None:
        """Forget the active provider, without touching any credential."""
        try:
            await self.storage_service.manager.delete_object(self._active_key)
        except Exception:
            pass

    async def save(
        self,
        provider: LLMProvider,
        api_key: str,
        *,
        model: Optional[str] = None,
        credential_type: str = "api_key",
    ) -> None:
        """Encrypt and persist a provider credential."""
        if self.credential_manager.uses_default_encryption:
            raise ValueError(
                "Refusing to store LLM credentials under default encryption keys. "
                "Set OHM_ENCRYPTION_KEY, or OHM_ENCRYPTION_SALT and "
                "OHM_ENCRYPTION_PASSWORD, to non-default values."
            )
        encrypted = self.credential_manager.encrypt_credential(api_key)
        payload = {
            "provider": provider.value,
            "credential_type": credential_type,
            "encrypted": encrypted,
            "masked_key": mask_api_key(api_key),
            "model": model,
        }
        await self.storage_service.manager.put_object(
            key=self._storage_key(provider),
            data=json.dumps(payload).encode("utf-8"),
            content_type="application/json",
            metadata={
                "type": STORAGE_OBJECT_TYPE_LLM_CREDENTIAL,
                "provider": provider.value,
            },
        )

    async def load(
        self,
        provider: LLMProvider,
        *,
        credential_type: str = "api_key",
    ) -> Optional[str]:
        """Return decrypted plaintext, or None if absent."""
        try:
            data = await self.storage_service.manager.get_object(
                self._storage_key(provider)
            )
        except Exception:
            return None
        try:
            payload = json.loads(data.decode("utf-8"))
        except (UnicodeDecodeError, json.JSONDecodeError):
            logger.warning("Unreadable LLM credential for %s", provider.value)
            return None
        if payload.get("credential_type", "api_key") != credential_type:
            return None
        encrypted = payload.get("encrypted")
        if not encrypted:
            return None
        return self.credential_manager.decrypt_credential(encrypted)

    async def delete(self, provider: LLMProvider) -> bool:
        """Remove a stored credential. Returns True if an object was deleted."""
        try:
            return bool(
                await self.storage_service.manager.delete_object(
                    self._storage_key(provider)
                )
            )
        except Exception:
            return False

    async def list_status(self) -> List[Dict[str, Any]]:
        """List stored credentials with masked keys only (never plaintext).

        Each row carries ``is_active``, so a reader can see which provider the
        node will actually use rather than inferring it from the order rows
        happen to come back in.
        """
        active = await self.get_active()
        statuses: List[Dict[str, Any]] = []
        async for obj in self.storage_service.manager.list_objects(
            prefix=self._storage_prefix
        ):
            raw = obj.get("data")
            if raw is None:
                try:
                    raw = await self.storage_service.manager.get_object(obj["key"])
                except Exception:
                    continue
            try:
                payload = json.loads(raw.decode("utf-8"))
            except (UnicodeDecodeError, json.JSONDecodeError, AttributeError):
                continue
            provider = payload.get("provider")
            masked = payload.get("masked_key")
            if not provider or not masked:
                continue
            statuses.append(
                {
                    "provider": provider,
                    "model": payload.get("model"),
                    "masked_key": masked,
                    "configured": True,
                    "is_active": active is not None and active.value == provider,
                }
            )
        return statuses
