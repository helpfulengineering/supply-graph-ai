"""Unit tests for the staging environment and standing up a fresh environment.

Staging is a rehearsal of production, so what matters is that it is (a) isolated
from production's data and job queues, and (b) otherwise identical. No live
Azure calls — subprocess.run is mocked.
"""

import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

_REPO_ROOT = Path(__file__).resolve().parents[2]
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

from deploy.providers.azure.app_secrets import (
    mirrored_secret_env_vars,
    mirrored_secret_names,
)
from src.config.schema import (
    deploy_env_vars,
    redis_deploy_config,
    worker_deploy_config,
)

# --- Staging is isolated from production -------------------------------------


def test_staging_writes_to_its_own_blob_container():
    staging = deploy_env_vars("staging")
    production = deploy_env_vars("production")

    assert staging["AZURE_STORAGE_CONTAINER"] != production["AZURE_STORAGE_CONTAINER"]
    # Same account, so one mirrored storage key serves both.
    assert staging["AZURE_STORAGE_ACCOUNT"] == production["AZURE_STORAGE_ACCOUNT"]


def test_staging_uses_different_redis_databases_than_production():
    """Sharing an instance is fine; sharing a broker db would cross the streams."""
    staging = redis_deploy_config("staging")
    production = redis_deploy_config("production")

    assert staging["host"] == production["host"]
    staging_dbs = {staging["cache_db"], staging["broker_db"], staging["results_db"]}
    production_dbs = {
        production["cache_db"],
        production["broker_db"],
        production["results_db"],
    }
    assert staging_dbs.isdisjoint(production_dbs)


# --- Staging is otherwise identical to production ----------------------------


def test_staging_is_treated_as_a_real_deployment():
    """A rehearsal on a laxer posture or a different server proves very little.

    Staging used to pin `USE_GUNICORN=true` by hand to work around the
    entrypoint only recognising "production". Both the server choice and the
    application's strictness are now derived from the same rule, so the
    workaround is gone and staging must simply be production-like.

    The behaviours themselves are covered by test_production_like_predicate.py
    and test_entrypoint_server_choice.py.
    """
    from src.config.schema import is_production_like

    assert is_production_like("staging") is True
    assert "USE_GUNICORN" not in deploy_env_vars("staging")


def test_staging_matches_production_worker_shape():
    assert worker_deploy_config("staging") == worker_deploy_config("production")


def test_both_environments_enable_jobs():
    """Staging led; production followed once the path was proven there.

    They must agree: a staging rehearsal of a feature production has switched
    off would test the wrong thing.
    """
    assert deploy_env_vars("staging")["JOBS_ENABLED"] == "True"
    assert deploy_env_vars("production")["JOBS_ENABLED"] == "True"


def test_staging_holds_no_secrets():
    for value in deploy_env_vars("staging").values():
        assert "rediss://" not in value
        assert not value.startswith("secretref:")


# --- Standing up a fresh environment -----------------------------------------


def _run_backend_deploy(record, extra_argv=(), app_exists=True):
    import importlib.util

    spec = importlib.util.spec_from_file_location(
        "_deploy_backend_under_test",
        _REPO_ROOT / "deploy" / "scripts" / "deploy_azure.py",
    )
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)

    def _run(command, capture_output, text, check):
        record.append(command)
        result = MagicMock()
        result.stdout = "mirrored-secret-value"
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
        "deploy_azure.py",
        "--image",
        "touchthesun/openhardwaremanager@sha256:abc",
        "--subscription-id",
        "test-sub",
        *extra_argv,
    ]
    with (
        patch.object(sys, "argv", argv),
        patch("deploy.providers.azure.container_apps.subprocess.run", side_effect=_run),
    ):
        return module.main()


def _app_command(calls):
    return next(
        c for c in calls if c[1] == "containerapp" and c[2] in ("create", "update")
    )


def test_production_deploy_writes_references_never_values():
    """Production has a vault, so the deploy must never handle a secret VALUE.

    Writing one would REPLACE the app's Key Vault reference — the deploy would
    succeed, the app would keep working on an inline copy, and the migration
    would be silently undone.
    """
    calls = []
    assert _run_backend_deploy(calls, ["--environment", "production"]) == 0

    command = _app_command(calls)
    env_tokens = command[command.index("--set-env-vars") + 1 :]

    # Env vars name secrets; they never carry one.
    for token in env_tokens:
        if token.startswith(
            ("API_KEYS=", "AZURE_STORAGE_KEY=", "GITHUB_ACCESS_TOKEN=")
        ):
            assert token.split("=", 1)[1].startswith("secretref:"), token

    # And the secrets set on the app are vault references.
    secrets_index = command.index("--secrets") if "--secrets" in command else None
    if secrets_index is not None:
        for token in command[secrets_index + 1 :]:
            if token.startswith("--"):
                break
            assert "keyvaultref:" in token, token

    # Nothing reads another app's secret value to copy it.
    assert not any(c[:4] == ["az", "containerapp", "secret", "show"] for c in calls)


