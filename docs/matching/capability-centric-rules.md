# Capability-Centric Heuristic Rules System

## Overview

The Capability-Centric Heuristic Rules System is the second layer in the Open Matching Engine's multi-layered matching approach. It applies rule-based matching using predefined knowledge about what requirements each capability can satisfy, providing a clear and explicit way to handle variations in terminology and domain-specific knowledge.

## Purpose

The Capability-Centric Heuristic Rules System provides:
- **Capability-Centric Logic**: Rules define what requirements a capability can satisfy
- **Bidirectional Matching**: Supports both capability-to-requirement and requirement-to-capability matching
- **Domain Separation**: Manufacturing and cooking rules are completely separate
- **Configuration-Driven**: Rules loaded from external YAML files
- **Extensible**: Easy to add new capabilities and requirements
- **Traceable**: Full context preservation in match results

## Architecture

### Core Data Models

```python
from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional, Set
from enum import Enum

class RuleType(Enum):
    """Types of capability rules."""
    CAPABILITY_MATCH = "capability_match"

class RuleDirection(Enum):
    """Direction of rule application."""
    BIDIRECTIONAL = "bidirectional"
    FORWARD = "forward"
    REVERSE = "reverse"

@dataclass
class CapabilityRule:
    """Individual capability-centric matching rule."""
    id: str                      # Unique identifier for the rule
    type: RuleType              # Rule type (capability_match, etc.)
    capability: str             # The capability being defined
    satisfies_requirements: List[str]  # List of requirements this capability can satisfy
    confidence: float           # Confidence score (0.0 to 1.0)
    domain: str                 # Target domain for the rule
    description: str            # Human-readable description
    source: str                 # Source of the rule (standards, documentation, etc.)
    tags: Set[str]             # Categorization tags for organization
    
    def can_satisfy_requirement(self, requirement: str) -> bool:
        """Check if this capability can satisfy the given requirement."""
        return requirement.lower().strip() in [req.lower().strip() for req in self.satisfies_requirements]
    
    def requirement_can_be_satisfied_by(self, requirement: str, capability: str) -> bool:
        """Check if the requirement can be satisfied by the capability."""
        return (capability.lower().strip() == self.capability.lower().strip() and 
                self.can_satisfy_requirement(requirement))

@dataclass
class CapabilityRuleSet:
    """Collection of capability rules for a specific domain."""
    domain: str                 # Target domain name
    version: str                # Rule set version
    description: str            # Domain description
    rules: Dict[str, CapabilityRule]  # Dictionary of rules by ID
    
    def find_rules_for_capability_requirement(self, capability: str, requirement: str) -> List[CapabilityRule]:
        """Find rules where the capability can satisfy the requirement."""
        matching_rules = []
        for rule in self.rules.values():
            if rule.requirement_can_be_satisfied_by(requirement, capability):
                matching_rules.append(rule)
        return matching_rules
```

### Rule Manager

```python
class CapabilityRuleManager:
    """Central manager for all capability rule sets with configuration loading."""
    
    def __init__(self, rules_directory: Optional[str] = None):
        self.rules_directory = rules_directory or self._get_default_rules_directory()
        self.rule_sets: Dict[str, CapabilityRuleSet] = {}
        self._initialized = False
        
    async def initialize(self) -> None:
        """Load all rule sets from configuration files."""
        await self._load_all_rule_sets()
        self._initialized = True
        
    def find_rules_for_capability_requirement(self, domain: str, capability: str, requirement: str) -> List[CapabilityRule]:
        """Find rules where the capability can satisfy the requirement in the specified domain."""
        rule_set = self.get_rule_set(domain)
        if not rule_set:
            return []
        return rule_set.find_rules_for_capability_requirement(capability, requirement)
```

### Capability Matcher

```python
@dataclass
class CapabilityMatchResult:
    """Result of a capability matching operation with full context."""
    requirement_object: Dict[str, Any]  # The complete requirement object
    capability_object: Dict[str, Any]   # The complete capability object
    requirement_field: str              # The field that was matched (e.g., "process_name")
    capability_field: str               # The field that was matched (e.g., "process_name")
    requirement_value: str              # The extracted value that was compared
    capability_value: str               # The extracted value that was compared
    matched: bool                       # Whether a match was found
    confidence: float                   # Confidence score
    rule_used: Optional[CapabilityRule] # The rule that was used
    match_type: str                     # Type of match
    domain: str                         # Domain of the match
    transformation_details: List[str]   # Details about the matching process

class CapabilityMatcher:
    """Handles capability-centric matching logic."""
    
    def __init__(self, rule_manager: CapabilityRuleManager):
        self.rule_manager = rule_manager
        self._initialized = False
        
    async def initialize(self) -> None:
        """Initialize the matcher."""
        await self.rule_manager.initialize()
        self._initialized = True
        
    async def capability_can_satisfy_requirement(self, capability: str, requirement: str, domain: str) -> bool:
        """Check if a capability can satisfy a requirement."""
        await self.ensure_initialized()
        rules = self.rule_manager.find_rules_for_capability_requirement(domain, capability, requirement)
        return len(rules) > 0
```

