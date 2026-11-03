"""
FastAPI dependencies for authentication.

This module provides dependencies for authentication and authorization
in FastAPI routes.
"""

from typing import Any, Callable, Optional

from fastapi import Depends, HTTPException, Request, status
from fastapi.security import HTTPBearer

from src.config import get_security_policy

from ..auth.origin import assert_allowed_origin
from ..auth.sessions import UNSAFE_METHODS, read_session_cookie
from ..models.auth import AuthenticatedUser
from ..models.visibility import (
    DEV_LOCAL_ACCOUNT,
    BulkVisibilityResult,
    ViewerScope,
    VisibilityLevel,
    is_shareable,
    visible_to,
)
from ..services.auth_service import AuthenticationService


class _BearerHeader(HTTPBearer):
    """Declares `http` / `bearer` in the OpenAPI document; returns the raw header.

    The scheme used to be `APIKeyHeader(name="Authorization")`, which the document
    renders as `apiKey`. The server has always required `Authorization: Bearer
    <token>` and refuses anything else, so a generated client, or a person in
    Swagger UI, sent what the document said and was rejected.

    FastAPI reads the declared scheme from this object's `model`, and what a route
    receives from `__call__`. Overriding only the latter keeps the parsing — and
    the specific 401 messages for a missing, malformed or empty token — exactly
    where they are, in `get_current_user`, instead of letting `HTTPBearer`
    swallow a non-Bearer scheme into "missing".
    """

    async def __call__(self, request: Request) -> Optional[str]:  # type: ignore[override]
        return request.headers.get("Authorization") or None


API_KEY_HEADER = _BearerHeader(
    scheme_name="BearerAuth",
    description="An OHM API key, sent as `Authorization: Bearer <key>`.",
    auto_error=False,
)


def _presented(request: Request, auth_header: Optional[str]) -> bool:
    return bool(auth_header) or read_session_cookie(request.cookies) is not None


async def _user_from_bearer(auth_header: str) -> AuthenticatedUser:
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


async def get_current_user(
    request: Request,
    auth_header: Optional[str] = Depends(API_KEY_HEADER),
) -> AuthenticatedUser:
    """Resolve the caller from a Bearer token, or else from the session cookie.

    A Bearer header wins and the cookie is ignored, so a session pasted into
    ``Authorization`` is refused by key validation rather than accepted as a
    cookie. Cookie-authenticated unsafe methods run the CSRF check here, so a
    route cannot forget it.
    """
    if auth_header:
        return await _user_from_bearer(auth_header)

    token = read_session_cookie(request.cookies)
    if not token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=(
                "Missing authentication token. Expected "
                "'Authorization: Bearer <token>' header"
            ),
        )

    # Before the session lookup. Login, register and recover call the same
    # check with no session. The CSRF header is checked with the session.
    if request.method in UNSAFE_METHODS:
        assert_allowed_origin(request)

    auth_service = await AuthenticationService.get_instance()
    return await auth_service.authenticate_session(token, request)


async def get_optional_user(
    request: Request,
    auth_header: Optional[str] = Depends(API_KEY_HEADER),
) -> Optional[AuthenticatedUser]:
    """
    Optional authentication dependency for public endpoints.

    Returns None if no credential is presented. A presented credential that
    does not validate still raises, whether it arrived as a header or a cookie.
    """
    if not _presented(request, auth_header):
        return None

    return await get_current_user(request, auth_header)


