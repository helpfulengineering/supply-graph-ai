"""
Tests for validation API models.

This module tests the Pydantic models for validation API requests and responses.
"""

import pytest
from src.core.api.models.validation.request import ValidationRequest, ValidationContextRequest
from src.core.api.models.validation.response import ValidationResponse, ValidationContextResponse, ValidationIssue
from src.core.api.models.validation.context import ValidationContextModel


class TestValidationRequest:
    """Test ValidationRequest model"""
    
    def test_validation_request_creation(self):
        """Test creating a validation request"""
        request = ValidationRequest(
            content={"title": "Test", "version": "1.0.0"},
            validation_type="okh_manifest"
        )
        
        assert request.content == {"title": "Test", "version": "1.0.0"}
        assert request.validation_type == "okh_manifest"
        assert request.context is None
        assert request.quality_level == "professional"
        assert request.strict_mode is False
    
    def test_validation_request_with_all_fields(self):
        """Test creating a validation request with all fields"""
        request = ValidationRequest(
            content={"title": "Test", "version": "1.0.0"},
            validation_type="okh_manifest",
            context="manufacturing",
            quality_level="hobby",
            strict_mode=True
        )
        
        assert request.content == {"title": "Test", "version": "1.0.0"}
        assert request.validation_type == "okh_manifest"
        assert request.context == "manufacturing"
        assert request.quality_level == "hobby"
        assert request.strict_mode is True


class TestValidationContextRequest:
    """Test ValidationContextRequest model"""
    
    def test_validation_context_request_creation(self):
        """Test creating a validation context request"""
        request = ValidationContextRequest(domain="manufacturing")
        
        assert request.domain == "manufacturing"
        assert request.quality_level == "professional"
        assert request.strict_mode is False


class TestValidationIssue:
    """Test ValidationIssue model"""
    
    def test_validation_issue_creation(self):
        """Test creating a validation issue"""
        issue = ValidationIssue(
            severity="error",
            message="Test error message"
        )
        
        assert issue.severity == "error"
        assert issue.message == "Test error message"
        assert issue.path == []
        assert issue.code is None
    
    def test_validation_issue_with_all_fields(self):
        """Test creating a validation issue with all fields"""
        issue = ValidationIssue(
            severity="warning",
            message="Test warning message",
            path=["field1", "field2"],
            code="TEST_WARNING"
        )
        
        assert issue.severity == "warning"
        assert issue.message == "Test warning message"
        assert issue.path == ["field1", "field2"]
        assert issue.code == "TEST_WARNING"


class TestValidationResponse:
    """Test ValidationResponse model"""
    
    def test_validation_response_creation(self):
        """Test creating a validation response"""
        response = ValidationResponse(
            valid=True,
            normalized_content={"title": "Test", "version": "1.0.0"}
        )
        
        assert response.valid is True
        assert response.normalized_content == {"title": "Test", "version": "1.0.0"}
        assert response.issues is None
        assert response.context is None
        assert response.metadata == {}
    
    def test_validation_response_with_issues(self):
        """Test creating a validation response with issues"""
        issue = ValidationIssue(
            severity="error",
            message="Test error",
            code="TEST_ERROR"
        )
        
        response = ValidationResponse(
            valid=False,
            normalized_content={"title": "Test"},
            issues=[issue]
        )
        
        assert response.valid is False
        assert len(response.issues) == 1
        assert response.issues[0].severity == "error"
        assert response.issues[0].message == "Test error"


class TestValidationContextModel:
    """Test ValidationContextModel"""
    
    def test_validation_context_model_creation(self):
        """Test creating a validation context model"""
        context = ValidationContextModel(
            name="test_context",
            domain="manufacturing",
            quality_level="professional"
        )
        
        assert context.name == "test_context"
        assert context.domain == "manufacturing"
        assert context.quality_level == "professional"
        assert context.strict_mode is False
        assert context.validation_rules == {}
        assert context.supported_types == []
        assert context.validation_strictness is None


class TestValidationContextResponse:
    """Test ValidationContextResponse model"""
    
    def test_validation_context_response_creation(self):
        """Test creating a validation context response"""
        context = ValidationContextModel(
            name="test_context",
            domain="manufacturing",
            quality_level="professional"
        )
        
        response = ValidationContextResponse(
            contexts=[context],
            total_count=1
        )
        
        assert len(response.contexts) == 1
        assert response.total_count == 1
        assert response.contexts[0].name == "test_context"
