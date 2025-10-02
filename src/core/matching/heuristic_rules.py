"""
Heuristic Rules System for Multi-Domain Matching

This module provides a modular, extensible system for managing heuristic matching rules
across different domains. It supports:

1. Domain-specific rule sets
2. Configurable rule loading from external files
3. Dynamic rule management at runtime
4. Horizontal extensibility (adding rules within domains)
5. Vertical extensibility (adding new domains)

Architecture:
- HeuristicRule: Individual rule definition
- HeuristicRuleSet: Collection of rules for a domain
- HeuristicRuleManager: Manages rule loading and retrieval
- Domain-specific rule configurations in YAML/JSON files
"""

from typing import Dict, List, Optional, Any, Union, Set
from dataclasses import dataclass, field
from enum import Enum
import yaml
import json
import os
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
    """Individual heuristic matching rule"""
    id: str
    type: RuleType
    key: str
    values: List[str]
    direction: RuleDirection = RuleDirection.BIDIRECTIONAL
    confidence: float = 0.9
    domain: str = "general"
    description: str = ""
    source: str = ""
    tags: Set[str] = field(default_factory=set)
    created_at: datetime = field(default_factory=datetime.now)
    updated_at: datetime = field(default_factory=datetime.now)
    
    def __post_init__(self):
        """Validate rule after initialization"""
        if not self.key or not self.values:
            raise ValueError(f"Rule {self.id}: key and values cannot be empty")
        if not 0.0 <= self.confidence <= 1.0:
            raise ValueError(f"Rule {self.id}: confidence must be between 0.0 and 1.0")
    
    def applies_to(self, text1: str, text2: str) -> bool:
        """Check if this rule applies to the given text pair"""
        text1_lower = text1.lower().strip()
        text2_lower = text2.lower().strip()
        
        if self.direction in [RuleDirection.BIDIRECTIONAL, RuleDirection.FORWARD]:
            if text1_lower == self.key.lower() and text2_lower in [v.lower() for v in self.values]:
                return True
        
        if self.direction in [RuleDirection.BIDIRECTIONAL, RuleDirection.REVERSE]:
            if text2_lower == self.key.lower() and text1_lower in [v.lower() for v in self.values]:
                return True
        
        # Check if both texts are values of the same key
        if text1_lower in [v.lower() for v in self.values] and text2_lower in [v.lower() for v in self.values]:
            return True
        
        return False
    
    def get_confidence(self, text1: str, text2: str) -> float:
        """Get confidence score for this rule applied to the given texts"""
        if self.applies_to(text1, text2):
            return self.confidence
        return 0.0
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert rule to dictionary for serialization"""
        return {
            "id": self.id,
            "type": self.type.value,
            "direction": self.direction.value,
            "key": self.key,
            "values": self.values,
            "confidence": self.confidence,
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
            confidence=data.get("confidence", 0.9),
            domain=data.get("domain", "general"),
            description=data.get("description", ""),
            source=data.get("source", ""),
            tags=set(data.get("tags", [])),
            created_at=datetime.fromisoformat(data.get("created_at", datetime.now().isoformat())),
            updated_at=datetime.fromisoformat(data.get("updated_at", datetime.now().isoformat()))
        )


@dataclass
class HeuristicRuleSet:
    """Collection of heuristic rules for a specific domain"""
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
    
    def find_matching_rules(self, text1: str, text2: str) -> List[HeuristicRule]:
        """Find all rules that apply to the given text pair"""
        matching_rules = []
        for rule in self.rules.values():
            if rule.applies_to(text1, text2):
                matching_rules.append(rule)
        return matching_rules
    
    def get_best_match(self, text1: str, text2: str) -> Optional[HeuristicRule]:
        """Get the rule with highest confidence that applies to the given texts"""
        matching_rules = self.find_matching_rules(text1, text2)
        if not matching_rules:
            return None
        
        # Return rule with highest confidence
        return max(matching_rules, key=lambda r: r.confidence)
    
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
    """Manages heuristic rules across all domains"""
    
    def __init__(self, rules_directory: Optional[str] = None):
        """Initialize the rule manager"""
        self.rules_directory = rules_directory or self._get_default_rules_directory()
        self.rule_sets: Dict[str, HeuristicRuleSet] = {}
        self._initialized = False
        
    def _get_default_rules_directory(self) -> str:
        """Get the default rules directory"""
        # Look for rules in the project structure
        current_dir = Path(__file__).parent
        rules_dir = current_dir / "rules"
        if rules_dir.exists():
            return str(rules_dir)
        
        # Fallback to a config directory
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
        
        # Look for rule files (YAML or JSON)
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
    
    def find_matching_rule(self, text1: str, text2: str, domain: str) -> Optional[HeuristicRule]:
        """Find the best matching rule for the given texts in the specified domain"""
        rule_set = self.get_rule_set(domain)
        if not rule_set:
            return None
        
        return rule_set.get_best_match(text1, text2)
    
    def get_rule_confidence(self, text1: str, text2: str, domain: str) -> float:
        """Get confidence score for heuristic matching between texts in the specified domain"""
        rule = self.find_matching_rule(text1, text2, domain)
        return rule.confidence if rule else 0.0
    
    def is_heuristic_match(self, text1: str, text2: str, domain: str, min_confidence: float = 0.7) -> bool:
        """Check if texts match heuristically in the specified domain"""
        confidence = self.get_rule_confidence(text1, text2, domain)
        return confidence >= min_confidence
    
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


# Global rule manager instance
_rule_manager: Optional[HeuristicRuleManager] = None


async def get_rule_manager() -> HeuristicRuleManager:
    """Get the global rule manager instance"""
    global _rule_manager
    if _rule_manager is None:
        _rule_manager = HeuristicRuleManager()
        await _rule_manager.initialize()
    return _rule_manager


def create_rule_manager(rules_directory: Optional[str] = None) -> HeuristicRuleManager:
    """Create a new rule manager instance"""
    return HeuristicRuleManager(rules_directory)
