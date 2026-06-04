"""Regression tests for storage_config._env quote-stripping.

docker run --env-file passes values verbatim (quotes included), while
python-dotenv (docker-compose, load_dotenv) strips them. _env() must
produce identical output from both styles.
"""

import os

import pytest

from src.config.storage_config import (
    MissingCredentialsError,
    _env,
    get_azure_credentials,
    get_default_storage_config,
)


class TestEnvHelper:
    def test_plain_value_unchanged(self, monkeypatch):
        monkeypatch.setenv("_TEST_KEY", "plainvalue")
        assert _env("_TEST_KEY") == "plainvalue"

    def test_double_quoted_value_stripped(self, monkeypatch):
        monkeypatch.setenv("_TEST_KEY", '"quotedvalue"')
        assert _env("_TEST_KEY") == "quotedvalue"

    def test_single_quoted_value_stripped(self, monkeypatch):
        monkeypatch.setenv("_TEST_KEY", "'quotedvalue'")
        assert _env("_TEST_KEY") == "quotedvalue"

    def test_whitespace_stripped(self, monkeypatch):
        monkeypatch.setenv("_TEST_KEY", "  value  ")
        assert _env("_TEST_KEY") == "value"

    def test_missing_key_returns_none(self, monkeypatch):
        monkeypatch.delenv("_TEST_KEY", raising=False)
        assert _env("_TEST_KEY") is None

    def test_missing_key_returns_default(self, monkeypatch):
        monkeypatch.delenv("_TEST_KEY", raising=False)
        assert _env("_TEST_KEY", "fallback") == "fallback"

    def test_empty_after_stripping_returns_none(self, monkeypatch):
        monkeypatch.setenv("_TEST_KEY", '""')
        assert _env("_TEST_KEY") is None


class TestGetAzureCredentials:
    def test_quoted_values_produce_clean_credentials(self, monkeypatch):
        """docker run --env-file passes 'AZURE_STORAGE_ACCOUNT="myaccount"' verbatim."""
        monkeypatch.setenv("AZURE_STORAGE_ACCOUNT", '"myaccount"')
        monkeypatch.setenv("AZURE_STORAGE_KEY", '"mybase64key=="')
        creds = get_azure_credentials()
        assert creds["account_name"] == "myaccount"
        assert creds["account_key"] == "mybase64key=="

    def test_unquoted_values_unchanged(self, monkeypatch):
        monkeypatch.setenv("AZURE_STORAGE_ACCOUNT", "myaccount")
        monkeypatch.setenv("AZURE_STORAGE_KEY", "mybase64key==")
        creds = get_azure_credentials()
        assert creds["account_name"] == "myaccount"
        assert creds["account_key"] == "mybase64key=="

    def test_missing_credentials_raise(self, monkeypatch):
        monkeypatch.delenv("AZURE_STORAGE_ACCOUNT", raising=False)
        monkeypatch.delenv("AZURE_STORAGE_KEY", raising=False)
        with pytest.raises(MissingCredentialsError):
            get_azure_credentials()


class TestGetDefaultStorageConfig:
    def test_quoted_storage_provider_resolved(self, monkeypatch):
        """STORAGE_PROVIDER='\"local\"' should still resolve to the local provider."""
        monkeypatch.setenv("STORAGE_PROVIDER", '"local"')
        monkeypatch.setenv("LOCAL_STORAGE_PATH", "storage")
        config = get_default_storage_config()
        assert config.provider == "local"

    def test_quoted_container_name_stripped(self, monkeypatch):
        monkeypatch.setenv("STORAGE_PROVIDER", "azure_blob")
        monkeypatch.setenv("AZURE_STORAGE_ACCOUNT", '"myaccount"')
        monkeypatch.setenv("AZURE_STORAGE_KEY", '"mybase64key=="')
        monkeypatch.setenv("AZURE_STORAGE_CONTAINER", '"mycontainer"')
        config = get_default_storage_config()
        assert config.bucket_name == "mycontainer"
        assert config.credentials["account_name"] == "myaccount"
