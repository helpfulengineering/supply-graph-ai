"""
Capability-Centric Heuristic Rules System

This module provides a capability-centric system for managing heuristic matching rules
that match requirements to capabilities. This is fundamentally different from the
previous synonym-based approach.

Key Concepts:
- CapabilityRule: Defines what requirements a capability can satisfy
- CapabilityRuleSet: Collection of capability rules for a domain
- CapabilityRuleManager: Manages rule loading and retrieval
- CapabilityMatcher: Performs capability-to-requirement matching

Architecture:
- Rules are capability-centric: "capability X can satisfy requirements Y, Z, W"
- Supports bidirectional matching: capability->requirement and requirement->capability
- Focuses on actual matching scenarios, not just synonym relationships
"""

from typing import Dict, List, Optional, Any, Set
from dataclasses import dataclass, field
from enum import Enum
import yaml
import json
from pathlib import Path
from datetime import datetime

from ..utils.logging import get_logger

logger = get_logger(__name__)


class RuleType(Enum):
    """Types of capability rules"""
    CAPABILITY_MATCH = "capability_match"  # Capability can satisfy requirements


class RuleDirection(Enum):
    """Direction of rule application"""
    BIDIRECTIONAL = "bidirectional"  # Apply in both directions
    FORWARD = "forward"              # Apply from capability to requirements
    REVERSE = "reverse"              # Apply from requirements to capability


