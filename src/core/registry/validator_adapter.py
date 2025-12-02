"""
Adapter for new validation framework validators to work with BaseValidator interface.

This adapter allows validators from the new validation framework (Validator)
to be used in contexts that expect BaseValidator.
"""

from typing import Optional, TYPE_CHECKING
from ..models.base.base_types import BaseValidator, Requirement, Capability

if TYPE_CHECKING:
    from ..validation.engine import Validator as ValidationEngineValidator
    from ..validation.context import ValidationContext
    from ..validation.result import ValidationResult


class ValidatorAdapter(BaseValidator):
    """
    Adapter that wraps a ValidationEngineValidator to implement BaseValidator interface.

    This allows new framework validators to be used in contexts expecting BaseValidator.
    """

    def __init__(self, validator: "ValidationEngineValidator"):
        """
        Initialize adapter with a ValidationEngineValidator.

        Args:
            validator: Validator from new validation framework
        """
        # Lazy import to avoid circular dependency
        from ..validation.engine import Validator as ValidationEngineValidator

        if not isinstance(validator, ValidationEngineValidator):
            raise TypeError(
                f"validator must be ValidationEngineValidator, got {type(validator)}"
            )
        self._validator = validator

    def validate(
        self, requirement: Requirement, capability: Optional[Capability] = None
    ) -> bool:
        """
        Validate a requirement or requirement-capability pair.

        This method adapts the new async ValidationResult interface to the
        old synchronous bool interface.

        Note: This is a simplified adapter. For full functionality, the new
        validation framework should be used directly with proper ValidationContext.

        Args:
            requirement: Requirement to validate
            capability: Optional capability to validate against

        Returns:
            True if valid, False otherwise
        """
        import asyncio

        # Lazy imports to avoid circular dependency
        from ..validation.factory import ValidationContextFactory

        # Try to infer domain from requirement type
        domain = "manufacturing"  # Default
        if hasattr(requirement, "type"):
            if requirement.type in ["recipe", "kitchen"]:
                domain = "cooking"

        # Create validation context with minimal required fields
        # Note: This is a limitation - we need domain/quality_level which may not be available
        try:
            context = ValidationContextFactory.create_context(
                domain_name=domain, quality_level="professional", strict_mode=False
            )
        except Exception:
            # Fallback: create minimal context if factory fails
            # This may fail if domain not registered, but we'll handle that
            context = None

        # Call async validator (run in event loop if needed)
        try:
            loop = asyncio.get_event_loop()
            if loop.is_running():
                # If loop is running, we can't use asyncio.run
                # This is a limitation - async validators in sync context
                # TODO: Consider making BaseValidator.validate async
                raise RuntimeError(
                    "Cannot use async validator in sync context. "
                    "Consider using async validation or sync validator."
                )
            else:
                # Convert requirement to dict for new framework
                data = (
                    {"requirement": requirement, "capability": capability}
                    if capability
                    else requirement
                )
                result = asyncio.run(self._validator.validate(data, context))
        except RuntimeError:
            # No event loop, create one
            data = (
                {"requirement": requirement, "capability": capability}
                if capability
                else requirement
            )
            result = asyncio.run(self._validator.validate(data, context))

        return result.valid

    @property
    def wrapped_validator(self) -> "ValidationEngineValidator":
        """Get the wrapped validator."""
        return self._validator
