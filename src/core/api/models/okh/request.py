from pydantic import BaseModel, Field
from typing import Dict, List, Optional, Any, Union
from uuid import UUID

class OKHCreateRequest(BaseModel):
    """Request model for creating a new OKH manifest"""
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
    materials: List[Dict[str, Any]] = Field(default_factory=list)
    manufacturing_specs: Optional[Dict[str, Any]] = None
    parts: List[Dict[str, Any]] = Field(default_factory=list)
    metadata: Dict[str, Any] = Field(default_factory=dict)


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
    materials: List[Dict[str, Any]] = Field(default_factory=list)
    manufacturing_specs: Optional[Dict[str, Any]] = None
    parts: List[Dict[str, Any]] = Field(default_factory=list)
    metadata: Dict[str, Any] = Field(default_factory=dict)

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