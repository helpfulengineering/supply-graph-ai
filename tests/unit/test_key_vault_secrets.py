"""Container App secrets backed by Key Vault rather than duplicated per app.

The properties worth pinning are the ones whose failure is an outage: a name the
platform rejects, a reference an app cannot resolve, or a secret value leaking
into something that gets logged.
"""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

_REPO_ROOT = Path(__file__).resolve().parents[2]
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

from deploy.providers.azure.key_vault import (
    KEY_VAULT_SECRET_REFS,
    MAX_SECRET_NAME_LENGTH,
    SecretNameTooLongError,
    container_app_secrets,
    key_vault_reference,
    secret_env_vars,
    secret_refs_for,
    secret_uri,
)

pytestmark = pytest.mark.unit

VAULT = "ohm-test-kv"


# --- The platform limit that forced a rename ---------------------------------


def test_every_secret_name_fits_the_platform_limit():
    """A Key Vault reference is rejected above 20 characters.

    `llm-encryption-password` was 23, which is why it is now
    `llm-encrypt-password`. Adding a longer name would fail at deploy time with
    a platform error that does not name the culprit.
    """
    too_long = {
        name: len(name)
        for name in KEY_VAULT_SECRET_REFS.values()
        if len(name) > MAX_SECRET_NAME_LENGTH
    }

    assert (
        not too_long
    ), f"names exceed the {MAX_SECRET_NAME_LENGTH}-char limit: {too_long}"


def test_a_too_long_name_fails_loudly_and_says_which():
    with pytest.raises(SecretNameTooLongError, match="this-name-is-far-too-long"):
        key_vault_reference(VAULT, "this-name-is-far-too-long")


def test_the_renamed_secret_kept_its_environment_variable():
    """Only the secret's NAME moved. The application reads the same env var, so
    it cannot tell the difference — which is what makes the rename safe."""
    assert KEY_VAULT_SECRET_REFS["LLM_ENCRYPTION_PASSWORD"] == "llm-encrypt-password"
    assert "LLM_ENCRYPTION_PASSWORD" in secret_env_vars()


# --- References resolve to the right place -----------------------------------


def test_a_reference_names_the_vault_the_secret_and_the_identity():
    reference = key_vault_reference(VAULT, "azure-storage-key")

    assert reference == (
        f"keyvaultref:https://{VAULT}.vault.azure.net/secrets/azure-storage-key"
        ",identityref:system"
    )


def test_the_uri_points_at_the_secret_not_a_version():
    """Pinning a version would freeze rotation, defeating the point."""
    assert secret_uri(VAULT, "api-key").endswith("/secrets/api-key")


# --- No secret value ever appears --------------------------------------------


def test_container_app_secrets_carry_pointers_never_values():
    """These get logged and pasted into issues; they must be safe to read."""
    for value in container_app_secrets(VAULT).values():
        assert value.startswith("keyvaultref:https://")
        assert "identityref:system" in value


def test_env_vars_carry_pointers_never_values():
    for value in secret_env_vars().values():
        assert value.startswith("secretref:")
        assert (
            "vault.azure.net" not in value
        )  # the env var names the SECRET, not the URI


# --- Each app gets only what it needs ----------------------------------------


def test_the_worker_does_not_get_the_api_keys():
    """It authenticates no callers, so granting it those is access it cannot use."""
    assert "API_KEYS" in secret_refs_for()
    assert "API_KEYS" not in secret_refs_for(worker=True)


def test_the_worker_gets_the_secrets_it_actually_needs():
    """Storage to read designs, git tokens because IT clones repositories, the
    encryption secrets because importing config in production demands them, and
    the broker URLs to consume jobs."""
    worker = secret_refs_for(worker=True)

    for required in (
        "AZURE_STORAGE_KEY",
        "GITHUB_ACCESS_TOKEN",
        "GITLAB_ACCESS_TOKEN",
        "LLM_ENCRYPTION_SALT",
        "LLM_ENCRYPTION_PASSWORD",
        "JOB_BROKER_URL",
        "JOB_RESULT_BACKEND",
    ):
        assert required in worker, required


def test_both_apps_reference_the_same_secret_for_a_shared_value():
    """The whole point: one value, two pointers, no copies to drift."""
    api = secret_refs_for()
    worker = secret_refs_for(worker=True)

    shared = set(api) & set(worker)
    assert shared, "expected shared secrets"
    for env_var in shared:
        assert api[env_var] == worker[env_var]


def test_key_vault_names_are_valid():
    """Key Vault accepts alphanumerics and dashes only."""
    import re

    for name in KEY_VAULT_SECRET_REFS.values():
        assert re.fullmatch(r"[A-Za-z0-9-]+", name), name


def test_the_github_secret_name_is_spelled_correctly():
    """It was `gihub-token` — missing a 't' — in the vault and on both apps.

    Pinned because the failure mode is quiet: a wrong name means the worker
    clones anonymously, and anonymous GitHub rate limits surface as intermittent
    429s during generation rather than as an obvious misconfiguration.
    """
    assert KEY_VAULT_SECRET_REFS["GITHUB_ACCESS_TOKEN"] == "github-token"
    assert "gihub-token" not in KEY_VAULT_SECRET_REFS.values()


# --- The deploy must not undo the migration ----------------------------------
#
# The failure this guards is silent: setting a secret VALUE replaces the app's
# Key Vault reference, the deploy succeeds, the app keeps working on an inline
# copy, and the duplicated secrets the vault removed quietly come back.


def _worker_deploy(record):
    import importlib.util

    spec = importlib.util.spec_from_file_location(
        "_worker_deploy_kv",
        _REPO_ROOT / "deploy" / "scripts" / "deploy_azure_worker.py",
    )
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)

    from unittest.mock import MagicMock, patch

    def _run(command, capture_output, text, check):
        record.append(command)
        result = MagicMock()
        result.returncode = 0
        result.stdout = "value-or-key"
        result.stderr = ""
        return result

    argv = [
        "deploy_azure_worker.py",
        "--image",
        "img@sha256:abc",
        "--subscription-id",
        "sub",
        "--environment",
        "production",
    ]
    with (
        patch.object(sys, "argv", argv),
        patch("deploy.providers.azure.container_apps.subprocess.run", side_effect=_run),
    ):
        return module.main()


def test_the_worker_deploy_writes_references_never_values():
    calls = []
    assert _worker_deploy(calls) == 0

    for command in calls:
        if command[:4] == ["az", "containerapp", "secret", "set"]:
            for token in command[command.index("--secrets") + 1 :]:
                assert "keyvaultref:" in token, token


def test_the_worker_deploy_no_longer_copies_secrets_from_the_api_app():
    """One value with two references has nothing to mirror."""
    calls = []
    assert _worker_deploy(calls) == 0

    assert not any(
        c[:4] == ["az", "containerapp", "secret", "show"] for c in calls
    ), "the worker deploy should not read the API app's secret values"
