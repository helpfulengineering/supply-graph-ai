"""Unit tests for deploying the Celery worker container app.

No live Azure calls — subprocess.run is mocked. These pin the properties that
make the worker correct rather than merely deployable: it shares the API's
config surface, it runs worker mode with no ingress, it carries the secrets it
needs, and it does not by itself switch async jobs on.
"""

import logging
import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

_REPO_ROOT = Path(__file__).resolve().parents[2]
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

from deploy.providers.azure.app_secrets import (
    mirrored_secret_env_vars,
    mirrored_secret_names,
)
from src.config.schema import (
    deploy_env_vars,
    worker_deploy_config,
    worker_deploy_env_vars,
)

# --- The worker inherits the API's config surface ----------------------------


def test_worker_inherits_the_shared_storage_target():
    """Declared once, so an API and worker cannot point at different data."""
    shared = deploy_env_vars("production")
    worker = worker_deploy_env_vars("production")

    for key in ("STORAGE_PROVIDER", "AZURE_STORAGE_ACCOUNT", "AZURE_STORAGE_CONTAINER"):
        assert worker[key] == shared[key]


def test_worker_env_layers_the_worker_table_on_top():
    worker = worker_deploy_env_vars("production")

    assert worker["CELERY_CONCURRENCY"] == "1"


def test_worker_deploy_shape_is_one_replica_of_the_api_size():
    shape = worker_deploy_config("production")

    assert shape["cpu"] == 1.0
    assert shape["memory"] == "2Gi"
    # Pinned at 1: ACA's default scaler is HTTP-based, and a no-ingress worker
    # gets no HTTP — min 0 without a queue scaler means jobs never run.
    assert shape["min_replicas"] == 1
    assert shape["max_replicas"] == 1


def test_worker_shape_excludes_the_env_subtable():
    """[worker.env] is container env, not deploy shape."""
    assert "env" not in worker_deploy_config("production")


def test_environment_without_a_worker_table_yields_nothing():
    assert worker_deploy_config("no-such-environment") == {}
    assert worker_deploy_env_vars("no-such-environment") == {}


def test_worker_inherits_the_jobs_flag_rather_than_setting_its_own():
    """The worker must never disagree with the API about whether jobs are on.

    It carries the flag because it shares the top-level config, not because the
    worker deploy sets one — so the two can never be configured apart.
    """
    shared = deploy_env_vars("production")
    worker = worker_deploy_env_vars("production")

    assert worker["JOBS_ENABLED"] == shared["JOBS_ENABLED"]
    assert "JOBS_ENABLED" not in worker_deploy_config("production")


# --- Secrets it needs --------------------------------------------------------


def test_worker_carries_storage_key_and_both_git_tokens():
    """The worker does the repo reading, so anonymous rate limits hit HERE."""
    env_vars = mirrored_secret_env_vars()

    assert env_vars["AZURE_STORAGE_KEY"].startswith("secretref:")
    assert env_vars["GITHUB_ACCESS_TOKEN"].startswith("secretref:")
    assert env_vars["GITLAB_ACCESS_TOKEN"].startswith("secretref:")
    assert not any("secretref:" not in value for value in env_vars.values())


def test_mirrored_names_match_the_live_secret_names():
    """`gihub-token` is missing a 't' in the live app; renaming is separate work."""
    assert mirrored_secret_names() == [
        "azure-storage-key",
        "gihub-token",
        "gitlab-token",
    ]


# --- The deploy itself -------------------------------------------------------


def _run_worker_deploy(record, app_exists=True):
    import importlib.util

    spec = importlib.util.spec_from_file_location(
        "_deploy_worker_under_test",
        _REPO_ROOT / "deploy" / "scripts" / "deploy_azure_worker.py",
    )
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)

    def _run(command, capture_output, text, check):
        record.append(command)
        result = MagicMock()
        result.stdout = "secret-or-key-value"
        result.stderr = ""
        if (
            command[:3] == ["az", "containerapp", "show"]
            and "--query" not in command
            and "secret" not in command
        ):
            result.returncode = 0 if app_exists else 1
        else:
            result.returncode = 0
        return result

    argv = [
        "deploy_azure_worker.py",
        "--image",
        "touchthesun/openhardwaremanager@sha256:abc",
        "--subscription-id",
        "test-sub",
        "--environment",
        "production",
    ]
    with (
        patch.object(sys, "argv", argv),
        patch("deploy.providers.azure.container_apps.subprocess.run", side_effect=_run),
    ):
        return module.main()


def _worker_command(calls):
    return next(
        c for c in calls if c[1] == "containerapp" and c[2] in ("create", "update")
    )


def test_worker_deploys_with_no_ingress_and_worker_mode():
    calls = []
    assert _run_worker_deploy(calls, app_exists=False) == 0

    command = _worker_command(calls)
    assert command[2] == "create"
    assert "--ingress" not in command
    assert "--target-port" not in command
    assert (
        command[command.index("--command") + 1] == "/usr/local/bin/docker-entrypoint.sh"
    )
    assert command[command.index("--args") + 1] == "worker"


