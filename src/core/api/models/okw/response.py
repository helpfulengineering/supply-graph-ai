from pydantic import BaseModel, Field
from typing import Dict, List, Optional, Any, Union
from uuid import UUID

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

class OKWResponse(BaseModel):
    """Response model for OKW facilities"""
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

class SuccessResponse(BaseModel):
    """Response model for successful operations"""
    # Required fields only
    success: bool
    message: str