async def get_viewer(
    request: Request,
    auth_header: Optional[str] = Depends(API_KEY_HEADER),
) -> Optional[AuthenticatedUser]:
    """Resolve the caller on a READ endpoint, without ever rejecting them.

    Reads decide *how much* to return rather than whether to answer: an
    unauthenticated caller gets the shareable subset, a recognised one gets
    everything. So an unusable credential means "treat as anonymous", not 401 —
    unlike :func:`get_optional_user`, which fails a supplied-but-invalid header.

    That distinction matters because these endpoints were previously open. A
    browser holding an expired key would otherwise stop being able to read
    public data at all, turning a stale token into a site-wide outage for that
    visitor.
    """
    if not _presented(request, auth_header):
        return None
    try:
        return await get_current_user(request, auth_header)
    except HTTPException:
        return None


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
        request: Request,
        auth_header: Optional[str] = Depends(API_KEY_HEADER),
    ) -> Optional[AuthenticatedUser]:
        if not get_security_policy().require_auth_for_writes:
            if not _presented(request, auth_header):
                return None
            try:
                return await get_current_user(request, auth_header)
            except HTTPException as exc:
                # A failed CSRF check is a refusal, even when writes are open.
                # A stale credential stays lenient, so dev flows keep working.
                if exc.status_code == status.HTTP_403_FORBIDDEN:
                    raise
                return None

        user = await get_current_user(request, auth_header)
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


def require_write_unless_public(is_public: Callable[[], bool]):
    """A write guard an operator can open to anonymous callers.

    Some writes are only nominally writes. Assembling an RFQ bundle creates a
    design package — which may already exist, and is cheap to rebuild from a
    manifest — so whether that needs a credential is a posture an operator
    should be able to choose, not a property of the route.

    ``is_public`` is read per request rather than captured, so the setting can
    move without a restart once it joins the runtime config plane.

    This composes ``require_write`` rather than reimplementing it: when the
    operator has not opened the route, the ordinary guard runs, including its
    own policy gating. When they have, the caller is still resolved so the work
    can be attributed — open does not mean anonymous, it means uncredentialed
    callers are also allowed.
    """

    async def dependency(
        request: Request,
        auth_header: Optional[str] = Depends(API_KEY_HEADER),
    ) -> Optional[AuthenticatedUser]:
        if is_public():
            return await get_optional_user(request, auth_header)
        return await require_write(request, auth_header)

    return dependency


async def require_coordinate(
    request: Request,
    auth_header: Optional[str] = Depends(API_KEY_HEADER),
) -> AuthenticatedUser:
    """Admin, or a node-scoped ``coordinate`` grant.

    An admin key passes because ``check_permission`` treats admin as every
    verb. A member does not, unless this node has granted them ``coordinate``.
    Strict, like :func:`require_admin_strict`: development does not relax it.
    """
    user = await get_current_user(request, auth_header)
    auth_service = await AuthenticationService.get_instance()
    scope = auth_service.local_node_scope()
    if not await auth_service.check_permission(user, ["coordinate"], scope=scope):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="This operation requires the 'coordinate' permission",
        )
    return user


async def require_admin_strict(
    request: Request,
    auth_header: Optional[str] = Depends(API_KEY_HEADER),
) -> AuthenticatedUser:
    """Always require a valid admin key — ignores SecurityPolicy write-auth relaxation.

    Use for operations that must never be anonymous even when
    ``ENVIRONMENT != production`` (e.g. LLM provider credential management).
    """
    user = await get_current_user(request, auth_header)
    auth_service = await AuthenticationService.get_instance()
    scope = auth_service.local_node_scope()
    if not await auth_service.check_permission(user, ["admin"], scope=scope):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="This operation requires the 'admin' permission",
        )
    return user


def created_by(user: Optional[AuthenticatedUser]) -> Optional[str]:
    """Attribution helper: the owning account id for a resolved user.

    Outside production an unresolved user is attributed to ``DEV_LOCAL_ACCOUNT``
    rather than to nobody, so that a record written without a key is readable
    back by the caller who wrote it — the two halves have to agree, or the
    record is orphaned on creation. See that constant for why this is an
    identity rather than a widened scope.
    """
    if user:
        return str(user.account_id)
    from src.config.schema import is_production_like
    from src.config.settings import ENVIRONMENT

    return None if is_production_like(ENVIRONMENT) else DEV_LOCAL_ACCOUNT


