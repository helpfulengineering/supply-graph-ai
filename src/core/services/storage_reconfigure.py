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
from ..storage.manager import StorageManager
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


async def ensure_configured(service: StorageService) -> None:
    """Configure the service from the instance's effective configuration.

    A long-running API process has already done this at boot. A CLI process has
    not: it starts, configures nothing, and would report that there is no
    storage to migrate from — describing the process rather than the instance.

    Uses the same precedence as boot, persisted over environment, so the CLI
    acts on the backend the instance actually uses rather than on whatever the
    shell happens to export.
    """
    if service.manager is not None:
        return

    config = load_config() or getattr(settings, "STORAGE_CONFIG", None)
    if config is None:
        return
    await service.configure(config)


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


@dataclass
class RestartPendingInfo:
    """Whether a running API's live backend disagrees with the saved one (#545).

    Only meaningful while an API is actually running: with none running (marker
    absent or stale), the saved configuration is simply what the next boot will
    apply, and there is nothing "pending" about that.
    """

    pending: bool
    live_provider: Optional[str] = None
    live_bucket: Optional[str] = None
    saved_provider: Optional[str] = None
    saved_bucket: Optional[str] = None
    #: When the live backend became live — the running API's own start time,
    #: from its marker. Not "since the divergence": nothing persists when a
    #: saved configuration changed, only when the process serving the old one
    #: started.
    since: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "pending": self.pending,
            "live_provider": self.live_provider,
            "live_bucket": self.live_bucket,
            "saved_provider": self.saved_provider,
            "saved_bucket": self.saved_bucket,
            "since": self.since,
        }


def restart_pending_info() -> RestartPendingInfo:
    """Read-only: never touches the marker or the saved configuration, just
    compares them. Works identically from the CLI or the API process, because
    both read the same on-disk marker rather than in-memory state — the CLI has
    no other way to know what a separate API process is actually serving.
    """
    from . import storage_liveness

    live = storage_liveness.read()
    if live.status != storage_liveness.LivenessStatus.RUNNING:
        return RestartPendingInfo(pending=False)

    saved = load_config() or getattr(settings, "STORAGE_CONFIG", None)
    if saved is None:
        return RestartPendingInfo(
            pending=False,
            live_provider=live.provider,
            live_bucket=live.bucket,
            since=live.started_at,
        )

    pending = live.provider != saved.provider or live.bucket != saved.bucket_name
    return RestartPendingInfo(
        pending=pending,
        live_provider=live.provider,
        live_bucket=live.bucket,
        saved_provider=saved.provider,
        saved_bucket=saved.bucket_name,
        since=live.started_at,
    )


