#!/usr/bin/env python3
"""Verify the API and worker agree about the secrets they share.

Secrets now live once in Key Vault; each app holds a *reference* resolved
through its managed identity. So the question worth asking changed. Comparing
resolved values proves little when there is only one copy — but two apps can
still be pointed at **different vault secrets**, or one can be left holding an
inline value while the other reads the vault. That is what this checks.

It also reports secrets that are still inline. Those are not automatically
wrong — the platform manages the registry credential itself, and the migration
deliberately leaves pre-rename secrets behind rather than deleting during a
cutover — but an inline copy of a value that should come from the vault is
drift waiting to happen.

No secret value is read at all — only the vault URI each app points at — so the
output is safe to paste anywhere.

Not part of ``make ready``: it needs live cloud credentials, and the merge gate
must stay runnable offline.

Usage:
    make secrets-check
    uv run python deploy/scripts/verify_app_secrets.py --environment staging \\
        --container-app-name openhardwaremanager-staging \\
        --worker-app-name openhardwaremanager-stg-worker
"""

import argparse
import json
import subprocess
import sys
from pathlib import Path

project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from deploy.providers.azure.key_vault import (  # noqa: E402
    WORKER_EXCLUDED_SECRETS,
    secret_refs_for,
)

# Secrets both apps must resolve identically. Sourced from the Key Vault mapping
# so this cannot drift from what the deploys actually wire — reading a separate
# list is how the previous version came to check a renamed-away secret while
# missing the live one.
SHARED_SECRETS = sorted(set(secret_refs_for(worker=True).values()))

# Expected on the API alone: a worker authenticates no callers.
API_ONLY_SECRETS = sorted(
    {
        name
        for env_var, name in secret_refs_for().items()
        if env_var in WORKER_EXCLUDED_SECRETS
    }
)


def _secrets(app: str, resource_group: str) -> dict:
    """Secret name -> its Key Vault URI, or None when the value is inline."""
    result = subprocess.run(
        [
            "az",
            "containerapp",
            "show",
            "--name",
            app,
            "--resource-group",
            resource_group,
            "--query",
            "properties.configuration.secrets",
            "--output",
            "json",
        ],
        capture_output=True,
        text=True,
        check=False,
    )
    if result.returncode != 0:
        raise RuntimeError(
            f"could not read secrets from {app}: {result.stderr.strip()}"
        )
    return {s["name"]: s.get("keyVaultUrl") for s in json.loads(result.stdout or "[]")}


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Verify the API and worker agree about their shared secrets"
    )
    parser.add_argument("--resource-group", default="project_data_rg")
    parser.add_argument("--container-app-name", default="openhardwaremanager")
    parser.add_argument("--worker-app-name", default="openhardwaremanager-worker")
    parser.add_argument("--environment", default="production", help="labels the report")
    args = parser.parse_args()

    api, worker = args.container_app_name, args.worker_app_name
    api_secrets = _secrets(api, args.resource_group)
    worker_secrets = _secrets(worker, args.resource_group)

    print("=" * 78)
    print(f"Shared secret check — {args.environment}")
    print(f"  api:    {api}")
    print(f"  worker: {worker}")
    print("=" * 78)

    problems: list[str] = []

    for name in SHARED_SECRETS:
        if name not in api_secrets:
            problems.append(f"{name}: missing from {api}")
            print(f"  ✗ {name:24} missing from api")
            continue
        if name not in worker_secrets:
            problems.append(f"{name}: missing from {worker}")
            print(f"  ✗ {name:24} missing from worker")
            continue

        api_uri, worker_uri = api_secrets[name], worker_secrets[name]
        if api_uri != worker_uri:
            problems.append(f"{name}: apps reference different sources")
            print(f"  ✗ {name:24} DIFFERENT sources")
            print(f"      api    → {api_uri or 'inline value'}")
            print(f"      worker → {worker_uri or 'inline value'}")
        elif api_uri:
            print(f"  ✓ {name:24} same vault secret")
        else:
            # Both inline and therefore equal only by luck; nothing keeps them so.
            problems.append(f"{name}: still an inline copy on both apps")
            print(f"  ✗ {name:24} inline on both — not vault-backed")

    for name in API_ONLY_SECRETS:
        if name not in api_secrets:
            problems.append(f"{name}: missing from {api}")
            print(f"  ✗ {name:24} missing from api (API-only secret)")
        else:
            print(f"  · {name:24} api only (expected)")

    leftovers = {
        app_name: sorted(
            name
            for name, uri in secrets.items()
            if uri is None and name not in API_ONLY_SECRETS
        )
        for app_name, secrets in ((api, api_secrets), (worker, worker_secrets))
    }
    if any(leftovers.values()):
        print("\n  Inline secrets (not vault-backed):")
        for app_name, names in leftovers.items():
            for name in names:
                note = " ← platform-managed" if "registry" in name else ""
                print(f"    {app_name}: {name}{note}")
        print("  Expected during a migration; remove once references are trusted.")

    print("=" * 78)
    if problems:
        print("❌ Problems:")
        for problem in problems:
            print(f"   - {problem}")
        return 1

    print("✅ Both apps reference the same vault secret for every shared value.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
