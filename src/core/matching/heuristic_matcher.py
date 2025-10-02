"""
Heuristic Matcher Implementation

This module provides a domain-aware heuristic matcher that uses the HeuristicRuleManager
to perform rule-based matching across different domains.
"""

from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass
import logging

from .heuristic_rules import HeuristicRuleManager, HeuristicRule, get_rule_manager
from ..utils.logging import get_logger

logger = get_logger(__name__)


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
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization"""
        return {
            "requirement": self.requirement,
            "capability": self.capability,
            "matched": self.matched,
            "confidence": self.confidence,
            "rule_used": self.rule_used.to_dict() if self.rule_used else None,
            "match_type": self.match_type,
            "domain": self.domain
        }


class HeuristicMatcher:
    """Domain-aware heuristic matcher using rule-based matching"""
    
    def __init__(self, rule_manager: Optional[HeuristicRuleManager] = None):
        """Initialize the heuristic matcher"""
        self.rule_manager = rule_manager
        self._initialized = False
    
    async def initialize(self) -> None:
        """Initialize the matcher with rule manager"""
        if self._initialized:
            return
        
        if self.rule_manager is None:
            self.rule_manager = await get_rule_manager()
        
        self._initialized = True
        logger.info("HeuristicMatcher initialized")
    
    async def ensure_initialized(self) -> None:
        """Ensure matcher is initialized"""
        if not self._initialized:
            await self.initialize()
    
    async def match(
        self, 
        requirement: str, 
        capabilities: List[str], 
        domain: str = "manufacturing",
        min_confidence: float = 0.7
    ) -> List[HeuristicMatchResult]:
        """
        Perform heuristic matching between a requirement and a list of capabilities
        
        Args:
            requirement: The requirement to match
            capabilities: List of capabilities to match against
            domain: The domain for rule selection
            min_confidence: Minimum confidence threshold for matches
            
        Returns:
            List of HeuristicMatchResult objects
        """
        await self.ensure_initialized()
        
        results = []
        requirement_lower = requirement.lower().strip()
        
        for capability in capabilities:
            capability_lower = capability.lower().strip()
            
            # Skip empty strings
            if not requirement_lower or not capability_lower:
                results.append(HeuristicMatchResult(
                    requirement=requirement,
                    capability=capability,
                    matched=False,
                    confidence=0.0,
                    domain=domain
                ))
                continue
            
            # Find matching rule
            rule = self.rule_manager.find_matching_rule(requirement_lower, capability_lower, domain)
            
            if rule and rule.confidence >= min_confidence:
                results.append(HeuristicMatchResult(
                    requirement=requirement,
                    capability=capability,
                    matched=True,
                    confidence=rule.confidence,
                    rule_used=rule,
                    domain=domain
                ))
                
                logger.debug(
                    f"Heuristic match found: '{requirement}' <-> '{capability}' "
                    f"(confidence: {rule.confidence}, rule: {rule.id})"
                )
            else:
                results.append(HeuristicMatchResult(
                    requirement=requirement,
                    capability=capability,
                    matched=False,
                    confidence=rule.confidence if rule else 0.0,
                    rule_used=rule,
                    domain=domain
                ))
        
        return results
    
    async def is_match(
        self, 
        requirement: str, 
        capability: str, 
        domain: str = "manufacturing",
        min_confidence: float = 0.7
    ) -> bool:
        """
        Check if a requirement matches a capability using heuristic rules
        
        Args:
            requirement: The requirement to match
            capability: The capability to match against
            domain: The domain for rule selection
            min_confidence: Minimum confidence threshold
            
        Returns:
            True if heuristic match found, False otherwise
        """
        await self.ensure_initialized()
        
        return self.rule_manager.is_heuristic_match(
            requirement.lower().strip(),
            capability.lower().strip(),
            domain,
            min_confidence
        )
    
    async def get_confidence(
        self, 
        requirement: str, 
        capability: str, 
        domain: str = "manufacturing"
    ) -> float:
        """
        Get confidence score for heuristic matching between requirement and capability
        
        Args:
            requirement: The requirement to match
            capability: The capability to match against
            domain: The domain for rule selection
            
        Returns:
            Confidence score (0.0 to 1.0)
        """
        await self.ensure_initialized()
        
        return self.rule_manager.get_rule_confidence(
            requirement.lower().strip(),
            capability.lower().strip(),
            domain
        )
    
    async def get_available_domains(self) -> List[str]:
        """Get list of available domains with heuristic rules"""
        await self.ensure_initialized()
        return self.rule_manager.get_available_domains()
    
    async def get_rule_statistics(self) -> Dict[str, Any]:
        """Get statistics about loaded heuristic rules"""
        await self.ensure_initialized()
        return self.rule_manager.get_rule_statistics()
    
    async def reload_rules(self) -> None:
        """Reload all heuristic rules from configuration files"""
        await self.ensure_initialized()
        await self.rule_manager.reload_rules()
        logger.info("Heuristic rules reloaded")


# Domain-specific heuristic matchers
class ManufacturingHeuristicMatcher(HeuristicMatcher):
    """Heuristic matcher specifically for manufacturing domain"""
    
    def __init__(self, rule_manager: Optional[HeuristicRuleManager] = None):
        super().__init__(rule_manager)
        self.domain = "manufacturing"
    
    async def match(
        self, 
        requirement: str, 
        capabilities: List[str], 
        min_confidence: float = 0.7
    ) -> List[HeuristicMatchResult]:
        """Match manufacturing requirements against capabilities"""
        return await super().match(requirement, capabilities, self.domain, min_confidence)
    
    async def is_match(
        self, 
        requirement: str, 
        capability: str, 
        min_confidence: float = 0.7
    ) -> bool:
        """Check if manufacturing requirement matches capability"""
        return await super().is_match(requirement, capability, self.domain, min_confidence)
    
    async def get_confidence(
        self, 
        requirement: str, 
        capability: str
    ) -> float:
        """Get confidence for manufacturing requirement-capability match"""
        return await super().get_confidence(requirement, capability, self.domain)


class CookingHeuristicMatcher(HeuristicMatcher):
    """Heuristic matcher specifically for cooking domain"""
    
    def __init__(self, rule_manager: Optional[HeuristicRuleManager] = None):
        super().__init__(rule_manager)
        self.domain = "cooking"
    
    async def match(
        self, 
        requirement: str, 
        capabilities: List[str], 
        min_confidence: float = 0.7
    ) -> List[HeuristicMatchResult]:
        """Match cooking requirements against capabilities"""
        return await super().match(requirement, capabilities, self.domain, min_confidence)
    
    async def is_match(
        self, 
        requirement: str, 
        capability: str, 
        min_confidence: float = 0.7
    ) -> bool:
        """Check if cooking requirement matches capability"""
        return await super().is_match(requirement, capability, self.domain, min_confidence)
    
    async def get_confidence(
        self, 
        requirement: str, 
        capability: str
    ) -> float:
        """Get confidence for cooking requirement-capability match"""
        return await super().get_confidence(requirement, capability, self.domain)


# Global heuristic matcher instances
_heuristic_matchers: Dict[str, HeuristicMatcher] = {}


async def get_heuristic_matcher(domain: str = "manufacturing") -> HeuristicMatcher:
    """Get a heuristic matcher for the specified domain"""
    global _heuristic_matchers
    
    if domain not in _heuristic_matchers:
        if domain == "manufacturing":
            _heuristic_matchers[domain] = ManufacturingHeuristicMatcher()
        elif domain == "cooking":
            _heuristic_matchers[domain] = CookingHeuristicMatcher()
        else:
            _heuristic_matchers[domain] = HeuristicMatcher()
        
        await _heuristic_matchers[domain].initialize()
    
    return _heuristic_matchers[domain]


def create_heuristic_matcher(domain: str = "manufacturing") -> HeuristicMatcher:
    """Create a new heuristic matcher for the specified domain"""
    if domain == "manufacturing":
        return ManufacturingHeuristicMatcher()
    elif domain == "cooking":
        return CookingHeuristicMatcher()
    else:
        return HeuristicMatcher()
