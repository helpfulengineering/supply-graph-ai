from pydantic import BaseModel, Field
from typing import Dict, Any, Optional, List
from uuid import UUID, uuid4
from enum import Enum
import networkx as nx

from src.core.registry.domain_registry import DomainRegistry
from src.core.models.supply_trees import SupplyTree, Workflow, WorkflowNode, ResourceURI, ResourceType


class RequirementsInput(BaseModel):
    content: Dict[str, Any]
    domain: Optional[str] = None
    type: str  # "okh" or "recipe"

class CapabilitiesInput(BaseModel):
    content: Dict[str, Any]
    domain: Optional[str] = None
    type: str  # "okw" or "kitchen"

class ProcessNode(BaseModel):
    id: UUID
    name: str
    inputs: List[str]
    outputs: List[str]
    requirements: Dict[str, Any]
    capabilities: Dict[str, Any]

class Workflow(BaseModel):
    id: UUID
    name: str
    nodes: Dict[str, ProcessNode]
    edges: List[Dict[str, UUID]]

class SupplyTreeResponse(BaseModel):
    id: UUID = Field(default_factory=uuid4)
    domain: str
    workflows: Dict[str, Workflow]
    confidence: float
    validation_status: bool
    metadata: Dict[str, Any] = {}


# Base classes for extractors, matchers, and validators
class BaseExtractor:
    def extract_requirements(self, content: Dict) -> 'NormalizedRequirements':
        raise NotImplementedError("Subclasses must implement extract_requirements")
        
    def extract_capabilities(self, content: Dict) -> 'NormalizedCapabilities':
        raise NotImplementedError("Subclasses must implement extract_capabilities")

class BaseMatcher:
    def generate_supply_tree(self, requirements: 'NormalizedRequirements', 
                            capabilities: 'NormalizedCapabilities') -> 'SupplyTree':
        raise NotImplementedError("Subclasses must implement generate_supply_tree")

class BaseValidator:
    def validate(self, supply_tree: 'SupplyTree') -> Dict:
        raise NotImplementedError("Subclasses must implement validate")

# Normalized data models with domain tracking
class NormalizedData:
    def __init__(self, content: Dict, domain: str):
        self.content = content
        self.domain = domain
        
class NormalizedRequirements(NormalizedData):
    pass
    
class NormalizedCapabilities(NormalizedData):
    pass

# Domain-specific implementations
class ManufacturingExtractor(BaseExtractor):
    def extract_requirements(self, content: Dict) -> NormalizedRequirements:
        # Extract OKH data to normalized requirements
        # Parse fields like materials, processes, tools, etc.
        return NormalizedRequirements(content=self._process_okh(content), domain="manufacturing")
    
    def extract_capabilities(self, content: Dict) -> NormalizedCapabilities:
        # Extract OKW data to normalized capabilities
        # Parse fields like equipment, facilities, etc.
        return NormalizedCapabilities(content=self._process_okw(content), domain="manufacturing")
        
    def _process_okh(self, content: Dict) -> Dict:
        # Process OKH data into normalized format
        processed = {
            "materials": content.get("materials", []),
            "processes": content.get("manufacturing_processes", []),
            "tools": content.get("tool_list", []),
            # Additional processing of OKH fields
        }
        return processed
        
    def _process_okw(self, content: Dict) -> Dict:
        # Process OKW data into normalized format
        processed = {
            "equipment": content.get("equipment", []),
            "processes": content.get("manufacturing_processes", []),
            "materials": content.get("typical_materials", []),
        }
        return processed

class CookingExtractor(BaseExtractor):
    def extract_requirements(self, content: Dict) -> NormalizedRequirements:
        # Extract recipe data to normalized requirements
        return NormalizedRequirements(content=self._process_recipe(content), domain="cooking")
    
    def extract_capabilities(self, content: Dict) -> NormalizedCapabilities:
        # Extract kitchen data to normalized capabilities
        return NormalizedCapabilities(content=self._process_kitchen(content), domain="cooking")
        
    def _process_recipe(self, content: Dict) -> Dict:
        # Process recipe data into normalized format
        processed = {
            "ingredients": content.get("ingredients", []),
            "steps": content.get("instructions", []),
            "tools": content.get("equipment", []),
            # Additional processing of recipe fields
        }
        return processed
        
    def _process_kitchen(self, content: Dict) -> Dict:
        # Process kitchen data into normalized format
        processed = {
            "available_ingredients": content.get("ingredients", []),
            "available_tools": content.get("tools", []),
            "appliances": content.get("appliances", []),
            # Additional processing of kitchen fields
        }
        return processed

