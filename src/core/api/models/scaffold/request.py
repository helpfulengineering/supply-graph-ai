from typing import Any, Dict, Optional, Literal
from pydantic import Field

from ..base import BaseAPIRequest

TemplateLevel = Literal['minimal', 'standard', 'detailed']
OutputFormat = Literal['json', 'zip', 'filesystem']


class ScaffoldRequest(BaseAPIRequest):
    """Request model for OKH project scaffolding.

    Mirrors ScaffoldOptions in services, exposed as API-friendly schema.
    """

    project_name: str = Field(..., description="Human-friendly project name; used for directory name.")
    version: str = Field("0.1.0", description="Initial project version string.")
    organization: Optional[str] = Field(None, description="Organization name for packaging alignment.")
    template_level: TemplateLevel = Field("standard", description="Template detail level")
    output_format: OutputFormat = Field("json", description="Output format: json, zip, filesystem")
    output_path: Optional[str] = Field(None, description="Target path for filesystem or zip outputs.")
    include_examples: bool = Field(True, description="Include example content in stubs.")
    okh_version: str = Field("OKH-LOSHv1.0", description="OKH schema version tag to use.")
