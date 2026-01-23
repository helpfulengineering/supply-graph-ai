"""
OKH Design Loading and Processing Module

Provides functions to load and process OKH designs from the API
for use in the Streamlit demo interface.
"""

import os
import sys
import asyncio
import logging
from typing import List, Dict, Any, Optional
import concurrent.futures

# Add project root to path for imports
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

from demo.api_client import fetch_okh_designs

logger = logging.getLogger(__name__)


def load_okh_designs() -> List[Dict[str, Any]]:
    """
    Load OKH designs from API (synchronous wrapper for async function).
    
    Returns:
        List of OKH design dictionaries
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
                    return new_loop.run_until_complete(fetch_okh_designs())
                finally:
                    new_loop.close()
            
            with concurrent.futures.ThreadPoolExecutor() as executor:
                future = executor.submit(run_in_thread)
                return future.result(timeout=70)  # 70 second timeout for OKH loading
                
        except RuntimeError:
            # No event loop running, create new one
            return asyncio.run(fetch_okh_designs())
    except Exception as e:
        logger.error(f"Failed to load OKH designs: {e}", exc_info=True)
        return []


def _count_sub_parts_recursive(sub_parts: List[Dict[str, Any]]) -> int:
    """
    Recursively count all sub-parts including nested ones.
    
    Args:
        sub_parts: List of sub-part dictionaries
        
    Returns:
        Total count of all sub-parts (including nested)
    """
    if not sub_parts or not isinstance(sub_parts, list):
        return 0
    
    count = 0
    for sub_part in sub_parts:
        count += 1  # Count this sub-part
        # Recursively count nested sub-parts
        if "sub_parts" in sub_part and isinstance(sub_part["sub_parts"], list):
            count += _count_sub_parts_recursive(sub_part["sub_parts"])
    
    return count


def get_design_metadata(design: Dict[str, Any]) -> Dict[str, Any]:
    """
    Extract metadata from an OKH design for display purposes.
    
    Args:
        design: OKH design dictionary
        
    Returns:
        Dictionary with metadata (name, complexity, component_count, etc.)
    """
    # Extract title/name
    name = design.get("title", "Untitled Design")
    
    # Count top-level parts
    parts = design.get("parts", [])
    top_level_parts = len(parts) if isinstance(parts, list) else 0
    
    # Count sub-parts recursively (including nested ones)
    sub_parts = design.get("sub_parts", [])
    sub_parts_count = _count_sub_parts_recursive(sub_parts) if isinstance(sub_parts, list) else 0
    
    # Total component count = top-level parts + all sub-parts
    component_count = top_level_parts + sub_parts_count
    
    # Determine complexity based on total component count
    # Adjusted thresholds based on actual data (most designs have 2-5 top-level parts,
    # but can have many nested sub-parts)
    if component_count == 0:
        complexity = "Unknown"
    elif component_count <= 3:
        complexity = "Simple"
    elif component_count <= 10:
        complexity = "Medium"
    elif component_count <= 25:
        complexity = "Complex"
    else:
        complexity = "Very Complex"
    
    # Extract other useful metadata
    description = design.get("description", "")
    function = design.get("function", "")
    version = design.get("version", "")
    design_id = design.get("id", "")
    
    return {
        "id": design_id,
        "name": name,
        "description": description,
        "function": function,
        "version": version,
        "component_count": component_count,
        "top_level_parts": top_level_parts,
        "sub_parts_count": sub_parts_count,
        "complexity": complexity,
        "full_design": design,  # Keep full design for matching
    }


def get_okh_designs_for_selection() -> List[Dict[str, Any]]:
    """
    Load and process OKH designs for dropdown selection.
    
    Returns:
        List of design metadata dictionaries suitable for dropdown display
    """
    designs = load_okh_designs()
    
    # Process each design to extract metadata
    processed_designs = []
    for design in designs:
        try:
            metadata = get_design_metadata(design)
            processed_designs.append(metadata)
        except Exception as e:
            logger.warning(f"Failed to process design {design.get('id', 'unknown')}: {e}")
            continue
    
    logger.info(f"Loaded {len(processed_designs)} OKH designs for selection")
    return processed_designs


def get_design_by_id(design_id: str, designs: List[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
    """
    Find a design by ID from a list of designs.
    
    Args:
        design_id: Design ID to find
        designs: List of design metadata dictionaries
        
    Returns:
        Design dictionary if found, None otherwise
    """
    for design in designs:
        if str(design.get("id", "")) == str(design_id):
            return design
    return None
