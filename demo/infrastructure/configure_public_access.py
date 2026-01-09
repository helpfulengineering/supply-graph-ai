#!/usr/bin/env python3
"""
Script to configure public access for Cloud Run deployment (Task 1.1.3).

This script updates the Cloud Run service to allow unauthenticated access
for demo purposes.

Usage:
    # Configure public access
    python -m demo.infrastructure.configure_public_access
    
    # Or with custom service name/region
    python -m demo.infrastructure.configure_public_access --service supply-graph-ai --region us-west1
"""

import argparse
import subprocess
import sys
import os
from typing import Optional, Dict, Any


class CloudRunPublicAccessConfigurator:
    """Configures public access for Cloud Run service."""

    DEFAULT_SERVICE_NAME = "supply-graph-ai"
    DEFAULT_REGION = "us-west1"
    DEFAULT_PROJECT_ID = os.getenv("GCP_PROJECT_ID", "nathan-playground-368310")

    def __init__(
        self,
        service_name: Optional[str] = None,
        region: Optional[str] = None,
        project_id: Optional[str] = None,
    ):
        """
        Initialize configurator.

        Args:
            service_name: Cloud Run service name
            region: GCP region
            project_id: GCP project ID
        """
        self.service_name = service_name or self.DEFAULT_SERVICE_NAME
        self.region = region or self.DEFAULT_REGION
        self.project_id = project_id or self.DEFAULT_PROJECT_ID

    def check_current_access(self) -> Dict[str, Any]:
        """
        Check current authentication configuration.

        Returns:
            Dictionary with current access configuration
        """
        try:
            result = subprocess.run(
                [
                    "gcloud",
                    "run",
                    "services",
                    "describe",
                    self.service_name,
                    "--region",
                    self.region,
                    "--format",
                    "json",
                ],
                capture_output=True,
                text=True,
                check=True,
            )

            import json

            service_data = json.loads(result.stdout)
            iam_policy = service_data.get("spec", {}).get("template", {}).get(
                "metadata", {}
            ).get("annotations", {})

            # Check if public access is enabled
            # Cloud Run uses IAM bindings to control access
            # We need to check the IAM policy
            iam_result = subprocess.run(
                [
                    "gcloud",
                    "run",
                    "services",
                    "get-iam-policy",
                    self.service_name,
                    "--region",
                    self.region,
                    "--format",
                    "json",
                ],
                capture_output=True,
                text=True,
            )

            if iam_result.returncode == 0:
                iam_policy_data = json.loads(iam_result.stdout)
                bindings = iam_policy_data.get("bindings", [])

                # Check for allUsers binding (public access)
                has_public_access = any(
                    binding.get("role") == "roles/run.invoker"
                    and "allUsers" in binding.get("members", [])
                    for binding in bindings
                )

                return {
                    "service_exists": True,
                    "public_access": has_public_access,
                    "service_name": self.service_name,
                    "region": self.region,
                }
            else:
                return {
                    "service_exists": False,
                    "error": iam_result.stderr,
                }

        except subprocess.CalledProcessError as e:
            return {
                "service_exists": False,
                "error": e.stderr,
            }
        except FileNotFoundError:
            return {
                "error": "gcloud CLI not found. Please install Google Cloud SDK.",
            }
        except Exception as e:
            return {
                "error": str(e),
            }

    def configure_public_access(self) -> Dict[str, Any]:
        """
        Configure public access for Cloud Run service.

        Returns:
            Dictionary with operation result
        """
        try:
            # Add IAM binding for allUsers (public access)
            result = subprocess.run(
                [
                    "gcloud",
                    "run",
                    "services",
                    "add-iam-policy-binding",
                    self.service_name,
                    "--region",
                    self.region,
                    "--member",
                    "allUsers",
                    "--role",
                    "roles/run.invoker",
                ],
                capture_output=True,
                text=True,
                check=True,
            )

            return {
                "success": True,
                "message": f"Public access configured for {self.service_name}",
                "output": result.stdout,
            }

        except subprocess.CalledProcessError as e:
            return {
                "success": False,
                "error": e.stderr,
                "return_code": e.returncode,
            }
        except FileNotFoundError:
            return {
                "success": False,
                "error": "gcloud CLI not found. Please install Google Cloud SDK.",
            }
        except Exception as e:
            return {
                "success": False,
                "error": str(e),
            }

    def remove_public_access(self) -> Dict[str, Any]:
        """
        Remove public access from Cloud Run service.

        Returns:
            Dictionary with operation result
        """
        try:
            # Remove IAM binding for allUsers
            result = subprocess.run(
                [
                    "gcloud",
                    "run",
                    "services",
                    "remove-iam-policy-binding",
                    self.service_name,
                    "--region",
                    self.region,
                    "--member",
                    "allUsers",
                    "--role",
                    "roles/run.invoker",
                ],
                capture_output=True,
                text=True,
                check=True,
            )

            return {
                "success": True,
                "message": f"Public access removed from {self.service_name}",
                "output": result.stdout,
            }

        except subprocess.CalledProcessError as e:
            return {
                "success": False,
                "error": e.stderr,
                "return_code": e.returncode,
            }
        except FileNotFoundError:
            return {
                "success": False,
                "error": "gcloud CLI not found. Please install Google Cloud SDK.",
            }
        except Exception as e:
            return {
                "success": False,
                "error": str(e),
            }