def created_by_did(user: Optional[AuthenticatedUser]) -> Optional[str]:
    """Attribution helper: the creator's subject DID, else ``None``.

    Stamped alongside the account id because record ownership keys on the DID
    (#403). ``None`` for env-configured keys, which carry no DID — those fall
    back to account attribution.
    """
    return user.subject_did if user else None


async def viewer_scope(user: Optional[AuthenticatedUser]) -> ViewerScope:
    """Which records ``user`` may see in a list (anonymous → shareable only)."""
    svc = await AuthenticationService.get_instance()
    return svc.viewer_scope(user)


async def can_read(
    service: Any, record_id: Any, user: Optional[AuthenticatedUser]
) -> bool:
    """Whether ``user`` may read ``record_id`` by id: the list rule (#606).

    ``service`` is the OKH or OKW service. Callers answer 404 on ``False``, not
    403, so the response does not confirm the id exists. Shareable records skip
    the attribution lookup, which is a storage scan.
    """
    level = await service.get_visibility(record_id)
    if is_shareable(level):
        return True
    did, account = await service.owner_attribution(str(record_id))
    return visible_to(level, await viewer_scope(user), did, account)


async def require_ownership(
    attribution: tuple[Optional[str], Optional[str]],
    user: Optional[AuthenticatedUser],
    noun: str,
) -> None:
    """Refuse unless ``user`` created the record ``attribution`` describes.

    Shared by OKH, asset, and OKW write-by-id routes (#514/#518), each
    resolving ``attribution`` from their own ``owner_attribution(id)``.
    ``require_write`` proves the caller holds *a* credential, not that they
    may touch *this* record — this decides the latter. 403, not 404: the
    caller already named this id, so there is nothing to hide; the honest
    answer is that they may not touch it. An unattributed record (no
    ``ohm_*`` stamp) refuses everyone, including its own creator, rather
    than treating "nobody" as "anybody." Admin gets no bypass — the same
    rule ``ViewerScope`` already applies to reads (ADR §9).
    """
    did, account = attribution
    if not (await viewer_scope(user)).owns(did, account):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"You do not have write access to this {noun}.",
        )


async def set_visibility_each(
    service: Any,
    ids: list[Any],
    level: VisibilityLevel,
    user: Optional[AuthenticatedUser],
) -> list[BulkVisibilityResult]:
    """Apply the single-record visibility rule to each id, reporting per id.

    ``not_found`` covers both a missing id and one ``user`` may not read, as
    ``can_read`` callers do; ``not_yours`` is the 403 of ``require_ownership``.
    """
    viewer = await viewer_scope(user)
    results = []
    for record_id in ids:
        if await service.get(record_id) is None or not await can_read(
            service, record_id, user
        ):
            results.append(BulkVisibilityResult(id=record_id, outcome="not_found"))
        elif not viewer.owns(*await service.owner_attribution(str(record_id))):
            results.append(BulkVisibilityResult(id=record_id, outcome="not_yours"))
        else:
            changed = await service.set_visibility(record_id, level)
            results.append(
                BulkVisibilityResult(
                    id=record_id, outcome="changed", visibility=changed
                )
            )
    return results


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
    claim = None
    grant = None
    if on_behalf_of and not subject:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=(
                "This node cannot publish for an organisation without a personal "
                "identity. Register one and ask the organisation's admin to "
                "affiliate you. An operator who is the admin can affiliate "
                "themselves. Attribution can be added later."
            ),
        )
    if on_behalf_of:
        auth_service = await AuthenticationService.get_instance()
        found = await auth_service.current_affiliation(subject, on_behalf_of)
        if found is None:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=(
                    "You are not yet affiliated with that organisation. Ask its "
                    "admin to affiliate you. Attribution can be added later."
                ),
            )
        claim, grant = found
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
        authored_by=credits,
        published_by=subject,
        on_behalf_of=on_behalf_of,
        space_claim=claim,
        affiliation=grant,
    )
    auth_service = await AuthenticationService.get_instance()
    return auth_service.sign_provenance_if_possible(provenance)
