# Domain-Integrated Validation Framework

## Overview

The Open Matching Engine (OME) implements a comprehensive, domain-integrated validation framework that provides consistent, context-aware validation across all API operations. The framework integrates seamlessly with the existing domain management system and supports quality-level-based validation for different use cases.

## Architecture

### Validation Layers

The validation framework operates across four distinct layers:

```
┌─────────────────────────────────────────────────────────────┐
│                    API Layer                                │
│  ┌─────────────────┐  ┌─────────────────┐  ┌──────────────┐ │
│  │   File Upload   │  │   Request       │  │   Response   │ │
│  │   Validation    │  │   Validation    │  │   Validation │ │
│  └─────────────────┘  └─────────────────┘  └──────────────┘ │
└─────────────────────────────────────────────────────────────┘
┌─────────────────────────────────────────────────────────────┐
│                  Service Layer                              │
│  ┌─────────────────┐  ┌─────────────────┐  ┌──────────────┐ │
│  │   Business      │  │   Domain        │  │   Cross-     │ │
│  │   Rules         │  │   Rules         │  │   Field      │ │
│  └─────────────────┘  └─────────────────┘  └──────────────┘ │
└─────────────────────────────────────────────────────────────┘
┌─────────────────────────────────────────────────────────────┐
│                   Model Layer                               │
│  ┌─────────────────┐  ┌─────────────────┐  ┌──────────────┐ │
│  │   Schema        │  │   Type          │  │   Constraint │ │
│  │   Validation    │  │   Validation    │  │   Validation │ │
│  └─────────────────┘  └─────────────────┘  └──────────────┘ │
└─────────────────────────────────────────────────────────────┘
┌─────────────────────────────────────────────────────────────┐
│                  Storage Layer                              │
│  ┌─────────────────┐  ┌─────────────────┐  ┌──────────────┐ │
│  │   Data          │  │   Integrity     │  │   Consistency│ │
│  │   Integrity     │  │   Checks        │  │   Validation │ │
│  └─────────────────┘  └─────────────────┘  └──────────────┘ │
└─────────────────────────────────────────────────────────────┘
```

## Core Components

### 1. Validation Engine

The central validation engine coordinates validation across domains and types:

```python
from src.core.validation import ValidationEngine, ValidationContext

# Initialize validation engine
engine = ValidationEngine()

# Validate with domain context
context = ValidationContext(
    name="professional_okh_validation",
    domain="manufacturing",
    quality_level="professional"
)

result = await engine.validate(
    data=okh_manifest_data,
    validation_type="okh_manifest",
    context=context
)
```

### 2. Validation Context

Validation contexts integrate with the existing domain system and define quality levels:

```python
@dataclass
class ValidationContext:
    """Context for validation operations - integrates with existing domain system"""
    name: str
    domain: str  # Must be a registered domain from DomainRegistry
    quality_level: str  # 'hobby', 'professional', 'medical' for manufacturing
    strict_mode: bool = False
    custom_rules: Dict[str, Any] = field(default_factory=dict)
    
    def __post_init__(self):
        """Validate that domain exists in registry"""
        from src.core.registry.domain_registry import DomainRegistry
        if self.domain not in DomainRegistry.list_domains():
            raise ValueError(f"Domain '{self.domain}' is not registered")
    
    def get_domain_services(self):
        """Get domain services for this context"""
        return DomainRegistry.get_domain_services(self.domain)
```

### 3. Validation Results

Structured validation results with errors, warnings, and metadata:

```python
@dataclass
class ValidationResult:
    """Result of a validation operation"""
    valid: bool
    errors: List[ValidationError] = field(default_factory=list)
    warnings: List[ValidationWarning] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def add_error(self, message: str, field: Optional[str] = None, code: Optional[str] = None):
        """Add a validation error"""
        self.valid = False
        self.errors.append(ValidationError(message=message, field=field, code=code))
    
    def add_warning(self, message: str, field: Optional[str] = None, code: Optional[str] = None):
        """Add a validation warning"""
        self.warnings.append(ValidationWarning(message=message, field=field, code=code))
```

## Domain-Specific Validation

### Manufacturing Domain

The manufacturing domain supports three quality levels with different validation requirements:

#### Quality Levels

1. **Hobby** - Relaxed validation for personal projects
2. **Professional** - Standard validation for commercial use
3. **Medical** - Strict validation for medical device manufacturing

