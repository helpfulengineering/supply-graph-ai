from pydantic import BaseModel, Field
from typing import Dict, List, Optional, Any, Union

from ..base import BaseAPIRequest, LLMRequestMixin

class OKHCreateRequest(BaseAPIRequest, LLMRequestMixin):
    """Request model for creating a new OKH manifest"""
    # Required fields first
    title: str
    repo: str
    version: str
    license: Union[str, Dict[str, Any]]  # Allow both string and dict
    licensor: Optional[Union[str, Dict[str, Any], List[Union[str, Dict[str, Any]]]]] = None  # Make optional
    documentation_language: Optional[Union[str, List[str]]] = None  # Make optional
    function: str
    
    # Optional fields after
    description: Optional[str] = None
    intended_use: Optional[str] = None
    keywords: List[str] = Field(default_factory=list)
    project_link: Optional[str] = None
    health_safety_notice: Optional[str] = None
    contact: Optional[Dict[str, Any]] = None
    contributors: List[Dict[str, Any]] = Field(default_factory=list)
    organization: Optional[Union[str, Dict[str, Any], List[Union[str, Dict[str, Any]]]]] = None
    image: Optional[str] = None
    version_date: Optional[str] = None
    readme: Optional[str] = None
    contribution_guide: Optional[str] = None
    manufacturing_files: List[Dict[str, Any]] = Field(default_factory=list)
    design_files: List[Dict[str, Any]] = Field(default_factory=list)
    making_instructions: List[Dict[str, Any]] = Field(default_factory=list)
    tool_list: List[str] = Field(default_factory=list)
    manufacturing_processes: List[str] = Field(default_factory=list)
    materials: List[Union[str, Dict[str, Any]]] = Field(default_factory=list)  # Allow both strings and dicts
    manufacturing_specs: Optional[Dict[str, Any]] = None
    parts: List[Dict[str, Any]] = Field(default_factory=list)
    metadata: Dict[str, Any] = Field(default_factory=dict)
    
    # Additional fields from OKH-LOSH format
    okhv: Optional[str] = None
    id: Optional[str] = None
    development_stage: Optional[str] = None
    technology_readiness_level: Optional[str] = None
    operating_instructions: Optional[List[Dict[str, Any]]] = None
    bom: Optional[Dict[str, Any]] = None
    standards_used: Optional[List[Dict[str, Any]]] = None
    tsdc: Optional[List[Dict[str, Any]]] = None
    sub_parts: Optional[List[Dict[str, Any]]] = None
    software: Optional[List[Dict[str, Any]]] = None
    files: Optional[List[Dict[str, Any]]] = None
    
    class Config:
        json_schema_extra = {
            "example": {
                "title": "Arduino-based IoT Sensor Node",
                "repo": "https://github.com/example/iot-sensor",
                "version": "1.0.0",
                "license": {"name": "MIT", "url": "https://opensource.org/licenses/MIT"},
                "licensor": "John Doe",
                "documentation_language": "en",
                "function": "IoT sensor node for environmental monitoring",
                "description": "A simple IoT sensor node based on Arduino",
                "intended_use": "Environmental monitoring and data collection",
                "keywords": ["iot", "sensor", "arduino", "environmental"],
                "project_link": "https://github.com/example/iot-sensor",
                "manufacturing_files": [
                    {"name": "pcb_design.kicad", "type": "design", "url": "https://github.com/example/iot-sensor/pcb.kicad"}
                ],
                "design_files": [
                    {"name": "enclosure.stl", "type": "3d_model", "url": "https://github.com/example/iot-sensor/enclosure.stl"}
                ],
                "tool_list": ["3D Printer", "Soldering Iron", "Multimeter"],
                "manufacturing_processes": ["3D Printing", "PCB Assembly", "Soldering"],
                "materials": [
                    {"name": "Arduino Nano", "quantity": 1, "specifications": "ATmega328P microcontroller"}
                ],
                "manufacturing_specs": {
                    "process_requirements": [
                        {"process_name": "PCB Assembly", "parameters": {}}
                    ]
                },
                "parts": [
                    {"name": "Arduino Nano", "quantity": 1, "specifications": "ATmega328P"}
                ],
                "metadata": {"category": "electronics", "difficulty": "beginner"},
                "use_llm": True,
                "llm_provider": "anthropic",
                "llm_model": "claude-sonnet-4-5",
                "quality_level": "professional",
                "strict_mode": False
            }
        }


