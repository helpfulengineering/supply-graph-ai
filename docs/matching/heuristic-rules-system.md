# Heuristic Rules System

## Overview

The Heuristic Rules System provides a modular, extensible framework for managing domain-specific matching rules in the Open Matching Engine (OME). This system replaces hardcoded heuristic rules with a configuration-driven approach that supports:

- **Domain Separation**: Rules are organized by domain (manufacturing, cooking, etc.)
- **Horizontal Extensibility**: Easy addition of new rules within existing domains
- **Vertical Extensibility**: Simple addition of new domains
- **Configuration Management**: Rules stored in external YAML/JSON files
- **Runtime Management**: Dynamic rule loading and reloading
- **Confidence Scoring**: Each rule includes confidence levels for match quality

## Architecture

### Core Components

```
┌─────────────────────────────────────────────────────────────┐
│                Heuristic Rules System                       │
├─────────────────────────────────────────────────────────────┤
│  ┌─────────────────┐  ┌─────────────────┐  ┌──────────────┐ │
│  │ HeuristicRule   │  │ HeuristicRuleSet│  │ HeuristicRule│ │
│  │                 │  │                 │  │ Manager      │ │
│  │ • Individual    │  │ • Domain        │  │ • Rule       │ │
│  │   rule          │  │   collection    │  │   loading    │ │
│  │ • Validation    │  │ • Rule          │  │ • Domain     │ │
│  │ • Matching      │  │   management    │  │   selection  │ │
│  │ • Serialization │  │ • Statistics    │  │ • Statistics │ │
│  └─────────────────┘  └─────────────────┘  └──────────────┘ │
├─────────────────────────────────────────────────────────────┤
│  ┌─────────────────┐  ┌─────────────────┐  ┌──────────────┐ │
│  │ HeuristicMatcher│  │ Domain-specific │  │ Rule         │ │
│  │                 │  │ Matchers        │  │ Configuration│ │
│  │ • Generic       │  │ • Manufacturing │  │ Files        │ │
│  │   matching      │  │ • Cooking       │  │ • YAML/JSON  │ │
│  │ • Domain-aware  │  │ • Extensible    │  │ • Versioned  │ │
│  │ • Confidence    │  │ • Specialized   │  │ • Validated  │ │
│  └─────────────────┘  └─────────────────┘  └──────────────┘ │
└─────────────────────────────────────────────────────────────┘
```

### Data Models

#### HeuristicRule
Individual matching rule with the following properties:

- **id**: Unique identifier for the rule
- **type**: Rule type (abbreviation, synonym, equivalent, substitution, normalization)
- **key**: Primary term or concept
- **values**: List of equivalent terms or concepts
- **direction**: Application direction (bidirectional, forward, reverse)
- **confidence**: Confidence score (0.0 to 1.0)
- **domain**: Target domain for the rule
- **description**: Human-readable description
- **source**: Source of the rule (standards, documentation, etc.)
- **tags**: Categorization tags for organization

#### HeuristicRuleSet
Collection of rules for a specific domain:

- **domain**: Target domain name
- **version**: Rule set version
- **description**: Domain description
- **rules**: Dictionary of rules by ID
- **metadata**: Additional domain-specific metadata

#### HeuristicRuleManager
Central manager for all rule sets:

- **Rule Loading**: Loads rules from configuration files
- **Domain Management**: Manages rule sets by domain
- **Matching Logic**: Finds applicable rules for text pairs
- **Statistics**: Provides rule usage and coverage statistics

## Rule Configuration

### File Structure

Rules are stored in YAML or JSON files in the `src/core/matching/rules/` directory:

```
src/core/matching/rules/
├── manufacturing.yaml    # Manufacturing domain rules
├── cooking.yaml         # Cooking domain rules
└── [domain].yaml        # Additional domain rules
```

### Rule File Format

