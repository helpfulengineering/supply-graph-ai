"""Identity API — the unified surface for API keys and accounts.

Backed by :class:`AuthenticationService` (parity service stem ``auth``) and
exposed under ``tags=["identity"]``. Management operations require the ``admin``
permission when the security policy enforces write auth (peacetime production);
in dev/test they are open, preserving existing flows. See
``notes/federated-identity-spec.md`` Slice 1.
"""

from typing import List, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Path, Query, status

from ...models.account import Account, AccountCreate
from ...models.attestation import Attestation, AttestationIssue, CertifyRequest
from ...models.auth import APIKeyCreate, APIKeyResponse, AuthenticatedUser
from ...models.binding import (
    DirectoryEntry,
    DirectoryPublishRequest,
    DomainBindRequest,
    DomainBindStartResponse,
    DomainVerifyRequest,
    IdentityBinding,
    OAuthBindRequest,
)
from ...models.capability import CapabilityGrant, GrantIssue
from ...models.identity import Identity, IdentityMint
from ...models.space import SpaceClaim, SpaceClaimRequest
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


# --- Self-sovereign identities (Slice 2) -------------------------------------


@router.post(
    "/identities",
    response_model=Identity,
    status_code=status.HTTP_201_CREATED,
    summary="Mint an identity",
)
async def mint_identity(
    payload: IdentityMint,
    _admin: object = Depends(require_admin),
    svc: AuthenticationService = Depends(get_auth_service),
) -> Identity:
    """Mint an Ed25519 ``did:key`` bound (custodially) to an account."""
    return await svc.create_identity(
        payload.account_id, payload.kind, payload.display_name
    )


@router.get("/identities/{did}", response_model=Identity, summary="Show an identity")
async def show_identity(
    did: str = Path(...),
    _admin: object = Depends(require_admin),
    svc: AuthenticationService = Depends(get_auth_service),
) -> Identity:
    identity = svc.get_identity(did)
    if not identity:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Identity not found"
        )
    return identity


@router.post(
    "/identities/{did}/rotate",
    response_model=Identity,
    summary="Rotate an identity's key",
)
async def rotate_identity(
    did: str = Path(...),
    _admin: object = Depends(require_admin),
    svc: AuthenticationService = Depends(get_auth_service),
) -> Identity:
    """Rotate to a fresh keypair, linking old -> new (signed by the old key)."""
    return await svc.rotate_identity(did)


# --- Capability grants (Slice 2) ---------------------------------------------


@router.post(
    "/grants",
    response_model=CapabilityGrant,
    status_code=status.HTTP_201_CREATED,
    summary="Issue a capability grant",
)
async def issue_grant(
    payload: GrantIssue,
    _admin: object = Depends(require_admin),
    svc: AuthenticationService = Depends(get_auth_service),
) -> CapabilityGrant:
    """Issue a signed grant. ``issuer_did`` defaults to the local node identity."""
    issuer_did = payload.issuer_did
    if not issuer_did:
        scope = svc.local_node_scope()
        if not scope:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="No local node identity to issue from; specify issuer_did",
            )
        issuer_did = scope.target
    return await svc.issue_grant(
        issuer_did=issuer_did,
        subject_did=payload.subject_did,
        permissions=payload.permissions,
        scope=payload.scope,
        ttl_days=payload.ttl_days,
        coarse_floor=payload.coarse_floor,
    )


@router.get("/grants", response_model=List[CapabilityGrant], summary="List grants")
async def list_grants(
    subject_did: str = Query(..., description="Subject DID to list grants for"),
    _admin: object = Depends(require_admin),
    svc: AuthenticationService = Depends(get_auth_service),
) -> List[CapabilityGrant]:
    return await svc.list_grants(subject_did)


@router.delete(
    "/grants/{grant_id}", response_model=SuccessResponse, summary="Revoke a grant"
)
async def revoke_grant(
    grant_id: UUID = Path(...),
    _admin: object = Depends(require_admin),
    svc: AuthenticationService = Depends(get_auth_service),
) -> SuccessResponse:
    await svc.revoke_grant(grant_id)
    return SuccessResponse(success=True, message=f"Grant {grant_id} revoked")


# --- Space claims + edge bootstrap (Slice 5) ---------------------------------


@router.post(
    "/spaces/claim",
    response_model=SpaceClaim,
    status_code=status.HTTP_201_CREATED,
    summary="Claim a space (TOFU admin bind)",
)
async def claim_space(
    payload: SpaceClaimRequest,
    _admin: object = Depends(require_admin),
    svc: AuthenticationService = Depends(get_auth_service),
) -> SpaceClaim:
    """Bind a PERSON DID as admin of a SPACE DID. First claimer wins."""
    return await svc.claim_space(payload.space_did, payload.admin_did)


@router.get(
    "/spaces/{space_did}/claim",
    response_model=SpaceClaim,
    summary="Show a space claim",
)
async def show_space_claim(
    space_did: str = Path(...),
    _admin: object = Depends(require_admin),
    svc: AuthenticationService = Depends(get_auth_service),
) -> SpaceClaim:
    claim = await svc.get_space_claim(space_did)
    if not claim:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Space claim not found"
        )
    return claim


@router.get("/spaces", response_model=List[SpaceClaim], summary="List space claims")
async def list_space_claims(
    _admin: object = Depends(require_admin),
    svc: AuthenticationService = Depends(get_auth_service),
) -> List[SpaceClaim]:
    return await svc.list_space_claims()


