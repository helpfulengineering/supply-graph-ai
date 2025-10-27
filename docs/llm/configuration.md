# LLM Configuration

This guide covers how to configure LLM providers, set up API keys, and customize LLM behavior in the Open Matching Engine. The system includes intelligent provider selection that automatically chooses the best available provider.

## Provider Selection System

The LLM integration includes an intelligent provider selection system that automatically chooses the best available provider based on configuration priority:

### Selection Priority

1. **Command Line Flags** (highest priority)
2. **Environment Variables** 
3. **Auto-Detection** (based on available API keys)
4. **Default Fallback** (lowest priority)

### Quick Setup

The simplest way to get started is to set your API keys and let the system auto-detect:

```bash
# Set your preferred API key
export ANTHROPIC_API_KEY="sk-ant-api03-..."

# Optional: Set default provider and model
export LLM_PROVIDER="anthropic"
export LLM_MODEL="claude-3-5-sonnet-20241022"

# Use LLM commands - provider will be automatically selected
ome llm generate "Hello world"
```

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

# Local Ollama (optional - for local models)
export OLLAMA_BASE_URL="http://localhost:11434"
```

### Provider Selection Variables

```bash
# Default provider (anthropic, openai, google, azure_openai, local)
export LLM_PROVIDER="anthropic"

# Default model for the provider
export LLM_MODEL="claude-3-5-sonnet-20241022"
```

### Optional Configuration

```bash
# Cost limits
export LLM_MAX_COST_PER_REQUEST="2.0"

# Timeout settings
export LLM_TIMEOUT="60"

# Enable/disable LLM features
export LLM_ENABLED="true"
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

### Automatic Provider Selection (Recommended)

The easiest way to use the LLM service is with automatic provider selection:

```python
from src.core.llm.provider_selection import create_llm_service_with_selection

# Create service with automatic provider selection
llm_service = await create_llm_service_with_selection()

# Generate content
response = await llm_service.generate(
    prompt="Analyze this hardware project...",
    config=LLMRequestConfig(max_tokens=4000)
)

print(f"Generated by: {response.metadata.provider}")
print(f"Model: {response.metadata.model}")
print(f"Cost: ${response.metadata.cost:.6f}")
```

### Manual Provider Selection

You can also specify a provider manually:

```python
from src.core.llm.provider_selection import create_llm_service_with_selection

# Specify provider via CLI-style parameters
llm_service = await create_llm_service_with_selection(
    cli_provider="anthropic",
    cli_model="claude-3-5-sonnet-20241022"
)

# Or use environment variables
import os
os.environ["LLM_PROVIDER"] = "openai"
os.environ["LLM_MODEL"] = "gpt-3.5-turbo"

llm_service = await create_llm_service_with_selection()
```

### Advanced Service Configuration

For advanced use cases, you can still configure the service manually:

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
    max_cost_per_request=2.0,
    enable_cost_tracking=True,
    max_concurrent_requests=10
)

# Create and initialize service
llm_service = LLMService("MyLLMService", service_config)
await llm_service.initialize()
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

## Provider Status and Information

### Check Available Providers

Use the CLI command to see which providers are available:

```bash
ome llm providers info
```

This will show:
- ✅ Available providers with API keys set
- ❌ Unavailable providers (missing API keys)
- Default models for each provider
- Environment variable names

### Provider Selection Examples

**Environment Variable Configuration:**
```bash
# Set default provider
export LLM_PROVIDER=anthropic
export LLM_MODEL=claude-3-5-sonnet-20241022

# Use LLM commands
ome llm generate "Hello world"
```

**CLI Flag Override:**
```bash
# Override environment variables
ome llm generate "Hello world" --provider openai --model gpt-3.5-turbo
```

**Auto-Detection (No Configuration):**
```bash
# System automatically selects best available provider
ome llm generate "Hello world"
```

### Provider Selection Logic

The system selects providers in this order:

1. **Command Line Flags** - `--provider` and `--model` flags
2. **Environment Variables** - `LLM_PROVIDER` and `LLM_MODEL`
3. **Auto-Detection** - Based on available API keys:
   - Anthropic Claude (if `ANTHROPIC_API_KEY` set)
   - OpenAI GPT (if `OPENAI_API_KEY` set)
   - Local Ollama (if service running)
4. **Default Fallback** - Uses first available provider

## Troubleshooting

### Common Issues

**1. No Providers Available**
```bash
Error: No LLM providers are available
```
**Solution:** Set at least one API key:
```bash
export ANTHROPIC_API_KEY="your_key_here"
```

**2. Provider Not Available**
```bash
Warning: CLI provider 'openai' not available, falling back to other options
```
**Solution:** Check that the provider's API key is set:
```bash
export OPENAI_API_KEY="your_key_here"
```

**3. Invalid Provider Name**
```bash
Warning: Invalid CLI provider 'invalid_provider', falling back to other options
```
**Solution:** Use valid provider names: `anthropic`, `openai`, `google`, `azure_openai`, `local`

**4. API Key Not Found**
```bash
Error: ANTHROPIC_API_KEY not found in environment
```
**Solution:** Set the environment variable or add it to your configuration file.

**5. Rate Limiting**
```bash
Error: Rate limit exceeded
```
**Solution:** Implement retry logic or switch to a different provider.

**6. Cost Limit Exceeded**
```bash
Error: Cost limit exceeded for request
```
**Solution:** Increase the cost limit or optimize your prompts.

### Debug Mode

Enable debug logging to see provider selection details:

```python
import logging
logging.getLogger("src.core.llm").setLevel(logging.DEBUG)
```

### Health Checks

```python
from src.core.llm.provider_selection import get_provider_selector

# Check provider information
selector = get_provider_selector()
info = selector.get_provider_info()
print(f"Available providers: {info['available_providers']}")
print(f"Unavailable providers: {info['unavailable_providers']}")

# Test provider selection
selection = selector.select_provider(verbose=True)
print(f"Selected provider: {selection['provider']}")
print(f"Strategy: {selection['strategy']}")
print(f"Reason: {selection['reason']}")
```


## Next Steps

- [API Reference](api.md) - Learn about LLM API endpoints
- [CLI Commands](cli.md) - Use LLM features from command line
- [Examples](examples.md) - See practical usage examples

## Quick Reference

### Environment Variables
```bash
# Required API Keys
export ANTHROPIC_API_KEY="your_key"     # Anthropic Claude
export OPENAI_API_KEY="your_key"        # OpenAI GPT
export GOOGLE_API_KEY="your_key"        # Google Gemini

# Optional Provider Selection
export LLM_PROVIDER="anthropic"         # Default provider
export LLM_MODEL="claude-3-5-sonnet-20241022"  # Default model
```

### CLI Commands
```bash
# Check provider status
ome llm providers info

# Generate with automatic provider selection
ome llm generate "Hello world"

# Override provider
ome llm generate "Hello world" --provider openai

# Generate OKH manifest
ome llm generate-okh https://github.com/user/project
```

### Python API
```python
from src.core.llm.provider_selection import create_llm_service_with_selection

# Automatic provider selection
service = await create_llm_service_with_selection()
response = await service.generate("Hello world")
```
