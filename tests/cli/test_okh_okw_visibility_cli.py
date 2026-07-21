"""CLI wiring tests for okh/okw create + visibility (Slice 4)."""

import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../../")))

from click.testing import CliRunner

from src.cli.okh import okh_group
from src.cli.okw import okw_group


def test_okh_exposes_create_and_visibility():
    runner = CliRunner()
    result = runner.invoke(okh_group, ["--help"])
    assert result.exit_code == 0
    assert "create" in result.output
    assert "visibility" in result.output


def test_okh_create_has_author_flags():
    runner = CliRunner()
    result = runner.invoke(okh_group, ["create", "--help"])
    assert result.exit_code == 0
    assert "--author" in result.output
    assert "--on-behalf-of" in result.output


def test_okh_visibility_subgroup():
    runner = CliRunner()
    result = runner.invoke(okh_group, ["visibility", "--help"])
    assert result.exit_code == 0
    assert "show" in result.output
    assert "set" in result.output


def test_okw_exposes_create_and_visibility():
    runner = CliRunner()
    result = runner.invoke(okw_group, ["--help"])
    assert result.exit_code == 0
    assert "create" in result.output
    assert "visibility" in result.output


def test_okw_create_has_author_flags():
    runner = CliRunner()
    result = runner.invoke(okw_group, ["create", "--help"])
    assert result.exit_code == 0
    assert "--author" in result.output
    assert "--on-behalf-of" in result.output
