"""
Temporary cooking validators for backward compatibility.

This file provides temporary validators that maintain the same interface
as the original validators while the new validation framework is being integrated.
"""

from typing import Dict, Any
from ...models.supply_trees import SupplyTree


class CookingValidator:
    """Temporary validator for cooking domain - maintains original interface"""
    
    def validate(self, supply_tree: SupplyTree) -> Dict[str, Any]:
        """Validate cooking supply tree"""
        is_valid = True
        issues = []
        
        # Basic validation - check we have at least one workflow
        if not supply_tree.workflows:
            is_valid = False
            issues.append("Supply tree has no workflows")
        
        # Lazy import NetworkX
        import networkx as nx
        
        # For each workflow, check it's a valid DAG
        for wf_id, workflow in supply_tree.workflows.items():
            if not nx.is_directed_acyclic_graph(workflow.graph):
                is_valid = False
                issues.append(f"Workflow {wf_id} has cycles, which is invalid for cooking")
        
        return {
            "valid": is_valid,
            "confidence": 0.9 if is_valid else 0.3,
            "issues": issues
        }
