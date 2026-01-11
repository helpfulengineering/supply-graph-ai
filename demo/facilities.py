"""
OKW Facilities Data Loading and Processing

Functions for loading OKW facilities from the API and preparing
them for visualization (e.g., map display).
"""

import pandas as pd
from typing import List, Dict, Any, Optional, Tuple
import logging
import asyncio
import os
import sys

# Add project root to path for imports
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

from demo.api_client import APIClient, fetch_okw_facilities

logger = logging.getLogger(__name__)


def parse_gps_coordinates(gps_str: Optional[str]) -> Optional[Tuple[float, float]]:
    """
    Parse GPS coordinates from string format.
    
    Args:
        gps_str: GPS coordinates as "lat, lon" string (e.g., "32.159304, -101.541663")
        
    Returns:
        Tuple of (latitude, longitude) or None if parsing fails
    """
    if not gps_str:
        return None
    
    try:
        parts = gps_str.split(",")
        if len(parts) != 2:
            return None
        
        lat = float(parts[0].strip())
        lon = float(parts[1].strip())
        
        # Validate coordinates are in reasonable ranges
        if -90 <= lat <= 90 and -180 <= lon <= 180:
            return (lat, lon)
        else:
            logger.warning(f"GPS coordinates out of range: {gps_str}")
            return None
            
    except (ValueError, AttributeError) as e:
        logger.warning(f"Failed to parse GPS coordinates '{gps_str}': {e}")
        return None


def load_facilities_data() -> List[Dict[str, Any]]:
    """
    Load OKW facilities from API (synchronous wrapper for async function).
    
    Returns:
        List of facility dictionaries
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
                    return new_loop.run_until_complete(fetch_okw_facilities())
                finally:
                    new_loop.close()
            
                with concurrent.futures.ThreadPoolExecutor() as executor:
                    future = executor.submit(run_in_thread)
                    return future.result(timeout=70)  # 70 second timeout for facilities loading
                
        except RuntimeError:
            # No event loop running, create new one
            return asyncio.run(fetch_okw_facilities())
    except Exception as e:
        logger.error(f"Failed to load facilities: {e}", exc_info=True)
        return []


def facilities_to_dataframe(facilities: List[Dict[str, Any]]) -> pd.DataFrame:
    """
    Convert facilities list to pandas DataFrame for map visualization.
    
    Args:
        facilities: List of facility dictionaries from API
        
    Returns:
        DataFrame with columns: lat, lon, name, city, country
    """
    rows = []
    skipped_count = 0
    
    for facility in facilities:
        location = facility.get("location", {})
        gps_str = location.get("gps_coordinates")
        
        if not gps_str:
            skipped_count += 1
            logger.debug(f"Skipping facility '{facility.get('name')}': No GPS coordinates")
            continue
        
        coords = parse_gps_coordinates(gps_str)
        if not coords:
            skipped_count += 1
            logger.debug(f"Skipping facility '{facility.get('name')}': Invalid GPS format '{gps_str}'")
            continue
        
        lat, lon = coords
        
        rows.append({
            "lat": lat,
            "lon": lon,
            "name": facility.get("name", "Unknown"),
            "city": location.get("city") or location.get("address", {}).get("city"),
            "country": location.get("country") or location.get("address", {}).get("country"),
            "facility_status": facility.get("facility_status", "Unknown"),
        })
    
    logger.info(f"Processed {len(facilities)} facilities: {len(rows)} with GPS, {skipped_count} skipped")
    
    if not rows:
        # Return empty DataFrame with correct columns
        return pd.DataFrame(columns=["lat", "lon", "name", "city", "country", "facility_status"])
    
    return pd.DataFrame(rows)


def get_facilities_for_map() -> pd.DataFrame:
    """
    Load facilities and convert to DataFrame for map visualization.
    
    Returns:
        DataFrame ready for st.map() with lat/lon columns
    """
    facilities = load_facilities_data()
    
    # Debug logging
    logger.info(f"Loaded {len(facilities)} facilities from API")
    if facilities:
        logger.info(f"Sample facility keys: {list(facilities[0].keys()) if facilities else 'None'}")
        sample_location = facilities[0].get("location", {}) if facilities else {}
        logger.info(f"Sample location structure: {sample_location}")
    
    return facilities_to_dataframe(facilities)
