#!/usr/bin/env python3
"""Deploy the OHM **frontend** container to Azure Container Apps.

Updates the frontend container app's image and applies its non-secret
per-environment config (``API_UPSTREAM_URL``, ``PORT``) from the
``[frontend]`` table of ``config/environments/<environment>.toml`` via
``--set-env-vars`` (additive). The frontend has no secrets.

The container app itself (ingress, target port 8080) is provisioned once
out-of-band; this script only updates an existing app, mirroring
``deploy_azure.py`` for the backend.
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
from src.config.schema import frontend_deploy_env_vars

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)


def main():
    """Deploy the frontend to Azure Container Apps."""
    parser = argparse.ArgumentParser(description="Deploy the OHM frontend to Azure")
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
        default="openhardwaremanager-frontend",
        help="Frontend Container App name (default: openhardwaremanager-frontend)",
    )
    parser.add_argument(
        "--region",
        default="eastus",
        help="Azure region, only used if the resource group needs creating",
    )
    parser.add_argument(
        "--image",
        required=True,
        help="Frontend image to deploy (e.g. touchthesun/openhardwaremanager-frontend:0.8.8)",
    )
    parser.add_argument(
        "--environment",
        default="production",
        help=(
            "Target environment; selects config/environments/<env>.toml [frontend] "
            "(default: production). Deliberately NOT read from the ENVIRONMENT env "
            "var — importing src.config loads .env, so inferring the deploy target "
            "from it would let a local .env redirect a prod deploy. Pass explicitly "
            "for anything but production."
        ),
    )
    parser.add_argument(
        "--memory", default="1Gi", help="Memory allocation (default: 1Gi)"
    )
    parser.add_argument(
        "--cpu", type=float, default=0.5, help="CPU allocation (default: 0.5)"
    )
    parser.add_argument("--min-instances", type=int, default=1)
    parser.add_argument("--max-instances", type=int, default=3)
    args = parser.parse_args()

    import os

    subscription_id = args.subscription_id or os.getenv("AZURE_SUBSCRIPTION_ID")
    if not subscription_id:
        print("❌ Error: --subscription-id is required or set AZURE_SUBSCRIPTION_ID")
        return 1

    # Non-secret frontend config from the centralized config surface. The
    # frontend has no secrets; API_UPSTREAM_URL / PORT are the whole surface.
    environment_vars = frontend_deploy_env_vars(args.environment)
    if not environment_vars.get("API_UPSTREAM_URL"):
        print(
            f"❌ Error: no [frontend].api_upstream_url for environment "
            f"{args.environment!r} in config/environments/{args.environment}.toml"
        )
        return 1

    print("=" * 80)
    print("Azure Container Apps Deployment — FRONTEND")
    print("=" * 80)
    print(f"Resource Group: {args.resource_group}")
    print(f"Container App: {args.container_app_name}")
    print(f"Image: {args.image}")
    print(f"Environment: {args.environment}")
    print("Applying frontend config from the config surface:")
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
                    "environment_vars": environment_vars,
                },
                "providers": {
                    "azure": {
                        "resource_group": args.resource_group,
                        "subscription_id": subscription_id,
                    }
                },
            }
        )

        deployer = AzureContainerAppsDeployer(config)

        print("\n🚀 Starting frontend deployment...")
        service_url = deployer.deploy()

        print("\n" + "=" * 80)
        print("✅ Frontend Deployment Successful!")
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
