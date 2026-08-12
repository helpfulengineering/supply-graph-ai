"""Recipe model: round-trip serialisation and the okh/recipe discriminator.

Mirrors KitchenCapability's test coverage (see the models themselves at
src/core/domains/cooking/models.py) — there was previously no test file for
either model.
"""

from __future__ import annotations

from uuid import uuid4

from src.core.domains.cooking.models import Recipe


def recipe_dict(**overrides) -> dict:
    data = {
        "id": str(uuid4()),
        "name": "Sourdough Bread",
        "ingredients": ["flour", "water", "salt", "starter"],
        "instructions": ["Mix", "Rest", "Bake"],
        "equipment": ["oven", "mixing bowl"],
    }
    data.update(overrides)
    return data


def okh_manifest_dict(**overrides) -> dict:
    data = {
        "id": str(uuid4()),
        "title": "Widget",
        "version": "1.0.0",
        "license": {"hardware": "MIT"},
        "function": "Does a thing",
    }
    data.update(overrides)
    return data


class TestRecipeRoundTrip:
    def test_from_dict_requires_id(self):
        data = recipe_dict()
        del data["id"]
        try:
            Recipe.from_dict(data)
            assert False, "expected ValueError"
        except ValueError:
            pass

    def test_from_dict_requires_name(self):
        data = recipe_dict()
        del data["name"]
        try:
            Recipe.from_dict(data)
            assert False, "expected ValueError"
        except ValueError:
            pass

    def test_to_dict_round_trips(self):
        data = recipe_dict()
        recipe = Recipe.from_dict(data)
        assert recipe.to_dict() == {**data, "domain": "cooking"}

    def test_defaults_domain_to_cooking(self):
        recipe = Recipe.from_dict(recipe_dict())
        assert recipe.domain == "cooking"


class TestRecipeDiscriminator:
    def test_recipe_shaped_data_is_a_recipe(self):
        assert Recipe.is_cooking_recipe(recipe_dict()) is True

    def test_okh_manifest_is_not_a_recipe(self):
        assert Recipe.is_cooking_recipe(okh_manifest_dict()) is False

    def test_explicit_domain_overrides_shape(self):
        # Recipe-shaped fields, but explicitly tagged manufacturing.
        data = recipe_dict(domain="manufacturing")
        assert Recipe.is_cooking_recipe(data) is False

        # OKH-shaped fields, but explicitly tagged cooking.
        data = okh_manifest_dict(domain="cooking")
        assert Recipe.is_cooking_recipe(data) is True

    def test_empty_data_is_not_a_recipe(self):
        assert Recipe.is_cooking_recipe({}) is False
