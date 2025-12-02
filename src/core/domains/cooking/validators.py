"""
Temporary cooking validators for backward compatibility.

This file provides temporary validators that maintain the same interface
as the original validators while the new validation framework is being integrated.
"""

from typing import Dict, Any
from ...models.supply_trees import SupplyTree


class CookingValidator:
    """Temporary validator for cooking domain - maintains original interface"""

    def validate(self, supply_tree: SupplyTree) -> Dict[str, Any]:
        """Validate simplified cooking supply tree"""
        is_valid = True
        issues = []

        # Basic validation - check required fields
        if not supply_tree.facility_id:
            is_valid = False
            issues.append("Supply tree missing facility_id")

        if not supply_tree.facility_name:
            is_valid = False
            issues.append("Supply tree missing facility_name")

        if not supply_tree.okh_reference:
            is_valid = False
            issues.append("Supply tree missing okh_reference")

        if supply_tree.confidence_score < 0.0 or supply_tree.confidence_score > 1.0:
            is_valid = False
            issues.append("Confidence score must be between 0.0 and 1.0")

        # Check if it's a cooking domain supply tree
        if (
            supply_tree.match_type != "cooking"
            and "cooking" not in supply_tree.metadata.get("domain", "")
        ):
            issues.append("Warning: Supply tree may not be for cooking domain")

        return {
            "valid": is_valid,
            "confidence": 0.9 if is_valid else 0.3,
            "issues": issues,
        }
