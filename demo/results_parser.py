"""
Results Parser Module

Parses matching API responses and extracts structured data for display.
This module handles both single-level and nested (multi-facility) matching modes.
"""

from typing import Dict, List, Any, Optional, Tuple, Set

from demo.solution_selectors import get_selector, DEFAULT_SELECTOR
from demo.facility_deduplication import (
    deduplicate_facilities,
    get_primary_facility_for_component,
    get_alternative_facilities_for_component
)


def detect_matching_mode(data: Dict[str, Any]) -> str:
    """
    Detect whether the response is nested or single-level matching.
    
    Args:
        data: The 'data' field from the API response
        
    Returns:
        'nested' or 'single-level'
    """
    matching_mode = data.get('matching_mode', 'single-level')
    
    # Also check for presence of 'solution' key (nested) vs 'solutions' key (single-level)
    if 'solution' in data and 'all_trees' in data.get('solution', {}):
        return 'nested'
    elif 'solutions' in data:
        return 'single-level'
    
    return matching_mode


def select_best_solution(
    data: Dict[str, Any],
    selector_name: str = None
) -> Dict[str, Any]:
    """
    Select the best solution from multiple solutions using a selector strategy.
    
    For nested matching, returns the single solution (no selection needed).
    For single-level matching, selects the best solution from the solutions array.
    
    Args:
        data: The 'data' field from the API response
        selector_name: Name of selector strategy (default: 'fewest_facilities')
        
    Returns:
        The selected solution dictionary (wrapped in 'data' structure for consistency)
    """
    matching_mode = detect_matching_mode(data)
    
    if matching_mode == 'nested':
        # Nested matching returns a single solution, no selection needed
        return data
    
    # Single-level matching has multiple solutions
    solutions = data.get('solutions', [])
    
    if not solutions:
        return data
    
    if len(solutions) == 1:
        # Only one solution, no selection needed
        return data
    
    # Select best solution using selector
    selector = get_selector(selector_name)
    best_solution = selector.select_best(solutions)
    
    # Create new data structure with selected solution
    # Keep other fields from original data
    selected_data = data.copy()
    selected_data['solutions'] = [best_solution]
    selected_data['total_solutions'] = 1
    selected_data['selected_solution_index'] = solutions.index(best_solution)
    selected_data['selection_criteria'] = selector_name or DEFAULT_SELECTOR
    
    return selected_data


