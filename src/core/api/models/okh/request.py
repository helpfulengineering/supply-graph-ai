from typing import Any, Dict, List, Optional, Union

from pydantic import BaseModel, Field

from ..base import BaseAPIRequest


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
    organization: Optional[
        Union[str, Dict[str, Any], List[Union[str, Dict[str, Any]]]]
    ] = None
    image: Optional[str] = None
    version_date: Optional[str] = None
    readme: Optional[str] = None
    contribution_guide: Optional[str] = None
    manufacturing_files: List[Dict[str, Any]] = Field(default_factory=list)
    design_files: List[Dict[str, Any]] = Field(default_factory=list)
    making_instructions: List[Dict[str, Any]] = Field(default_factory=list)
    tool_list: List[str] = Field(default_factory=list)
    manufacturing_processes: List[str] = Field(default_factory=list)
    materials: List[Union[str, Dict[str, Any]]] = Field(
        default_factory=list
    )  # Allow both strings and dicts
    manufacturing_specs: Optional[Dict[str, Any]] = None
    parts: List[Dict[str, Any]] = Field(default_factory=list)
    metadata: Dict[str, Any] = Field(default_factory=dict)

    # Additional fields from OKH-LOSH format
    okhv: Optional[str] = None
    id: Optional[str] = None
    development_stage: Optional[str] = None
    technology_readiness_level: Optional[str] = None
    operating_instructions: Optional[List[Dict[str, Any]]] = None
    bom: Optional[Dict[str, Any]] = None
    standards_used: Optional[List[Dict[str, Any]]] = None
    tsdc: Optional[List[Dict[str, Any]]] = None
    sub_parts: Optional[List[Dict[str, Any]]] = None
    software: Optional[List[Dict[str, Any]]] = None
    files: Optional[List[Dict[str, Any]]] = None


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


class OKHGenerateRequest(BaseModel):
    """Request model for generating OKH manifest from URL or local path"""

    # Required fields
    url: str = Field(
        ...,
        description=(
            "Repository URL (GitHub / GitLab) **or** an absolute path to a locally "
            "cloned repository on the server filesystem.  When a local path is given "
            "the service skips network extraction and reads the directory directly."
        ),
    )

    # Optional fields
    skip_review: bool = Field(
        False, description="Skip interactive review and generate manifest directly"
    )
    verbose: bool = Field(
        False,
        description="Include file metadata in manifest (default: False for less verbose output)",
    )
    clone: bool = Field(
        False,
        description=(
            "Clone the repository locally before extraction (faster, no API rate limits). "
            "Ignored when `url` is already a local path."
        ),
    )
    save_clone: Optional[str] = Field(
        None,
        description=(
            "Server-side path where the cloned repository should be persisted after "
            "generation instead of being deleted.  Only used when `clone=true` and "
            "`url` is a remote URL.  Useful for caching clones so a subsequent request "
            "can pass the saved path as `url` to skip re-cloning."
        ),
    )


class OKHFromStorageRequest(BaseAPIRequest):
    """Request model for retrieving OKH manifest from storage"""

    # Required fields
    manifest_id: str = Field(
        ..., description="ID of the stored OKH manifest to retrieve"
    )
