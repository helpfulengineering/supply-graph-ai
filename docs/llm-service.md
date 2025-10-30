# LLM Service Documentation

## Overview

The LLM Service provides Large Language Model integration for the Open Matching Engine (OME), enabling sophisticated AI-powered generation and matching capabilities. The service supports multiple LLM providers and provides a unified interface for both API and CLI interactions.

## Features

- **Multi-Provider Support**: Anthropic, OpenAI, Google, Azure OpenAI, and local models
- **Unified Interface**: Consistent API across all providers
- **Cost Tracking**: Real-time cost monitoring and usage analytics
- **Fallback Mechanisms**: Automatic provider switching on failures
- **Context Management**: Temporary context files for debugging and analysis
- **Quality Control**: Output validation and confidence scoring

## Configuration

### Environment Variables

Create a `.env` file in the project root with your API keys:

```bash
# Anthropic (Claude models)
ANTHROPIC_API_KEY=sk-ant-api03-...

# OpenAI (GPT models)
OPENAI_API_KEY=sk-...

# Google (Gemini models)
GOOGLE_API_KEY=...

# Azure OpenAI
AZURE_OPENAI_API_KEY=...
AZURE_OPENAI_ENDPOINT=https://your-resource.openai.azure.com/

# LLM Configuration
LLM_ENABLED=true
LLM_DEFAULT_PROVIDER=anthropic
LLM_DEFAULT_MODEL=claude-3-5-sonnet-20241022
```

### Configuration File

You can also configure the LLM service using a JSON configuration file at `config/llm_config.json`:

```json
{
  "enabled": true,
  "default_provider": "anthropic",
  "default_model": "claude-3-5-sonnet-20241022",
  "fallback_enabled": true,
  "cost_tracking_enabled": true,
  "max_concurrent_requests": 10,
  "request_timeout_seconds": 60,
  "providers": {
    "anthropic": {
      "enabled": true,
      "timeout_seconds": 30,
      "max_retries": 3
    },
    "openai": {
      "enabled": false,
      "timeout_seconds": 30,
      "max_retries": 3
    }
  }
}
```

## API Usage

### Service Status

Check the LLM service status:

```bash
curl -X GET http://localhost:8001/v1/api/llm/status
```

Response:
```json
{
  "status": "active",
  "providers": {
    "anthropic": {
      "status": "connected",
      "model": "claude-3-5-sonnet-20241022",
      "available": true
    }
  },
  "metrics": {
    "total_requests": 42,
    "successful_requests": 40,
    "failed_requests": 2,
    "total_cost": 0.15,
    "average_response_time": 1.2
  }
}
```

### Text Generation

Generate text using the LLM service:

```bash
curl -X POST http://localhost:8001/v1/api/llm/generate \
  -H "Content-Type: application/json" \
  -d '{
    "prompt": "Explain the benefits of 3D printing in manufacturing",
    "max_tokens": 200,
    "temperature": 0.7,
    "provider": "anthropic",
    "model": "claude-3-5-sonnet-20241022"
  }'
```

Response:
```json
{
  "content": "3D printing offers several key benefits in manufacturing...",
  "status": "success",
  "metadata": {
    "provider": "anthropic",
    "model": "claude-3-5-sonnet-20241022",
    "tokens_used": 156,
    "cost": 0.0023,
    "processing_time": 1.1
  }
}
```

### OKH Manifest Generation

Generate an OKH manifest from a GitHub repository:

```bash
curl -X POST http://localhost:8001/v1/api/llm/generate-okh \
  -H "Content-Type: application/json" \
  -d '{
    "url": "https://github.com/example/project",
    "preserve_context": true,
    "quality_level": "high",
    "strict_mode": false
  }'
```

### Matching Analysis

Analyze matching between requirements and capabilities:

```bash
curl -X POST http://localhost:8001/v1/api/llm/match \
  -H "Content-Type: application/json" \
  -d '{
    "requirements": ["3D printing", "CNC machining"],
    "capabilities": ["3D printer", "CNC mill", "Laser cutter"],
    "domain": "manufacturing",
    "preserve_context": true
  }'
```

Response:
```json
{
  "matches": [
    {
      "requirement": "3D printing",
      "capability": "3D printer",
      "matched": true,
      "confidence": 0.95,
      "quality": "semantic_match",
      "method": "llm_capability_analysis_manufacturing",
      "reasons": ["Direct capability match for additive manufacturing process"]
    }
  ],
  "summary": {
    "total_requirements": 2,
    "total_capabilities": 3,
    "matches_found": 2,
    "average_confidence": 0.87
  }
}
```

## CLI Usage

### Basic Commands

#### Check LLM Service Status

```bash
# Check overall service status
ome llm service status

# Check specific provider status
ome llm providers status

# List available providers
ome llm providers list
```

#### Text Generation

```bash
# Generate text with default settings
ome llm generate "Explain the benefits of open-source hardware"

# Generate with specific parameters
ome llm generate "Create a manufacturing process description" \
  --max-tokens 300 \
  --temperature 0.3 \
  --provider anthropic \
  --model claude-3-5-sonnet-20241022
```

#### OKH Manifest Generation

```bash
# Generate OKH manifest from GitHub URL
ome llm generate-okh https://github.com/example/project

# Generate with context preservation
ome llm generate-okh https://github.com/example/project \
  --preserve-context \
  --quality-level high \
  --strict-mode

# Generate with specific LLM settings
ome llm generate-okh https://github.com/example/project \
  --provider anthropic \
  --model claude-3-5-sonnet-20241022 \
  --preserve-context
```

#### Matching Analysis

