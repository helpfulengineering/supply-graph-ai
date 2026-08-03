#!/usr/bin/env python3
"""Verify the API and worker container apps agree on their shared secrets.

The deploys mirror these secrets from the API app on every run, so they cannot
drift across a deploy. This confirms that actually took effect, and catches the
two cases mirroring cannot: a half-completed deploy, and someone editing a
secret directly in the portal afterwards.

Compares **digests**, never values, so the output is safe to paste anywhere.

The sharp one is the broker URL. An API and worker pointed at different Redis
databases means jobs are accepted and never consumed — no error in either app,
a progress bar at 0%, and nothing that looks wrong until you compare the two.

Not part of ``make ready``: it needs live cloud credentials, and the merge gate
must stay runnable offline.

Usage:
    uv run python deploy/scripts/verify_app_secrets.py
    uv run python deploy/scripts/verify_app_secrets.py --environment staging \\
        --container-app-name openhardwaremanager-staging \\
        --worker-app-name openhardwaremanager-stg-worker
"""

import argparse
import hashlib
import subprocess
import sys
from pathlib import Path

project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from deploy.providers.azure.app_secrets import (  # noqa: E402
    API_ONLY_SECRET_ENV_REFS,
    mirrored_secret_names,
)
from deploy.providers.azure.redis_secrets import (  # noqa: E402
    SECRET_CACHE_URL,
    SECRET_JOB_BROKER_URL,
    SECRET_JOB_RESULT_BACKEND,
)

# Secrets both apps must hold identically. The Redis URLs are included because a
# broker mismatch is invisible in either app on its own.
SHARED_SECRETS = sorted(
    set(mirrored_secret_names())
    | {SECRET_CACHE_URL, SECRET_JOB_BROKER_URL, SECRET_JOB_RESULT_BACKEND}
)

# Expected on the API only — a worker authenticates no callers. Absence from the
# worker is correct, not drift.
API_ONLY_SECRETS = sorted(set(API_ONLY_SECRET_ENV_REFS.values()))


def _digest(value: str) -> str:
    """Short, stable fingerprint. Never reveals the secret."""
    return hashlib.sha256(value.encode("utf-8")).hexdigest()[:12]


def _read_secret(app: str, resource_group: str, name: str) -> str | None:
    result = subprocess.run(
        [
            "az",
            "containerapp",
            "secret",
            "show",
            "--name",
            app,
            "--resource-group",
            resource_group,
            "--secret-name",
            name,
            "--query",
            "value",
            "--output",
            "tsv",
        ],
        capture_output=True,
        text=True,
        check=False,
    )
    if result.returncode != 0:
        return None
    value = result.stdout.strip()
    return value or None


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Verify the API and worker agree on their shared secrets"
    )
    parser.add_argument("--resource-group", default="project_data_rg")
    parser.add_argument("--container-app-name", default="openhardwaremanager")
    parser.add_argument("--worker-app-name", default="openhardwaremanager-worker")
    parser.add_argument(
        "--environment",
        default="production",
        help="Labels the report only; secret names are the same across environments",
    )
    args = parser.parse_args()

    api, worker = args.container_app_name, args.worker_app_name

    print("=" * 78)
    print(f"Shared secret check — {args.environment}")
    print(f"  api:    {api}")
    print(f"  worker: {worker}")
    print("=" * 78)

    problems: list[str] = []

    for name in SHARED_SECRETS:
        api_value = _read_secret(api, args.resource_group, name)
        worker_value = _read_secret(worker, args.resource_group, name)

        if api_value is None and worker_value is None:
            problems.append(f"{name}: missing from BOTH apps")
            print(f"  ✗ {name:24} missing from both")
            continue
        if api_value is None:
            problems.append(f"{name}: missing from {api}")
            print(f"  ✗ {name:24} missing from api")
            continue
        if worker_value is None:
            problems.append(f"{name}: missing from {worker}")
            print(f"  ✗ {name:24} missing from worker")
            continue

        api_digest, worker_digest = _digest(api_value), _digest(worker_value)
        if api_digest != worker_digest:
            problems.append(
                f"{name}: differs (api {api_digest} != worker {worker_digest})"
            )
            print(f"  ✗ {name:24} DIFFERS  api={api_digest} worker={worker_digest}")
        else:
            print(f"  ✓ {name:24} agree    {api_digest}")

    for name in API_ONLY_SECRETS:
        if _read_secret(api, args.resource_group, name) is None:
            problems.append(f"{name}: missing from {api}")
            print(f"  ✗ {name:24} missing from api (API-only secret)")
        else:
            print(f"  · {name:24} api only (expected)")

    print("=" * 78)
    if problems:
        print("❌ Secret drift detected:")
        for problem in problems:
            print(f"   - {problem}")
        print("\nRe-run the deploys to re-mirror, or fix the source app's secret.")
        return 1

    print("✅ The API and worker agree on every shared secret.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
