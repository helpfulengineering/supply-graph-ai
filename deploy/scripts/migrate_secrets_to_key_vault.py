#!/usr/bin/env python3
"""Move an environment's Container App secrets into Key Vault, once.

Container App secrets are per-app, so every shared value exists twice. This
replaces the copies with references: the value lives once in Key Vault, and both
apps hold a pointer resolved at runtime through their managed identity. Rotation
then means one edit and no deploy.

**The order matters, because an app that cannot resolve a secret does not
start.** Each step is safe to stop after:

1. Create the vault (idempotent).
2. Enable a system-assigned identity on each app.
3. Grant each identity read access, and the deploy principal write access.
4. Copy the current values from the apps into the vault.
5. Repoint each app's secrets at the vault.
6. Verify the apps still run.

The original inline secrets are **left in place** — a Container App secret is
replaced by name, so repointing overwrites them anyway, and anything this script
does not touch stays untouched. Removing leftovers is a separate, later step
once the references have been trusted for a while.

Run with --dry-run first. Rehearse on staging before production: an app that
fails to resolve a secret fails to start, and that is a live outage in prod.

Usage:
    uv run python deploy/scripts/migrate_secrets_to_key_vault.py \\
        --environment staging --vault-name ohm-staging-kv \\
        --container-app-name openhardwaremanager-staging \\
        --worker-app-name openhardwaremanager-stg-worker --dry-run
"""

import argparse
import subprocess
import sys
from pathlib import Path

project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from deploy.providers.azure.key_vault import (  # noqa: E402
    container_app_secrets,
    secret_env_vars,
    secret_refs_for,
)

# Where each Key Vault secret's current value comes from: the API app holds the
# authoritative copy today, so it is the source for every one of them.
SOURCE_APP_ROLE = "api"


def _run(command: list[str], *, dry_run: bool = False, redact: bool = False) -> str:
    """Run an az command, returning stdout. Never echoes a secret value."""
    shown = command if not redact else [*command[:6], "…(values redacted)"]
    if dry_run:
        print(f"   would run: {' '.join(shown)}")
        return ""
    result = subprocess.run(command, capture_output=True, text=True, check=False)
    if result.returncode != 0:
        raise RuntimeError(f"{' '.join(shown)}\n{result.stderr.strip()}")
    return result.stdout.strip()


