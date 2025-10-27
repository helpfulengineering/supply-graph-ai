# LLM Generation Layer

The LLM Generation Layer enhances OKH manifest generation by using Large Language Models to analyze project data and extract high-quality manifest fields.

## Overview

The LLM Generation Layer is the fourth layer in the 4-layer generation architecture:

1. **Direct Layer**: Extract metadata from platform APIs
2. **Heuristic Layer**: Pattern recognition and rule-based extraction
3. **NLP Layer**: Natural language processing for text analysis
4. **LLM Layer**: AI-powered analysis and generation ⭐

## Features

- **Context-Aware Analysis**: Understands project structure and content
- **Schema Compliance**: Generates OKH manifests that follow standards
- **Quality Scoring**: Provides confidence scores for generated content
- **Multi-Provider Support**: Works with Anthropic, OpenAI, Google, and local models
- **Cost Management**: Built-in cost tracking and optimization
- **Error Recovery**: Graceful handling of API failures

## Architecture

```
┌─────────────────┐
│   Project Data  │
│   (GitHub, etc) │
└─────────┬───────┘
          │
          ▼
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   Direct Layer  │    │ Heuristic Layer │    │    NLP Layer    │
│   (Platform)    │    │   (Patterns)    │    │   (Text NLP)    │
└─────────┬───────┘    └─────────┬───────┘    └─────────┬───────┘
          │                      │                      │
          └──────────────────────┼──────────────────────┘
                                 │
                    ┌─────────────┴─────────────┐
                    │     LLM Generation        │
                    │        Layer              │
                    │  (AI-Powered Analysis)    │
                    └─────────────┬─────────────┘
                                  │
                    ┌─────────────┴─────────────┐
                    │      LLM Service          │
                    │   (Provider Management)   │
                    └─────────────┬─────────────┘
                                  │
                    ┌─────────────┴─────────────┐
                    │    LLM Providers          │
                    │  Anthropic | OpenAI | ... │
                    └───────────────────────────┘
```

## Configuration

### Basic Configuration

```python
from src.core.generation.models import LayerConfig

# Enable LLM layer
config = LayerConfig(
    use_llm=True,
    llm_config={
        "provider": "anthropic",
        "model": "claude-3-5-sonnet-20241022",
        "max_tokens": 4000,
        "temperature": 0.1,
        "timeout": 60
    }
)
```

### Advanced Configuration

```python
from src.core.llm.service import LLMService, LLMServiceConfig
from src.core.llm.providers.base import LLMProviderType

# Create custom LLM service
llm_service_config = LLMServiceConfig(
    name="GenerationLLMService",
    default_provider=LLMProviderType.ANTHROPIC,
    default_model="claude-3-5-sonnet-20241022",
    max_retries=3,
    retry_delay=1.0,
    timeout=60,
    enable_fallback=True,
    max_cost_per_request=2.0,
    enable_cost_tracking=True
)

llm_service = LLMService("GenerationLLMService", llm_service_config)

# Create LLM layer with custom service
from src.core.generation.layers.llm import LLMGenerationLayer

llm_layer = LLMGenerationLayer(
    layer_config=config,
    llm_service=llm_service,
    preserve_context=True  # For debugging
)
```

## Usage

### Basic Usage

```python
from src.core.generation.engine import GenerationEngine
from src.core.generation.models import LayerConfig, ProjectData

# Create engine with LLM layer enabled
config = LayerConfig(use_llm=True)
engine = GenerationEngine(config)

# Generate manifest
project_data = ProjectData(
    platform=PlatformType.GITHUB,
    url="https://github.com/example/project",
    metadata={"name": "My Project", "description": "A cool project"},
    files=[...],
    documentation=[...]
)

manifest = await engine.generate_manifest_async(project_data)
```

### CLI Usage

```bash
# Generate OKH manifest with LLM
ome okh generate-from-url https://github.com/example/project --use-llm

# With specific provider
ome okh generate-from-url https://github.com/example/project \
  --llm-provider anthropic \
  --llm-model claude-3-5-sonnet-20241022

# Preserve context files for debugging
ome okh generate-from-url https://github.com/example/project \
  --use-llm \
  --preserve-context
```

