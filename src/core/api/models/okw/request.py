from typing import Any, Dict, List, Optional

from pydantic import BaseModel, ConfigDict, Field

from ..base import BaseAPIRequest, LLMRequestMixin


class OKWCreateRequest(BaseAPIRequest, LLMRequestMixin):
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

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "name": "TechFab Manufacturing Hub",
                "facility_status": "active",
                "access_type": "public",
                "location": {
                    "address": {
                        "street": "123 Industrial Ave",
                        "city": "San Francisco",
                        "country": "USA",
                    },
                    "coordinates": {"latitude": 37.7749, "longitude": -122.4194},
                },
                "manufacturing_processes": ["PCB Assembly", "3D Printing"],
                "equipment": [
                    {"name": "Pick and Place Machine", "type": "PCB Assembly"}
                ],
                "typical_materials": ["FR4", "PLA", "ABS"],
                "use_llm": True,
                "llm_provider": "anthropic",
                "llm_model": "claude-sonnet-4-5",
                "quality_level": "professional",
                "strict_mode": False,
            }
        }
    )


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
