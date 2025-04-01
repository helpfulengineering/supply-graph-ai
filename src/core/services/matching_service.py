from ..api.models.match.request import RequirementsInput, CapabilitiesInput
from ..api.models.match.response import SupplyTreeResponse, Workflow, ProcessNode
from ..registry.domain_registry import DomainRegistry
from .domain_service import DomainDetector

class MatchingService:
    """Service for matching requirements to capabilities"""
    
    @staticmethod
    async def match(requirements: RequirementsInput, capabilities: CapabilitiesInput) -> SupplyTreeResponse:
        """Match requirements to capabilities and generate a SupplyTree"""
        
        # 1. Detect and validate domain
        domain = DomainDetector.detect_domain(requirements, capabilities)
        DomainDetector.validate_domain_consistency(requirements, capabilities, domain)
        
        # 2. Get domain components
        extractor = DomainRegistry.get_extractor(domain)
        matcher = DomainRegistry.get_matcher(domain)
        validator = DomainRegistry.get_validator(domain)
        
        # 3. Extract data
        normalized_req = extractor.extract_requirements(requirements.content)
        normalized_cap = extractor.extract_capabilities(capabilities.content)
        
        # 4. Generate supply tree
        supply_tree = matcher.generate_supply_tree(normalized_req, normalized_cap)
        
        # 5. Validate
        validation_result = validator.validate(supply_tree)
        
        # 6. Convert to response
        workflows = {}
        for wf_id, workflow in supply_tree.workflows.items():
            # Convert nodes
            nodes = {}
            for node_id in workflow.graph.nodes():
                node_data = workflow.graph.nodes[node_id].get('data', {})
                nodes[str(node_id)] = ProcessNode(
                    id=node_id,
                    name=node_data.get('name', f"Node-{node_id}"),
                    inputs=list(node_data.get('input_requirements', {}).keys()),
                    outputs=list(node_data.get('output_specifications', {}).keys()),
                    requirements=node_data.get('input_requirements', {}),
                    capabilities=node_data.get('output_specifications', {})
                )
            
            # Convert edges
            edges = []
            for source, target in workflow.graph.edges():
                edges.append({"source": source, "target": target})
            
            workflows[str(wf_id)] = Workflow(
                id=wf_id,
                name=workflow.name,
                nodes=nodes,
                edges=edges
            )
        
        # Create response
        response = SupplyTreeResponse(
            id=supply_tree.id,
            domain=domain,
            workflows=workflows,
            confidence=validation_result.get('confidence', 0.0),
            validation_status=validation_result.get('valid', False),
            metadata={
                "creation_time": supply_tree.creation_time.isoformat()
            }
        )
        
        return response