from typing import Dict, Any, List
from dataclasses import dataclass
import logging
from ..registry.domain_registry import DomainRegistry
from ..models.supply_trees import Workflow
from ..api.models.supply_tree.response import SupplyTreeResponse


logger = logging.getLogger(__name__)

@dataclass
class DomainDetectionResult:
    """Results of domain detection with confidence"""
    domain: str
    confidence: float
    method: str  # "explicit", "type_mapping", "content_analysis", "fallback"
    alternative_domains: Dict[str, float] = None
    
    def __post_init__(self):
        if self.alternative_domains is None:
            self.alternative_domains = {}
    
    def is_confident(self, threshold: float = 0.8) -> bool:
        """Check if detection meets confidence threshold"""
        return self.confidence >= threshold
    
    def get_alternatives(self, min_score: float = 0.4) -> List[str]:
        """Get alternative domains above minimum confidence score"""
        return [
            domain for domain, score in self.alternative_domains.items() 
            if score >= min_score
        ]

class DomainDetector:
    """Enhanced domain detection and validation system"""
    
    # Type-based domain mapping
    TYPE_DOMAIN_MAP = {
        ("okh", "okw"): "manufacturing",
        ("recipe", "kitchen"): "cooking",
        ("okh", "manufacturing_facility"): "manufacturing",
        ("recipe", "cooking_facility"): "cooking"
    }
    
    # Content-based domain detection keywords
    DOMAIN_KEYWORDS = {
        "manufacturing": [
            "machining", "tolerance", "material", "equipment", 
            "hardware", "manufacturing", "fabrication", "cnc",
            "3d printing", "additive", "subtractive", "tooling"
        ],
        "cooking": [
            "recipe", "ingredient", "kitchen", "cooking", 
            "baking", "food", "meal", "preparation", "chef",
            "cuisine", "flavor", "seasoning"
        ]
    }
    
    @classmethod
    def detect_domain(cls, requirements: Any, capabilities: Any) -> DomainDetectionResult:
        """Detect domain from input data with confidence scoring"""
        
        # Method 1: Explicit domain information
        if hasattr(requirements, 'domain') and hasattr(capabilities, 'domain'):
            if requirements.domain and capabilities.domain:
                if requirements.domain == capabilities.domain:
                    return DomainDetectionResult(
                        domain=requirements.domain,
                        confidence=1.0,
                        method="explicit"
                    )
                else:
                    raise ValueError(f"Domain mismatch: requirements={requirements.domain}, capabilities={capabilities.domain}")
        
        # Method 2: Type-based detection
        if hasattr(requirements, 'type') and hasattr(capabilities, 'type'):
            key = (requirements.type, capabilities.type)
            if key in cls.TYPE_DOMAIN_MAP:
                return DomainDetectionResult(
                    domain=cls.TYPE_DOMAIN_MAP[key],
                    confidence=0.9,
                    method="type_mapping"
                )
        
        # Method 3: Content analysis
        content_result = cls._detect_from_content(requirements, capabilities)
        if content_result.confidence > 0.0:  # Accept any content analysis result
            return content_result
        
        # Method 4: Registry-based fallback
        available_domains = DomainRegistry.list_domains()
        if len(available_domains) == 1:
            return DomainDetectionResult(
                domain=available_domains[0],
                confidence=0.5,
                method="fallback"
            )
        
        raise ValueError(f"Could not detect domain from inputs. Available domains: {available_domains}")
    
    @classmethod
    def _detect_from_content(cls, requirements: Any, capabilities: Any) -> DomainDetectionResult:
        """Detect domain from content analysis"""
        domain_scores = {}
        
        # Analyze requirements content
        req_text = cls._extract_text_content(requirements)
        cap_text = cls._extract_text_content(capabilities)
        combined_text = f"{req_text} {cap_text}".lower()
        
        # Score each domain based on keyword presence
        for domain, keywords in cls.DOMAIN_KEYWORDS.items():
            score = 0
            for keyword in keywords:
                if keyword.lower() in combined_text:
                    score += 1
            # Normalize by keyword count, but ensure minimum score if any keywords found
            normalized_score = score / len(keywords) if keywords else 0
            if score > 0 and normalized_score < 0.1:
                normalized_score = 0.1  # Minimum confidence if any keywords found
            domain_scores[domain] = normalized_score
        
        if not domain_scores:
            return DomainDetectionResult(
                domain="unknown",
                confidence=0.0,
                method="content_analysis"
            )
        
        # Find best match
        best_domain = max(domain_scores.items(), key=lambda x: x[1])
        
        return DomainDetectionResult(
            domain=best_domain[0],
            confidence=best_domain[1],
            method="content_analysis",
            alternative_domains={k: v for k, v in domain_scores.items() if k != best_domain[0]}
        )
    
    @classmethod
    def _extract_text_content(cls, obj: Any) -> str:
        """Extract text content from an object for analysis"""
        if hasattr(obj, 'content') and isinstance(obj.content, dict):
            return str(obj.content)
        elif hasattr(obj, 'to_dict'):
            return str(obj.to_dict())
        elif isinstance(obj, dict):
            return str(obj)
        else:
            return str(obj)
    
    @classmethod
    def validate_domain_consistency(cls, requirements: Any, capabilities: Any, detected_domain: str) -> bool:
        """Ensure domain consistency between inputs"""
        # Check explicit domain attributes
        if hasattr(requirements, 'domain') and requirements.domain:
            if requirements.domain != detected_domain:
                raise ValueError(f"Requirements domain {requirements.domain} doesn't match detected domain {detected_domain}")
                
        if hasattr(capabilities, 'domain') and capabilities.domain:
            if capabilities.domain != detected_domain:
                raise ValueError(f"Capabilities domain {capabilities.domain} doesn't match detected domain {detected_domain}")
        
        # Validate domain exists in registry
        if detected_domain not in DomainRegistry.list_domains():
            raise ValueError(f"Domain '{detected_domain}' is not registered")
        
        return True
    
    @classmethod
    def detect_and_validate_domain(cls, requirements: Any, capabilities: Any) -> str:
        """Detect and validate domain consistency - returns domain name"""
        detection_result = cls.detect_domain(requirements, capabilities)
        cls.validate_domain_consistency(requirements, capabilities, detection_result.domain)
        return detection_result.domain
    
    @classmethod
    def get_domain_services(cls, domain: str):
        """Get all domain services"""
        return DomainRegistry.get_domain_services(domain)
    
    @classmethod
    def get_domain_extractor(cls, domain: str):
        """Get domain-specific extractor component"""
        return DomainRegistry.get_extractor(domain)
    
    @classmethod
    def get_domain_matcher(cls, domain: str):
        """Get domain-specific matcher component"""
        return DomainRegistry.get_matcher(domain)
    
    @classmethod
    def get_domain_validator(cls, domain: str):
        """Get domain-specific validator component"""
        return DomainRegistry.get_validator(domain)
    
    @classmethod
    def get_domain_orchestrator(cls, domain: str):
        """Get domain-specific orchestrator if available"""
        return DomainRegistry.get_orchestrator(domain)

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
