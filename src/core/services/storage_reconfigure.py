"""Switch storage providers without being able to break the instance (#377).

``StorageService.configure`` is not safe to call from a request handler. It
does two things that are right for boot and wrong here: it **swallows
connection failures** so the API can start degraded, and it **replaces the
active manager before connecting**. Called naively from an endpoint, a mistyped
credential returns success and leaves the instance with no working storage and
no route back — the endpoint that would fix it needs storage-backed admin
credentials to authenticate.

So the order is validate, then commit:

1. Build the candidate configuration.
2. Prove it with :func:`~src.core.services.storage_setup.setup_storage` — a
   real connect, a write/read round trip, and the directory structure
   validated if present or initialized if not. Setup *is* part of
   configuration, not a step after it.
3. Only then persist it and swap the live service.

A failure at step 1 or 2 leaves the instance serving exactly as it was, because
nothing has been touched yet. A failure at step 3 restores the previous
configuration before raising.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, List, Optional

from ...config import settings
from ..storage.base import StorageConfig
from ..utils.logging import get_logger
from .storage_config_store import load_config, save_config
from .storage_service import StorageService
from .storage_setup import StorageSetupError, setup_storage

logger = get_logger(__name__)

#: Credential keys that may be supplied per provider. Anything else is
#: rejected rather than silently dropped, so a typo in a credential name is a
#: clear error instead of an authentication failure later.
PROVIDER_CREDENTIALS = {
    "local": set(),
    "gcs": {"project_id", "credentials_path", "credentials_json"},
    "azure_blob": {"account_name", "account_key", "connection_string"},
    "aws_s3": {"access_key_id", "secret_access_key", "session_token"},
}


class StorageReconfigureError(RuntimeError):
    """The new configuration was rejected. The instance is unchanged."""


@dataclass
class StorageConfigView:
    """The current configuration, with nothing secret in it.

    Credential *names* are reported but never their values: an operator needs
    to know whether an account key is set, and never needs it echoed back.
    """

    provider: str
    bucket: str
    region: Optional[str]
    endpoint_url: Optional[str]
    credential_names: List[str]
    persisted: bool
    configured: bool
    #: Where the reported configuration came from: the connected service
    #: ("live"), the persisted file ("persisted"), or the environment
    #: ("environment"). A short-lived CLI process never configures the storage
    #: service, so without this it would report "unknown" for an instance that
    #: is configured perfectly well.
    source: str

    def to_dict(self) -> Dict[str, Any]:
        return {
            "provider": self.provider,
            "bucket": self.bucket,
            "region": self.region,
            "endpoint_url": self.endpoint_url,
            "credential_names": sorted(self.credential_names),
            "persisted": self.persisted,
            "configured": self.configured,
            "source": self.source,
        }


def _validate_credentials(provider: str, credentials: Dict[str, str]) -> None:
    allowed = PROVIDER_CREDENTIALS.get(provider)
    if allowed is None:
        raise StorageReconfigureError(
            f"Unknown storage provider '{provider}'. "
            f"Expected one of: {', '.join(sorted(PROVIDER_CREDENTIALS))}."
        )
    unexpected = sorted(set(credentials) - allowed)
    if unexpected:
        raise StorageReconfigureError(
            f"Unexpected credential(s) for provider '{provider}': "
            f"{', '.join(unexpected)}. "
            f"Accepted: {', '.join(sorted(allowed)) or 'none'}."
        )


async def current_config(service: StorageService) -> StorageConfigView:
    """What this instance is configured with, and where that came from.

    Falls back from the connected service to the persisted file to the
    environment. The fallback is not cosmetic: the API asks a long-running
    process whose service is configured, while the CLI asks a process that has
    just started and configured nothing. Reporting "unknown" to the CLI would
    describe the process, not the instance.
    """
    stored = load_config()

    config = service.manager.config if service.manager else None
    source = "live"
    if config is None:
        config = stored
        source = "persisted"
    if config is None:
        config = getattr(settings, "STORAGE_CONFIG", None)
        source = "environment"

    if config is None:
        return StorageConfigView(
            provider="unknown",
            bucket="",
            region=None,
            endpoint_url=None,
            credential_names=[],
            persisted=stored is not None,
            configured=False,
            source="none",
        )

    return StorageConfigView(
        provider=config.provider,
        bucket=config.bucket_name,
        region=config.region,
        endpoint_url=config.endpoint_url,
        credential_names=[k for k, v in (config.credentials or {}).items() if v],
        persisted=stored is not None,
        configured=bool(getattr(service, "_configured", False)),
        source=source,
    )


async def reconfigure_storage(
    service: StorageService,
    provider: str,
    bucket: str,
    region: Optional[str] = None,
    endpoint_url: Optional[str] = None,
    credentials: Optional[Dict[str, str]] = None,
) -> Dict[str, Any]:
    """Validate a new backend, then commit to it.

    Existing data is left where it is; this switches which backend the
    instance reads and writes. Migration and wiping are #381.

    Raises:
        StorageReconfigureError: the candidate was rejected, or the commit
            failed and the previous configuration was restored.
    """
    credentials = {k: v for k, v in (credentials or {}).items() if v}
    _validate_credentials(provider, credentials)

    candidate = StorageConfig(
        provider=provider,
        bucket_name=bucket,
        region=region,
        credentials=credentials,
        endpoint_url=endpoint_url,
    )

    # 1. Prove the candidate before anything is touched.
    try:
        setup = await setup_storage(candidate)
    except StorageSetupError as exc:
        raise StorageReconfigureError(str(exc)) from exc

    previous = service.manager.config if service.manager else None

    # 2. Persist before swapping. Persisting is the step most likely to fail
    #    for a reason unrelated to the backend — an unwritable volume, or
    #    default encryption material — and failing here leaves the instance
    #    running on the old provider rather than on a provider it will forget.
    save_config(candidate)

    # 3. Swap. `configure` swallows its own failures, so its outcome is read
    #    back rather than trusted.
    await service.configure(candidate)
    if not getattr(service, "_configured", False):
        if previous is not None:
            await service.configure(previous)
            save_config(previous)
        raise StorageReconfigureError(
            "The new backend verified but could not be activated; the previous "
            "configuration has been restored."
        )

    logger.info("Storage reconfigured to provider=%s bucket=%s", provider, bucket)
    return {
        "provider": candidate.provider,
        "bucket": candidate.bucket_name,
        "region": candidate.region,
        "verified": setup.verified,
        "prefixes_found": setup.prefixes_found,
        "prefixes_created": setup.prefixes_created,
        "previous_provider": previous.provider if previous else None,
        "previous_bucket": previous.bucket_name if previous else None,
    }
