"""CLI wiring tests for the identity group (Slice 1)."""

import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../../")))

from click.testing import CliRunner

from src.cli.identity import identity_group


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
