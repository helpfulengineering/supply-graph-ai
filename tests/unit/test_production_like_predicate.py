"""One question — "is this a real deployment?" — asked the same way everywhere.

`ENVIRONMENT` used to decide two unrelated things: which config file to load, and
how strictly the application behaves. Only the first is a legitimate use of the
name. These tests pin the second onto a single derived predicate, and pin the
consequence that motivated it.
"""

from __future__ import annotations

import importlib
import sys
from pathlib import Path

import pytest

_REPO_ROOT = Path(__file__).resolve().parents[2]
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

from src.config.schema import (
    RELAXED_ENVIRONMENTS,
    Settings,
    is_production_like,
    resolve_cors_origins,
)

pytestmark = pytest.mark.unit


# --- Truth table -------------------------------------------------------------


@pytest.mark.parametrize("environment", sorted(RELAXED_ENVIRONMENTS))
def test_known_sandboxes_are_relaxed(environment):
    assert is_production_like(environment) is False


@pytest.mark.parametrize(
    "environment",
    ["production", "staging", "demo", "preprod", "qa", "anything-else"],
)
def test_everything_else_is_a_real_deployment(environment):
    """Fail CLOSED: a name nobody anticipated is strict, not lax.

    An opt-in 'strict' setting would reproduce the v0.10.6 bug the first time
    someone forgot it on a new environment.
    """
    assert is_production_like(environment) is True


@pytest.mark.parametrize("environment", ["PRODUCTION", " Staging ", "Development"])
def test_matching_ignores_case_and_surrounding_space(environment):
    expected = environment.strip().lower() not in RELAXED_ENVIRONMENTS
    assert is_production_like(environment) is expected


@pytest.mark.parametrize("environment", [None, "", "   "])
def test_missing_environment_is_treated_as_a_real_deployment(environment):
    """Unset is the most dangerous case, so it must not be the laxest."""
    assert is_production_like(environment) is True


def test_settings_exposes_the_same_answer():
    assert Settings(environment="staging").is_production_like is True
    assert Settings(environment="test").is_production_like is False


# --- The failure this exists to prevent --------------------------------------


def test_staging_now_demands_the_encryption_secrets_that_broke_v0_10_6(monkeypatch):
    """Regression: v0.10.6 crash-looped in production, staging booted clean.

    The worker died at import with "…_ENCRYPTION_SALT and …_ENCRYPTION_PASSWORD
    must be set in production" (the variables were LLM_-prefixed then; #371
    renamed them to OHM_ and kept the old names working). The staging rehearsal
    built to catch exactly that ran the same image happily, because the guard
    compared the environment to "production" and staging's was "staging".

    Staging must now fail the same way production does — that is the whole point.
    """
    monkeypatch.setenv("ENVIRONMENT", "staging")
    # Both spellings, since either configures it (#371) — clearing only one
    # would let the other satisfy the guard and the test would pass vacuously.
    for name in (
        "OHM_ENCRYPTION_SALT",
        "OHM_ENCRYPTION_PASSWORD",
        "OHM_ENCRYPTION_KEY",
        "LLM_ENCRYPTION_SALT",
        "LLM_ENCRYPTION_PASSWORD",
        "LLM_ENCRYPTION_KEY",
    ):
        monkeypatch.delenv(name, raising=False)

    llm_config = importlib.import_module("src.config.llm_config")

    with pytest.raises(ValueError, match="ENCRYPTION"):
        llm_config.CredentialManager()


def test_a_sandbox_still_boots_without_encryption_secrets(monkeypatch):
    """The relaxed environments must stay usable with no secrets at all."""
    monkeypatch.setenv("ENVIRONMENT", "development")
    monkeypatch.delenv("LLM_ENCRYPTION_SALT", raising=False)
    monkeypatch.delenv("LLM_ENCRYPTION_PASSWORD", raising=False)
    monkeypatch.delenv("LLM_ENCRYPTION_KEY", raising=False)

    llm_config = importlib.import_module("src.config.llm_config")

    llm_config.CredentialManager()  # must not raise


# --- The other strictness checks move together -------------------------------


def test_cors_denies_by_default_on_any_real_deployment():
    assert resolve_cors_origins(None, "production") == []
    assert resolve_cors_origins(None, "staging") == []
    assert resolve_cors_origins(None, "development") == ["*"]
    assert resolve_cors_origins(None, "test") == ["*"]


def test_startup_validation_hard_fails_on_any_real_deployment():
    """A misconfigured deployment must refuse to boot, not degrade quietly."""
    from src.config.schema import enforce_startup_config

    broken = Settings(
        environment="staging",
        storage_provider="azure_blob",
        azure_storage_account=None,
        azure_storage_container=None,
        azure_storage_key=None,
    )
    with pytest.raises(RuntimeError):
        enforce_startup_config(broken)

    degraded = Settings(
        environment="development",
        storage_provider="azure_blob",
        azure_storage_account=None,
        azure_storage_container=None,
        azure_storage_key=None,
    )
    assert enforce_startup_config(degraded)  # warns, returns problems, no raise


@pytest.mark.parametrize(
    "environment,expected",
    [("production", True), ("staging", True), ("development", False), ("test", False)],
)
def test_write_auth_is_enforced_on_any_real_deployment(
    monkeypatch, environment, expected
):
    import src.config.security_policy as security_policy
    import src.config.settings as settings_module

    # The policy reads the module-level ENVIRONMENT; patch it rather than
    # reloading the module, which drags in storage and LLM config as a side effect.
    monkeypatch.setattr(settings_module, "ENVIRONMENT", environment)

    assert security_policy._peacetime_requires_auth_for_writes() is expected
