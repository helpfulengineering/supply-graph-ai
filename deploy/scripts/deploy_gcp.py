#!/usr/bin/env python3
"""
Manual deployment script for GCP Cloud Run.

This script uses the GCP deployer to deploy the service manually.
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


def main():
    """Deploy to GCP Cloud Run."""
    parser = argparse.ArgumentParser(description="Deploy to GCP Cloud Run")
    parser.add_argument(
        "--project-id",
        required=True,
        help="GCP project ID (or set GCP_PROJECT_ID env var)",
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
        required=True,
        help="Docker image to deploy (e.g., us-west1-docker.pkg.dev/project/repo/image:tag)",
    )
    parser.add_argument(
        "--storage-bucket",
        default=os.getenv("GCP_STORAGE_BUCKET", "supply-graph-ai-storage"),
        help="GCS storage bucket name (default: from GCP_STORAGE_BUCKET env var or supply-graph-ai-storage)",
    )
    parser.add_argument(
        "--service-account",
        default=None,
        help="Service account email (default: supply-graph-ai@PROJECT_ID.iam.gserviceaccount.com)",
    )
    parser.add_argument(
        "--memory",
        default="4Gi",
        help="Memory allocation (default: 4Gi)",
    )
    parser.add_argument(
        "--cpu",
        type=int,
        default=2,
        help="CPU allocation (default: 2)",
    )
    parser.add_argument(
        "--timeout",
        type=int,
        default=300,
        help="Request timeout in seconds (default: 300)",
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
        default=100,
        help="Maximum instances (default: 100)",
    )
    parser.add_argument(
        "--allow-unauthenticated",
        action="store_true",
        help="Allow unauthenticated access (default: False - requires authentication)",
    )

    args = parser.parse_args()

    # Use environment variable if project-id not provided
    project_id = args.project_id or os.getenv("GCP_PROJECT_ID")
    if not project_id:
        print(
            "❌ Error: --project-id is required or set GCP_PROJECT_ID environment variable"
        )
        return 1

    # Build service account email
    service_account = (
        args.service_account or f"supply-graph-ai@{project_id}.iam.gserviceaccount.com"
    )

    print("=" * 80)
    print("GCP Cloud Run Deployment")
    print("=" * 80)
    print(f"Project ID: {project_id}")
    print(f"Region: {args.region}")
    print(f"Service Name: {args.service_name}")
    print(f"Image: {args.image}")
    print(f"Service Account: {service_account}")
    print(f"Memory: {args.memory}")
    print(f"CPU: {args.cpu}")
    print("=" * 80)

    try:
        # Create configuration
        config = GCPDeploymentConfig.with_defaults(
            project_id=project_id,
            region=args.region,
            service_name=args.service_name,
            image=args.image,
            memory=args.memory,
            cpu=args.cpu,
            timeout=args.timeout,
            min_instances=args.min_instances,
            max_instances=args.max_instances,
            environment_vars={
                "ENVIRONMENT": "production",
                "STORAGE_PROVIDER": "gcs",
                "GCP_STORAGE_BUCKET": args.storage_bucket,
                "GCP_PROJECT_ID": project_id,
            },
            secrets={
                "API_KEYS": "api-keys:latest",
                "LLM_ENCRYPTION_KEY": "llm-encryption-key:latest",
                "LLM_ENCRYPTION_SALT": "llm-encryption-salt:latest",
                "LLM_ENCRYPTION_PASSWORD": "llm-encryption-password:latest",
            },
            provider_config={
                "service_account": service_account,
                "allow_unauthenticated": args.allow_unauthenticated,
            },
        )

        # Create deployer
        deployer = GCPCloudRunDeployer(config)

        # Deploy
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
