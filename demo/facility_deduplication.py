"""
Facility Deduplication Module

Groups facilities by name and aggregates component assignments.
Shows each facility once with all components it produces.
"""

from typing import Dict, List, Any, Set, Optional


def deduplicate_facilities(
    all_trees: List[Dict[str, Any]],
    aggregate_score_method: str = 'highest',
    min_confidence: float = 0.0
) -> List[Dict[str, Any]]:
    """
    Deduplicate facilities by grouping by facility name.
    
    Each facility appears once with all components it produces listed.
    
    Args:
        all_trees: List of all tree dictionaries from solution
        aggregate_score_method: How to aggregate scores ('highest' or 'average')
        min_confidence: Minimum confidence score to include (default: 0.0, include all)
                        Use > 0.0 to filter out low-confidence matches
        
    Returns:
        List of deduplicated facility dictionaries with:
        - name: str (facility name)
        - components: List[Dict] (all components this facility produces)
        - aggregate_score: float
        - stage: str (most common stage, or 'mixed' if multiple)
        - depends_on: Set[str] (all dependencies)
    """
    # Filter out trees with confidence below threshold
    # This ensures only actual matches are included (not failed matches with 0.0 confidence)
    filtered_trees = [
        tree for tree in all_trees
        if tree.get('confidence_score', 0.0) > min_confidence
    ]
    
    # Group trees by facility name
    facilities_dict: Dict[str, List[Dict[str, Any]]] = {}
    
    for tree in filtered_trees:
        facility_name = tree.get('facility_name', 'Unknown')
        
        if facility_name not in facilities_dict:
            facilities_dict[facility_name] = []
        
        facilities_dict[facility_name].append(tree)
    
    # Convert to list format
    deduplicated = []
    
    for facility_name, trees in facilities_dict.items():
        # Extract component information from trees, deduplicating by component_id
        # This ensures each component is only counted once per facility, even if
        # multiple trees exist for the same component (e.g., from different solutions)
        components_by_id: Dict[str, Dict[str, Any]] = {}
        scores = []
        stages = []
        all_depends_on = set()
        
        for tree in trees:
            component_id = tree.get('component_id')
            component_name = tree.get('component_name')
            confidence_score = tree.get('confidence_score', 0.0)
            production_stage = tree.get('production_stage', 'final')
            depends_on = tree.get('depends_on', [])
            
            # If we haven't seen this component_id yet, or if this tree has a higher confidence score
            if component_id:
                if component_id not in components_by_id:
                    # First time seeing this component - add it
                    components_by_id[component_id] = {
                        'tree': tree,
                        'component_id': component_id,
                        'component_name': component_name,
                        'confidence_score': confidence_score,
                        'production_stage': production_stage,
                        'depends_on': depends_on
                    }
                else:
                    # Component already exists - keep the one with higher confidence score
                    existing_score = components_by_id[component_id].get('confidence_score', 0.0)
                    if confidence_score > existing_score:
                        components_by_id[component_id] = {
                            'tree': tree,
                            'component_id': component_id,
                            'component_name': component_name,
                            'confidence_score': confidence_score,
                            'production_stage': production_stage,
                            'depends_on': depends_on
                        }
            else:
                # Component without ID - add it (shouldn't happen, but handle gracefully)
                # Use tree ID as fallback key
                tree_id = str(tree.get('id', ''))
                if tree_id and tree_id not in components_by_id:
                    components_by_id[tree_id] = {
                        'tree': tree,
                        'component_id': component_id,
                        'component_name': component_name,
                        'confidence_score': confidence_score,
                        'production_stage': production_stage,
                        'depends_on': depends_on
                    }
            
            # Always collect scores and stages for aggregation (use all trees)
            scores.append(confidence_score)
            stages.append(production_stage)
            
            # Collect all dependencies
            if depends_on:
                all_depends_on.update(str(dep) for dep in depends_on)
        
        # Convert deduplicated components dict to list
        components = list(components_by_id.values())
        
        # Calculate aggregate score
        if aggregate_score_method == 'highest':
            aggregate_score = max(scores) if scores else 0.0
        elif aggregate_score_method == 'average':
            aggregate_score = sum(scores) / len(scores) if scores else 0.0
        else:
            raise ValueError(f"Unknown aggregate_score_method: {aggregate_score_method}")
        
        # Determine stage (most common, or 'mixed' if multiple different stages)
        unique_stages = set(stages)
        if len(unique_stages) == 1:
            stage = stages[0]
        else:
            stage = 'mixed'
        
        deduplicated.append({
            'name': facility_name,
            'components': components,
            'component_count': len(components),
            'aggregate_score': aggregate_score,
            'stage': stage,
            'depends_on': list(all_depends_on),
            'primary_tree': trees[0]  # Keep first tree for backward compatibility
        })
    
    return deduplicated


def get_primary_facility_for_component(
    component_id: str,
    component_mapping: Dict[str, List[Dict[str, Any]]],
    all_trees: List[Dict[str, Any]]
) -> Optional[Dict[str, Any]]:
    """
    Get the primary (best match) facility for a component.
    
    Args:
        component_id: Component ID
        component_mapping: Component mapping from solution
        all_trees: All trees from solution
        
    Returns:
        Tree dictionary for primary facility, or None if not found
    """
    if component_id not in component_mapping:
        return None
    
    trees = component_mapping[component_id]
    if not trees:
        return None
    
    # Find the tree with highest confidence score
    best_tree = None
    best_score = -1.0
    
    for tree in trees:
        if isinstance(tree, dict):
            score = tree.get('confidence_score', 0.0)
            if score > best_score:
                best_score = score
                best_tree = tree
    
    return best_tree


def get_alternative_facilities_for_component(
    component_id: str,
    component_mapping: Dict[str, List[Dict[str, Any]]],
    primary_facility_name: str,
    limit: int = 5
) -> List[Dict[str, Any]]:
    """
    Get alternative facilities for a component (excluding primary).
    
    Args:
        component_id: Component ID
        component_mapping: Component mapping from solution
        primary_facility_name: Name of primary facility
        limit: Maximum number of alternatives to return
        
    Returns:
        List of alternative facility trees, sorted by confidence (highest first)
    """
    if component_id not in component_mapping:
        return []
    
    trees = component_mapping[component_id]
    alternatives = []
    
    for tree in trees:
        if isinstance(tree, dict):
            facility_name = tree.get('facility_name')
            if facility_name and facility_name != primary_facility_name:
                alternatives.append(tree)
    
    # Sort by confidence score (highest first)
    alternatives.sort(
        key=lambda t: t.get('confidence_score', 0.0),
        reverse=True
    )
    
    return alternatives[:limit]
