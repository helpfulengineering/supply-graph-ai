#!/usr/bin/env python3
"""Deploy the OHM **Celery worker** container to Azure Container Apps.

The worker runs the SAME image as the API in ``worker`` mode, with no ingress:
it serves no HTTP and only consumes jobs from the Redis broker.

Its container env comes from the shared config surface — the top-level settings
in ``config/environments/<environment>.toml`` plus that file's ``[worker.env]``
table — so the storage target is declared exactly once and the API and worker
cannot drift apart. Deploy shape (cpu, memory, replicas) comes from the same
file's ``[worker]`` table; CLI flags override it for one-off runs.

Secrets are provisioned, not assumed:

* the three Redis URLs are minted from the key Azure holds (same generator the
  backend deploy uses), and
* the storage key and git access tokens are MIRRORED from the API app, so the
  two apps' copies cannot diverge.

Unlike ``deploy_azure.py`` / ``deploy_azure_frontend.py``, this script will
CREATE the container app if it does not exist — the shared deployer supports
ingress-less apps, so no hand-built app is required.
"""

import argparse
import logging
import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from deploy.providers.azure import (
    AzureContainerAppsDeployer,
    AzureDeploymentConfig,
    DeploymentError,
)
from deploy.providers.azure.app_secrets import (
    mirrored_secret_env_vars,
    mirrored_secret_names,
)
from deploy.providers.azure.key_vault import (
    container_app_secrets,
    secret_env_vars as vault_secret_env_vars,
)
from deploy.providers.azure.redis_secrets import (
    build_redis_secret_values,
    redis_secret_env_vars,
)
from src.config.schema import (
    key_vault_name,
    redis_deploy_config,
    worker_deploy_config,
    worker_deploy_env_vars,
)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)

# The image's ENTRYPOINT dispatches on its first argument (api|cli|worker).
# Passing both is explicit about what the container runs, rather than relying on
# how the platform merges an image ENTRYPOINT with overridden args.
WORKER_COMMAND = ["/usr/local/bin/docker-entrypoint.sh"]
WORKER_ARGS = ["worker"]


