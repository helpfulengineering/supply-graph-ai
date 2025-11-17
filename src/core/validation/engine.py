"""
Central validation engine integrated with domain system.

This module provides the main ValidationEngine class that coordinates
validation across different domains and validation types.
"""

from typing import Dict, List, Optional, Any
from abc import ABC, abstractmethod
from .context import ValidationContext
from .result import ValidationResult
from .exceptions import ValidationEngineError, DomainValidationError
from ..registry.domain_registry import DomainRegistry


class Validator(ABC):
    """Base class for all validators"""

    @abstractmethod
    async def validate(self, data: Any, context: Optional[ValidationContext] = None) -> ValidationResult:
        """Validate data and return result"""

    @property
    @abstractmethod
    def validation_type(self) -> str:
        """Return the type of validation this validator performs"""

    @property
    @abstractmethod
    def priority(self) -> int:
        """Return validation priority (higher = earlier)"""


class ValidationEngine:
    """Central validation engine integrated with domain system"""
    
    def __init__(self):
        self.validators: Dict[str, List[Validator]] = {}
        self.domain_registry = DomainRegistry
    
    async def validate(self, 
                      data: Any, 
                      validation_type: str, 
                      context: Optional[ValidationContext] = None) -> ValidationResult:
        """Validate data using domain-specific validators"""
        result = ValidationResult(valid=True)
        
        try:
            # Get domain-specific validator if context provided
            if context:
                domain_result = await self._validate_with_domain_context(data, validation_type, context)
                result.merge(domain_result)
            
            # Apply general validators for this validation type
            if validation_type in self.validators:
                for validator in self.validators[validation_type]:
                    validator_result = await self._run_validator(validator, data, context)
                    result.merge(validator_result)
            
        except Exception as e:
            result.add_error(
                f"Validation engine error: {str(e)}",
                code="validation_engine_error"
            )
            raise ValidationEngineError(f"Validation failed: {str(e)}") from e
        
        return result
    
    async def _validate_with_domain_context(self, 
                                          data: Any, 
                                          validation_type: str, 
                                          context: ValidationContext) -> ValidationResult:
        """Validate data using domain-specific context"""
        result = ValidationResult(valid=True)
        
        try:
            # Get domain services
            domain_services = self.domain_registry.get_domain_services(context.domain)
            domain_validator = domain_services.validator
            
            # Apply domain-specific validation
            if hasattr(domain_validator, 'validate'):
                # Use the domain validator's validate method
                import inspect
                if inspect.iscoroutinefunction(domain_validator.validate):
                    validation_result = await domain_validator.validate(data, context)
                else:
                    # Handle synchronous validators
                    validation_result = domain_validator.validate(data)
                
                # Convert to our ValidationResult format
                if isinstance(validation_result, dict):
                    result = self._convert_dict_to_validation_result(validation_result)
                elif isinstance(validation_result, bool):
                    if not validation_result:
                        result.add_error("Domain validation failed", code="domain_validation_failed")
                else:
                    # Assume it's already a ValidationResult-like object
                    result = validation_result
            
            # Apply context-specific validation rules
            context_result = await self._apply_context_validation(data, context)
            result.merge(context_result)
            
        except ValueError as e:
            result.add_error(f"Domain validation error: {str(e)}", code="domain_validation_error")
            raise DomainValidationError(f"Domain validation failed: {str(e)}") from e
        except Exception as e:
            result.add_error(f"Unexpected domain validation error: {str(e)}", code="domain_validation_unexpected")
            raise DomainValidationError(f"Unexpected domain validation error: {str(e)}") from e
        
        return result
    
    async def _apply_context_validation(self, data: Any, context: ValidationContext) -> ValidationResult:
        """Apply context-specific validation rules"""
        result = ValidationResult(valid=True)
        
        # Validate quality level
        if not context.is_quality_level_valid():
            result.add_error(
                f"Invalid quality level '{context.quality_level}' for domain '{context.domain}'",
                code="invalid_quality_level"
            )
        
        # Apply custom rules if any
        if context.custom_rules:
            custom_result = await self._apply_custom_rules(data, context.custom_rules)
            result.merge(custom_result)
        
        return result
    
    async def _apply_custom_rules(self, data: Any, custom_rules: Dict[str, Any]) -> ValidationResult:
        """Apply custom validation rules"""
        result = ValidationResult(valid=True)
        
        # Basic custom rule validation
        for rule_name, rule_value in custom_rules.items():
            if isinstance(rule_value, dict) and "required" in rule_value:
                required_fields = rule_value["required"]
                if isinstance(required_fields, list):
                    for field in required_fields:
                        if isinstance(data, dict) and field not in data:
                            result.add_error(
                                f"Required field '{field}' is missing",
                                field=field,
                                code="required_field_missing"
                            )
        
        return result
    
    def _convert_dict_to_validation_result(self, validation_dict: Dict[str, Any]) -> ValidationResult:
        """Convert dictionary validation result to ValidationResult object"""
        result = ValidationResult(valid=validation_dict.get("valid", True))
        
        # Convert issues to errors and warnings
        issues = validation_dict.get("issues", [])
        warnings = validation_dict.get("warnings", [])
        
        for issue in issues:
            if isinstance(issue, str):
                result.add_error(issue)
            elif isinstance(issue, dict):
                result.add_error(
                    issue.get("message", "Unknown error"),
                    field=issue.get("field"),
                    code=issue.get("code")
                )
        
        for warning in warnings:
            if isinstance(warning, str):
                result.add_warning(warning)
            elif isinstance(warning, dict):
                result.add_warning(
                    warning.get("message", "Unknown warning"),
                    field=warning.get("field"),
                    code=warning.get("code")
                )
        
        # Add metadata
        if "completeness_score" in validation_dict:
            result.metadata["completeness_score"] = validation_dict["completeness_score"]
        if "confidence" in validation_dict:
            result.metadata["confidence"] = validation_dict["confidence"]
        
        return result
    
    async def _run_validator(self, validator: Any, data: Any, context: Optional[ValidationContext]) -> ValidationResult:
        """Run a validator and return ValidationResult"""
        try:
            if hasattr(validator, 'validate'):
                if context:
                    validation_result = validator.validate(data, context)
                else:
                    validation_result = validator.validate(data)
                
                if isinstance(validation_result, ValidationResult):
                    return validation_result
                elif isinstance(validation_result, dict):
                    return self._convert_dict_to_validation_result(validation_result)
                elif isinstance(validation_result, bool):
                    result = ValidationResult(valid=validation_result)
                    if not validation_result:
                        result.add_error("Validator returned false", code="validator_failed")
                    return result
                else:
                    # Unknown return type
                    return ValidationResult(valid=True)
            else:
                return ValidationResult(valid=True)
        except Exception as e:
            result = ValidationResult(valid=False)
            result.add_error(f"Validator error: {str(e)}", code="validator_error")
            return result
    
    def register_validator(self, validation_type: str, validator: Any, priority: int = 0):
        """Register a validator for a specific validation type"""
        if validation_type not in self.validators:
            self.validators[validation_type] = []
        
        # Insert validator at the correct priority position
        self.validators[validation_type].insert(priority, validator)
    
    def get_registered_validators(self, validation_type: str) -> List[Any]:
        """Get all registered validators for a validation type"""
        return self.validators.get(validation_type, [])
    
    def clear_validators(self, validation_type: Optional[str] = None):
        """Clear validators for a specific type or all types"""
        if validation_type:
            self.validators.pop(validation_type, None)
        else:
            self.validators.clear()
