"""Match against this node's member facilities (#575).

A member facility is one whose creator is a person account on this node. A
synced facility carries its origin's account id, so attribution alone is not
enough: the account has to exist here.
"""

from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

import pytest

from src.core.models.account import Account, AccountKind
from src.core.services.auth_service import AuthenticationService
from src.core.services.okw_service import OKWService

pytestmark = pytest.mark.unit


@pytest.mark.asyncio
async def test_members_are_this_nodes_enabled_person_accounts():
    person = Account(display_name="Ada")
    disabled = Account(display_name="Gone", disabled=True)
    space = Account(display_name="Workshop", kind=AccountKind.SPACE)
    svc = AuthenticationService()
    svc._account_storage = MagicMock()
    svc._account_storage.list_accounts = AsyncMock(
        return_value=[person, disabled, space]
    )

    assert await svc.member_account_ids() == {str(person.id)}


def _space(source, facility_id=None):
    facility = MagicMock(name=facility_id or source)
    return {"id": facility_id or str(uuid4()), "source": source, "_facility": facility}


@pytest.mark.asyncio
async def test_the_member_filter_keeps_only_facilities_by_member_accounts():
    mine, synced, mom = _space("local"), _space("local"), _space("mom")
    svc = OKWService.__new__(OKWService)
    svc._load_network_candidates = AsyncMock(
        return_value=([mine, synced, mom], 0, True)
    )
    svc.inventory = AsyncMock(
        return_value=[
            {"id": mine["id"], "created_by_account": "member"},
            {"id": synced["id"], "created_by_account": "remote-node-account"},
        ]
    )

    kept = await svc.get_network_match_facilities(authors={"member"}, viewer=None)

    assert kept == [mine["_facility"]]


@pytest.mark.asyncio
async def test_without_the_member_filter_nothing_is_dropped_for_authorship():
    local, mom = _space("local"), _space("mom")
    svc = OKWService.__new__(OKWService)
    svc._load_network_candidates = AsyncMock(return_value=([local, mom], 0, True))
    svc.inventory = AsyncMock(side_effect=AssertionError("not needed"))

    kept = await svc.get_network_match_facilities(viewer=None)

    assert kept == [local["_facility"], mom["_facility"]]


def test_the_cli_asks_for_member_facilities_only():
    from src.cli.match import _network_filter

    assert _network_filter(False, None, None, members=True) == {
        "include_mom": False,
        "members_only": True,
    }


def test_the_cli_network_match_still_includes_maps_of_making():
    from src.cli.match import _network_filter

    assert _network_filter(True, "DE", None, members=False) == {
        "include_mom": True,
        "country": "DE",
    }
    assert _network_filter(False, None, None, members=False) is None
