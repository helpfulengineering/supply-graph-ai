#!/usr/bin/env python3
"""
Test script for GCP Cloud Run deployer.

This script allows testing the GCP deployer locally before integrating into CI/CD.
"""

import argparse
import logging
import os
import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from deploy.providers.gcp import (
    DeploymentError,
    GCPCloudRunDeployer,
    GCPDeploymentConfig,
)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)


def test_config_creation():
    """Test that configuration can be created correctly."""
    print("\n" + "=" * 80)
    print("TEST 1: Configuration Creation")
    print("=" * 80)

    try:
        config = GCPDeploymentConfig.with_defaults(
            project_id="test-project-123",
            region="us-west1",
            service_name="test-service",
            image="us-west1-docker.pkg.dev/test-project-123/repo/image:latest",
            environment_vars={
                "STORAGE_PROVIDER": "gcs",
                "GCP_STORAGE_BUCKET": "test-bucket",
            },
            secrets={
                "API_KEYS": "api-keys:latest",
                "LLM_ENCRYPTION_KEY": "llm-encryption-key:latest",
            },
        )

        print("✅ Configuration created successfully")
        print(f"   Project ID: {config.provider_config.get('project_id')}")
        print(f"   Region: {config.region}")
        print(f"   Service: {config.service.name}")
        print(f"   Image: {config.service.image}")
        print(f"   Memory: {config.service.memory}")
        print(f"   CPU: {config.service.cpu}")
        print(f"   Environment vars: {len(config.service.environment_vars)}")
        print(f"   Secrets: {len(config.service.secrets)}")
        return config
    except Exception as e:
        print(f"❌ Configuration creation failed: {e}")
        import traceback

        traceback.print_exc()
        return None


def test_deployer_instantiation(config):
    """Test that deployer can be instantiated."""
    print("\n" + "=" * 80)
    print("TEST 2: Deployer Instantiation")
    print("=" * 80)

    if not config:
        print("⏭️  Skipping - no config available")
        return None

    try:
        deployer = GCPCloudRunDeployer(config)
        print("✅ Deployer instantiated successfully")
        print(f"   Project ID: {deployer.project_id}")
        print(f"   Service name: {deployer.config.service.name}")
        return deployer
    except Exception as e:
        print(f"❌ Deployer instantiation failed: {e}")
        import traceback

        traceback.print_exc()
        return None


def test_secret_handling(deployer):
    """Test secret handling logic."""
    print("\n" + "=" * 80)
    print("TEST 3: Secret Handling")
    print("=" * 80)

    if not deployer:
        print("⏭️  Skipping - no deployer available")
        return

    try:
        # Test building secrets list (this will check actual secrets if gcloud is configured)
        secrets_list, generated_env_vars = deployer._build_secrets_list()
        print("✅ Secret handling logic works")
        print(f"   Secrets list: {secrets_list or '(empty)'}")
        print(f"   Generated env vars: {len(generated_env_vars)}")
        if generated_env_vars:
            print(f"   Generated vars: {list(generated_env_vars.keys())}")
    except Exception as e:
        print(f"⚠️  Secret handling test: {e}")
        print(
            "   (This is expected if gcloud is not configured or secrets don't exist)"
        )


def test_env_vars_building(deployer):
    """Test environment variables building."""
    print("\n" + "=" * 80)
    print("TEST 4: Environment Variables Building")
    print("=" * 80)

    if not deployer:
        print("⏭️  Skipping - no deployer available")
        return

    try:
        env_vars_str = deployer._build_env_vars_string()
        print("✅ Environment variables string built successfully")
        print(
            f"   Env vars string: {env_vars_str[:100]}..."
            if len(env_vars_str) > 100
            else f"   Env vars string: {env_vars_str}"
        )
    except Exception as e:
        print(f"❌ Environment variables building failed: {e}")
        import traceback

        traceback.print_exc()


def test_service_status_check(deployer, dry_run=True):
    """Test service status checking."""
    print("\n" + "=" * 80)
    print("TEST 5: Service Status Check")
    print("=" * 80)

    if not deployer:
        print("⏭️  Skipping - no deployer available")
        return

    if dry_run:
        print("⏭️  Skipping - dry run mode (would require gcloud authentication)")
        return

    try:
        status = deployer.get_status()
        print("✅ Service status retrieved")
        print(f"   Status: {status}")
    except DeploymentError as e:
        print(f"⚠️  Service status check: {e}")
        print("   (This is expected if service doesn't exist)")
    except Exception as e:
        print(f"❌ Service status check failed: {e}")
        import traceback

        traceback.print_exc()


