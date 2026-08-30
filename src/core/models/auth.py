"""
Authentication and authorization data models.

This module defines the data models for API key management,
authentication, and authorization.
"""

from datetime import datetime
from typing import List, Optional
from uuid import UUID

from pydantic import BaseModel, Field

from .account import ROOT_ACCOUNT_ID


class APIKey(BaseModel):
    """API Key model for storage"""

    key_id: UUID
    key_hash: str  # bcrypt hashed token
    # SHA-256 of the token, used only as a lookup key so authentication does not
    # have to scan (#409). Safe as a plain digest because the token is 256 bits
    # of CSPRNG output, not a password: there is no brute-force surface for a
    # stretching function to defend. ``None`` on keys issued before #409 — a
    # bcrypt hash cannot be reversed, so those can never gain one.
    token_digest: Optional[str] = None
    name: str
    description: Optional[str] = None
    permissions: List[str] = Field(default_factory=list)
    created_at: datetime
    last_used_at: Optional[datetime] = None
    expires_at: Optional[datetime] = None
    revoked: bool = False
    created_by: str = "system"


class APIKeyCreate(BaseModel):
    """Request model for creating API key"""

    name: str
    description: Optional[str] = None
    permissions: List[str] = Field(default_factory=lambda: ["read"])
    expires_at: Optional[datetime] = None
    account_id: Optional[UUID] = None  # owning account; defaults to the root account


class APIKeyResponse(BaseModel):
    """Response model for API key (without hash)"""

    key_id: UUID
    name: str
    description: Optional[str] = None
    permissions: List[str]
    created_at: datetime
    last_used_at: Optional[datetime] = None
    expires_at: Optional[datetime] = None
    revoked: bool = False
    token: Optional[str] = None  # Only returned on creation


class AuthenticatedUser(BaseModel):
    """Model representing the identity behind an authenticated request.

    Backed today by an API key; ``account_id`` is who writes are attributed to,
    and ``subject_did`` is a placeholder for the self-sovereign DID added in Slice 2.
    """

    key_id: UUID
    name: str
    permissions: List[str]
    account_id: UUID = ROOT_ACCOUNT_ID
    subject_did: Optional[str] = None


class RegistrationCreate(BaseModel):
    """Request payload for self-service registration."""

    display_name: str = Field(..., min_length=1, max_length=200)


class RegistrationResponse(BaseModel):
    """What a newly registered person needs to start using the node.

    Flat rather than nesting the full ``Identity``: a registrant needs their DID,
    not the rotation chain, and ``key.token`` is the only time the token exists.
    """

    account_id: UUID
    display_name: str
    did: str
    key: APIKeyResponse
    #: The way back in if the token is lost. Shown once, like the token, and
    #: stored only as a hash. Registration is the only place it is issued, and
    #: redeeming it issues a replacement.
    recovery_code: Optional[str] = None


class RecoveryRedeem(BaseModel):
    """Request payload for redeeming a recovery code."""

    code: str = Field(..., min_length=1, max_length=512)
