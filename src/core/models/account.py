"""Account model — the custodial unit of identity (person or space).

An ``Account`` is who a write is attributed to and what an API key belongs to.
In Slice 1 accounts are custodial (no keypair); Slice 2 binds them to a
self-sovereign ``did:key`` via ``subject_did``.
"""

from datetime import datetime
from enum import Enum
from uuid import UUID, uuid4

from pydantic import BaseModel, Field


class AccountKind(str, Enum):
    """Whether an account represents a human or an organizational space."""

    PERSON = "person"
    SPACE = "space"


# The synthetic account that env-configured API keys map to. Deployments that
# authenticate solely via API_KEYS get a stable, attributable owner instead of a
# blanket-admin dummy.
ROOT_ACCOUNT_ID = UUID("00000000-0000-0000-0000-000000000001")


class Account(BaseModel):
    """A custodial identity that owns API keys and authors records."""

    id: UUID = Field(default_factory=uuid4)
    display_name: str
    kind: AccountKind = AccountKind.PERSON
    created_at: datetime = Field(default_factory=datetime.utcnow)
    disabled: bool = False


class AccountCreate(BaseModel):
    """Request payload for creating an account."""

    display_name: str
    kind: AccountKind = AccountKind.PERSON
