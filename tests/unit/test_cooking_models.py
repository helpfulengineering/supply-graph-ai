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


def okh_recipe_dict(**overrides) -> dict:
    """An OKH-shaped manifest that is actually a recipe -- the format real
    recipe data is uploaded in (see docs-site/docs/guides/deploy-a-cooking-domain-instance.md).
    No `domain` field: this predates that tag, so the discriminator falls
    back to the manufacturing_processes cooking-verb signal."""
    data = {
        "id": str(uuid4()),
        "title": "Chocolate Chip Cookies",
        "version": "0.0.1",
        "license": {"documentation": "CC0-1.0"},
        "function": "cooking",
        "materials": [
            {"name": "flour"},
            {"material_type": "butter"},
            "chocolate chips",
        ],
        "tool_list": ["Oven", "Sheet Pan", {"name": "Spatula"}],
        "making_instructions": [{"title": "Mix and bake"}],
        "manufacturing_processes": ["bake"],
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


class TestRecipeFromOkhShape:
    """An OKH-shaped recipe (title/materials/tool_list/making_instructions)
    maps onto the same Recipe fields as the simple format, mirroring
    CookingExtractor._detailed_extract_requirements()."""

    def test_title_becomes_name(self):
        recipe = Recipe.from_dict(okh_recipe_dict())
        assert recipe.name == "Chocolate Chip Cookies"

    def test_materials_become_ingredients(self):
        recipe = Recipe.from_dict(okh_recipe_dict())
        assert recipe.ingredients == ["flour", "butter", "chocolate chips"]

    def test_tool_list_becomes_equipment(self):
        recipe = Recipe.from_dict(okh_recipe_dict())
        assert recipe.equipment == ["Oven", "Sheet Pan", "Spatula"]

    def test_making_instructions_become_instructions(self):
        recipe = Recipe.from_dict(okh_recipe_dict())
        assert recipe.instructions == ["Mix and bake"]

    def test_manufacturing_processes_fill_in_when_no_making_instructions(self):
        data = okh_recipe_dict(making_instructions=[])
        recipe = Recipe.from_dict(data)
        assert recipe.instructions == ["bake"]

    def test_requires_name_or_title(self):
        data = okh_recipe_dict()
        del data["title"]
        try:
            Recipe.from_dict(data)
            assert False, "expected ValueError"
        except ValueError:
            pass

    def test_bom_atoms_fill_in_ingredients_when_no_materials(self):
        # Some hand-authored recipe manifests bury the BOM under
        # metadata.original.bom_atoms instead of the standard `materials`
        # field.
        data = okh_recipe_dict(materials=[])
        data["metadata"] = {
            "original": {
                "bom_atoms": {
                    "flour": {"identifier": "Q779360"},
                    "butter": {"identifier": "Q83037"},
                }
            }
        }
        recipe = Recipe.from_dict(data)
        assert recipe.ingredients == ["flour", "butter"]


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

    def test_okh_shaped_recipe_with_cooking_process_is_a_recipe(self):
        # Real recipe data is uploaded as an OKH manifest whose
        # manufacturing_processes name a cooking technique (e.g. "bake").
        assert Recipe.is_cooking_recipe(okh_recipe_dict()) is True

    def test_okh_manifest_with_non_cooking_process_is_not_a_recipe(self):
        # Shape alone can't distinguish a recipe from a hardware design --
        # only a genuine hardware design's manufacturing_processes ("mill",
        # "drill") is what keeps it classified as an OKH manifest.
        data = okh_recipe_dict(manufacturing_processes=["mill", "drill"])
        assert Recipe.is_cooking_recipe(data) is False
