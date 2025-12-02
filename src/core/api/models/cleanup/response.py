from typing import List
from pydantic import Field

from ..base import SuccessResponse


class CleanupResponse(SuccessResponse):
    """Response model for OKH project cleanup/optimization."""

    removed_files: List[str] = Field(
        default_factory=list, description="Files removed during cleanup"
    )
    removed_directories: List[str] = Field(
        default_factory=list, description="Directories removed during cleanup"
    )
    bytes_saved: int = Field(0, description="Total bytes saved by removing files")
    warnings: List[str] = Field(
        default_factory=list, description="Non-fatal issues encountered"
    )
