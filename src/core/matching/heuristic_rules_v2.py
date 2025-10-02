"""
Heuristic Rules System - Redesigned with Clear Separation of Concerns

This module provides a modular, extensible system for managing heuristic matching rules
with clear separation between data storage, rule management, and matching logic.

Architecture:
- HeuristicRule: Pure data container for rule definitions
- HeuristicRuleSet: Collection of rules for a domain (data only)
- HeuristicRuleManager: Rule loading, storage, and retrieval (no matching logic)
- HeuristicMatcher: Matching logic and confidence calculation
"""

from typing import Dict, List, Optional, Any, Set
from dataclasses import dataclass, field
from enum import Enum
import yaml
import json
from pathlib import Path
import logging
from datetime import datetime

from ..utils.logging import get_logger

logger = get_logger(__name__)


class RuleType(Enum):
    """Types of heuristic rules"""
    ABBREVIATION = "abbreviation"
    SYNONYM = "synonym"
    EQUIVALENT = "equivalent"
    SUBSTITUTION = "substitution"
    NORMALIZATION = "normalization"


class RuleDirection(Enum):
    """Direction of rule application"""
    BIDIRECTIONAL = "bidirectional"  # Apply in both directions
    FORWARD = "forward"              # Apply from key to values
    REVERSE = "reverse"              # Apply from values to key