def parse_nested_solution(
    data: Dict[str, Any],
    use_deduplication: bool = True,
    aggregate_score_method: str = 'highest'
) -> Dict[str, Any]:
    """
    Parse nested solution response structure.
    
    Args:
        data: The 'data' field from the API response
        use_deduplication: Whether to use facility deduplication (default: True)
        aggregate_score_method: How to aggregate scores ('highest' or 'average')
        
    Returns:
        Dictionary with parsed solution information:
        - solution_score: float
        - facility_count: int (unique facilities)
        - tree_count: int
        - all_trees: List[Dict] with all trees (preserves component assignments)
        - facilities_in_solution: List[Dict] with facility info (deduplicated if enabled)
        - deduplicated_facilities: List[Dict] (if deduplication enabled)
        - component_mapping: Dict (if available)
        - dependency_graph: Dict (if available)
        - production_sequence: List (if available)
    """
    solution = data.get('solution', {})
    all_trees = solution.get('all_trees', [])
    solution_score = solution.get('score', 0.0)
    tree_count = solution.get('tree_count', len(all_trees))
    
    # Use facility deduplication if enabled
    if use_deduplication:
        # Filter out trees with 0.0 confidence - these are failed matches that shouldn't be displayed
        # Only show components that actually matched (confidence > 0)
        deduplicated_facilities = deduplicate_facilities(
            all_trees,
            aggregate_score_method=aggregate_score_method,
            min_confidence=0.01  # Exclude 0.0 confidence matches (failed matches)
        )
        
        # Convert deduplicated format to backward-compatible format
        facilities_in_solution = []
        for facility in deduplicated_facilities:
            facilities_in_solution.append({
                'name': facility['name'],
                'tree': facility['primary_tree'],  # Keep for backward compatibility
                'trees': facility['components'],  # All component trees
                'component_id': facility['components'][0].get('component_id') if facility['components'] else None,
                'component_name': facility['components'][0].get('component_name') if facility['components'] else None,
                'confidence': facility['aggregate_score'],
                'depends_on': facility['depends_on'],
                'component_count': facility['component_count'],
                'stage': facility['stage']
            })
    else:
        # Original grouping logic (for backward compatibility)
        facilities_dict = {}  # facility_name -> list of trees for that facility
        
        for tree in all_trees:
            facility_name = tree.get('facility_name', 'Unknown')
            tree_id = tree.get('id')
            
            if facility_name not in facilities_dict:
                facilities_dict[facility_name] = []
            
            facilities_dict[facility_name].append({
                'tree': tree,
                'tree_id': tree_id,
                'component_id': tree.get('component_id'),
                'component_name': tree.get('component_name'),
                'confidence': tree.get('confidence_score', 0),
                'depends_on': tree.get('depends_on', []),
                'production_stage': tree.get('production_stage', 'final')
            })
        
        # Convert to list format
        facilities_in_solution = []
        for facility_name, trees in facilities_dict.items():
            primary_tree = trees[0]['tree']
            facilities_in_solution.append({
                'name': facility_name,
                'tree': primary_tree,
                'trees': trees,
                'component_id': trees[0].get('component_id'),
                'component_name': trees[0].get('component_name'),
                'confidence': max(t.get('confidence', 0) for t in trees),
                'depends_on': list(set(
                    dep for t in trees for dep in t.get('depends_on', [])
                )),
                'component_count': len(trees)
            })
        
        deduplicated_facilities = None
    
    facility_count = len(facilities_in_solution)
    
    result = {
        'solution_score': solution_score,
        'facility_count': facility_count,
        'tree_count': tree_count,
        'all_trees': all_trees,  # Preserve all trees
        'facilities_in_solution': facilities_in_solution,
        'component_mapping': solution.get('component_mapping', {}),
        'dependency_graph': solution.get('dependency_graph', {}),
        'production_sequence': solution.get('production_sequence', [])
    }
    
    # Add deduplicated facilities if available
    if deduplicated_facilities:
        result['deduplicated_facilities'] = deduplicated_facilities
    
    return result


def group_facilities_by_stage(
    production_sequence: Optional[List[List[str]]],
    all_trees: List[Dict[str, Any]],
    selected_facility_names: Optional[Set[str]] = None,
    selected_tree_ids: Optional[Set[str]] = None
) -> List[Dict[str, Any]]:
    """
    Group facilities by production stage from production_sequence.
    
    Only includes trees from selected facilities/solution (if provided).
    This ensures production sequence shows only the selected solution,
    not all possible combinations.
    
    Args:
        production_sequence: List of stages, each stage is a list of tree IDs
        all_trees: List of all tree dictionaries
        selected_facility_names: Set of facility names to include (filters to selected solution)
        selected_tree_ids: Set of tree IDs to include (more precise filtering)
        
    Returns:
        List of stage dictionaries with:
        - stage_number: int
        - tree_ids: List[str] (filtered)
        - trees: List[Dict] (full tree objects, filtered to selected solution)
        - can_parallelize: bool (always True for stages)
    """
    if not production_sequence:
        return []
    
    # Create a lookup: tree_id -> tree
    tree_lookup = {str(tree.get('id', '')): tree for tree in all_trees}
    
    stages = []
    for stage_idx, stage_tree_ids in enumerate(production_sequence, 1):
        trees_in_stage = []
        filtered_tree_ids = []
        
        for tree_id in stage_tree_ids:
            tree = tree_lookup.get(str(tree_id))
            if not tree:
                continue
            
            # Filter by tree ID if provided (most precise)
            if selected_tree_ids is not None:
                if str(tree_id) not in selected_tree_ids:
                    continue  # Skip trees not in selected solution
            
            # Filter by facility name if provided (less precise but useful)
            if selected_facility_names is not None:
                facility_name = tree.get('facility_name', 'Unknown')
                if facility_name not in selected_facility_names:
                    continue  # Skip trees from facilities not in selected solution
            
            trees_in_stage.append(tree)
            filtered_tree_ids.append(str(tree_id))
        
        # Only add stage if it has trees (after filtering)
        if trees_in_stage:
            stages.append({
                'stage_number': stage_idx,
                'tree_ids': filtered_tree_ids,  # Only include filtered tree IDs
                'trees': trees_in_stage,
                'can_parallelize': True  # All facilities in a stage can work in parallel
            })
    
    return stages


