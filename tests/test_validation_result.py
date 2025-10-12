"""
Tests for validation result models.

This module tests the ValidationResult, ValidationError, and ValidationWarning classes.
"""

import pytest
from src.core.validation.result import ValidationResult, ValidationError, ValidationWarning


class TestValidationError:
    """Test ValidationError class"""
    
    def test_validation_error_creation(self):
        """Test creating a validation error"""
        error = ValidationError("Test error message")
        assert error.message == "Test error message"
        assert error.field is None
        assert error.code is None
    
    def test_validation_error_with_field_and_code(self):
        """Test creating a validation error with field and code"""
        error = ValidationError("Test error", field="test_field", code="TEST_ERROR")
        assert error.message == "Test error"
        assert error.field == "test_field"
        assert error.code == "TEST_ERROR"
    
    def test_validation_error_to_dict(self):
        """Test converting validation error to dictionary"""
        error = ValidationError("Test error", field="test_field", code="TEST_ERROR")
        result = error.to_dict()
        expected = {
            "message": "Test error",
            "field": "test_field",
            "code": "TEST_ERROR"
        }
        assert result == expected
    
    def test_validation_error_to_dict_minimal(self):
        """Test converting validation error to dictionary with minimal fields"""
        error = ValidationError("Test error")
        result = error.to_dict()
        expected = {"message": "Test error"}
        assert result == expected


class TestValidationWarning:
    """Test ValidationWarning class"""
    
    def test_validation_warning_creation(self):
        """Test creating a validation warning"""
        warning = ValidationWarning("Test warning message")
        assert warning.message == "Test warning message"
        assert warning.field is None
        assert warning.code is None
    
    def test_validation_warning_with_field_and_code(self):
        """Test creating a validation warning with field and code"""
        warning = ValidationWarning("Test warning", field="test_field", code="TEST_WARNING")
        assert warning.message == "Test warning"
        assert warning.field == "test_field"
        assert warning.code == "TEST_WARNING"
    
    def test_validation_warning_to_dict(self):
        """Test converting validation warning to dictionary"""
        warning = ValidationWarning("Test warning", field="test_field", code="TEST_WARNING")
        result = warning.to_dict()
        expected = {
            "message": "Test warning",
            "field": "test_field",
            "code": "TEST_WARNING"
        }
        assert result == expected


class TestValidationResult:
    """Test ValidationResult class"""
    
    def test_validation_result_creation_valid(self):
        """Test creating a valid validation result"""
        result = ValidationResult(valid=True)
        assert result.valid is True
        assert len(result.errors) == 0
        assert len(result.warnings) == 0
        assert len(result.metadata) == 0
    
    def test_validation_result_creation_invalid(self):
        """Test creating an invalid validation result"""
        result = ValidationResult(valid=False)
        assert result.valid is False
        assert len(result.errors) == 0
        assert len(result.warnings) == 0
        assert len(result.metadata) == 0
    
    def test_add_error(self):
        """Test adding an error to validation result"""
        result = ValidationResult(valid=True)
        result.add_error("Test error", field="test_field", code="TEST_ERROR")
        
        assert result.valid is False
        assert len(result.errors) == 1
        assert result.errors[0].message == "Test error"
        assert result.errors[0].field == "test_field"
        assert result.errors[0].code == "TEST_ERROR"
    
    def test_add_warning(self):
        """Test adding a warning to validation result"""
        result = ValidationResult(valid=True)
        result.add_warning("Test warning", field="test_field", code="TEST_WARNING")
        
        assert result.valid is True  # Warnings don't make result invalid
        assert len(result.warnings) == 1
        assert result.warnings[0].message == "Test warning"
        assert result.warnings[0].field == "test_field"
        assert result.warnings[0].code == "TEST_WARNING"
    
    def test_merge_validation_results(self):
        """Test merging two validation results"""
        result1 = ValidationResult(valid=True)
        result1.add_warning("Warning 1")
        
        result2 = ValidationResult(valid=False)
        result2.add_error("Error 1")
        result2.add_warning("Warning 2")
        result2.metadata["test"] = "value"
        
        result1.merge(result2)
        
        assert result1.valid is False  # Merged result should be invalid
        assert len(result1.errors) == 1
        assert len(result1.warnings) == 2
        assert result1.metadata["test"] == "value"
        assert result1.errors[0].message == "Error 1"
        assert result1.warnings[0].message == "Warning 1"
        assert result1.warnings[1].message == "Warning 2"
    
    def test_to_dict(self):
        """Test converting validation result to dictionary"""
        result = ValidationResult(valid=False)
        result.add_error("Test error", field="test_field", code="TEST_ERROR")
        result.add_warning("Test warning", field="test_field", code="TEST_WARNING")
        result.metadata["test_key"] = "test_value"
        
        result_dict = result.to_dict()
        expected = {
            "valid": False,
            "errors": [{"message": "Test error", "field": "test_field", "code": "TEST_ERROR"}],
            "warnings": [{"message": "Test warning", "field": "test_field", "code": "TEST_WARNING"}],
            "metadata": {"test_key": "test_value"}
        }
        assert result_dict == expected
    
    def test_properties(self):
        """Test validation result properties"""
        result = ValidationResult(valid=True)
        
        # Initially no errors or warnings
        assert not result.has_errors
        assert not result.has_warnings
        assert result.error_count == 0
        assert result.warning_count == 0
        
        # Add error
        result.add_error("Test error")
        assert result.has_errors
        assert result.error_count == 1
        
        # Add warning
        result.add_warning("Test warning")
        assert result.has_warnings
        assert result.warning_count == 1
