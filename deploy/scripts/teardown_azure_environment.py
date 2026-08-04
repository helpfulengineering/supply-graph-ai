#!/usr/bin/env python3
"""Delete a non-production environment's Container Apps (and optionally its blobs).

Staging is meant to be disposable: stood up to rehearse a deploy, torn down when
the work is finished. Doing that by hand means hunting through the portal and
leaving something running, so this makes it one command.

**Refuses to touch production.** The guard is on the environment name AND on the
app names, because the expensive mistake here is deleting the live service.

Usage:
    # show what would be deleted
    uv run python deploy/scripts/teardown_azure_environment.py --environment staging

    # actually delete the container apps
    uv run python deploy/scripts/teardown_azure_environment.py \\
        --environment staging --yes

    # also delete the environment's blob container (data loss, opt in explicitly)
    uv run python deploy/scripts/teardown_azure_environment.py \\
        --environment staging --yes --delete-blob-container
"""

import argparse
import subprocess
import sys
from pathlib import Path

project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from src.config.schema import deploy_env_vars  # noqa: E402

# Environments this script will never operate on, whatever else is passed.
PROTECTED_ENVIRONMENTS = {"production", "prod"}

# App names that must never be deleted by this script, as a second guard in case
# an environment file is ever mis-edited to point at the live apps.
PROTECTED_APPS = {
    "openhardwaremanager",
    "openhardwaremanager-frontend",
    "openhardwaremanager-worker",
}

# Vaults that must never be deleted by this script. Deleting one takes every
# secret both live apps resolve at runtime, so they stop starting.
PROTECTED_VAULTS = {"ohm-prod-kv"}


