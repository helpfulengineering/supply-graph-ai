from typing import Any, Dict, Optional
from pydantic import Field

from ..base import SuccessResponse


class ScaffoldResponse(SuccessResponse):
    """Response model for OKH project scaffolding.

    Extends SuccessResponse with scaffold-specific fields.
    """

    project_name: str = Field(..., description="Echo of input project name.")
    structure: Dict[str, Any] = Field(..., description="Directory/file structure blueprint.")
    manifest_template: Dict[str, Any] = Field(..., description="Manifest template aligned to OKH schema.")
    download_url: Optional[str] = Field(None, description="Download URL when output_format is zip.")
    filesystem_path: Optional[str] = Field(None, description="Filesystem path when output_format is filesystem.")
