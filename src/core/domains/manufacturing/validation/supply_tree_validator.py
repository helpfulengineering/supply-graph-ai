"""
Supply tree validator for manufacturing domain.

This module provides a supply tree validator for the manufacturing domain.
"""

from typing import Any, Optional

from ....models.supply_trees import SupplyTree
from ....validation.context import ValidationContext
from ....validation.engine import Validator
from ....validation.result import ValidationResult
from ....validation.rules.manufacturing import ManufacturingValidationRules


class ManufacturingSupplyTreeValidator(Validator):
    """Supply tree validator for manufacturing domain using new validation framework"""

    def __init__(self):
        self.validation_rules = ManufacturingValidationRules()

    @property
    def validation_type(self) -> str:
        """Return the type of validation this validator performs"""
        return "supply_tree"

    @property
    def priority(self) -> int:
        """Return validation priority (higher = earlier)"""
        return 60  # Medium priority for supply tree validation

    async def validate(
        self, data: Any, context: Optional[ValidationContext] = None
    ) -> ValidationResult:
        """Validate supply tree data using domain-specific rules"""
        result = ValidationResult(valid=True)

        # Handle different data types
        if isinstance(data, SupplyTree):
            return await self._validate_supply_tree(data, context)
        elif isinstance(data, dict):
            # Try to create SupplyTree from dict
            try:
                supply_tree = SupplyTree.from_dict(data)
                return await self._validate_supply_tree(supply_tree, context)
            except Exception as e:
                result.add_error(f"Failed to parse supply tree: {str(e)}")
                return result
        else:
            result.add_error(
                f"Unsupported data type for supply tree validation: {type(data)}"
            )
            return result

    async def _validate_supply_tree(
        self, supply_tree: SupplyTree, context: Optional[ValidationContext] = None
    ) -> ValidationResult:
        """Validate supply tree using domain-specific rules"""
        result = ValidationResult(valid=True)

        # Get quality level from context or default to professional
        quality_level = "professional"
        if context:
            quality_level = context.quality_level

        # Validate quality level is supported
        if not ManufacturingValidationRules.validate_quality_level(quality_level):
            result.add_error(f"Unsupported quality level: {quality_level}")
            return result

        # Validate basic supply tree structure
        await self._validate_basic_structure(supply_tree, quality_level, result)

        return result

    async def _validate_basic_structure(
        self, supply_tree: SupplyTree, quality_level: str, result: ValidationResult
    ):
        """Validate basic simplified supply tree structure"""

        # Check required fields for simplified SupplyTree
        if not hasattr(supply_tree, "facility_id") or not supply_tree.facility_id:
            result.add_error(
                "Supply tree missing facility_id",
                field="facility_id",
                code="missing_facility_id",
            )

        if not hasattr(supply_tree, "facility_name") or not supply_tree.facility_name:
            result.add_error(
                "Supply tree missing facility_name",
                field="facility_name",
                code="missing_facility_name",
            )

        if not hasattr(supply_tree, "okh_reference") or not supply_tree.okh_reference:
            result.add_error(
                "Supply tree missing okh_reference",
                field="okh_reference",
                code="missing_okh_reference",
            )

        if not hasattr(supply_tree, "confidence_score"):
            result.add_error(
                "Supply tree missing confidence_score",
                field="confidence_score",
                code="missing_confidence_score",
            )
        elif supply_tree.confidence_score < 0.0 or supply_tree.confidence_score > 1.0:
            result.add_error(
                "Confidence score must be between 0.0 and 1.0",
                field="confidence_score",
                code="invalid_confidence_score",
            )
