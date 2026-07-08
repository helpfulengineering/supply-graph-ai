"""Characterization tests for the typed config schema (Slice 1).

These pin the schema's behaviour to the pre-migration semantics of
``settings.py`` / ``storage_config.py``: quote-stripping, per-environment TOML
layering (env overrides file), CORS resolution, OKW source resolution, and
environment normalization.
"""

import pytest

import src.config.schema as schema_mod
from src.config.schema import (
    Settings,
    deploy_env_vars,
    enforce_startup_config,
    frontend_deploy_env_vars,
    get_settings,
    resolve_cors_origins,
    storage_config_problems,
)

# Slice-1 env vars that must be neutralized for deterministic tests (the
# developer's .env is loaded at import time and would otherwise leak in).
_SLICE1_ENV = (
    "ENVIRONMENT",
    "STORAGE_PROVIDER",
    "AZURE_STORAGE_ACCOUNT",
    "AZURE_STORAGE_CONTAINER",
    "AZURE_STORAGE_KEY",
    "OKW_SOURCE",
    "CORS_ORIGINS",
)


@pytest.fixture
def clean_env(monkeypatch):
    for key in _SLICE1_ENV:
        monkeypatch.delenv(key, raising=False)
    return monkeypatch


class TestTomlLayering:
    def test_development_defaults_from_toml(self, clean_env):
        s = get_settings()
        assert s.environment == "development"
        assert s.storage_provider == "local"

    def test_production_target_from_toml(self, clean_env):
        clean_env.setenv("ENVIRONMENT", "production")
        s = get_settings()
        assert s.storage_provider == "azure_blob"
        assert s.azure_storage_account == "projdatablobstorage"
        assert s.azure_storage_container == "production"

    def test_env_overrides_toml(self, clean_env):
        clean_env.setenv("ENVIRONMENT", "production")
        clean_env.setenv("AZURE_STORAGE_CONTAINER", "override-container")
        assert get_settings().azure_storage_container == "override-container"

    def test_unknown_environment_has_no_toml_but_still_loads(self, clean_env):
        clean_env.setenv("ENVIRONMENT", "does-not-exist")
        s = get_settings()
        assert s.environment == "does-not-exist"
        assert s.storage_provider == "local"  # field default (no file)


class TestQuoteStripping:
    def test_quoted_env_values_stripped(self, clean_env):
        clean_env.setenv("STORAGE_PROVIDER", '"azure_blob"')
        clean_env.setenv("AZURE_STORAGE_ACCOUNT", '"myaccount"')
        clean_env.setenv("AZURE_STORAGE_CONTAINER", "'mycontainer'")
        s = get_settings()
        assert s.storage_provider == "azure_blob"
        assert s.azure_storage_account == "myaccount"
        assert s.azure_storage_container == "mycontainer"

    def test_empty_quoted_value_becomes_none(self, clean_env):
        clean_env.setenv("AZURE_STORAGE_CONTAINER", '""')
        assert get_settings().azure_storage_container is None


class TestEnvironmentNormalization:
    def test_default_is_development(self, clean_env):
        assert get_settings().environment == "development"

    def test_uppercase_lowercased(self, clean_env):
        clean_env.setenv("ENVIRONMENT", "PRODUCTION")
        assert get_settings().environment == "production"

    def test_whitespace_stripped(self, clean_env):
        clean_env.setenv("ENVIRONMENT", "  Test  ")
        assert get_settings().environment == "test"


class TestOkwSourceResolution:
    def test_unset_defaults_to_union(self, clean_env):
        # #240: unset resolves to union (storage ∪ MoM), not storage.
        assert get_settings().okw_source_resolved == "union"

    def test_explicit_storage(self, clean_env):
        clean_env.setenv("OKW_SOURCE", "storage")
        assert get_settings().okw_source_resolved == "storage"

    def test_explicit_mom(self, clean_env):
        clean_env.setenv("OKW_SOURCE", "mom")
        assert get_settings().okw_source_resolved == "mom"

    def test_explicit_union(self, clean_env):
        clean_env.setenv("OKW_SOURCE", "union")
        assert get_settings().okw_source_resolved == "union"

    def test_unknown_falls_back_to_union(self, clean_env):
        clean_env.setenv("OKW_SOURCE", "nonsense")
        assert get_settings().okw_source_resolved == "union"

    def test_empty_string_resolves_to_union(self, clean_env):
        clean_env.setenv("OKW_SOURCE", "")
        assert get_settings().okw_source_resolved == "union"

    def test_tristate_distinguishes_unset_from_storage(self, clean_env):
        # Raw field preserves the None-vs-"storage" distinction for #240.
        assert get_settings().okw_source is None
        clean_env.setenv("OKW_SOURCE", "storage")
        assert get_settings().okw_source == "storage"


