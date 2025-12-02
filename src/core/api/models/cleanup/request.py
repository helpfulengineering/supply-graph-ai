from typing import Optional

from pydantic import Field

from ..base import BaseAPIRequest


class CleanupRequest(BaseAPIRequest):
    """Request model for OKH project cleanup/optimization."""

    project_path: str = Field(
        ..., description="Absolute path to the project root directory"
    )
    remove_unmodified_stubs: bool = Field(
        True, description="Remove documentation stubs that were not modified"
    )
    remove_empty_directories: bool = Field(
        True, description="Remove directories that are empty after cleanup"
    )
    dry_run: bool = Field(
        True, description="If true, only report what would be removed"
    )