@dataclass
class CapabilityRule:
    """
    Defines what requirements a capability can satisfy.
    
    This is the core data structure for capability-centric matching.
    Each rule specifies: "capability X can satisfy requirements Y, Z, W"
    """
    id: str
    type: RuleType
    capability: str
    satisfies_requirements: List[str]
    direction: RuleDirection = RuleDirection.BIDIRECTIONAL
    confidence: float = 0.9
    domain: str = "general"
    description: str = ""
    source: str = ""
    tags: Set[str] = field(default_factory=set)
    created_at: datetime = field(default_factory=datetime.now)
    updated_at: datetime = field(default_factory=datetime.now)
    
    def __post_init__(self):
        """Validate rule data after initialization"""
        if not self.capability or not self.satisfies_requirements:
            raise ValueError(f"Rule {self.id}: capability and satisfies_requirements cannot be empty")
        if not 0.0 <= self.confidence <= 1.0:
            raise ValueError(f"Rule {self.id}: confidence must be between 0.0 and 1.0")
    
    def can_satisfy_requirement(self, requirement: str) -> bool:
        """
        Check if this capability can satisfy the given requirement.
        
        Args:
            requirement: The requirement to check
            
        Returns:
            True if this capability can satisfy the requirement
        """
        if not requirement:
            return False
        
        requirement_lower = requirement.lower().strip()
        for req in self.satisfies_requirements:
            if requirement_lower == req.lower().strip():
                return True
        
        return False
    
    def requirement_can_be_satisfied_by(self, requirement: str, capability: str) -> bool:
        """
        Check if a requirement can be satisfied by a capability.
        
        Args:
            requirement: The requirement to check
            capability: The capability to check
            
        Returns:
            True if the requirement can be satisfied by the capability
        """
        if not requirement or not capability:
            return False
        
        # Check if the capability matches this rule's capability
        if capability.lower().strip() != self.capability.lower().strip():
            return False
        
        # Check if the requirement is in the satisfies_requirements list
        return self.can_satisfy_requirement(requirement)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert rule to dictionary for serialization"""
        return {
            "id": self.id,
            "type": self.type.value,
            "capability": self.capability,
            "satisfies_requirements": self.satisfies_requirements,
            "direction": self.direction.value,
            "confidence": self.confidence,
            "domain": self.domain,
            "description": self.description,
            "source": self.source,
            "tags": list(self.tags),
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat()
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'CapabilityRule':
        """Create rule from dictionary"""
        return cls(
            id=data["id"],
            type=RuleType(data["type"]),
            capability=data["capability"],
            satisfies_requirements=data["satisfies_requirements"],
            direction=RuleDirection(data.get("direction", "bidirectional")),
            confidence=data.get("confidence", 0.9),
            domain=data.get("domain", "general"),
            description=data.get("description", ""),
            source=data.get("source", ""),
            tags=set(data.get("tags", [])),
            created_at=datetime.fromisoformat(data.get("created_at", datetime.now().isoformat())),
            updated_at=datetime.fromisoformat(data.get("updated_at", datetime.now().isoformat()))
        )


@dataclass
class CapabilityRuleSet:
    """
    Collection of capability rules for a specific domain.
    
    This class stores and manages capability rules for a domain.
    """
    domain: str
    version: str = "1.0.0"
    description: str = ""
    rules: Dict[str, CapabilityRule] = field(default_factory=dict)
    metadata: Dict[str, Any] = field(default_factory=dict)
    created_at: datetime = field(default_factory=datetime.now)
    updated_at: datetime = field(default_factory=datetime.now)
    
    def add_rule(self, rule: CapabilityRule) -> None:
        """Add a rule to this rule set"""
        if rule.domain != self.domain and rule.domain != "general":
            logger.warning(f"Adding rule {rule.id} with domain {rule.domain} to rule set for domain {self.domain}")
        
        self.rules[rule.id] = rule
        self.updated_at = datetime.now()
        logger.debug(f"Added rule {rule.id} to domain {self.domain}")
    
    def remove_rule(self, rule_id: str) -> bool:
        """Remove a rule from this rule set"""
        if rule_id in self.rules:
            del self.rules[rule_id]
            self.updated_at = datetime.now()
            logger.debug(f"Removed rule {rule_id} from domain {self.domain}")
            return True
        return False
    
    def get_rule(self, rule_id: str) -> Optional[CapabilityRule]:
        """Get a specific rule by ID"""
        return self.rules.get(rule_id)
    
    def get_rules_by_type(self, rule_type: RuleType) -> List[CapabilityRule]:
        """Get all rules of a specific type"""
        return [rule for rule in self.rules.values() if rule.type == rule_type]
    
    def get_rules_by_tag(self, tag: str) -> List[CapabilityRule]:
        """Get all rules with a specific tag"""
        return [rule for rule in self.rules.values() if tag in rule.tags]
    
    def get_all_rules(self) -> List[CapabilityRule]:
        """Get all rules in this set"""
        return list(self.rules.values())
    
    def find_rules_for_capability_requirement(self, capability: str, requirement: str) -> List[CapabilityRule]:
        """
        Find all rules where the capability can satisfy the requirement.
        
        Args:
            capability: The capability to check
            requirement: The requirement to check
            
        Returns:
            List of rules where the capability can satisfy the requirement
        """
        matching_rules = []
        for rule in self.rules.values():
            if rule.requirement_can_be_satisfied_by(requirement, capability):
                matching_rules.append(rule)
        return matching_rules
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert rule set to dictionary for serialization"""
        return {
            "domain": self.domain,
            "version": self.version,
            "description": self.description,
            "rules": {rule_id: rule.to_dict() for rule_id, rule in self.rules.items()},
            "metadata": self.metadata,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat()
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'CapabilityRuleSet':
        """Create rule set from dictionary"""
        rule_set = cls(
            domain=data["domain"],
            version=data.get("version", "1.0.0"),
            description=data.get("description", ""),
            metadata=data.get("metadata", {}),
            created_at=datetime.fromisoformat(data.get("created_at", datetime.now().isoformat())),
            updated_at=datetime.fromisoformat(data.get("updated_at", datetime.now().isoformat()))
        )
        
        # Load rules
        for rule_data in data.get("rules", {}).values():
            rule = CapabilityRule.from_dict(rule_data)
            rule_set.add_rule(rule)
        
        return rule_set


class CapabilityRuleManager:
    """
    Manages capability rules across all domains.
    
    This class is responsible for:
    - Loading rules from configuration files
    - Storing and organizing rule sets by domain
    - Providing rule retrieval methods
    - Rule set management (add/remove/update)
    """
    
    def __init__(self, rules_directory: Optional[str] = None):
        """Initialize the rule manager"""
        self.rules_directory = rules_directory or self._get_default_rules_directory()
        self.rule_sets: Dict[str, CapabilityRuleSet] = {}
        self._initialized = False
        
    def _get_default_rules_directory(self) -> str:
        """Get the default rules directory"""
        current_dir = Path(__file__).parent
        rules_dir = current_dir / "rules"
        if rules_dir.exists():
            return str(rules_dir)
        
        config_dir = current_dir.parent / "config" / "rules"
        return str(config_dir)
    
    async def initialize(self) -> None:
        """Initialize the rule manager by loading all rule sets"""
        if self._initialized:
            return
        
        logger.info(f"Initializing CapabilityRuleManager with rules directory: {self.rules_directory}")
        
        try:
            await self._load_all_rule_sets()
            self._initialized = True
            logger.info(f"Loaded {len(self.rule_sets)} rule sets: {list(self.rule_sets.keys())}")
        except Exception as e:
            logger.error(f"Failed to initialize CapabilityRuleManager: {e}", exc_info=True)
            raise
    
    async def _load_all_rule_sets(self) -> None:
        """Load all rule sets from the rules directory"""
        rules_path = Path(self.rules_directory)
        if not rules_path.exists():
            logger.warning(f"Rules directory does not exist: {self.rules_directory}")
            return
        
        rule_files = list(rules_path.glob("*.yaml")) + list(rules_path.glob("*.yml")) + list(rules_path.glob("*.json"))
        
        for rule_file in rule_files:
            try:
                await self._load_rule_set_from_file(rule_file)
            except Exception as e:
                logger.error(f"Failed to load rule set from {rule_file}: {e}", exc_info=True)
                continue
    
    async def _load_rule_set_from_file(self, file_path: Path) -> None:
        """Load a rule set from a file"""
        logger.debug(f"Loading rule set from {file_path}")
        
        with open(file_path, 'r', encoding='utf-8') as f:
            if file_path.suffix.lower() in ['.yaml', '.yml']:
                data = yaml.safe_load(f)
            else:  # .json
                data = json.load(f)
        
        rule_set = CapabilityRuleSet.from_dict(data)
        self.rule_sets[rule_set.domain] = rule_set
        logger.info(f"Loaded rule set for domain '{rule_set.domain}' with {len(rule_set.rules)} rules")
    
    # Rule Set Management Methods
    def get_rule_set(self, domain: str) -> Optional[CapabilityRuleSet]:
        """Get rule set for a specific domain"""
        return self.rule_sets.get(domain)
    
    def get_available_domains(self) -> List[str]:
        """Get list of available domains"""
        return list(self.rule_sets.keys())
    
    def add_rule_set(self, rule_set: CapabilityRuleSet) -> None:
        """Add a new rule set"""
        self.rule_sets[rule_set.domain] = rule_set
        logger.info(f"Added rule set for domain '{rule_set.domain}' with {len(rule_set.rules)} rules")
    
    def remove_rule_set(self, domain: str) -> bool:
        """Remove a rule set for a domain"""
        if domain in self.rule_sets:
            del self.rule_sets[domain]
            logger.info(f"Removed rule set for domain '{domain}'")
            return True
        return False
    
    # Rule Retrieval Methods
    def get_rule(self, domain: str, rule_id: str) -> Optional[CapabilityRule]:
        """Get a specific rule by domain and ID"""
        rule_set = self.get_rule_set(domain)
        if not rule_set:
            return None
        return rule_set.get_rule(rule_id)
    
    def get_rules_by_type(self, domain: str, rule_type: RuleType) -> List[CapabilityRule]:
        """Get all rules of a specific type in a domain"""
        rule_set = self.get_rule_set(domain)
        if not rule_set:
            return []
        return rule_set.get_rules_by_type(rule_type)
    
    def get_rules_by_tag(self, domain: str, tag: str) -> List[CapabilityRule]:
        """Get all rules with a specific tag in a domain"""
        rule_set = self.get_rule_set(domain)
        if not rule_set:
            return []
        return rule_set.get_rules_by_tag(tag)
    
    def get_all_rules_for_domain(self, domain: str) -> List[CapabilityRule]:
        """Get all rules for a specific domain"""
        rule_set = self.get_rule_set(domain)
        if not rule_set:
            return []
        return rule_set.get_all_rules()
    
    def find_rules_for_capability_requirement(self, domain: str, capability: str, requirement: str) -> List[CapabilityRule]:
        """Find rules where a capability can satisfy a requirement"""
        rule_set = self.get_rule_set(domain)
        if not rule_set:
            return []
        return rule_set.find_rules_for_capability_requirement(capability, requirement)
    
    # Statistics and Management
    def get_rule_statistics(self) -> Dict[str, Any]:
        """Get statistics about loaded rules"""
        total_rules = sum(len(rule_set.rules) for rule_set in self.rule_sets.values())
        rule_types = {}
        
        for rule_set in self.rule_sets.values():
            for rule in rule_set.rules.values():
                rule_type = rule.type.value
                rule_types[rule_type] = rule_types.get(rule_type, 0) + 1
        
        return {
            "total_domains": len(self.rule_sets),
            "total_rules": total_rules,
            "domains": list(self.rule_sets.keys()),
            "rule_types": rule_types,
            "rules_directory": self.rules_directory
        }
    
    async def reload_rules(self) -> None:
        """Reload all rules from files"""
        logger.info("Reloading all capability rules")
        self.rule_sets.clear()
        self._initialized = False
        await self.initialize()


@dataclass
class CapabilityMatchResult:
    """
    Result of a capability matching operation.
    
    This tracks matching events within the system, capturing the full context
    of what was matched and how the matching was performed.
    """
    # The actual requirement and capability objects (or their key fields)
    requirement_object: Dict[str, Any]
    capability_object: Dict[str, Any]
    
    # The specific fields that were matched
    requirement_field: str  # e.g., "process_name"
    capability_field: str   # e.g., "process_name"
    
    # The extracted values that were compared
    requirement_value: str  # e.g., "milling"
    capability_value: str   # e.g., "cnc machining"
    
    # Matching results
    matched: bool
    confidence: float
    rule_used: Optional[CapabilityRule] = None
    match_type: str = "capability_match"
    domain: str = "general"
    transformation_details: List[str] = field(default_factory=list)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization"""
        return {
            "requirement_object": self.requirement_object,
            "capability_object": self.capability_object,
            "requirement_field": self.requirement_field,
            "capability_field": self.capability_field,
            "requirement_value": self.requirement_value,
            "capability_value": self.capability_value,
            "matched": self.matched,
            "confidence": self.confidence,
            "rule_used": self.rule_used.to_dict() if self.rule_used else None,
            "match_type": self.match_type,
            "domain": self.domain,
            "transformation_details": self.transformation_details
        }


class CapabilityMatcher:
    """
    Handles capability-centric matching logic.
    
    This class is responsible for:
    - Checking if capabilities can satisfy requirements
    - Checking if requirements can be satisfied by capabilities
    - Matching lists of requirements to lists of capabilities
    - Providing detailed match results with metadata
    """
    
    def __init__(self, rule_manager: CapabilityRuleManager):
        """Initialize the matcher with a rule manager"""
        self.rule_manager = rule_manager
        self._initialized = False
    
    async def initialize(self) -> None:
        """Initialize the matcher"""
        if self._initialized:
            return
        
        # Ensure rule manager is initialized
        await self.rule_manager.initialize()
        self._initialized = True
        logger.info("CapabilityMatcher initialized")
    
    async def ensure_initialized(self) -> None:
        """Ensure matcher is initialized"""
        if not self._initialized:
            await self.initialize()
    
    async def capability_can_satisfy_requirement(self, capability: str, requirement: str, domain: str) -> bool:
        """
        Check if a capability can satisfy a requirement.
        
        Args:
            capability: The capability to check
            requirement: The requirement to check
            domain: The domain for rule selection
            
        Returns:
            True if the capability can satisfy the requirement
        """
        await self.ensure_initialized()
        
        # Find rules where this capability can satisfy this requirement
        rules = self.rule_manager.find_rules_for_capability_requirement(domain, capability, requirement)
        return len(rules) > 0
    
    async def requirement_can_be_satisfied_by(self, requirement: str, capability: str, domain: str) -> bool:
        """
        Check if a requirement can be satisfied by a capability.
        
        Args:
            requirement: The requirement to check
            capability: The capability to check
            domain: The domain for rule selection
            
        Returns:
            True if the requirement can be satisfied by the capability
        """
        await self.ensure_initialized()
        
        # This is the same as capability_can_satisfy_requirement, just with different parameter order
        return await self.capability_can_satisfy_requirement(capability, requirement, domain)
    
    async def match_requirements_to_capabilities(
        self, 
        requirements: List[Dict[str, Any]], 
        capabilities: List[Dict[str, Any]], 
        domain: str = "manufacturing",
        requirement_field: str = "process_name",
        capability_field: str = "process_name"
    ) -> List[CapabilityMatchResult]:
        """
        Match a list of requirement objects to a list of capability objects.
        
        Args:
            requirements: List of requirement dictionaries
            capabilities: List of capability dictionaries
            domain: The domain for rule selection
            requirement_field: The field to extract from requirements for matching
            capability_field: The field to extract from capabilities for matching
            
        Returns:
            List of CapabilityMatchResult objects
        """
        await self.ensure_initialized()
        
        results = []
        
        for requirement_obj in requirements:
            for capability_obj in capabilities:
                # Extract the values to compare
                requirement_value = requirement_obj.get(requirement_field, "").lower().strip()
                capability_value = capability_obj.get(capability_field, "").lower().strip()
                
                # Skip empty values
                if not requirement_value or not capability_value:
                    results.append(CapabilityMatchResult(
                        requirement_object=requirement_obj,
                        capability_object=capability_obj,
                        requirement_field=requirement_field,
                        capability_field=capability_field,
                        requirement_value=requirement_value,
                        capability_value=capability_value,
                        matched=False,
                        confidence=0.0,
                        domain=domain
                    ))
                    continue
                
                # Find matching rules
                rules = self.rule_manager.find_rules_for_capability_requirement(domain, capability_value, requirement_value)
                
                if rules:
                    # Use the rule with highest confidence
                    best_rule = max(rules, key=lambda r: r.confidence)
                    
                    results.append(CapabilityMatchResult(
                        requirement_object=requirement_obj,
                        capability_object=capability_obj,
                        requirement_field=requirement_field,
                        capability_field=capability_field,
                        requirement_value=requirement_value,
                        capability_value=capability_value,
                        matched=True,
                        confidence=best_rule.confidence,
                        rule_used=best_rule,
                        domain=domain,
                        transformation_details=[f"Capability '{capability_value}' can satisfy requirement '{requirement_value}'"]
                    ))
                    
                    logger.debug(
                        f"Capability match found: '{capability_value}' satisfies '{requirement_value}' "
                        f"(confidence: {best_rule.confidence}, rule: {best_rule.id})"
                    )
                else:
                    results.append(CapabilityMatchResult(
                        requirement_object=requirement_obj,
                        capability_object=capability_obj,
                        requirement_field=requirement_field,
                        capability_field=capability_field,
                        requirement_value=requirement_value,
                        capability_value=capability_value,
                        matched=False,
                        confidence=0.0,
                        domain=domain
                    ))
        
        return results


# Global instances
_rule_manager: Optional[CapabilityRuleManager] = None
_capability_matcher: Optional[CapabilityMatcher] = None


async def get_rule_manager() -> CapabilityRuleManager:
    """Get the global rule manager instance"""
    global _rule_manager
    if _rule_manager is None:
        _rule_manager = CapabilityRuleManager()
        await _rule_manager.initialize()
    return _rule_manager


async def get_capability_matcher() -> CapabilityMatcher:
    """Get the global capability matcher instance"""
    global _capability_matcher
    if _capability_matcher is None:
        rule_manager = await get_rule_manager()
        _capability_matcher = CapabilityMatcher(rule_manager)
        await _capability_matcher.initialize()
    return _capability_matcher


def create_rule_manager(rules_directory: Optional[str] = None) -> CapabilityRuleManager:
    """Create a new rule manager instance"""
    return CapabilityRuleManager(rules_directory)


def create_capability_matcher(rule_manager: CapabilityRuleManager) -> CapabilityMatcher:
    """Create a new capability matcher instance"""
    return CapabilityMatcher(rule_manager)
