# Heuristic Rules System

## Overview

The Capability-Centric Heuristic Rules System is the second layer in the Open Hardware Manager's multi-layered matching approach. It applies rule-based matching using predefined knowledge about what requirements each capability can satisfy, providing a clear and explicit way to handle variations in terminology and domain-specific knowledge.

**Rules are now user-configurable** and can be managed via API endpoints or CLI commands. Rules are stored in `src/config/rules/` and can be easily updated, imported, exported, and validated.

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

Rules are stored in YAML files in the `src/config/rules/` directory (user-accessible location):

```
src/config/rules/
├── manufacturing.yaml
└── cooking.yaml
```

**Note:** Rules have been moved from `src/core/matching/rules/` to `src/config/rules/` to make them user-accessible. The system maintains backward compatibility and will fall back to the old location if needed.

### Manufacturing Rules Example

```yaml
# src/core/matching/capability_rules/manufacturing.yaml
domain: manufacturing
version: "1.0.0"
description: "Capability-centric rules for manufacturing domain - defines what requirements each capability can satisfy"

metadata:
  maintainer: "OHM Manufacturing Team"
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
  maintainer: "OHM Cooking Team"
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


## Rules Management

The Rules Management system provides programmatic access to manage matching rules through both API and CLI interfaces. This enables users to inspect, modify, import, export, and validate rules without directly editing configuration files.

### Accessing Rules

#### Via API

All rules management operations are available through RESTful API endpoints under `/v1/api/match/rules`:

- **List Rules**: `GET /v1/api/match/rules` - List all rules with optional filtering
- **Get Rule**: `GET /v1/api/match/rules/{domain}/{rule_id}` - Get a specific rule
- **Create Rule**: `POST /v1/api/match/rules` - Create a new rule
- **Update Rule**: `PUT /v1/api/match/rules/{domain}/{rule_id}` - Update an existing rule
- **Delete Rule**: `DELETE /v1/api/match/rules/{domain}/{rule_id}` - Delete a rule
- **Import Rules**: `POST /v1/api/match/rules/import` - Import rules from YAML/JSON file
- **Export Rules**: `POST /v1/api/match/rules/export` - Export rules to YAML/JSON format
- **Validate Rules**: `POST /v1/api/match/rules/validate` - Validate rule file without importing
- **Compare Rules**: `POST /v1/api/match/rules/compare` - Compare rules file with current rules (dry-run)
- **Reset Rules**: `POST /v1/api/match/rules/reset` - Reset all rules (clear all rule sets)

See [API Documentation](../api/routes.md#rules-management-routes) for detailed endpoint documentation.

#### Via CLI

All rules management operations are available through CLI commands under `ome match rules`:

- **List Rules**: `ome match rules list` - List all rules with optional filtering
- **Get Rule**: `ome match rules get DOMAIN RULE_ID` - Get a specific rule
- **Create Rule**: `ome match rules create` - Create a new rule (supports `--file` or `--interactive`)
- **Update Rule**: `ome match rules update DOMAIN RULE_ID` - Update an existing rule (supports `--file` or `--interactive`)
- **Delete Rule**: `ome match rules delete DOMAIN RULE_ID` - Delete a rule
- **Import Rules**: `ome match rules import FILE` - Import rules from YAML/JSON file
- **Export Rules**: `ome match rules export OUTPUT_FILE` - Export rules to YAML/JSON format
- **Validate Rules**: `ome match rules validate FILE` - Validate rule file without importing
- **Compare Rules**: `ome match rules compare FILE` - Compare rules file with current rules (dry-run)
- **Reset Rules**: `ome match rules reset` - Reset all rules (clear all rule sets)

See [CLI Documentation](../CLI/index.md) for detailed command documentation.

### Import/Export Workflows

#### Export Rules for Backup

```bash
# Export all rules to YAML
ome match rules export backup_rules.yaml

# Export specific domain
ome match rules export manufacturing_rules.yaml --domain manufacturing

# Export with metadata
ome match rules export rules_with_metadata.yaml --include-metadata
```

#### Import Updated Rules

```bash
# Validate before importing
ome match rules validate updated_rules.yaml

# Compare to see changes
ome match rules compare updated_rules.yaml

# Import with dry-run to preview
ome match rules import updated_rules.yaml --dry-run

# Import the rules
ome match rules import updated_rules.yaml
```

### Validation Process

Rules are automatically validated when imported or created. The validation process checks:

- **Required Fields**: All required fields must be present (`id`, `type`, `capability`, `satisfies_requirements`, `domain`)
- **Data Types**: Fields must have correct types (strings, numbers, lists, etc.)
- **Value Ranges**: Confidence scores must be between 0.0 and 1.0
- **Business Rules**: Additional checks for duplicate requirements, low confidence warnings, etc.

Use the `validate` command or endpoint to check rules before importing:

```bash
ome match rules validate rules.yaml
```

### Best Practices for Rule Management

- **Always validate before importing**: Use `validate` to check rule files before importing
- **Use compare to preview changes**: Use `compare` to see what changes will be made before importing
- **Export rules as backup**: Export rules before making major changes
- **Use interactive mode for complex rules**: Use `--interactive` flag when creating or updating rules
- **Test with dry-run**: Use `--dry-run` flag when importing to preview changes
- **Version control rule files**: Keep rule files in version control to track changes
- **Document rule changes**: Add descriptions to rules explaining their purpose

## Configuration Management

### Adding New Rules

You can add new rules using either the API, CLI, or by directly editing YAML files:

#### Method 1: Using CLI (Recommended)

```bash
# Interactive mode (recommended for new rules)
ome match rules create --interactive

# Or from a file
ome match rules create --file new_rule.yaml
```

#### Method 2: Using API

```bash
curl -X POST http://localhost:8001/v1/api/match/rules \
  -H "Content-Type: application/json" \
  -d '{
    "rule_data": {
      "id": "new_rule_id",
      "type": "capability_match",
      "capability": "new capability",
      "satisfies_requirements": ["req1", "req2"],
      "confidence": 0.9,
      "domain": "manufacturing"
    }
  }'
```

#### Method 3: Direct File Editing

1. **Edit the appropriate YAML file** in `src/config/rules/`:
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

2. **Reload the rules** (if editing files directly):
   - Rules are automatically reloaded when the server restarts
   - Or use the API/CLI to import the updated rules file
   - Or restart the matching service to reload rules

**Recommended Approach:**
- Use the API or CLI to create/update rules instead of editing files directly
- This ensures proper validation and immediate availability

### Adding New Domains

1. **Create a new YAML file** in `src/core/matching/capability_rules/`
2. **Follow the same structure** as existing domain files
3. **The system will automatically load** the new domain on initialization