#### OKH Validation Rules

```python
# Hobby level - Basic requirements
hobby_okh_rules = {
    'required_fields': [
        'title', 'version', 'license', 'licensor', 
        'documentation_language', 'function'
    ],
    'optional_fields': [
        'description', 'keywords', 'manufacturing_processes', 
        'materials', 'tool_list'
    ],
    'validation_strictness': 'relaxed'
}

# Professional level - Enhanced requirements
professional_okh_rules = {
    'required_fields': [
        'title', 'version', 'license', 'licensor', 
        'documentation_language', 'function',
        'manufacturing_specs', 'manufacturing_processes', 
        'materials', 'tool_list'
    ],
    'optional_fields': [
        'description', 'keywords', 'quality_standards', 
        'certifications', 'regulatory_compliance'
    ],
    'validation_strictness': 'standard'
}

# Medical level - Strict requirements
medical_okh_rules = {
    'required_fields': [
        'title', 'version', 'license', 'licensor', 
        'documentation_language', 'function',
        'manufacturing_specs', 'quality_standards', 
        'certifications', 'regulatory_compliance',
        'traceability', 'testing_procedures',
        'manufacturing_processes', 'materials', 'tool_list'
    ],
    'optional_fields': [
        'description', 'keywords', 'cpc_patent_class', 'tsdc'
    ],
    'validation_strictness': 'strict'
}
```

#### OKW Validation Rules

```python
# Professional OKW facility validation
professional_okw_rules = {
    'required_fields': [
        'name', 'location', 'facility_status',
        'equipment', 'manufacturing_processes'
    ],
    'optional_fields': [
        'typical_materials', 'certifications', 'quality_standards'
    ],
    'equipment_validation': {
        'required_fields': ['name', 'type'],
        'optional_fields': ['specifications', 'location', 'materials_worked']
    },
    'process_validation': {
        'valid_processes': [
            'https://en.wikipedia.org/wiki/CNC_mill',
            'https://en.wikipedia.org/wiki/3D_printing',
            'https://en.wikipedia.org/wiki/CNC_lathe',
            'https://en.wikipedia.org/wiki/Laser_cutting',
            'https://en.wikipedia.org/wiki/Assembly'
        ]
    }
}
```

### Cooking Domain

The cooking domain supports three quality levels for recipe and kitchen validation:

#### Quality Levels

1. **Home** - Basic validation for home cooking
2. **Commercial** - Standard validation for commercial kitchens
3. **Professional** - Strict validation for professional culinary operations

#### Recipe Validation Rules

```python
# Home level - Basic recipe requirements
home_recipe_rules = {
    'required_fields': ['name', 'ingredients', 'instructions'],
    'optional_fields': ['description', 'cooking_time', 'servings'],
    'validation_strictness': 'relaxed'
}

# Commercial level - Enhanced requirements
commercial_recipe_rules = {
    'required_fields': [
        'name', 'ingredients', 'instructions',
        'cooking_time', 'servings'
    ],
    'optional_fields': [
        'description', 'nutritional_info', 'allergen_info'
    ],
    'validation_strictness': 'standard'
}

# Professional level - Strict requirements
professional_recipe_rules = {
    'required_fields': [
        'name', 'ingredients', 'instructions',
        'cooking_time', 'servings', 'nutritional_info'
    ],
    'optional_fields': [
        'description', 'allergen_info', 'food_safety_notes'
    ],
    'validation_strictness': 'strict'
}
```

## API Integration

### Validation Endpoints

The framework provides enhanced validation endpoints that support domain-aware validation:

#### OKH Validation

```bash
# Validate OKH manifest with professional quality level
curl -X POST "http://localhost:8001/v1/okh/validate" \
  -H "Content-Type: application/json" \
  -d '{
    "content": {
      "title": "Professional IoT Sensor Node",
      "version": "2.0.0",
      "license": {"hardware": "MIT", "documentation": "MIT", "software": "MIT"},
      "licensor": "Professional Hardware Corp",
      "documentation_language": "en",
      "function": "Industrial IoT sensor node for environmental monitoring",
      "manufacturing_processes": ["https://en.wikipedia.org/wiki/3D_printing"],
      "materials": [{"material_type": "https://en.wikipedia.org/wiki/PLA"}],
      "tool_list": ["3D printer"],
      "manufacturing_specs": {"tolerance": "0.1mm"}
    },
    "validation_context": "professional"
  }'
```

