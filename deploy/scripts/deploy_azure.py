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
from src.config.schema import deploy_env_vars

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
        default=os.getenv("ENVIRONMENT", "production"),
        help="Target environment; selects config/environments/<env>.toml (default: production)",
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
                    }
                },
            }
        )

        deployer = AzureContainerAppsDeployer(config)

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
