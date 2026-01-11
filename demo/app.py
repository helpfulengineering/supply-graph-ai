"""
OHM Demo - Multi-Facility Matching Interface

Streamlit application for demonstrating Open Hardware Manager (OHM)
multi-facility matching capabilities with synthetic demo data.
"""

import streamlit as st
import os
import sys
import pandas as pd

# Add project root to path for imports
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

from demo.facilities import get_facilities_for_map
from demo.okh_designs import get_okh_designs_for_selection, get_design_by_id
from demo.matching import match_facilities

# Page configuration
st.set_page_config(
    page_title="OHM Demo - Multi-Facility Matching",
    page_icon="🔧",
    layout="wide",
    initial_sidebar_state="collapsed"
)

# Default API URL (can be overridden via environment variable)
DEFAULT_API_URL = "https://supply-graph-ai-1085931013579.us-west1.run.app"
API_BASE_URL = os.getenv("CLOUD_RUN_URL", DEFAULT_API_URL).rstrip("/")


def main():
    """Main application entry point."""
    
    # Title
    st.title("🔧 OHM Demo - Multi-Facility Matching")
    st.markdown("---")
    
    # Map Section
    st.markdown("## Map Visualization")
    st.markdown("OKW facilities displayed on an interactive map")
    
    # Load and display facilities on map
    with st.spinner("Loading facilities from API... This may take a moment."):
        try:
            facilities_df = get_facilities_for_map()
            
            # Debug: Show raw data info
            with st.expander("Debug Info", expanded=False):
                st.write(f"API URL: {API_BASE_URL}")
                st.write(f"DataFrame shape: {facilities_df.shape}")
                st.write(f"DataFrame columns: {list(facilities_df.columns)}")
                if not facilities_df.empty:
                    st.write("Sample data:")
                    st.dataframe(facilities_df.head())
                else:
                    st.write("⚠️ DataFrame is empty - no facilities loaded")
            
            if facilities_df.empty:
                st.warning("No facilities with GPS coordinates found.")
                st.info("**Possible causes:**")
                st.markdown("- The API returned no facilities")
                st.markdown("- Facilities don't have GPS coordinates in the `gps_coordinates` field")
                st.markdown("- There was an error loading data (check Debug Info and terminal logs)")
                st.markdown("- Async loading failed (check for uvloop/nest_asyncio errors)")
            else:
                st.map(facilities_df[["lat", "lon"]])
                st.success(f"✅ Displaying {len(facilities_df)} facilities on map")
                
                # Show facility count by status
                if "facility_status" in facilities_df.columns:
                    status_counts = facilities_df["facility_status"].value_counts()
                    st.markdown("**Facilities by Status:**")
                    for status, count in status_counts.items():
                        st.markdown(f"- {status}: {count}")
                        
        except Exception as e:
            st.error(f"Failed to load facilities: {e}")
            st.exception(e)
            st.info("💡 **Tip**: Check terminal logs for detailed error messages")
    
    st.markdown("---")
    
    # Controls Section: OKH Design Selection
    st.markdown("## Design Selection")
    
    # Load OKH designs
    with st.spinner("Loading OKH designs... This may take a moment."):
        try:
            designs = get_okh_designs_for_selection()
            
            if not designs:
                st.warning("No OKH designs found. Please ensure the API is accessible and data is loaded.")
                st.info("**Possible causes:**")
                st.markdown("- The API returned no designs")
                st.markdown("- There was an error loading data (check terminal logs)")
                st.markdown("- Async loading failed")
            else:
                # Create dropdown for design selection
                design_options = {
                    f"{d['name']} ({d['complexity']}, {d['component_count']} components)": d['id']
                    for d in designs
                }
                
                selected_design_label = st.selectbox(
                    "Select OKH Design:",
                    options=list(design_options.keys()),
                    help="Choose an OKH design to match with facilities"
                )
                
                # Get selected design
                selected_design_id = design_options[selected_design_label]
                selected_design = get_design_by_id(selected_design_id, designs)
                
                if selected_design:
                    # Display design details
                    st.markdown("### Design Details")
                    col1, col2, col3 = st.columns(3)
                    
                    with col1:
                        st.metric("Complexity", selected_design['complexity'])
                    with col2:
                        st.metric("Components", selected_design['component_count'])
                    with col3:
                        st.metric("Version", selected_design['version'] or "N/A")
                    
                    if selected_design['description']:
                        st.markdown(f"**Description:** {selected_design['description']}")
                    if selected_design['function']:
                        st.markdown(f"**Function:** {selected_design['function']}")
                
                # Quantity input
                st.markdown("### Production Quantity")
                quantity = st.number_input(
                    "Quantity:",
                    min_value=1,
                    value=1,
                    step=1,
                    help="Number of units to produce"
                )
                
                st.markdown("---")
                
                # Matching Parameters Section
                st.markdown("## Matching Parameters")
                
                col1, col2 = st.columns(2)
                
                with col1:
                    # Location filters
                    location_by_city = st.text_input(
                        "Filter by City (optional):",
                        value="",
                        help="Filter facilities by city name (e.g., 'New York', 'San Francisco')"
                    )
                    location_by_city = location_by_city.strip() if location_by_city else None
                    
                    # Distance filter (simplified - just lat/lon for now)
                    use_distance_filter = st.checkbox("Filter by distance", help="Filter facilities by distance from a location")
                    location_by_distance = None
                    if use_distance_filter:
                        dist_col1, dist_col2 = st.columns(2)
                        with dist_col1:
                            lat = st.number_input("Latitude:", value=37.7749, format="%.6f")
                        with dist_col2:
                            lon = st.number_input("Longitude:", value=-122.4194, format="%.6f")
                        radius_km = st.number_input("Radius (km):", min_value=1, value=100, step=10)
                        location_by_distance = {
                            "latitude": lat,
                            "longitude": lon,
                            "radius_km": radius_km
                        }
                
                with col2:
                    # Confidence threshold
                    min_confidence = st.slider(
                        "Minimum Confidence:",
                        min_value=0.0,
                        max_value=1.0,
                        value=0.3,
                        step=0.05,
                        help="Minimum confidence score for matches (0.0 = any match, 1.0 = perfect match)"
                    )
                    
                    # Max depth
                    max_depth = st.number_input(
                        "Max Depth (optional):",
                        min_value=1,
                        value=None,
                        step=1,
                        help="Maximum nesting depth for component matching. Leave empty for auto-detect."
                    )
                    max_depth = int(max_depth) if max_depth else None
                
                st.markdown("---")
                
                # Matching execution button
                st.markdown("## Execute Matching")
                
                if st.button("Match Facilities", type="primary", use_container_width=True):
                    # Store selected design and parameters in session state
                    if selected_design:
                        with st.spinner("Matching facilities... This may take 30-60 seconds for complex designs."):
                            try:
                                # Get full OKH manifest from the selected design
                                okh_manifest = selected_design['full_design']
                                
                                # Execute matching
                                result = match_facilities(
                                    okh_manifest=okh_manifest,
                                    quantity=quantity,
                                    location_by_city=location_by_city,
                                    location_by_distance=location_by_distance,
                                    min_confidence=min_confidence,
                                    max_depth=max_depth,
                                )
                                
                                # Store result in session state for results display
                                st.session_state['matching_result'] = result
                                st.session_state['matching_params'] = {
                                    'design_name': selected_design['name'],
                                    'quantity': quantity,
                                    'location_by_city': location_by_city,
                                    'location_by_distance': location_by_distance,
                                    'min_confidence': min_confidence,
                                    'max_depth': max_depth,
                                }
                                
                                st.success("✅ Matching completed successfully!")
                                st.rerun()  # Refresh to show results
                                
                            except Exception as e:
                                error_msg = str(e)
                                st.error(f"❌ Matching failed: {error_msg}")
                                
                                # Show more details if available
                                if "422" in error_msg or "validation" in error_msg.lower():
                                    st.warning("**Validation Error**: The request format may be incorrect. Check that:")
                                    st.markdown("- OKH manifest is properly formatted")
                                    st.markdown("- All required fields are present")
                                    st.markdown("- Field names match API expectations")
                                elif "timeout" in error_msg.lower() or "ReadTimeout" in error_msg:
                                    st.warning("**Timeout Error**: The matching operation took too long.")
                                    st.markdown("- Try reducing the complexity (select a simpler design)")
                                    st.markdown("- Try reducing `max_depth` if set")
                                    st.markdown("- Try increasing `min_confidence` to reduce matches")
                                    st.markdown("- The operation may still be processing on the server")
                                
                                # Show exception details in expander
                                with st.expander("🔍 Error Details"):
                                    st.exception(e)
                                
                                st.info("💡 **Tip**: Check terminal logs for detailed error messages")
                    else:
                        st.warning("Please select an OKH design first.")
                
        except Exception as e:
            st.error(f"Failed to load OKH designs: {e}")
            st.exception(e)
            st.info("💡 **Tip**: Check terminal logs for detailed error messages")
    
    st.markdown("---")
    
    # Results Section
    st.markdown("## Matching Results")
    
    if 'matching_result' in st.session_state:
        result = st.session_state['matching_result']
        params = st.session_state.get('matching_params', {})
        
        st.success(f"✅ Matching completed for: **{params.get('design_name', 'Unknown Design')}**")
        
        # Display basic result info
        if result.get('status') == 'success':
            # Parse the actual API response structure
            data = result.get('data', {})
            solutions = data.get('solutions', [])
            total_solutions = data.get('total_solutions', len(solutions))
            
            st.markdown(f"**Total Solutions:** {total_solutions}")
            
            # Extract trees from solutions
            all_trees = [sol.get('tree', {}) for sol in solutions if sol.get('tree')]
            st.markdown(f"**Total Trees:** {len(all_trees)}")
            
            # Show matched facilities count
            facility_count = len(set(
                sol.get('facility_name') or sol.get('tree', {}).get('facility_name')
                for sol in solutions
                if sol.get('facility_name') or sol.get('tree', {}).get('facility_name')
            ))
            st.markdown(f"**Matched Facilities:** {facility_count}")
            
            # Show matching metrics if available
            matching_metrics = data.get('matching_metrics', {})
            if matching_metrics:
                st.markdown("**Matching Breakdown:**")
                col1, col2, col3, col4 = st.columns(4)
                with col1:
                    st.metric("Direct", matching_metrics.get('direct_matches', 0))
                with col2:
                    st.metric("Heuristic", matching_metrics.get('heuristic_matches', 0))
                with col3:
                    st.metric("NLP", matching_metrics.get('nlp_matches', 0))
                with col4:
                    st.metric("LLM", matching_metrics.get('llm_matches', 0))
            
            # Show processing time
            processing_time = data.get('processing_time', 0)
            if processing_time:
                st.markdown(f"**Processing Time:** {processing_time:.2f} seconds")
            
            # Debug: Show full result structure
            with st.expander("🔍 Debug: Full Matching Result", expanded=False):
                st.json(result)
            
            if facility_count == 0:
                st.warning("⚠️ **No facilities matched!** This could indicate:")
                st.markdown("- Process name mismatch (OKH uses '3DP', OKW uses Wikipedia URLs)")
                st.markdown("- Confidence threshold too high (current: {})".format(params.get('min_confidence', 0.3)))
                st.markdown("- No compatible facilities in database")
                st.markdown("- Matching logic issue")
                
                # Show what was requested
                st.markdown("**Request Parameters:**")
                st.json(params)
            else:
                # Show top matches
                st.markdown("---")
                st.markdown("### Top Matches")
                
                # Sort solutions by confidence/score (highest first)
                sorted_solutions = sorted(
                    solutions,
                    key=lambda s: s.get('score', s.get('confidence', 0)),
                    reverse=True
                )
                
                # Show top 5 matches
                for idx, sol in enumerate(sorted_solutions[:5], 1):
                    tree = sol.get('tree', {})
                    facility_name = sol.get('facility_name') or tree.get('facility_name', 'Unknown')
                    confidence = sol.get('confidence', sol.get('score', tree.get('confidence_score', 0)))
                    match_type = sol.get('match_type', tree.get('match_type', 'unknown'))
                    
                    with st.expander(f"#{idx} {facility_name} (Confidence: {confidence:.2f})", expanded=(idx == 1)):
                        col1, col2 = st.columns(2)
                        with col1:
                            st.markdown(f"**Match Type:** {match_type}")
                            st.markdown(f"**Confidence Score:** {confidence:.2f}")
                            if sol.get('rank'):
                                st.markdown(f"**Rank:** {sol.get('rank')}")
                        with col2:
                            facility = sol.get('facility', {})
                            location = facility.get('location', {})
                            city = location.get('city', 'N/A')
                            country = location.get('country', 'N/A')
                            st.markdown(f"**Location:** {city}, {country}")
                            if location.get('gps_coordinates'):
                                st.markdown(f"**GPS:** {location.get('gps_coordinates')}")
                        
                        # Show capabilities used
                        capabilities = tree.get('capabilities_used', [])
                        if capabilities:
                            st.markdown("**Capabilities Used:**")
                            for cap in capabilities[:5]:  # Show first 5
                                # Extract process name from Wikipedia URL if present
                                if 'wikipedia.org/wiki/' in str(cap):
                                    process_name = str(cap).split('/wiki/')[-1].replace('_', ' ').title()
                                    st.markdown(f"- {process_name}")
                                else:
                                    st.markdown(f"- {cap}")
                        
                        # Show materials required
                        materials = tree.get('materials_required', [])
                        if materials:
                            st.markdown("**Materials Required:**")
                            for mat in materials[:3]:  # Show first 3
                                if isinstance(mat, str):
                                    # Parse MaterialSpec string representation
                                    # Format: "MaterialSpec(material_id='PLA', name='...', quantity=..., unit='...', notes='...')"
                                    if 'MaterialSpec' in mat:
                                        # Extract material name and quantity
                                        import re
                                        name_match = re.search(r"name='([^']+)'", mat)
                                        qty_match = re.search(r"quantity=([^,)]+)", mat)
                                        unit_match = re.search(r"unit='([^']+)'", mat)
                                        
                                        name = name_match.group(1) if name_match else "Unknown"
                                        qty = qty_match.group(1) if qty_match else "N/A"
                                        unit = unit_match.group(1) if unit_match else ""
                                        
                                        if qty != "None" and qty != "N/A":
                                            st.markdown(f"- {name}: {qty} {unit}")
                                        else:
                                            st.markdown(f"- {name}")
                                    else:
                                        st.markdown(f"- {mat}")
                                elif isinstance(mat, dict):
                                    # Material is already a dict
                                    name = mat.get('name', mat.get('material_id', 'Unknown'))
                                    qty = mat.get('quantity')
                                    unit = mat.get('unit', '')
                                    if qty:
                                        st.markdown(f"- {name}: {qty} {unit}")
                                    else:
                                        st.markdown(f"- {name}")
                                else:
                                    st.markdown(f"- {str(mat)}")
            
            st.info("🚧 Full results display coming in Task 3.5")
        else:
            st.warning(f"Matching completed with status: {result.get('status', 'unknown')}")
            if result.get('message'):
                st.info(result['message'])
            
            # Show error details if available
            if result.get('errors'):
                with st.expander("🔍 Error Details"):
                    st.json(result.get('errors'))
    else:
        st.info("👆 Select a design and click 'Match Facilities' to see results here")


if __name__ == "__main__":
    main()
