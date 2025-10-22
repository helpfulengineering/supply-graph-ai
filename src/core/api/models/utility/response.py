from pydantic import BaseModel, Field
from typing import Dict, List, Optional, Any

from ..base import SuccessResponse, LLMResponseMixin, ValidationResult as BaseValidationResult

class Domain(BaseModel):
    """Model for domain information"""
    # Required fields only
    id: str
    name: str
    description: str

class DomainsResponse(SuccessResponse, LLMResponseMixin):
    """Response model for available domains with standardized fields and LLM information"""
    # Required fields only
    domains: List[Domain]
    
    # Additional fields for enhanced response
    processing_time: float = 0.0
    validation_results: Optional[List[BaseValidationResult]] = None
    
    class Config:
        json_schema_extra = {
            "example": {
                "domains": [
                    {
                        "id": "manufacturing",
                        "name": "Manufacturing Domain",
                        "description": "Hardware manufacturing capabilities"
                    }
                ],
                "status": "success",
                "message": "Domains retrieved successfully",
                "timestamp": "2024-01-01T12:00:00Z",
                "request_id": "req_123456789",
                "processing_time": 0.1,
                "llm_used": True,
                "llm_provider": "anthropic",
                "llm_cost": 0.001,
                "data": {},
                "validation_results": []
            }
        }

class Context(BaseModel):
    """Model for validation context information"""
    # Required fields only
    id: str
    name: str
    description: str

class ContextsResponse(SuccessResponse, LLMResponseMixin):
    """Response model for validation contexts with standardized fields and LLM information"""
    # Required fields only
    contexts: List[Context]
    
    # Additional fields for enhanced response
    processing_time: float = 0.0
    validation_results: Optional[List[BaseValidationResult]] = None
    
    class Config:
        json_schema_extra = {
            "example": {
                "contexts": [
                    {
                        "id": "professional",
                        "name": "Professional Manufacturing",
                        "description": "Commercial-grade production"
                    }
                ],
                "status": "success",
                "message": "Contexts retrieved successfully",
                "timestamp": "2024-01-01T12:00:00Z",
                "request_id": "req_123456789",
                "processing_time": 0.1,
                "llm_used": True,
                "llm_provider": "anthropic",
                "llm_cost": 0.001,
                "data": {},
                "validation_results": []
            }
        }

class ErrorResponse(BaseModel):
    """Response model for API errors"""
    # Required fields first
    error: Dict[str, Any]  # Contains code, message, details