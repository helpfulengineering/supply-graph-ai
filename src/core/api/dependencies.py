"""
FastAPI dependencies for authentication.

This module provides dependencies for authentication and authorization
in FastAPI routes.
"""

from typing import Optional

from fastapi import Depends, HTTPException, status
from fastapi.security import APIKeyHeader

from src.config import get_security_policy

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


def require_permission(permission: str):
    """Build a dependency that authorizes a mutating request, gated by policy.

    When ``SecurityPolicy.require_auth_for_writes`` is False (peacetime dev/test),
    the dependency is a no-op that still resolves an optional user for attribution
    when a valid key is supplied. When True (peacetime production), a valid key
    carrying ``permission`` is required — otherwise 401 (missing/invalid) or 403
    (insufficient permission).

    The resolved value is the authenticated user (or ``None`` when unenforced and
    anonymous) so callers can attribute the write to ``user.account_id``.
    """

    async def dependency(
        auth_header: Optional[str] = Depends(API_KEY_HEADER),
    ) -> Optional[AuthenticatedUser]:
        if not get_security_policy().require_auth_for_writes:
            if not auth_header:
                return None
            try:
                return await get_current_user(auth_header)
            except HTTPException:
                return None  # lenient when unenforced: never break existing dev flows

        user = await get_current_user(auth_header)
        auth_service = await AuthenticationService.get_instance()
        # Consult capability grants on the local node scope so a DID-backed user
        # can be authorized by a signed grant, not only by flat key permissions.
        scope = auth_service.local_node_scope()
        if not await auth_service.check_permission(user, [permission], scope=scope):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"This operation requires the '{permission}' permission",
            )
        return user

    return dependency


require_write = require_permission("write")
require_admin = require_permission("admin")


def created_by(user: Optional[AuthenticatedUser]) -> Optional[str]:
    """Attribution helper: the owning account id for a resolved user, else ``None``."""
    return str(user.account_id) if user else None


async def resolve_provenance(
    user: Optional[AuthenticatedUser],
    author: Optional[str] = None,
    on_behalf_of: Optional[str] = None,
):
    """Build record provenance for a write, signed by the node if a key is held.

    Defaults authorship + publication to the authenticated subject's DID; an
    explicit ``author`` (a ``did:...`` or a claimable external id like
    ``orcid:...``) overrides. Returns ``None`` when there is nothing to attribute
    (anonymous, DID-less write), so existing flows produce no provenance.
    """
    from ..models.provenance import Credit, RecordProvenance

    subject = user.subject_did if user else None
    credits = []
    if author:
        if author.startswith("did:"):
            credits.append(Credit(subject_did=author, role="author"))
        else:
            credits.append(Credit(external_id=author, role="author"))
    elif subject:
        credits.append(Credit(subject_did=subject, role="author"))

    if not credits and not subject and not on_behalf_of:
        return None

    provenance = RecordProvenance(
        authored_by=credits, published_by=subject, on_behalf_of=on_behalf_of
    )
    auth_service = await AuthenticationService.get_instance()
    return auth_service.sign_provenance_if_possible(provenance)
