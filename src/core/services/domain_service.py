from ..registry.domain_registry import DomainRegistry


class DomainDetector:
    """Detects and validates domains from input data"""
    
    @staticmethod
    def detect_domain(requirements, capabilities):
        """Detect domain from input types"""
        domain_map = {
            ("okh", "okw"): "manufacturing",
            ("recipe", "kitchen"): "cooking"
        }
        
        key = (requirements.type, capabilities.type)
        if key in domain_map:
            return domain_map[key]
        
        # If explicit domain is provided, use it
        if requirements.domain and requirements.domain == capabilities.domain:
            return requirements.domain
            
        raise ValueError(f"Incompatible input types: {requirements.type} and {capabilities.type}")
    
    @staticmethod
    def validate_domain_consistency(requirements, capabilities, detected_domain):
        """Ensure domain consistency between inputs"""
        if requirements.domain and requirements.domain != detected_domain:
            raise ValueError(f"Requirements domain {requirements.domain} doesn't match detected domain {detected_domain}")
            
        if capabilities.domain and capabilities.domain != detected_domain:
            raise ValueError(f"Capabilities domain {capabilities.domain} doesn't match detected domain {detected_domain}")
        
        return True

    def detect_and_validate_domain(requirements, capabilities):
        """Detect and validate domain consistency"""
        detector = DomainDetector()
        domain = detector.detect_domain(requirements, capabilities)
        detector.validate_domain_consistency(requirements, capabilities, domain)
        return domain

    def get_domain_extractor(domain):
        """Get domain-specific extractor component"""
        return DomainRegistry.get_extractor(domain)

    def get_domain_matcher(domain):
        """Get domain-specific matcher component"""
        return DomainRegistry.get_matcher(domain)

    def get_domain_validator(domain):
        """Get domain-specific validator component"""
        return DomainRegistry.get_validator(domain)

    def convert_supply_tree_to_response(supply_tree, domain, validation_result):
        """Convert internal SupplyTree to API response format"""
        # Extract workflows from supply tree
        workflows = {}
        for workflow_id, workflow in supply_tree.workflows.items():
            # Convert nodes to API format
            nodes = {}
            for node in workflow.graph.nodes():
                node_data = workflow.graph.nodes[node]
                process_node = ProcessNode(
                    id=node,
                    name=node_data.get('name', f"Node-{node}"),
                    inputs=node_data.get('input_requirements', {}).keys(),
                    outputs=node_data.get('output_specifications', {}).keys(),
                    requirements={uri.identifier: uri.path for uri in node_data.get('okh_refs', [])},
                    capabilities={uri.identifier: uri.path for uri in node_data.get('okw_refs', [])}
                )
                nodes[str(node)] = process_node
            
            # Convert edges to API format
            edges = []
            for source, target in workflow.graph.edges():
                edges.append({"source": source, "target": target})
            
            # Create workflow
            workflows[str(workflow_id)] = Workflow(
                id=workflow_id,
                name=workflow.name,
                nodes=nodes,
                edges=edges
            )
        
        # Calculate confidence score (simplified example)
        confidence = validation_result.get('confidence', 0.0) if isinstance(validation_result, dict) else 0.8
        
        # Create response
        response = SupplyTreeResponse(
            id=supply_tree.id,
            domain=domain,
            workflows=workflows,
            confidence=confidence,
            validation_status=validation_result.get('valid', False) if isinstance(validation_result, dict) else True,
            metadata={
                "creation_time": supply_tree.creation_time.isoformat(),
                "snapshot_count": len(supply_tree.snapshots)
            }
        )
        
        return response
