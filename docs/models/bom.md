# Bill of Materials

## Overview

The Open Matching Engine supports nested and recursive Bill of Materials where any component can potentially be decomposed into sub-components. The complexity emerges dynamically during the matching process based on component availability and matching requirements.

## Key Principles

1. **Uniform Component Model**: All components use the same data structure, with optional children
2. **Dynamic Complexity**: A component is treated as "simple" if it's available or as "complex" if it needs to be decomposed
3. **Availability-Driven Recursion**: The system only recurses into sub-components when a component isn't directly available
4. **Depth Control**: User-specified maximum depth limits how deep the matching process will go

## Implementation Details

### Component Structure

Components have a unified structure with:
- Basic information (id, name, quantity, unit)
- Optional sub-components list
- Optional reference to an external definition
- Material and process requirements

### Matching Process

1. For each component, the matcher first tries to find a direct match
2. If no direct match is found and the current depth < max_depth:
   a. If the component has sub-components, it tries to match those
   b. If the component has an external reference, it resolves and matches it
3. If depth limit is reached, the component is considered unmatchable

### Supply Tree Generation

The Supply Tree reflects this dynamic complexity:
- Components matched directly become simple workflow nodes
- Components that required decomposition generate connected sub-workflows
- The resulting structure captures both the logical and physical dependencies

## Example Scenario

Given a "Chair" component that requires:
- Wood frame
- Cushion
- Mounting hardware

The matching process would:
1. Try to find a direct match for the complete chair
2. If not found, try to match each sub-component:
   - If "Wood frame" isn't available, decompose further into timber pieces
   - If "Cushion" is available, treat it as a simple component
   - If "Mounting hardware" isn't directly available, match its sub-components

The resulting Supply Tree would show:
- The chair as the root workflow
- Connected workflows for any components that required decomposition
- Direct nodes for components that were matched without decomposition

# Code Scaffolding

