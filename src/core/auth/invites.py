"""Invite links (#569).

Only the digest is persisted. The token is returned once, at mint time.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import datetime
from typing import Optional
from uuid import UUID

from src.core.storage.constants import AUTH_INVITE_INDEX_PREFIX, AUTH_INVITES_PREFIX


@dataclass
class Invite:
    invite_id: UUID
    token_digest: str
    expires_at: datetime
    use_limit: Optional[int] = None
    uses: int = 0
    revoked: bool = False


@dataclass
class MintedInvite:
    invite_id: UUID
    token: str
    expires_at: datetime
    use_limit: Optional[int] = None


def _record_key(invite_id: UUID) -> str:
    return f"{AUTH_INVITES_PREFIX}/{invite_id}.json"


def _index_key(digest: str) -> str:
    return f"{AUTH_INVITE_INDEX_PREFIX}/{digest}.json"


def _dump(invite: Invite) -> bytes:
    return json.dumps(
        {
            "invite_id": str(invite.invite_id),
            "token_digest": invite.token_digest,
            "expires_at": invite.expires_at.isoformat(),
            "use_limit": invite.use_limit,
            "uses": invite.uses,
            "revoked": invite.revoked,
        }
    ).encode("utf-8")


def _load(data: bytes) -> Invite:
    body = json.loads(data.decode("utf-8"))
    return Invite(
        invite_id=UUID(body["invite_id"]),
        token_digest=body["token_digest"],
        expires_at=datetime.fromisoformat(body["expires_at"]),
        use_limit=body.get("use_limit"),
        uses=body.get("uses", 0),
        revoked=body.get("revoked", False),
    )


async def save(manager, invite: Invite) -> None:
    await manager.put_object(
        key=_record_key(invite.invite_id),
        data=_dump(invite),
        content_type="application/json",
    )
    await manager.put_object(
        key=_index_key(invite.token_digest),
        data=json.dumps({"invite_id": str(invite.invite_id)}).encode("utf-8"),
        content_type="application/json",
    )


async def list_all(manager) -> list[Invite]:
    found: list[Invite] = []
    async for obj in manager.list_objects(prefix=f"{AUTH_INVITES_PREFIX}/"):
        data = obj.get("data")
        if data is None:
            data = await manager.get_object(obj["key"])
        found.append(_load(data))
    return found


async def load(manager, invite_id: UUID) -> Optional[Invite]:
    try:
        return _load(await manager.get_object(_record_key(invite_id)))
    except Exception:
        return None


async def find(manager, digest: str) -> Optional[Invite]:
    try:
        pointer = await manager.get_object(_index_key(digest))
        invite_id = UUID(json.loads(pointer.decode("utf-8"))["invite_id"])
        return _load(await manager.get_object(_record_key(invite_id)))
    except Exception:
        return None
