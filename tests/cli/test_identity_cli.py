"""CLI wiring tests for the identity group (Slice 1)."""

import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../../")))

from click.testing import CliRunner

from src.cli.base import CLIConfig, CLIContext
from src.cli.identity import identity_group


def test_registration_set_sends_the_operators_choice(monkeypatch):
    runner = CliRunner()
    seen = {}

    async def fake(cli_ctx, method, path, json=None):
        seen["method"] = method
        seen["path"] = path
        seen["json"] = json
        return {"registration": json["registration"]}

    monkeypatch.setattr("src.cli.identity._request", fake)
    result = runner.invoke(
        identity_group,
        ["registration", "--set", "closed"],
        obj=CLIContext(CLIConfig()),
    )
    assert result.exit_code == 0, result.output
    assert seen == {
        "method": "PUT",
        "path": "/registration",
        "json": {"registration": "closed"},
    }
    assert "closed" in result.output


def test_invite_mint_sends_the_expiry_and_use_limit(monkeypatch):
    runner = CliRunner()
    seen = {}

    async def fake(cli_ctx, method, path, json=None):
        seen["method"] = method
        seen["path"] = path
        seen["json"] = json
        return {
            "invite_id": "11111111-1111-4111-8111-111111111111",
            "token": "minted-token",
            "expires_at": "2026-12-01T00:00:00Z",
            "use_limit": 4,
        }

    monkeypatch.setattr("src.cli.identity._request", fake)
    result = runner.invoke(
        identity_group,
        ["invite", "mint", "--ttl-days", "7", "--use-limit", "4"],
        obj=CLIContext(CLIConfig()),
    )
    assert result.exit_code == 0, result.output
    assert seen == {
        "method": "POST",
        "path": "/invites",
        "json": {"ttl_days": 7, "use_limit": 4},
    }
    assert "minted-token" in result.output


def test_coordinate_sends_the_subject_and_shows_expiry(monkeypatch):
    runner = CliRunner()
    seen = {}

    async def fake(cli_ctx, method, path, json=None):
        seen["method"] = method
        seen["path"] = path
        seen["json"] = json
        return {
            "grant_id": "11111111-1111-4111-8111-111111111111",
            "expires_at": "2027-05-02T00:00:00Z",
            "permissions": ["coordinate"],
        }

    monkeypatch.setattr("src.cli.identity._request", fake)
    result = runner.invoke(
        identity_group,
        ["coordinate", "did:key:z6MkAda"],
        obj=CLIContext(CLIConfig()),
    )
    assert result.exit_code == 0, result.output
    assert seen == {
        "method": "POST",
        "path": "/coordinate",
        "json": {"subject_did": "did:key:z6MkAda"},
    }
    assert "2027-05-02T00:00:00Z" in result.output


def test_identity_group_exposes_subcommands():
    runner = CliRunner()
    result = runner.invoke(identity_group, ["--help"])
    assert result.exit_code == 0
    for cmd in (
        "whoami",
        "keys",
        "accounts",
        "identities",
        "grants",
        "spaces",
        "attestations",
        "reputation",
        "bindings",
        "directory",
        "security-policy",
        "registration",
        "invite",
    ):
        assert cmd in result.output


def test_spaces_subgroup_commands():
    runner = CliRunner()
    result = runner.invoke(identity_group, ["spaces", "--help"])
    assert result.exit_code == 0
    for cmd in ("claim", "show", "list"):
        assert cmd in result.output


def test_attestations_subgroup_commands():
    runner = CliRunner()
    result = runner.invoke(identity_group, ["attestations", "--help"])
    assert result.exit_code == 0
    for cmd in ("issue", "certify", "list"):
        assert cmd in result.output


def test_bindings_subgroup_commands():
    runner = CliRunner()
    result = runner.invoke(identity_group, ["bindings", "--help"])
    assert result.exit_code == 0
    for cmd in ("domain-start", "domain-verify", "oauth", "list"):
        assert cmd in result.output


def test_directory_subgroup_commands():
    runner = CliRunner()
    result = runner.invoke(identity_group, ["directory", "--help"])
    assert result.exit_code == 0
    for cmd in ("publish", "list"):
        assert cmd in result.output


def test_grants_bootstrap_edge_command():
    runner = CliRunner()
    result = runner.invoke(identity_group, ["grants", "--help"])
    assert result.exit_code == 0
    assert "bootstrap-edge" in result.output


def test_identities_subgroup_commands():
    runner = CliRunner()
    result = runner.invoke(identity_group, ["identities", "--help"])
    assert result.exit_code == 0
    for cmd in ("create", "show", "rotate"):
        assert cmd in result.output


def test_grants_subgroup_commands():
    runner = CliRunner()
    result = runner.invoke(identity_group, ["grants", "--help"])
    assert result.exit_code == 0
    for cmd in ("issue", "list", "revoke"):
        assert cmd in result.output


def test_keys_subgroup_commands():
    runner = CliRunner()
    result = runner.invoke(identity_group, ["keys", "--help"])
    assert result.exit_code == 0
    for cmd in ("create", "list", "revoke"):
        assert cmd in result.output


def test_accounts_subgroup_commands():
    runner = CliRunner()
    result = runner.invoke(identity_group, ["accounts", "--help"])
    assert result.exit_code == 0
    for cmd in ("create", "list", "disable"):
        assert cmd in result.output
