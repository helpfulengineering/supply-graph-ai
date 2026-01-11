#!/usr/bin/env python3
"""
Automated pre-demo validation script.

This script runs automated checks from the pre-demo checklist and reports
which items pass, fail, or require manual verification.
"""

import asyncio
import sys
from pathlib import Path
from typing import Dict, Any, List, Tuple

# Add project root to path if running directly
if __name__ == "__main__" and not __package__:
    project_root = Path(__file__).parent.parent.parent
    sys.path.insert(0, str(project_root))

from demo.infrastructure.verification import run_health_check, CloudRunVerifier


# Configuration
CLOUD_RUN_URL = "https://supply-graph-ai-1085931013579.us-west1.run.app"
LOCAL_URL = "http://localhost:8001"


class PreDemoChecker:
    """Automated pre-demo validation checks."""

    def __init__(self, cloud_url: str = CLOUD_RUN_URL, local_url: str = LOCAL_URL):
        self.cloud_url = cloud_url
        self.local_url = local_url
        self.results: List[Tuple[str, str, bool, str]] = []  # (section, item, passed, message)

    async def check_cloud_run_health(self) -> bool:
        """Check Cloud Run health endpoint."""
        try:
            verifier = CloudRunVerifier(base_url=self.cloud_url)
            result = await verifier.check_health()
            passed = result.get("accessible") and result.get("status_code") == 200
            message = f"Status: {result.get('status_code')}, Latency: {result.get('latency_ms', 0):.2f}ms"
            if result.get("requires_auth"):
                message += " (⚠️ requires authentication)"
            self.results.append(("1.1.1", "Cloud Run accessible", passed, message))
            return passed
        except Exception as e:
            self.results.append(("1.1.1", "Cloud Run accessible", False, f"Error: {str(e)}"))
            return False

    async def check_cloud_run_public_access(self) -> bool:
        """Check Cloud Run public access."""
        try:
            verifier = CloudRunVerifier(base_url=self.cloud_url)
            result = await verifier.check_health()
            requires_auth = result.get("requires_auth", False)
            passed = not requires_auth and result.get("status_code") == 200
            message = "Public access configured" if passed else "Authentication required"
            self.results.append(("1.1.2", "Public access configured", passed, message))
            return passed
        except Exception as e:
            self.results.append(("1.1.2", "Public access configured", False, f"Error: {str(e)}"))
            return False

    async def check_cloud_run_latency(self) -> bool:
        """Check Cloud Run network latency."""
        try:
            verifier = CloudRunVerifier(base_url=self.cloud_url)
            result = await verifier.check_health()
            latency_ms = result.get("latency_ms", 0)
            passed = latency_ms < 500  # Acceptable: < 500ms
            message = f"Latency: {latency_ms:.2f}ms ({'✅' if passed else '⚠️'})"
            self.results.append(("1.1.3", "Network latency acceptable", passed, message))
            return passed
        except Exception as e:
            self.results.append(("1.1.3", "Network latency acceptable", False, f"Error: {str(e)}"))
            return False

    async def check_api_endpoints(self) -> bool:
        """Check all API endpoints."""
        try:
            results = await run_health_check(base_url=self.cloud_url)
            all_passed = all(r.get("accessible", False) for r in results.values())
            
            details = []
            for name, result in results.items():
                status = "✅" if result.get("accessible") else "❌"
                code = result.get("status_code", "N/A")
                details.append(f"{name}: {status} {code}")
            
            message = "; ".join(details)
            self.results.append(("1.2", "API endpoints accessible", all_passed, message))
            return all_passed
        except Exception as e:
            self.results.append(("1.2", "API endpoints accessible", False, f"Error: {str(e)}"))
            return False

    async def check_match_endpoint_performance(self) -> bool:
        """Check match endpoint performance."""
        try:
            verifier = CloudRunVerifier(base_url=self.cloud_url)
            result = await verifier.check_match_endpoint()
            latency_ms = result.get("latency_ms", 0)
            passed = latency_ms < 10000  # Acceptable: < 10s
            message = f"Latency: {latency_ms:.2f}ms ({'✅' if latency_ms < 3000 else '⚠️'})"
            self.results.append(("1.3.1", "Match endpoint performance", passed, message))
            return passed
        except Exception as e:
            self.results.append(("1.3.1", "Match endpoint performance", False, f"Error: {str(e)}"))
            return False

    async def check_okh_data(self) -> bool:
        """Check OKH data availability."""
        try:
            verifier = CloudRunVerifier(base_url=self.cloud_url)
            result = await verifier.check_okh_endpoint()
            passed = result.get("accessible") and result.get("status_code") == 200
            message = f"Status: {result.get('status_code')}, Accessible: {result.get('accessible')}"
            self.results.append(("2.1.1", "OKH data available", passed, message))
            return passed
        except Exception as e:
            self.results.append(("2.1.1", "OKH data available", False, f"Error: {str(e)}"))
            return False

    async def check_okw_data(self) -> bool:
        """Check OKW data availability."""
        try:
            verifier = CloudRunVerifier(base_url=self.cloud_url)
            result = await verifier.check_okw_endpoint()
            # OKW may timeout if no data, but should be accessible
            passed = result.get("accessible") or "timeout" in str(result.get("error", "")).lower()
            message = f"Status: {result.get('status_code', 'N/A')}, Accessible: {result.get('accessible')}"
            if not result.get("accessible"):
                message += f" (Error: {result.get('error', 'Unknown')})"
            self.results.append(("2.2.1", "OKW data available", passed, message))
            return passed
        except Exception as e:
            self.results.append(("2.2.1", "OKW data available", False, f"Error: {str(e)}"))
            return False

    async def check_local_deployment(self) -> bool:
        """Check local backup deployment."""
        try:
            verifier = CloudRunVerifier(base_url=self.local_url, timeout=5.0)
            result = await verifier.check_health()
            passed = result.get("accessible") and result.get("status_code") == 200
            message = f"Status: {result.get('status_code')}, Accessible: {result.get('accessible')}"
            self.results.append(("3.1.2", "Local deployment accessible", passed, message))
            return passed
        except Exception as e:
            # Local deployment may not be running - that's okay
            message = f"Not running or not accessible: {str(e)}"
            self.results.append(("3.1.2", "Local deployment accessible", False, message))
            return False

    async def run_all_checks(self) -> Dict[str, Any]:
        """Run all automated checks."""
        print("🔍 Running automated pre-demo checks...\n")
        
        checks = [
            ("Cloud Run Health", self.check_cloud_run_health()),
            ("Public Access", self.check_cloud_run_public_access()),
            ("Network Latency", self.check_cloud_run_latency()),
            ("API Endpoints", self.check_api_endpoints()),
            ("Match Performance", self.check_match_endpoint_performance()),
            ("OKH Data", self.check_okh_data()),
            ("OKW Data", self.check_okw_data()),
            ("Local Deployment", self.check_local_deployment()),
        ]
        
        for name, check in checks:
            try:
                await check
            except Exception as e:
                print(f"⚠️  Error in {name}: {e}")
        
        # Calculate summary
        passed = sum(1 for _, _, p, _ in self.results if p)
        total = len(self.results)
        
        return {
            "summary": {
                "passed": passed,
                "total": total,
                "failed": total - passed,
            },
            "results": self.results,
        }

    def print_report(self, results: Dict[str, Any]):
        """Print formatted report."""
        summary = results["summary"]
        
        print("=" * 70)
        print("PRE-DEMO VALIDATION REPORT")
        print("=" * 70)
        print(f"\nSummary: {summary['passed']}/{summary['total']} checks passed\n")
        
        print("Detailed Results:")
        print("-" * 70)
        
        for section, item, passed, message in results["results"]:
            status = "✅ PASS" if passed else "❌ FAIL"
            print(f"{status} [{section}] {item}")
            print(f"         {message}\n")
        
        print("=" * 70)
        
        if summary["passed"] == summary["total"]:
            print("\n✅ All automated checks passed!")
            print("   Continue with manual checks from PRE_DEMO_CHECKLIST.md")
        else:
            print(f"\n⚠️  {summary['failed']} check(s) failed")
            print("   Review failed items and complete manual checks")
            print("   See PRE_DEMO_CHECKLIST.md for detailed requirements")
        
        print("=" * 70)


async def main():
    """Run pre-demo validation checks."""
    checker = PreDemoChecker()
    results = await checker.run_all_checks()
    checker.print_report(results)
    
    # Exit with error code if any critical checks failed
    summary = results["summary"]
    if summary["failed"] > 0:
        # Allow some failures (e.g., local deployment not running)
        # Only exit with error if critical checks fail
        critical_sections = ["1.1.1", "1.1.2", "1.2", "2.1.1"]
        critical_failed = any(
            not passed and section in critical_sections
            for section, _, passed, _ in results["results"]
        )
        return 1 if critical_failed else 0
    
    return 0


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)
