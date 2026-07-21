from typing import Any, Dict, List, Optional

from pydantic import BaseModel, ConfigDict, Field, field_validator

from ..base import BaseAPIRequest, LLMRequestMixin


class PackageBuildRequest(BaseAPIRequest, LLMRequestMixin):
    """Request model for building a package from manifest data"""

    # Core package fields
    manifest_data: Dict[str, Any] = Field(
        ..., min_length=1, description="OKH manifest data"
    )
    options: Optional[Dict[str, Any]] = Field(None, description="Build options")

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "manifest_data": {
                    "title": "Test Package",
                    "version": "1.0.0",
                    "manufacturing_specs": {
                        "process_requirements": [
                            {"process_name": "3D Printing", "parameters": {}}
                        ]
                    },
                },
                "options": {"include_dependencies": True, "compress_output": True},
                "use_llm": True,
                "llm_provider": "anthropic",
                "llm_model": "claude-sonnet-4-5",
                "quality_level": "professional",
                "strict_mode": False,
            }
        }
    )


class PackagePushRequest(BaseModel):
    """Request model for pushing a package to remote storage"""

    package_name: str = Field(..., description="Package name (e.g., 'org/project')")
    version: str = Field(..., description="Package version")

    model_config = ConfigDict(
        json_schema_extra={
            "example": {"package_name": "example/test-package", "version": "1.0.0"}
        }
    )


class PackagePullRequest(BaseModel):
    """Request model for pulling a package from remote storage"""

    package_name: str = Field(..., description="Package name (e.g., 'org/project')")
    version: str = Field(..., description="Package version")

    output_dir: Optional[str] = Field(
        None, description="Output directory for the pulled package"
    )

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "package_name": "example/test-package",
                "version": "1.0.0",
                "output_dir": "/path/to/output",
            }
        }
    )


class PackageZipItem(BaseModel):
    """One package identity for a batch zip download."""

    org: str = Field(..., min_length=1, description="Organization slug")
    project: str = Field(..., min_length=1, description="Project slug")
    version: str = Field(..., min_length=1, description="Package version")

    model_config = ConfigDict(
        json_schema_extra={
            "example": {"org": "community", "project": "widget", "version": "1.0.0"}
        }
    )


class PackageDownloadZipRequest(BaseModel):
    """Request body for POST /api/package/download-zip."""

    items: List[PackageZipItem] = Field(
        ...,
        min_length=1,
        description="Packages to include as .tar.gz entries in the zip",
    )

    @field_validator("items")
    @classmethod
    def _require_items(cls, items: List[PackageZipItem]) -> List[PackageZipItem]:
        if not items:
            raise ValueError("items must not be empty")
        return items

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "items": [
                    {"org": "community", "project": "widget", "version": "1.0.0"},
                    {"org": "acme", "project": "bracket", "version": "2.1.0"},
                ]
            }
        }
    )
