from pydantic import BaseModel, Field
from typing import Dict, List, Optional, Any


class OKWCreateRequest(BaseModel):
    """Request model for creating a new OKW facility"""
    # Required fields first
    name: str
    location: Dict[str, Any]
    facility_status: str
    
    # Optional fields after
    owner: Optional[Dict[str, Any]] = None
    contact: Optional[Dict[str, Any]] = None
    affiliations: List[Dict[str, Any]] = Field(default_factory=list)
    opening_hours: Optional[str] = None
    description: Optional[str] = None
    date_founded: Optional[str] = None
    access_type: str = "RESTRICTED"
    wheelchair_accessibility: Optional[str] = None
    equipment: List[Dict[str, Any]] = Field(default_factory=list)
    manufacturing_processes: List[str] = Field(default_factory=list)
    typical_batch_size: Optional[str] = None
    floor_size: Optional[int] = None
    storage_capacity: Optional[str] = None
    typical_materials: List[Dict[str, Any]] = Field(default_factory=list)
    certifications: List[str] = Field(default_factory=list)
    metadata: Dict[str, Any] = Field(default_factory=dict)

class OKWUpdateRequest(BaseModel):
    """Request model for updating an OKW facility"""
    # Required fields first
    name: str
    location: Dict[str, Any]
    facility_status: str
    
    # Optional fields after
    owner: Optional[Dict[str, Any]] = None
    contact: Optional[Dict[str, Any]] = None
    affiliations: List[Dict[str, Any]] = Field(default_factory=list)
    opening_hours: Optional[str] = None
    description: Optional[str] = None
    date_founded: Optional[str] = None
    access_type: str = "RESTRICTED"
    wheelchair_accessibility: Optional[str] = None
    equipment: List[Dict[str, Any]] = Field(default_factory=list)
    manufacturing_processes: List[str] = Field(default_factory=list)
    typical_batch_size: Optional[str] = None
    floor_size: Optional[int] = None
    storage_capacity: Optional[str] = None
    typical_materials: List[Dict[str, Any]] = Field(default_factory=list)
    certifications: List[str] = Field(default_factory=list)
    metadata: Dict[str, Any] = Field(default_factory=dict)

class OKWValidateRequest(BaseModel):
    """Request model for validating an OKW object"""
    # Required fields only
    content: Dict[str, Any]
    
    # Optional fields after
    validation_context: Optional[str] = None

class OKWExtractRequest(BaseModel):
    """Request model for extracting capabilities from an OKW object"""
    # Required fields only
    content: Dict[str, Any]