@dataclass
class HeuristicRule:
    """
    Pure data container for a heuristic matching rule.
    
    This class only stores rule data and provides basic validation.
    It does NOT contain matching logic - that's handled by HeuristicMatcher.
    """
    id: str
    type: RuleType
    key: str
    values: List[str]
    direction: RuleDirection = RuleDirection.BIDIRECTIONAL
    base_confidence: float = 0.9  # Base confidence for this rule type
    domain: str = "general"
    description: str = ""
    source: str = ""
    tags: Set[str] = field(default_factory=set)
    created_at: datetime = field(default_factory=datetime.now)
    updated_at: datetime = field(default_factory=datetime.now)
    
    def __post_init__(self):
        """Validate rule data after initialization"""
        if not self.key or not self.values:
            raise ValueError(f"Rule {self.id}: key and values cannot be empty")
        if not 0.0 <= self.base_confidence <= 1.0:
            raise ValueError(f"Rule {self.id}: base_confidence must be between 0.0 and 1.0")
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert rule to dictionary for serialization"""
        return {
            "id": self.id,
            "type": self.type.value,
            "direction": self.direction.value,
            "key": self.key,
            "values": self.values,
            "base_confidence": self.base_confidence,
            "domain": self.domain,
            "description": self.description,
            "source": self.source,
            "tags": list(self.tags),
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat()
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'HeuristicRule':
        """Create rule from dictionary"""
        return cls(
            id=data["id"],
            type=RuleType(data["type"]),
            direction=RuleDirection(data.get("direction", "bidirectional")),
            key=data["key"],
            values=data["values"],
            base_confidence=data.get("base_confidence", 0.9),
            domain=data.get("domain", "general"),
            description=data.get("description", ""),
            source=data.get("source", ""),
            tags=set(data.get("tags", [])),
            created_at=datetime.fromisoformat(data.get("created_at", datetime.now().isoformat())),
            updated_at=datetime.fromisoformat(data.get("updated_at", datetime.now().isoformat()))
        )


@dataclass
class HeuristicRuleSet:
    """
    Pure data container for a collection of rules for a specific domain.
    
    This class only stores and manages rule collections.
    It does NOT contain matching logic - that's handled by HeuristicMatcher.
    """
    domain: str
    version: str = "1.0.0"
    description: str = ""
    rules: Dict[str, HeuristicRule] = field(default_factory=dict)
    metadata: Dict[str, Any] = field(default_factory=dict)
    created_at: datetime = field(default_factory=datetime.now)
    updated_at: datetime = field(default_factory=datetime.now)
    
    def add_rule(self, rule: HeuristicRule) -> None:
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
    
    def get_rule(self, rule_id: str) -> Optional[HeuristicRule]:
        """Get a specific rule by ID"""
        return self.rules.get(rule_id)
    
    def get_rules_by_type(self, rule_type: RuleType) -> List[HeuristicRule]:
        """Get all rules of a specific type"""
        return [rule for rule in self.rules.values() if rule.type == rule_type]
    
    def get_rules_by_tag(self, tag: str) -> List[HeuristicRule]:
        """Get all rules with a specific tag"""
        return [rule for rule in self.rules.values() if tag in rule.tags]
    
    def get_all_rules(self) -> List[HeuristicRule]:
        """Get all rules in this set"""
        return list(self.rules.values())
    
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
    def from_dict(cls, data: Dict[str, Any]) -> 'HeuristicRuleSet':
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
            rule = HeuristicRule.from_dict(rule_data)
            rule_set.add_rule(rule)
        
        return rule_set


class HeuristicRuleManager:
    """
    Manages rule loading, storage, and retrieval.
    
    This class is responsible for:
    - Loading rules from configuration files
    - Storing and organizing rule sets by domain
    - Providing rule retrieval methods
    - Rule set management (add/remove/update)
    
    This class does NOT contain matching logic - that's handled by HeuristicMatcher.
    """
    
    def __init__(self, rules_directory: Optional[str] = None):
        """Initialize the rule manager"""
        self.rules_directory = rules_directory or self._get_default_rules_directory()
        self.rule_sets: Dict[str, HeuristicRuleSet] = {}
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
        
        logger.info(f"Initializing HeuristicRuleManager with rules directory: {self.rules_directory}")
        
        try:
            await self._load_all_rule_sets()
            self._initialized = True
            logger.info(f"Loaded {len(self.rule_sets)} rule sets: {list(self.rule_sets.keys())}")
        except Exception as e:
            logger.error(f"Failed to initialize HeuristicRuleManager: {e}", exc_info=True)
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
        
        rule_set = HeuristicRuleSet.from_dict(data)
        self.rule_sets[rule_set.domain] = rule_set
        logger.info(f"Loaded rule set for domain '{rule_set.domain}' with {len(rule_set.rules)} rules")
    
    # Rule Set Management Methods
    def get_rule_set(self, domain: str) -> Optional[HeuristicRuleSet]:
        """Get rule set for a specific domain"""
        return self.rule_sets.get(domain)
    
    def get_available_domains(self) -> List[str]:
        """Get list of available domains"""
        return list(self.rule_sets.keys())
    
    def add_rule_set(self, rule_set: HeuristicRuleSet) -> None:
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
    
    # Rule Retrieval Methods (no matching logic)
    def get_rule(self, domain: str, rule_id: str) -> Optional[HeuristicRule]:
        """Get a specific rule by domain and ID"""
        rule_set = self.get_rule_set(domain)
        if not rule_set:
            return None
        return rule_set.get_rule(rule_id)
    
    def get_rules_by_type(self, domain: str, rule_type: RuleType) -> List[HeuristicRule]:
        """Get all rules of a specific type in a domain"""
        rule_set = self.get_rule_set(domain)
        if not rule_set:
            return []
        return rule_set.get_rules_by_type(rule_type)
    
    def get_rules_by_tag(self, domain: str, tag: str) -> List[HeuristicRule]:
        """Get all rules with a specific tag in a domain"""
        rule_set = self.get_rule_set(domain)
        if not rule_set:
            return []
        return rule_set.get_rules_by_tag(tag)
    
    def get_all_rules_for_domain(self, domain: str) -> List[HeuristicRule]:
        """Get all rules for a specific domain"""
        rule_set = self.get_rule_set(domain)
        if not rule_set:
            return []
        return rule_set.get_all_rules()
    
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
        logger.info("Reloading all heuristic rules")
        self.rule_sets.clear()
        self._initialized = False
        await self.initialize()


@dataclass
class HeuristicMatchResult:
    """Result of a heuristic matching operation"""
    requirement: str
    capability: str
    matched: bool
    confidence: float
    rule_used: Optional[HeuristicRule] = None
    match_type: str = "heuristic"
    domain: str = "general"
    transformation_details: List[str] = field(default_factory=list)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization"""
        return {
            "requirement": self.requirement,
            "capability": self.capability,
            "matched": self.matched,
            "confidence": self.confidence,
            "rule_used": self.rule_used.to_dict() if self.rule_used else None,
            "match_type": self.match_type,
            "domain": self.domain,
            "transformation_details": self.transformation_details
        }