def main() -> int:
    parser = argparse.ArgumentParser(description="Migrate app secrets into Key Vault")
    parser.add_argument("--environment", required=True)
    parser.add_argument("--vault-name", required=True)
    parser.add_argument("--resource-group", default="project_data_rg")
    parser.add_argument("--container-app-name", required=True, help="the API app")
    parser.add_argument("--worker-app-name", required=True)
    parser.add_argument("--location", default="westus3")
    parser.add_argument(
        "--deploy-principal-id",
        default=None,
        help="Object id of the CI principal that mints Redis URLs; granted write access",
    )
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    api, worker, vault = args.container_app_name, args.worker_app_name, args.vault_name
    dry = args.dry_run

    print("=" * 78)
    print(f"Key Vault migration — {args.environment}")
    print(f"  vault:  {vault}")
    print(f"  apps:   {api}, {worker}")
    print(f"  mode:   {'DRY RUN' if dry else 'APPLY'}")
    print("=" * 78)

    subscription = _run(["az", "account", "show", "--query", "id", "-o", "tsv"])
    vault_scope = (
        f"/subscriptions/{subscription}/resourceGroups/{args.resource_group}"
        f"/providers/Microsoft.KeyVault/vaults/{vault}"
    )

    print("\n[1/6] Vault")
    exists = _run(
        ["az", "keyvault", "list", "--query", f"[?name=='{vault}'].name", "-o", "tsv"]
    )
    if exists:
        print(f"   exists: {vault}")
    else:
        _run(
            [
                "az",
                "keyvault",
                "create",
                "--name",
                vault,
                "--resource-group",
                args.resource_group,
                "--location",
                args.location,
                "--enable-rbac-authorization",
                "true",
            ],
            dry_run=dry,
        )
        print(f"   created: {vault}")

    print("\n[2/6] Managed identities")
    principals = {}
    for app in (api, worker):
        principal = _run(
            [
                "az",
                "containerapp",
                "identity",
                "assign",
                "--system-assigned",
                "--name",
                app,
                "--resource-group",
                args.resource_group,
                "--query",
                "principalId",
                "-o",
                "tsv",
            ],
            dry_run=dry,
        )
        principals[app] = principal
        print(f"   {app}: {principal or '(dry run)'}")

    print("\n[3/6] Access")
    for app, principal in principals.items():
        if principal:
            _run(
                [
                    "az",
                    "role",
                    "assignment",
                    "create",
                    "--assignee-object-id",
                    principal,
                    "--assignee-principal-type",
                    "ServicePrincipal",
                    "--role",
                    "Key Vault Secrets User",
                    "--scope",
                    vault_scope,
                ],
                dry_run=dry,
            )
        print(f"   {app}: Key Vault Secrets User")
    # Whoever runs this must WRITE secrets, and an RBAC-enabled vault grants no
    # data-plane access to subscription Owners — management-plane rights are not
    # enough. Without this the copy step fails with a bare 403.
    operator = _run(
        ["az", "ad", "signed-in-user", "show", "--query", "id", "-o", "tsv"]
    )
    if operator:
        _run(
            [
                "az",
                "role",
                "assignment",
                "create",
                "--assignee-object-id",
                operator,
                "--assignee-principal-type",
                "User",
                "--role",
                "Key Vault Secrets Officer",
                "--scope",
                vault_scope,
            ],
            dry_run=dry,
        )
        print("   operator: Key Vault Secrets Officer")

    if args.deploy_principal_id:
        # The deploy mints the Redis URLs on every run, so it must WRITE.
        _run(
            [
                "az",
                "role",
                "assignment",
                "create",
                "--assignee-object-id",
                args.deploy_principal_id,
                "--assignee-principal-type",
                "ServicePrincipal",
                "--role",
                "Key Vault Secrets Officer",
                "--scope",
                vault_scope,
            ],
            dry_run=dry,
        )
        print("   deploy principal: Key Vault Secrets Officer")
    else:
        print(
            "   ⚠  no --deploy-principal-id: CI cannot mint Redis URLs into the vault"
        )

    print("\n[4/6] Copy values in (from the API app, the current source of truth)")
    for env_var, name in secret_refs_for().items():
        # The live secret may still carry its pre-rename name.
        legacy = {"llm-encrypt-password": "llm-encryption-password"}.get(name, name)
        value = _run(
            [
                "az",
                "containerapp",
                "secret",
                "show",
                "--name",
                api,
                "--resource-group",
                args.resource_group,
                "--secret-name",
                legacy,
                "--query",
                "value",
                "-o",
                "tsv",
            ],
            dry_run=dry,
        )
        if not dry and not value:
            print(f"   ✗ {name}: nothing to copy (missing on {api})")
            continue
        _run(
            [
                "az",
                "keyvault",
                "secret",
                "set",
                "--vault-name",
                vault,
                "--name",
                name,
                "--value",
                value or "placeholder",
            ],
            dry_run=dry,
            redact=True,
        )
        print(f"   ✓ {name}" + (f"  (was {legacy})" if legacy != name else ""))

    print("\n[5/6] Repoint the apps")
    for app, is_worker in ((api, False), (worker, True)):
        refs = container_app_secrets(vault, worker=is_worker)
        _run(
            [
                "az",
                "containerapp",
                "secret",
                "set",
                "--name",
                app,
                "--resource-group",
                args.resource_group,
                "--secrets",
                *[f"{n}={v}" for n, v in refs.items()],
            ],
            dry_run=dry,
        )
        env = secret_env_vars(worker=is_worker)
        _run(
            [
                "az",
                "containerapp",
                "update",
                "--name",
                app,
                "--resource-group",
                args.resource_group,
                "--set-env-vars",
                *[f"{k}={v}" for k, v in env.items()],
            ],
            dry_run=dry,
        )
        print(f"   {app}: {len(refs)} secret(s) now reference the vault")

    print("\n[6/6] Verify")
    if dry:
        print("   skipped (dry run)")
    else:
        for app in (api, worker):
            state = _run(
                [
                    "az",
                    "containerapp",
                    "revision",
                    "list",
                    "--name",
                    app,
                    "--resource-group",
                    args.resource_group,
                    "--query",
                    "[?properties.active].properties.runningState",
                    "-o",
                    "tsv",
                ],
            )
            print(f"   {app}: {state or 'unknown'}")
        print("\n   Revisions take a moment to roll. Re-check, then run the")
        print("   end-to-end probe before trusting this.")

    print("\n" + "=" * 78)
    print("Done." if not dry else "Dry run complete — nothing changed.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