```yaml
domain: manufacturing
version: "1.0.0"
description: "Heuristic matching rules for manufacturing and hardware production domain"

metadata:
  maintainer: "OME Manufacturing Team"
  last_updated: "2024-01-01"
  source: "Industry standards and manufacturing terminology"

rules:
  cnc_abbreviation:
    id: "cnc_abbreviation"
    type: "abbreviation"
    direction: "bidirectional"
    key: "cnc"
    values: ["computer numerical control", "computer numerical control machining", "cnc machining"]
    confidence: 0.95
    domain: "manufacturing"
    description: "Standard industry abbreviation for Computer Numerical Control"
    source: "ISO Manufacturing Terminology"
    tags: ["abbreviation", "machining", "automation"]
```

### Rule Types

#### Abbreviation
Expands abbreviations to full terms:
```yaml
type: "abbreviation"
key: "cnc"
values: ["computer numerical control", "computer numerical control machining"]
```

#### Synonym
Maps synonyms and equivalent terms:
```yaml
type: "synonym"
key: "additive manufacturing"
values: ["3d printing", "3-d printing", "rapid prototyping"]
```

#### Equivalent
Maps equivalent concepts or processes:
```yaml
type: "equivalent"
key: "stainless steel"
values: ["304 stainless", "316 stainless", "ss", "stainless"]
```

#### Substitution
Maps substitutable materials or components:
```yaml
type: "substitution"
key: "aluminum"
values: ["al", "aluminium", "aluminum alloy"]
```

#### Normalization
Maps variations to standardized forms:
```yaml
type: "normalization"
key: "sauté"
values: ["saute", "sauted", "sautéed", "pan-fry"]
```

### Rule Directions

#### Bidirectional (Default)
Rule applies in both directions:
- "cnc" ↔ "computer numerical control"
- "computer numerical control" ↔ "cnc"

#### Forward
Rule applies only from key to values:
- "cnc" → "computer numerical control" (but not reverse)

#### Reverse
Rule applies only from values to key:
- "computer numerical control" → "cnc" (but not reverse)

## Usage Examples

### Basic Rule Creation

```python
from src.core.matching.heuristic_rules import HeuristicRule, RuleType, RuleDirection

# Create a new rule
rule = HeuristicRule(
    id="cnc_rule",
    type=RuleType.ABBREVIATION,
    key="cnc",
    values=["computer numerical control", "cnc machining"],
    confidence=0.95,
    domain="manufacturing",
    description="CNC abbreviation expansion"
)

# Test rule application
assert rule.applies_to("cnc", "computer numerical control")
assert rule.applies_to("computer numerical control", "cnc")
```

### Rule Set Management

```python
from src.core.matching.heuristic_rules import HeuristicRuleSet

# Create rule set
rule_set = HeuristicRuleSet(domain="manufacturing")

# Add rules
rule_set.add_rule(rule)

# Find matching rules
matching_rules = rule_set.find_matching_rules("cnc", "computer numerical control")
best_match = rule_set.get_best_match("cnc", "computer numerical control")
```

### Rule Manager Usage

```python
from src.core.matching.heuristic_rules import HeuristicRuleManager

# Initialize manager
manager = HeuristicRuleManager()
await manager.initialize()

# Find matching rule
rule = manager.find_matching_rule("cnc", "computer numerical control", "manufacturing")

# Get confidence score
confidence = manager.get_rule_confidence("cnc", "computer numerical control", "manufacturing")

# Check if heuristic match exists
is_match = manager.is_heuristic_match("cnc", "computer numerical control", "manufacturing", 0.8)
```

### Heuristic Matcher Usage

```python
from src.core.matching.heuristic_matcher import get_heuristic_matcher

# Get domain-specific matcher
matcher = await get_heuristic_matcher("manufacturing")

# Perform matching
results = await matcher.match(
    "cnc",
    ["computer numerical control", "milling", "cnc machining"],
    "manufacturing"
)

# Check individual matches
is_match = await matcher.is_match("cnc", "computer numerical control", "manufacturing")
confidence = await matcher.get_confidence("cnc", "computer numerical control", "manufacturing")
```

## Domain-Specific Rules

### Manufacturing Domain

The manufacturing domain includes rules for:

