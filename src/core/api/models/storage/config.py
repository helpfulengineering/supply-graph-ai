"""Storage configuration API models (#377).

Nothing here carries a credential *value*. The read endpoint reports which
credential names are set so an operator can see that an account key exists
without it being echoed back, and the write endpoint accepts them but never
returns them.
"""

from __future__ import annotations

from typing import Dict, List, Optional

from pydantic import BaseModel, Field

from ..base import SuccessResponse


class StorageConfigData(BaseModel):
    """The configuration the instance is running on."""

    provider: str
    bucket: str
    region: Optional[str] = None
    endpoint_url: Optional[str] = None
    # Names only, never values.
    credential_names: List[str] = Field(default_factory=list)
    #: True when a configuration file is on disk, as opposed to the instance
    #: running on its environment settings.
    persisted: bool
    #: False when storage was configured but the connection failed — the app
    #: boots degraded rather than refusing to start.
    configured: bool
    #: "live", "persisted", "environment", or "none" — which of those the
    #: reported configuration was read from.
    source: str


class StorageFingerprint(BaseModel):
    """What the running app is actually connected to, plus object counts.

    Reported alongside the configuration because the two can disagree: the
    configuration is what was asked for, the fingerprint is what answered.
    Counts are ``None`` when storage could not be reached.
    """

    provider: Optional[str] = None
    account: Optional[str] = None
    container: Optional[str] = None
    okh_count: Optional[int] = None
    okw_count: Optional[int] = None
    error: Optional[str] = None


class StorageConfigView(BaseModel):
    """``data`` payload of the read endpoint."""

    config: StorageConfigData
    fingerprint: StorageFingerprint


class StorageConfigResponse(SuccessResponse):
    """Envelope for ``GET /api/storage/config``."""

    data: StorageConfigView


class StorageConfigureRequest(BaseModel):
    """A new backend to switch to.

    Existing data is left where it is. Moving or erasing it is #381.
    """

    provider: str = Field(..., description="local, gcs, azure_blob or aws_s3")
    bucket: str = Field(
        ..., min_length=1, description="Bucket, container, or local path"
    )
    region: Optional[str] = Field(None, description="Region for cloud providers")
    endpoint_url: Optional[str] = Field(
        None, description="Override endpoint, for S3-compatible backends"
    )
    credentials: Dict[str, str] = Field(
        default_factory=dict,
        description=(
            "Provider credentials. Names are checked against the provider, so "
            "a misspelled key is rejected rather than silently ignored."
        ),
    )


class StorageConfigureData(BaseModel):
    """What the switch did."""

    provider: str
    bucket: str
    region: Optional[str] = None
    #: Always true on success — the backend was proved with a write/read round
    #: trip before anything was committed.
    verified: bool
    prefixes_found: List[str] = Field(default_factory=list)
    prefixes_created: List[str] = Field(default_factory=list)
    previous_provider: Optional[str] = None
    previous_bucket: Optional[str] = None


class StorageConfigureResponse(SuccessResponse):
    """Envelope for ``POST /api/storage/config``."""

    data: StorageConfigureData
