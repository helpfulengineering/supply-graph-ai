"""Attribute commands send the organisation to the API (#589)."""

from click.testing import CliRunner

from src.cli.base import CLIConfig, CLIContext
from src.cli.okh import okh_group
from src.cli.okw import okw_group

RECORD = "11111111-2222-4333-8444-555555555555"


class _Client:
    def __init__(self) -> None:
        self.seen: dict = {}

    async def request(self, method, endpoint, json_data=None, params=None):
        self.seen = {
            "method": method,
            "path": endpoint,
            "json": json_data,
            "params": params,
        }
        return {"on_behalf_of": (json_data or {}).get("on_behalf_of")}


def _invoke(group, args):
    client = _Client()
    ctx = CLIContext(CLIConfig())
    ctx.api_client = client
    result = CliRunner().invoke(group, args, obj=ctx)
    return result, client


def test_okh_attribute_sends_the_organisation():
    result, client = _invoke(
        okh_group, ["attribute", RECORD, "--on-behalf-of", "did:key:zOrg"]
    )
    assert result.exit_code == 0, result.output
    assert client.seen["method"] == "PUT"
    assert client.seen["path"] == f"/api/okh/{RECORD}/attribution"
    assert client.seen["json"] == {"on_behalf_of": "did:key:zOrg"}


def test_okh_attribute_clear_removes_the_organisation():
    result, client = _invoke(okh_group, ["attribute", RECORD, "--clear"])
    assert result.exit_code == 0, result.output
    assert client.seen["json"] == {"on_behalf_of": None}


def test_okw_attribute_sends_the_organisation():
    result, client = _invoke(
        okw_group, ["attribute", RECORD, "--on-behalf-of", "did:key:zOrg"]
    )
    assert result.exit_code == 0, result.output
    assert client.seen["method"] == "PUT"
    assert client.seen["path"] == f"/api/okw/{RECORD}/attribution"
    assert client.seen["json"] == {"on_behalf_of": "did:key:zOrg"}