def get_component_name_for_tree(
    tree: Dict[str, Any],
    name_map: Dict[str, str]
) -> str:
    """
    Get component name for a tree, using name_map as fallback.
    
    Args:
        tree: Tree dictionary
        name_map: Component ID -> Component Name mapping
        
    Returns:
        Component name (or ID as fallback)
    """
    # First try component_name from tree
    comp_name = tree.get('component_name')
    if comp_name:
        return comp_name
    
    # Then try name_map using component_id
    comp_id = tree.get('component_id')
    if comp_id and comp_id in name_map:
        return name_map[comp_id]
    
    # Fallback to component_id
    if comp_id:
        return comp_id
    
    return "Unknown Component"


def parse_single_level_solutions(
    data: Dict[str, Any],
    use_selection: bool = False,  # Default False for backward compatibility
    selector_name: str = None
) -> Dict[str, Any]:
    """
    Parse single-level solutions response structure.
    
    Args:
        data: The 'data' field from the API response
        use_selection: Whether to select best solution (default: True)
        selector_name: Name of selector strategy (default: 'fewest_facilities')
        
    Returns:
        Dictionary with parsed solution information:
        - total_solutions: int (original count)
        - selected_solutions: int (after selection, if enabled)
        - facility_count: int
        - all_trees: List[Dict]
        - solutions: List[Dict] (selected solutions if use_selection=True, else all)
        - selection_criteria: str (if selection was used)
    """
    # Select best solution if enabled
    if use_selection:
        selected_data = select_best_solution(data, selector_name)
        solutions = selected_data.get('solutions', [])
        selection_criteria = selected_data.get('selection_criteria', selector_name or DEFAULT_SELECTOR)
        original_total = data.get('total_solutions', len(data.get('solutions', [])))
    else:
        solutions = data.get('solutions', [])
        selection_criteria = None
        original_total = len(solutions)
    
    # Extract trees from solutions
    all_trees = [sol.get('tree', {}) for sol in solutions if sol.get('tree')]
    
    # Count unique facilities
    facility_count = len(set(
        sol.get('facility_name') or sol.get('tree', {}).get('facility_name')
        for sol in solutions
        if sol.get('facility_name') or sol.get('tree', {}).get('facility_name')
    ))
    
    result = {
        'total_solutions': original_total,
        'facility_count': facility_count,
        'all_trees': all_trees,
        'solutions': solutions
    }
    
    if use_selection:
        result['selected_solutions'] = len(solutions)
        result['selection_criteria'] = selection_criteria
    
    return result


def get_solution_summary(matching_mode: str, parsed_data: Dict[str, Any]) -> str:
    """
    Generate a solution-level summary string.
    
    Args:
        matching_mode: 'nested' or 'single-level'
        parsed_data: Parsed solution data from parse_nested_solution or parse_single_level_solutions
        
    Returns:
        Summary string like "Solution 1: 3 facilities required" or "8 individual matches"
    """
    if matching_mode == 'nested':
        facility_count = parsed_data.get('facility_count', 0)
        return f"Solution: {facility_count} Facilities Required"
    else:
        total_solutions = parsed_data.get('total_solutions', 0)
        return f"All Matches ({total_solutions} facilities)"