def test_worker_creates_with_secrets_inline_because_the_app_does_not_exist_yet():
    """`az containerapp secret set` cannot target an app that does not exist."""
    calls = []
    assert _run_worker_deploy(calls, app_exists=False) == 0

    command = _worker_command(calls)
    assert "--secrets" in command
    secret_names = {
        token.split("=", 1)[0]
        for token in command[command.index("--secrets") + 1 :]
        if "=" in token and not token.startswith("--")
    }
    assert {"azure-storage-key", "gihub-token", "gitlab-token"} <= secret_names
    assert {"job-broker-url", "job-result-backend"} <= secret_names


def test_worker_update_sets_secrets_before_the_update():
    calls = []
    assert _run_worker_deploy(calls, app_exists=True) == 0

    kinds = [
        (
            "secret-set"
            if c[:4] == ["az", "containerapp", "secret", "set"]
            else "app-update" if c[:3] == ["az", "containerapp", "update"] else None
        )
        for c in calls
    ]
    ordered = [kind for kind in kinds if kind]
    assert ordered.index("secret-set") < ordered.index("app-update")


def test_worker_env_vars_carry_no_secret_values():
    calls = []
    assert _run_worker_deploy(calls, app_exists=True) == 0

    command = _worker_command(calls)
    env_tokens = command[command.index("--set-env-vars") + 1 :]

    assert "CELERY_CONCURRENCY=1" in env_tokens
    assert "AZURE_STORAGE_KEY=secretref:azure-storage-key" in env_tokens
    assert "JOB_BROKER_URL=secretref:job-broker-url" in env_tokens
    assert not any("rediss://" in token for token in env_tokens)


def test_worker_deploy_does_not_look_up_an_fqdn():
    calls = []
    assert _run_worker_deploy(calls, app_exists=True) == 0

    assert not any("properties.configuration.ingress.fqdn" in c for c in calls)


def test_create_command_is_logged_with_secret_values_redacted(caplog):
    caplog.set_level(logging.INFO)
    calls = []
    assert _run_worker_deploy(calls, app_exists=False) == 0

    assert "secret-or-key-value" not in caplog.text
    assert "azure-storage-key=***" in caplog.text


# --- Shared-secret verification ----------------------------------------------
#
# The deploys mirror these on every run, so this confirms mirroring took effect
# and catches what mirroring cannot: a half-completed deploy, or a secret edited
# by hand in the portal afterwards.


def _load_verifier():
    import importlib.util

    spec = importlib.util.spec_from_file_location(
        "_verify_secrets_under_test",
        _REPO_ROOT / "deploy" / "scripts" / "verify_app_secrets.py",
    )
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _run_verifier(values_by_app):
    """values_by_app: {app_name: {secret_name: value or None}}"""
    module = _load_verifier()

    def _run(command, capture_output, text, check):
        app = command[command.index("--name") + 1]
        secret = command[command.index("--secret-name") + 1]
        value = values_by_app.get(app, {}).get(secret)
        result = MagicMock()
        result.returncode = 0 if value is not None else 1
        result.stdout = value or ""
        result.stderr = ""
        return result

    with (
        patch.object(sys, "argv", ["verify_app_secrets.py"]),
        patch("subprocess.run", side_effect=_run),
    ):
        return module.main(), module


def _all_agreeing():
    module = _load_verifier()
    shared = {name: f"value-for-{name}" for name in module.SHARED_SECRETS}
    return {
        "openhardwaremanager": {**shared, "api-key": "the-api-key"},
        "openhardwaremanager-worker": dict(shared),
    }


def test_secret_check_passes_when_both_apps_agree():
    code, _ = _run_verifier(_all_agreeing())
    assert code == 0


def test_secret_check_detects_a_differing_value():
    values = _all_agreeing()
    values["openhardwaremanager-worker"]["job-broker-url"] = "pointing-somewhere-else"

    code, _ = _run_verifier(values)
    assert code == 1


def test_secret_check_detects_a_missing_secret_on_the_worker():
    values = _all_agreeing()
    values["openhardwaremanager-worker"]["azure-storage-key"] = None

    code, _ = _run_verifier(values)
    assert code == 1


def test_api_only_secret_is_not_reported_as_drift():
    """A worker authenticates no callers, so api-key is correctly absent."""
    values = _all_agreeing()
    assert "api-key" not in values["openhardwaremanager-worker"]

    code, _ = _run_verifier(values)
    assert code == 0


def test_missing_api_only_secret_on_the_api_is_a_problem():
    values = _all_agreeing()
    values["openhardwaremanager"]["api-key"] = None

    code, _ = _run_verifier(values)
    assert code == 1


def test_shared_set_covers_the_broker_url():
    """A broker mismatch is invisible in either app alone — jobs just never run."""
    module = _load_verifier()

    assert "job-broker-url" in module.SHARED_SECRETS
    assert "job-result-backend" in module.SHARED_SECRETS
    assert "azure-storage-key" in module.SHARED_SECRETS
    # API-only secrets must not be in the shared set, or every check would fail.
    assert "api-key" not in module.SHARED_SECRETS


def test_digest_never_reveals_the_value():
    module = _load_verifier()
    secret = "rediss://:super-secret-key@host:6380/1"

    digest = module._digest(secret)

    assert secret not in digest
    assert "super-secret-key" not in digest
    assert module._digest(secret) == digest
    assert module._digest(secret + "x") != digest
