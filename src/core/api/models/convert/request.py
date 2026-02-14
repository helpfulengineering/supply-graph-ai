"""Request models for the convert API endpoints."""

from typing import Any, Dict, List, Optional, Union

from pydantic import BaseModel, ConfigDict, Field

from ..base import BaseAPIRequest


class ConvertToDatasheetRequest(BaseAPIRequest):
    """Request model for converting an OKH manifest to an MSF datasheet.

    Accepts a full OKH manifest (as JSON) and produces a populated MSF
    3D-printed product technical specification datasheet (.docx).
    """

    # The OKH manifest content (same shape as OKHCreateRequest)
    title: str
    version: str
    license: Union[str, Dict[str, Any]]
    licensor: Optional[Union[str, Dict[str, Any], List[Union[str, Dict[str, Any]]]]] = (
        None
    )
    documentation_language: Optional[Union[str, List[str]]] = None
    function: str

    # Optional OKH fields
    repo: Optional[str] = None
    description: Optional[str] = None
    intended_use: Optional[str] = None
    keywords: List[str] = Field(default_factory=list)
    image: Optional[str] = None
    development_stage: Optional[str] = None
    technology_readiness_level: Optional[str] = None
    health_safety_notice: Optional[str] = None
    manufacturing_files: List[Dict[str, Any]] = Field(default_factory=list)
    design_files: List[Dict[str, Any]] = Field(default_factory=list)
    making_instructions: List[Dict[str, Any]] = Field(default_factory=list)
    operating_instructions: List[Dict[str, Any]] = Field(default_factory=list)
    tool_list: List[str] = Field(default_factory=list)
    manufacturing_processes: List[str] = Field(default_factory=list)
    materials: List[Union[str, Dict[str, Any]]] = Field(default_factory=list)
    manufacturing_specs: Optional[Dict[str, Any]] = None
    standards_used: Optional[List[Dict[str, Any]]] = None
    parts: List[Dict[str, Any]] = Field(default_factory=list)
    metadata: Dict[str, Any] = Field(default_factory=dict)
    version_date: Optional[str] = None
    contact: Optional[Dict[str, Any]] = None
    contributors: List[Dict[str, Any]] = Field(default_factory=list)
    organization: Optional[
        Union[str, Dict[str, Any], List[Union[str, Dict[str, Any]]]]
    ] = None

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "title": "Oxygen Splitter Adapter",
                "version": "2.1.0",
                "license": {"hardware": "CERN-OHL-S-2.0"},
                "licensor": "MSF 3D Printing Team",
                "documentation_language": "en",
                "function": "Splits oxygen flow from a single concentrator to two patients",
                "description": "3D-printed adapter for oxygen concentrator splitting",
                "repo": "https://github.com/example/oxygen-splitter",
                "keywords": ["MED", "respiratory"],
                "development_stage": "production",
                "materials": [{"material_id": "PLA", "name": "PLA White"}],
                "tool_list": ["Prusa i3 MK3S"],
                "metadata": {
                    "critical_item": "Yes",
                    "dangerous_goods": "No",
                },
            }
        },
    )


class ConvertFromDatasheetRequest(BaseModel):
    """Request model for converting an MSF datasheet to an OKH manifest.

    The datasheet file is uploaded via multipart form data, so this model
    is used only for optional metadata accompanying the upload.
    """

    # Optional template path override (for validation against a custom template)
    template_path: Optional[str] = Field(
        None,
        description="Optional path to a custom MSF template for structure validation",
    )

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "template_path": None,
            }
        },
    )
