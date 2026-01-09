"""
Local deployment verification script for backup deployment testing.

This script verifies that the local Docker deployment (localhost:8001) is
accessible and all API endpoints are functioning correctly.
"""

import asyncio
import argparse
import json
import sys
from pathlib import Path
from typing import Dict, Any

# Add project root to path if running directly
if __name__ == "__main__" and not __package__:
    project_root = Path(__file__).parent.parent.parent
    sys.path.insert(0, str(project_root))

from demo.infrastructure.verification import CloudRunVerifier, run_health_check


DEFAULT_LOCAL_URL = "http://localhost:8001"
DEFAULT_TIMEOUT = 10.0  # Local should be faster than Cloud Run


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
    """Run local deployment health check and display results."""
    parser = argparse.ArgumentParser(description="Verify local Docker deployment")
    parser.add_argument(
        "--url",
        type=str,
        default=DEFAULT_LOCAL_URL,
        help=f"Local deployment URL (default: {DEFAULT_LOCAL_URL})",
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="Output results as JSON",
    )
    parser.add_argument(
        "--timeout",
        type=float,
        default=DEFAULT_TIMEOUT,
        help=f"Request timeout in seconds (default: {DEFAULT_TIMEOUT})",
    )
    args = parser.parse_args()

    print("🔍 Verifying local Docker deployment...")
    print(f"URL: {args.url}")
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
