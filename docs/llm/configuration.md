# LLM Configuration

This guide covers how to configure LLM providers, set up API keys, and customize LLM behavior in the Open Matching Engine.

## Environment Variables

### Required API Keys

Set the appropriate API key for your chosen provider:

```bash
# Anthropic Claude (recommended)
export ANTHROPIC_API_KEY="sk-ant-api03-..."

# OpenAI GPT
export OPENAI_API_KEY="sk-..."

# Google Gemini
export GOOGLE_API_KEY="AIza..."

# Azure OpenAI
export AZURE_OPENAI_API_KEY="your_azure_key"
export AZURE_OPENAI_ENDPOINT="https://your-resource.openai.azure.com/"
```

### Optional Configuration

```bash
# Default provider (anthropic, openai, google, azure, local)
export OME_LLM_DEFAULT_PROVIDER="anthropic"

# Default model
export OME_LLM_DEFAULT_MODEL="claude-3-5-sonnet-20241022"

# Cost limits
export OME_LLM_MAX_COST_PER_REQUEST="2.0"

# Timeout settings
export OME_LLM_TIMEOUT="60"
```

## Configuration Files

### YAML Configuration

Create `config/llm_config.yaml`:

```yaml
llm:
  default_provider: "anthropic"
  default_model: "claude-3-5-sonnet-20241022"
  timeout: 60
  max_retries: 3
  retry_delay: 1.0
  enable_fallback: true
  max_cost_per_request: 2.0
  enable_cost_tracking: true
  max_concurrent_requests: 10
  request_queue_size: 100
  
  providers:
    anthropic:
      api_key: "${ANTHROPIC_API_KEY}"
      model: "claude-3-5-sonnet-20241022"
      base_url: null
      timeout: 60
      max_tokens: 4000
      temperature: 0.1
      
    openai:
      api_key: "${OPENAI_API_KEY}"
      model: "gpt-4-turbo-preview"
      base_url: null
      timeout: 60
      max_tokens: 4000
      temperature: 0.1
      
    google:
      api_key: "${GOOGLE_API_KEY}"
      model: "gemini-pro"
      base_url: null
      timeout: 60
      max_tokens: 4000
      temperature: 0.1
      
    local:
      api_key: null
      model: "llama2:7b"
      base_url: "http://localhost:11434"
      timeout: 120
      max_tokens: 2000
      temperature: 0.1
```

### JSON Configuration

Create `config/llm_config.json`:

```json
{
  "llm": {
    "default_provider": "anthropic",
    "default_model": "claude-3-5-sonnet-20241022",
    "timeout": 60,
    "max_retries": 3,
    "retry_delay": 1.0,
    "enable_fallback": true,
    "max_cost_per_request": 2.0,
    "enable_cost_tracking": true,
    "max_concurrent_requests": 10,
    "request_queue_size": 100,
    "providers": {
      "anthropic": {
        "api_key": "${ANTHROPIC_API_KEY}",
        "model": "claude-3-5-sonnet-20241022",
        "base_url": null,
        "timeout": 60,
        "max_tokens": 4000,
        "temperature": 0.1
      },
      "openai": {
        "api_key": "${OPENAI_API_KEY}",
        "model": "gpt-4-turbo-preview",
        "base_url": null,
        "timeout": 60,
        "max_tokens": 4000,
        "temperature": 0.1
      }
    }
  }
}
```

## Provider-Specific Configuration

### Anthropic Claude

```python
from src.core.llm.providers.anthropic import AnthropicProvider
from src.core.llm.providers.base import LLMProviderConfig

config = LLMProviderConfig(
    provider_type=LLMProviderType.ANTHROPIC,
    api_key="your_anthropic_key",
    model="claude-3-5-sonnet-20241022",
    base_url=None,  # Use default Anthropic API
    timeout=60,
    max_tokens=4000,
    temperature=0.1
)

provider = AnthropicProvider(config)
```

**Available Models:**
- `claude-3-5-sonnet-20241022` (recommended)
- `claude-3-5-haiku-20241022` (faster, cheaper)
- `claude-3-opus-20240229` (most capable)

### OpenAI GPT

```python
from src.core.llm.providers.openai import OpenAIProvider

config = LLMProviderConfig(
    provider_type=LLMProviderType.OPENAI,
    api_key="your_openai_key",
    model="gpt-4-turbo-preview",
    base_url=None,  # Use default OpenAI API
    timeout=60,
    max_tokens=4000,
    temperature=0.1
)

provider = OpenAIProvider(config)
```

**Available Models:**
- `gpt-4-turbo-preview` (recommended)
- `gpt-4` (stable)
- `gpt-3.5-turbo` (faster, cheaper)

### Google Gemini

```python
from src.core.llm.providers.google import GoogleProvider

config = LLMProviderConfig(
    provider_type=LLMProviderType.GOOGLE,
    api_key="your_google_key",
    model="gemini-pro",
    base_url=None,  # Use default Google API
    timeout=60,
    max_tokens=4000,
    temperature=0.1
)

provider = GoogleProvider(config)
```

