# Python API

The OME Python API provides a direct interface for Python applications to interact with the matching engine without going through HTTP.

## Installation

### For development (from the repository root)
```bash
pip install -e .
```

### Basic Usage
```python
from ome.client import MatchingEngine

# Initialize the engine
engine = MatchingEngine()

# Match requirements to capabilities

result = engine.match(
    requirements={
        "content": {
            "title": "Example Recipe",
            "ingredients": ["flour", "water", "salt"],
            "instructions": ["Mix ingredients", "Knead dough", "Bake"]
        },
        "domain": "cooking",
        "type": "recipe"
    },
    capabilities={
        "content": {
            "name": "Home Kitchen",
            "tools": ["mixing bowl", "oven", "knife"],
            "ingredients": ["flour", "water", "salt", "sugar"]
        },
        "domain": "cooking",
        "type": "kitchen"
    }
)
```

## Access the Supply Tree
```python
supply_tree = result.supply_tree

# Check validation status
is_valid = result.validation_status

# Get confidence score
confidence = result.confidence
```

## Key Classes

### MatchingEngine
The main entry point for the Python API.

```python
class MatchingEngine:
    def match(self, requirements, capabilities):
        """Match requirements to capabilities and generate a Supply Tree."""
        # ...
        
    def register_domain(self, domain, extractor, matcher, validator):
        """Register a new domain with its components."""
        # ...
        
    def validate(self, supply_tree, context=None):
        """Validate a Supply Tree in a specific context."""
        # ...
```

### SupplyTree
Represents a complete solution matching requirements to capabilities.

```python
class SupplyTree:
    def add_workflow(self, workflow):
        """Add a workflow to the Supply Tree."""
        # ...
        
    def connect_workflows(self, connection):
        """Connect two workflows."""
        # ...
        
    def validate(self, context=None):
        """Validate the Supply Tree in a specific context."""
        # ...
        
    def to_dict(self):
        """Convert to dictionary representation."""
        # ...
        
    @classmethod
    def from_dict(cls, data):
        """Create from dictionary representation."""
        # ...
```

## Advanced Usage

### Custom Domain Registration

```python
from ome.client import MatchingEngine
from my_domain.extractors import MyDomainExtractor
from my_domain.matchers import MyDomainMatcher
from my_domain.validators import MyDomainValidator

# Initialize the engine
engine = MatchingEngine()

# Register a custom domain
engine.register_domain(
    domain="my_domain",
    extractor=MyDomainExtractor(),
    matcher=MyDomainMatcher(),
    validator=MyDomainValidator()
)

# Use the custom domain
result = engine.match(
    requirements={
        "content": {...},
        "domain": "my_domain",
        "type": "my_requirements"
    },
    capabilities={
        "content": {...},
        "domain": "my_domain",
        "type": "my_capabilities"
    }
)
```

### Custom Validation Contexts
```python
from ome.client import ValidationContext

# Define a custom validation context
medical_context = ValidationContext(
    domain="medical_devices",
    standards=["ISO_13485", "ASTM_F899"],
    acceptance_criteria={...},
    validation_procedures={...}
)

# Validate using the custom context
validation_result = engine.validate(
    supply_tree=my_supply_tree,
    context=medical_context
)
```