def get_facility_dependency_indicator(facility_info: Dict[str, Any]) -> str:
    """
    Get visual indicator for facility dependencies.
    
    Args:
        facility_info: Facility information dict with 'depends_on' key
        
    Returns:
        Emoji indicator: "🔗" if has dependencies, "⚡" if independent
    """
    depends_on = facility_info.get('depends_on', [])
    return "🔗" if depends_on else "⚡"


def has_nested_components(okh_manifest: Dict[str, Any]) -> bool:
    """
    Check if OKH manifest has nested components that would require nested matching.
    
    This mirrors the API's _has_nested_components logic but works with dict format.
    
    Args:
        okh_manifest: OKH manifest dictionary
        
    Returns:
        True if design has nested components, False otherwise
    """
    # Check for nested components in sub_parts
    sub_parts = okh_manifest.get('sub_parts', [])
    if sub_parts and len(sub_parts) > 0:
        # Check if any sub_parts have nested sub_parts
        for sub_part in sub_parts:
            if isinstance(sub_part, dict) and sub_part.get('sub_parts'):
                return True
        # If sub_parts exist (even without nested sub_parts), it's still nested
        return True
    
    # Check for external BOM (would require BOM loading to fully check)
    # For now, return False (conservative - requires BOM loading)
    if okh_manifest.get('bom'):
        # Could check BOM file for nested structure
        # For now, return False (conservative - requires BOM loading)
        pass
    
    return False


def get_component_name_map(okh_manifest: Dict[str, Any]) -> Dict[str, str]:
    """
    Create a mapping from component ID to component name from OKH manifest.
    
    Args:
        okh_manifest: OKH manifest dictionary
        
    Returns:
        Dictionary mapping component_id -> component_name
    """
    name_map = {}
    
    # Map from parts (using 'id' field)
    parts = okh_manifest.get('parts', [])
    if isinstance(parts, list):
        for part in parts:
            if isinstance(part, dict):
                comp_id = part.get('id')
                comp_name = part.get('name')
                if comp_id:
                    name_map[str(comp_id)] = comp_name or comp_id  # Use ID as fallback
    
    # Map from sub_parts (using 'component_id' field)
    sub_parts = okh_manifest.get('sub_parts', [])
    if isinstance(sub_parts, list):
        for sub_part in sub_parts:
            if isinstance(sub_part, dict):
                comp_id = sub_part.get('component_id')
                comp_name = sub_part.get('name')
                if comp_id:
                    name_map[str(comp_id)] = comp_name or comp_id  # Use ID as fallback
    
    return name_map


