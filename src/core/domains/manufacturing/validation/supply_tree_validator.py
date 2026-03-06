"""
Supply tree validator for manufacturing domain.

This module provides a supply tree validator for the manufacturing domain.
"""

from typing import Any, Dict, Optional

from ....models.okh import OKHManifest
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

    # ------------------------------------------------------------------
    # OKH-aware supply tree validation (sync, for compatibility layer)
    # ------------------------------------------------------------------

    def validate_supply_tree(
        self, supply_tree: SupplyTree, okh_manifest: OKHManifest
    ) -> Dict[str, Any]:
        """
        Validate a supply tree against an OKH manifest (sync, legacy-style result).

        Checks that all process requirements extracted from the manifest are
        covered by the supply tree's declared capabilities, and returns a
        dict with ``valid``, ``issues``, ``warnings``, and ``confidence`` keys.
        """
        result: Dict[str, Any] = {
            "valid": True,
            "issues": [],
            "warnings": [],
            "confidence": 0.0,
        }

        # Basic structural checks
        if not supply_tree.facility_name:
            result["valid"] = False
            result["issues"].append("Supply tree missing facility_name")

        if not supply_tree.okh_reference:
            result["valid"] = False
            result["issues"].append("Supply tree missing okh_reference")

        if supply_tree.confidence_score < 0.0 or supply_tree.confidence_score > 1.0:
            result["valid"] = False
            result["issues"].append("confidence_score must be between 0.0 and 1.0")

        # Check process requirements against declared capabilities
        process_reqs = okh_manifest.extract_requirements()
        for req in process_reqs:
            if not self._is_requirement_satisfied(req, supply_tree):
                if getattr(req, "is_required", True):
                    result["valid"] = False
                    result["issues"].append(
                        f"Required process not satisfied: {req.process_name}"
                    )
                else:
                    result["warnings"].append(
                        f"Optional process not satisfied: {req.process_name}"
                    )

        result["confidence"] = self._calculate_confidence(supply_tree, okh_manifest)
        return result

    def _is_requirement_satisfied(
        self, requirement: Any, supply_tree: SupplyTree
    ) -> bool:
        """Return True if the process requirement is covered by the supply tree."""
        process_name = getattr(requirement, "process_name", "").lower()
        if not process_name:
            return False

        for capability in supply_tree.capabilities_used:
            if process_name in capability.lower():
                return True

        return False

    def _calculate_confidence(
        self, supply_tree: SupplyTree, okh_manifest: OKHManifest
    ) -> float:
        """
        Combine the supply tree's own confidence score with the ratio of
        satisfied OKH process requirements.

        Weights: 60 % requirement coverage, 40 % native confidence score.
        """
        process_reqs = okh_manifest.extract_requirements()
        if not process_reqs:
            return supply_tree.confidence_score

        satisfied = sum(
            1
            for req in process_reqs
            if self._is_requirement_satisfied(req, supply_tree)
        )
        requirement_coverage = satisfied / len(process_reqs)

        return 0.6 * requirement_coverage + 0.4 * supply_tree.confidence_score
