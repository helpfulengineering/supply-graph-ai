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