def test_production_deploy_mints_redis_urls_into_the_vault_not_onto_the_app():
    """The generator still runs every deploy; its output goes to the vault."""
    calls = []
    assert _run_backend_deploy(calls, ["--environment", "production"]) == 0

    vault_writes = [c for c in calls if c[:4] == ["az", "keyvault", "secret", "set"]]
    written = {c[c.index("--name") + 1] for c in vault_writes}

    assert {"job-broker-url", "job-result-backend", "cache-redis-url"} <= written

    # The URL itself must never be set as an app secret.
    app_secret_sets = [
        c for c in calls if c[:4] == ["az", "containerapp", "secret", "set"]
    ]
    for command in app_secret_sets:
        assert not any("rediss://" in token for token in command), command


def test_mirroring_wires_both_the_values_and_the_env_refs():
    calls = []
    assert (
        _run_backend_deploy(
            calls,
            [
                "--environment",
                "staging",
                "--container-app-name",
                "openhardwaremanager-staging",
                "--mirror-secrets-from",
                "openhardwaremanager",
            ],
            app_exists=False,
        )
        == 0
    )

    command = _app_command(calls)
    assert command[2] == "create"

    secret_names = {
        token.split("=", 1)[0]
        for token in command[command.index("--secrets") + 1 :]
        if "=" in token and not token.startswith("--")
    }
    assert set(mirrored_secret_names(include_api_keys=True)) <= secret_names

    env_tokens = command[command.index("--env-vars") + 1 :]
    for env_var, ref in mirrored_secret_env_vars(include_api_keys=True).items():
        assert f"{env_var}={ref}" in env_tokens


def test_mirroring_reads_from_the_named_source_app():
    calls = []
    _run_backend_deploy(
        calls,
        [
            "--environment",
            "staging",
            "--container-app-name",
            "openhardwaremanager-staging",
            "--mirror-secrets-from",
            "openhardwaremanager",
        ],
        app_exists=False,
    )

    reads = [c for c in calls if c[:4] == ["az", "containerapp", "secret", "show"]]
    assert reads, "expected the source app's secrets to be read"
    for command in reads:
        assert command[command.index("--name") + 1] == "openhardwaremanager"


def _run_teardown(argv):
    import importlib.util

    spec = importlib.util.spec_from_file_location(
        "_teardown_under_test",
        _REPO_ROOT / "deploy" / "scripts" / "teardown_azure_environment.py",
    )
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)

    calls = []

    def _run(command, capture_output, text, check):
        calls.append(command)
        result = MagicMock()
        result.returncode = 0
        result.stdout = ""
        result.stderr = ""
        return result

    with (
        patch.object(sys, "argv", ["teardown.py", *argv]),
        patch("subprocess.run", side_effect=_run),
    ):
        return module.main(), calls


def test_teardown_refuses_production():
    """The expensive mistake here is deleting the live service."""
    code, calls = _run_teardown(["--environment", "production", "--yes"])

    assert code == 1
    assert calls == []


def test_teardown_refuses_the_live_app_names_even_under_another_environment():
    """Second guard, in case an environment file is ever mis-edited."""
    code, calls = _run_teardown(
        [
            "--environment",
            "staging",
            "--container-app-name",
            "openhardwaremanager",
            "--yes",
        ]
    )

    assert code == 1
    assert calls == []


def test_teardown_without_yes_deletes_nothing():
    code, calls = _run_teardown(["--environment", "staging"])

    assert code == 0
    assert calls == []


def test_teardown_refuses_the_production_vault():
    """Deleting it takes every secret both live apps resolve at runtime, so they
    stop starting. Guarded by name as well as by environment."""
    code, calls = _run_teardown(
        [
            "--environment",
            "staging",
            "--vault-name",
            "ohm-prod-kv",
            "--delete-key-vault",
            "--yes",
        ]
    )

    assert code == 1
    assert calls == []


def test_teardown_keeps_the_vault_unless_explicitly_asked():
    _, calls = _run_teardown(["--environment", "staging", "--yes"])

    assert not any("keyvault" in command for command in calls)


def test_teardown_purges_the_vault_it_deletes():
    """A soft-deleted vault keeps its NAME reserved for 90 days, so a delete
    without a purge silently blocks the next rebuild of this environment."""
    _, calls = _run_teardown(
        ["--environment", "staging", "--delete-key-vault", "--yes"]
    )

    verbs = [c[2] for c in calls if c[:2] == ["az", "keyvault"]]
    assert "delete" in verbs, "expected the vault to be deleted"
    assert "purge" in verbs, "a deleted-but-unpurged vault blocks the next rebuild"
    assert verbs.index("delete") < verbs.index("purge")


def test_teardown_keeps_blobs_unless_explicitly_asked():
    _, calls = _run_teardown(["--environment", "staging", "--yes"])

    assert not any("storage" in command for command in calls)
    deleted = [c for c in calls if c[:3] == ["az", "containerapp", "delete"]]
    assert len(deleted) == 2


def test_created_app_targets_the_port_the_image_actually_binds():
    """The image's entrypoint defaults to 8001; ingress on 8080 would be dead."""
    calls = []
    _run_backend_deploy(
        calls,
        [
            "--environment",
            "staging",
            "--container-app-name",
            "openhardwaremanager-staging",
            "--mirror-secrets-from",
            "openhardwaremanager",
        ],
        app_exists=False,
    )

    command = _app_command(calls)
    assert command[command.index("--target-port") + 1] == "8001"
    assert command[command.index("--ingress") + 1] == "external"
