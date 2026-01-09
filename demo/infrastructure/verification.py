"""
Cloud Run deployment verification for demo infrastructure.

This module provides functionality to verify Cloud Run deployment accessibility
and API endpoint functionality for the demo workflow.
"""

import os
import asyncio
from typing import Dict, Any, Optional
import httpx


class CloudRunVerifier:
    """Verifies Cloud Run deployment accessibility and API endpoints."""

    DEFAULT_CLOUD_RUN_URL = "https://supply-graph-ai-1085931013579.us-west1.run.app"
    DEFAULT_TIMEOUT = 20.0  # 20 seconds timeout (increased for slow endpoints)

    def __init__(self, base_url: Optional[str] = None, timeout: float = DEFAULT_TIMEOUT):
        """
        Initialize Cloud Run verifier.

        Args:
            base_url: Base URL for Cloud Run deployment. If None, uses environment
                     variable CLOUD_RUN_URL or default URL.
            timeout: Request timeout in seconds.
        """
        self.base_url = (
            base_url
            or os.getenv("CLOUD_RUN_URL")
            or self.DEFAULT_CLOUD_RUN_URL
        ).rstrip("/")
        self.timeout = timeout

    async def check_health(self) -> Dict[str, Any]:
        """
        Check health endpoint accessibility.

        Returns:
            Dictionary with:
            - accessible: bool - Whether endpoint is accessible
            - status_code: int - HTTP status code (if accessible)
            - latency_ms: float - Response latency in milliseconds
            - response_data: dict - Response JSON data (if accessible and 200)
            - requires_auth: bool - Whether endpoint requires authentication (403)
            - error: str - Error message (if not accessible)
        """
        url = f"{self.base_url}/health"
        
        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.get(url)
                latency_ms = response.elapsed.total_seconds() * 1000
                
                # 200 = accessible and public
                # 403 = accessible but requires authentication
                # Other 4xx/5xx = accessible but error
                is_accessible = response.status_code < 500
                requires_auth = response.status_code == 403
                
                result = {
                    "accessible": is_accessible,
                    "status_code": response.status_code,
                    "latency_ms": latency_ms,
                    "requires_auth": requires_auth,
                }
                
                if response.status_code == 200:
                    try:
                        result["response_data"] = response.json()
                    except Exception:
                        result["response_data"] = None
                else:
                    result["response_data"] = None
                
                return result
        except httpx.TimeoutException as e:
            return {
                "accessible": False,
                "error": f"Request timed out: {str(e)}",
            }
        except httpx.ConnectError as e:
            return {
                "accessible": False,
                "error": f"Connection error: {str(e)}",
            }
        except Exception as e:
            return {
                "accessible": False,
                "error": f"Unexpected error: {str(e)}",
            }

    async def check_match_endpoint(self) -> Dict[str, Any]:
        """
        Check matching endpoint accessibility.

        Returns:
            Dictionary with accessibility information (same format as check_health).
        """
        url = f"{self.base_url}/v1/api/match"
        
        # Use minimal payload for testing
        test_payload = {
            "okh_manifest": {
                "title": "Test",
                "version": "1.0.0",
            }
        }
        
        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.post(url, json=test_payload)
                latency_ms = response.elapsed.total_seconds() * 1000
                
                is_accessible = response.status_code < 500
                requires_auth = response.status_code == 403
                
                result = {
                    "accessible": is_accessible,
                    "status_code": response.status_code,
                    "latency_ms": latency_ms,
                    "requires_auth": requires_auth,
                }
                
                if response.status_code == 200:
                    try:
                        result["response_data"] = response.json()
                    except Exception:
                        result["response_data"] = None
                else:
                    result["response_data"] = None
                
                return result
        except httpx.TimeoutException as e:
            return {
                "accessible": False,
                "error": f"Request timed out: {str(e)}",
            }
        except httpx.ConnectError as e:
            return {
                "accessible": False,
                "error": f"Connection error: {str(e)}",
            }
        except Exception as e:
            return {
                "accessible": False,
                "error": f"Unexpected error: {str(e)}",
            }

    async def check_okh_endpoint(self) -> Dict[str, Any]:
        """
        Check OKH endpoint accessibility.

        Returns:
            Dictionary with accessibility information (same format as check_health).
        """
        url = f"{self.base_url}/v1/api/okh?page=1&page_size=1"
        
        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.get(url)
                latency_ms = response.elapsed.total_seconds() * 1000
                
                is_accessible = response.status_code < 500
                requires_auth = response.status_code == 403
                
                result = {
                    "accessible": is_accessible,
                    "status_code": response.status_code,
                    "latency_ms": latency_ms,
                    "requires_auth": requires_auth,
                }
                
                if response.status_code == 200:
                    try:
                        result["response_data"] = response.json()
                    except Exception:
                        result["response_data"] = None
                else:
                    result["response_data"] = None
                
                return result
        except httpx.TimeoutException as e:
            return {
                "accessible": False,
                "error": f"Request timed out: {str(e)}",
            }
        except httpx.ConnectError as e:
            return {
                "accessible": False,
                "error": f"Connection error: {str(e)}",
            }
        except Exception as e:
            return {
                "accessible": False,
                "error": f"Unexpected error: {str(e)}",
            }

    async def check_okw_endpoint(self) -> Dict[str, Any]:
        """
        Check OKW endpoint accessibility.

        Returns:
            Dictionary with accessibility information (same format as check_health).
        """
        url = f"{self.base_url}/v1/api/okw/search?page=1&page_size=1"
        
        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.get(url)
                latency_ms = response.elapsed.total_seconds() * 1000
                
                is_accessible = response.status_code < 500
                requires_auth = response.status_code == 403
                
                result = {
                    "accessible": is_accessible,
                    "status_code": response.status_code,
                    "latency_ms": latency_ms,
                    "requires_auth": requires_auth,
                }
                
                if response.status_code == 200:
                    try:
                        result["response_data"] = response.json()
                    except Exception:
                        result["response_data"] = None
                else:
                    result["response_data"] = None
                
                return result
        except httpx.TimeoutException as e:
            return {
                "accessible": False,
                "error": f"Request timed out: {str(e)}",
            }
        except httpx.ConnectError as e:
            return {
                "accessible": False,
                "error": f"Connection error: {str(e)}",
            }
        except Exception as e:
            return {
                "accessible": False,
                "error": f"Unexpected error: {str(e)}",
            }


async def run_health_check(base_url: Optional[str] = None) -> Dict[str, Any]:
    """
    Run comprehensive health check for all demo endpoints.

    Args:
        base_url: Optional base URL override.

    Returns:
        Dictionary with results for all endpoint checks.
    """
    verifier = CloudRunVerifier(base_url=base_url)
    
    results = {
        "health": await verifier.check_health(),
        "match_endpoint": await verifier.check_match_endpoint(),
        "okh_endpoint": await verifier.check_okh_endpoint(),
        "okw_endpoint": await verifier.check_okw_endpoint(),
    }
    
    return results


if __name__ == "__main__":
    """Run health check script."""
    import json
    
    async def main():
        results = await run_health_check()
        print(json.dumps(results, indent=2))
        
        # Exit with error code if any endpoint is not accessible
        all_accessible = all(
            result.get("accessible", False)
            for result in results.values()
        )
        exit(0 if all_accessible else 1)
    
    asyncio.run(main())
