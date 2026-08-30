"""Response models for the file-type taxonomy routes.

Derived from payloads captured in ``tests/api/golden/`` before these models
existed, not from reading the route bodies: ``response_model`` filters, so a
model written from the code can silently drop a field a client reads. See
``docs/architecture/api-response-contracts.md``.
"""

from __future__ import annotations

from typing import List, Optional

from pydantic import BaseModel

from ..base import SuccessResponse


class FileTypeDefinition(BaseModel):
    """One canonical file type and how it is recognised."""

    canonical_id: str
    display_name: str
    extensions: List[str]
    mime_types: List[str]
    # Required but nullable, not optional: every item in the payload carries
    # all three keys (verified across all 32 in the golden). A default would
    # make them optional in the schema, and the client would then have to
    # handle an `undefined` the route never sends.
    okh_role: Optional[str]
    parent: Optional[str]
    render_tier: Optional[str]


class FileTypeIndexData(BaseModel):
    total: int
    #: Path to the YAML the taxonomy came from, or "built-in".
    source: str
    file_types: List[FileTypeDefinition]


class FileTypeIndexResponse(SuccessResponse):
    data: FileTypeIndexData


class FileTypeValidationData(BaseModel):
    valid: bool
    total_file_types: int
    errors: List[str]
    source: str


class FileTypeValidationResponse(SuccessResponse):
    data: FileTypeValidationData
