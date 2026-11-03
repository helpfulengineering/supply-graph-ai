"""Create commands send the organisation to the API (#577)."""

import json

from click.testing import CliRunner

from src.cli.base import CLIConfig, CLIContext
from src.cli.okh import okh_group
from src.cli.okw import okw_group


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
        return {"success": True}


def test_okh_create_sends_the_organisation(tmp_path):
    path = tmp_path / "design.json"
    path.write_text(json.dumps({"title": "Widget"}))
    client = _Client()
    ctx = CLIContext(CLIConfig())
    ctx.api_client = client

    result = CliRunner().invoke(
        okh_group,
        ["create", str(path), "--on-behalf-of", "did:key:zOrg"],
        obj=ctx,
    )

    assert result.exit_code == 0, result.output
    assert client.seen["method"] == "POST"
    assert client.seen["path"] == "/api/okh/create"
    assert client.seen["params"] == {"on_behalf_of": "did:key:zOrg"}
    assert client.seen["json"] == {"content": {"title": "Widget"}}


def test_okw_create_sends_the_organisation(tmp_path):
    path = tmp_path / "shop.json"
    path.write_text(json.dumps({"name": "Open Shop"}))
    client = _Client()
    ctx = CLIContext(CLIConfig())
    ctx.api_client = client

    result = CliRunner().invoke(
        okw_group,
        ["create", str(path), "--on-behalf-of", "did:key:zOrg"],
        obj=ctx,
    )

    assert result.exit_code == 0, result.output
    assert client.seen["method"] == "POST"
    assert client.seen["path"] == "/api/okw/create"
    assert client.seen["params"] == {"on_behalf_of": "did:key:zOrg"}
    assert client.seen["json"] == {"content": {"name": "Open Shop"}}