def main():
    """Main function."""
    parser = argparse.ArgumentParser(
        description="Configure public access for Cloud Run deployment"
    )
    parser.add_argument(
        "--service",
        type=str,
        default=CloudRunPublicAccessConfigurator.DEFAULT_SERVICE_NAME,
        help="Cloud Run service name",
    )
    parser.add_argument(
        "--region",
        type=str,
        default=CloudRunPublicAccessConfigurator.DEFAULT_REGION,
        help="GCP region",
    )
    parser.add_argument(
        "--project",
        type=str,
        default=None,
        help="GCP project ID",
    )
    parser.add_argument(
        "--check",
        action="store_true",
        help="Check current access configuration only",
    )
    parser.add_argument(
        "--remove",
        action="store_true",
        help="Remove public access (restore authentication requirement)",
    )

    args = parser.parse_args()

    configurator = CloudRunPublicAccessConfigurator(
        service_name=args.service,
        region=args.region,
        project_id=args.project,
    )

    if args.check:
        # Just check current status
        status = configurator.check_current_access()
        print("Current Access Configuration:")
        print(f"  Service: {status.get('service_name', 'N/A')}")
        print(f"  Region: {status.get('region', 'N/A')}")
        if status.get("service_exists"):
            if status.get("public_access"):
                print("  ✅ Public access is ENABLED")
            else:
                print("  ⚠️  Public access is DISABLED (authentication required)")
        else:
            print(f"  ❌ Service not found or error: {status.get('error', 'Unknown')}")
        return 0

    if args.remove:
        # Remove public access
        print(f"Removing public access from {args.service}...")
        result = configurator.remove_public_access()
        if result.get("success"):
            print(f"✅ {result.get('message')}")
            return 0
        else:
            print(f"❌ Error: {result.get('error')}")
            return 1

    # Configure public access
    print(f"Configuring public access for {args.service}...")
    print(f"Region: {args.region}")

    # Check current status first
    status = configurator.check_current_access()
    if status.get("public_access"):
        print("✅ Public access is already configured")
        return 0

    # Configure public access
    result = configurator.configure_public_access()
    if result.get("success"):
        print(f"✅ {result.get('message')}")
        print("\nVerifying configuration...")
        
        # Verify
        verify_status = configurator.check_current_access()
        if verify_status.get("public_access"):
            print("✅ Verification successful: Public access is now enabled")
            return 0
        else:
            print("⚠️  Warning: Configuration may not have taken effect yet")
            return 0
    else:
        print(f"❌ Error: {result.get('error')}")
        return 1


if __name__ == "__main__":
    sys.exit(main())
