"""CLI wiring + behavior tests for `ohm okh list-recipes` / `ohm okw list-kitchens`."""

from __future__ import annotations

import json
import os
import sys
from unittest.mock import AsyncMock, patch
from uuid import uuid4

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../../")))

from click.testing import CliRunner

from src.cli.okh import okh_group
from src.cli.okw import okw_group
from src.core.domains.cooking.models import KitchenCapability, Recipe


def test_okh_exposes_list_recipes():
    runner = CliRunner()
    result = runner.invoke(okh_group, ["--help"])
    assert result.exit_code == 0
    assert "list-recipes" in result.output


def test_okw_exposes_list_kitchens():
    runner = CliRunner()
    result = runner.invoke(okw_group, ["--help"])
    assert result.exit_code == 0
    assert "list-kitchens" in result.output


def _recipe() -> Recipe:
    return Recipe.from_dict(
        {
            "id": str(uuid4()),
            "name": "Sourdough Bread",
            "ingredients": ["flour", "water", "salt"],
            "instructions": ["Mix", "Bake"],
            "equipment": ["oven"],
        }
    )


def _kitchen() -> KitchenCapability:
    return KitchenCapability.from_dict(
        {
            "id": str(uuid4()),
            "name": "Test Kitchen",
            "appliances": ["oven"],
            "tools": ["knife"],
            "ingredients": [],
        }
    )


class DummyCLIContext:
    """Minimal stand-in for CLIContext, matching test_scaffold_cleanup_cli.py."""

    def __init__(self):
        self.output_format = "text"
        self.verbose = False

    def start_command_tracking(self, *_args, **_kwargs):
        pass

    def end_command_tracking(self):
        pass

    def log(self, *_args, **_kwargs):
        pass


def test_list_recipes_falls_back_to_direct_service_and_prints_json():
    """No server reachable in tests, so this exercises the fallback listing path."""
    runner = CliRunner()
    svc = AsyncMock()
    svc.list_recipes = AsyncMock(return_value=[_recipe()])

    async def run_fallback(_self, _http_op, fallback_op):
        return await fallback_op()

    with (
        patch("src.cli.okh.OKHService.get_instance", AsyncMock(return_value=svc)),
        patch("src.cli.okh.SmartCommand.execute_with_fallback", run_fallback),
    ):
        result = runner.invoke(
            okh_group, ["list-recipes", "--json"], obj=DummyCLIContext()
        )

    assert result.exit_code == 0, result.output
    body = json.loads(result.output)
    assert body["total"] == 1
    assert body["recipes"][0]["name"] == "Sourdough Bread"


def test_list_kitchens_falls_back_to_direct_service_and_prints_json():
    runner = CliRunner()
    svc = AsyncMock()
    svc.list_kitchens = AsyncMock(return_value=[_kitchen()])

    async def run_fallback(_self, _http_op, fallback_op):
        return await fallback_op()

    with (
        patch("src.cli.okw.OKWService.get_instance", AsyncMock(return_value=svc)),
        patch("src.cli.okw.SmartCommand.execute_with_fallback", run_fallback),
    ):
        result = runner.invoke(
            okw_group, ["list-kitchens", "--json"], obj=DummyCLIContext()
        )

    assert result.exit_code == 0, result.output
    body = json.loads(result.output)
    assert body["total"] == 1
    assert body["kitchens"][0]["name"] == "Test Kitchen"
