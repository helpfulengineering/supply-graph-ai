"""Where storage configuration is persisted, and why it is not in storage (#377).

Every other credential OHM holds is written **into** the object store it
configures. Storage configuration cannot be: credentials for the new provider
would be written into the old one and orphaned the moment the switch takes
effect, leaving an instance that cannot reach the backend it is configured for
and cannot read the configuration that would tell it so.

So this is a small encrypted file on local disk, read at boot *before* the
storage service is configured. The installer mounts its directory as a volume,
which is what makes configuration survive a container replacement.

Credentials are encrypted with the same ``OHM_ENCRYPTION_*`` material as LLM
provider keys (#371), through the same ``CredentialManager``. Persisting
credentials under the built-in default salt and password is refused: the
default key is in the source tree, so encrypting with it is obfuscation, not
protection. A configuration carrying no credentials — ``local``, or a cloud
provider using ambient instance credentials — has nothing to protect and is
allowed either way, which is what keeps a development instance workable before
a secret has been minted.
"""

from __future__ import annotations

import json
import os
import stat
from pathlib import Path
from typing import Any, Dict, Optional

from ...config.llm_config import CredentialManager
from ..storage.base import StorageConfig
from ..utils.logging import get_logger

logger = get_logger(__name__)

_DIR_MODE = 0o700
_FILE_MODE = 0o600

#: Bumped only if the on-disk shape changes incompatibly.
SCHEMA_VERSION = 1


class StorageConfigStoreError(RuntimeError):
    """The configuration could not be persisted or read back."""


def config_path() -> Path:
    """Where the configuration file lives.

    ``OHM_STORAGE_CONFIG_PATH`` overrides it, which is how the installer points
    the file at a mounted volume.
    """
    override = os.getenv("OHM_STORAGE_CONFIG_PATH")
    if override and override.strip():
        return Path(override.strip()).expanduser()
    return Path.home() / ".ohm" / "storage-config.json"


def _write_secret(path: Path, text: str) -> None:
    """Write 0600 inside a 0700 directory, and repair modes if they drifted."""
    path.parent.mkdir(parents=True, exist_ok=True, mode=_DIR_MODE)
    if stat.S_IMODE(path.parent.stat().st_mode) != _DIR_MODE:
        path.parent.chmod(_DIR_MODE)
    path.write_text(text, encoding="utf-8")
    path.chmod(_FILE_MODE)


def _credential_manager() -> CredentialManager:
    return CredentialManager()


def save_config(config: StorageConfig) -> Path:
    """Persist ``config``, encrypting its credentials.

    Raises:
        StorageConfigStoreError: the configuration carries credentials and the
            encryption material is still the built-in default.
    """
    manager = _credential_manager()

    credentials = {k: v for k, v in (config.credentials or {}).items() if v}
    if credentials and manager.uses_default_encryption:
        raise StorageConfigStoreError(
            "Refusing to persist storage credentials under default encryption "
            "keys. Set OHM_ENCRYPTION_SALT and OHM_ENCRYPTION_PASSWORD (or "
            "OHM_ENCRYPTION_KEY) first — the default key ships in the source "
            "tree, so encrypting with it protects nothing."
        )

    payload: Dict[str, Any] = {
        "schema_version": SCHEMA_VERSION,
        "provider": config.provider,
        "bucket_name": config.bucket_name,
        "region": config.region,
        "endpoint_url": config.endpoint_url,
        # Encrypted individually rather than as one blob, so a future reader can
        # tell which keys are present without decrypting anything.
        "credentials": {
            name: manager.encrypt_credential(value)
            for name, value in credentials.items()
        },
    }

    path = config_path()
    try:
        _write_secret(path, json.dumps(payload, indent=2) + "\n")
    except OSError as exc:
        raise StorageConfigStoreError(
            f"Could not write storage configuration to {path}: {exc}"
        ) from exc
    logger.info("Storage configuration persisted to %s", path)
    return path


def load_config() -> Optional[StorageConfig]:
    """The persisted configuration, or ``None`` when there is not one.

    Never raises. This is called at boot before storage is configured, and a
    corrupt or unreadable file must not stop the process from starting on its
    environment configuration — a node that will not boot is worse than one
    running on the settings it was deployed with. The reason is logged.
    """
    path = config_path()
    if not path.exists():
        return None

    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        logger.error(
            "Ignoring unreadable storage configuration at %s: %s. "
            "Falling back to the environment.",
            path,
            exc,
        )
        return None

    version = payload.get("schema_version")
    if version != SCHEMA_VERSION:
        logger.error(
            "Ignoring storage configuration at %s: schema_version %r, expected "
            "%r. Falling back to the environment.",
            path,
            version,
            SCHEMA_VERSION,
        )
        return None

    try:
        manager = _credential_manager()
        credentials = {
            name: manager.decrypt_credential(value)
            for name, value in (payload.get("credentials") or {}).items()
        }
    except Exception as exc:  # noqa: BLE001 — boot must not depend on this
        logger.error(
            "Could not decrypt storage credentials at %s: %s. The encryption "
            "material has probably changed. Falling back to the environment.",
            path,
            exc,
        )
        return None

    return StorageConfig(
        provider=payload.get("provider", "local"),
        bucket_name=payload.get("bucket_name") or "storage",
        region=payload.get("region"),
        credentials=credentials,
        endpoint_url=payload.get("endpoint_url"),
    )


def clear_config() -> bool:
    """Remove the persisted configuration. True when a file was removed."""
    path = config_path()
    try:
        path.unlink()
        return True
    except FileNotFoundError:
        return False
    except OSError as exc:
        raise StorageConfigStoreError(
            f"Could not remove storage configuration at {path}: {exc}"
        ) from exc
