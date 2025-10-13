"""
Validation result models.

This module provides the ValidationResult, ValidationError, and ValidationWarning
classes for structured validation responses.
"""

from dataclasses import dataclass, field
from typing import List, Optional, Dict, Any


@dataclass
class ValidationError:
    """Represents a validation error"""
    message: str
    field: Optional[str] = None
    code: Optional[str] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for API responses"""
        result = {"message": self.message}
        if self.field:
            result["field"] = self.field
        if self.code:
            result["code"] = self.code
        return result


@dataclass
class ValidationWarning:
    """Represents a validation warning"""
    message: str
    field: Optional[str] = None
    code: Optional[str] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for API responses"""
        result = {"message": self.message}
        if self.field:
            result["field"] = self.field
        if self.code:
            result["code"] = self.code
        return result


@dataclass
class ValidationResult:
    """Result of a validation operation"""
    valid: bool
    errors: List[ValidationError] = field(default_factory=list)
    warnings: List[ValidationWarning] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def add_error(self, message: str, field: Optional[str] = None, code: Optional[str] = None):
        """Add a validation error"""
        self.errors.append(ValidationError(message, field, code))
        self.valid = False
    
    def add_warning(self, message: str, field: Optional[str] = None, code: Optional[str] = None):
        """Add a validation warning"""
        self.warnings.append(ValidationWarning(message, field, code))
    
    def merge(self, other: 'ValidationResult'):
        """Merge another validation result into this one"""
        self.errors.extend(other.errors)
        self.warnings.extend(other.warnings)
        self.metadata.update(other.metadata)
        # If either result is invalid, the merged result is invalid
        if not other.valid:
            self.valid = False
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for API responses"""
        return {
            "valid": self.valid,
            "errors": [error.to_dict() for error in self.errors],
            "warnings": [warning.to_dict() for warning in self.warnings],
            "metadata": self.metadata
        }
    
    @property
    def has_errors(self) -> bool:
        """Check if there are any errors"""
        return len(self.errors) > 0
    
    @property
    def has_warnings(self) -> bool:
        """Check if there are any warnings"""
        return len(self.warnings) > 0
    
    @property
    def error_count(self) -> int:
        """Get the number of errors"""
        return len(self.errors)
    
    @property
    def warning_count(self) -> int:
        """Get the number of warnings"""
        return len(self.warnings)
