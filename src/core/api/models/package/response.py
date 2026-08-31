from typing import Any, Dict, List, Optional

from pydantic import BaseModel, ConfigDict, Field

from ..base import LLMResponseMixin, SuccessResponse
from ..base import ValidationResult as BaseValidationResult


class PackageResponse(SuccessResponse, LLMResponseMixin):
    """Response model for package operations with standardized fields and LLM information"""

    # Core response data
    package: Optional[dict] = None
    processing_time: float = 0.0

    # Enhanced metadata
    validation_results: Optional[List[BaseValidationResult]] = None

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "status": "success",
                "message": "Package operation completed successfully",
                "timestamp": "2024-01-01T12:00:00Z",
                "request_id": "req_123456789",
                "package": {
                    "name": "test-package",
                    "version": "1.0.0",
                    "status": "built",
                },
                "processing_time": 2.5,
                "llm_used": True,
                "llm_provider": "anthropic",
                "llm_cost": 0.025,
                "data": {},
                "metadata": {},
            }
        }
    )


class PackageMetadataResponse(BaseModel):
    """Response model for package metadata"""

    name: str
    version: str
    package_path: str

    created_at: Optional[str] = None
    size: Optional[int] = None
    checksum: Optional[str] = None
    metadata: Dict[str, Any] = Field(default_factory=dict)


class PackageListResponse(BaseModel):
    """Response model for listing packages"""

    packages: List[PackageMetadataResponse]
    total: int
    page: int
    page_size: int


class PackageVerificationResponse(BaseModel):
    """Response model for package verification"""

    valid: bool
    checksum_match: bool

    errors: List[str] = Field(default_factory=list)
    warnings: List[str] = Field(default_factory=list)
    metadata: Dict[str, Any] = Field(default_factory=dict)


class PackagePushResponse(BaseModel):
    """Response model for package push operations"""

    success: bool
    message: str

    remote_path: Optional[str] = None
    metadata: Dict[str, Any] = Field(default_factory=dict)


class PackagePullResponse(BaseModel):
    """Response model for package pull operations"""

    success: bool
    message: str

    local_path: Optional[str] = None
    metadata: Optional[PackageMetadataResponse] = None


# ---------------------------------------------------------------------------
# Envelopes for the package routes (#373)
#
# Derived from goldens in ``tests/api/test_package_response_contract.py``, not
# from reading the handlers. Note that ``PackageMetadataResponse`` above is a
# different thing despite the name — it is the push/pull payload, and does not
# describe what these routes return.
# ---------------------------------------------------------------------------


class PackageBuildOptions(BaseModel):
    """The switches a build was run with, echoed back on its metadata."""

    include_design_files: bool
    include_manufacturing_files: bool
    include_making_instructions: bool
    include_software: bool
    include_parts: bool
    include_operating_instructions: bool
    include_quality_instructions: bool
    include_risk_assessment: bool
    include_schematics: bool
    include_tool_settings: bool
    verify_downloads: bool
    max_concurrent_downloads: int
    output_dir: Optional[str] = None


class PackageFileInfo(BaseModel):
    """One file inside a package, as recorded at build time."""

    original_url: str
    local_path: str
    content_type: Optional[str] = None
    size_bytes: int
    checksum_sha256: str
    downloaded_at: Optional[str] = None
    file_type: Optional[str] = None
    part_name: Optional[str] = None


class PackageMetadataPayload(BaseModel):
    """``PackageMetadata.to_dict()`` — what build and metadata both return."""

    package_name: str
    version: str
    okh_manifest_id: str
    build_timestamp: str
    ohm_version: str
    total_files: int
    total_size_bytes: int
    file_inventory: List[PackageFileInfo]
    build_options: PackageBuildOptions
    package_path: str


class PackageMetadataData(BaseModel):
    """The ``data`` payload of the metadata and build routes."""

    metadata: PackageMetadataPayload


class PackageMetadataEnvelope(SuccessResponse):
    """Envelope for ``GET /api/package/{org}/{project}/{version}``."""

    data: PackageMetadataData


class PackageBuildEnvelope(SuccessResponse):
    """Envelope for ``POST /api/package/build/{manifest_id}``."""

    data: PackageMetadataData


class PackageIntegrityResult(BaseModel):
    """What ``_verify_package_integrity`` reports about files on disk."""

    valid: bool
    package_name: str
    version: str
    total_files: int
    total_size_bytes: int
    # Always constructed by `_verify_package_integrity`, so required.
    missing_files: List[str]
    corrupted_files: List[str]
    extra_files: List[str]


class PackageVerifyData(BaseModel):
    """The ``data`` payload of the verify route."""

    verification: PackageIntegrityResult


class PackageVerifyEnvelope(SuccessResponse):
    """Envelope for ``GET /api/package/{org}/{project}/{version}/verify``."""

    data: PackageVerifyData


class PinRecord(BaseModel):
    """A certified snapshot of a package version's content hashes."""

    pinned_at: str
    pinned_by: str
    manifest_content_hash: str
    # Keyed by path within the package, so a map rather than a fixed shape.
    # Required, not defaulted: `create_pin_record` always writes it, and a
    # default here would make it optional in the generated client, forcing
    # callers to null-check a field that is always present.
    file_hashes: Dict[str, str]
    note: Optional[str] = None


class PackagePinData(BaseModel):
    """The ``data`` payload of the pin route."""

    pin_record: PinRecord


class PackagePinEnvelope(SuccessResponse):
    """Envelope for ``POST /api/package/{org}/{project}/{version}/pin``."""

    data: PackagePinData


class PackageVerifyPinData(BaseModel):
    """Whether a pinned package still matches its pin, and what moved."""

    verified: bool
    changed_files: List[str]


class PackageVerifyPinEnvelope(SuccessResponse):
    """Envelope for ``GET /api/package/{org}/{project}/{version}/verify-pin``."""

    data: PackageVerifyPinData


class SignatureRecord(BaseModel):
    """The detached signature written beside a package's file manifest."""

    signed_by: str
    signature: str
    signed_at: str
    algorithm: str


class PackageVerifySignatureData(BaseModel):
    """The ``data`` payload of the signature-verification route."""

    valid: bool
    signature_record: SignatureRecord


class PackageVerifySignatureEnvelope(SuccessResponse):
    """Envelope for ``.../verify-signature``."""

    data: PackageVerifySignatureData


class PackageDeleteEnvelope(SuccessResponse):
    """Envelope for ``DELETE /api/package/{org}/{project}/{version}``.

    ``data`` is empty by design — the message carries the outcome — so this
    declares the envelope and nothing more.
    """

    data: Dict[str, Any] = Field(default_factory=dict)


class RemotePackageEntry(BaseModel):
    """One package version found in remote storage."""

    package_name: str
    version: str
    org: str
    project: str
    last_modified: Optional[str] = None
    size: int = 0


class PackageRemoteData(BaseModel):
    """The ``data`` payload of the remote listing."""

    packages: List[RemotePackageEntry]
    total: int


class PackageRemoteEnvelope(SuccessResponse):
    """Envelope for ``GET /api/package/remote``."""

    data: PackageRemoteData