def _run(command: list[str]) -> tuple[int, str, str]:
    result = subprocess.run(command, capture_output=True, text=True, check=False)
    return result.returncode, result.stdout, result.stderr


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Tear down a non-production environment"
    )
    parser.add_argument(
        "--environment",
        required=True,
        help="Environment to tear down (production is refused)",
    )
    parser.add_argument("--resource-group", default="project_data_rg")
    parser.add_argument(
        "--container-app-name",
        default=None,
        help="API app name (default: openhardwaremanager-<environment>)",
    )
    parser.add_argument(
        "--worker-app-name",
        default=None,
        help="Worker app name (default: openhardwaremanager-stg-worker for staging)",
    )
    parser.add_argument(
        "--vault-name",
        default=None,
        help="Key Vault name (default: ohm-<environment>-kv)",
    )
    parser.add_argument(
        "--delete-key-vault",
        action="store_true",
        help=(
            "Also delete the environment's Key Vault, and PURGE it. Purging is "
            "irreversible, and is the point: a soft-deleted vault keeps its name "
            "reserved for 90 days, so the next rebuild of this environment would "
            "fail on a name collision."
        ),
    )
    parser.add_argument(
        "--delete-blob-container",
        action="store_true",
        help="Also delete the environment's blob container. Destroys data.",
    )
    parser.add_argument(
        "--yes", action="store_true", help="Actually delete (otherwise dry run)"
    )
    args = parser.parse_args()

    if args.environment.lower() in PROTECTED_ENVIRONMENTS:
        print(f"❌ Refusing to tear down protected environment {args.environment!r}.")
        return 1

    api_app = args.container_app_name or f"openhardwaremanager-{args.environment}"
    worker_app = args.worker_app_name or (
        "openhardwaremanager-stg-worker"
        if args.environment == "staging"
        else f"openhardwaremanager-{args.environment}-worker"
    )

    for app in (api_app, worker_app):
        if app in PROTECTED_APPS:
            print(f"❌ Refusing to delete protected container app {app!r}.")
            return 1

    vault = args.vault_name or f"ohm-{args.environment}-kv"
    if args.delete_key_vault and vault in PROTECTED_VAULTS:
        print(f"❌ Refusing to delete protected Key Vault {vault!r}.")
        return 1

    env_vars = deploy_env_vars(args.environment)
    blob_container = env_vars.get("AZURE_STORAGE_CONTAINER")
    storage_account = env_vars.get("AZURE_STORAGE_ACCOUNT")

    print("=" * 80)
    print(f"Teardown — environment {args.environment!r}")
    print("=" * 80)
    print(f"Resource group:   {args.resource_group}")
    print(f"Container apps:   {api_app}, {worker_app}")
    if args.delete_blob_container:
        print(f"Blob container:   {storage_account}/{blob_container}  (DATA LOSS)")
    else:
        print(f"Blob container:   {storage_account}/{blob_container}  (kept)")
    if args.delete_key_vault:
        print(f"Key Vault:        {vault}  (DELETED AND PURGED — irreversible)")
    else:
        print(f"Key Vault:        {vault}  (kept)")
    print("=" * 80)

    if not args.yes:
        print("\nDry run — nothing deleted. Re-run with --yes to proceed.")
        return 0

    failures = []
    for app in (api_app, worker_app):
        print(f"\n🗑  Deleting container app {app}...")
        code, _, stderr = _run(
            [
                "az",
                "containerapp",
                "delete",
                "--name",
                app,
                "--resource-group",
                args.resource_group,
                "--yes",
            ]
        )
        if code != 0:
            # A missing app is fine — teardown should be idempotent.
            if "not found" in stderr.lower() or "notfound" in stderr.lower():
                print(f"   already gone: {app}")
            else:
                failures.append(f"{app}: {stderr.strip()}")
                print(f"   ❌ {stderr.strip()}")
        else:
            print(f"   deleted: {app}")

    if args.delete_key_vault:
        print(f"\n🗑  Deleting Key Vault {vault}...")
        code, _, stderr = _run(
            [
                "az",
                "keyvault",
                "delete",
                "--name",
                vault,
                "--resource-group",
                args.resource_group,
            ]
        )
        if code != 0 and "not found" not in stderr.lower():
            failures.append(f"key vault {vault}: {stderr.strip()}")
            print(f"   ❌ {stderr.strip()}")
        else:
            # Soft-delete keeps the NAME reserved for 90 days, so without this
            # the next rebuild of this environment fails on a name collision.
            location = _run(
                [
                    "az",
                    "group",
                    "show",
                    "--name",
                    args.resource_group,
                    "--query",
                    "location",
                    "--output",
                    "tsv",
                ]
            )[1].strip()
            code, _, stderr = _run(
                ["az", "keyvault", "purge", "--name", vault, "--location", location]
            )
            if code != 0 and "not found" not in stderr.lower():
                failures.append(
                    f"key vault {vault} deleted but NOT purged — the name stays "
                    f"reserved: {stderr.strip()}"
                )
                print(f"   ⚠  deleted but not purged: {stderr.strip()}")
            else:
                print(f"   deleted and purged: {vault}")

    if args.delete_blob_container and blob_container:
        print(f"\n🗑  Deleting blob container {blob_container}...")
        code, key, _ = _run(
            [
                "az",
                "storage",
                "account",
                "keys",
                "list",
                "--account-name",
                storage_account,
                "--resource-group",
                args.resource_group,
                "--query",
                "[0].value",
                "--output",
                "tsv",
            ]
        )
        if code != 0:
            failures.append("could not read the storage account key")
        else:
            code, _, stderr = _run(
                [
                    "az",
                    "storage",
                    "container",
                    "delete",
                    "--name",
                    blob_container,
                    "--account-name",
                    storage_account,
                    "--account-key",
                    key.strip(),
                ]
            )
            if code != 0:
                failures.append(f"blob container: {stderr.strip()}")
            else:
                print(f"   deleted: {blob_container}")

    if failures:
        print("\n❌ Teardown finished with problems:")
        for failure in failures:
            print(f"   - {failure}")
        return 1

    print("\n✅ Teardown complete.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