@router.post(
    "/grants/bootstrap-edge",
    response_model=CapabilityGrant,
    status_code=status.HTTP_201_CREATED,
    summary="Self-issue an edge genesis grant",
)
async def bootstrap_edge_grant(
    subject_did: str = Query(..., description="Subject DID (signs its own grant)"),
    _admin: object = Depends(require_admin),
    svc: AuthenticationService = Depends(get_auth_service),
) -> CapabilityGrant:
    """Isolated-edge bootstrap: subject self-issues write on the local node scope."""
    return await svc.bootstrap_edge_grant(subject_did)


# --- Attestations (Slice 6) --------------------------------------------------


@router.post(
    "/attestations",
    response_model=Attestation,
    status_code=status.HTTP_201_CREATED,
    summary="Issue an attestation",
)
async def issue_attestation(
    payload: AttestationIssue,
    _admin: object = Depends(require_admin),
    svc: AuthenticationService = Depends(get_auth_service),
) -> Attestation:
    """Issue a signed durable attestation. ``issuer_did`` defaults to the node."""
    return await svc.issue_attestation(
        type=payload.type,
        subject_did=payload.subject_did,
        issuer_did=payload.issuer_did,
        content_hash=payload.content_hash,
        claim=payload.claim,
        expires_at=payload.expires_at,
    )


@router.post(
    "/attestations/certify",
    response_model=Attestation,
    status_code=status.HTTP_201_CREATED,
    summary="Certify a release (bundle hash)",
)
async def certify(
    payload: CertifyRequest,
    _admin: object = Depends(require_admin),
    svc: AuthenticationService = Depends(get_auth_service),
) -> Attestation:
    """Bind firm DID → bundle hash → version as a ``certified`` attestation."""
    return await svc.certify(
        subject_did=payload.subject_did,
        bundle_hash=payload.bundle_hash,
        version=payload.version,
        issuer_did=payload.issuer_did,
        claim=payload.claim,
        manifest_content_hash=payload.manifest_content_hash,
    )


@router.get(
    "/attestations",
    response_model=List[Attestation],
    summary="List attestations",
)
async def list_attestations(
    subject_did: Optional[str] = Query(None, description="Filter by subject DID"),
    content_hash: Optional[str] = Query(None, description="Filter by content hash"),
    _admin: object = Depends(require_admin),
    svc: AuthenticationService = Depends(get_auth_service),
) -> List[Attestation]:
    return await svc.list_attestations(
        subject_did=subject_did, content_hash=content_hash
    )


@router.get(
    "/reputation/{subject_did}",
    response_model=List[Attestation],
    summary="Reputation attestations for a subject",
)
async def list_reputation(
    subject_did: str = Path(...),
    _admin: object = Depends(require_admin),
    svc: AuthenticationService = Depends(get_auth_service),
) -> List[Attestation]:
    """Known-type, signature-valid attestations about ``subject_did`` (no scoring)."""
    return await svc.list_reputation(subject_did)


# --- Bindings + directory (Slice 7) ------------------------------------------


@router.post(
    "/bindings/domain",
    response_model=DomainBindStartResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Start a domain binding",
)
async def start_domain_binding(
    payload: DomainBindRequest,
    _admin: object = Depends(require_admin),
    svc: AuthenticationService = Depends(get_auth_service),
) -> DomainBindStartResponse:
    """Issue a challenge and the ``.well-known/ohm-did.json`` document to host."""
    result = await svc.start_domain_binding(payload.subject_did, payload.domain)
    return DomainBindStartResponse(**result)


@router.post(
    "/bindings/domain/verify",
    response_model=IdentityBinding,
    summary="Verify a domain binding via .well-known",
)
async def verify_domain_binding(
    payload: DomainVerifyRequest,
    _admin: object = Depends(require_admin),
    svc: AuthenticationService = Depends(get_auth_service),
) -> IdentityBinding:
    """Fetch ``https://{domain}/.well-known/ohm-did.json`` and finalize the bind."""
    return await svc.verify_domain_binding(payload.subject_did, payload.domain)


@router.post(
    "/bindings/oauth",
    response_model=IdentityBinding,
    status_code=status.HTTP_201_CREATED,
    summary="Record an OAuth/OIDC binding",
)
async def bind_oauth(
    payload: OAuthBindRequest,
    _admin: object = Depends(require_admin),
    svc: AuthenticationService = Depends(get_auth_service),
) -> IdentityBinding:
    """Store an external IdP subject binding (redirect dance is out of band)."""
    return await svc.bind_oauth(
        subject_did=payload.subject_did,
        provider=payload.provider,
        external_subject=payload.external_subject,
        evidence=payload.evidence,
        verified=payload.verified,
    )


@router.get(
    "/bindings",
    response_model=List[IdentityBinding],
    summary="List identity bindings",
)
async def list_bindings(
    subject_did: Optional[str] = Query(None, description="Filter by subject DID"),
    _admin: object = Depends(require_admin),
    svc: AuthenticationService = Depends(get_auth_service),
) -> List[IdentityBinding]:
    return await svc.list_bindings(subject_did=subject_did)


@router.post(
    "/directory",
    response_model=DirectoryEntry,
    status_code=status.HTTP_201_CREATED,
    summary="Publish a trust-on-follow directory entry",
)
async def publish_directory_entry(
    payload: DirectoryPublishRequest,
    _admin: object = Depends(require_admin),
    svc: AuthenticationService = Depends(get_auth_service),
) -> DirectoryEntry:
    return await svc.publish_directory_entry(
        did=payload.did,
        display_name=payload.display_name,
        base_url=payload.base_url,
        domain=payload.domain,
    )


@router.get(
    "/directory",
    response_model=List[DirectoryEntry],
    summary="List the trust-on-follow directory",
)
async def list_directory(
    _admin: object = Depends(require_admin),
    svc: AuthenticationService = Depends(get_auth_service),
) -> List[DirectoryEntry]:
    """Peacetime registry posture: a local directory of known DIDs to follow."""
    return await svc.list_directory()
