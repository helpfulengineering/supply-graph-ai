"""Response models for the convert API endpoints."""

from typing import Any, Dict, List

from pydantic import ConfigDict, Field

from ..base import SuccessResponse


class ConvertToDatasheetResponse(SuccessResponse):
    """Response model for OKH → MSF datasheet conversion.

    Returns the generated datasheet as a downloadable file (handled by
    the route via StreamingResponse).  This model wraps the metadata
    returned alongside the file.
    """

    manifest_title: str = Field(..., description="Title from the source OKH manifest")
    manifest_version: str = Field(
        ..., description="Version from the source OKH manifest"
    )
    output_filename: str = Field(..., description="Name of the generated .docx file")

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "success": True,
                "message": "Datasheet generated successfully",
                "manifest_title": "Oxygen Splitter Adapter",
                "manifest_version": "2.1.0",
                "output_filename": "oxygen-splitter-adapter-datasheet.docx",
            }
        },
    )


class ConvertFromDatasheetResponse(SuccessResponse):
    """Response model for MSF datasheet → OKH conversion.

    Returns the full OKH manifest data parsed from the uploaded
    datasheet.
    """

    manifest: Dict[str, Any] = Field(
        ..., description="The parsed OKH manifest as a JSON object"
    )
    manifest_title: str = Field(..., description="Title extracted from the datasheet")
    fields_populated: int = Field(
        0, description="Number of OKH fields populated from the datasheet"
    )
    warnings: List[str] = Field(
        default_factory=list,
        description="Any warnings encountered during conversion",
    )

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "success": True,
                "message": "Datasheet converted to OKH manifest successfully",
                "manifest_title": "Oxygen Splitter Adapter",
                "manifest": {
                    "title": "Oxygen Splitter Adapter",
                    "version": "1.0.0",
                    "license": {"hardware": "CERN-OHL-S-2.0"},
                    "function": "Splits oxygen flow",
                },
                "fields_populated": 15,
                "warnings": [],
            }
        },
    )