**Available Models:**
- `gemini-pro` (recommended)
- `gemini-pro-vision` (with image support)

### Local Models (Ollama)

```python
from src.core.llm.providers.local import LocalProvider

config = LLMProviderConfig(
    provider_type=LLMProviderType.LOCAL,
    api_key=None,  # Not needed for local models
    model="llama2:7b",
    base_url="http://localhost:11434",  # Ollama default
    timeout=120,  # Longer timeout for local models
    max_tokens=2000,
    temperature=0.1
)

provider = LocalProvider(config)
```

**Available Models:**
- `llama2:7b` (recommended)
- `llama2:13b` (more capable)
- `codellama:7b` (code-focused)
- `mistral:7b` (alternative)

## Service Configuration

### Basic Service Setup

```python
from src.core.llm.service import LLMService, LLMServiceConfig
from src.core.llm.providers.base import LLMProviderType

# Create service configuration
service_config = LLMServiceConfig(
    name="MyLLMService",
    default_provider=LLMProviderType.ANTHROPIC,
    default_model="claude-3-5-sonnet-20241022",
    max_retries=3,
    retry_delay=1.0,
    timeout=60,
    enable_fallback=True,
    fallback_providers=[
        LLMProviderType.ANTHROPIC,
        LLMProviderType.OPENAI,
        LLMProviderType.GOOGLE
    ],
    max_cost_per_request=2.0,
    enable_cost_tracking=True,
    max_concurrent_requests=10,
    request_queue_size=100
)

# Create and initialize service
llm_service = LLMService("MyLLMService", service_config)
await llm_service.initialize()
```

### Advanced Configuration

```python
# Custom provider configuration
providers = {
    "anthropic": LLMProviderConfig(
        provider_type=LLMProviderType.ANTHROPIC,
        api_key="your_key",
        model="claude-3-5-sonnet-20241022",
        timeout=60,
        max_tokens=4000,
        temperature=0.1
    ),
    "openai": LLMProviderConfig(
        provider_type=LLMProviderType.OPENAI,
        api_key="your_key",
        model="gpt-4-turbo-preview",
        timeout=60,
        max_tokens=4000,
        temperature=0.1
    )
}

service_config = LLMServiceConfig(
    name="AdvancedLLMService",
    default_provider=LLMProviderType.ANTHROPIC,
    providers=providers,
    enable_fallback=True,
    max_cost_per_request=5.0,
    enable_cost_tracking=True
)
```

## Layer Configuration

### Generation Layer

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

### Matching Layer

```python
from src.core.matching.models import MatchingConfig

# Enable LLM layer for matching
config = MatchingConfig(
    use_llm=True,
    llm_config={
        "provider": "anthropic",
        "model": "claude-3-5-sonnet-20241022",
        "max_tokens": 2000,
        "temperature": 0.1,
        "timeout": 30
    }
)
```

## Cost Management

### Setting Cost Limits

```python
# Per-request cost limit
service_config = LLMServiceConfig(
    max_cost_per_request=1.0,  # $1.00 per request
    enable_cost_tracking=True
)

# Monitor costs
metrics = await llm_service.get_service_metrics()
print(f"Total cost: ${metrics.total_cost:.4f}")
print(f"Average cost per request: ${metrics.average_cost_per_request:.4f}")
```

### Provider Cost Comparison

| Provider | Model | Cost per 1K tokens | Speed | Quality |
|----------|-------|-------------------|-------|---------|
| Anthropic | Claude-3.5-Sonnet | $0.003 | Medium | High |
| Anthropic | Claude-3.5-Haiku | $0.00025 | Fast | Good |
| OpenAI | GPT-4-Turbo | $0.01 | Medium | High |
| OpenAI | GPT-3.5-Turbo | $0.0005 | Fast | Good |
| Google | Gemini-Pro | $0.0005 | Fast | Good |
| Local | Llama2-7B | $0.00 | Slow | Medium |

## Troubleshooting

### Common Issues

**1. API Key Not Found**
```bash
Error: ANTHROPIC_API_KEY not found in environment
```
**Solution:** Set the environment variable or add it to your configuration file.

**2. Provider Not Available**
```bash
Error: Provider 'openai' not available
```
**Solution:** Check that the provider is properly configured and the API key is valid.

**3. Rate Limiting**
```bash
Error: Rate limit exceeded
```
**Solution:** Implement retry logic or switch to a different provider.

**4. Cost Limit Exceeded**
```bash
Error: Cost limit exceeded for request
```
**Solution:** Increase the cost limit or optimize your prompts.

### Debug Mode

Enable debug logging:

```python
import logging
logging.getLogger("src.core.llm").setLevel(logging.DEBUG)
```

### Health Checks

```python
# Check provider health
status = await llm_service.get_provider_status()
print(f"Provider status: {status}")

# Test connection
health = await llm_service.health_check()
print(f"Service health: {health}")
```


## Next Steps

- [API Reference](api.md) - Learn about LLM API endpoints
- [CLI Commands](cli.md) - Use LLM features from command line
- [Examples](examples.md) - See practical usage examples