def format_component_mapping(
    component_mapping: Dict[str, List[Dict[str, Any]]],
    name_map: Dict[str, str],
    selected_facility_names: Optional[Set[str]] = None,
    selected_tree_ids: Optional[Set[str]] = None,
    max_facilities_per_component: int = 3
) -> List[Dict[str, Any]]:
    """
    Format component mapping for display, with component names and deduplicated facilities.
    
    Only includes facilities from the selected solution (if provided).
    Limits to top N facilities per component by confidence score (Option 1: MVP/Demo).
    This ensures component mapping shows only the best facilities, reducing noise.
    
    Args:
        component_mapping: Dictionary mapping component_id -> list of trees
        name_map: Dictionary mapping component_id -> component_name
        selected_facility_names: Set of facility names to include (filters to selected solution)
        selected_tree_ids: Set of tree IDs to include (more precise filtering)
        max_facilities_per_component: Maximum number of facilities to show per component (default: 3)
        
    Returns:
        List of formatted component mappings with:
        - component_id: str
        - component_name: str (from name_map, trees, or ID as fallback)
        - facilities: List[str] (deduplicated facility names, filtered and limited to top N)
        - facility_details: List[Dict] (detailed facility info, sorted by confidence, limited to top N)
    """
    formatted = []
    
    for comp_id, trees in component_mapping.items():
        # Get component name with multiple fallbacks:
        # 1. Try name_map (from OKH manifest)
        # 2. Try component_name from trees (from SupplyTree objects)
        # 3. Fall back to component_id
        comp_name = name_map.get(comp_id)
        
        # If not in name_map, try to get from trees
        if not comp_name or comp_name == comp_id:
            for tree in trees:
                if isinstance(tree, dict):
                    tree_comp_name = tree.get('component_name')
                    if tree_comp_name:
                        comp_name = tree_comp_name
                        break  # Use first non-empty component_name found
        
        # Final fallback to component_id
        if not comp_name:
            comp_name = comp_id
        
        # Extract unique facilities from trees, filtering to selected solution
        # Collect all matching facilities with their details
        facility_details_all = []  # Store all facility details before limiting
        seen_facilities = set()
        
        for tree in trees:
            if not isinstance(tree, dict):
                continue
            
            # Filter by tree ID if provided (most precise)
            if selected_tree_ids is not None:
                tree_id = str(tree.get('id', ''))
                if tree_id not in selected_tree_ids:
                    continue  # Skip trees not in selected solution
            
            facility_name = tree.get('facility_name', 'Unknown')
            
            # Filter by facility name if provided
            if selected_facility_names is not None:
                if facility_name not in selected_facility_names:
                    continue  # Skip facilities not in selected solution
            
            # Track unique facilities with details
            if facility_name and facility_name not in seen_facilities:
                seen_facilities.add(facility_name)
                
                # Store facility details for sorting and limiting
                facility_details_all.append({
                    'name': facility_name,
                    'tree_id': str(tree.get('id', '')),
                    'confidence_score': tree.get('confidence_score', 0),
                    'component_id': comp_id,
                    'component_name': comp_name
                })
        
        # Sort by confidence score (highest first) - Option 1: Top N limiting
        facility_details_all.sort(key=lambda x: x['confidence_score'], reverse=True)
        
        # Limit to top N facilities per component (Option 1: MVP/Demo)
        facility_details_limited = facility_details_all[:max_facilities_per_component]
        
        # Extract facility names from limited details
        facilities = [fd['name'] for fd in facility_details_limited]
        
        formatted.append({
            'component_id': comp_id,
            'component_name': comp_name,
            'facilities': facilities,  # Already sorted by confidence (highest first)
            'facility_details': facility_details_limited,  # Limited to top N
            'total_facilities_available': len(facility_details_all),  # For info display
            'facilities_shown': len(facility_details_limited)  # For info display
        })
    
    return formatted


def detect_duplicate_component_mappings(
    formatted_mapping: List[Dict[str, Any]]
) -> Dict[str, Any]:
    """
    Detect if component mappings are duplicates (same facilities for different components).
    
    Args:
        formatted_mapping: List of formatted component mappings
        
    Returns:
        Dictionary with:
        - has_duplicates: bool
        - unique_facility_sets: int (number of unique facility combinations)
        - duplicate_groups: List[List[str]] (groups of component IDs with same facilities)
    """
    # Group components by their facility sets
    facility_set_to_components = {}
    
    for comp_info in formatted_mapping:
        # Create a tuple of sorted facilities as a key
        facilities_key = tuple(sorted(comp_info['facilities']))
        
        if facilities_key not in facility_set_to_components:
            facility_set_to_components[facilities_key] = []
        
        facility_set_to_components[facilities_key].append({
            'component_id': comp_info['component_id'],
            'component_name': comp_info['component_name']
        })
    
    # Find duplicates (multiple components with same facility set)
    duplicate_groups = []
    for facility_set, components in facility_set_to_components.items():
        if len(components) > 1:
            duplicate_groups.append([c['component_name'] or c['component_id'] for c in components])
    
    return {
        'has_duplicates': len(duplicate_groups) > 0,
        'unique_facility_sets': len(facility_set_to_components),
        'duplicate_groups': duplicate_groups,
        'total_components': len(formatted_mapping)
    }
