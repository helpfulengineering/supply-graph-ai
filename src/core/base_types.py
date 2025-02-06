from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Dict, List, Optional, Set, Any
from enum import Enum

class MatchConfidence(Enum):
    """Standardized confidence levels for matches"""
    NONE = 0
    LOW = 0.25
    MEDIUM = 0.5
    HIGH = 0.75
    PERFECT = 1.0

@dataclass
class Requirement:
    """Base class for any required capability or resource"""
    name: str
    type: str
    parameters: Dict[str, Any]
    constraints: Dict[str, Any]
    is_required: bool = True
    
    def __hash__(self):
        return hash(f"{self.type}:{self.name}")

@dataclass
class Capability:
    """Base class for any available capability or resource"""
    name: str
    type: str
    parameters: Dict[str, Any]
    limitations: Dict[str, Any]

@dataclass
class Substitution:
    """Represents a possible substitution for a requirement"""
    original: Requirement
    substitute: Capability
    confidence: float
    constraints: Dict[str, Any]
    notes: Optional[str] = None

@dataclass
class MatchResult:
    """Result of matching requirements against capabilities"""
    confidence: float
    matched_capabilities: Dict[Requirement, Capability]
    missing_requirements: List[Requirement]
    substitutions: List[Substitution]
    notes: Optional[str] = None

class BaseParser(ABC):
    """Abstract base class for parsing domain-specific inputs"""
    
    @abstractmethod
    def parse_requirements(self, input_data: Any) -> List[Requirement]:
        """Parse input into standardized requirements"""
        pass
    
    @abstractmethod
    def parse_capabilities(self, input_data: Any) -> List[Capability]:
        """Parse input into standardized capabilities"""
        pass

class BaseMatcher(ABC):
    """Abstract base class for matching requirements to capabilities"""
    
    @abstractmethod
    def match(self, 
              requirements: List[Requirement],
              capabilities: List[Capability]) -> MatchResult:
        """Match requirements against capabilities"""
        pass

class BaseKnowledgeProvider(ABC):
    """Abstract base class for domain knowledge providers"""
    
    @abstractmethod
    def get_substitutions(self, 
                         requirement: Requirement,
                         capabilities: List[Capability]) -> List[Substitution]:
        """Find possible substitutions for a requirement"""
        pass
    
    @abstractmethod
    def validate_match(self,
                      requirement: Requirement,
                      capability: Capability) -> float:
        """Validate and score a potential match"""
        pass

class BaseValidator(ABC):
    """Abstract base class for validation rules"""
    
    @abstractmethod
    def validate(self,
                requirement: Requirement,
                capability: Optional[Capability] = None) -> bool:
        """Validate a requirement or requirement-capability pair"""
        pass

# Helper functions for confidence scoring
def combine_confidence_scores(scores: List[float]) -> float:
    """Combine multiple confidence scores into a single score"""
    if not scores:
        return 0.0
    # For now, simple average - could be made more sophisticated
    return sum(scores) / len(scores)

class KnowledgeBase(ABC):
    """Abstract base class for managing evolving knowledge"""
    
    @abstractmethod
    def add_rule(self, rule_type: str, rule_data: Dict[str, Any], confidence: float = 1.0):
        """Add a new rule to the knowledge base"""
        pass
    
    @abstractmethod
    def query_rules(self, rule_type: str, query: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Query rules matching given criteria"""
        pass
    
    @abstractmethod
    def update_confidence(self, rule_id: str, new_confidence: float):
        """Update confidence score for a rule based on feedback"""
        pass

class FeedbackCollector(ABC):
    """Abstract base class for collecting and processing feedback"""
    
    @abstractmethod
    def record_feedback(self, 
                       match_result: MatchResult,
                       success: bool,
                       feedback_data: Dict[str, Any]):
        """Record feedback about a match result"""
        pass
    
    @abstractmethod
    def analyze_feedback(self) -> List[Dict[str, Any]]:
        """Analyze collected feedback to generate insights"""
        pass

class Context:
    """Manages contextual information for matching operations"""
    
    def __init__(self):
        self.constraints: Dict[str, Any] = {}
        self.preferences: Dict[str, Any] = {}
        self.temporary_rules: List[Dict[str, Any]] = []
        
    def add_constraint(self, name: str, value: Any):
        """Add a constraint to the context"""
        self.constraints[name] = value
        
    def add_preference(self, name: str, value: Any):
        """Add a preference to the context"""
        self.preferences[name] = value
        
    def add_temporary_rule(self, rule: Dict[str, Any]):
        """Add a temporary rule for this context"""
        self.temporary_rules.append(rule)