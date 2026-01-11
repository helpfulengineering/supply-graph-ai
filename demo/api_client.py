"""
API Client for OHM Demo Interface

Provides functions to interact with the OHM API for fetching
OKH designs, OKW facilities, and executing matches.
"""

import os
import httpx
from typing import Dict, Any, List, Optional
import logging

logger = logging.getLogger(__name__)

# Default API URL (can be overridden via environment variable)
DEFAULT_API_URL = "https://supply-graph-ai-1085931013579.us-west1.run.app"
API_BASE_URL = os.getenv("CLOUD_RUN_URL", DEFAULT_API_URL).rstrip("/")
DEFAULT_TIMEOUT = 30.0  # 30 seconds timeout for API calls
MATCHING_TIMEOUT = 120.0  # 2 minutes timeout for matching operations (can be slow)


class APIClient:
    """Client for interacting with OHM API."""
    
    def __init__(self, base_url: Optional[str] = None, timeout: float = DEFAULT_TIMEOUT):
        """
        Initialize API client.
        
        Args:
            base_url: Base URL for API. If None, uses environment variable
                     CLOUD_RUN_URL or default URL.
            timeout: Request timeout in seconds.
        """
        self.base_url = (base_url or API_BASE_URL).rstrip("/")
        self.timeout = timeout
    
    async def _request(
        self,
        method: str,
        endpoint: str,
        params: Optional[Dict[str, Any]] = None,
        json_data: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """
        Make HTTP request to API.
        
        Args:
            method: HTTP method (GET, POST, etc.)
            endpoint: API endpoint path (e.g., "/v1/api/okh")
            params: Query parameters
            json_data: JSON body for POST requests
            
        Returns:
            Response JSON data
            
        Raises:
            httpx.HTTPError: If request fails
        """
        url = f"{self.base_url}{endpoint}"
        
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            if method.upper() == "GET":
                response = await client.get(url, params=params)
            elif method.upper() == "POST":
                response = await client.post(url, params=params, json=json_data)
            else:
                raise ValueError(f"Unsupported HTTP method: {method}")
            
            # Try to get error details before raising
            if response.status_code >= 400:
                try:
                    error_data = response.json()
                    error_detail = error_data.get("detail", str(response.status_code))
                    # Create a more informative error message
                    error_msg = f"API Error ({response.status_code}): {error_detail}"
                    if isinstance(error_detail, dict):
                        # If detail is a dict, try to extract message
                        error_msg = error_data.get("message", str(error_detail))
                    raise httpx.HTTPStatusError(
                        error_msg,
                        request=response.request,
                        response=response
                    )
                except (ValueError, KeyError):
                    # If we can't parse the error, use the default behavior
                    pass
            
            response.raise_for_status()
            return response.json()
    
    async def get_okh_designs(
        self,
        page: int = 1,
        page_size: int = 100,
        timeout: Optional[float] = None
    ) -> Dict[str, Any]:
        """
        Fetch OKH designs from API.
        
        Args:
            page: Page number (1-indexed)
            page_size: Number of items per page
            timeout: Optional timeout override (default: uses instance timeout)
            
        Returns:
            API response with OKH designs
        """
        # Use longer timeout for OKH loading (can be slow with many designs)
        okh_timeout = timeout or 60.0  # 60 seconds for OKH designs
        
        # Temporarily override timeout for this request
        original_timeout = self.timeout
        self.timeout = okh_timeout
        try:
            return await self._request(
                "GET",
                "/v1/api/okh",
                params={"page": page, "page_size": page_size}
            )
        finally:
            # Restore original timeout
            self.timeout = original_timeout
    
    async def get_okw_facilities(
        self,
        page: int = 1,
        page_size: int = 100,
        timeout: Optional[float] = None
    ) -> Dict[str, Any]:
        """
        Fetch OKW facilities from API.
        
        Args:
            page: Page number (1-indexed)
            page_size: Number of items per page
            timeout: Optional timeout override (default: uses instance timeout)
            
        Returns:
            API response with OKW facilities
        """
        # Use longer timeout for facilities loading (can be slow with many facilities)
        facilities_timeout = timeout or 60.0  # 60 seconds for facilities
        
        # Temporarily override timeout for this request
        original_timeout = self.timeout
        self.timeout = facilities_timeout
        try:
            return await self._request(
                "GET",
                "/v1/api/okw/search",
                params={"page": page, "page_size": page_size}
            )
        finally:
            # Restore original timeout
            self.timeout = original_timeout
    
    async def match_facilities(
        self,
        okh_manifest: Dict[str, Any],
        quantity: int = 1,
        location_by_city: Optional[str] = None,
        location_by_distance: Optional[Dict[str, Any]] = None,
        min_confidence: float = 0.3,
        max_depth: Optional[int] = None,
        timeout: Optional[float] = None,
    ) -> Dict[str, Any]:
        """
        Execute facility matching for an OKH design.
        
        Args:
            okh_manifest: OKH manifest dictionary
            quantity: Production quantity (not used by API, kept for compatibility)
            location_by_city: Filter by city name (optional) - maps to "location" field
            location_by_distance: Filter by distance (optional) - dict with "latitude", "longitude", "radius_km"
            min_confidence: Minimum confidence threshold (default: 0.3)
            max_depth: Maximum nesting depth (optional, auto-detect if None)
            
        Returns:
            API response with matching results
        """
        payload = {
            "okh_manifest": okh_manifest,
            "min_confidence": min_confidence,
        }
        
        # Map location_by_city to API's "location" field
        if location_by_city:
            payload["location"] = location_by_city
        
        # Map location_by_distance to API's "location_coords" and "max_distance_km" fields
        if location_by_distance:
            lat = location_by_distance.get("latitude")
            lon = location_by_distance.get("longitude")
            radius_km = location_by_distance.get("radius_km")
            
            if lat is not None and lon is not None:
                # API expects "lng" not "longitude"
                payload["location_coords"] = {"lat": float(lat), "lng": float(lon)}
            
            if radius_km is not None:
                # API expects "max_distance_km" not "radius_km"
                payload["max_distance_km"] = float(radius_km)
        
        if max_depth is not None:
            payload["max_depth"] = max_depth
        
        # Use longer timeout for matching operations
        matching_timeout = timeout or MATCHING_TIMEOUT
        
        # Temporarily override timeout for this request
        original_timeout = self.timeout
        self.timeout = matching_timeout
        try:
            return await self._request(
                "POST",
                "/v1/api/match",
                json_data=payload
            )
        finally:
            # Restore original timeout
            self.timeout = original_timeout
    
    async def check_health(self) -> Dict[str, Any]:
        """
        Check API health status.
        
        Returns:
            Health status response
        """
        return await self._request("GET", "/health")


# Convenience functions for Streamlit
async def fetch_okh_designs() -> List[Dict[str, Any]]:
    """
    Fetch all OKH designs (convenience function).
    
    Returns:
        List of OKH design dictionaries from API response
    """
    client = APIClient()
    response = await client.get_okh_designs(page_size=100)
    # API returns PaginatedResponse with "items" field
    designs = response.get("items", [])
    
    # Convert Pydantic models to dicts if needed
    if designs and hasattr(designs[0], "model_dump"):
        return [d.model_dump() if hasattr(d, "model_dump") else d for d in designs]
    elif designs and hasattr(designs[0], "dict"):
        return [d.dict() if hasattr(d, "dict") else d for d in designs]
    
    return designs


async def fetch_okw_facilities() -> List[Dict[str, Any]]:
    """Fetch all OKW facilities (convenience function)."""
    client = APIClient()
    response = await client.get_okw_facilities(page_size=100)
    # API returns OKWListResponse with "results" field, not "items"
    facilities = response.get("results", [])
    
    # Convert Pydantic models to dicts if needed
    if facilities and hasattr(facilities[0], "model_dump"):
        return [f.model_dump() if hasattr(f, "model_dump") else f for f in facilities]
    elif facilities and hasattr(facilities[0], "dict"):
        return [f.dict() if hasattr(f, "dict") else f for f in facilities]
    
    return facilities