```python
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Any, Union
from uuid import UUID, uuid4
from enum import Enum


@dataclass
class Component:
    """Unified component model supporting nested structure"""
    id: str
    name: str
    quantity: float
    unit: str
    sub_components: List['Component'] = field(default_factory=list)
    reference: Optional[Dict[str, str]] = None  # {type, id} for external reference
    requirements: Dict[str, Any] = field(default_factory=dict)
    metadata: Dict[str, Any] = field(default_factory=dict)
    # Additional fields for Supply Tree compatibility
    process_steps: List[str] = field(default_factory=list)
    equipment_requirements: Dict[str, Any] = field(default_factory=dict)
    time_requirements: Dict[str, Any] = field(default_factory=dict)
    quality_requirements: Dict[str, Any] = field(default_factory=dict)
    
    # Optional properties
    cost_factors: Dict[str, float] = field(default_factory=dict)
    energy_requirements: Dict[str, Any] = field(default_factory=dict)
    skill_requirements: List[str] = field(default_factory=list)
    environmental_impact: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary representation"""
        result = {
            "id": self.id,
            "name": self.name,
            "quantity": self.quantity,
            "unit": self.unit,
            "requirements": self.requirements,
            "metadata": self.metadata
        }
        
        if self.sub_components:
            result["sub_components"] = [c.to_dict() for c in self.sub_components]
            
        if self.reference:
            result["reference"] = self.reference
            
        return result
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'Component':
        """Create from dictionary representation"""
        sub_components = []
        
        if "sub_components" in data:
            for comp_data in data["sub_components"]:
                sub_components.append(cls.from_dict(comp_data))
        
        return cls(
            id=data["id"],
            name=data["name"],
            quantity=data["quantity"],
            unit=data["unit"],
            sub_components=sub_components,
            reference=data.get("reference"),
            requirements=data.get("requirements", {}),
            metadata=data.get("metadata", {})
        )
    
    def has_decomposition(self) -> bool:
        """Check if this component has sub-components or a reference"""
        return bool(self.sub_components) or bool(self.reference)


class ReferenceResolver:
    """Handles resolution of external component references"""
    
    def resolve(self, reference_type: str, reference_id: str) -> Optional[Component]:
        """Resolve a reference to a component"""
        # Implementation would depend on how references are stored/retrieved
        pass


class MatchResult(Enum):
    """Possible results from component matching"""
    DIRECT_MATCH = "direct_match"       # Component matched directly
    DECOMPOSED_MATCH = "decomposed"     # Component matched via decomposition
    NO_MATCH = "no_match"               # Component couldn't be matched
    DEPTH_LIMIT_REACHED = "depth_limit" # Matching stopped due to depth limit


@dataclass
class ComponentMatchResult:
    """Result of matching a component"""
    component: Component
    result: MatchResult
    matched_capability: Optional[Any] = None
    sub_results: List['ComponentMatchResult'] = field(default_factory=list)
    confidence: float = 0.0
    depth: int = 0


class ComponentMatcher:
    """Matches components against available capabilities with depth control"""
    
    def __init__(self, reference_resolver: Optional[ReferenceResolver] = None):
        self.resolver = reference_resolver or ReferenceResolver()
    
    def match_component(self, 
                       component: Component, 
                       capabilities: List[Any],
                       max_depth: int = 5,
                       current_depth: int = 0) -> ComponentMatchResult:
        """
        Match a component against available capabilities
        
        Args:
            component: The component to match
            capabilities: Available capabilities to match against
            max_depth: Maximum recursion depth allowed
            current_depth: Current depth in the recursion
            
        Returns:
            ComponentMatchResult with match details
        """
        # Try direct match first
        direct_match = self._find_direct_match(component, capabilities)
        
        if direct_match:
            return ComponentMatchResult(
                component=component,
                result=MatchResult.DIRECT_MATCH,
                matched_capability=direct_match,
                confidence=1.0,
                depth=current_depth
            )
        
        # If we've reached max depth, stop here
        if current_depth >= max_depth:
            return ComponentMatchResult(
                component=component,
                result=MatchResult.DEPTH_LIMIT_REACHED,
                confidence=0.0,
                depth=current_depth
            )
        
        # If component has sub-components, try matching those
        if component.sub_components:
            return self._match_sub_components(
                component=component,
                capabilities=capabilities,
                max_depth=max_depth,
                current_depth=current_depth
            )
        
        # If component has a reference, resolve and match it
        if component.reference:
            return self._match_reference(
                component=component,
                capabilities=capabilities,
                max_depth=max_depth,
                current_depth=current_depth
            )
        
        # No match possible
        return ComponentMatchResult(
            component=component,
            result=MatchResult.NO_MATCH,
            confidence=0.0,
            depth=current_depth
        )
    
    def _find_direct_match(self, component: Component, capabilities: List[Any]) -> Optional[Any]:
        """Find a direct match for a component"""
        # Implementation depends on how capabilities are structured
        # This would match component requirements against capabilities
        pass
    
    def _match_sub_components(self, 
                            component: Component, 
                            capabilities: List[Any],
                            max_depth: int,
                            current_depth: int) -> ComponentMatchResult:
        """Match a component by matching its sub-components"""
        sub_results = []
        
        # Match each sub-component
        for sub_component in component.sub_components:
            sub_result = self.match_component(
                component=sub_component,
                capabilities=capabilities,
                max_depth=max_depth,
                current_depth=current_depth + 1
            )
            sub_results.append(sub_result)
        
        # Check if all sub-components matched
        all_matched = all(r.result in [MatchResult.DIRECT_MATCH, MatchResult.DECOMPOSED_MATCH] 
                         for r in sub_results)
        
        if all_matched:
            # Calculate aggregate confidence
            confidence = sum(r.confidence for r in sub_results) / len(sub_results)
            
            return ComponentMatchResult(
                component=component,
                result=MatchResult.DECOMPOSED_MATCH,
                sub_results=sub_results,
                confidence=confidence,
                depth=current_depth
            )
        else:
            return ComponentMatchResult(
                component=component,
                result=MatchResult.NO_MATCH,
                sub_results=sub_results,
                confidence=0.0,
                depth=current_depth
            )
    
    def _match_reference(self, 
                       component: Component, 
                       capabilities: List[Any],
                       max_depth: int,
                       current_depth: int) -> ComponentMatchResult:
        """Match a component by resolving and matching its reference"""
        ref = component.reference
        
        # Resolve reference
        resolved = self.resolver.resolve(ref["type"], ref["id"])
        
        if not resolved:
            return ComponentMatchResult(
                component=component,
                result=MatchResult.NO_MATCH,
                confidence=0.0,
                depth=current_depth
            )
        
        # Match resolved component
        resolved_result = self.match_component(
            component=resolved,
            capabilities=capabilities,
            max_depth=max_depth,
            current_depth=current_depth + 1
        )
        
        # If resolved component matched, this component is considered matched
        if resolved_result.result in [MatchResult.DIRECT_MATCH, MatchResult.DECOMPOSED_MATCH]:
            return ComponentMatchResult(
                component=component,
                result=MatchResult.DECOMPOSED_MATCH,
                sub_results=[resolved_result],
                confidence=resolved_result.confidence,
                depth=current_depth
            )
        else:
            return ComponentMatchResult(
                component=component,
                result=MatchResult.NO_MATCH,
                sub_results=[resolved_result],
                confidence=0.0,
                depth=current_depth
            )


@dataclass
class BillOfMaterials:
    """Container for a complete Bill of Materials"""
    name: str
    components: List[Component]
    id: str = field(default_factory=lambda: str(uuid4()))
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary representation"""
        return {
            "id": self.id,
            "name": self.name,
            "components": [c.to_dict() for c in self.components],
            "metadata": self.metadata
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'BillOfMaterials':
        """Create from dictionary representation"""
        components = [Component.from_dict(c) for c in data.get("components", [])]
        
        bom = cls(
            name=data["name"],
            components=components,
            metadata=data.get("metadata", {})
        )
        
        if "id" in data:
            bom.id = data["id"]
            
        return bom


class SupplyTreeGenerator:
    """Generates Supply Trees from BOM match results"""
    
    def generate_supply_tree(self, 
                           bom: BillOfMaterials,
                           match_results: List[ComponentMatchResult]) -> 'SupplyTree':
        """
        Generate a Supply Tree from BOM match results
        
        The Supply Tree structure will reflect the dynamic complexity:
        - Components with direct matches become simple workflow nodes
        - Components matched through decomposition generate connected sub-workflows
        """
        from src.core.models.supply_trees import SupplyTree, Workflow, WorkflowNode, WorkflowConnection
        
        # Create supply tree
        supply_tree = SupplyTree()
        
        # Create primary workflow
        primary_workflow = Workflow(
            name=f"Primary workflow for {bom.name}",
        )
        
        # Process match results
        for result in match_results:
            if result.result == MatchResult.DIRECT_MATCH:
                # Create single node for direct match
                node = self._create_node_for_direct_match(result)
                primary_workflow.add_node(node)
                
            elif result.result == MatchResult.DECOMPOSED_MATCH:
                # Create connected workflows for decomposed match
                node, sub_workflows, connections = self._create_structure_for_decomposed_match(result)
                
                # Add node to primary workflow
                primary_workflow.add_node(node)
                
                # Add sub-workflows and connections to supply tree
                for workflow in sub_workflows:
                    supply_tree.add_workflow(workflow)
                
                for connection in connections:
                    supply_tree.connect_workflows(connection)
        
        # Add primary workflow to supply tree
        supply_tree.add_workflow(primary_workflow)
        
        return supply_tree
    
    def _create_node_for_direct_match(self, result: ComponentMatchResult) -> 'WorkflowNode':
        """Create a workflow node for a direct component match"""
        from src.core.models.supply_trees import WorkflowNode
        
        component = result.component
        capability = result.matched_capability
        
        node = WorkflowNode(
            name=component.name,
            input_requirements={
                "quantity": component.quantity,
                "unit": component.unit,
                **component.requirements
            },
            output_specifications={},
            # Add references to the matched capability
            # ...
        )
        
        return node
    
    def _create_structure_for_decomposed_match(self, 
                                            result: ComponentMatchResult) -> tuple:
        """
        Create connected workflows for a decomposed match
        
        Returns:
            tuple of (primary_node, sub_workflows, connections)
        """
        from src.core.models.supply_trees import Workflow, WorkflowNode, WorkflowConnection
        
        component = result.component
        
        # Create node for the decomposed component
        node = WorkflowNode(
            name=component.name,
            input_requirements={
                "quantity": component.quantity,
                "unit": component.unit,
                **component.requirements
            },
            output_specifications={}
        )
        
        # Create sub-workflows and connections
        sub_workflows = []
        connections = []
        
        # Process each sub-result recursively
        for sub_result in result.sub_results:
            if sub_result.result == MatchResult.DIRECT_MATCH:
                # Create workflow with single node
                workflow = Workflow(
                    name=f"Workflow for {sub_result.component.name}"
                )
                
                sub_node = self._create_node_for_direct_match(sub_result)
                workflow.add_node(sub_node)
                
                sub_workflows.append(workflow)
                
                # Create connection
                connection = WorkflowConnection(
                    source_node=node.id,
                    source_workflow=None,  # Will be set later
                    target_node=sub_node.id,
                    target_workflow=workflow.id,
                    connection_type="decomposition"
                )
                
                connections.append(connection)
                
            elif sub_result.result == MatchResult.DECOMPOSED_MATCH:
                # Recursively create structure for sub-result
                sub_node, more_workflows, more_connections = (
                    self._create_structure_for_decomposed_match(sub_result)
                )
                
                # Create workflow for this level
                workflow = Workflow(
                    name=f"Workflow for {sub_result.component.name}"
                )
                
                workflow.add_node(sub_node)
                sub_workflows.append(workflow)
                
                # Add connection to the sub-workflow
                connection = WorkflowConnection(
                    source_node=node.id,
                    source_workflow=None,  # Will be set later
                    target_node=sub_node.id,
                    target_workflow=workflow.id,
                    connection_type="decomposition"
                )
                
                connections.append(connection)
                
                # Add more sub-workflows and connections
                sub_workflows.extend(more_workflows)
                connections.extend(more_connections)
        
        return node, sub_workflows, connections
```