```bash
# Analyze matching between requirements and capabilities
ome llm match \
  --requirements "3D printing,CNC machining" \
  --capabilities "3D printer,CNC mill,Laser cutter" \
  --domain manufacturing \
  --preserve-context

# Match from file
ome llm match \
  --requirements-file requirements.txt \
  --capabilities-file capabilities.txt \
  --domain manufacturing
```

#### Provider Management

```bash
# Set default provider
ome llm providers set anthropic

# Test provider connection
ome llm providers test anthropic

# Check provider metrics
ome llm service metrics
```

### Advanced Usage

#### Context Preservation

When using `--preserve-context`, the LLM service creates temporary context files that can be examined for debugging:

```bash
# Generate with context preservation
ome llm generate-okh https://github.com/example/project --preserve-context

# Check context files
ls temp_generation_context/
# Output: context_20241201_143022.md
```

Context files contain:
- Full LLM prompts
- Generated responses
- Analysis steps
- Confidence scores
- Processing metadata

#### Quality Levels

Different quality levels affect the depth of analysis:

- `low`: Basic analysis, faster processing
- `medium`: Standard analysis (default)
- `high`: Complete analysis, slower processing

```bash
ome llm generate-okh https://github.com/example/project --quality-level high
```

#### Strict Mode

Strict mode enforces stricter validation and error handling:

```bash
ome llm generate-okh https://github.com/example/project --strict-mode
```

## Error Handling

### Common Errors

#### API Key Not Found
```
Error: ANTHROPIC_API_KEY not found in environment
```
**Solution**: Set the API key in your `.env` file or environment variables.

#### Provider Unavailable
```
Error: Provider 'anthropic' is not available
```
**Solution**: Check provider configuration and API key validity.

#### Rate Limit Exceeded
```
Error: Rate limit exceeded for provider 'anthropic'
```
**Solution**: Wait before retrying or switch to a different provider.

#### Model Not Found
```
Error: Model 'claude-3-5-sonnet-20241022' not found
```
**Solution**: Use a valid model name for the provider.

### Debugging

#### Enable Debug Logging

```bash
export LOG_LEVEL=DEBUG
ome llm generate "test prompt"
```

#### Check Service Health

```bash
ome llm service health
```

#### View Context Files

When using `--preserve-context`, examine the generated context files:

```bash
# List context files
ls temp_*_context/

# View a context file
cat temp_generation_context/context_20241201_143022.md
```

## Performance Optimization

### Concurrent Requests

The LLM service supports concurrent requests with configurable limits:

```bash
# Check current limits
ome llm service metrics

# Adjust limits in configuration
{
  "max_concurrent_requests": 5,
  "request_timeout_seconds": 30
}
```

### Cost Management

Monitor and control costs:

```bash
# Check current costs
ome llm service metrics

# Set cost limits
{
  "cost_tracking_enabled": true,
  "max_daily_cost": 10.0
}
```

### Response Caching

Enable response caching for repeated requests:

```bash
{
  "response_caching_enabled": true,
  "cache_ttl_seconds": 3600
}
```

## Integration Examples

### Python Integration

```python
from src.core.llm.service import LLMService
from src.core.llm.models.requests import LLMRequest, LLMRequestConfig, LLMRequestType

# Initialize service
llm_service = LLMService()
await llm_service.initialize()

# Create request
request = LLMRequest(
    prompt="Analyze this manufacturing process",
    request_type=LLMRequestType.ANALYSIS,
    config=LLMRequestConfig(max_tokens=200, temperature=0.1)
)

# Generate response
response = await llm_service.generate(request)
print(response.content)
```

### JavaScript Integration

```javascript
// Generate text
const response = await fetch('/v1/api/llm/generate', {
  method: 'POST',
  headers: {
    'Content-Type': 'application/json',
  },
  body: JSON.stringify({
    prompt: 'Explain 3D printing benefits',
    max_tokens: 200,
    temperature: 0.7
  })
});

const data = await response.json();
console.log(data.content);
```

## Best Practices

### Prompt Engineering

1. **Be Specific**: Provide clear, specific prompts
2. **Use Context**: Include relevant domain context
3. **Set Expectations**: Specify output format and length
4. **Iterate**: Test and refine prompts for better results

### Error Handling

1. **Check Status**: Always verify service status before making requests
2. **Handle Failures**: Implement retry logic for transient failures
3. **Monitor Costs**: Track usage to avoid unexpected charges
4. **Validate Outputs**: Always validate LLM responses before using them

### Performance

1. **Batch Requests**: Group related requests when possible
2. **Use Caching**: Enable caching for repeated requests
3. **Optimize Prompts**: Shorter prompts are faster and cheaper
4. **Monitor Metrics**: Track response times and success rates

## Troubleshooting

### Service Won't Start

1. Check API keys are set correctly
2. Verify provider configuration
3. Check network connectivity
4. Review error logs

### Poor Quality Results

1. Adjust temperature settings
2. Improve prompt quality
3. Use higher quality models
4. Enable strict mode for validation

### High Costs

1. Monitor usage patterns
2. Use cheaper models for simple tasks
3. Enable response caching
4. Set cost limits

### Slow Performance

1. Check network latency
2. Reduce concurrent requests
3. Use faster models
4. Optimize prompts

## Support

For additional support:

1. Check the logs: `logs/app.log`
2. Review context files when using `--preserve-context`
3. Test with simple prompts first
4. Verify configuration with `ome llm service status`

## Changelog

### Version 1.0.0 (December 2024)
- Initial LLM service implementation
- Anthropic provider support
- CLI integration
- Context file management
- Cost tracking and analytics
