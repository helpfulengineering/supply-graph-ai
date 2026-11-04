"""The organisation admin affiliates from the command line (#578)."""

from click.testing import CliRunner

from src.cli.base import CLIConfig, CLIContext
from src.cli.identity import identity_group


def _invoke(monkeypatch, args, payload):
    seen = {}

    async def fake(cli_ctx, method, path, json=None):
        seen["method"] = method
        seen["path"] = path
        seen["json"] = json
        return payload

    monkeypatch.setattr("src.cli.identity._request", fake)
    result = CliRunner().invoke(identity_group, args, obj=CLIContext(CLIConfig()))
    return result, seen


def test_affiliate_add_sends_the_person_and_shows_expiry(monkeypatch):
    result, seen = _invoke(
        monkeypatch,
        ["affiliate", "add", "did:key:zAda", "--space", "did:key:zFab"],
        {
            "grant_id": "11111111-1111-4111-8111-111111111111",
            "expires_at": "2027-02-01T00:00:00Z",
        },
    )
    assert result.exit_code == 0, result.output
    assert seen == {
        "method": "POST",
        "path": "/affiliations",
        "json": {"space_did": "did:key:zFab", "subject_did": "did:key:zAda"},
    }
    assert "2027-02-01T00:00:00Z" in result.output


def test_affiliate_revoke_sends_the_grant(monkeypatch):
    result, seen = _invoke(
        monkeypatch,
        ["affiliate", "revoke", "11111111-1111-4111-8111-111111111111"],
        {"success": True, "message": "revoked"},
    )
    assert result.exit_code == 0, result.output
    assert seen["method"] == "DELETE"
    assert seen["path"] == "/affiliations/11111111-1111-4111-8111-111111111111"


def test_affiliate_renew_shows_the_new_expiry(monkeypatch):
    result, seen = _invoke(
        monkeypatch,
        ["affiliate", "renew", "11111111-1111-4111-8111-111111111111"],
        {
            "grant_id": "22222222-2222-4222-8222-222222222222",
            "expires_at": "2027-05-01T00:00:00Z",
        },
    )
    assert result.exit_code == 0, result.output
    assert seen["method"] == "POST"
    assert seen["path"] == "/affiliations/11111111-1111-4111-8111-111111111111/renew"
    assert "2027-05-01T00:00:00Z" in result.output