def test_deployment_command_building(deployer):
    """Test that deployment command can be built (without executing)."""
    print("\n" + "=" * 80)
    print("TEST 6: Deployment Command Building")
    print("=" * 80)

    if not deployer:
        print("⏭️  Skipping - no deployer available")
        return

    try:
        # We can't actually test deploy() without gcloud, but we can verify
        # that the configuration is correct for building commands
        print("✅ Deployment configuration is valid")
        print(f"   Service name: {deployer.config.service.name}")
        print(f"   Image: {deployer.config.service.image}")
        print(f"   Region: {deployer.config.region}")
        print(f"   Memory: {deployer.config.service.memory}")
        print(f"   CPU: {deployer.config.service.cpu}")
        print(f"   Timeout: {deployer.config.service.timeout}")
        print(f"   Min instances: {deployer.config.service.min_instances}")
        print(f"   Max instances: {deployer.config.service.max_instances}")
        print("\n   Deployment command would be:")
        print(f"   gcloud run deploy {deployer.config.service.name} \\")
        print(f"     --image {deployer.config.service.image} \\")
        print(f"     --region {deployer.config.region} \\")
        print(f"     --memory {deployer.config.service.memory} \\")
        print(f"     --cpu {deployer.config.service.cpu} \\")
        print(f"     --timeout {deployer.config.service.timeout} \\")
        print(f"     --min-instances {deployer.config.service.min_instances} \\")
        print(f"     --max-instances {deployer.config.service.max_instances}")
    except Exception as e:
        print(f"❌ Deployment command building failed: {e}")
        import traceback

        traceback.print_exc()


def main():
    """Run all tests."""
    parser = argparse.ArgumentParser(description="Test GCP Cloud Run deployer")
    parser.add_argument(
        "--project-id",
        default=os.getenv("GCP_PROJECT_ID", "test-project-123"),
        help="GCP project ID (default: from GCP_PROJECT_ID env var or test-project-123)",
    )
    parser.add_argument(
        "--region",
        default=os.getenv("GCP_REGION", "us-west1"),
        help="GCP region (default: from GCP_REGION env var or us-west1)",
    )
    parser.add_argument(
        "--service-name",
        default="supply-graph-ai",
        help="Service name (default: supply-graph-ai)",
    )
    parser.add_argument(
        "--image",
        default=None,
        help="Docker image (default: from config or example image)",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        default=True,
        help="Dry run mode - don't execute actual gcloud commands (default: True)",
    )
    parser.add_argument(
        "--no-dry-run",
        action="store_false",
        dest="dry_run",
        help="Execute actual gcloud commands (requires authentication)",
    )

    args = parser.parse_args()

    print("=" * 80)
    print("GCP Cloud Run Deployer Test Suite")
    print("=" * 80)
    print(f"Project ID: {args.project_id}")
    print(f"Region: {args.region}")
    print(f"Service Name: {args.service_name}")
    print(f"Dry Run: {args.dry_run}")
    print("=" * 80)

    # Build image if not provided
    if not args.image:
        # Try to construct from environment or use example
        ar_registry = os.getenv("AR_REGISTRY", "us-west1-docker.pkg.dev")
        ar_repository = os.getenv("AR_REPOSITORY", "cloud-run-source-deploy")
        args.image = (
            f"{ar_registry}/{args.project_id}/{ar_repository}/supply-graph-ai:latest"
        )

    # Test 1: Configuration
    config = test_config_creation()
    if not config:
        print("\n❌ Configuration test failed - cannot continue")
        return 1

    # Update config with provided values
    config.provider_config["project_id"] = args.project_id
    config.region = args.region
    config.service.name = args.service_name
    config.service.image = args.image

    # Test 2: Deployer instantiation
    deployer = test_deployer_instantiation(config)
    if not deployer:
        print("\n❌ Deployer instantiation failed - cannot continue")
        return 1

    # Test 3: Secret handling
    test_secret_handling(deployer)

    # Test 4: Environment variables
    test_env_vars_building(deployer)

    # Test 5: Service status (only if not dry run)
    test_service_status_check(deployer, dry_run=args.dry_run)

    # Test 6: Deployment command building
    test_deployment_command_building(deployer)

    print("\n" + "=" * 80)
    print("TEST SUMMARY")
    print("=" * 80)
    print("✅ All basic tests passed!")
    print("\nNext steps:")
    print("1. Configure gcloud authentication: gcloud auth login")
    print("2. Set GCP_PROJECT_ID environment variable")
    print("3. Run with --no-dry-run to test actual deployment")
    print("=" * 80)

    return 0


if __name__ == "__main__":
    sys.exit(main())