class OKHUpdateRequest(BaseModel):
    """Request model for updating an OKH manifest"""
    # Required fields first
    title: str
    repo: str
    version: str
    license: Dict[str, Any]
    licensor: Union[str, Dict[str, Any], List[Union[str, Dict[str, Any]]]]
    documentation_language: Union[str, List[str]]
    function: str
    
    # Optional fields after
    description: Optional[str] = None
    intended_use: Optional[str] = None
    keywords: List[str] = Field(default_factory=list)
    project_link: Optional[str] = None
    health_safety_notice: Optional[str] = None
    contact: Optional[Dict[str, Any]] = None
    contributors: List[Dict[str, Any]] = Field(default_factory=list)
    organization: Optional[Union[str, Dict[str, Any], List[Union[str, Dict[str, Any]]]]] = None
    image: Optional[str] = None
    version_date: Optional[str] = None
    readme: Optional[str] = None
    contribution_guide: Optional[str] = None
    manufacturing_files: List[Dict[str, Any]] = Field(default_factory=list)
    design_files: List[Dict[str, Any]] = Field(default_factory=list)
    making_instructions: List[Dict[str, Any]] = Field(default_factory=list)
    tool_list: List[str] = Field(default_factory=list)
    manufacturing_processes: List[str] = Field(default_factory=list)
    materials: List[Union[str, Dict[str, Any]]] = Field(default_factory=list)  # Allow both strings and dicts
    manufacturing_specs: Optional[Dict[str, Any]] = None
    parts: List[Dict[str, Any]] = Field(default_factory=list)
    metadata: Dict[str, Any] = Field(default_factory=dict)
    
    # Additional fields from OKH-LOSH format
    okhv: Optional[str] = None
    id: Optional[str] = None
    development_stage: Optional[str] = None
    technology_readiness_level: Optional[str] = None
    operating_instructions: Optional[List[Dict[str, Any]]] = None
    bom: Optional[Dict[str, Any]] = None
    standards_used: Optional[List[Dict[str, Any]]] = None
    tsdc: Optional[List[Dict[str, Any]]] = None
    sub_parts: Optional[List[Dict[str, Any]]] = None
    software: Optional[List[Dict[str, Any]]] = None
    files: Optional[List[Dict[str, Any]]] = None

class OKHValidateRequest(BaseModel):
    """Request model for validating an OKH object"""
    # Required fields first
    content: Dict[str, Any]
    
    # Optional fields after
    validation_context: Optional[str] = None

class OKHExtractRequest(BaseModel):
    """Request model for extracting requirements from an OKH object"""
    # Required fields only
    content: Dict[str, Any]

class OKHUploadRequest(BaseModel):
    """Request model for uploading an OKH file"""
    # Optional fields for upload metadata
    description: Optional[str] = None
    tags: List[str] = Field(default_factory=list)
    validation_context: Optional[str] = None

class OKHGenerateRequest(BaseModel):
    """Request model for generating OKH manifest from URL"""
    # Required fields
    url: str = Field(..., description="Repository URL to generate manifest from")
    
    # Optional fields
    skip_review: bool = Field(False, description="Skip interactive review and generate manifest directly")


class OKHFromStorageRequest(BaseAPIRequest):
    """Request model for retrieving OKH manifest from storage"""
    # Required fields
    manifest_id: str = Field(..., description="ID of the stored OKH manifest to retrieve")