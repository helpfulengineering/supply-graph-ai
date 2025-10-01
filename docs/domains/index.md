# Domain Management in Open Matching Engine

The Open Matching Engine (OME) supports multiple domains through a unified domain management system. This system enables the engine to operate across different domains (such as manufacturing and cooking) while maintaining consistent behavior and providing domain-specific functionality.

## Overview

The domain management system provides:

- **Multi-domain Support**: Seamless operation across different domains
- **Domain Detection**: Automatic detection of the appropriate domain from input data
- **Domain-specific Components**: Specialized extractors, matchers, and validators for each domain
- **Unified API**: Consistent interface regardless of the domain being used
- **Health Monitoring**: Real-time monitoring of domain system health

## Supported Domains

### Manufacturing Domain
- **Purpose**: Hardware production and manufacturing capability matching
- **Input Types**: `okh` (Open Know-How), `okw` (Open Know-Where)
- **Output Types**: `supply_tree`, `manufacturing_plan`
- **Components**: OKHExtractor, OKHMatcher, OKHValidator
- **Documentation**: [Manufacturing Domain Details](manufacturing.md)

### Cooking Domain
- **Purpose**: Recipe and kitchen capability matching
- **Input Types**: `recipe`, `kitchen`
- **Output Types**: `cooking_workflow`, `meal_plan`
- **Components**: CookingExtractor, CookingMatcher, CookingValidator
- **Documentation**: [Cooking Domain Details](cooking.md)

## Domain Detection

The system uses a multi-layered approach to detect the appropriate domain:

1. **Explicit Detection**: Uses domain attributes when explicitly provided
2. **Type-based Detection**: Maps input types to domains (e.g., "okh" → "manufacturing")
3. **Content Analysis**: Analyzes content for domain-specific keywords
4. **Fallback**: Uses single available domain when only one exists

## API Endpoints

### Domain Management
- `GET /v1/match/domains` - List all available domains
- `GET /v1/match/domains/{domain_name}` - Get domain details
- `GET /v1/match/domains/{domain_name}/health` - Domain health check
- `POST /v1/match/detect-domain` - Detect domain from input data

### Domain-aware Matching
- `POST /v1/match` - Match requirements to capabilities (domain-aware)
- `POST /v1/match/upload` - Match from uploaded files (domain-aware)

## Usage Examples

### List Available Domains
```bash
curl http://localhost:8001/v1/match/domains
```

### Get Domain Information
```bash
curl http://localhost:8001/v1/match/domains/manufacturing
```

### Detect Domain from Input
```bash
curl -X POST http://localhost:8001/v1/match/detect-domain \
  -H "Content-Type: application/json" \
  -d '{
    "requirements_data": {"type": "okh", "content": {"manufacturing_processes": ["CNC"]}},
    "capabilities_data": {"type": "okw", "content": {"equipment": ["CNC mill"]}}
  }'
```

### Domain-aware Matching
```bash
curl -X POST http://localhost:8001/v1/match \
  -H "Content-Type: application/json" \
  -d '{
    "okh_manifest": {
      "title": "CNC Bracket",
      "manufacturing_processes": ["CNC", "Deburring"],
      "license": {"hardware": "CERN-OHL-S-2.0"},
      "licensor": "Test Org",
      "documentation_language": "en",
      "function": "Precision bracket"
    }
  }'
```

## Adding New Domains

To add a new domain to the system:

1. **Create Domain Components**:
   - Extractor: Inherit from `BaseExtractor`
   - Matcher: Inherit from `BaseMatcher` (or implement matching interface)
   - Validator: Inherit from `BaseValidator` (or implement validation interface)

2. **Register Domain**:
   ```python
   from src.core.registry.domain_registry import DomainRegistry, DomainMetadata, DomainStatus
   
   metadata = DomainMetadata(
       name="new_domain",
       display_name="New Domain",
       description="Description of the new domain",
       version="1.0.0",
       status=DomainStatus.ACTIVE,
       supported_input_types={"input_type1", "input_type2"},
       supported_output_types={"output_type1", "output_type2"},
       documentation_url="https://docs.ome.org/domains/new_domain",
       maintainer="Your Team"
   )
   
   DomainRegistry.register_domain(
       domain_name="new_domain",
       extractor=NewDomainExtractor(),
       matcher=NewDomainMatcher(),
       validator=NewDomainValidator(),
       metadata=metadata
   )
   ```

3. **Update Configuration**:
   - Add domain configuration to `src/config/domains.py`
   - Update type mappings and keywords
   - Add domain-specific documentation

## Domain System Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                    Domain Management System                 │
├─────────────────────────────────────────────────────────────┤
│  ┌─────────────────┐  ┌─────────────────┐  ┌──────────────┐ │
│  │ Domain Registry │  │ Domain Detector │  │ Domain Config│ │
│  │                 │  │                 │  │              │ │
│  │ • Registration  │  │ • Multi-layer   │  │ • Metadata   │ │
│  │ • Service Mgmt  │  │   Detection     │  │ • Types      │ │
│  │ • Health Checks │  │ • Validation    │  │ • Keywords   │ │
│  │ • Type Mapping  │  │ • Confidence    │  │ • Mappings   │ │
│  └─────────────────┘  └─────────────────┘  └──────────────┘ │
├─────────────────────────────────────────────────────────────┤
│  ┌─────────────────┐  ┌─────────────────┐  ┌──────────────┐ │
│  │ Matching Service│  │ API Routes      │  │ Domain       │ │
│  │                 │  │                 │  │ Components   │ │
│  │ • Domain-aware  │  │ • Domain info   │  │ • Extractors │ │
│  │ • Service lookup│  │ • Health checks │  │ • Matchers   │ │
│  │ • Validation    │  │ • Detection     │  │ • Validators │ │
│  └─────────────────┘  └─────────────────┘  └──────────────┘ │
└─────────────────────────────────────────────────────────────┘
```

## Testing

The domain management system includes comprehensive tests:

```bash
# Run simple integration test
python test_domain_management_simple.py

# Run interactive demo
python test_domain_system.py

# Run full pytest suite (if pytest is installed)
pytest tests/test_domain_management_integration.py -v
```

## Best Practices

1. **Domain Consistency**: Ensure requirements and capabilities are from the same domain
2. **Type Validation**: Validate input types against domain capabilities
3. **Health Monitoring**: Regularly check domain system health
4. **Error Handling**: Handle domain detection failures gracefully
5. **Documentation**: Keep domain documentation up to date

## Troubleshooting

### Common Issues

1. **Domain Not Found**: Ensure the domain is properly registered
2. **Type Not Supported**: Check that the input type is supported by the domain
3. **Detection Failures**: Verify input data contains domain-specific keywords
4. **Health Check Failures**: Check that all domain components are properly initialized

### Debug Commands

```bash
# Check domain health
curl http://localhost:8001/v1/match/domains/manufacturing/health

# List all domains
curl http://localhost:8001/v1/match/domains

# Test domain detection
curl -X POST http://localhost:8001/v1/match/detect-domain \
  -H "Content-Type: application/json" \
  -d '{"requirements_data": {...}, "capabilities_data": {...}}'
```

## Future Enhancements

- **Cross-domain Matching**: Support for matching across different domains
- **Dynamic Domain Loading**: Loading domains from configuration files
- **Advanced Content Analysis**: NLP/ML-based domain detection
- **Domain Performance Metrics**: Monitoring and optimization
- **Domain-specific Validation Rules**: Custom validation for each domain