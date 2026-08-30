"""Record ownership is scoped per viewer, and keys on the subject DID (#403).

Before this, list endpoints applied the shareable filter only for anonymous
callers and applied no ownership filter at all for authenticated ones. That was
harmless while "any authenticated user" meant the node operator; open
registration makes it a disclosure bug, so the two ship together.

The rule under test is three-way: anonymous sees shareable, a user sees
shareable plus their own, and an **admin sees exactly what any other user sees**
— operators enumerate through the inventory surface instead (ADR §9).
"""

from unittest.mock import AsyncMock
from uuid import UUID, uuid4

import pytest

from src.core.federation.identity import generate_identity
from src.core.models.auth import AuthenticatedUser
from src.core.models.provenance import OHM_CREATED_BY_DID_KEY, OHM_CREATED_BY_KEY
from src.core.models.visibility import (
    ANONYMOUS_SCOPE,
    ViewerScope,
    VisibilityLevel,
    visible_to,
)
from src.core.services.auth_service import AuthenticationService
from src.core.services.okh_service import OKHService
from src.core.storage.identity_key_store import IdentityKeyStore

ADA_DID = "did:key:zAda"
BOB_DID = "did:key:zBob"
ADA_ACCOUNT = "11111111-1111-4111-8111-111111111111"
BOB_ACCOUNT = "22222222-2222-4222-8222-222222222222"

ADA = ViewerScope(account_id=ADA_ACCOUNT, dids=frozenset({ADA_DID}))
BOB = ViewerScope(account_id=BOB_ACCOUNT, dids=frozenset({BOB_DID}))


def _entry(record_id: str, did=None, account=None) -> dict:
    manifest = {"id": record_id, "title": "T"}
    if did:
        manifest[OHM_CREATED_BY_DID_KEY] = did
    if account:
        manifest[OHM_CREATED_BY_KEY] = account
    return {"manifest": manifest}


@pytest.mark.parametrize(
    "level,scope,expected",
    [
        (VisibilityLevel.PUBLIC, ANONYMOUS_SCOPE, True),
        (VisibilityLevel.FOLLOWERS, ANONYMOUS_SCOPE, True),
        (VisibilityLevel.PRIVATE, ANONYMOUS_SCOPE, False),
        (VisibilityLevel.PRIVATE, ADA, True),
        (VisibilityLevel.PRIVATE, BOB, False),
    ],
)
def test_visibility_decision_matrix(level, scope, expected):
    assert visible_to(level, scope, ADA_DID, ADA_ACCOUNT) is expected


def test_account_fallback_covers_records_and_keys_that_have_no_did():
    """Env keys carry no DID, and pre-#403 records carry only account attribution."""
    assert visible_to(VisibilityLevel.PRIVATE, ADA, None, ADA_ACCOUNT) is True
    assert visible_to(VisibilityLevel.PRIVATE, BOB, None, ADA_ACCOUNT) is False


def test_a_record_with_no_attribution_at_all_is_owned_by_nobody():
    assert visible_to(VisibilityLevel.PRIVATE, ADA, None, None) is False


@pytest.mark.asyncio
async def test_visible_entries_filters_on_raw_catalogue_dicts():
    """The check must run before from_dict, which drops the ohm_* attribution."""
    mine = str(uuid4())
    theirs = str(uuid4())
    shared = str(uuid4())

    svc = OKHService()
    svc.get_visibility = AsyncMock(
        side_effect=lambda rid: (
            VisibilityLevel.PUBLIC if rid == shared else VisibilityLevel.PRIVATE
        )
    )
    entries = [
        _entry(mine, did=ADA_DID),
        _entry(theirs, did=BOB_DID),
        _entry(shared, did=BOB_DID),
    ]

    kept = await svc._visible_entries(entries, ADA)
    assert [e["manifest"]["id"] for e in kept] == [mine, shared]

    kept_anon = await svc._visible_entries(entries, ANONYMOUS_SCOPE)
    assert [e["manifest"]["id"] for e in kept_anon] == [shared]


def _service_with_identities(tmp_path) -> AuthenticationService:
    svc = AuthenticationService()
    svc._identity_store = IdentityKeyStore(tmp_path)
    svc._initialized = True
    return svc


def _user(account_id: str, did, permissions) -> AuthenticatedUser:
    return AuthenticatedUser(
        key_id=uuid4(),
        name="k",
        permissions=permissions,
        account_id=UUID(account_id),
        subject_did=did,
    )


def test_admin_scope_is_identical_to_an_ordinary_users(tmp_path):
    """`admin` must buy nothing here — that is the whole boundary (ADR §9)."""
    svc = _service_with_identities(tmp_path)

    ordinary = svc.viewer_scope(_user(ADA_ACCOUNT, ADA_DID, ["read", "write"]))
    admin = svc.viewer_scope(_user(ADA_ACCOUNT, ADA_DID, ["read", "write", "admin"]))

    assert admin == ordinary
    assert visible_to(VisibilityLevel.PRIVATE, admin, BOB_DID, BOB_ACCOUNT) is False


def test_anonymous_user_resolves_to_the_empty_scope(tmp_path):
    assert _service_with_identities(tmp_path).viewer_scope(None) == ANONYMOUS_SCOPE


@pytest.mark.asyncio
async def test_rotation_does_not_hide_your_own_records_from_you(tmp_path):
    """A rotated key must still own what the superseded key created."""
    svc = _service_with_identities(tmp_path)
    account = uuid4()
    original = await svc.create_identity(account, display_name="Ada")
    rotated = await svc.rotate_identity(original.did)
    assert rotated.did != original.did

    scope = svc.viewer_scope(_user(str(account), rotated.did, ["read", "write"]))

    # The record was stamped with the DID that has since been rotated away.
    assert visible_to(VisibilityLevel.PRIVATE, scope, original.did, None) is True
    assert visible_to(VisibilityLevel.PRIVATE, scope, rotated.did, None) is True
    assert visible_to(VisibilityLevel.PRIVATE, scope, BOB_DID, None) is False


def test_env_key_without_a_did_still_owns_what_it_created(tmp_path):
    """Env-configured keys carry no subject DID; account attribution is the fallback."""
    svc = _service_with_identities(tmp_path)
    scope = svc.viewer_scope(_user(ADA_ACCOUNT, None, ["read", "write", "admin"]))

    assert scope.dids == frozenset()
    assert visible_to(VisibilityLevel.PRIVATE, scope, None, ADA_ACCOUNT) is True
    assert visible_to(VisibilityLevel.PRIVATE, scope, None, BOB_ACCOUNT) is False
