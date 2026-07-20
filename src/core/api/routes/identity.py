"""Identity API — the unified surface for API keys and accounts.

Backed by :class:`AuthenticationService` (parity service stem ``auth``) and
exposed under ``tags=["identity"]``. Management operations require the ``admin``
permission when the security policy enforces write auth (peacetime production);
in dev/test they are open, preserving existing flows. See
``notes/federated-identity-spec.md`` Slice 1.
"""

from typing import List
from uuid import UUID

from fastapi import APIRouter, Depends, Path, status

from ...models.account import Account, AccountCreate
from ...models.auth import APIKeyCreate, APIKeyResponse, AuthenticatedUser
from ...services.auth_service import AuthenticationService
from ..dependencies import get_current_user, require_admin
from ..models.base import SuccessResponse

router = APIRouter()


async def get_auth_service() -> AuthenticationService:
    return await AuthenticationService.get_instance()


@router.get("/whoami", response_model=AuthenticatedUser, summary="Current identity")
async def whoami(
    user: AuthenticatedUser = Depends(get_current_user),
) -> AuthenticatedUser:
    """Return the identity (key + account) behind the presented credential."""
    return user


@router.post(
    "/keys",
    response_model=APIKeyResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create an API key",
)
async def create_key(
    payload: APIKeyCreate,
    _admin: object = Depends(require_admin),
    svc: AuthenticationService = Depends(get_auth_service),
) -> APIKeyResponse:
    """Mint an API key. The plaintext token is returned only in this response."""
    return await svc.create_api_key(payload)


@router.get("/keys", response_model=List[APIKeyResponse], summary="List API keys")
async def list_keys(
    _admin: object = Depends(require_admin),
    svc: AuthenticationService = Depends(get_auth_service),
) -> List[APIKeyResponse]:
    """List API keys. Tokens are never returned here."""
    return await svc.list_api_keys()


@router.delete(
    "/keys/{key_id}", response_model=SuccessResponse, summary="Revoke an API key"
)
async def revoke_key(
    key_id: UUID = Path(...),
    _admin: object = Depends(require_admin),
    svc: AuthenticationService = Depends(get_auth_service),
) -> SuccessResponse:
    await svc.revoke_api_key(key_id)
    return SuccessResponse(success=True, message=f"API key {key_id} revoked")


@router.post(
    "/accounts",
    response_model=Account,
    status_code=status.HTTP_201_CREATED,
    summary="Create an account",
)
async def create_account(
    payload: AccountCreate,
    _admin: object = Depends(require_admin),
    svc: AuthenticationService = Depends(get_auth_service),
) -> Account:
    return await svc.create_account(payload)


@router.get("/accounts", response_model=List[Account], summary="List accounts")
async def list_accounts(
    _admin: object = Depends(require_admin),
    svc: AuthenticationService = Depends(get_auth_service),
) -> List[Account]:
    return await svc.list_accounts()


@router.post(
    "/accounts/{account_id}/disable",
    response_model=Account,
    summary="Disable an account",
)
async def disable_account(
    account_id: UUID = Path(...),
    _admin: object = Depends(require_admin),
    svc: AuthenticationService = Depends(get_auth_service),
) -> Account:
    return await svc.disable_account(account_id)
