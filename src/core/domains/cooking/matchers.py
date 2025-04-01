import networkx as nx
from uuid import uuid4
from src.core.models.base_types import NormalizedRequirements, NormalizedCapabilities
from src.core.models.supply_trees import SupplyTree, Workflow, WorkflowNode, ResourceURI, ResourceType

class CookingMatcher:
    """Matcher for cooking domain"""
    
    def generate_supply_tree(self, requirements: 'NormalizedRequirements', 
                           capabilities: 'NormalizedCapabilities') -> SupplyTree:
        """Generate a cooking supply tree"""
        # Create supply tree
        supply_tree = SupplyTree()
        
        # Create primary workflow
        workflow = Workflow(
            id=uuid4(),
            name="Cooking Process",
            graph=nx.DiGraph()
        )
        
        # Add nodes for each recipe step
        prev_node = None
        for i, step in enumerate(requirements.content.get("steps", [])):
            # Create node
            node = WorkflowNode(
                name=f"Step {i+1}: {step[:30]}...",
                okh_refs=[ResourceURI(
                    resource_type=ResourceType.RECIPE,
                    identifier=f"step_{i}",
                    path=["steps"]
                )],
                okw_refs=[],
                input_requirements={"step": step},
                output_specifications={}
            )
            
            # Add to workflow
            workflow.add_node(node)
            
            # Connect to previous node if it exists
            if prev_node:
                workflow.graph.add_edge(prev_node.id, node.id)
            
            prev_node = node
        
        # Add workflow to supply tree
        supply_tree.add_workflow(workflow)
        
        # Add snapshots for requirements and capabilities
        supply_tree.add_snapshot("recipe://main", requirements.content)
        supply_tree.add_snapshot("kitchen://main", capabilities.content)
        
        return supply_tree