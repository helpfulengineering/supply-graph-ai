#!/usr/bin/env python3
"""
Test script for AWS ECS Fargate deployer.

This script allows testing the AWS deployer locally before deploying.
"""

import os
import sys
import argparse
import logging
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from deploy.providers.aws import AWSDeploymentConfig, AWSFargateDeployer, DeploymentError

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)


def main():
    """Test AWS deployer."""
    parser = argparse.ArgumentParser(description="Test AWS ECS Fargate deployer")
    parser.add_argument(
        "--region",
        default=os.getenv("AWS_REGION", "us-east-1"),
        help="AWS region (default: from AWS_REGION env var or us-east-1)",
    )
    parser.add_argument(
        "--cluster",
        required=True,
        help="ECS cluster name",
    )
    parser.add_argument(
        "--subnet",
        required=True,
        action="append",
        dest="subnets",
        help="Subnet ID (can be specified multiple times)",
    )
    parser.add_argument(
        "--security-group",
        required=True,
        action="append",
        dest="security_groups",
        help="Security group ID (can be specified multiple times)",
    )
    parser.add_argument(
        "--execution-role-arn",
        default=os.getenv("AWS_ECS_EXECUTION_ROLE_ARN"),
        help="ECS execution role ARN (or set AWS_ECS_EXECUTION_ROLE_ARN env var)",
    )
    parser.add_argument(
        "--task-role-arn",
        default=os.getenv("AWS_ECS_TASK_ROLE_ARN"),
        help="ECS task role ARN (optional, or set AWS_ECS_TASK_ROLE_ARN env var)",
    )
    parser.add_argument(
        "--ecr-repository",
        default=os.getenv("AWS_ECR_REPOSITORY", "supply-graph-ai"),
        help="ECR repository name (default: from AWS_ECR_REPOSITORY env var or supply-graph-ai)",
    )
    parser.add_argument(
        "--image",
        default=None,
        help="Docker image (default: constructed from ECR repository)",
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
        help="Dry run mode - don't execute actual AWS commands (default: True)",
    )
    parser.add_argument(
        "--no-dry-run",
        action="store_false",
        dest="dry_run",
        help="Execute actual AWS commands (requires authentication)",
    )

    args = parser.parse_args()

    # Build image if not provided
    if not args.image:
        # Try to get account ID
        import subprocess
        try:
            account_id = subprocess.check_output(
                ["aws", "sts", "get-caller-identity", "--query", "Account", "--output", "text"],
                text=True,
            ).strip()
            args.image = f"{account_id}.dkr.ecr.{args.region}.amazonaws.com/{args.ecr_repository}:latest"
        except Exception:
            args.image = f"123456789012.dkr.ecr.{args.region}.amazonaws.com/{args.ecr_repository}:latest"
            print(f"⚠️  Could not get AWS account ID, using placeholder: {args.image}")

    if not args.execution_role_arn:
        print("❌ Error: --execution-role-arn is required or set AWS_ECS_EXECUTION_ROLE_ARN env var")
        return 1

    print("=" * 80)
    print("AWS ECS Fargate Deployer Test Suite")
    print("=" * 80)
    print(f"Region: {args.region}")
    print(f"Cluster: {args.cluster}")
    print(f"Service Name: {args.service_name}")
    print(f"Image: {args.image}")
    print(f"Subnets: {', '.join(args.subnets)}")
    print(f"Security Groups: {', '.join(args.security_groups)}")
    print(f"Execution Role: {args.execution_role_arn}")
    print(f"Dry Run: {args.dry_run}")
    print("=" * 80)

    try:
        # Create configuration
        config = AWSDeploymentConfig.with_defaults(
            region=args.region,
            service_name=args.service_name,
            image=args.image,
            environment_vars={
                "ENVIRONMENT": "production",
                "STORAGE_PROVIDER": "s3",
            },
            provider_config={
                "cluster": args.cluster,
                "subnets": args.subnets,
                "security_groups": args.security_groups,
                "execution_role_arn": args.execution_role_arn,
                "task_role_arn": args.task_role_arn,
            },
        )

        # Create deployer
        deployer = AWSFargateDeployer(config)

        print("\n✅ Configuration created successfully")
        print(f"   Cluster: {deployer.cluster}")
        print(f"   Region: {deployer.config.region}")
        print(f"   Service: {deployer.config.service.name}")
        print(f"   Memory (MB): {deployer._convert_memory_to_mb('4Gi')}")
        print(f"   CPU units: {deployer._convert_cpu_to_units(2)}")

        if args.dry_run:
            print("\n⏭️  Dry run mode - skipping actual deployment")
            print("\n✅ All tests passed!")
            print("\nNext steps:")
            print("1. Verify AWS CLI is configured: aws configure")
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

