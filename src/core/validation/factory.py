"""
Validation context factory.

This module provides the ValidationContextFactory class for creating
domain-aware validation contexts.
"""

from typing import Any, Optional

from ..registry.domain_registry import DomainRegistry
from .context import ValidationContext
from .exceptions import ValidationContextError


class ValidationContextFactory:
    """Factory for creating validation contexts from domain configurations"""

    @staticmethod
    def create_context(
        domain_name: str, quality_level: str = "professional", strict_mode: bool = False
    ) -> ValidationContext:
        """Create validation context from domain configuration"""

        # Validate domain exists
        if domain_name not in DomainRegistry.list_domains():
            raise ValidationContextError(
                f"Domain '{domain_name}' not found. Available domains: {DomainRegistry.list_domains()}"
            )

        # Get domain metadata
        domain_metadata = DomainRegistry.get_domain_metadata(domain_name)

        # Create context
        context = ValidationContext(
            name=f"{domain_name}_{quality_level}",
            domain=domain_name,
            quality_level=quality_level,
            strict_mode=strict_mode,
        )

        return context

    @staticmethod
    def create_manufacturing_context(
        quality_level: str = "professional", strict_mode: bool = False
    ) -> ValidationContext:
        """Create validation context for manufacturing domain"""
        return ValidationContextFactory.create_context(
            domain_name="manufacturing",
            quality_level=quality_level,
            strict_mode=strict_mode,
        )

    @staticmethod
    def create_cooking_context(
        quality_level: str = "home", strict_mode: bool = False
    ) -> ValidationContext:
        """Create validation context for cooking domain"""
        return ValidationContextFactory.create_context(
            domain_name="cooking", quality_level=quality_level, strict_mode=strict_mode
        )

    @staticmethod
    def create_context_from_detection(
        requirements: Any, capabilities: Any, quality_level: str = "professional"
    ) -> ValidationContext:
        """Create validation context from domain detection"""

        # Try to detect domain from requirements and capabilities
        detected_domain = ValidationContextFactory._detect_domain(
            requirements, capabilities
        )

        if detected_domain:
            return ValidationContextFactory.create_context(
                detected_domain, quality_level
            )
        else:
            # Default to manufacturing if detection fails
            return ValidationContextFactory.create_context(
                "manufacturing", quality_level
            )

    @staticmethod
    def _detect_domain(requirements: Any, capabilities: Any) -> Optional[str]:
        """Detect domain from requirements and capabilities"""
        # Simple domain detection logic
        # This could be enhanced with more sophisticated detection

        if isinstance(requirements, dict):
            # Check for manufacturing keywords
            manufacturing_keywords = [
                "okh",
                "okw",
                "manufacturing",
                "hardware",
                "machining",
                "tolerance",
            ]
            if any(
                keyword in str(requirements).lower()
                for keyword in manufacturing_keywords
            ):
                return "manufacturing"

            # Check for cooking keywords
            cooking_keywords = [
                "recipe",
                "cooking",
                "kitchen",
                "ingredient",
                "food",
                "meal",
            ]
            if any(
                keyword in str(requirements).lower() for keyword in cooking_keywords
            ):
                return "cooking"

        if isinstance(capabilities, dict):
            # Check capabilities for domain indicators
            manufacturing_capabilities = ["cnc", "3d printing", "machining", "assembly"]
            if any(
                cap in str(capabilities).lower() for cap in manufacturing_capabilities
            ):
                return "manufacturing"

            cooking_capabilities = ["oven", "stove", "refrigerator", "kitchen"]
            if any(cap in str(capabilities).lower() for cap in cooking_capabilities):
                return "cooking"

        return None

    @staticmethod
    def get_available_quality_levels(domain_name: str) -> list:
        """Get available quality levels for a domain"""
        quality_levels = {
            "manufacturing": ["hobby", "professional", "medical"],
            "cooking": ["home", "commercial", "professional"],
        }

        return quality_levels.get(domain_name, [])

    @staticmethod
    def validate_quality_level(domain_name: str, quality_level: str) -> bool:
        """Validate that a quality level is valid for a domain"""
        available_levels = ValidationContextFactory.get_available_quality_levels(
            domain_name
        )
        return quality_level in available_levels
