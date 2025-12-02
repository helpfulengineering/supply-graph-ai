from pydantic import BaseModel, ConfigDict
from typing import Dict, List, Optional, Any
from uuid import UUID

# Import base classes for enhanced functionality
from ..base import SuccessResponse, LLMResponseMixin, ValidationResult as BaseValidationResult

class SupplyTreeResponse(SuccessResponse, LLMResponseMixin):
    """Consolidated supply tree response with standardized fields and LLM information"""
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "id": "00000000-0000-0000-0000-000000000000",
                "facility_id": "12345678-1234-1234-1234-123456789012",
                "facility_name": "Electronics Manufacturing Facility",
                "okh_reference": "electronics-manufacturing",
                "confidence_score": 0.8,
                "creation_time": "2024-01-01T12:00:00Z",
                "estimated_cost": 1000.0,
                "estimated_time": "2 weeks",
                "materials_required": ["copper", "plastic", "silicon"],
                "capabilities_used": ["soldering", "assembly", "testing"],
                "match_type": "direct",
                "metadata": {"project": "IoT Sensor Node"},
                "processing_time": 2.5,
                "validation_results": [],
                "status": "success",
                "message": "Supply tree operation completed successfully",
                "timestamp": "2024-01-01T12:00:00Z",
                "request_id": "req_123456789",
                "llm_used": True,
                "llm_provider": "anthropic",
                "llm_cost": 0.025,
                "data": {}
            }
        }
    )
    
    # Required fields first
    id: UUID
    facility_id: UUID
    facility_name: str
    okh_reference: str
    confidence_score: float
    creation_time: str
    
    # Optional fields after
    estimated_cost: Optional[float] = None
    estimated_time: Optional[str] = None
    materials_required: List[str] = []
    capabilities_used: List[str] = []
    match_type: str = "unknown"
    metadata: Dict[str, Any] = {}
    
    # Additional fields for enhanced response
    processing_time: float = 0.0
    validation_results: Optional[List[BaseValidationResult]] = None

# Keep the old class name for backward compatibility
SimplifiedSupplyTreeResponse = SupplyTreeResponse

class OptimizationMetrics(BaseModel):
    """Response model for optimization metrics"""
    # All optional fields
    cost: Optional[float] = None
    time: Optional[str] = None

class SupplyTreeOptimizationResponse(SupplyTreeResponse):
    """Response model for optimized supply tree"""
    # Additional required field in this subclass
    optimization_metrics: OptimizationMetrics

class ValidationIssue(BaseModel):
    """Model for validation issues"""
    # Required fields first
    type: str  # "error", "warning", "info"
    message: str
    
    # Optional fields after
    path: Optional[str] = None
    component: Optional[str] = None

class ValidationResult(BaseModel):
    """Response model for validation results"""
    # Required fields first
    valid: bool
    confidence: float
    
    # Optional fields after
    issues: List[Dict[str, Any]] = []

class SupplyTreeListResponse(BaseModel):
    """Response model for listing supply trees"""
    # Required fields first
    results: List[SupplyTreeResponse]
    total: int
    page: int
    page_size: int

class SuccessResponse(BaseModel):
    """Response model for successful operations"""
    # Required fields only
    success: bool
    message: str