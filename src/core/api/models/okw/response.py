from pydantic import BaseModel, Field
from typing import Dict, List, Optional, Any, Union
from uuid import UUID

from ..base import SuccessResponse, LLMResponseMixin, ValidationResult as BaseValidationResult

class ValidationIssue(BaseModel):
    """Model for validation issues"""
    # Required fields first
    severity: str  # "error", "warning", "info"
    message: str
    
    # Optional fields after
    path: List[str] = []

class Capability(BaseModel):
    """Model for extracted capabilities"""
    # Required fields first
    type: str
    
    # Optional fields after
    parameters: Dict[str, Any] = {}
    limitations: Dict[str, Any] = {}

class OKWResponse(SuccessResponse, LLMResponseMixin):
    """Response model for OKW facilities with standardized fields and LLM information"""
    # Required fields first
    id: UUID
    name: str
    location: Dict[str, Any]
    facility_status: str
    access_type: str
    
    # Optional fields after
    owner: Optional[Dict[str, Any]] = None
    contact: Optional[Dict[str, Any]] = None
    affiliations: List[Dict[str, Any]] = []
    opening_hours: Optional[str] = None
    description: Optional[str] = None
    date_founded: Optional[str] = None
    wheelchair_accessibility: Optional[str] = None
    equipment: List[Dict[str, Any]] = []
    manufacturing_processes: List[str] = []
    typical_batch_size: Optional[str] = None
    floor_size: Optional[int] = None
    storage_capacity: Optional[str] = None
    typical_materials: List[Dict[str, Any]] = []
    certifications: List[str] = []
    metadata: Dict[str, Any] = {}
    domain: Optional[str] = None  # "manufacturing" or "cooking"
    
    # Additional fields for enhanced response
    processing_time: float = 0.0
    validation_results: Optional[List[BaseValidationResult]] = None
    
    class Config:
        json_schema_extra = {
            "example": {
                "status": "success",
                "message": "OKW operation completed successfully",
                "timestamp": "2024-01-01T12:00:00Z",
                "request_id": "req_123456789",
                "facility": {
                    "id": "facility_123",
                    "name": "TechFab Manufacturing Hub",
                    "facility_status": "active"
                },
                "processing_time": 1.25,
                "llm_used": True,
                "llm_provider": "anthropic",
                "llm_cost": 0.012,
                "data": {},
                "metadata": {}
            }
        }

class OKWValidationResponse(BaseModel):
    """Response model for OKW validation"""
    # Required fields first
    valid: bool
    normalized_content: Dict[str, Any]
    
    # Optional fields after
    issues: Optional[List[ValidationIssue]] = None

class OKWExtractResponse(BaseModel):
    """Response model for capability extraction"""
    # Required fields only
    capabilities: List[Capability]

class OKWListResponse(BaseModel):
    """Response model for listing OKW facilities"""
    # Required fields first
    results: List[OKWResponse]
    total: int
    page: int
    page_size: int

class OKWUploadResponse(BaseModel):
    """Response model for OKW file upload"""
    # Required fields first
    success: bool
    message: str
    okw: OKWResponse
    
    # Optional fields after
    validation_issues: Optional[List[ValidationIssue]] = None

class OKWExportResponse(BaseModel):
    """Response model for OKW schema export"""
    # Required fields first
    success: bool
    message: str
    schema: Dict[str, Any]
    
    # Optional fields after
    schema_version: Optional[str] = "http://json-schema.org/draft-07/schema#"
    model_name: Optional[str] = "ManufacturingFacility"