def main():
    """Deploy the Celery worker to Azure Container Apps."""
    parser = argparse.ArgumentParser(
        description="Deploy the OHM Celery worker to Azure"
    )
    parser.add_argument(
        "--resource-group",
        default="project_data_rg",
        help="Azure resource group (default: project_data_rg)",
    )
    parser.add_argument(
        "--subscription-id",
        default=None,
        help="Azure subscription ID (or set AZURE_SUBSCRIPTION_ID)",
    )
    parser.add_argument(
        "--container-app-name",
        default="openhardwaremanager-worker",
        help="Worker Container App name (default: openhardwaremanager-worker)",
    )
    parser.add_argument(
        "--container-app-env",
        default="ohm-env",
        help="Container Apps environment, used only when creating (default: ohm-env)",
    )
    parser.add_argument(
        "--api-container-app-name",
        default="openhardwaremanager",
        help=(
            "App to mirror shared secrets FROM (default: openhardwaremanager). "
            "The API app is the single source for the storage key and git tokens."
        ),
    )
    parser.add_argument(
        "--region",
        default="eastus",
        help="Azure region, only used if the resource group needs creating",
    )
    parser.add_argument(
        "--image",
        required=True,
        help="Image to deploy — the SAME image as the API (e.g. touchthesun/openhardwaremanager@sha256:…)",
    )
    parser.add_argument(
        "--environment",
        default="production",
        help=(
            "Target environment; selects config/environments/<env>.toml [worker] "
            "(default: production). Deliberately NOT read from the ENVIRONMENT env "
            "var — importing src.config loads .env, so inferring the deploy target "
            "from it would let a local .env redirect a prod deploy. Pass explicitly "
            "for anything but production."
        ),
    )
    parser.add_argument("--cpu", type=float, default=None, help="Override [worker].cpu")
    parser.add_argument("--memory", default=None, help="Override [worker].memory")
    parser.add_argument(
        "--min-instances", type=int, default=None, help="Override [worker].min_replicas"
    )
    parser.add_argument(
        "--max-instances", type=int, default=None, help="Override [worker].max_replicas"
    )
    args = parser.parse_args()

    import os

    subscription_id = args.subscription_id or os.getenv("AZURE_SUBSCRIPTION_ID")
    if not subscription_id:
        print("❌ Error: --subscription-id is required or set AZURE_SUBSCRIPTION_ID")
        return 1

    # Deploy shape from the config surface, overridable per-run.
    shape = worker_deploy_config(args.environment)
    if not shape:
        print(
            f"❌ Error: no [worker] table for environment {args.environment!r} in "
            f"config/environments/{args.environment}.toml"
        )
        return 1

    cpu = args.cpu if args.cpu is not None else shape.get("cpu", 1.0)
    memory = args.memory or shape.get("memory", "2Gi")
    min_instances = (
        args.min_instances
        if args.min_instances is not None
        else shape.get("min_replicas", 1)
    )
    max_instances = (
        args.max_instances
        if args.max_instances is not None
        else shape.get("max_replicas", 1)
    )

    # Shared top-level config + [worker.env], then secretRef pointers. No secret
    # VALUE is ever applied as an env var.
    environment_vars = worker_deploy_env_vars(args.environment)
    environment_vars["ENVIRONMENT"] = args.environment

    # With a vault, the worker references the same secrets the API does — one
    # value, two pointers — so there is nothing to mirror and no value to hold.
    vault = key_vault_name(args.environment)
    if vault:
        environment_vars.update(vault_secret_env_vars(worker=True))
    else:
        environment_vars.update(mirrored_secret_env_vars())

    redis_config = redis_deploy_config(args.environment)
    if redis_config and not vault:
        environment_vars.update(redis_secret_env_vars())

    print("=" * 80)
    print("Azure Container Apps Deployment — CELERY WORKER")
    print("=" * 80)
    print(f"Resource Group: {args.resource_group}")
    print(f"Container App: {args.container_app_name}")
    print(f"Image: {args.image}")
    print(f"Environment: {args.environment}")
    print(f"Shape: {cpu} vCPU / {memory}, replicas {min_instances}-{max_instances}")
    print(f"Runs: {' '.join(WORKER_COMMAND + WORKER_ARGS)} (no ingress)")
    print("Applying worker env from the shared config surface:")
    for key, value in sorted(environment_vars.items()):
        print(f"  {key}={value}")
    print("=" * 80)

    try:
        # Resolve secret VALUES before building the config: the deployer sets
        # them ahead of an update, or passes them inline when creating the app
        # (which cannot have secrets set on it before it exists).
        if not vault:
            print(
                f"\n🔑 Mirroring shared secrets from "
                f"{args.api_container_app_name!r}"
            )
        probe = AzureContainerAppsDeployer(
            AzureDeploymentConfig.from_dict(
                {
                    "provider": "azure",
                    "environment": args.environment,
                    "region": args.region,
                    "service": {"name": args.container_app_name, "image": args.image},
                    "providers": {
                        "azure": {
                            "resource_group": args.resource_group,
                            "subscription_id": subscription_id,
                        }
                    },
                }
            )
        )
        if vault:
            # References only. Mirroring a VALUE here would replace the app's
            # Key Vault reference and quietly recreate the duplicate copies the
            # vault exists to remove.
            secrets = container_app_secrets(vault, worker=True)
        else:
            secrets = {
                name: probe.read_secret(name, app_name=args.api_container_app_name)
                for name in mirrored_secret_names()
            }
        if redis_config and not vault:
            print(f"🔑 Minting Redis secrets from {redis_config['resource_name']!r}")
            access_key = probe.fetch_redis_access_key(redis_config["resource_name"])
            secrets.update(build_redis_secret_values(redis_config, access_key))

        config = AzureDeploymentConfig.from_dict(
            {
                "provider": "azure",
                "environment": args.environment,
                "region": args.region,
                "service": {
                    "name": args.container_app_name,
                    "image": args.image,
                    "memory": memory,
                    "cpu": cpu,
                    "min_instances": min_instances,
                    "max_instances": max_instances,
                    "environment_vars": environment_vars,
                    "secrets": secrets,
                    # A worker serves no HTTP: no ingress, and therefore no
                    # public URL to look up after deploying.
                    "ingress_enabled": False,
                    "command": WORKER_COMMAND,
                    "args": WORKER_ARGS,
                },
                "providers": {
                    "azure": {
                        "resource_group": args.resource_group,
                        "subscription_id": subscription_id,
                        "container_app_env": args.container_app_env,
                    }
                },
            }
        )

        deployer = AzureContainerAppsDeployer(config)

        print("\n🚀 Starting worker deployment...")
        deployer.deploy()

        print("\n" + "=" * 80)
        print("✅ Worker Deployment Successful!")
        print("=" * 80)
        print(f"Container App: {args.container_app_name} (no ingress)")
        print("Check it is consuming:")
        print(
            f"  az containerapp logs show -n {args.container_app_name} "
            f"-g {args.resource_group} --tail 50"
        )
        print("Expect a 'celery@... ready.' banner and a connection to the broker.")
        print("=" * 80)
        return 0

    except DeploymentError as e:
        print(f"\n❌ Deployment failed: {e}")
        return 1
    except Exception as e:
        print(f"\n❌ Unexpected error: {e}")
        import traceback

        traceback.print_exc()
        return 1


if __name__ == "__main__":
    sys.exit(main())
