from typing import Any, Dict, List, Optional, Union
from uuid import UUID

from pydantic import BaseModel, ConfigDict

from ..base import LLMResponseMixin, SuccessResponse
from ..base import ValidationResult as BaseValidationResult


class ValidationIssue(BaseModel):
    """Model for validation issues"""

    severity: str  # "error", "warning", "info"
    message: str

    path: List[str] = []


class ProcessRequirement(BaseModel):
    """Model for extracted process requirements"""

    process_name: str

    parameters: Dict[str, Any] = {}
    validation_criteria: Dict[str, Any] = {}
    required_tools: List[str] = []
    notes: str = ""


class OKHResponse(SuccessResponse, LLMResponseMixin):
    """Response model for OKH manifests with standardized fields and LLM information"""

    id: UUID
    title: str
    version: str
    license: Dict[str, Any]
    licensor: Union[str, Dict[str, Any], List[Union[str, Dict[str, Any]]]]
    documentation_language: Union[str, List[str]]
    function: str

    repo: Optional[str] = None
    description: Optional[str] = None
    intended_use: Optional[str] = None
    keywords: List[str] = []
    project_link: Optional[str] = None
    health_safety_notice: Optional[str] = None
    contact: Optional[Dict[str, Any]] = None
    contributors: List[Dict[str, Any]] = []
    organization: Optional[
        Union[str, Dict[str, Any], List[Union[str, Dict[str, Any]]]]
    ] = None
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
    components: List[Dict[str, Any]] = []
    metadata: Dict[str, Any] = {}

    processing_time: float = 0.0
    validation_results: Optional[List[BaseValidationResult]] = None

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "id": "00000000-0000-0000-0000-000000000000",
                "title": "Arduino-based IoT Sensor Node",
                "version": "1.0.0",
                "license": {
                    "name": "MIT",
                    "url": "https://opensource.org/licenses/MIT",
                },
                "licensor": "John Doe",
                "documentation_language": "en",
                "function": "IoT sensor node for environmental monitoring",
                "repo": "https://github.com/example/iot-sensor",
                "description": "A simple IoT sensor node based on Arduino",
                "intended_use": "Environmental monitoring and data collection",
                "keywords": ["iot", "sensor", "arduino", "environmental"],
                "project_link": "https://github.com/example/iot-sensor",
                "manufacturing_files": [
                    {
                        "name": "pcb_design.kicad",
                        "type": "design",
                        "url": "https://github.com/example/iot-sensor/pcb.kicad",
                    }
                ],
                "design_files": [
                    {
                        "name": "enclosure.stl",
                        "type": "3d_model",
                        "url": "https://github.com/example/iot-sensor/enclosure.stl",
                    }
                ],
                "tool_list": ["3D Printer", "Soldering Iron", "Multimeter"],
                "manufacturing_processes": ["3D Printing", "PCB Assembly", "Soldering"],
                "materials": [
                    {
                        "name": "Arduino Nano",
                        "quantity": 1,
                        "specifications": "ATmega328P microcontroller",
                    }
                ],
                "manufacturing_specs": {
                    "process_requirements": [
                        {"process_name": "PCB Assembly", "parameters": {}}
                    ]
                },
                "parts": [
                    {
                        "name": "Arduino Nano",
                        "quantity": 1,
                        "specifications": "ATmega328P",
                    }
                ],
                "metadata": {"category": "electronics", "difficulty": "beginner"},
                "status": "success",
                "message": "OKH operation completed successfully",
                "timestamp": "2024-01-01T12:00:00Z",
                "request_id": "req_123456789",
                "processing_time": 1.25,
                "llm_used": True,
                "llm_provider": "anthropic",
                "llm_cost": 0.012,
                "data": {},
                "validation_results": [],
            }
        }
    )


class OKHValidationResponse(BaseModel):
    """Response model for OKH validation"""

    valid: bool
    normalized_content: Dict[str, Any]
    completeness_score: float

    issues: Optional[List[ValidationIssue]] = None


class OKHExtractResponse(BaseModel):
    """Response model for requirement extraction"""

    requirements: List[ProcessRequirement]


class OKHListResponse(BaseModel):
    """Response model for listing OKH manifests"""

    results: List[OKHResponse]
    total: int
    page: int
    page_size: int


class OKHUploadResponse(BaseModel):
    """Response model for OKH file upload"""

    success: bool
    message: str
    okh: OKHResponse

    validation_issues: Optional[List[ValidationIssue]] = None
    completeness_score: Optional[float] = None


class OKHGenerateResponse(BaseModel):
    """Response model for OKH manifest generation from URL"""

    success: bool
    message: str
    manifest: Dict[str, Any]

    quality_report: Optional[Dict[str, Any]] = None


class OKHExportResponse(BaseModel):
    """Response model for OKH schema export"""

    success: bool
    message: str
    json_schema: Dict[
        str, Any
    ]  # Renamed from 'schema' to avoid shadowing BaseModel.schema

    schema_version: Optional[str] = "http://json-schema.org/draft-07/schema#"
    model_name: Optional[str] = "OKHManifest"