def _pending_message(pending: RestartPendingInfo) -> str:
    return (
        f"A restart is already pending: the API has been serving "
        f"{pending.live_provider} ({pending.live_bucket}) since {pending.since}, "
        f"but the saved configuration is {pending.saved_provider} "
        f"({pending.saved_bucket}). Restart the API to apply that change before "
        "switching again — one change at a time, so a second switch cannot be "
        "lost underneath the first."
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
        StorageReconfigureError: the candidate was rejected, the commit
            failed and the previous configuration was restored, or a restart
            is already pending from an earlier switch (#545 D7).
    """
    pending = restart_pending_info()
    if pending.pending:
        raise StorageReconfigureError(_pending_message(pending))

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

    # A no-op in a process with no marker (the CLI never starts one); in the
    # API process this keeps the liveness marker from reporting the backend
    # this process just left (#539 D9, #544).
    from . import storage_liveness

    storage_liveness.refresh_backend(candidate.provider, candidate.bucket_name)

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


# ---------------------------------------------------------------------------
# Switch modes (#381)
#
# #377 shipped one answer to "what happens to the data already there": leave
# it. These are the other two. The mode is the caller's explicit choice, and
# the default stays `abandon` so nothing changes for an existing caller.
# ---------------------------------------------------------------------------

MODE_ABANDON = "abandon"
MODE_MIGRATE = "migrate"
MODE_ABANDON_AND_WIPE = "abandon_and_wipe"
SWITCH_MODES = (MODE_ABANDON, MODE_MIGRATE, MODE_ABANDON_AND_WIPE)

_WIPE_RETIRED = (
    "The combined switch-and-wipe mode (abandon_and_wipe) has been retired: run from "
    "a separate process it erased the old storage while a running API was still "
    "serving from it, and the API had not been told to stop. Switch first (mode "
    "abandon), restart the API if you switched from the command line, confirm the "
    "node is healthy on the new storage, then delete the old data yourself; a "
    "guarded `ohm storage wipe` is planned (#547). Nothing was changed."
)
_MIGRATE_OVER_API_RETIRED = (
    "Storage migration over the API has been retired: the background job could not "
    "find the storage it was meant to copy from, so it never worked. Run "
    "`ohm storage config set --mode migrate` on the node instead. Nothing was "
    "changed."
)


def retired_switch_mode_message(mode: str, *, via_api: bool) -> Optional[str]:
    """Why a switch mode is refused, or None when it is still supported.

    One place, so the API and the CLI cannot drift apart on what they say. The CLI
    still offers `migrate`; only the API's job version was retired.
    """
    if mode == MODE_ABANDON_AND_WIPE:
        return _WIPE_RETIRED
    if mode == MODE_MIGRATE and via_api:
        return _MIGRATE_OVER_API_RETIRED
    return None


def build_candidate(
    provider: str,
    bucket: str,
    region: Optional[str] = None,
    endpoint_url: Optional[str] = None,
    credentials: Optional[Dict[str, str]] = None,
) -> StorageConfig:
    """Validate the shape of a requested configuration and build it.

    Separated from :func:`reconfigure_storage` so the migration job can reuse
    exactly the same checks in the worker, rather than a second copy that
    drifts.
    """
    credentials = {k: v for k, v in (credentials or {}).items() if v}
    _validate_credentials(provider, credentials)
    return StorageConfig(
        provider=provider,
        bucket_name=bucket,
        region=region,
        credentials=credentials,
        endpoint_url=endpoint_url,
    )


async def migrate_and_switch(
    service: StorageService,
    candidate: StorageConfig,
    progress: Optional[Any] = None,
) -> Dict[str, Any]:
    """Copy everything to ``candidate``, verify it, and only then switch.

    The instance keeps serving from the old backend for the whole copy. A
    migration that fails partway — or is abandoned — leaves a working instance
    on its original storage and a partial copy on the destination, which is
    recoverable; the reverse is not.
    """
    from .storage_setup import StorageSetupError, setup_storage
    from .storage_transfer import copy_all_objects

    # Checked again, redundantly, inside reconfigure_storage() at the end —
    # this copy is checked here too so a pending restart fails before a
    # possibly long copy runs at all, not after.
    pending = restart_pending_info()
    if pending.pending:
        raise StorageReconfigureError(_pending_message(pending))

    previous = service.manager.config if service.manager else None
    if previous is None:
        raise StorageReconfigureError("There is no current storage to migrate from.")

    # 1. Prove the destination before reading a single object.
    try:
        await setup_storage(candidate)
    except StorageSetupError as exc:
        raise StorageReconfigureError(str(exc)) from exc

    source = StorageManager(previous)
    destination = StorageManager(candidate)
    await source.connect()
    await destination.connect()

    try:
        report = await copy_all_objects(source, destination, progress=progress)
    finally:
        await source.disconnect()
        await destination.disconnect()

    if not report.ok:
        raise StorageReconfigureError(
            f"Migration did not complete: {len(report.failures)} object(s) "
            f"failed. The instance is still serving from "
            f"{previous.bucket_name!r} and nothing was switched. "
            f"First failures: {'; '.join(report.failures[:3])}"
        )

    # 2. Only now, with a verified copy, is it safe to swap.
    result = await reconfigure_storage(
        service,
        provider=candidate.provider,
        bucket=candidate.bucket_name,
        region=candidate.region,
        endpoint_url=candidate.endpoint_url,
        credentials=candidate.credentials,
    )
    result["mode"] = MODE_MIGRATE
    result["migration"] = report.to_dict()
    return result


# ---------------------------------------------------------------------------
# Standalone guarded wipe (#547)
#
# #543 retired the combined switch-and-wipe: run from a separate process it
# erased the backend a running API was still serving from. This restores the
# ability to erase an old backend, as its own explicit step, guarded against
# erasing anything a boot or a running process still needs.
# ---------------------------------------------------------------------------


def _wipe_refusal(reason: str) -> "StorageReconfigureError":
    return StorageReconfigureError(f"Refusing to wipe: {reason} Nothing was deleted.")


async def guarded_wipe(
    provider: str,
    bucket: str,
    wipe_confirm: str,
    dry_run: bool = False,
    credentials: Optional[Dict[str, str]] = None,
    region: Optional[str] = None,
    endpoint_url: Optional[str] = None,
) -> Dict[str, Any]:
    """Erase a backend's contents — but only once nothing live needs it.

    Refuses when the target is:

    - **pending** (#545): a restart is already owed elsewhere, and wiping
      anything while the node's own picture of its storage is out of date is
      one step from repeating #543's incident at a different layer.
    - the **saved configuration** — what the next boot applies.
    - the **environment-configured backend**, when there is no saved
      configuration (a fresh process without one falls back to it, so it is
      exactly as live as a saved one would be).
    - what a **running API's marker says it is live on** (#544), matched by
      provider and bucket. An unreadable or ambiguous marker refuses
      regardless of the target, the same fail-closed rule the marker itself
      follows: it must never look safer than a readable one. A *stale*
      marker does not refuse — that is what staleness means — but it is
      still there for `ohm storage status --forget` to clear by hand.

    Raises:
        StorageReconfigureError: the wipe was refused for one of the reasons
            above. Nothing was touched.
        WipeGuardError: ``wipe_confirm`` did not match ``bucket``.
    """
    from . import storage_liveness
    from .storage_transfer import wipe_storage

    credentials = {k: v for k, v in (credentials or {}).items() if v}
    _validate_credentials(provider, credentials)
    candidate = StorageConfig(
        provider=provider,
        bucket_name=bucket,
        region=region,
        credentials=credentials,
        endpoint_url=endpoint_url,
    )

    def _same(other: Optional[StorageConfig]) -> bool:
        return (
            other is not None
            and other.provider == candidate.provider
            and other.bucket_name == candidate.bucket_name
        )

    # Live-marker first, deliberately: whenever the marker is running and
    # readable, "not pending" (checked next) is only true when live already
    # equals saved — so a match here always also matches the saved-config
    # check below. Checking live first means the message names the sharper,
    # more concrete reason ("a running API is serving from this") rather
    # than the structurally-redundant "it's the saved configuration" one.
    live = storage_liveness.read()
    if live.status == storage_liveness.LivenessStatus.RUNNING:
        if live.provider is None and live.bucket is None:
            raise _wipe_refusal(
                "a running API's liveness marker is unreadable "
                f"({live.error}), so it cannot be ruled out as the backend a "
                "live process is serving from. Wait for it to go stale "
                "(~45s by default) and try again, or confirm independently "
                "that the process is dead."
            )
        if live.provider == candidate.provider and live.bucket == candidate.bucket_name:
            age = (
                f"{live.age_seconds:.1f}s"
                if live.age_seconds is not None
                else "unknown"
            )
            raise _wipe_refusal(
                f"a running API (heartbeat {age} old) is still serving from "
                f"{bucket!r}. Switch it elsewhere and restart first."
            )

    pending = restart_pending_info()
    if pending.pending:
        # Reuses the same explanation the switch guard gives — same
        # condition, same fix (restart first) — rather than a second copy of
        # "what pending means" that could drift from it.
        raise StorageReconfigureError(_pending_message(pending))

    saved = load_config()
    if _same(saved):
        raise _wipe_refusal(
            f"{bucket!r} is the saved storage configuration — the backend the "
            "node applies at its next boot. Switch away from it first (and "
            "restart, if you switched from the CLI), then wipe."
        )
    if saved is None and _same(getattr(settings, "STORAGE_CONFIG", None)):
        raise _wipe_refusal(
            f"{bucket!r} is the environment-configured backend — what a fresh "
            "process with no saved configuration would use. Set a saved "
            "configuration pointing elsewhere first, then wipe."
        )

    manager = StorageManager(candidate)
    await manager.connect()
    try:
        report = await wipe_storage(
            manager, candidate.bucket_name, wipe_confirm, dry_run=dry_run
        )
    finally:
        await manager.disconnect()

    return {
        "provider": candidate.provider,
        "bucket": candidate.bucket_name,
        "wipe": report.to_dict(),
    }