## Rule Configuration

### File Structure

Rules are stored in YAML files in the `src/core/matching/capability_rules/` directory:

```
src/core/matching/capability_rules/
├── manufacturing.yaml
└── cooking.yaml
```

### Manufacturing Rules Example

```yaml
# src/core/matching/capability_rules/manufacturing.yaml
domain: manufacturing
version: "1.0.0"
description: "Capability-centric rules for manufacturing domain - defines what requirements each capability can satisfy"

metadata:
  maintainer: "OME Manufacturing Team"
  last_updated: "2024-01-01"
  source: "Manufacturing standards and industry terminology"

rules:
  cnc_machining_capability:
    id: "cnc_machining_capability"
    type: "capability_match"
    capability: "cnc machining"
    satisfies_requirements: ["milling", "machining", "material removal", "subtractive manufacturing", "cnc", "computer numerical control"]
    confidence: 0.95
    domain: "manufacturing"
    description: "CNC machining can satisfy various milling and machining requirements"
    source: "Manufacturing Standards Institute"
    tags: ["machining", "automation", "subtractive"]

  additive_manufacturing_capability:
    id: "additive_manufacturing_capability"
    type: "capability_match"
    capability: "3d printing"
    satisfies_requirements: ["additive manufacturing", "rapid prototyping", "additive fabrication", "3d printing", "3-d printing"]
    confidence: 0.95
    domain: "manufacturing"
    description: "3D printing can satisfy additive manufacturing requirements"
    source: "Additive Manufacturing Standards"
    tags: ["additive", "prototyping", "3d"]

  surface_finish_capability:
    id: "surface_finish_capability"
    type: "capability_match"
    capability: "surface finishing"
    satisfies_requirements: ["surface finish", "surface roughness", "ra value", "surface texture", "finish quality", "surface treatment"]
    confidence: 0.85
    domain: "manufacturing"
    description: "Surface finishing can satisfy various surface treatment requirements"
    source: "Surface Treatment Standards"
    tags: ["finishing", "surface", "treatment"]
```

### Cooking Rules Example

```yaml
# src/core/matching/capability_rules/cooking.yaml
domain: cooking
version: "1.0.0"
description: "Capability-centric rules for cooking domain - defines what requirements each capability can satisfy"

metadata:
  maintainer: "OME Cooking Team"
  last_updated: "2024-01-01"
  source: "Culinary terminology and cooking standards"

rules:
  sauté_capability:
    id: "sauté_capability"
    type: "capability_match"
    capability: "sauté pan"
    satisfies_requirements: ["sauté", "saute", "sauted", "sautéed", "pan-fry", "pan fry", "frying", "sautéing"]
    confidence: 0.95
    domain: "cooking"
    description: "Sauté pan can satisfy sautéing and pan-frying requirements"
    source: "Culinary Arts Institute"
    tags: ["technique", "cooking", "frying"]

  roasting_capability:
    id: "roasting_capability"
    type: "capability_match"
    capability: "oven"
    satisfies_requirements: ["roast", "roasted", "roasting", "bake", "baked", "baking", "oven cook", "oven cooking"]
    confidence: 0.9
    domain: "cooking"
    description: "Oven can satisfy roasting and baking requirements"
    source: "Culinary Arts Institute"
    tags: ["technique", "cooking", "oven"]

  pot_capability:
    id: "pot_capability"
    type: "capability_match"
    capability: "saucepan"
    satisfies_requirements: ["pot", "saucepan", "cooking pot", "stock pot", "soup pot", "boiling"]
    confidence: 0.9
    domain: "cooking"
    description: "Saucepan can satisfy various pot-based cooking requirements"
    source: "Culinary Arts Institute"
    tags: ["equipment", "cooking", "pot"]
```

## Usage Examples

### Basic Usage