### API Usage

```bash
# Generate OKH manifest via API
curl -X POST "https://your-domain.com/v1/api/okh/generate" \
  -H "Authorization: Bearer your_api_key" \
  -H "Content-Type: application/json" \
  -d '{
    "url": "https://github.com/example/project",
    "use_llm": true,
    "llm_config": {
      "provider": "anthropic",
      "model": "claude-3-5-sonnet-20241022"
    }
  }'
```

## Analysis Process

The LLM Generation Layer follows a structured analysis process:

### 1. Project Analysis
- **Repository Structure**: Analyze file organization and project layout
- **Content Extraction**: Extract key information from README, docs, and code
- **Technology Identification**: Identify programming languages, frameworks, and tools
- **Domain Classification**: Determine project domain (IoT, robotics, etc.)

### 2. Content Extraction
- **Metadata Extraction**: Extract name, version, description, and license
- **Manufacturing Analysis**: Identify manufacturing processes and materials
- **Documentation Review**: Analyze documentation quality and completeness
- **Dependency Mapping**: Identify software and hardware dependencies

### 3. Schema Mapping
- **Field Mapping**: Map extracted data to OKH schema fields
- **Validation**: Ensure all required fields are populated
- **Format Compliance**: Validate field formats and content types
- **Quality Assessment**: Generate confidence scores for each field

### 4. Manifest Generation
- **JSON Generation**: Create structured OKH manifest JSON
- **Confidence Scoring**: Assign confidence scores to each field
- **Error Handling**: Handle missing or invalid data gracefully
- **Context Preservation**: Save analysis context for debugging

## Generated Fields

The LLM layer can generate all OKH manifest fields:

### Required Fields
- **title**: Project name (confidence: 0.9-1.0)
- **version**: Version identifier (confidence: 0.7-0.9)
- **license**: License information (confidence: 0.8-0.9)
- **licensor**: License holder (confidence: 0.7-0.9)
- **documentation_language**: Language codes (confidence: 0.9-1.0)
- **function**: Functional description (confidence: 0.8-0.9)

### Optional Fields
- **description**: Detailed description (confidence: 0.8-1.0)
- **keywords**: Relevant tags (confidence: 0.8-0.9)
- **manufacturing_processes**: Manufacturing methods (confidence: 0.7-0.9)
- **materials**: Material specifications (confidence: 0.7-0.8)
- **manufacturing_specs**: Detailed specifications (confidence: 0.6-0.8)
- **parts**: Component specifications (confidence: 0.6-0.8)
- **software**: Software dependencies (confidence: 0.7-0.9)
- **standards_used**: Compliance standards (confidence: 0.5-0.7)

## Quality Metrics

The LLM layer provides comprehensive quality metrics:

### Confidence Scores
- **Field-Level**: Individual confidence scores for each field
- **Overall Quality**: Weighted average of all field scores
- **Completeness**: Percentage of required fields populated
- **Accuracy**: Estimated accuracy based on source quality

### Example Output
```json
{
  "manifest": {
    "title": "IoT Sensor Node",
    "version": "1.0.0",
    "license": {"hardware": "MIT", "documentation": "MIT", "software": "MIT"},
    "function": "Environmental monitoring sensor node",
    "description": "A low-power IoT sensor node...",
    "keywords": ["iot", "sensor", "environmental", "arduino"],
    "manufacturing_processes": ["3D printing", "PCB assembly", "soldering"],
    "materials": [
      {
        "material_id": "arduino_pro_mini",
        "name": "Arduino Pro Mini 3.3V",
        "quantity": 1,
        "unit": "piece"
      }
    ]
  },
  "confidence_scores": {
    "title": 1.0,
    "version": 0.7,
    "license": 0.9,
    "function": 0.9,
    "description": 1.0,
    "keywords": 0.9,
    "manufacturing_processes": 0.9,
    "materials": 0.8
  },
  "quality_metrics": {
    "overall_quality": 0.85,
    "completeness": 0.90,
    "accuracy": 0.80
  }
}
```

## Performance

