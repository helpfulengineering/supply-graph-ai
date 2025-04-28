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

class ProcessRequirement(BaseModel):
    """Model for extracted process requirements"""
    # Required fields first
    process_name: str
    
    # Optional fields after
    parameters: Dict[str, Any] = {}
    validation_criteria: Dict[str, Any] = {}
    required_tools: List[str] = []
    notes: str = ""

class OKHResponse(BaseModel):
    """Response model for OKH manifests"""
    # Required fields first
    id: UUID
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
    keywords: List[str] = []
    project_link: Optional[str] = None
    health_safety_notice: Optional[str] = None
    contact: Optional[Dict[str, Any]] = None
    contributors: List[Dict[str, Any]] = []
    organization: Optional[Union[str, Dict[str, Any], List[Union[str, Dict[str, Any]]]]] = None
    image: Optional[str] = None
    version_date: Optional[str] = None
    readme: Optional[str] = None
    contribution_guide: Optional[str] = None
    manufacturing_files: List[Dict[str, Any]] = []
    design_files: List[Dict[str, Any]] = []
    making_instructions: List[Dict[str, Any]] = []
    tool_list: List[str] = []
    manufacturing_processes: List[str] = []
    materials: List[Dict[str, Any]] = []
    manufacturing_specs: Optional[Dict[str, Any]] = None
    parts: List[Dict[str, Any]] = []
    metadata: Dict[str, Any] = {}

class OKHValidationResponse(BaseModel):
    """Response model for OKH validation"""
    # Required fields first
    valid: bool
    normalized_content: Dict[str, Any]
    completeness_score: float
    
    # Optional fields after
    issues: Optional[List[ValidationIssue]] = None

class OKHExtractResponse(BaseModel):
    """Response model for requirement extraction"""
    # Required fields only
    requirements: List[ProcessRequirement]

class OKHListResponse(BaseModel):
    """Response model for listing OKH manifests"""
    # Required fields first
    results: List[OKHResponse]
    total: int
    page: int
    page_size: int

class SuccessResponse(BaseModel):
    """Response model for successful operations"""
    # Required fields only
    success: bool
    message: str