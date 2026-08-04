#!/usr/bin/env python3
"""
Manual deployment script for Azure Container Apps.

This script uses the Azure deployer to update the running container app's image
and to authoritatively apply the **non-secret** per-environment configuration
from ``config/environments/<environment>.toml`` (storage provider / account /
container, etc.) via ``--set-env-vars``. Secrets (storage keys, LLM encryption
secrets, API keys) are never applied here -- they stay Azure ``secretRef`` /
``.env`` only, and the additive update path leaves them untouched.
"""

import argparse
import logging
import os
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
from src.config.schema import deploy_env_vars, key_vault_name, redis_deploy_config

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)


def main():
    """Deploy to Azure Container Apps."""
    parser = argparse.ArgumentParser(description="Deploy to Azure Container Apps")
    parser.add_argument(
        "--resource-group",
        default=os.getenv("AZURE_RESOURCE_GROUP", "project_data_rg"),
        help="Azure resource group (default: from AZURE_RESOURCE_GROUP env var or project_data_rg)",
    )
    parser.add_argument(
        "--subscription-id",
        default=os.getenv("AZURE_SUBSCRIPTION_ID"),
        help="Azure subscription ID (or set AZURE_SUBSCRIPTION_ID env var)",
    )
    parser.add_argument(
        "--container-app-name",
        default=os.getenv("AZURE_CONTAINER_APP_NAME", "openhardwaremanager"),
        help="Container App name (default: from AZURE_CONTAINER_APP_NAME env var or openhardwaremanager)",
    )
    parser.add_argument(
        "--region",
        default=os.getenv("AZURE_REGION", "eastus"),
        help="Azure region, only used if the resource group needs creating (default: eastus)",
    )
    parser.add_argument(
        "--image",
        required=True,
        help="Docker image to deploy (e.g., touchthesun/openhardwaremanager:0.8.6)",
    )
    parser.add_argument(
        "--environment",
        default="production",
        help=(
            "Target environment; selects config/environments/<env>.toml "
            "(default: production). Deliberately NOT read from the ENVIRONMENT "
            "env var: importing src.config loads .env, so inferring the deploy "
            "target from it would let a developer's local .env redirect a prod "
            "deploy. Pass --environment explicitly for anything but production."
        ),
    )
    parser.add_argument(
        "--cors-origins",
        default=os.getenv("CORS_ORIGINS", "*"),
        help='CORS_ORIGINS value to set (default: "*" -- supply-graph-ai is a public API)',
    )
    parser.add_argument(
        "--memory",
        default="2Gi",
        help="Memory allocation (default: 2Gi)",
    )
    parser.add_argument(
        "--cpu",
        type=float,
        default=1,
        help="CPU allocation (default: 1)",
    )
    parser.add_argument(
        "--min-instances",
        type=int,
        default=1,
        help="Minimum instances (default: 1)",
    )
    parser.add_argument(
        "--max-instances",
        type=int,
        default=3,
        help="Maximum instances (default: 3)",
    )

    parser.add_argument(
        "--mirror-secrets-from",
        default=None,
        help=(
            "Copy the shared secrets (storage key, API keys, git tokens) from "
            "this container app onto the target, and wire the matching secretRef "
            "env vars. Needed when STANDING UP a new environment, whose app has "
            "no secrets yet. Omit for an established app (e.g. production, which "
            "is itself the source) — the deploy then leaves its secrets untouched."
        ),
    )
    parser.add_argument(
        "--container-app-env",
        default="ohm-env",
        help=(
            "Container Apps environment, used only when CREATING an app "
            "(default: ohm-env). Ignored when updating an existing app."
        ),
    )
    parser.add_argument(
        "--target-port",
        type=int,
        default=8001,
        help=(
            "Container port for ingress, used only when CREATING an app "
            "(default: 8001 — the port this image's entrypoint binds by default)."
        ),
    )

    args = parser.parse_args()

    if not args.subscription_id:
        print(
            "❌ Error: --subscription-id is required or set AZURE_SUBSCRIPTION_ID environment variable"
        )
        return 1

    # Authoritatively apply the non-secret per-environment config (storage
    # provider / account / container, etc.) from config/environments/<env>.toml,
    # plus the runtime ENVIRONMENT and CORS_ORIGINS. Secrets are NOT included:
    # deploy_env_vars() refuses schema-secret keys, and the additive
    # --set-env-vars update leaves existing secretRefs (e.g. AZURE_STORAGE_KEY)
    # untouched.
    environment_vars = deploy_env_vars(args.environment)
    environment_vars["ENVIRONMENT"] = args.environment
    environment_vars["CORS_ORIGINS"] = args.cors_origins

    # Redis URLs are schema secrets, so they are never applied as values — the
    # env vars carry `secretref:` pointers to secrets minted below from the key
    # Azure holds. Setting JOB_* here does NOT enable async jobs: jobs_available()
    # also requires JOBS_ENABLED, which stays off until it is turned on
    # deliberately in the production config.
    redis_config = redis_deploy_config(args.environment)
    if redis_config:
        environment_vars.update(redis_secret_env_vars())

    # With a vault, every secret env var points at a reference and the deploy
    # never handles a value. Without one, standing up a new environment still
    # needs the values mirrored from an established app.
    vault = key_vault_name(args.environment)
    if vault:
        environment_vars.update(vault_secret_env_vars())
    elif args.mirror_secrets_from:
        environment_vars.update(mirrored_secret_env_vars(include_api_keys=True))

    print("=" * 80)
    print("Azure Container Apps Deployment")
    print("=" * 80)
    print(f"Resource Group: {args.resource_group}")
    print(f"Container App: {args.container_app_name}")
    print(f"Image: {args.image}")
    print(f"Environment: {args.environment}")
    print("Applying non-secret env vars (secrets stay secretRef, untouched):")
    for key, value in environment_vars.items():
        print(f"  {key}={value}")
    print("=" * 80)

    try:
        config = AzureDeploymentConfig.from_dict(
            {
                "provider": "azure",
                "environment": args.environment,
                "region": args.region,
                "service": {
                    "name": args.container_app_name,
                    "image": args.image,
                    "memory": args.memory,
                    "cpu": args.cpu,
                    "min_instances": args.min_instances,
                    "max_instances": args.max_instances,
                    # Only applied when creating; an update never sets ingress.
                    "port": args.target_port,
                    # UPDATE to an existing container app via --set-env-vars
                    # (additive): applies the non-secret per-env values below and
                    # leaves everything else (secretRefs incl. AZURE_STORAGE_KEY,
                    # LLM encryption secrets) untouched.
                    "environment_vars": environment_vars,
                },
                "providers": {
                    "azure": {
                        "resource_group": args.resource_group,
                        "subscription_id": args.subscription_id,
                        "container_app_env": args.container_app_env,
                    }
                },
            }
        )

        deployer = AzureContainerAppsDeployer(config)

        # Mint the Redis URLs from the key Azure holds. Doing this every deploy
        # makes Azure the single source of truth for the credential: rotating
        # the key needs no repo change, and apps sharing the instance cannot
        # drift apart. The deployer sets them before the update that references
        # them — a secretRef to a secret that does not exist yet fails.
        secrets = {}

        if vault:
            # References, not values. Setting a value here would REPLACE the
            # Key Vault reference on the app and silently undo the migration —
            # the deploy would succeed and the app would work, on a copy.
            secrets.update(container_app_secrets(vault))
        elif args.mirror_secrets_from:
            print(f"\n🔑 Mirroring shared secrets from {args.mirror_secrets_from!r}")
            secrets.update(
                {
                    name: deployer.read_secret(name, app_name=args.mirror_secrets_from)
                    for name in mirrored_secret_names(include_api_keys=True)
                }
            )

        if redis_config:
            print(
                f"\n🔑 Minting Redis secrets from {redis_config['resource_name']!r} "
                f"(cache db {redis_config['cache_db']}, broker db "
                f"{redis_config['broker_db']}, results db {redis_config['results_db']})"
            )
            access_key = deployer.fetch_redis_access_key(redis_config["resource_name"])
            minted = build_redis_secret_values(redis_config, access_key)
            if vault:
                # The value belongs in the vault; the app already references it.
                for name, url in minted.items():
                    deployer.write_vault_secret(vault, name, url)
            else:
                secrets.update(minted)
        else:
            print(
                f"\nℹ️  No [redis] table for environment {args.environment!r}; "
                "leaving Redis secrets untouched."
            )

        config.service.secrets = secrets

        print("\n🚀 Starting deployment...")
        service_url = deployer.deploy()

        print("\n" + "=" * 80)
        print("✅ Deployment Successful!")
        print("=" * 80)
        print(f"Service URL: {service_url}")
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