class ManufacturingMatcher(BaseMatcher):
    def generate_supply_tree(self, requirements: NormalizedRequirements, 
                           capabilities: NormalizedCapabilities) -> 'SupplyTree':
        supply_tree = SupplyTree()
        
        # Create primary workflow
        workflow = Workflow(
            id=uuid4(),
            name="Manufacturing Workflow",
            graph=nx.DiGraph(),
            entry_points=set(),
            exit_points=set()
        )
        
        # Match processes to equipment
        for process in requirements.content.get("processes", []):
            matching_equipment = self._find_matching_equipment(
                process, capabilities.content.get("equipment", [])
            )
            
            if matching_equipment:
                # Create node for this process
                node = WorkflowNode(
                    name=f"Process: {process}",
                    okh_refs=[self._create_resource_uri("okh", process, ["processes"])],
                    okw_refs=[self._create_resource_uri("okw", equip, ["equipment"]) 
                             for equip in matching_equipment]
                )
                workflow.add_node(node)
        
        # Add workflow to supply tree
        supply_tree.add_workflow(workflow)
        
        return supply_tree
        
    def _find_matching_equipment(self, process: str, equipment: List) -> List:
        # Find equipment that can handle this process
        # Simplified matching logic
        return [e for e in equipment if self._can_equipment_handle_process(e, process)]
        
    def _can_equipment_handle_process(self, equipment: Dict, process: str) -> bool:
        # Check if equipment can handle process
        # Simplified check
        return process in equipment.get("processes", [])
        
    def _create_resource_uri(self, type_str: str, identifier: str, path: List[str]) -> 'ResourceURI':
        # Create a resource URI
        return ResourceURI(
            resource_type=ResourceType(type_str),
            identifier=identifier,
            path=path
        )

class CookingMatcher(BaseMatcher):
    def generate_supply_tree(self, requirements: NormalizedRequirements, 
                           capabilities: NormalizedCapabilities) -> 'SupplyTree':
        
        supply_tree = SupplyTree()
        
        # Create primary workflow
        workflow = Workflow(
            id=uuid4(),
            name="Cooking Workflow",
            graph=nx.DiGraph(),
            entry_points=set(),
            exit_points=set()
        )
        
        # Process recipe steps
        previous_node = None
        for i, step in enumerate(requirements.content.get("steps", [])):
            # Check if kitchen can support this step
            required_tools = self._extract_tools_from_step(step)
            available_tools = capabilities.content.get("available_tools", [])
            
            if self._can_kitchen_handle_step(required_tools, available_tools):
                # Create node for this step
                node = WorkflowNode(
                    name=f"Step {i+1}: {step[:50]}...",
                    okh_refs=[self._create_resource_uri("recipe", f"step_{i}", ["steps"])],
                    okw_refs=[self._create_resource_uri("kitchen", tool, ["tools"]) 
                             for tool in required_tools]
                )
                
                # Add node and connect to previous if exists
                workflow.add_node(node)
                if previous_node:
                    workflow.graph.add_edge(previous_node.id, node.id)
                
                previous_node = node
        
        # Add workflow to supply tree
        supply_tree.add_workflow(workflow)
        
        return supply_tree
        
    def _extract_tools_from_step(self, step: str) -> List[str]:
        # Extract required tools from step description
        # Simplified extraction
        import re
        tools = []
        tool_patterns = ["using a ([a-zA-Z ]+)", "with a ([a-zA-Z ]+)", "in a ([a-zA-Z ]+)"]
        for pattern in tool_patterns:
            matches = re.findall(pattern, step.lower())
            tools.extend(matches)
        return tools
        
    def _can_kitchen_handle_step(self, required_tools: List[str], available_tools: List[str]) -> bool:
        # Check if kitchen has necessary tools
        return all(any(req.lower() in avail.lower() for avail in available_tools) for req in required_tools)
        
    def _create_resource_uri(self, type_str: str, identifier: str, path: List[str]) -> 'ResourceURI':
            return ResourceURI(
            resource_type=ResourceType(type_str),
            identifier=identifier,
            path=path
        )

class ManufacturingValidator(BaseValidator):
    def validate(self, supply_tree: 'SupplyTree') -> Dict:
        # Validate manufacturing supply tree
        is_valid = True
        issues = []
        
        # Check if all processes have matching equipment
        for workflow in supply_tree.workflows.values():
            for node_id in workflow.graph.nodes():
                node_data = workflow.graph.nodes[node_id]['data']
                if not node_data.get('okw_refs'):
                    issues.append(f"Node {node_id} has no matching equipment")
                    is_valid = False
        
        # Check for disconnected nodes
        for workflow in supply_tree.workflows.values():
            if not nx.is_connected(workflow.graph.to_undirected()):
                issues.append(f"Workflow {workflow.id} has disconnected nodes")
                is_valid = False
        
        return {
            "valid": is_valid,
            "confidence": 0.8 if is_valid else 0.4,
            "issues": issues
        }

class CookingValidator(BaseValidator):
    def validate(self, supply_tree: 'SupplyTree') -> Dict:
        # Validate cooking supply tree
        is_valid = True
        issues = []
        
        # Check if all steps have required tools
        for workflow in supply_tree.workflows.values():
            for node_id in workflow.graph.nodes():
                node_data = workflow.graph.nodes[node_id]['data']
                if not node_data.get('okw_refs'):
                    issues.append(f"Step {node_id} requires unavailable tools")
                    is_valid = False
        
        # Check for proper sequence (should be a path)
        for workflow in supply_tree.workflows.values():
            if not nx.is_directed_acyclic_graph(workflow.graph):
                issues.append(f"Workflow {workflow.id} has cycles, which is invalid for cooking")
                is_valid = False
        
        return {
            "valid": is_valid,
            "confidence": 0.9 if is_valid else 0.3,
            "issues": issues
        }

# Register domain components
DomainRegistry.register_extractor("manufacturing", ManufacturingExtractor())
DomainRegistry.register_matcher("manufacturing", ManufacturingMatcher())
DomainRegistry.register_validator("manufacturing", ManufacturingValidator())

DomainRegistry.register_extractor("cooking", CookingExtractor())
DomainRegistry.register_matcher("cooking", CookingMatcher())
DomainRegistry.register_validator("cooking", CookingValidator())