### Processing Times
- **Small Projects**: 2-5 seconds
- **Medium Projects**: 5-10 seconds
- **Large Projects**: 10-20 seconds
- **Complex Projects**: 20-30 seconds

### Cost Analysis
- **Anthropic Claude**: ~$0.014 per request
- **OpenAI GPT-4**: ~$0.020 per request
- **Google Gemini**: ~$0.008 per request
- **Local Models**: $0.000 per request

### Token Usage
- **Input Tokens**: 1,000-3,000 tokens
- **Output Tokens**: 500-2,000 tokens
- **Total Tokens**: 1,500-5,000 tokens per request

## Error Handling

### Common Errors
- **API Failures**: Automatic fallback to alternative providers
- **Rate Limiting**: Exponential backoff and retry
- **Cost Limits**: Request rejection with clear error messages
- **Timeout**: Graceful degradation to other layers

### Fallback Behavior
```python
# LLM layer fails, fallback to NLP layer
if llm_layer_fails:
    result = nlp_layer.process(project_data)
    result.add_log("LLM layer failed, using NLP layer")
```

## Debugging

### Context Files
Enable context preservation for debugging:

```python
llm_layer = LLMGenerationLayer(
    layer_config=config,
    preserve_context=True  # Saves analysis context
)
```

Context files are saved in `temp_context/` directory and contain:
- Project analysis
- Field mapping progress
- LLM reasoning
- Generated manifest

### Logging
Enable debug logging:

```python
import logging
logging.getLogger("src.core.generation.layers.llm").setLevel(logging.DEBUG)
```

### Metrics
Monitor LLM performance:

```python
# Get layer metrics
metrics = llm_layer.get_metrics()
print(f"Total requests: {metrics.total_requests}")
print(f"Success rate: {metrics.success_rate}")
print(f"Average cost: ${metrics.average_cost:.4f}")
```

## Best Practices

### 1. Provider Selection
- **Anthropic Claude**: Best quality for hardware analysis
- **OpenAI GPT-4**: Good balance of quality and speed
- **Google Gemini**: Cost-effective alternative
- **Local Models**: For development and testing

### 2. Prompt Optimization
- Use clear, specific prompts
- Include relevant context
- Specify output format
- Set appropriate temperature

### 3. Cost Management
- Set reasonable cost limits
- Monitor usage patterns
- Use fallback providers
- Cache results when possible

### 4. Error Handling
- Implement proper error handling
- Use fallback mechanisms
- Log errors for debugging
- Provide user feedback

## Examples

### Complete Workflow

```python
from src.core.generation.engine import GenerationEngine
from src.core.generation.models import LayerConfig, ProjectData, PlatformType

# Configure with LLM layer
config = LayerConfig(
    use_llm=True,
    llm_config={
        "provider": "anthropic",
        "model": "claude-3-5-sonnet-20241022",
        "max_tokens": 4000,
        "temperature": 0.1
    }
)

# Create engine
engine = GenerationEngine(config)

# Generate manifest
project_data = ProjectData(
    platform=PlatformType.GITHUB,
    url="https://github.com/example/iot-sensor",
    metadata={
        "name": "IoT Sensor Node",
        "description": "Environmental monitoring sensor"
    },
    files=[...],
    documentation=[...]
)

manifest = await engine.generate_manifest_async(project_data)

# Check results
print(f"Generated fields: {len(manifest.generated_fields)}")
print(f"Overall quality: {manifest.quality_report.overall_quality}")
print(f"Missing required: {len(manifest.missing_fields)}")
```

### Custom Analysis

```python
from src.core.generation.layers.llm import LLMGenerationLayer

# Create custom LLM layer
llm_layer = LLMGenerationLayer(
    layer_config=config,
    preserve_context=True
)

# Process project data
result = await llm_layer.process(project_data)

# Analyze results
for field_name, field_gen in result.fields.items():
    print(f"{field_name}: {field_gen.value} (confidence: {field_gen.confidence:.2f})")
```

## Next Steps

- [Configuration](configuration.md) - Set up LLM providers
- [API Reference](api.md) - Learn about LLM API endpoints
- [CLI Commands](cli.md) - Use LLM features from command line
- [Examples](examples.md) - See practical usage examples