```python
from src.core.matching.capability_rules import CapabilityRuleManager, CapabilityMatcher

# Initialize the system
rule_manager = CapabilityRuleManager()
matcher = CapabilityMatcher(rule_manager)
await matcher.initialize()

# Check if a capability can satisfy a requirement
can_satisfy = await matcher.capability_can_satisfy_requirement("cnc machining", "milling", "manufacturing")
print(f"CNC machining can satisfy milling: {can_satisfy}")  # True

# Check bidirectional matching
can_satisfy = await matcher.requirement_can_be_satisfied_by("milling", "cnc machining", "manufacturing")
print(f"Milling can be satisfied by CNC machining: {can_satisfy}")  # True
```

### Object-to-Object Matching

```python
# Match requirement objects to capability objects
requirements = [
    {"process_name": "milling", "parameters": {"tolerance": "0.001"}},
    {"process_name": "additive manufacturing", "parameters": {"layer_height": "0.1"}}
]

capabilities = [
    {"process_name": "cnc machining", "parameters": {"max_tolerance": "0.0005"}},
    {"process_name": "3d printing", "parameters": {"layer_height": "0.05"}}
]

results = await matcher.match_requirements_to_capabilities(requirements, capabilities, "manufacturing")

for result in results:
    print(f"Requirement: {result.requirement_value}")
    print(f"Capability: {result.capability_value}")
    print(f"Matched: {result.matched}")
    print(f"Confidence: {result.confidence}")
    if result.rule_used:
        print(f"Rule: {result.rule_used.id}")
    print("---")
```

### Domain-Specific Examples

#### Manufacturing Domain
```python
# Manufacturing examples
manufacturing_requirements = [
    {"process_name": "milling"},
    {"process_name": "surface finish"},
    {"process_name": "welding"}
]

manufacturing_capabilities = [
    {"process_name": "cnc machining"},
    {"process_name": "surface finishing"},
    {"process_name": "tig welding"}
]

results = await matcher.match_requirements_to_capabilities(
    manufacturing_requirements, manufacturing_capabilities, "manufacturing"
)

# Expected matches:
# milling -> cnc machining (confidence: 0.95)
# surface finish -> surface finishing (confidence: 0.85)
# welding -> tig welding (confidence: 0.9)
```

#### Cooking Domain
```python
# Cooking examples
cooking_requirements = [
    {"technique": "sauté"},
    {"technique": "bake"},
    {"technique": "boiling"}
]

cooking_capabilities = [
    {"technique": "sauté pan"},
    {"technique": "oven"},
    {"technique": "saucepan"}
]

results = await matcher.match_requirements_to_capabilities(
    cooking_requirements, cooking_capabilities, "cooking",
    requirement_field="technique", capability_field="technique"
)

# Expected matches:
# sauté -> sauté pan (confidence: 0.95)
# bake -> oven (confidence: 0.9)
# boiling -> saucepan (confidence: 0.9)
```

## Integration with Matching Service

The Capability-Centric Heuristic Rules System is integrated as Layer 2 in the MatchingService:

```python
class MatchingService:
    def __init__(self):
        self.rule_manager = CapabilityRuleManager()
        self.capability_matcher = CapabilityMatcher(self.rule_manager)
        
    async def _heuristic_match(self, requirement: str, capability: str, domain: str) -> bool:
        """Perform heuristic matching using capability-centric rules."""
        return await self.capability_matcher.capability_can_satisfy_requirement(
            capability, requirement, domain
        )
    
    async def _can_satisfy_requirements(self, requirements: List[Dict], capabilities: List[Dict]) -> bool:
        """Check if capabilities can satisfy requirements using multi-layered matching."""
        for req in requirements:
            req_process = req.get("process_name", "").lower().strip()
            if not req_process:
                continue
                
            for cap in capabilities:
                cap_process = cap.get("process_name", "").lower().strip()
                if not cap_process:
                    continue
                
                # Layer 1: Direct Matching
                if self._direct_match(req_process, cap_process, domain="manufacturing"):
                    return True
                
                # Layer 2: Heuristic Matching (capability-centric rules)
                if await self._heuristic_match(req_process, cap_process, domain="manufacturing"):
                    return True
        
        return False
```


## Configuration Management

### Adding New Rules

1. **Edit the appropriate YAML file**:
   ```yaml
   new_capability_rule:
     id: "new_capability_rule"
     type: "capability_match"
     capability: "new capability"
     satisfies_requirements: ["requirement1", "requirement2"]
     confidence: 0.9
     domain: "manufacturing"
     description: "Description of the new capability"
     source: "Source of the rule"
     tags: ["tag1", "tag2"]
   ```

2. **Reload the rules**:
   ```python
   await rule_manager.reload_rules()
   ```

### Adding New Domains

1. **Create a new YAML file** in `src/core/matching/capability_rules/`
2. **Follow the same structure** as existing domain files
3. **The system will automatically load** the new domain on initialization