#### OKW Validation

```bash
# Validate OKW facility with professional quality level
curl -X POST "http://localhost:8001/v1/okw/validate" \
  -H "Content-Type: application/json" \
  -d '{
    "content": {
      "name": "Professional Manufacturing Facility",
      "location": {"address": "123 Industrial Blvd", "coordinates": {"lat": 40.7128, "lng": -74.0060}},
      "facility_status": "operational",
      "equipment": [
        {
          "name": "CNC Mill",
          "type": "machining",
          "specifications": {"max_workpiece_size": "500x300x200mm"}
        }
      ],
      "manufacturing_processes": ["https://en.wikipedia.org/wiki/CNC_mill"]
    },
    "validation_context": "professional"
  }'
```

### Response Format

Validation responses include structured error and warning information:

```json
{
  "valid": true,
  "normalized_content": { /* validated and normalized data */ },
  "completeness_score": 0.95,
  "issues": [
    {
      "severity": "warning",
      "message": "Optional field 'description' is missing, consider adding for better documentation",
      "path": ["description"],
      "code": "optional_field_missing"
    }
  ],
  "context": {
    "name": "professional_okh_validation",
    "domain": "manufacturing",
    "quality_level": "professional",
    "strict_mode": false
  },
  "metadata": {
    "completeness_score": 0.95,
    "validation_time_ms": 45
  }
}
```

## Validation Context Factory

The framework provides a factory for creating validation contexts:

```python
from src.core.validation import ValidationContextFactory

# Create context for manufacturing domain
context = ValidationContextFactory.create_context(
    domain_name="manufacturing",
    quality_level="professional",
    strict_mode=False
)

# Create context for cooking domain
cooking_context = ValidationContextFactory.create_context(
    domain_name="cooking",
    quality_level="home"
)

# Create context from domain detection
detected_context = ValidationContextFactory.create_context_from_detection(
    requirements=requirement_data,
    capabilities=capability_data,
    quality_level="professional"
)
```

## Domain Integration

### Integration with DomainRegistry

The validation framework integrates with the existing domain management system:

```python
# Validation context validates domain existence
context = ValidationContext(
    name="test",
    domain="manufacturing",  # Must be registered in DomainRegistry
    quality_level="professional"
)

# Access domain services through context
domain_services = context.get_domain_services()
domain_validator = context.get_domain_validator()
```

### Integration with DomainDetector

Automatic domain detection for validation context creation:

```python
# Detect domain from requirements and capabilities
detected_domain = DomainDetector.detect_and_validate_domain(
    requirements, capabilities
)

# Create validation context with detected domain
context = ValidationContextFactory.create_context(
    domain_name=detected_domain,
    quality_level="professional"
)
```

## Error Handling

### Standardized Error Responses

The framework provides consistent error response formats:

```json
{
  "error": {
    "code": "validation_failed",
    "message": "Validation failed for the provided data",
    "details": {
      "validation_type": "okh_manifest",
      "context": "manufacturing",
      "errors": [
        {
          "field": "manufacturing_specs",
          "code": "required_field_missing",
          "message": "Manufacturing specifications are required for professional quality level"
        }
      ],
      "warnings": [
        {
          "field": "description",
          "code": "optional_field_missing",
          "message": "Description is recommended for better documentation"
        }
      ]
    }
  }
}
```

### HTTP Status Code Mapping

- `400 Bad Request`: Input validation failures
- `422 Unprocessable Entity`: Business rule validation failures
- `409 Conflict`: Data integrity validation failures
- `413 Payload Too Large`: File size validation failures
- `415 Unsupported Media Type`: File type validation failures

## Testing

### Real Integration Testing

The framework includes comprehensive integration tests with real domain services:

```python
# Test manufacturing OKH validation with real data
async def test_manufacturing_okh_validator_with_real_data():
    validator = ManufacturingOKHValidator()
    
    # Test with complete professional OKH data
    complete_okh_data = {
        "title": "Professional IoT Sensor Node",
        "version": "2.0.0",
        "license": {"hardware": "MIT", "documentation": "MIT", "software": "MIT"},
        "licensor": "Professional Hardware Corp",
        "documentation_language": "en",
        "function": "Industrial IoT sensor node for environmental monitoring",
        "manufacturing_processes": ["https://en.wikipedia.org/wiki/3D_printing"],
        "materials": [{"material_type": "https://en.wikipedia.org/wiki/PLA"}],
        "tool_list": ["3D printer"],
        "manufacturing_specs": {"tolerance": "0.1mm"}
    }
    
    context = ValidationContext(
        name="test_professional",
        domain="manufacturing",
        quality_level="professional"
    )
    
    result = await validator.validate(complete_okh_data, context)
    assert result.valid is True
    assert result.metadata["completeness_score"] > 0.8
```

### Test Coverage

The framework includes tests for:

- **Unit Tests**: Individual validation components
- **Integration Tests**: Component interactions and data flow
- **End-to-End Tests**: Complete API workflows with real HTTP calls
- **Real Data Tests**: Validation with actual domain data
- **Edge Case Tests**: Boundary conditions and error scenarios

## Performance Considerations

### Validation Caching

The framework supports validation result caching for improved performance:

```python
# Configuration for validation caching
VALIDATION_CONFIG = ValidationConfig(
    enable_caching=True,
    cache_ttl=3600,  # 1 hour
    validation_timeout=30,  # 30 seconds
    max_validation_errors=100
)
```

### Async Operations

All validation operations are asynchronous for optimal performance:

```python
# Async validation operations
result = await validation_engine.validate(data, validation_type, context)
result = await validator.validate(data, context)
```

## Migration and Backward Compatibility

### Legacy Validation Infrastructure

The framework maintains backward compatibility with existing validation endpoints:

- All existing validation endpoints continue to work
- New framework provides enhanced functionality
- Gradual migration ensures no breaking changes
- Legacy validation code is preserved in staging directory

### Staging Strategy

Legacy validation files are staged during migration:

```
src/core/validation/staging/
├── README.md
├── validation_service_legacy.py
├── manufacturing_okh_validator_legacy.py
└── cooking_validators_legacy.py
```

## Future Extensions

### Planned Enhancements

1. **Advanced Validation Features**
   - Machine learning-based validation
   - Automated testing integration
   - Real-time validation monitoring
   - Predictive validation capabilities

2. **Context Management**
   - Dynamic context creation
   - Context version control
   - Context compatibility checking
   - Context optimization

3. **Integration Enhancements**
   - External standard integration
   - Certification system integration
   - Quality management integration
   - Compliance system integration

### Performance Optimizations

1. **Validation Caching**
   - Schema caching
   - Context caching
   - Result caching for identical data

2. **Lazy Validation**
   - Validate only when needed
   - Defer expensive validations
   - Use async validation where possible

3. **Batch Validation**
   - Validate multiple items together
   - Bulk validation for file uploads
   - Optimized database validation queries

## Best Practices

### 1. Context Definition
- Use appropriate quality levels for your use case
- Define clear validation criteria
- Implement robust validation procedures
- Document context requirements

### 2. Error Handling
- Provide clear, actionable error messages
- Use appropriate severity levels
- Consider blocking vs. non-blocking failures
- Document remediation paths

### 3. Performance
- Use async validation operations
- Enable caching for repeated validations
- Optimize validation procedures
- Monitor validation performance

### 4. Testing
- Test with real domain data
- Include edge cases and error scenarios
- Validate response formats
- Test integration with domain services

## Implementation Status

### ✅ Completed Features

- **Core Validation Framework**: Complete with domain integration
- **Manufacturing Domain Validation**: OKH and OKW validation with quality levels
- **Cooking Domain Validation**: Recipe and kitchen validation with quality levels
- **API Integration**: Enhanced validation endpoints with domain awareness
- **Real Integration Testing**: Comprehensive tests with actual domain services
- **Error Handling**: Standardized error responses and HTTP status codes
- **Performance**: Async operations and caching support

### 🔄 In Progress

- **Advanced Validation Features**: Machine learning and predictive validation
- **Context Management**: Dynamic context creation and version control
- **Integration Enhancements**: External standard and certification integration

### 📋 Future Plans

- **Performance Optimization**: Advanced caching and batch validation
- **Monitoring and Analytics**: Validation metrics and performance monitoring
- **Advanced Features**: Real-time validation and automated testing integration

---

**Last Updated**: December 2024  
**Status**: Production Ready - Core Framework Complete