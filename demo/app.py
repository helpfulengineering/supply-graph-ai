"""
OHM Demo - Multi-Facility Matching Interface

Streamlit application for demonstrating Open Hardware Manager (OHM)
multi-facility matching capabilities with synthetic demo data.
"""

import streamlit as st
import os
import sys
import pandas as pd
import pydeck as pdk
from typing import Dict, Any

# Add project root to path for imports
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

from demo.facilities import get_facilities_with_full_data
from demo.okh_designs import get_okh_designs_for_selection, get_design_by_id
from demo.matching import match_facilities
from demo.results_parser import (
    detect_matching_mode,
    parse_nested_solution,
    parse_single_level_solutions,
    select_best_solution,
    get_solution_summary,
    get_facility_dependency_indicator,
    has_nested_components,
    get_component_name_map,
    format_component_mapping,
    detect_duplicate_component_mappings,
    group_facilities_by_stage,
    get_component_name_for_tree
)
from demo.rfq_generator import generate_rfq
from demo.solution_selectors import DEFAULT_SELECTOR
from demo.facility_deduplication import (
    get_alternative_facilities_for_component
)

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


def _display_facility_details(facility: Dict[str, Any]) -> None:
    """
    Display detailed information about a facility in a formatted way.
    
    Args:
        facility: Full facility dictionary from API
    """
    # Basic Information
    st.markdown(f"### {facility.get('name', 'Unknown Facility')}")
    
    # Location Information
    location = facility.get('location', {})
    if location:
        col1, col2 = st.columns(2)
        with col1:
            if location.get('city'):
                st.markdown(f"**City:** {location.get('city')}")
            if location.get('state'):
                st.markdown(f"**State/Region:** {location.get('state')}")
        with col2:
            if location.get('country'):
                st.markdown(f"**Country:** {location.get('country')}")
            if location.get('gps_coordinates'):
                st.markdown(f"**Coordinates:** {location.get('gps_coordinates')}")
    
    # Contact Information
    contact = facility.get('contact', {})
    if contact:
        st.markdown("---")
        st.markdown("**Contact Information:**")
        if contact.get('email'):
            st.markdown(f"- **Email:** {contact.get('email')}")
        if contact.get('phone'):
            st.markdown(f"- **Phone:** {contact.get('phone')}")
        if contact.get('name'):
            st.markdown(f"- **Contact Name:** {contact.get('name')}")
    
    # Facility Status
    if facility.get('facility_status'):
        st.markdown("---")
        status = facility.get('facility_status')
        status_emoji = "✅" if status.lower() == "active" else "⚠️"
        st.markdown(f"**Status:** {status_emoji} {status}")
    
    # Manufacturing Processes
    manufacturing_processes = facility.get('manufacturing_processes', [])
    if manufacturing_processes:
        st.markdown("---")
        st.markdown("**Manufacturing Processes:**")
        for process in manufacturing_processes[:5]:  # Show first 5
            if isinstance(process, str):
                # Extract process name from Wikipedia URL if present
                if 'wikipedia.org/wiki/' in process:
                    process_name = process.split('/wiki/')[-1].replace('_', ' ').title()
                    st.markdown(f"- {process_name}")
                else:
                    st.markdown(f"- {process}")
        if len(manufacturing_processes) > 5:
            st.caption(f"... and {len(manufacturing_processes) - 5} more processes")
    
    # Equipment
    equipment = facility.get('equipment', [])
    if equipment:
        st.markdown("---")
        st.markdown("**Equipment:**")
        for item in equipment[:5]:  # Show first 5
            if isinstance(item, dict):
                # Extract equipment name from equipment_type (Wikipedia URL)
                equipment_type = item.get('equipment_type', '')
                if equipment_type:
                    if 'wikipedia.org/wiki/' in equipment_type:
                        eq_name = equipment_type.split('/wiki/')[-1].replace('_', ' ').title()
                    else:
                        eq_name = equipment_type
                else:
                    eq_name = 'Unknown Equipment'
                
                # Build equipment description with make/model if available
                make = item.get('make', '')
                model = item.get('model', '')
                if make and model:
                    eq_display = f"{eq_name} ({make} {model})"
                elif make:
                    eq_display = f"{eq_name} ({make})"
                elif model:
                    eq_display = f"{eq_name} ({model})"
                else:
                    eq_display = eq_name
                
                # Add condition if available
                condition = item.get('condition', '')
                if condition:
                    eq_display += f" - {condition}"
                
                st.markdown(f"- {eq_display}")
            elif isinstance(item, str):
                st.markdown(f"- {item}")
        if len(equipment) > 5:
            st.caption(f"... and {len(equipment) - 5} more equipment items")


