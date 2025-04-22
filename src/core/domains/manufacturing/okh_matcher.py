from typing import List, Dict, Any, Optional
from uuid import uuid4

from src.core.models.base.base_types import BaseMatcher, Requirement, Capability, MatchResult, ResourceType, Substitution
from src.core.models.supply_trees import SupplyTree, Workflow, WorkflowNode, ResourceURI, WorkflowConnection
from src.core.models.okh import OKHManifest, ProcessRequirement

class OKHRequirement(Requirement):
    """OKH-specific requirement implementation"""
    
    def __init__(self, process_req: ProcessRequirement):
        super().__init__(
            name=process_req.process_name,
            type="process",
            parameters=process_req.parameters,
            constraints=process_req.validation_criteria
        )
        self.process_requirement = process_req
        self.required_tools = process_req.required_tools

class OKHMatcher(BaseMatcher):
    """Implementation of BaseMatcher for OKH data"""
    
    def match(self, 
             requirements: List[Requirement],
             capabilities: List[Capability]) -> MatchResult:
        """Match OKH requirements against capabilities"""
        matched_capabilities = {}
        missing_requirements = []
        substitutions = []
        
        for req in requirements:
            # Skip non-OKH requirements
            if not isinstance(req, OKHRequirement):
                continue
                
            # Find matching capability
            matched = False
            for capability in capabilities:
                # Check if capability can satisfy requirement
                if self._can_satisfy(req, capability):
                    matched_capabilities[req] = capability
                    matched = True
                    break
                    
                # Check for possible substitution
                elif self._can_substitute(req, capability):
                    substitution = self._create_substitution(req, capability)
                    substitutions.append(substitution)
            
            # Add to missing if not matched
            if not matched:
                missing_requirements.append(req)
        
        # Calculate overall confidence
        confidence = self._calculate_confidence(
            matched_capabilities, 
            missing_requirements,
            substitutions,
            len(requirements)
        )
        
        return MatchResult(
            confidence=confidence,
            matched_capabilities=matched_capabilities,
            missing_requirements=missing_requirements,
            substitutions=substitutions
        )
    
    def generate_supply_tree(self, 
                           okh_manifest: OKHManifest,
                           capabilities: List[Capability]) -> SupplyTree:
        """Generate a SupplyTree from OKH manifest and capabilities"""
        # Create new supply tree
        supply_tree = SupplyTree()
        
        # Create primary workflow
        primary_workflow = Workflow(
            name=f"Primary workflow for {okh_manifest.title}"
        )
        
        # Extract process requirements and convert to OKHRequirements
        process_reqs = okh_manifest.extract_requirements()
        requirements = [OKHRequirement(req) for req in process_reqs]
        
        # Match requirements to capabilities
        match_result = self.match(requirements, capabilities)
        
        # Create workflow nodes from matched requirements
        previous_node = None
        for i, req in enumerate(requirements):
            # Skip if requirement is missing and has no substitutions
            if req in match_result.missing_requirements and not any(
                sub.original == req for sub in match_result.substitutions
            ):
                continue
                
            # Get matching capability or substitution
            capability = None
            substitution = None
            
            if req in match_result.matched_capabilities:
                capability = match_result.matched_capabilities[req]
            else:
                # Find substitution if available
                for sub in match_result.substitutions:
                    if sub.original == req:
                        substitution = sub
                        capability = sub.substitute
                        break
            
            if not capability:
                continue
                
            # Create node for this requirement
            node = WorkflowNode(
                name=f"Step {i+1}: {req.name}",
                okh_refs=[ResourceURI(
                    resource_type=ResourceType.OKH,
                    identifier=str(okh_manifest.id),
                    path=["process_requirements", str(i)]
                )],
                okw_refs=[ResourceURI(
                    resource_type=ResourceType.OKW,
                    identifier=str(getattr(capability, 'id', uuid4())),
                    path=["capabilities", capability.type]
                )] if capability else [],
                input_requirements=req.parameters,
                output_specifications=req.constraints
            )
            
            # Add substitution information if applicable
            if substitution:
                node.metadata["substitution"] = {
                    "original": req.name,
                    "substitute": capability.name,
                    "confidence": substitution.confidence,
                    "notes": substitution.notes
                }
            
            # Add node to workflow
            primary_workflow.add_node(node)
            if previous_node:
                primary_workflow.graph.add_edge(previous_node.id, node.id)
                
            previous_node = node
        
        # Add workflow to supply tree
        if primary_workflow.graph.number_of_nodes() > 0:
            supply_tree.add_workflow(primary_workflow)
        
        # Add part-specific workflows if needed
        self._add_part_workflows(supply_tree, okh_manifest, capabilities, primary_workflow)
        
        # Add snapshots of relevant data
        supply_tree.add_snapshot(f"okh://{okh_manifest.id}", okh_manifest.to_dict())
        
        return supply_tree
    
    def _add_part_workflows(self, 
                         supply_tree: SupplyTree, 
                         okh_manifest: OKHManifest,
                         capabilities: List[Capability],
                         primary_workflow: Workflow) -> None:
        """Add part-specific workflows to the supply tree"""
        # Only add if primary workflow exists
        if primary_workflow.id not in supply_tree.workflows:
            return
            
        # Create workflows for each part
        for part in okh_manifest.parts:
            if not part.tsdc:
                continue
                
            part_workflow = Workflow(
                name=f"Workflow for {part.name}"
            )
            
            # Create nodes for each TSDC
            previous_node = None
            for i, tsdc in enumerate(part.tsdc):
                # Create process requirement for this TSDC
                params = {}
                if hasattr(part, 'manufacturing_params'):
                    params = part.manufacturing_params.copy()
                params['material'] = part.material
                
                proc_req = ProcessRequirement(
                    process_name=tsdc,
                    parameters=params,
                    validation_criteria={},
                    required_tools=[]
                )
                
                # Create requirement and find capability
                requirement = OKHRequirement(proc_req)
                capability = self._find_capability(requirement, capabilities)
                
                if not capability:
                    continue
                    
                # Create node for this TSDC
                node = WorkflowNode(
                    name=f"{part.name} - {tsdc}",
                    okh_refs=[ResourceURI(
                        resource_type=ResourceType.OKH,
                        identifier=str(okh_manifest.id),
                        path=["parts", str(part.id), "tsdc", str(i)]
                    )],
                    okw_refs=[ResourceURI(
                        resource_type=ResourceType.OKW,
                        identifier=str(getattr(capability, 'id', uuid4())),
                        path=["capabilities", capability.type]
                    )],
                    input_requirements=requirement.parameters,
                    output_specifications=requirement.constraints
                )
                
                # Add node to workflow
                part_workflow.add_node(node)
                if previous_node:
                    part_workflow.graph.add_edge(previous_node.id, node.id)
                    
                previous_node = node
            
            # Only add workflow if it has nodes
            if part_workflow.graph.number_of_nodes() > 0:
                supply_tree.add_workflow(part_workflow)
                
                # Connect to primary workflow
                if primary_workflow and primary_workflow.exit_points:
                    last_node = next(iter(primary_workflow.exit_points))
                    first_node = next(iter(part_workflow.entry_points)) if part_workflow.entry_points else None
                    
                    if last_node and first_node:
                        connection = WorkflowConnection(
                            source_workflow=primary_workflow.id,
                            source_node=last_node,
                            target_workflow=part_workflow.id,
                            target_node=first_node,
                            connection_type="component"
                        )
                        supply_tree.connect_workflows(connection)
    
    def _find_capability(self, 
                      requirement: OKHRequirement, 
                      capabilities: List[Capability]) -> Optional[Capability]:
        """Find a capability that can satisfy a requirement"""
        for capability in capabilities:
            if self._can_satisfy(requirement, capability):
                return capability
        return None
    
    def _can_satisfy(self, 
                   requirement: OKHRequirement, 
                   capability: Capability) -> bool:
        """Check if a capability can satisfy a requirement"""
        # Check if process name matches capability type
        if requirement.name == capability.type:
            return True
            
        # Check if capability parameters include this process
        if 'processes' in capability.parameters and requirement.name in capability.parameters['processes']:
            return True
            
        return False
    
    def _can_substitute(self, 
                      requirement: OKHRequirement, 
                      capability: Capability) -> bool:
        """Check if a capability can be a substitute for a requirement"""
        # Check if capability is a known substitute
        if 'substitutes_for' in capability.parameters and requirement.name in capability.parameters['substitutes_for']:
            return True
            
        # TODO: Add more sophisticated substitution rules
        return False
    
    def _create_substitution(self, 
                          requirement: OKHRequirement,
                          capability: Capability) -> Any:
        """Create a substitution record"""        
        confidence = 0.7  # Default confidence for substitutions
        
        # Adjust confidence based on substitute metadata
        if 'substitutes_for' in capability.parameters and requirement.name in capability.parameters['substitutes_for']:
            if isinstance(capability.parameters['substitutes_for'], dict) and 'confidence' in capability.parameters['substitutes_for'][requirement.name]:
                confidence = capability.parameters['substitutes_for'][requirement.name]['confidence']
        
        return Substitution(
            original=requirement,
            substitute=capability,
            confidence=confidence,
            constraints=capability.limitations,
            notes=f"Substitute {capability.name} for {requirement.name}"
        )
    
    def _calculate_confidence(self, 
                           matched: Dict[Requirement, Capability],
                           missing: List[Requirement],
                           substitutions: List[Any],
                           total_count: int) -> float:
        """Calculate overall match confidence"""
        if total_count == 0:
            return 0.0
            
        # Weight exact matches higher than substitutions
        exact_matches = len(matched)
        sub_matches = len(substitutions)
        
        # Calculate weighted match ratio
        weighted_matches = exact_matches + 0.7 * sub_matches
        
        # Calculate base confidence from match ratio
        base_confidence = weighted_matches / total_count
        
        # Adjust confidence based on missing critical requirements
        if missing:
            # Check if any missing requirements are critical
            critical_missing = any(req.is_required for req in missing)
            if critical_missing:
                # Reduce confidence significantly for missing critical requirements
                base_confidence *= 0.5
        
        return base_confidence