- **Abbreviations**: CNC, CAD, CAM, FMS, etc.
- **Process Synonyms**: Additive manufacturing ↔ 3D printing
- **Material Synonyms**: Stainless steel variations, aluminum types
- **Tool Synonyms**: End mill variations, drill bit types
- **Equipment Synonyms**: Lathe types, mill variations
- **Quality Terms**: Precision, tolerance, surface finish

Example manufacturing rules:
```yaml
cnc_abbreviation:
  key: "cnc"
  values: ["computer numerical control", "computer numerical control machining"]
  confidence: 0.95

additive_manufacturing_synonyms:
  key: "additive manufacturing"
  values: ["3d printing", "3-d printing", "rapid prototyping"]
  confidence: 0.9

stainless_steel_synonyms:
  key: "stainless steel"
  values: ["304 stainless", "316 stainless", "ss", "stainless"]
  confidence: 0.85
```

### Cooking Domain

The cooking domain includes rules for:

- **Technique Synonyms**: Sauté variations, braising methods
- **Ingredient Synonyms**: Onion types, garlic variations
- **Equipment Synonyms**: Knife types, pan variations
- **Temperature Synonyms**: Heat level equivalents
- **Measurement Synonyms**: Teaspoon/tablespoon abbreviations
- **Preparation Methods**: Dicing, chopping, mincing variations

Example cooking rules:
```yaml
sauté_synonyms:
  key: "sauté"
  values: ["saute", "sauted", "sautéed", "pan-fry"]
  confidence: 0.95

onion_synonyms:
  key: "onion"
  values: ["yellow onion", "white onion", "sweet onion"]
  confidence: 0.9

teaspoon_synonyms:
  key: "teaspoon"
  values: ["tsp", "tsp.", "tea spoon"]
  confidence: 0.95
```

## Integration with Matching Service

The heuristic rules system is integrated into the MatchingService as Layer 2 of the multi-layered matching approach:

```python
# Layer 1: Direct Matching (exact and near-miss)
if self._direct_match(req_process, cap_process, domain="manufacturing"):
    return True

# Layer 2: Heuristic Matching (rule-based)
if await self._heuristic_match(req_process, cap_process, domain="manufacturing"):
    return True
```

The system automatically:
1. Loads domain-specific rules at startup
2. Selects appropriate rules based on the domain
3. Applies rules with confidence scoring
4. Falls back gracefully if rules are unavailable

## Adding New Domains

### 1. Create Rule Configuration File

Create a new YAML file in `src/core/matching/rules/`:

```yaml
# src/core/matching/rules/electronics.yaml
domain: electronics
version: "1.0.0"
description: "Heuristic matching rules for electronics and circuit design domain"

metadata:
  maintainer: "OME Electronics Team"
  last_updated: "2024-01-01"
  source: "Electronics industry standards"

rules:
  pcb_abbreviation:
    id: "pcb_abbreviation"
    type: "abbreviation"
    key: "pcb"
    values: ["printed circuit board", "circuit board"]
    confidence: 0.95
    domain: "electronics"
    description: "Standard abbreviation for Printed Circuit Board"
    tags: ["abbreviation", "circuit", "board"]
```

### 2. Create Domain-Specific Matcher (Optional)

```python
# src/core/domains/electronics/heuristic_matcher.py
from src.core.matching.heuristic_matcher import HeuristicMatcher

class ElectronicsHeuristicMatcher(HeuristicMatcher):
    def __init__(self, rule_manager=None):
        super().__init__(rule_manager)
        self.domain = "electronics"
    
    async def match(self, requirement, capabilities, min_confidence=0.7):
        return await super().match(requirement, capabilities, self.domain, min_confidence)
```

### 3. Update Domain Registry

Add the new domain to the domain registry with appropriate extractors, matchers, and validators.

## Performance Considerations

### Rule Loading
- Rules are loaded once at startup
- Configuration files are cached in memory
- Hot reloading available for development

### Matching Performance
- Rules are indexed by domain for fast lookup
- Confidence scoring is cached
- Fallback mechanisms prevent performance degradation

### Memory Usage
- Rules are stored efficiently in memory
- Domain separation prevents unnecessary rule loading
- Statistics tracking has minimal overhead

## Best Practices