def main():
    """Main application entry point."""
    
    # Title
    st.title("🔧 OHM Demo - Multi-Facility Matching")
    st.markdown("---")
    
    # Map Section
    st.markdown("## Map Visualization")
    st.markdown("OKW facilities displayed on an interactive map. Click on a pin to view facility details.")
    
    # Load and display facilities on map
    with st.spinner("Loading facilities from API... This may take a moment."):
        try:
            # Load facilities with full data for modal display
            facilities_df, full_facilities = get_facilities_with_full_data()
            
            # Store full facilities in session state for modal access
            if 'facilities_data' not in st.session_state:
                st.session_state['facilities_data'] = full_facilities
            
            # Create a mapping from facility name to full data for quick lookup
            facility_lookup = {}
            facility_by_name = {}  # Simple name-based lookup for location access
            for facility in full_facilities:
                name = facility.get('name', 'Unknown')
                location = facility.get('location', {})
                city = location.get('city', '')
                country = location.get('country', '')
                # Use name + location as key for uniqueness
                key = f"{name}|{city}|{country}"
                facility_lookup[key] = facility
                # Also create simple name-based lookup (use first occurrence if duplicates)
                if name not in facility_by_name:
                    facility_by_name[name] = facility
            
            # Store lookup in session state
            st.session_state['facility_lookup'] = facility_lookup
            st.session_state['facility_by_name'] = facility_by_name
            
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
                # Create interactive map with Pydeck
                # Create a layer for facility markers with custom icons and outlines
                layer = pdk.Layer(
                    "ScatterplotLayer",
                    data=facilities_df,
                    get_position=["lon", "lat"],
                    get_color=[200, 30, 0, 200],  # Red fill color with transparency
                    get_radius=800,  # Radius in meters
                    pickable=True,  # Enable click events
                    auto_highlight=True,
                    radius_min_pixels=6,
                    radius_max_pixels=18,
                    stroked=True,  # Enable outline
                    get_line_color=[255, 255, 255, 255],  # White outline for contrast
                    line_width_min_pixels=2,  # Thick outline for visibility
                )
                
                # Set initial viewport (center on facilities)
                if not facilities_df.empty:
                    view_state = pdk.ViewState(
                        latitude=facilities_df['lat'].mean(),
                        longitude=facilities_df['lon'].mean(),
                        zoom=3,
                        pitch=0,
                    )
                else:
                    view_state = pdk.ViewState(
                        latitude=37.7749,
                        longitude=-122.4194,
                        zoom=3,
                        pitch=0,
                    )
                
                # Create the deck with tooltip and visible base map
                # Use CartoDB's free base map which works without API keys and has good contrast
                # CartoDB Positron is a light style with visible streets and labels
                deck = pdk.Deck(
                    map_style="https://basemaps.cartocdn.com/gl/positron-gl-style/style.json",  # CartoDB Positron - light, visible, no API key needed
                    initial_view_state=view_state,
                    layers=[layer],
                    tooltip={
                        "html": "<b>{name}</b><br/>{city}, {country}<br/><i>Select facility below to view details</i>",
                        "style": {
                            "color": "white",
                            "backgroundColor": "rgba(0, 0, 0, 0.8)",
                            "padding": "8px",
                            "borderRadius": "4px",
                        }
                    },
                )
                
                # Display the map
                selected_map_object = st.pydeck_chart(deck, width='stretch')
                
                # Facility selector for viewing details
                st.markdown("---")
                st.markdown("### 📍 View Facility Details")
                st.caption("Select a facility from the dropdown to view detailed information")
                
                # Create facility options for dropdown
                facility_options = ["Select a facility..."] + [
                    f"{row['name']} ({row.get('city', 'N/A')}, {row.get('country', 'N/A')})"
                    for _, row in facilities_df.iterrows()
                ]
                
                selected_facility_label = st.selectbox(
                    "Choose a facility:",
                    options=facility_options,
                    key="facility_selector",
                    help="Select a facility to view its details"
                )
                
                # Display facility details if one is selected
                if selected_facility_label and selected_facility_label != "Select a facility...":
                    # Extract facility name from label
                    facility_name = selected_facility_label.split(" (")[0]
                    
                    # Find matching facility in DataFrame
                    matching_facility = facilities_df[facilities_df['name'] == facility_name]
                    
                    if not matching_facility.empty:
                        facility_row = matching_facility.iloc[0]
                        facility_city = facility_row.get('city', '')
                        facility_country = facility_row.get('country', '')
                        
                        # Look up full facility data
                        lookup_key = f"{facility_name}|{facility_city}|{facility_country}"
                        full_facility = facility_lookup.get(lookup_key)
                        
                        if full_facility:
                            st.markdown("---")
                            with st.expander(f"📍 **{facility_name}** - Facility Details", expanded=True):
                                _display_facility_details(full_facility)
                        else:
                            st.warning(f"Full facility data not found for {facility_name}")
                    else:
                        st.warning(f"Facility {facility_name} not found in data")
                
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
                
                # Store in session state for RFQ generation
                st.session_state['selected_design_id'] = selected_design_id
                if selected_design:
                    st.session_state['selected_design'] = selected_design
                
                # Store selected design ID and design in session state
                st.session_state['selected_design_id'] = selected_design_id
                if selected_design:
                    st.session_state['selected_design'] = selected_design
                
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
                # Get quantity from session state or use default
                default_quantity = st.session_state.get('quantity', 1)
                quantity = st.number_input(
                    "Quantity:",
                    min_value=1,
                    value=default_quantity,
                    step=1,
                    help="Number of units to produce"
                )
                # Store quantity in session state
                st.session_state['quantity'] = quantity
                
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
                        min_value=0,
                        value=0,
                        step=1,
                        help="Maximum nesting depth (0 = single-level, >0 = nested). Leave at 0 for auto-detect nested designs."
                    )
                    max_depth = int(max_depth) if max_depth is not None else 0
                    # Convert 0 to None for API (0 means "use default/auto-detect")
                    max_depth = None if max_depth == 0 else max_depth
                
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
                                
                                # Auto-detect if nested matching is needed
                                # If max_depth is explicitly set (> 0), use it; otherwise auto-detect for nested designs
                                auto_detect_depth = None
                                if max_depth is None or max_depth == 0:
                                    # Check if design has nested components
                                    if has_nested_components(okh_manifest):
                                        auto_detect_depth = True
                                        st.info("🔗 **Nested design detected**: Auto-enabling multi-facility matching")
                                
                                # Execute matching
                                result = match_facilities(
                                    okh_manifest=okh_manifest,
                                    quantity=quantity,
                                    location_by_city=location_by_city,
                                    location_by_distance=location_by_distance,
                                    min_confidence=min_confidence,
                                    max_depth=max_depth,
                                    auto_detect_depth=auto_detect_depth,
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
            
            # Detect matching mode using tested parser function
            matching_mode = detect_matching_mode(data)
            
            # Get selected design info for component count
            # First try to get from session state (preferred - faster)
            selected_design = st.session_state.get('selected_design')
            
            # If not in session state, try to get by ID
            if not selected_design and 'selected_design_id' in st.session_state:
                # Get designs list
                designs = get_okh_designs_for_selection()
                selected_design = get_design_by_id(st.session_state['selected_design_id'], designs)
                # Store it for next time
                if selected_design:
                    st.session_state['selected_design'] = selected_design
            
            # Solution Selection UI (for single-level matching with multiple solutions)
            selector_name = DEFAULT_SELECTOR
            if matching_mode == 'single-level':
                # Check if there are multiple solutions
                solutions = data.get('solutions', [])
                if len(solutions) > 1:
                    st.markdown("### Solution Selection")
                    selector_options = {
                        'Fewest Facilities': 'fewest_facilities',
                        'Highest Score': 'highest_score',
                        'Best Match Scores': 'best_match_scores'
                    }
                    
                    selected_option = st.selectbox(
                        "Select solution strategy:",
                        options=list(selector_options.keys()),
                        index=0,  # Default to "Fewest Facilities"
                        help="Choose how to select the best solution from multiple matches"
                    )
                    selector_name = selector_options[selected_option]
                    
                    # Apply selection
                    data = select_best_solution(data, selector_name)
                    st.info(f"📊 **Selected**: {selected_option} (showing 1 of {len(solutions)} solutions)")
            
            # Parse response based on matching mode using tested parser functions
            if matching_mode == 'nested':
                # Parse nested solution with deduplication enabled
                parsed = parse_nested_solution(
                    data,
                    use_deduplication=True,
                    aggregate_score_method='highest'
                )
                # Store parsed data for RFQ generation
                st.session_state['parsed_matching_data'] = parsed
                solution_score = parsed['solution_score']
                facility_count = parsed['facility_count']
                tree_count = parsed['tree_count']
                facilities_in_solution = parsed['facilities_in_solution']
                component_mapping = parsed['component_mapping']
                deduplicated_facilities = parsed.get('deduplicated_facilities')  # Extract early
                solution = data.get('solution', {})  # Keep for dependency info
                
                # Display summary metrics for nested solution
                st.info(f"🔗 **Multi-Facility Solution Detected**: This design requires **{facility_count} facilities** working together. No single facility can produce the entire design.")
                
                col1, col2, col3, col4 = st.columns(4)
                with col1:
                    st.metric("Solution Score", f"{solution_score:.2f}")
                    st.caption("Aggregate confidence across all facilities")
                with col2:
                    st.metric("Facilities Required", facility_count)
                    st.caption("Unique facilities needed for this design")
                with col3:
                    st.metric("Total Trees", tree_count)
                    st.caption("Supply trees (component-facility matches)")
                with col4:
                    if selected_design:
                        component_count = selected_design.get('component_count', 'N/A')
                        st.metric("Components", component_count)
                        st.caption("Total components in OKH design")
                    else:
                        st.metric("Components", "N/A")
                
                # Show component mapping if available (with proper labeling and deduplication)
                if component_mapping:
                    # Get component name mapping from the selected design
                    comp_name_map = {}
                    if selected_design and 'full_design' in selected_design:
                        comp_name_map = get_component_name_map(selected_design['full_design'])
                    
                    # Get selected facility names and tree IDs from deduplicated facilities
                    selected_facility_names = None
                    selected_tree_ids = None
                    
                    if deduplicated_facilities:
                        selected_facility_names = {f['name'] for f in deduplicated_facilities}
                        # Get tree IDs from all components in selected facilities
                        selected_tree_ids = set()
                        for facility in deduplicated_facilities:
                            for comp_info in facility['components']:
                                tree = comp_info.get('tree', {})
                                tree_id = tree.get('id')
                                if tree_id:
                                    selected_tree_ids.add(str(tree_id))
                    elif facilities_in_solution:
                        selected_facility_names = {f['name'] for f in facilities_in_solution}
                        # Get tree IDs from facilities_in_solution
                        selected_tree_ids = set()
                        for facility_info in facilities_in_solution:
                            trees = facility_info.get('trees', [])
                            for tree_info in trees:
                                if isinstance(tree_info, dict):
                                    tree = tree_info.get('tree', tree_info)
                                    tree_id = tree.get('id')
                                    if tree_id:
                                        selected_tree_ids.add(str(tree_id))
                    
                    # Format component mapping with names, deduplication, filtering to selected solution,
                    # and limiting to top N facilities per component (Option 1: MVP/Demo)
                    formatted_mapping = format_component_mapping(
                        component_mapping,
                        comp_name_map,
                        selected_facility_names=selected_facility_names,
                        selected_tree_ids=selected_tree_ids,
                        max_facilities_per_component=3  # Show top 3 facilities per component
                    )
                    
                    if formatted_mapping:
                        st.markdown("**Component-to-Facility Mapping:**")
                        st.markdown("Shows which facilities in the selected solution can produce each component.")
                        st.caption(
                            "💡 **Note**: Facility names like 'Assembly Facility 1' and 'Assembly Facility 2' "
                            "represent different facilities, not the same facility at different stages. "
                            "Showing top 3 facilities per component by confidence score."
                        )
                        
                        # Detect duplicate mappings
                        duplicate_info = detect_duplicate_component_mappings(formatted_mapping)
                        
                        if duplicate_info['has_duplicates']:
                            st.warning(
                                f"⚠️ **Note**: {duplicate_info['total_components']} components map to "
                                f"only {duplicate_info['unique_facility_sets']} unique facility set(s). "
                                f"Multiple components can be produced by the same facilities."
                            )
                        
                        for comp_info in formatted_mapping:
                            comp_id = comp_info['component_id']
                            comp_name = comp_info['component_name']
                            facilities = comp_info['facilities']
                            
                            if facilities:
                                # Always show component name prominently (not ID)
                                # If name wasn't found, try to extract from component_id or use a fallback
                                if comp_name == comp_id:
                                    # Try to get a better name from the component mapping
                                    # This handles cases where name_map wasn't populated
                                    st.markdown(f"**Component** (ID: `{comp_id}`)")
                                    st.caption("⚠️ Component name not found. Showing ID instead.")
                                else:
                                    # Component name found - show it prominently
                                    st.markdown(f"**{comp_name}**")
                                    st.caption(f"Component ID: `{comp_id}`")
                                
                                # Show unique facilities (already deduplicated, filtered, and limited to top N)
                                total_available = comp_info.get('total_facilities_available', len(facilities))
                                facilities_shown = comp_info.get('facilities_shown', len(facilities))
                                
                                if len(facilities) == 1:
                                    st.markdown(f"  - **Facility:** {facilities[0]}")
                                else:
                                    st.markdown(f"  - **Facilities** ({facilities_shown}): {', '.join(facilities)}")
                                
                                # Show info if more facilities were available but not shown
                                if total_available > facilities_shown:
                                    st.caption(
                                        f"ℹ️ Showing top {facilities_shown} of {total_available} available facilities "
                                        f"(sorted by confidence score). All matches are saved in the solution."
                                    )
                                
                                st.markdown("")  # Add spacing
                            else:
                                # Component has no facilities in selected solution
                                if comp_name != comp_id:
                                    st.markdown(f"**{comp_name}**")
                                else:
                                    st.markdown(f"**Component** (ID: `{comp_id}`)")
                                st.caption("⚠️ No facilities in selected solution for this component.")
                                st.markdown("")
                
            else:
                # Parse single-level solutions with selection enabled
                parsed = parse_single_level_solutions(
                    data,
                    use_selection=True,
                    selector_name=selector_name
                )
                # Store parsed data for RFQ generation
                st.session_state['parsed_matching_data'] = parsed
                total_solutions = parsed['total_solutions']
                facility_count = parsed['facility_count']
                all_trees = parsed['all_trees']
                solutions = parsed['solutions']
                selection_criteria = parsed.get('selection_criteria')
                
                # Display summary metrics
                col1, col2, col3, col4 = st.columns(4)
                with col1:
                    st.metric("Total Solutions", total_solutions)
                    if selection_criteria and total_solutions > 1:
                        st.caption(f"Selected: {selection_criteria}")
                with col2:
                    st.metric("Total Trees", len(all_trees))
                with col3:
                    st.metric("Matched Facilities", facility_count)
                with col4:
                    # Show component count from selected design
                    if selected_design:
                        component_count = selected_design.get('component_count', 'N/A')
                        st.metric("Components", component_count)
                    else:
                        st.metric("Components", "N/A")
            
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
            
            # Get facility_count for the check (from parsed data or variables)
            if matching_mode == 'nested':
                display_facility_count = parsed.get('facility_count', 0)
            else:
                display_facility_count = facility_count
            
            if display_facility_count == 0:
                st.warning("⚠️ **No facilities matched!** This could indicate:")
                st.markdown("- Process name mismatch (OKH uses '3DP', OKW uses Wikipedia URLs)")
                st.markdown("- Confidence threshold too high (current: {})".format(params.get('min_confidence', 0.3)))
                st.markdown("- No compatible facilities in database")
                st.markdown("- Matching logic issue")
                
                # Show what was requested
                st.markdown("**Request Parameters:**")
                st.json(params)
            else:
                # Show matches based on matching mode
                st.markdown("---")
                
                if matching_mode == 'nested':
                    # Display nested solution with facility grouping
                    # Use tested function for solution summary
                    solution_summary = get_solution_summary(matching_mode, parsed)
                    st.markdown(f"### {solution_summary}")
                    
                    # Show solution-level information with clear labels
                    st.markdown(f"**Solution Score:** {solution_score:.2f} (aggregate confidence across all facilities)")
                    
                    # Get component name mapping for better display
                    comp_name_map = {}
                    if selected_design and 'full_design' in selected_design:
                        comp_name_map = get_component_name_map(selected_design['full_design'])
                    
                    # deduplicated_facilities already extracted above
                    if deduplicated_facilities:
                        # Display using deduplicated facilities (Phase 1 implementation)
                        st.markdown("#### Facilities in This Solution:")
                        st.info("🏭 Each facility is shown once with all components it produces listed below.")
                        
                        for idx, facility in enumerate(deduplicated_facilities, 1):
                            facility_name = facility['name']
                            components = facility['components']
                            aggregate_score = facility['aggregate_score']
                            stage = facility['stage']
                            depends_on = facility['depends_on']
                            
                            # Show facility with all components
                            dep_indicator = "🔗" if depends_on else "⚡"
                            title = f"{dep_indicator} #{idx} {facility_name} (Score: {aggregate_score:.2f})"
                            
                            if len(components) > 1:
                                title += f" - Produces {len(components)} components"
                            
                            with st.expander(title, expanded=(idx == 1)):
                                # Facility-level info
                                col1, col2 = st.columns(2)
                                with col1:
                                    st.markdown(f"**Facility Name:** {facility_name}")
                                    st.markdown(f"**Aggregate Score:** {aggregate_score:.2f}")
                                    st.markdown(f"**Production Stage:** {stage}")
                                    if depends_on:
                                        st.markdown(f"**Depends On:** {', '.join(str(d) for d in depends_on)}")
                                    else:
                                        st.markdown("**Dependencies:** None (can start immediately)")
                                
                                with col2:
                                    # Get location from first component's tree, then fallback to facility lookup
                                    location_info = {}
                                    if components:
                                        primary_tree = components[0].get('tree', {})
                                        location_info = primary_tree.get('metadata', {}).get('facility_location', {})
                                    
                                    # If not in tree metadata, look up from full facility data
                                    if not location_info or not location_info.get('city'):
                                        facility_by_name = st.session_state.get('facility_by_name', {})
                                        facility = facility_by_name.get(facility_name)
                                        if facility:
                                            location_info = facility.get('location', {})
                                    
                                    # Extract city and country with multiple fallbacks
                                    city = 'N/A'
                                    country = 'N/A'
                                    if location_info:
                                        city = location_info.get('city') or location_info.get('address', {}).get('city') or 'N/A'
                                        country = location_info.get('country') or location_info.get('address', {}).get('country') or 'N/A'
                                    
                                    st.markdown(f"**Location:** {city}, {country}")

                                    gps = location_info.get('gps_coordinates') if location_info else None
                                    if gps:
                                        st.markdown(f"**GPS Coordinates:** {gps}")
                                
                                # Show all components this facility produces
                                st.markdown("**Components Produced by This Facility:**")
                                for comp_info in components:
                                    comp_name = comp_info.get('component_name') or comp_info.get('component_id', 'Unknown')
                                    comp_id = comp_info.get('component_id')
                                    comp_score = comp_info.get('confidence_score', 0)
                                    
                                    # Use name map if available
                                    if comp_id and comp_id in comp_name_map:
                                        comp_name = comp_name_map[comp_id]
                                    
                                    st.markdown(f"- **{comp_name}** (Component ID: `{comp_id}`, Score: {comp_score:.2f})")
                                    
                                    # Show alternative facilities for this component (on request)
                                    if component_mapping and comp_id:
                                        alternatives = get_alternative_facilities_for_component(
                                            comp_id,
                                            component_mapping,
                                            facility_name,
                                            limit=3
                                        )
                                        
                                        if alternatives:
                                            with st.expander(f"Show alternative facilities for {comp_name}", expanded=False):
                                                st.markdown(f"**Alternative facilities for {comp_name}:**")
                                                for alt_tree in alternatives:
                                                    alt_facility = alt_tree.get('facility_name', 'Unknown')
                                                    alt_score = alt_tree.get('confidence_score', 0)
                                                    st.markdown(f"- {alt_facility} (Score: {alt_score:.2f})")
                    
                    # Show production sequence if available (filtered to selected solution)
                    production_sequence = parsed.get('production_sequence', [])
                    all_trees_parsed = parsed.get('all_trees', [])
                    
                    if production_sequence and all_trees_parsed:
                        # Get selected facility names and tree IDs from deduplicated facilities
                        selected_facility_names = None
                        selected_tree_ids = None
                        
                        if deduplicated_facilities:
                            selected_facility_names = {f['name'] for f in deduplicated_facilities}
                            # Get tree IDs from all components in selected facilities
                            selected_tree_ids = set()
                            for facility in deduplicated_facilities:
                                for comp_info in facility['components']:
                                    tree = comp_info.get('tree', {})
                                    tree_id = tree.get('id')
                                    if tree_id:
                                        selected_tree_ids.add(str(tree_id))
                        elif facilities_in_solution:
                            selected_facility_names = {f['name'] for f in facilities_in_solution}
                            # Get tree IDs from facilities_in_solution
                            selected_tree_ids = set()
                            for facility_info in facilities_in_solution:
                                trees = facility_info.get('trees', [])
                                for tree_info in trees:
                                    if isinstance(tree_info, dict):
                                        tree = tree_info.get('tree', tree_info)
                                        tree_id = tree.get('id')
                                        if tree_id:
                                            selected_tree_ids.add(str(tree_id))
                        
                        # Group facilities by stage, filtering to selected solution only
                        stages = group_facilities_by_stage(
                            production_sequence,
                            all_trees_parsed,
                            selected_facility_names=selected_facility_names,
                            selected_tree_ids=selected_tree_ids
                        )
                        
                        if stages:  # Only show if we have stages after filtering
                            st.markdown("#### Production Plan:")
                            st.info("📋 **Component-Based Production**: Each component can be produced by the facilities listed. Facilities in the same stage can work in parallel.")
                            st.caption(f"Selected solution: {len(selected_facility_names) if selected_facility_names else 'all'} facilities across {len(stages)} production stage(s)")
                            
                            # Reorganize: Group by component instead of by stage
                            # This makes it easier to see "what facilities can produce X component"
                            component_to_facilities = {}
                            
                            for stage in stages:
                                stage_num = stage['stage_number']
                                trees_in_stage = stage['trees']
                                
                                for tree in trees_in_stage:
                                    comp_id = tree.get('component_id', '')
                                    comp_name = get_component_name_for_tree(tree, comp_name_map)
                                    facility_name = tree.get('facility_name', 'Unknown')
                                    confidence = tree.get('confidence_score', 0)
                                    
                                    # Get location info for decision-making
                                    # Try multiple sources: tree metadata, then lookup from full facility data
                                    location_info = tree.get('metadata', {}).get('facility_location', {})
                                    
                                    # If not in tree metadata, look up from full facility data
                                    if not location_info or not location_info.get('city'):
                                        facility_by_name = st.session_state.get('facility_by_name', {})
                                        facility = facility_by_name.get(facility_name)
                                        if facility:
                                            location_info = facility.get('location', {})
                                    
                                    # Extract city and country with multiple fallbacks
                                    city = 'N/A'
                                    country = 'N/A'
                                    if location_info:
                                        # Try direct city field first
                                        city = location_info.get('city', '')
                                        # If not found, try nested address structure
                                        if not city:
                                            city = location_info.get('address', {}).get('city', '')
                                        # If still not found, use N/A
                                        if not city:
                                            city = 'N/A'
                                        
                                        # Same for country
                                        country = location_info.get('country', '')
                                        if not country:
                                            country = location_info.get('address', {}).get('country', '')
                                        if not country:
                                            country = 'N/A'
                                    
                                    if comp_id not in component_to_facilities:
                                        component_to_facilities[comp_id] = {
                                            'name': comp_name,
                                            'stage': stage_num,
                                            'facilities': []
                                        }
                                    
                                    # Add facility info
                                    component_to_facilities[comp_id]['facilities'].append({
                                        'name': facility_name,
                                        'city': city,
                                        'country': country,
                                        'confidence': confidence,
                                        'stage': stage_num
                                    })
                            
                            # Display organized by component
                            for comp_id, comp_info in sorted(component_to_facilities.items(), key=lambda x: (x[1]['stage'], x[1]['name'])):
                                comp_name = comp_info['name']
                                stage_num = comp_info['stage']
                                facilities = comp_info['facilities']
                                
                                # Sort facilities by confidence (best first)
                                facilities.sort(key=lambda x: x['confidence'], reverse=True)
                                
                                # Show component header with stage info
                                with st.expander(f"🔧 **{comp_name}** (Stage {stage_num}) - {len(facilities)} facility/facilities available", expanded=False):
                                    st.caption(f"Component ID: `{comp_id}` | Production Stage: {stage_num}")
                                    
                                    # Show facilities in a table-like format for easy scanning
                                    for idx, facility in enumerate(facilities, 1):
                                        col1, col2, col3 = st.columns([3, 2, 1])
                                        with col1:
                                            st.markdown(f"**{idx}. {facility['name']}**")
                                        with col2:
                                            location_str = f"{facility['city']}, {facility['country']}"
                                            st.markdown(f"📍 {location_str}")
                                        with col3:
                                            st.markdown(f"Score: {facility['confidence']:.2f}")
                                    
                                    if len(facilities) > 1:
                                        st.caption(f"💡 Multiple facilities available - choose based on location, capacity, or lead time")
                                    
                                    # Show stage dependency info
                                    if stage_num > 1:
                                        st.info(f"⏱️ Stage {stage_num} - Requires completion of earlier stages first")
                    
                    # Fallback: display facilities without deduplication (if deduplication not available)
                    if not deduplicated_facilities:
                        st.markdown("#### Facilities in This Solution:")
                        
                        for idx, facility_info in enumerate(facilities_in_solution, 1):
                            facility_name = facility_info['name']
                            trees = facility_info.get('trees', [facility_info.get('tree', {})])
                            confidence = facility_info.get('confidence', 0)
                            
                            if len(trees) > 1:
                                st.markdown(f"**#{idx} {facility_name}** (handles {len(trees)} components, Score: {confidence:.2f})")
                                for tree_info in trees:
                                    if isinstance(tree_info, dict) and 'tree' in tree_info:
                                        tree = tree_info['tree']
                                    else:
                                        tree = tree_info if isinstance(tree_info, dict) else {}
                                    
                                    comp_name = get_component_name_for_tree(tree, comp_name_map)
                                    comp_confidence = tree.get('confidence_score', 0)
                                    st.markdown(f"  - Component: **{comp_name}** (Score: {comp_confidence:.2f})")
                            else:
                                tree = trees[0].get('tree', trees[0]) if isinstance(trees[0], dict) else {}
                                comp_name = get_component_name_for_tree(tree, comp_name_map)
                                
                                dep_indicator = get_facility_dependency_indicator(facility_info)
                                title = f"{dep_indicator} #{idx} {facility_name} → {comp_name} (Score: {confidence:.2f})"
                                
                                with st.expander(title, expanded=(idx == 1)):
                                    col1, col2 = st.columns(2)
                                    with col1:
                                        st.markdown(f"**Component Name:** {comp_name}")
                                        comp_id = tree.get('component_id')
                                        if comp_id:
                                            st.markdown(f"**Component ID:** `{comp_id}`")
                                        st.markdown(f"**Confidence Score:** {confidence:.2f}")
                                        
                                        depends_on = facility_info.get('depends_on', [])
                                        if depends_on:
                                            st.markdown(f"**Depends On:** {', '.join(str(d) for d in depends_on)}")
                                        else:
                                            st.markdown("**Dependencies:** None (can start immediately)")
                                    with col2:
                                        # Get location from tree metadata, then fallback to facility lookup
                                        location_info = tree.get('metadata', {}).get('facility_location', {})
                                        
                                        # If not in tree metadata, look up from full facility data
                                        if not location_info or not location_info.get('city'):
                                            facility_by_name = st.session_state.get('facility_by_name', {})
                                            facility = facility_by_name.get(facility_name)
                                            if facility:
                                                location_info = facility.get('location', {})
                                        
                                        # Extract city and country with multiple fallbacks
                                        city = 'N/A'
                                        country = 'N/A'
                                        if location_info:
                                            city = location_info.get('city') or location_info.get('address', {}).get('city') or 'N/A'
                                            country = location_info.get('country') or location_info.get('address', {}).get('country') or 'N/A'
                                        
                                        st.markdown(f"**Location:** {city}, {country}")
                                        
                                        gps = location_info.get('gps_coordinates')
                                        if gps:
                                            st.markdown(f"**GPS Coordinates:** {gps}")
                                        
                                        facility_id = tree.get('okw_reference') or facility_info.get('tree', {}).get('okw_reference')
                                        if facility_id:
                                            st.markdown(f"**Facility ID:** `{facility_id}`")
                                    
                                    capabilities = tree.get('capabilities_used', [])
                                    if capabilities:
                                        st.markdown("**Capabilities Used:**")
                                        for cap in capabilities[:5]:
                                            if 'wikipedia.org/wiki/' in str(cap):
                                                process_name = str(cap).split('/wiki/')[-1].replace('_', ' ').title()
                                                st.markdown(f"- {process_name}")
                                            else:
                                                st.markdown(f"- {cap}")
                                    
                                    materials = tree.get('materials_required', [])
                                    if materials:
                                        st.markdown("**Materials Required:**")
                                        for mat in materials[:3]:
                                            if isinstance(mat, str):
                                                if 'MaterialSpec' in mat:
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
                                                name = mat.get('name', mat.get('material_id', 'Unknown'))
                                                qty = mat.get('quantity')
                                                unit = mat.get('unit', '')
                                                if qty:
                                                    st.markdown(f"- {name}: {qty} {unit}")
                                                else:
                                                    st.markdown(f"- {name}")
                                            else:
                                                st.markdown(f"- {str(mat)}")
                else:
                    # Single-level: display selected solution
                    # parsed, total_solutions, facility_count, all_trees, solutions, selection_criteria
                    # are already set in the parsing section above
                    
                    # Use tested function for solution summary
                    solution_summary = get_solution_summary(matching_mode, parsed)
                    st.markdown(f"### {solution_summary}")
                    
                    # Show selection info if multiple solutions existed
                    if selection_criteria and total_solutions > 1:
                        selector_display = {
                            'fewest_facilities': 'Fewest Facilities',
                            'highest_score': 'Highest Score',
                            'best_match_scores': 'Best Match Scores'
                        }.get(selection_criteria, selection_criteria)
                        st.caption(f"📊 Solution selected using: **{selector_display}** (from {total_solutions} total solutions)")
                    
                    # Sort solutions by confidence/score (highest first)
                    sorted_solutions = sorted(
                        solutions,
                        key=lambda s: s.get('score', s.get('confidence', s.get('tree', {}).get('confidence_score', 0))),
                        reverse=True
                    )
                    
                    # Show selected matches
                    for idx, sol in enumerate(sorted_solutions, 1):
                        tree = sol.get('tree', {})
                        facility_name = sol.get('facility_name') or tree.get('facility_name', 'Unknown')
                        confidence = sol.get('confidence', sol.get('score', tree.get('confidence_score', 0)))
                        match_type = sol.get('match_type', tree.get('match_type', 'unknown'))
                        
                        # Get solution score (prefer score, then confidence, then tree confidence_score)
                        solution_score = sol.get('score', sol.get('confidence', tree.get('confidence_score', 0)))
                        
                        with st.expander(f"#{idx} {facility_name} (Score: {solution_score:.2f})", expanded=(idx == 1)):
                            col1, col2 = st.columns(2)
                            with col1:
                                st.markdown(f"**Match Type:** {match_type}")
                                st.markdown(f"**Solution Score:** {solution_score:.2f}")
                                st.markdown(f"**Confidence Score:** {confidence:.2f}")
                                if sol.get('rank'):
                                    st.markdown(f"**Rank:** {sol.get('rank')}")
                                
                                # Show facility ID if available
                                facility_id = sol.get('facility_id') or tree.get('facility_id')
                                if facility_id:
                                    st.markdown(f"**Facility ID:** `{facility_id}`")
                            with col2:
                                facility = sol.get('facility', {})
                                location = facility.get('location', {})
                                city = location.get('city', 'N/A')
                                country = location.get('country', 'N/A')
                                st.markdown(f"**Location:** {city}, {country}")
                                
                                gps = location.get('gps_coordinates')
                                if gps:
                                    st.markdown(f"**GPS Coordinates:** {gps}")
                            
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
            
            # RFQ Generation Section
            if display_facility_count > 0:
                st.markdown("---")
                st.markdown("## RFQ Generation")
                st.markdown("Generate Request for Quotation documents for matched facilities")
                
                # Get quantity from session state
                quantity = st.session_state.get('quantity', 1)
                
                # Button to generate RFQs
                if st.button("📄 Generate RFQs", type="primary", use_container_width=True):
                    try:
                        with st.spinner("Generating RFQs... This may take a moment."):
                            # Get design data from session state (preferred) or re-fetch if needed
                            selected_design = st.session_state.get('selected_design')
                            
                            # If not in session state, try to get by ID
                            if not selected_design and 'selected_design_id' in st.session_state:
                                designs = get_okh_designs_for_selection()
                                selected_design = get_design_by_id(st.session_state['selected_design_id'], designs)
                                # Store it for next time
                                if selected_design:
                                    st.session_state['selected_design'] = selected_design
                            
                            if not selected_design:
                                st.error("⚠️ Design information not available. Please select a design and run matching again.")
                            else:
                                # Get full design data (raw OKH manifest)
                                design_data = selected_design.get('full_design', {})
                                
                                # Merge metadata into design_data so RFQ generator has both
                                # raw OKH fields (title) and processed metadata (name)
                                if design_data:
                                    # Ensure name is available (from metadata, not just title)
                                    if 'name' not in design_data and selected_design.get('name'):
                                        design_data['name'] = selected_design.get('name')
                                    # Ensure other metadata fields are available
                                    if 'function' not in design_data and selected_design.get('function'):
                                        design_data['function'] = selected_design.get('function')
                                    if 'description' not in design_data and selected_design.get('description'):
                                        design_data['description'] = selected_design.get('description')
                                    if 'version' not in design_data and selected_design.get('version'):
                                        design_data['version'] = selected_design.get('version')
                                else:
                                    # Fallback to metadata only
                                    design_data = {
                                        'name': selected_design.get('name', 'Unknown Design'),
                                        'id': selected_design.get('id', 'N/A'),
                                        'function': selected_design.get('function', ''),
                                        'description': selected_design.get('description', ''),
                                        'version': selected_design.get('version', '')
                                    }
                                
                                # Get parsed data from session state
                                parsed_data = st.session_state.get('parsed_matching_data')
                                
                                # Generate RFQs
                                rfqs = generate_rfq(
                                    matching_result=result,
                                    design_data=design_data,
                                    quantity=quantity,
                                    parsed_data=parsed_data
                                )
                                
                                # Store in session state
                                st.session_state['rfqs'] = rfqs
                                
                                st.success(f"✅ Generated {len(rfqs)} RFQ(s)")
                    except Exception as e:
                        st.error(f"❌ Error generating RFQs: {str(e)}")
                        with st.expander("🔍 Error Details"):
                            import traceback
                            st.code(traceback.format_exc())
                
                # Display RFQs if available
                if 'rfqs' in st.session_state and st.session_state['rfqs']:
                    rfqs = st.session_state['rfqs']
                    
                    st.markdown(f"### Generated RFQs ({len(rfqs)} facility/facilities)")
                    st.caption("💡 **Note**: These RFQs are for demonstration purposes. They show how RFQs could be generated from matching results.")
                    
                    # Display each RFQ
                    for idx, rfq_data in enumerate(rfqs, 1):
                        facility_name = rfq_data['facility_name']
                        rfq_text = rfq_data['rfq_text']
                        rfq_quantity = rfq_data['quantity']
                        components = rfq_data.get('components', [])
                        
                        # Create expandable section for each RFQ
                        title = f"RFQ #{idx}: {facility_name}"
                        if components:
                            title += f" ({len(components)} component(s))"
                        title += f" - Quantity: {rfq_quantity}"
                        
                        with st.expander(title, expanded=(idx == 1)):
                            # Show RFQ text in a code block for easy copy-paste
                            st.markdown("**RFQ Text:**")
                            st.code(rfq_text, language=None)
                            
                            # Show summary
                            col1, col2 = st.columns(2)
                            with col1:
                                st.metric("Quantity", rfq_quantity)
                            with col2:
                                if components:
                                    st.metric("Components", len(components))
                                    st.caption(", ".join(components[:3]))
                                    if len(components) > 3:
                                        st.caption(f"... and {len(components) - 3} more")
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
