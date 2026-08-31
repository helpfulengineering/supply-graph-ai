"""Storage configuration persists outside the storage it configures (#377).

Every other credential OHM holds is written into the object store. Storage
configuration cannot be: credentials for the new provider would be written into
the old one and orphaned the moment the switch takes effect, leaving an
instance that can neither reach its backend nor read the configuration that
would explain why.
"""

from __future__ import annotations

import json
import stat

import pytest

from src.core.services.storage_config_store import (
    SCHEMA_VERSION,
    StorageConfigStoreError,
    clear_config,
    config_path,
    load_config,
    save_config,
)
from src.core.storage.base import StorageConfig


@pytest.fixture(autouse=True)
def isolated_config(monkeypatch, tmp_path):
    monkeypatch.setenv("OHM_STORAGE_CONFIG_PATH", str(tmp_path / "cfg" / "store.json"))
    monkeypatch.setenv("OHM_ENCRYPTION_SALT", "unit-test-salt")
    monkeypatch.setenv("OHM_ENCRYPTION_PASSWORD", "unit-test-password")
    return tmp_path


def test_no_file_means_no_configuration():
    assert load_config() is None


def test_round_trip_preserves_everything_including_credentials():
    save_config(
        StorageConfig(
            provider="azure_blob",
            bucket_name="production",
            region="westeurope",
            credentials={"account_name": "acct", "account_key": "secret-value"},
        )
    )

    loaded = load_config()

    assert loaded.provider == "azure_blob"
    assert loaded.bucket_name == "production"
    assert loaded.region == "westeurope"
    assert loaded.credentials["account_key"] == "secret-value"


def test_credentials_are_not_written_in_plain_text():
    save_config(
        StorageConfig(
            provider="azure_blob",
            bucket_name="production",
            credentials={"account_key": "secret-value"},
        )
    )

    raw = config_path().read_text(encoding="utf-8")

    assert "secret-value" not in raw
    # The name is readable so a reader can see which keys exist without
    # decrypting anything.
    assert "account_key" in raw


def test_the_file_is_not_readable_by_anyone_else():
    save_config(StorageConfig(provider="local", bucket_name="/tmp/whatever"))

    path = config_path()
    assert stat.S_IMODE(path.stat().st_mode) == 0o600
    assert stat.S_IMODE(path.parent.stat().st_mode) == 0o700


def test_credentials_are_refused_under_default_encryption(monkeypatch):
    """The default key ships in the source tree; encrypting with it is theatre."""
    monkeypatch.delenv("OHM_ENCRYPTION_SALT", raising=False)
    monkeypatch.delenv("OHM_ENCRYPTION_PASSWORD", raising=False)
    monkeypatch.delenv("OHM_ENCRYPTION_KEY", raising=False)
    monkeypatch.delenv("LLM_ENCRYPTION_SALT", raising=False)
    monkeypatch.delenv("LLM_ENCRYPTION_PASSWORD", raising=False)
    monkeypatch.delenv("LLM_ENCRYPTION_KEY", raising=False)

    with pytest.raises(StorageConfigStoreError) as excinfo:
        save_config(
            StorageConfig(
                provider="azure_blob",
                bucket_name="production",
                credentials={"account_key": "secret-value"},
            )
        )

    assert "default encryption" in str(excinfo.value).lower()
    assert not config_path().exists()


def test_a_configuration_without_credentials_is_allowed_under_default_encryption(
    monkeypatch,
):
    """Otherwise a developer could not point local storage anywhere.

    There is nothing to protect in `provider=local, bucket=/path`, so refusing
    it would block the common case to guard against no risk.
    """
    monkeypatch.delenv("OHM_ENCRYPTION_SALT", raising=False)
    monkeypatch.delenv("OHM_ENCRYPTION_PASSWORD", raising=False)
    monkeypatch.delenv("OHM_ENCRYPTION_KEY", raising=False)
    monkeypatch.delenv("LLM_ENCRYPTION_SALT", raising=False)
    monkeypatch.delenv("LLM_ENCRYPTION_PASSWORD", raising=False)
    monkeypatch.delenv("LLM_ENCRYPTION_KEY", raising=False)

    save_config(StorageConfig(provider="local", bucket_name="/tmp/anywhere"))

    assert load_config().bucket_name == "/tmp/anywhere"


def test_a_corrupt_file_falls_back_rather_than_stopping_the_process():
    """Boot reads this. A node that will not start is worse than one on env."""
    path = config_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("{ this is not json", encoding="utf-8")

    assert load_config() is None


def test_a_future_schema_is_ignored_rather_than_misread():
    path = config_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps({"schema_version": SCHEMA_VERSION + 1, "provider": "gcs"}),
        encoding="utf-8",
    )

    assert load_config() is None


def test_credentials_encrypted_with_other_material_are_not_guessed_at(monkeypatch):
    """Rotating the encryption secret must not silently yield a broken config."""
    save_config(
        StorageConfig(
            provider="azure_blob",
            bucket_name="production",
            credentials={"account_key": "secret-value"},
        )
    )

    monkeypatch.setenv("OHM_ENCRYPTION_PASSWORD", "a-different-password")

    assert load_config() is None


def test_clear_removes_the_file():
    save_config(StorageConfig(provider="local", bucket_name="/tmp/whatever"))

    assert clear_config() is True
    assert load_config() is None
    assert clear_config() is False
