"""Account storage layer.

Persists :class:`Account` objects as one JSON object per account under a shared
prefix, mirroring :class:`AuthStorage`.
"""

import json
import logging
from datetime import datetime
from typing import List, Optional
from uuid import UUID

from ..models.account import Account
from ..services.storage_service import StorageService
from .constants import AUTH_ACCOUNTS_PREFIX, STORAGE_OBJECT_TYPE_ACCOUNT

logger = logging.getLogger(__name__)


class AccountStorage:
    """Storage layer for account persistence."""

    def __init__(self, storage_service: StorageService):
        self.storage_service = storage_service
        self._storage_prefix = AUTH_ACCOUNTS_PREFIX

    async def save_account(self, account: Account) -> None:
        """Persist an account (create or update)."""
        account_data = account.model_dump(mode="json")
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
