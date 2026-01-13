"""
Solution Selector Module

Provides extensible solution selection strategies for choosing the best solution
from multiple nested supply tree solutions.

Uses Base Class Inheritance pattern for extensibility.
"""

from abc import ABC, abstractmethod
from typing import Dict, List, Any, Set


class SolutionSelector(ABC):
    """Base class for solution selection strategies."""
    
    @abstractmethod
    def select_best(self, solutions: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Select the best solution from a list of solutions.
        
        Args:
            solutions: List of solution dictionaries from API response
            
        Returns:
            The selected solution dictionary
            
        Raises:
            ValueError: If solutions list is empty
        """
        pass
    
    def _count_unique_facilities(self, solution: Dict[str, Any]) -> int:
        """Count unique facilities in a solution."""
        # Handle nested solution format
        solution_data = solution.get('solution', {})
        all_trees = solution_data.get('all_trees', [])
        
        # Handle single-level solution format
        if not all_trees:
            # Single-level: check if there's a tree directly
            tree = solution.get('tree', {})
            if tree:
                facility_name = tree.get('facility_name') or solution.get('facility_name')
                return 1 if facility_name else 0
            # Or check facility_name directly
            facility_name = solution.get('facility_name')
            return 1 if facility_name else 0
        
        unique_facilities = set()
        for tree in all_trees:
            facility_name = tree.get('facility_name')
            if facility_name:
                unique_facilities.add(facility_name)
        
        return len(unique_facilities)
    
    def _get_solution_score(self, solution: Dict[str, Any]) -> float:
        """Get the solution score."""
        # Handle nested solution format
        solution_data = solution.get('solution', {})
        score = solution_data.get('score', 0.0)
        
        # Handle single-level solution format
        if score == 0.0:
            score = solution.get('score', solution.get('confidence', 0.0))
        
        return score
    
    def _get_average_component_score(self, solution: Dict[str, Any]) -> float:
        """Calculate average confidence score across all component matches."""
        # Handle nested solution format
        solution_data = solution.get('solution', {})
        all_trees = solution_data.get('all_trees', [])
        
        # Handle single-level solution format
        if not all_trees:
            tree = solution.get('tree', {})
            if tree:
                return tree.get('confidence_score', solution.get('confidence', solution.get('score', 0.0)))
            # Fallback to solution score/confidence
            return solution.get('score', solution.get('confidence', 0.0))
        
        total_score = sum(
            tree.get('confidence_score', 0.0) 
            for tree in all_trees
        )
        
        # Round to avoid floating point precision issues
        return round(total_score / len(all_trees), 10)


class FewestFacilitiesSelector(SolutionSelector):
    """
    Select solution with fewest unique facilities (default).
    
    This minimizes the number of facilities needed to produce the design,
    which is often preferred for simplicity and coordination.
    """
    
    def select_best(self, solutions: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Select solution with fewest unique facilities."""
        if not solutions:
            raise ValueError("Solutions list cannot be empty")
        
        if len(solutions) == 1:
            return solutions[0]
        
        # Find solution with fewest facilities
        best_solution = None
        min_facilities = float('inf')
        
        for solution in solutions:
            facility_count = self._count_unique_facilities(solution)
            
            if facility_count < min_facilities:
                min_facilities = facility_count
                best_solution = solution
            elif facility_count == min_facilities:
                # Tie-breaker: prefer higher solution score
                current_score = self._get_solution_score(best_solution)
                candidate_score = self._get_solution_score(solution)
                
                if candidate_score > current_score:
                    best_solution = solution
        
        return best_solution


class HighestScoreSelector(SolutionSelector):
    """
    Select solution with highest aggregate score.
    
    This maximizes overall confidence in the solution.
    """
    
    def select_best(self, solutions: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Select solution with highest solution score."""
        if not solutions:
            raise ValueError("Solutions list cannot be empty")
        
        if len(solutions) == 1:
            return solutions[0]
        
        # Find solution with highest score
        best_solution = None
        max_score = -1.0
        
        for solution in solutions:
            score = self._get_solution_score(solution)
            
            if score > max_score:
                max_score = score
                best_solution = solution
            elif score == max_score:
                # Tie-breaker: prefer fewer facilities
                current_facilities = self._count_unique_facilities(best_solution)
                candidate_facilities = self._count_unique_facilities(solution)
                
                if candidate_facilities < current_facilities:
                    best_solution = solution
        
        return best_solution


class BestMatchScoresSelector(SolutionSelector):
    """
    Select solution with best individual match scores.
    
    This maximizes the average confidence across all component-facility matches,
    ensuring high-quality matches for each component.
    """
    
    def select_best(self, solutions: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Select solution with highest average component match score."""
        if not solutions:
            raise ValueError("Solutions list cannot be empty")
        
        if len(solutions) == 1:
            return solutions[0]
        
        # Find solution with highest average component score
        best_solution = None
        max_avg_score = -1.0
        
        for solution in solutions:
            avg_score = self._get_average_component_score(solution)
            
            # Use small tolerance for floating point comparison
            if avg_score > max_avg_score + 1e-9:
                max_avg_score = avg_score
                best_solution = solution
            elif abs(avg_score - max_avg_score) < 1e-9:
                # Tie-breaker: prefer fewer facilities
                if best_solution is None:
                    max_avg_score = avg_score
                    best_solution = solution
                else:
                    current_facilities = self._count_unique_facilities(best_solution)
                    candidate_facilities = self._count_unique_facilities(solution)
                    
                    if candidate_facilities < current_facilities:
                        best_solution = solution
        
        return best_solution


# Registry of available selectors
SELECTOR_REGISTRY = {
    'fewest_facilities': FewestFacilitiesSelector,
    'highest_score': HighestScoreSelector,
    'best_match_scores': BestMatchScoresSelector,
}

# Default selector
DEFAULT_SELECTOR = 'fewest_facilities'


def get_selector(selector_name: str = None) -> SolutionSelector:
    """
    Get a solution selector by name.
    
    Args:
        selector_name: Name of the selector (default: 'fewest_facilities')
        
    Returns:
        SolutionSelector instance
        
    Raises:
        ValueError: If selector name is not found
    """
    if selector_name is None:
        selector_name = DEFAULT_SELECTOR
    
    if selector_name not in SELECTOR_REGISTRY:
        raise ValueError(
            f"Unknown selector: {selector_name}. "
            f"Available: {list(SELECTOR_REGISTRY.keys())}"
        )
    
    selector_class = SELECTOR_REGISTRY[selector_name]
    return selector_class()
