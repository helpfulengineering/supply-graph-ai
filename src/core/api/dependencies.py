"""
FastAPI dependencies for authentication.

This module provides dependencies for authentication and authorization
in FastAPI routes.
"""

from typing import Optional

from fastapi import Depends, HTTPException, status
from fastapi.security import APIKeyHeader

from ..models.auth import AuthenticatedUser
from ..services.auth_service import AuthenticationService

# Define API key header dependency
API_KEY_HEADER = APIKeyHeader(name="Authorization", auto_error=False)


async def get_current_user(
    auth_header: Optional[str] = Depends(API_KEY_HEADER),
) -> AuthenticatedUser:
    """
    FastAPI dependency for authentication.

    Validates Authorization: Bearer <token> header and returns authenticated user.

    Args:
        auth_header: Authorization header value (from API_KEY_HEADER dependency)

    Returns:
        AuthenticatedUser if valid

    Raises:
        HTTPException 401 if invalid or missing
    """
    if not auth_header:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing authentication token. Expected 'Authorization: Bearer <token>' header",
        )

    if not auth_header.startswith("Bearer "):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authentication token format. Expected 'Bearer <token>'",
        )

    token = auth_header.replace("Bearer ", "").strip()

    if not token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Empty authentication token",
        )

    auth_service = await AuthenticationService.get_instance()
    return await auth_service.validate_api_key(token)


async def get_optional_user(
    auth_header: Optional[str] = Depends(API_KEY_HEADER),
) -> Optional[AuthenticatedUser]:
    """
    Optional authentication dependency for public endpoints.

    Returns None if no auth header, otherwise validates and returns user.
    If a header is provided but invalid, still raises HTTPException.

    Args:
        auth_header: Authorization header value (from API_KEY_HEADER dependency)

    Returns:
        AuthenticatedUser if valid header provided, None if no header

    Raises:
        HTTPException 401 if header is provided but invalid
    """
    if not auth_header:
        return None

    # If header is provided, validate it (will raise if invalid)
    return await get_current_user(auth_header)
