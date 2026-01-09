#!/usr/bin/env python3
"""
Health check script for Cloud Run deployment verification.

This script can be run pre-demo to verify that the Cloud Run deployment
is accessible and all required endpoints are working.

Usage:
    # From project root
    python -m demo.infrastructure.verify_deployment
    python -m demo.infrastructure.verify_deployment --url https://custom-url.com
    
    # Or directly
    python demo/infrastructure/verify_deployment.py
    python demo/infrastructure/verify_deployment.py --url https://custom-url.com
"""

import asyncio
import argparse
import json
import sys
import os
from pathlib import Path
from typing import Dict, Any

# Add project root to path if running directly
if __name__ == "__main__" and not __package__:
    project_root = Path(__file__).parent.parent.parent
    sys.path.insert(0, str(project_root))

from demo.infrastructure.verification import run_health_check


def format_result(result: Dict[str, Any]) -> str:
    """Format a single endpoint result for display."""
    if result.get("accessible"):
        status = "✅"
        status_code = result.get('status_code')
        latency = result.get('latency_ms', 0)
        details = f"Status: {status_code}, Latency: {latency:.2f}ms"
        if result.get("requires_auth"):
            details += " (⚠️ requires authentication)"
    else:
        status = "❌"
        details = f"Error: {result.get('error', 'Unknown error')}"
    return f"{status} {details}"


async def main():
    """Run health check and display results."""
    parser = argparse.ArgumentParser(description="Verify Cloud Run deployment")
    parser.add_argument(
        "--url",
        type=str,
        help="Custom Cloud Run URL (default: uses CLOUD_RUN_URL env var or default)",
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="Output results as JSON",
    )
    args = parser.parse_args()

    print("🔍 Verifying Cloud Run deployment...")
    print(f"URL: {args.url or 'https://supply-graph-ai-1085931013579.us-west1.run.app'}")
    print()

    try:
        results = await run_health_check(base_url=args.url)

        if args.json:
            print(json.dumps(results, indent=2))
        else:
            print("Health Check Results:")
            print("=" * 60)
            print(f"Health Endpoint:     {format_result(results['health'])}")
            print(f"Match Endpoint:      {format_result(results['match_endpoint'])}")
            print(f"OKH Endpoint:        {format_result(results['okh_endpoint'])}")
            print(f"OKW Endpoint:        {format_result(results['okw_endpoint'])}")
            print("=" * 60)

            # Determine overall status
            all_accessible = all(
                result.get("accessible", False) for result in results.values()
            )

            if all_accessible:
                print("\n✅ All endpoints are accessible!")
                return 0
            else:
                print("\n❌ Some endpoints are not accessible. See details above.")
                return 1

    except Exception as e:
        print(f"\n❌ Error running health check: {e}")
        if args.json:
            print(json.dumps({"error": str(e)}, indent=2))
        return 1


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)