class TestCorsResolution:
    def test_pure_resolver_dev_unset_allows_all(self):
        assert resolve_cors_origins(None, "development") == ["*"]

    def test_pure_resolver_prod_unset_denies_all(self):
        assert resolve_cors_origins(None, "production") == []

    def test_pure_resolver_explicit_wildcard(self):
        assert resolve_cors_origins("*", "production") == ["*"]

    def test_pure_resolver_comma_list(self):
        assert resolve_cors_origins("https://a.com, https://b.com ", "production") == [
            "https://a.com",
            "https://b.com",
        ]

    def test_pure_resolver_empty_string_dev(self):
        assert resolve_cors_origins("   ", "development") == ["*"]

    def test_schema_dev_unset(self, clean_env):
        assert get_settings().cors_allow_origins == ["*"]

    def test_schema_prod_unset(self, clean_env):
        clean_env.setenv("ENVIRONMENT", "production")
        assert get_settings().cors_allow_origins == []

    def test_schema_comma_list(self, clean_env):
        clean_env.setenv("CORS_ORIGINS", "https://x.io,https://y.io")
        assert get_settings().cors_allow_origins == ["https://x.io", "https://y.io"]


class TestInitOverride:
    def test_init_kwargs_win(self, clean_env):
        # init > env > toml precedence
        clean_env.setenv("STORAGE_PROVIDER", "azure_blob")
        assert Settings(storage_provider="gcs").storage_provider == "gcs"


class TestStartupPosture:
    def test_azure_complete_has_no_problems(self, clean_env):
        s = Settings(
            storage_provider="azure_blob",
            azure_storage_account="a",
            azure_storage_container="c",
            azure_storage_key="k",
        )
        assert storage_config_problems(s) == []

    def test_azure_missing_fields_reported(self, clean_env):
        s = Settings(
            storage_provider="azure_blob",
            azure_storage_account="a",
            azure_storage_container=None,
            azure_storage_key=None,
        )
        problems = storage_config_problems(s)
        assert any("AZURE_STORAGE_CONTAINER" in p for p in problems)
        assert any("AZURE_STORAGE_KEY" in p for p in problems)

    def test_local_has_no_problems(self, clean_env):
        assert storage_config_problems(Settings(storage_provider="local")) == []

    def test_unknown_provider_reported(self, clean_env):
        assert storage_config_problems(Settings(storage_provider="floppy-disk"))

    def test_production_hard_fails_on_problem(self, clean_env):
        s = Settings(environment="production", storage_provider="azure_blob")
        with pytest.raises(RuntimeError, match="Invalid production configuration"):
            enforce_startup_config(s)

    def test_development_warns_not_raises(self, clean_env):
        s = Settings(environment="development", storage_provider="azure_blob")
        # Returns the problems (degraded) instead of raising.
        assert enforce_startup_config(s)

    def test_clean_config_returns_empty(self, clean_env):
        s = Settings(environment="production", storage_provider="local")
        assert enforce_startup_config(s) == []


class TestDeployEnvVars:
    def test_production_applies_storage_target(self):
        env = deploy_env_vars("production")
        assert env["STORAGE_PROVIDER"] == "azure_blob"
        assert env["AZURE_STORAGE_ACCOUNT"] == "projdatablobstorage"
        assert env["AZURE_STORAGE_CONTAINER"] == "production"

    def test_development_is_local(self):
        assert deploy_env_vars("development") == {"STORAGE_PROVIDER": "local"}

    def test_missing_environment_returns_empty(self):
        assert deploy_env_vars("does-not-exist") == {}

    def test_keys_are_uppercased_env_names(self):
        # TOML uses snake_case; deploy needs upper-case env-var names.
        assert all(k == k.upper() for k in deploy_env_vars("production"))

    def test_secret_keys_are_refused(self, tmp_path, monkeypatch):
        # A secret accidentally placed in a per-env file must never be deployed.
        (tmp_path / "sneaky.toml").write_text(
            'storage_provider = "azure_blob"\n'
            'azure_storage_key = "leaked-secret-key"\n',
            encoding="utf-8",
        )
        monkeypatch.setattr(schema_mod, "_CONFIG_ENV_DIR", tmp_path)
        env = deploy_env_vars("sneaky")
        assert env == {"STORAGE_PROVIDER": "azure_blob"}
        assert "AZURE_STORAGE_KEY" not in env

    def test_frontend_table_does_not_leak_into_backend_env(self):
        # The [frontend] table is another service's deploy config; the backend
        # container must not receive it as a FRONTEND / API_UPSTREAM_URL var.
        env = deploy_env_vars("production")
        assert "FRONTEND" not in env
        assert "API_UPSTREAM_URL" not in env
        assert env["STORAGE_PROVIDER"] == "azure_blob"


class TestFrontendDeployEnvVars:
    def test_production_frontend_config(self):
        env = frontend_deploy_env_vars("production")
        assert env["API_UPSTREAM_URL"].startswith("https://openhardwaremanager")
        assert "/v1" not in env["API_UPSTREAM_URL"]  # origin only, proxy adds /v1
        assert env["PORT"] == "8080"

    def test_keys_are_uppercased_env_names(self):
        assert all(k == k.upper() for k in frontend_deploy_env_vars("production"))

    def test_absent_table_returns_empty(self):
        # test.toml intentionally has no [frontend] table (no frontend deploy).
        assert frontend_deploy_env_vars("test") == {}

    def test_missing_environment_returns_empty(self):
        assert frontend_deploy_env_vars("does-not-exist") == {}