### Rule Design
1. **Use Clear IDs**: Descriptive, unique rule identifiers
2. **Set Appropriate Confidence**: Match confidence to rule reliability
3. **Include Metadata**: Source, description, and tags for maintainability
4. **Test Rules**: Validate rules with test cases
5. **Version Control**: Track rule changes and versions

### Domain Organization
1. **Separate Concerns**: Keep domain rules separate
2. **Consistent Naming**: Use consistent naming conventions
3. **Documentation**: Document domain-specific terminology
4. **Validation**: Validate rule files before deployment

### Performance Optimization
1. **Confidence Thresholds**: Set appropriate minimum confidence levels
2. **Rule Prioritization**: Order rules by frequency of use
3. **Caching**: Leverage built-in caching mechanisms
4. **Monitoring**: Track rule usage and performance

## Troubleshooting

### Common Issues

#### Rules Not Loading
- Check file format (YAML/JSON syntax)
- Verify file location in rules directory
- Check domain name consistency

#### Low Match Rates
- Review confidence thresholds
- Check rule coverage for domain terminology
- Validate rule direction settings

#### Performance Issues
- Monitor rule set sizes
- Check for duplicate or conflicting rules
- Optimize confidence thresholds

### Debug Commands

```python
# Get rule statistics
stats = await matcher.get_rule_statistics()
print(f"Loaded {stats['total_rules']} rules across {stats['total_domains']} domains")

# Check available domains
domains = await matcher.get_available_domains()
print(f"Available domains: {domains}")

# Test specific rule
rule = manager.find_matching_rule("cnc", "computer numerical control", "manufacturing")
if rule:
    print(f"Found rule: {rule.id} with confidence {rule.confidence}")
```

## Future Enhancements

### Planned Features
- **Rule Learning**: Automatic rule generation from match data
- **Confidence Tuning**: Machine learning-based confidence optimization
- **Cross-Domain Rules**: Rules that apply across multiple domains
- **Rule Analytics**: Advanced usage and performance analytics
- **Dynamic Rule Updates**: Real-time rule updates without restart

### Extension Points
- **Custom Rule Types**: Support for domain-specific rule types
- **Rule Validation**: Advanced rule validation and testing
- **Performance Metrics**: Detailed performance monitoring
- **Rule Sharing**: Cross-project rule sharing and distribution

## API Reference

### HeuristicRuleManager

#### Methods
- `initialize()`: Load all rule sets from configuration files
- `get_rule_set(domain)`: Get rule set for specific domain
- `find_matching_rule(text1, text2, domain)`: Find best matching rule
- `get_rule_confidence(text1, text2, domain)`: Get confidence score
- `is_heuristic_match(text1, text2, domain, min_confidence)`: Check for match
- `get_rule_statistics()`: Get usage statistics
- `reload_rules()`: Reload rules from files

### HeuristicMatcher

#### Methods
- `match(requirement, capabilities, domain, min_confidence)`: Perform matching
- `is_match(requirement, capability, domain, min_confidence)`: Check single match
- `get_confidence(requirement, capability, domain)`: Get confidence score
- `get_available_domains()`: List available domains
- `get_rule_statistics()`: Get rule statistics
- `reload_rules()`: Reload all rules

### Domain-Specific Matchers

#### ManufacturingHeuristicMatcher
- Inherits from HeuristicMatcher
- Pre-configured for manufacturing domain
- Optimized for manufacturing terminology

#### CookingHeuristicMatcher
- Inherits from HeuristicMatcher
- Pre-configured for cooking domain
- Optimized for culinary terminology

## Conclusion

The Heuristic Rules System provides a robust, extensible foundation for domain-specific matching in the Open Matching Engine. By separating rules from code and providing comprehensive management capabilities, the system enables:

- **Rapid Domain Expansion**: Easy addition of new domains
- **Maintainable Rules**: Configuration-driven rule management
- **High Performance**: Optimized matching with confidence scoring
- **Flexible Architecture**: Support for various rule types and directions

This system forms the foundation for Layer 2 of the multi-layered matching approach, working in conjunction with Direct Matching (Layer 1) and future NLP (Layer 3) and AI/ML (Layer 4) matching layers.
