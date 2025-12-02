"""
Enhanced recipe validator for cooking domain.

This module provides an enhanced recipe validator that integrates with
the new validation framework.
"""

from typing import Dict, Any, Optional, List
from ....validation.engine import Validator
from ....validation.context import ValidationContext
from ....validation.result import ValidationResult, ValidationError, ValidationWarning
from ....validation.rules.cooking import CookingValidationRules
from ....models.supply_trees import SupplyTree
import re


class CookingRecipeValidator(Validator):
    """Enhanced recipe validator for cooking domain using new validation framework"""

    def __init__(self):
        self.validation_rules = CookingValidationRules()

    @property
    def validation_type(self) -> str:
        """Return the type of validation this validator performs"""
        return "recipe"

    @property
    def priority(self) -> int:
        """Return validation priority (higher = earlier)"""
        return 80  # Medium-high priority for recipe validation

    async def validate(
        self, data: Any, context: Optional[ValidationContext] = None
    ) -> ValidationResult:
        """Validate recipe data using domain-specific rules"""
        result = ValidationResult(valid=True)

        # Handle different data types
        if isinstance(data, dict):
            return await self._validate_recipe_dict(data, context)
        elif isinstance(data, SupplyTree):
            # Extract recipe data from supply tree
            recipe_data = self._extract_recipe_from_supply_tree(data)
            return await self._validate_recipe_dict(recipe_data, context)
        else:
            result.add_error(
                f"Unsupported data type for recipe validation: {type(data)}"
            )
            return result

    async def _validate_recipe_dict(
        self, recipe_data: Dict[str, Any], context: Optional[ValidationContext] = None
    ) -> ValidationResult:
        """Validate recipe dictionary using domain-specific rules"""
        result = ValidationResult(valid=True)

        # Get quality level from context or default to home
        quality_level = "home"
        if context:
            quality_level = context.quality_level

        # Validate quality level is supported
        if quality_level not in self.validation_rules.get_supported_quality_levels():
            result.add_error(f"Unsupported quality level: {quality_level}")
            return result

        # Get validation rules for this quality level
        rules = self.validation_rules.get_recipe_validation_rules(quality_level)

        # Validate required fields
        required_fields = rules.get("required_fields", [])
        missing_fields = self.validation_rules.get_missing_required_fields(
            recipe_data, quality_level
        )

        for field in missing_fields:
            result.add_error(
                f"Required field '{field}' is missing for {quality_level} quality level",
                field=field,
                code="required_field_missing",
            )

        # Validate field content based on quality level
        await self._validate_field_content(recipe_data, quality_level, result)

        # Validate ingredients
        await self._validate_ingredients(recipe_data, quality_level, result)

        # Validate instructions
        await self._validate_instructions(recipe_data, quality_level, result)

        # Validate cooking time and servings
        await self._validate_cooking_info(recipe_data, quality_level, result)

        # Validate nutritional information
        await self._validate_nutritional_info(recipe_data, quality_level, result)

        # Validate allergen information
        await self._validate_allergen_info(recipe_data, quality_level, result)

        # Validate food safety
        await self._validate_food_safety(recipe_data, quality_level, result)

        # Calculate recipe completeness score
        completeness_score = self._calculate_completeness(recipe_data, quality_level)
        result.metadata["completeness_score"] = completeness_score

        # Add warnings for missing optional fields
        await self._add_optional_field_warnings(recipe_data, quality_level, result)

        return result

    async def _validate_field_content(
        self, recipe_data: Dict[str, Any], quality_level: str, result: ValidationResult
    ):
        """Validate content of individual fields"""

        # Validate recipe name
        if "name" in recipe_data and recipe_data["name"]:
            name = recipe_data["name"]
            if len(name.strip()) < 3:
                result.add_warning(
                    "Recipe name is very short, consider providing a more descriptive name",
                    field="name",
                    code="name_too_short",
                )
            elif len(name.strip()) > 100:
                result.add_warning(
                    "Recipe name is very long, consider shortening it",
                    field="name",
                    code="name_too_long",
                )

        # Validate description
        if "description" in recipe_data and recipe_data["description"]:
            description = recipe_data["description"]
            if len(description.strip()) < 10:
                result.add_warning(
                    "Description is very brief, consider providing more detail",
                    field="description",
                    code="description_brief",
                )

    async def _validate_ingredients(
        self, recipe_data: Dict[str, Any], quality_level: str, result: ValidationResult
    ):
        """Validate ingredients"""

        if "ingredients" not in recipe_data or not recipe_data["ingredients"]:
            result.add_error(
                "Ingredients are required",
                field="ingredients",
                code="ingredients_required",
            )
            return

        ingredients = recipe_data["ingredients"]

        # Validate ingredients format
        if not isinstance(ingredients, list):
            result.add_error(
                "Ingredients must be a list",
                field="ingredients",
                code="ingredients_not_list",
            )
            return

        if len(ingredients) == 0:
            result.add_error(
                "At least one ingredient is required",
                field="ingredients",
                code="no_ingredients",
            )
            return

        # Validate each ingredient
        for i, ingredient in enumerate(ingredients):
            await self._validate_ingredient_item(ingredient, i, quality_level, result)

    async def _validate_ingredient_item(
        self, ingredient: Any, index: int, quality_level: str, result: ValidationResult
    ):
        """Validate individual ingredient item"""

        if isinstance(ingredient, str):
            # Simple string ingredient
            if len(ingredient.strip()) < 2:
                result.add_error(
                    f"Ingredient {index}: ingredient description is too short",
                    field=f"ingredients[{index}]",
                    code="ingredient_too_short",
                )
        elif isinstance(ingredient, dict):
            # Structured ingredient
            await self._validate_structured_ingredient(
                ingredient, index, quality_level, result
            )
        else:
            result.add_error(
                f"Ingredient {index}: invalid format, must be string or dict",
                field=f"ingredients[{index}]",
                code="ingredient_invalid_format",
            )

    async def _validate_structured_ingredient(
        self,
        ingredient: Dict[str, Any],
        index: int,
        quality_level: str,
        result: ValidationResult,
    ):
        """Validate structured ingredient"""

        # Check required fields
        if "name" not in ingredient or not ingredient["name"]:
            result.add_error(
                f"Ingredient {index}: name is required",
                field=f"ingredients[{index}].name",
                code="ingredient_name_required",
            )

        # Validate quantity
        if "quantity" in ingredient and ingredient["quantity"]:
            if not self._is_valid_quantity(ingredient["quantity"]):
                result.add_warning(
                    f"Ingredient {index}: quantity format may be invalid",
                    field=f"ingredients[{index}].quantity",
                    code="ingredient_quantity_invalid",
                )

        # Validate unit
        if "unit" in ingredient and ingredient["unit"]:
            if not self._is_valid_unit(ingredient["unit"]):
                result.add_warning(
                    f"Ingredient {index}: unit '{ingredient['unit']}' may not be standard",
                    field=f"ingredients[{index}].unit",
                    code="ingredient_unit_non_standard",
                )

        # Validate allergen information
        if "allergens" in ingredient and ingredient["allergens"]:
            if not self._is_valid_allergen_list(ingredient["allergens"]):
                result.add_warning(
                    f"Ingredient {index}: allergen information may be invalid",
                    field=f"ingredients[{index}].allergens",
                    code="ingredient_allergens_invalid",
                )

    async def _validate_instructions(
        self, recipe_data: Dict[str, Any], quality_level: str, result: ValidationResult
    ):
        """Validate cooking instructions"""

        if "instructions" not in recipe_data or not recipe_data["instructions"]:
            result.add_error(
                "Instructions are required",
                field="instructions",
                code="instructions_required",
            )
            return

        instructions = recipe_data["instructions"]

        # Validate instructions format
        if isinstance(instructions, str):
            if len(instructions.strip()) < 20:
                result.add_warning(
                    "Instructions are very brief, consider providing more detail",
                    field="instructions",
                    code="instructions_brief",
                )
        elif isinstance(instructions, list):
            if len(instructions) == 0:
                result.add_error(
                    "At least one instruction step is required",
                    field="instructions",
                    code="no_instruction_steps",
                )
                return

            # Validate each instruction step
            for i, step in enumerate(instructions):
                if isinstance(step, str):
                    if len(step.strip()) < 10:
                        result.add_warning(
                            f"Instruction step {i+1} is very brief",
                            field=f"instructions[{i}]",
                            code="instruction_step_brief",
                        )
                elif isinstance(step, dict):
                    await self._validate_instruction_step(
                        step, i, quality_level, result
                    )
        else:
            result.add_error(
                "Instructions must be a string or list",
                field="instructions",
                code="instructions_invalid_format",
            )

    async def _validate_instruction_step(
        self,
        step: Dict[str, Any],
        index: int,
        quality_level: str,
        result: ValidationResult,
    ):
        """Validate individual instruction step"""

        # Check required fields
        if "description" not in step or not step["description"]:
            result.add_error(
                f"Instruction step {index+1}: description is required",
                field=f"instructions[{index}].description",
                code="instruction_description_required",
            )

        # Validate timing
        if "time" in step and step["time"]:
            if not self._is_valid_time(step["time"]):
                result.add_warning(
                    f"Instruction step {index+1}: time format may be invalid",
                    field=f"instructions[{index}].time",
                    code="instruction_time_invalid",
                )

        # Validate temperature
        if "temperature" in step and step["temperature"]:
            if not self._is_valid_temperature(step["temperature"]):
                result.add_warning(
                    f"Instruction step {index+1}: temperature format may be invalid",
                    field=f"instructions[{index}].temperature",
                    code="instruction_temperature_invalid",
                )

    async def _validate_cooking_info(
        self, recipe_data: Dict[str, Any], quality_level: str, result: ValidationResult
    ):
        """Validate cooking time and servings information"""

        # Validate cooking time
        if "cooking_time" in recipe_data and recipe_data["cooking_time"]:
            if not self._is_valid_time(recipe_data["cooking_time"]):
                result.add_warning(
                    "Cooking time format may be invalid",
                    field="cooking_time",
                    code="cooking_time_invalid",
                )
        elif quality_level in ["commercial", "professional"]:
            result.add_warning(
                "Cooking time is recommended for commercial/professional quality levels",
                field="cooking_time",
                code="cooking_time_recommended",
            )

        # Validate servings
        if "servings" in recipe_data and recipe_data["servings"]:
            servings = recipe_data["servings"]
            if isinstance(servings, (int, float)):
                if servings <= 0:
                    result.add_error(
                        "Servings must be greater than 0",
                        field="servings",
                        code="servings_invalid",
                    )
                elif servings > 100:
                    result.add_warning(
                        "Servings seems unusually high",
                        field="servings",
                        code="servings_high",
                    )
            else:
                result.add_warning(
                    "Servings should be a number",
                    field="servings",
                    code="servings_not_number",
                )
        elif quality_level in ["commercial", "professional"]:
            result.add_warning(
                "Servings information is recommended for commercial/professional quality levels",
                field="servings",
                code="servings_recommended",
            )

    async def _validate_nutritional_info(
        self, recipe_data: Dict[str, Any], quality_level: str, result: ValidationResult
    ):
        """Validate nutritional information"""

        if "nutritional_info" not in recipe_data or not recipe_data["nutritional_info"]:
            if quality_level == "professional":
                result.add_warning(
                    "Nutritional information is recommended for professional quality level",
                    field="nutritional_info",
                    code="nutritional_info_recommended",
                )
            return

        nutritional_info = recipe_data["nutritional_info"]

        if not isinstance(nutritional_info, dict):
            result.add_warning(
                "Nutritional information should be a dictionary",
                field="nutritional_info",
                code="nutritional_info_not_dict",
            )
            return

        # Validate nutritional fields
        nutritional_fields = [
            "calories",
            "protein",
            "carbs",
            "fat",
            "fiber",
            "sugar",
            "sodium",
        ]
        for field in nutritional_fields:
            if field in nutritional_info:
                value = nutritional_info[field]
                if isinstance(value, (int, float)):
                    if value < 0:
                        result.add_warning(
                            f"Nutritional value for {field} cannot be negative",
                            field=f"nutritional_info.{field}",
                            code="nutritional_value_negative",
                        )
                else:
                    result.add_warning(
                        f"Nutritional value for {field} should be a number",
                        field=f"nutritional_info.{field}",
                        code="nutritional_value_not_number",
                    )

    async def _validate_allergen_info(
        self, recipe_data: Dict[str, Any], quality_level: str, result: ValidationResult
    ):
        """Validate allergen information"""

        if "allergen_info" not in recipe_data or not recipe_data["allergen_info"]:
            if quality_level in ["commercial", "professional"]:
                result.add_warning(
                    "Allergen information is recommended for commercial/professional quality levels",
                    field="allergen_info",
                    code="allergen_info_recommended",
                )
            return

        allergen_info = recipe_data["allergen_info"]

        if isinstance(allergen_info, list):
            if not self._is_valid_allergen_list(allergen_info):
                result.add_warning(
                    "Allergen list contains non-standard allergens",
                    field="allergen_info",
                    code="allergen_list_non_standard",
                )
        elif isinstance(allergen_info, str):
            if allergen_info.lower() not in ["none", "no allergens", "allergen-free"]:
                result.add_warning(
                    "Allergen information should be a list or 'none'",
                    field="allergen_info",
                    code="allergen_info_format",
                )
        else:
            result.add_warning(
                "Allergen information should be a list or string",
                field="allergen_info",
                code="allergen_info_invalid_format",
            )

    async def _validate_food_safety(
        self, recipe_data: Dict[str, Any], quality_level: str, result: ValidationResult
    ):
        """Validate food safety information"""

        if (
            "food_safety_notes" not in recipe_data
            or not recipe_data["food_safety_notes"]
        ):
            if quality_level == "professional":
                result.add_warning(
                    "Food safety notes are recommended for professional quality level",
                    field="food_safety_notes",
                    code="food_safety_notes_recommended",
                )
            return

        food_safety_notes = recipe_data["food_safety_notes"]

        if isinstance(food_safety_notes, str):
            if len(food_safety_notes.strip()) < 10:
                result.add_warning(
                    "Food safety notes are very brief, consider providing more detail",
                    field="food_safety_notes",
                    code="food_safety_notes_brief",
                )
        elif isinstance(food_safety_notes, list):
            if len(food_safety_notes) == 0:
                result.add_warning(
                    "Food safety notes list is empty",
                    field="food_safety_notes",
                    code="food_safety_notes_empty",
                )
        else:
            result.add_warning(
                "Food safety notes should be a string or list",
                field="food_safety_notes",
                code="food_safety_notes_invalid_format",
            )

    def _calculate_completeness(
        self, recipe_data: Dict[str, Any], quality_level: str
    ) -> float:
        """Calculate recipe completeness score (0.0-1.0)"""

        # Get validation rules for this quality level
        rules = self.validation_rules.get_recipe_validation_rules(quality_level)
        required_fields = rules.get("required_fields", [])
        optional_fields = rules.get("optional_fields", [])

        # Count present fields
        required_present = sum(
            1
            for field in required_fields
            if field in recipe_data and recipe_data[field] is not None
        )
        optional_present = sum(
            1
            for field in optional_fields
            if field in recipe_data and recipe_data[field] is not None
        )

        # Calculate score (required fields weighted more heavily)
        if not required_fields:
            return 0.0

        required_score = required_present / len(required_fields)
        optional_score = (
            optional_present / len(optional_fields) if optional_fields else 1.0
        )

        # Weight: 70% required fields, 30% optional fields
        return 0.7 * required_score + 0.3 * optional_score

    async def _add_optional_field_warnings(
        self, recipe_data: Dict[str, Any], quality_level: str, result: ValidationResult
    ):
        """Add warnings for missing optional fields"""

        rules = self.validation_rules.get_recipe_validation_rules(quality_level)
        optional_fields = rules.get("optional_fields", [])

        missing_optional = [
            field
            for field in optional_fields
            if field not in recipe_data or recipe_data[field] is None
        ]

        for field in missing_optional:
            result.add_warning(
                f"Optional field '{field}' is missing, consider adding for better documentation",
                field=field,
                code="optional_field_missing",
            )

    def _extract_recipe_from_supply_tree(
        self, supply_tree: SupplyTree
    ) -> Dict[str, Any]:
        """Extract recipe data from supply tree"""
        # This is a simplified extraction - in a real implementation,
        # this would parse the supply tree to extract recipe information

        recipe_data = {
            "name": "Extracted Recipe",
            "ingredients": [],
            "instructions": [],
        }

        # Extract ingredients from supply tree nodes
        for workflow in supply_tree.workflows.values():
            for node_id in workflow.graph.nodes:
                node = workflow.graph.nodes[node_id]["data"]
                if hasattr(node, "name") and "ingredient" in node.name.lower():
                    recipe_data["ingredients"].append(node.name)

        # Extract instructions from workflow steps
        for workflow in supply_tree.workflows.values():
            for node_id in workflow.graph.nodes:
                node = workflow.graph.nodes[node_id]["data"]
                if hasattr(node, "name") and "step" in node.name.lower():
                    recipe_data["instructions"].append(node.name)

        return recipe_data

    def _is_valid_quantity(self, quantity: Any) -> bool:
        """Check if quantity is valid"""
        if isinstance(quantity, (int, float)):
            return quantity > 0
        elif isinstance(quantity, str):
            # Check for common quantity patterns
            patterns = [
                r"^\d+(\.\d+)?$",  # Simple number
                r"^\d+(\.\d+)?\s*/\s*\d+$",  # Fraction
                r"^\d+(\.\d+)?\s*-\s*\d+(\.\d+)?$",  # Range
            ]
            return any(re.match(pattern, quantity.strip()) for pattern in patterns)
        return False

    def _is_valid_unit(self, unit: str) -> bool:
        """Check if unit is valid"""
        valid_units = [
            "cup",
            "cups",
            "tablespoon",
            "tablespoons",
            "tbsp",
            "teaspoon",
            "teaspoons",
            "tsp",
            "ounce",
            "ounces",
            "oz",
            "pound",
            "pounds",
            "lb",
            "lbs",
            "gram",
            "grams",
            "g",
            "kilogram",
            "kilograms",
            "kg",
            "liter",
            "liters",
            "l",
            "milliliter",
            "milliliters",
            "ml",
            "piece",
            "pieces",
            "slice",
            "slices",
            "clove",
            "cloves",
            "bunch",
            "bunches",
        ]
        return unit.lower() in valid_units

    def _is_valid_allergen_list(self, allergens: List[str]) -> bool:
        """Check if allergen list is valid"""
        common_allergens = [
            "milk",
            "eggs",
            "fish",
            "shellfish",
            "tree nuts",
            "peanuts",
            "wheat",
            "soybeans",
            "sesame",
            "mustard",
            "celery",
            "lupin",
            "sulphites",
        ]
        return all(allergen.lower() in common_allergens for allergen in allergens)

    def _is_valid_time(self, time: Any) -> bool:
        """Check if time format is valid"""
        if isinstance(time, (int, float)):
            return time > 0
        elif isinstance(time, str):
            # Check for common time patterns
            patterns = [
                r"^\d+\s*min(?:ute)?s?$",  # Minutes
                r"^\d+\s*h(?:our)?s?$",  # Hours
                r"^\d+\s*h(?:our)?s?\s*\d+\s*min(?:ute)?s?$",  # Hours and minutes
            ]
            return any(
                re.match(pattern, time.strip(), re.IGNORECASE) for pattern in patterns
            )
        return False

    def _is_valid_temperature(self, temperature: Any) -> bool:
        """Check if temperature format is valid"""
        if isinstance(temperature, (int, float)):
            return 0 <= temperature <= 1000  # Reasonable cooking temperature range
        elif isinstance(temperature, str):
            # Check for common temperature patterns
            patterns = [
                r"^\d+\s*°?[CF]$",  # Temperature with unit
                r"^\d+\s*degrees?\s*[CF]$",  # Temperature with "degrees"
            ]
            return any(
                re.match(pattern, temperature.strip(), re.IGNORECASE)
                for pattern in patterns
            )
        return False
