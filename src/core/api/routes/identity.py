"""Identity API — the unified surface for API keys and accounts.

Backed by :class:`AuthenticationService` (parity service stem ``auth``) and
exposed under ``tags=["identity"]``. Management operations require the ``admin``
permission when the security policy enforces write auth (peacetime production);
in dev/test they are open, preserving existing flows. See
``notes/federated-identity-spec.md`` Slice 1.
"""

from typing import Any, Dict, List, Optional
from uuid import UUID

from fastapi import (
    APIRouter,
    Depends,
    HTTPException,
    Path,
    Query,
    Request,
    Response,
    status,
)

from src.config.security_policy import SecurityMode, get_security_policy

from ...models.account import Account, AccountCreate
from ...models.attestation import Attestation, AttestationIssue, CertifyRequest
from ...auth.origin import assert_allowed_origin, request_is_https
from ...auth.sessions import (
    apply_session_cookies,
    clear_session_cookies,
    read_session_cookie,
)
from ...models.auth import (
    APIKeyCreate,
    APIKeyResponse,
    AuthenticatedUser,
    LoginRequest,
    RecoveryRedeem,
    RegistrationCreate,
    RegistrationResponse,
)
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
from ...services.auth_service import (
    SELF_SERVICE_PERMISSIONS,
    AuthenticationService,
)
from ..dependencies import get_current_user, require_admin
from ..models.base import SuccessResponse
from ..models.identity.policy import SecurityPolicyResponse

router = APIRouter()


async def get_auth_service() -> AuthenticationService:
    return await AuthenticationService.get_instance()


@router.get("/whoami", response_model=AuthenticatedUser, summary="Current identity")
async def whoami(
    user: AuthenticatedUser = Depends(get_current_user),
) -> AuthenticatedUser:
    """Return the identity (key + account) behind the presented credential."""
    return user


@router.get(
    "/security-policy",
    response_model=SecurityPolicyResponse,
    summary="Active security mode policy",
)
async def show_security_policy() -> Dict[str, Any]:
    """Return the active ``SecurityPolicy`` knobs (deployment posture, not secret)."""
    return get_security_policy().to_public_dict()


@router.post(
    "/keys",
    response_model=APIKeyResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create an API key",
)
async def create_key(
    payload: APIKeyCreate,
    user: AuthenticatedUser = Depends(get_current_user),
    svc: AuthenticationService = Depends(get_auth_service),
) -> APIKeyResponse:
    """Mint an API key. The plaintext token is returned only in this response.

    Scoped rather than admin-only (#413): an ordinary person mints keys on
    their own account — a second one for the CLI, a replacement before revoking
    the old — and cannot mint for anyone else or above the self-service floor.
    An admin keeps both abilities.
    """
    if "admin" not in user.permissions:
        payload = payload.model_copy(
            update={
                "account_id": user.account_id,
                "permissions": [
                    p for p in payload.permissions if p in SELF_SERVICE_PERMISSIONS
                ]
                or list(SELF_SERVICE_PERMISSIONS),
            }
        )
    return await svc.create_api_key(payload)


@router.get("/keys", response_model=List[APIKeyResponse], summary="List API keys")
async def list_keys(
    user: AuthenticatedUser = Depends(get_current_user),
    svc: AuthenticationService = Depends(get_auth_service),
) -> List[APIKeyResponse]:
    """List API keys — your own, or all of them for an admin.

    Tokens are never returned here.
    """
    return await svc.list_api_keys_for(user)


@router.delete(
    "/keys/{key_id}", response_model=SuccessResponse, summary="Revoke an API key"
)
async def revoke_key(
    key_id: UUID = Path(...),
    user: AuthenticatedUser = Depends(get_current_user),
    svc: AuthenticationService = Depends(get_auth_service),
) -> SuccessResponse:
    """Revoke a key you own; an admin may revoke any."""
    await svc.revoke_api_key_for(user, key_id)
    return SuccessResponse(success=True, message=f"API key {key_id} revoked")


@router.post(
    "/keys/revoke-others",
    response_model=SuccessResponse,
    summary="Revoke every other key on your account",
)
async def revoke_other_keys(
    user: AuthenticatedUser = Depends(get_current_user),
    svc: AuthenticationService = Depends(get_auth_service),
) -> SuccessResponse:
    """Kill every key on your account except the one making this request.

    The panic case is "I pasted my key somewhere I should not have"; enumerating
    and revoking one at a time is the wrong thing to ask of someone in it.
    """
    revoked = await svc.revoke_other_keys(user)
    return SuccessResponse(
        success=True, message=f"Revoked {revoked} other key(s) on your account"
    )


