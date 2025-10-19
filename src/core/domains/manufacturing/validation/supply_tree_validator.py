"""
Supply tree validator for manufacturing domain.

This module provides a supply tree validator for the manufacturing domain.
"""

from typing import Dict, Any, Optional, List
from ....validation.engine import Validator
from ....validation.context import ValidationContext
from ....validation.result import ValidationResult, ValidationError, ValidationWarning
from ....validation.rules.manufacturing import ManufacturingValidationRules
from ....models.supply_trees import SupplyTree
from ....models.okh import OKHManifest


class ManufacturingSupplyTreeValidator(Validator):
    """Supply tree validator for manufacturing domain using new validation framework"""
    
    def __init__(self):
        self.validation_rules = ManufacturingValidationRules()
    
    @property
    def validation_type(self) -> str:
        """Return the type of validation this validator performs"""
        return "supply_tree"
    
    @property
    def priority(self) -> int:
        """Return validation priority (higher = earlier)"""
        return 60  # Medium priority for supply tree validation
    
    async def validate(self, data: Any, context: Optional[ValidationContext] = None) -> ValidationResult:
        """Validate supply tree data using domain-specific rules"""
        result = ValidationResult(valid=True)
        
        # Handle different data types
        if isinstance(data, SupplyTree):
            return await self._validate_supply_tree(data, context)
        elif isinstance(data, dict):
            # Try to create SupplyTree from dict
            try:
                supply_tree = SupplyTree.from_dict(data)
                return await self._validate_supply_tree(supply_tree, context)
            except Exception as e:
                result.add_error(f"Failed to parse supply tree: {str(e)}")
                return result
        else:
            result.add_error(f"Unsupported data type for supply tree validation: {type(data)}")
            return result
    
    async def _validate_supply_tree(self, supply_tree: SupplyTree, 
                                  context: Optional[ValidationContext] = None) -> ValidationResult:
        """Validate supply tree using domain-specific rules"""
        result = ValidationResult(valid=True)
        
        # Get quality level from context or default to professional
        quality_level = "professional"
        if context:
            quality_level = context.quality_level
        
        # Validate quality level is supported
        if not ManufacturingValidationRules.validate_quality_level(quality_level):
            result.add_error(f"Unsupported quality level: {quality_level}")
            return result
        
        # Validate basic supply tree structure
        await self._validate_basic_structure(supply_tree, quality_level, result)
        
        # Validate workflows
        await self._validate_workflows(supply_tree, quality_level, result)
        
        # Validate nodes
        await self._validate_nodes(supply_tree, quality_level, result)
        
        # Validate edges
        await self._validate_edges(supply_tree, quality_level, result)
        
        # Calculate supply tree quality score
        quality_score = self._calculate_quality_score(supply_tree, quality_level)
        result.metadata['quality_score'] = quality_score
        
        return result
    
    async def _validate_basic_structure(self, supply_tree: SupplyTree, 
                                      quality_level: str, result: ValidationResult):
        """Validate basic supply tree structure"""
        
        # Check if supply tree has workflows
        if not hasattr(supply_tree, 'workflows') or not supply_tree.workflows:
            result.add_error(
                "Supply tree has no workflows",
                field="workflows",
                code="no_workflows"
            )
            return
        
        # Check if workflows is a dictionary
        if not isinstance(supply_tree.workflows, dict):
            result.add_error(
                "Workflows must be a dictionary",
                field="workflows",
                code="workflows_not_dict"
            )
            return
        
        # Check if there's at least one workflow
        if len(supply_tree.workflows) == 0:
            result.add_error(
                "At least one workflow is required",
                field="workflows",
                code="no_workflows"
            )
    
    async def _validate_workflows(self, supply_tree: SupplyTree, 
                                quality_level: str, result: ValidationResult):
        """Validate individual workflows"""
        
        for workflow_id, workflow in supply_tree.workflows.items():
            await self._validate_workflow(workflow, workflow_id, quality_level, result)
    
    async def _validate_workflow(self, workflow: Any, workflow_id: str, 
                               quality_level: str, result: ValidationResult):
        """Validate individual workflow"""
        
        # Check if workflow has a graph
        if not hasattr(workflow, 'graph'):
            result.add_error(
                f"Workflow {workflow_id}: missing graph",
                field=f"workflows.{workflow_id}.graph",
                code="workflow_missing_graph"
            )
            return
        
        graph = workflow.graph
        
        # Lazy import NetworkX
        import networkx as nx
        
        # Check if graph is a NetworkX graph
        if not isinstance(graph, nx.Graph):
            result.add_error(
                f"Workflow {workflow_id}: graph must be a NetworkX graph",
                field=f"workflows.{workflow_id}.graph",
                code="workflow_invalid_graph_type"
            )
            return
        
        # Check if graph is a DAG (Directed Acyclic Graph)
        if not nx.is_directed_acyclic_graph(graph):
            result.add_error(
                f"Workflow {workflow_id}: graph contains cycles, which is invalid for supply trees",
                field=f"workflows.{workflow_id}.graph",
                code="workflow_has_cycles"
            )
        
        # Check if graph has nodes
        if graph.number_of_nodes() == 0:
            result.add_error(
                f"Workflow {workflow_id}: graph has no nodes",
                field=f"workflows.{workflow_id}.graph",
                code="workflow_no_nodes"
            )
        
        # Check if graph has edges
        if graph.number_of_edges() == 0:
            result.add_warning(
                f"Workflow {workflow_id}: graph has no edges",
                field=f"workflows.{workflow_id}.graph",
                code="workflow_no_edges"
            )
    
    async def _validate_nodes(self, supply_tree: SupplyTree, 
                            quality_level: str, result: ValidationResult):
        """Validate workflow nodes"""
        
        for workflow_id, workflow in supply_tree.workflows.items():
            for node_id in workflow.graph.nodes:
                await self._validate_node(workflow.graph.nodes[node_id], 
                                        node_id, workflow_id, quality_level, result)
    
    async def _validate_node(self, node_data: Any, node_id: str, 
                           workflow_id: str, quality_level: str, result: ValidationResult):
        """Validate individual node"""
        
        # Check if node has data
        if 'data' not in node_data:
            result.add_error(
                f"Node {node_id} in workflow {workflow_id}: missing data",
                field=f"workflows.{workflow_id}.nodes.{node_id}.data",
                code="node_missing_data"
            )
            return
        
        node = node_data['data']
        
        # Check if node has a name
        if not hasattr(node, 'name') or not node.name:
            result.add_error(
                f"Node {node_id} in workflow {workflow_id}: missing name",
                field=f"workflows.{workflow_id}.nodes.{node_id}.name",
                code="node_missing_name"
            )
        
        # Check if node has a type
        if not hasattr(node, 'type') or not node.type:
            result.add_warning(
                f"Node {node_id} in workflow {workflow_id}: missing type",
                field=f"workflows.{workflow_id}.nodes.{node_id}.type",
                code="node_missing_type"
            )
    
    async def _validate_edges(self, supply_tree: SupplyTree, 
                            quality_level: str, result: ValidationResult):
        """Validate workflow edges"""
        
        for workflow_id, workflow in supply_tree.workflows.items():
            for edge in workflow.graph.edges:
                await self._validate_edge(edge, workflow_id, quality_level, result)
    
    async def _validate_edge(self, edge: tuple, workflow_id: str, 
                           quality_level: str, result: ValidationResult):
        """Validate individual edge"""
        
        source, target = edge
        
        # Check if edge connects valid nodes
        if source not in supply_tree.workflows[workflow_id].graph.nodes:
            result.add_error(
                f"Edge in workflow {workflow_id}: source node {source} does not exist",
                field=f"workflows.{workflow_id}.edges",
                code="edge_invalid_source"
            )
        
        if target not in supply_tree.workflows[workflow_id].graph.nodes:
            result.add_error(
                f"Edge in workflow {workflow_id}: target node {target} does not exist",
                field=f"workflows.{workflow_id}.edges",
                code="edge_invalid_target"
            )
    
    def _calculate_quality_score(self, supply_tree: SupplyTree, quality_level: str) -> float:
        """Calculate supply tree quality score (0.0-1.0)"""
        
        if not supply_tree.workflows:
            return 0.0
        
        total_score = 0.0
        workflow_count = 0
        
        # Lazy import NetworkX
        import networkx as nx
        
        for workflow in supply_tree.workflows.values():
            workflow_score = 0.0
            
            # Graph structure score
            if hasattr(workflow, 'graph') and isinstance(workflow.graph, nx.Graph):
                # Check if it's a DAG
                if nx.is_directed_acyclic_graph(workflow.graph):
                    workflow_score += 0.3
                
                # Check node count
                node_count = workflow.graph.number_of_nodes()
                if node_count > 0:
                    workflow_score += 0.2
                
                # Check edge count
                edge_count = workflow.graph.number_of_edges()
                if edge_count > 0:
                    workflow_score += 0.2
                
                # Check connectivity
                if node_count > 1:
                    # Calculate connectivity ratio
                    max_edges = node_count * (node_count - 1)  # Directed graph
                    if max_edges > 0:
                        connectivity = edge_count / max_edges
                        workflow_score += 0.3 * min(1.0, connectivity)
            
            total_score += workflow_score
            workflow_count += 1
        
        return total_score / workflow_count if workflow_count > 0 else 0.0
