"""
Authentication and authorization data models.

This module defines the data models for API key management,
authentication, and authorization.
"""

from datetime import datetime
from typing import List, Optional
from uuid import UUID

from pydantic import BaseModel, Field


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
    """Model representing authenticated user/API key"""

    key_id: UUID
    name: str
    permissions: List[str]
