"""Storage configuration API models (#377).

Nothing here carries a credential *value*. The read endpoint reports which
credential names are set so an operator can see that an account key exists
without it being echoed back, and the write endpoint accepts them but never
returns them.
"""

from __future__ import annotations

from typing import Any, Dict, List, Literal, Optional

from pydantic import BaseModel, Field

from ..base import SuccessResponse


class StorageConfigData(BaseModel):
    """The configuration the instance is running on."""

    provider: str
    bucket: str
    region: Optional[str] = None
    endpoint_url: Optional[str] = None
    # Names only, never values. Required rather than defaulted: the service
    # always builds this list, and a Pydantic default makes the field optional
    # in the generated client, forcing callers to null-check something that is
    # always there.
    credential_names: List[str]
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
    # Optional with a None default rather than a defaulted literal, and that
    # is a compatibility decision: openapi-typescript renders a field with a
    # server-side default as *required in the body*, so declaring
    # `mode: Literal[...] = "abandon"` would make every existing caller of this
    # endpoint fail to compile for a field they neither know nor need. None
    # means abandon, which is what the endpoint did before this existed.
    mode: Optional[Literal["abandon", "migrate", "abandon_and_wipe"]] = Field(
        None,
        description=(
            "What happens to the data already in storage. 'abandon' leaves it "
            "where it is and switches (the default, and #377's behaviour). "
            "'migrate' and 'abandon_and_wipe' are retired and answer 400 with "
            "what to do instead; they remain in this list only so a caller "
            "following the old documentation gets that explanation."
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
    # Always built by the setup result, so required for the same reason.
    prefixes_found: List[str]
    prefixes_created: List[str]
    previous_provider: Optional[str] = None
    previous_bucket: Optional[str] = None

    #: Which mode ran. Only "abandon" now: the others are retired and refused
    #: before anything happens.
    mode: str = "abandon"


class StorageConfigureResponse(SuccessResponse):
    """Envelope for ``POST /api/storage/config``."""

    data: StorageConfigureData