class HeuristicMatcher:
    """
    Handles heuristic matching logic and confidence calculation.
    
    This class is responsible for:
    - Applying rules to text pairs
    - Calculating confidence scores based on rule applications
    - Determining if texts match heuristically
    - Providing detailed match results with metadata
    
    This class uses HeuristicRuleManager to get rules but handles all matching logic.
    """
    
    def __init__(self, rule_manager: HeuristicRuleManager):
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
        logger.info("HeuristicMatcher initialized")
    
    async def ensure_initialized(self) -> None:
        """Ensure matcher is initialized"""
        if not self._initialized:
            await self.initialize()
    
    def _normalize_text(self, text: str) -> str:
        """Normalize text for comparison"""
        return text.lower().strip()
    
    def _rule_applies_to_texts(self, rule: HeuristicRule, text1: str, text2: str) -> bool:
        """
        Check if a rule applies to the given text pair.
        
        This is the core matching logic that was previously in HeuristicRule.
        """
        norm_text1 = self._normalize_text(text1)
        norm_text2 = self._normalize_text(text2)
        norm_key = self._normalize_text(rule.key)
        norm_values = [self._normalize_text(v) for v in rule.values]
        
        # Check forward direction (key -> values)
        if rule.direction in [RuleDirection.BIDIRECTIONAL, RuleDirection.FORWARD]:
            if norm_text1 == norm_key and norm_text2 in norm_values:
                return True
        
        # Check reverse direction (values -> key)
        if rule.direction in [RuleDirection.BIDIRECTIONAL, RuleDirection.REVERSE]:
            if norm_text2 == norm_key and norm_text1 in norm_values:
                return True
        
        # Check if both texts are values of the same key
        if norm_text1 in norm_values and norm_text2 in norm_values:
            return True
        
        return False
    
    def _calculate_confidence(self, rule: HeuristicRule, text1: str, text2: str) -> float:
        """
        Calculate confidence score for a rule application.
        
        This is where the actual confidence calculation happens,
        not just returning the rule's base_confidence.
        """
        if not self._rule_applies_to_texts(rule, text1, text2):
            return 0.0
        
        # Start with base confidence
        confidence = rule.base_confidence
        
        # Apply confidence adjustments based on rule type
        if rule.type == RuleType.ABBREVIATION:
            # Abbreviations are usually high confidence
            confidence = min(0.95, confidence)
        elif rule.type == RuleType.SYNONYM:
            # Synonyms might be slightly lower confidence
            confidence = min(0.9, confidence)
        elif rule.type == RuleType.SUBSTITUTION:
            # Substitutions might have lower confidence
            confidence = min(0.85, confidence)
        elif rule.type == RuleType.NORMALIZATION:
            # Normalizations are usually high confidence
            confidence = min(0.95, confidence)
        
        # Apply direction-based adjustments
        if rule.direction == RuleDirection.BIDIRECTIONAL:
            # Bidirectional rules are more reliable
            confidence = min(0.95, confidence)
        else:
            # Unidirectional rules might be less reliable
            confidence = max(0.7, confidence - 0.05)
        
        return confidence
    
    async def find_matching_rule(self, text1: str, text2: str, domain: str) -> Optional[HeuristicRule]:
        """
        Find the best matching rule for the given texts in the specified domain.
        
        This is the main matching logic that determines which rule applies.
        """
        await self.ensure_initialized()
        
        rules = self.rule_manager.get_all_rules_for_domain(domain)
        if not rules:
            return None
        
        # Find all applicable rules
        applicable_rules = []
        for rule in rules:
            if self._rule_applies_to_texts(rule, text1, text2):
                applicable_rules.append(rule)
        
        if not applicable_rules:
            return None
        
        # Return rule with highest confidence
        return max(applicable_rules, key=lambda r: self._calculate_confidence(r, text1, text2))
    
    async def calculate_confidence(self, text1: str, text2: str, domain: str) -> float:
        """
        Calculate confidence score for heuristic matching between texts in the specified domain.
        
        This is the main confidence calculation method.
        """
        await self.ensure_initialized()
        
        rule = await self.find_matching_rule(text1, text2, domain)
        if not rule:
            return 0.0
        
        return self._calculate_confidence(rule, text1, text2)
    
    async def is_heuristic_match(self, text1: str, text2: str, domain: str, min_confidence: float = 0.7) -> bool:
        """
        Check if texts match heuristically in the specified domain.
        
        This is the main matching decision method.
        """
        confidence = await self.calculate_confidence(text1, text2, domain)
        return confidence >= min_confidence
    
    async def match(self, requirement: str, capabilities: List[str], domain: str = "manufacturing", min_confidence: float = 0.7) -> List[HeuristicMatchResult]:
        """
        Perform heuristic matching between a requirement and a list of capabilities.
        
        This is the main matching method that returns detailed results.
        """
        await self.ensure_initialized()
        
        results = []
        
        for capability in capabilities:
            # Skip empty strings
            if not requirement.strip() or not capability.strip():
                results.append(HeuristicMatchResult(
                    requirement=requirement,
                    capability=capability,
                    matched=False,
                    confidence=0.0,
                    domain=domain
                ))
                continue
            
            # Find matching rule
            rule = await self.find_matching_rule(requirement, capability, domain)
            
            if rule:
                confidence = self._calculate_confidence(rule, requirement, capability)
                matched = confidence >= min_confidence
                
                # Create transformation details
                transformation_details = []
                if rule.type == RuleType.ABBREVIATION:
                    transformation_details.append(f"Abbreviation expansion: {rule.key} ↔ {', '.join(rule.values)}")
                elif rule.type == RuleType.SYNONYM:
                    transformation_details.append(f"Synonym mapping: {rule.key} ↔ {', '.join(rule.values)}")
                elif rule.type == RuleType.SUBSTITUTION:
                    transformation_details.append(f"Substitution: {rule.key} ↔ {', '.join(rule.values)}")
                elif rule.type == RuleType.NORMALIZATION:
                    transformation_details.append(f"Normalization: {rule.key} ↔ {', '.join(rule.values)}")
                
                results.append(HeuristicMatchResult(
                    requirement=requirement,
                    capability=capability,
                    matched=matched,
                    confidence=confidence,
                    rule_used=rule,
                    domain=domain,
                    transformation_details=transformation_details
                ))
                
                if matched:
                    logger.debug(
                        f"Heuristic match found: '{requirement}' <-> '{capability}' "
                        f"(confidence: {confidence}, rule: {rule.id})"
                    )
            else:
                results.append(HeuristicMatchResult(
                    requirement=requirement,
                    capability=capability,
                    matched=False,
                    confidence=0.0,
                    domain=domain
                ))
        
        return results


# Global instances
_rule_manager: Optional[HeuristicRuleManager] = None
_heuristic_matcher: Optional[HeuristicMatcher] = None


async def get_rule_manager() -> HeuristicRuleManager:
    """Get the global rule manager instance"""
    global _rule_manager
    if _rule_manager is None:
        _rule_manager = HeuristicRuleManager()
        await _rule_manager.initialize()
    return _rule_manager


async def get_heuristic_matcher() -> HeuristicMatcher:
    """Get the global heuristic matcher instance"""
    global _heuristic_matcher
    if _heuristic_matcher is None:
        rule_manager = await get_rule_manager()
        _heuristic_matcher = HeuristicMatcher(rule_manager)
        await _heuristic_matcher.initialize()
    return _heuristic_matcher


def create_rule_manager(rules_directory: Optional[str] = None) -> HeuristicRuleManager:
    """Create a new rule manager instance"""
    return HeuristicRuleManager(rules_directory)


def create_heuristic_matcher(rule_manager: HeuristicRuleManager) -> HeuristicMatcher:
    """Create a new heuristic matcher instance"""
    return HeuristicMatcher(rule_manager)
