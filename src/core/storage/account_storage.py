"""Account storage layer.

Persists :class:`Account` objects as one JSON object per account under a shared
prefix, mirroring :class:`AuthStorage`.
"""

import asyncio
import json
import logging
from datetime import datetime
from typing import Dict, List, Optional
from uuid import UUID

from ..models.account import Account
from ..services.storage_service import StorageService
from .constants import (
    AUTH_ACCOUNTS_PREFIX,
    AUTH_RECOVERY_INDEX_PREFIX,
    AUTH_USERNAME_INDEX_PREFIX,
    STORAGE_OBJECT_TYPE_ACCOUNT,
)

logger = logging.getLogger(__name__)

# One lock per username, in this process. The object store has no
# create-if-absent, so two requests here cannot both claim the same name.
# Two replicas still can (#414).
_username_locks: Dict[str, asyncio.Lock] = {}
_username_locks_guard = asyncio.Lock()


class UsernameTaken(Exception):
    """The username already points at a different account."""


async def _username_lock(username: str) -> asyncio.Lock:
    async with _username_locks_guard:
        lock = _username_locks.get(username)
        if lock is None:
            lock = asyncio.Lock()
            _username_locks[username] = lock
        return lock


class AccountStorage:
    """Storage layer for account persistence."""

    def __init__(self, storage_service: StorageService):
        self.storage_service = storage_service
        self._storage_prefix = AUTH_ACCOUNTS_PREFIX

    @staticmethod
    def _recovery_index_key(digest: str) -> str:
        """Storage key for a recovery-digest pointer. The digest is hex."""
        return f"{AUTH_RECOVERY_INDEX_PREFIX}/{digest}.json"

    async def bind_recovery_digest(self, account: Account, digest: str) -> None:
        """Point ``digest`` at ``account`` and drop the pointer it replaces.

        The old pointer goes first: a crash between the two leaves a code that
        resolves to nothing, which fails closed. Doing it the other way round
        would leave a superseded code still resolving, which does not.
        """
        previous = account.recovery_digest
        if previous and previous != digest:
            try:
                await self.storage_service.manager.delete_object(
                    self._recovery_index_key(previous)
                )
            except Exception as exc:  # pragma: no cover - backend-specific
                logger.warning(f"Could not remove superseded recovery pointer: {exc}")
        account.recovery_digest = digest
        await self.save_account(account)
        await self.storage_service.manager.put_object(
            key=self._recovery_index_key(digest),
            data=json.dumps({"account_id": str(account.id)}).encode("utf-8"),
            content_type="application/json",
            metadata={"type": STORAGE_OBJECT_TYPE_ACCOUNT, "id": str(account.id)},
        )

    async def find_by_recovery_digest(self, digest: str) -> Optional[Account]:
        """Resolve a recovery digest to its account in constant work, or None.

        One point read then one load, rather than scanning every account — the
        same shape as API key lookup (#409), and for the same reason: an
        unknown code must not cost work proportional to the user count.
        """
        try:
            data = await self.storage_service.manager.get_object(
                self._recovery_index_key(digest)
            )
            account_id = json.loads(data.decode("utf-8"))["account_id"]
        except Exception:
            return None
        return await self.load_account(UUID(account_id))

    @staticmethod
    def _username_index_key(username: str) -> str:
        return f"{AUTH_USERNAME_INDEX_PREFIX}/{username}.json"

    async def find_by_username(self, username: str) -> Optional[Account]:
        """Resolve a username to its account, or None."""
        try:
            data = await self.storage_service.manager.get_object(
                self._username_index_key(username)
            )
            account_id = json.loads(data.decode("utf-8"))["account_id"]
        except Exception:
            return None
        return await self.load_account(UUID(account_id))

    async def claim_username(self, account: Account, username: str) -> None:
        """Point ``username`` at ``account``.

        Read, write, read back. A lost race leaves the other account's pointer
        in place and raises :class:`UsernameTaken`.
        """
        async with await _username_lock(username):
            existing = await self.find_by_username(username)
            if existing is not None and existing.id != account.id:
                raise UsernameTaken(username)
            account.username = username
            await self.save_account(account)
            await self.storage_service.manager.put_object(
                key=self._username_index_key(username),
                data=json.dumps({"account_id": str(account.id)}).encode("utf-8"),
                content_type="application/json",
                metadata={
                    "type": STORAGE_OBJECT_TYPE_ACCOUNT,
                    "id": str(account.id),
                },
            )
            again = await self.find_by_username(username)
            if again is None or again.id != account.id:
                raise UsernameTaken(username)

    async def save_account(self, account: Account) -> None:
        """Persist an account (create or update)."""
        account_data = account.model_dump(mode="json")
        # ``password_hash`` is excluded from serialisation so an API response
        # cannot include it. Storage is the one place it has to be written.
        account_data["password_hash"] = account.password_hash
        account_data["id"] = str(account.id)
        account_data["created_at"] = account.created_at.isoformat()

        data = json.dumps(account_data).encode("utf-8")
        await self.storage_service.manager.put_object(
            key=self._get_storage_key(account.id),
            data=data,
            content_type="application/json",
            metadata={
                "type": STORAGE_OBJECT_TYPE_ACCOUNT,
                "id": str(account.id),
                "kind": account.kind.value,
            },
        )

    async def load_account(self, account_id: UUID) -> Optional[Account]:
        """Load a single account, or ``None`` if absent/unreadable."""
        try:
            data = await self.storage_service.manager.get_object(
                self._get_storage_key(account_id)
            )
            return self._deserialize(json.loads(data.decode("utf-8")))
        except Exception as e:
            logger.debug(f"Failed to load account {account_id}: {e}")
            return None

    async def list_accounts(self) -> List[Account]:
        """List all accounts."""
        accounts: List[Account] = []
        prefix = f"{self._storage_prefix}/"
        try:
            async for obj in self.storage_service.manager.list_objects(prefix=prefix):
                data = obj.get("data") or await self.storage_service.manager.get_object(
                    obj["key"]
                )
                try:
                    accounts.append(self._deserialize(json.loads(data.decode("utf-8"))))
                except Exception as e:
                    logger.warning(
                        f"Failed to parse account from {obj.get('key', 'unknown')}: {e}"
                    )
        except Exception as e:
            logger.error(f"Failed to list accounts: {e}")
            raise
        return accounts

    @staticmethod
    def _deserialize(account_data: dict) -> Account:
        account_data["id"] = UUID(account_data["id"])
        if account_data.get("created_at"):
            account_data["created_at"] = datetime.fromisoformat(
                account_data["created_at"]
            )
        return Account(**account_data)

    def _get_storage_key(self, account_id: UUID) -> str:
        return f"{self._storage_prefix}/{account_id}.json"
