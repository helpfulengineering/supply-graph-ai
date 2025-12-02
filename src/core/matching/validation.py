"""
Validation Service for Capability Rules

This service provides validation functionality for rule data using dataclass constructors.
It leverages the built-in validation in CapabilityRule and CapabilityRuleSet dataclasses
and adds additional business rule validations.
"""

import logging
from typing import Any, Dict, List

from .capability_rules import CapabilityRule, CapabilityRuleSet

logger = logging.getLogger(__name__)


class ValidationService:
    """Service for validating rule data using dataclass constructors"""

    async def validate_rule_set(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Validate rule set data by attempting to construct CapabilityRuleSet.

        Args:
            data: Dictionary containing rule set data

        Returns:
            Dict with validation results:
            - valid: bool
            - errors: list of error messages
            - warnings: list of warning messages
        """
        errors = []
        warnings = []

        try:
            # Attempt to construct rule set (this will validate via __post_init__)
            rule_set = CapabilityRuleSet.from_dict(data)

            # Additional business logic validations
            warnings.extend(self._validate_business_rules(rule_set))

            return {"valid": True, "errors": [], "warnings": warnings}
        except ValueError as e:
            # Dataclass validation errors
            errors.append(str(e))
            return {"valid": False, "errors": errors, "warnings": warnings}
        except (KeyError, TypeError) as e:
            # Missing required fields or type errors
            errors.append(f"Invalid data structure: {str(e)}")
            return {"valid": False, "errors": errors, "warnings": warnings}
        except Exception as e:
            # Unexpected errors
            logger.exception("Unexpected validation error")
            errors.append(f"Validation error: {str(e)}")
            return {"valid": False, "errors": errors, "warnings": warnings}

    async def validate_rule(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Validate a single rule by attempting to construct CapabilityRule.

        Args:
            data: Dictionary containing rule data

        Returns:
            Dict with validation results:
            - valid: bool
            - errors: list of error messages
            - warnings: list of warning messages
        """
        errors = []
        warnings = []

        try:
            # Attempt to construct rule (this will validate via __post_init__)
            rule = CapabilityRule.from_dict(data)

            # Additional business logic validations
            warnings.extend(self._validate_rule_business_rules(rule))

            return {"valid": True, "errors": [], "warnings": warnings}
        except ValueError as e:
            errors.append(str(e))
            return {"valid": False, "errors": errors, "warnings": warnings}
        except (KeyError, TypeError) as e:
            errors.append(f"Invalid data structure: {str(e)}")
            return {"valid": False, "errors": errors, "warnings": warnings}
        except Exception as e:
            logger.exception("Unexpected validation error")
            errors.append(f"Validation error: {str(e)}")
            return {"valid": False, "errors": errors, "warnings": warnings}

    def _validate_business_rules(self, rule_set: CapabilityRuleSet) -> List[str]:
        """
        Additional business logic validations for rule sets.

        Args:
            rule_set: The validated rule set

        Returns:
            List of warning messages
        """
        warnings = []

        # Check for duplicate rule IDs across domains (future enhancement)
        # Check for conflicting rules (future enhancement)

        # Check for rules with very low confidence
        low_confidence_rules = [
            rule_id for rule_id, rule in rule_set.rules.items() if rule.confidence < 0.5
        ]
        if low_confidence_rules:
            warnings.append(
                f"Rules with low confidence (< 0.5): {', '.join(low_confidence_rules)}"
            )

        # Check for rules with duplicate requirements (case-insensitive)
        for rule_id, rule in rule_set.rules.items():
            req_lower = [r.lower().strip() for r in rule.satisfies_requirements]
            if len(req_lower) != len(set(req_lower)):
                warnings.append(
                    f"Rule '{rule_id}' has duplicate requirements (case-insensitive)"
                )

        # Check for rules with very long requirement lists
        long_requirement_rules = [
            rule_id
            for rule_id, rule in rule_set.rules.items()
            if len(rule.satisfies_requirements) > 20
        ]
        if long_requirement_rules:
            warnings.append(
                f"Rules with many requirements (> 20), consider splitting: {', '.join(long_requirement_rules)}"
            )

        return warnings

    def _validate_rule_business_rules(self, rule: CapabilityRule) -> List[str]:
        """
        Additional business logic validations for individual rules.

        Args:
            rule: The validated rule

        Returns:
            List of warning messages
        """
        warnings = []

        # Check for duplicate requirements (case-insensitive)
        req_lower = [r.lower().strip() for r in rule.satisfies_requirements]
        if len(req_lower) != len(set(req_lower)):
            warnings.append(
                "Duplicate requirements found in satisfies_requirements (case-insensitive)"
            )

        # Check confidence thresholds
        if rule.confidence < 0.5:
            warnings.append("Low confidence score (< 0.5) may result in poor matches")

        # Check for very long requirement lists (might indicate over-broad rule)
        if len(rule.satisfies_requirements) > 20:
            warnings.append(
                "Rule has many requirements (> 20), consider splitting into multiple rules"
            )

        return warnings
