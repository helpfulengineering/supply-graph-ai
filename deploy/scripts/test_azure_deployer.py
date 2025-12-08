#!/usr/bin/env python3
"""
Test script for Azure Container Apps deployer.

This script allows testing the Azure deployer locally before deploying.
"""

import os
import sys
import argparse
import logging
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from deploy.providers.azure import (
    AzureDeploymentConfig,
    AzureContainerAppsDeployer,
    DeploymentError,
)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)


def main():
    """Test Azure deployer."""
    parser = argparse.ArgumentParser(description="Test Azure Container Apps deployer")
    parser.add_argument(
        "--subscription-id",
        required=True,
        help="Azure subscription ID (or set AZURE_SUBSCRIPTION_ID env var)",
    )
    parser.add_argument(
        "--resource-group",
        required=True,
        help="Azure resource group name",
    )
    parser.add_argument(
        "--region",
        default=os.getenv("AZURE_REGION", "eastus"),
        help="Azure region (default: from AZURE_REGION env var or eastus)",
    )
    parser.add_argument(
        "--container-app-env",
        default=os.getenv("AZURE_CONTAINER_APP_ENV"),
        help="Container App environment name (optional, will be created if not exists)",
    )
    parser.add_argument(
        "--registry-server",
        default=os.getenv("AZURE_REGISTRY_SERVER"),
        help="Container registry server (optional, for private images)",
    )
    parser.add_argument(
        "--registry-username",
        default=os.getenv("AZURE_REGISTRY_USERNAME"),
        help="Container registry username (optional)",
    )
    parser.add_argument(
        "--registry-password",
        default=os.getenv("AZURE_REGISTRY_PASSWORD"),
        help="Container registry password (optional)",
    )
    parser.add_argument(
        "--image",
        default="ghcr.io/helpfulengineering/supply-graph-ai:latest",
        help="Docker image (default: ghcr.io/helpfulengineering/supply-graph-ai:latest)",
    )
    parser.add_argument(
        "--service-name",
        default="supply-graph-ai",
        help="Service name (default: supply-graph-ai)",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        default=True,
        help="Dry run mode - don't execute actual Azure commands (default: True)",
    )
    parser.add_argument(
        "--no-dry-run",
        action="store_false",
        dest="dry_run",
        help="Execute actual Azure commands (requires authentication)",
    )

    args = parser.parse_args()

    print("=" * 80)
    print("Azure Container Apps Deployer Test Suite")
    print("=" * 80)
    print(f"Subscription ID: {args.subscription_id}")
    print(f"Resource Group: {args.resource_group}")
    print(f"Region: {args.region}")
    print(f"Service Name: {args.service_name}")
    print(f"Image: {args.image}")
    if args.container_app_env:
        print(f"Container App Environment: {args.container_app_env}")
    if args.registry_server:
        print(f"Registry Server: {args.registry_server}")
    print(f"Dry Run: {args.dry_run}")
    print("=" * 80)

    try:
        # Build provider config
        provider_config = {}
        if args.container_app_env:
            provider_config["container_app_env"] = args.container_app_env
        if args.registry_server:
            provider_config["registry_server"] = args.registry_server
            if args.registry_username:
                provider_config["registry_username"] = args.registry_username
            if args.registry_password:
                provider_config["registry_password"] = args.registry_password

        # Create configuration
        config = AzureDeploymentConfig.with_defaults(
            resource_group=args.resource_group,
            subscription_id=args.subscription_id,
            region=args.region,
            service_name=args.service_name,
            image=args.image,
            environment_vars={
                "ENVIRONMENT": "production",
                "STORAGE_PROVIDER": "azure",
            },
            provider_config=provider_config,
        )

        # Create deployer
        deployer = AzureContainerAppsDeployer(config)

        print("\n✅ Configuration created successfully")
        print(f"   Resource Group: {deployer.resource_group}")
        print(f"   Subscription ID: {deployer.subscription_id}")
        print(f"   Region: {deployer.config.region}")
        print(f"   Service: {deployer.config.service.name}")
        print(f"   Memory (GB): {deployer._convert_memory_to_gb('4Gi')}")

        if args.dry_run:
            print("\n⏭️  Dry run mode - skipping actual deployment")
            print("\n✅ All tests passed!")
            print("\nNext steps:")
            print("1. Verify Azure CLI is configured: az login")
            print("2. Verify you have the required permissions")
            print("3. Run with --no-dry-run to test actual deployment")
        else:
            print("\n🚀 Testing actual deployment...")
            # Test setup
            deployer.setup()
            print("✅ Setup completed successfully")

            # Test status check
            status = deployer.get_status()
            print(f"✅ Status check: {status}")

        return 0

    except DeploymentError as e:
        print(f"\n❌ Deployment error: {e}")
        return 1
    except Exception as e:
        print(f"\n❌ Unexpected error: {e}")
        import traceback

        traceback.print_exc()
        return 1


if __name__ == "__main__":
    sys.exit(main())