@router.post(
    "/keys/{key_id}/renew",
    response_model=APIKeyResponse,
    summary="Extend a key's expiry",
)
async def renew_key(
    key_id: UUID = Path(...),
    user: AuthenticatedUser = Depends(get_current_user),
    svc: AuthenticationService = Depends(get_auth_service),
) -> APIKeyResponse:
    """Push the expiry out by the policy TTL, keeping the same token.

    So nothing has to be re-pasted wherever it is already stored.
    """
    return await svc.renew_api_key(user, key_id)


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


# --- Self-service onboarding (#403) ------------------------------------------


@router.post(
    "/register",
    response_model=RegistrationResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Register a person on this node",
)
async def register(
    payload: RegistrationCreate,
    request: Request,
    response: Response,
    svc: AuthenticationService = Depends(get_auth_service),
) -> RegistrationResponse:
    """Self-service onboarding — deliberately unauthenticated.

    A username and password sign the person in with a session cookie and
    return no API token (#570). Omitting both keeps the command-line
    registration, which still returns a token, for one release.

    Refused when the active mode closes registration; the issued credential
    never carries ``admin``.
    """
    assert_allowed_origin(request)
    if payload.username is not None or payload.password is not None:
        if not payload.username or not payload.password:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="Username and password are both required.",
            )
        body, token, csrf = await svc.register_member(
            payload.username,
            payload.password,
            payload.display_name,
            https=request_is_https(request),
        )
        _set_session(request, response, token, csrf)
        return body
    return await svc.register(payload.display_name)


@router.post("/login", response_model=AuthenticatedUser, summary="Sign in")
async def login(
    payload: LoginRequest,
    request: Request,
    response: Response,
    svc: AuthenticationService = Depends(get_auth_service),
) -> AuthenticatedUser:
    """Sign in with a username and password. Sets the session cookies.

    Deliberately unauthenticated. The failure message does not say which of
    the two was wrong.
    """
    assert_allowed_origin(request)
    user, token, csrf = await svc.login(
        payload.username,
        payload.password,
        https=request_is_https(request),
    )
    _set_session(request, response, token, csrf)
    return user


@router.post("/logout", status_code=status.HTTP_204_NO_CONTENT, summary="Sign out")
async def logout(
    request: Request,
    svc: AuthenticationService = Depends(get_auth_service),
    _user: AuthenticatedUser = Depends(get_current_user),
) -> Response:
    """End the browser session and clear its cookies."""
    token = read_session_cookie(request.cookies)
    if token:
        await svc.revoke_session_token(token)
    response = Response(status_code=status.HTTP_204_NO_CONTENT)
    clear_session_cookies(response)
    return response


def _set_session(request: Request, response: Response, token: str, csrf: str) -> None:
    https = request_is_https(request)
    apply_session_cookies(
        response,
        token=token,
        csrf=csrf,
        https=https,
        shielded=get_security_policy().mode == SecurityMode.SHIELDED,
    )


@router.post(
    "/recover",
    response_model=RegistrationResponse,
    summary="Redeem a recovery code",
)
async def recover(
    payload: RecoveryRedeem,
    request: Request,
    response: Response,
    svc: AuthenticationService = Depends(get_auth_service),
) -> RegistrationResponse:
    """Trade a recovery code for a way back in — deliberately unauthenticated.

    A password sets a new one and signs this browser in (#571). Omitting it
    keeps the command-line recovery, which still returns a token, for one
    release. Either way the account's existing keys and sessions are revoked
    and a replacement code is issued.
    """
    assert_allowed_origin(request)
    if payload.password is not None:
        body, token, csrf = await svc.recover_password(
            payload.code,
            payload.password,
            https=request_is_https(request),
        )
        _set_session(request, response, token, csrf)
        return body
    return await svc.redeem_recovery_code(payload.code)


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
    user: AuthenticatedUser = Depends(get_current_user),
    svc: AuthenticationService = Depends(get_auth_service),
) -> List[Attestation]:
    """Attestations about you, or all of them for an admin.

    Scoped rather than admin-only (#406): break-glass records an
    ``admin_access`` attestation whose subject is the record's owner, and an
    accounting the subject cannot read is not an accounting.
    """
    return await svc.list_attestations_for(
        user, subject_did=subject_did, content_hash=content_hash
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
