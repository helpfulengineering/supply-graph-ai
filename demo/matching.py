"""
Matching Execution Module

Provides functions to execute facility matching from the Streamlit demo interface.
"""

import os
import sys
import asyncio
import logging
from typing import Dict, Any, Optional, List
import concurrent.futures

# Add project root to path for imports
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

from demo.api_client import APIClient

logger = logging.getLogger(__name__)


async def _match_facilities_async(
    okh_manifest: Dict[str, Any],
    quantity: int = 1,
    location_by_city: Optional[str] = None,
    location_by_distance: Optional[Dict[str, Any]] = None,
    min_confidence: float = 0.3,
    max_depth: Optional[int] = None,
) -> Dict[str, Any]:
    """
    Execute facility matching (async function).
    
    Args:
        okh_manifest: OKH manifest dictionary
        quantity: Production quantity
        location_by_city: Filter by city name (optional)
        location_by_distance: Filter by distance (optional)
        min_confidence: Minimum confidence threshold (default: 0.3)
        max_depth: Maximum nesting depth (optional, auto-detect if None)
        
    Returns:
        API response with matching results
    """
    client = APIClient()
    return await client.match_facilities(
        okh_manifest=okh_manifest,
        quantity=quantity,
        location_by_city=location_by_city,
        location_by_distance=location_by_distance,
        min_confidence=min_confidence,
        max_depth=max_depth,
    )


def match_facilities(
    okh_manifest: Dict[str, Any],
    quantity: int = 1,
    location_by_city: Optional[str] = None,
    location_by_distance: Optional[Dict[str, Any]] = None,
    min_confidence: float = 0.3,
    max_depth: Optional[int] = None,
) -> Dict[str, Any]:
    """
    Execute facility matching (synchronous wrapper for async function).
    
    Args:
        okh_manifest: OKH manifest dictionary
        quantity: Production quantity
        location_by_city: Filter by city name (optional)
        location_by_distance: Filter by distance (optional)
        min_confidence: Minimum confidence threshold (default: 0.3)
        max_depth: Maximum nesting depth (optional, auto-detect if None)
        
    Returns:
        API response with matching results
        
    Raises:
        Exception: If matching fails
    """
    try:
        # Check if we're in a running event loop (e.g., Streamlit with uvloop)
        try:
            loop = asyncio.get_running_loop()
            # If loop is running (Streamlit uses uvloop which nest_asyncio can't patch)
            # Run the async function in a separate thread with its own event loop
            import concurrent.futures
            
            def run_in_thread():
                """Run async function in a new thread with new event loop"""
                # Create new event loop in this thread (not uvloop)
                new_loop = asyncio.new_event_loop()
                asyncio.set_event_loop(new_loop)
                try:
                    return new_loop.run_until_complete(
                        _match_facilities_async(
                            okh_manifest=okh_manifest,
                            quantity=quantity,
                            location_by_city=location_by_city,
                            location_by_distance=location_by_distance,
                            min_confidence=min_confidence,
                            max_depth=max_depth,
                        )
                    )
                finally:
                    new_loop.close()
            
            with concurrent.futures.ThreadPoolExecutor() as executor:
                future = executor.submit(run_in_thread)
                return future.result(timeout=150)  # 150 second timeout for matching (2.5 minutes)
                
        except RuntimeError:
            # No event loop running, create new one
            return asyncio.run(
                _match_facilities_async(
                    okh_manifest=okh_manifest,
                    quantity=quantity,
                    location_by_city=location_by_city,
                    location_by_distance=location_by_distance,
                    min_confidence=min_confidence,
                    max_depth=max_depth,
                )
            )
    except Exception as e:
        logger.error(f"Failed to execute matching: {e}", exc_info=True)
        raise
