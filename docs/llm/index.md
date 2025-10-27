# LLM Integration

The Open Matching Engine (OME) includes Large Language Model (LLM) integration for OKH manifest generation and facility matching. This section covers configuration, API endpoints, CLI commands, and usage examples.

## Overview

The LLM integration provides:

- **Multi-Provider Support**: Anthropic Claude, OpenAI GPT, Google Gemini, and local models
- **Intelligent Generation**: Enhanced OKH manifest generation with context-aware analysis
- **Smart Matching**: Improved facility matching using natural language understanding
- **Cost Management**: Built-in cost tracking and optimization
- **Fallback Mechanisms**: Automatic provider switching for reliability

## Quick Start

### 1. Configuration

Set your API keys in environment variables:

```bash
# Anthropic (recommended)
export ANTHROPIC_API_KEY="your_anthropic_key"

# OpenAI (alternative)
export OPENAI_API_KEY="your_openai_key"

# Google (alternative)
export GOOGLE_API_KEY="your_google_key"
```

### 2. Basic Usage

```bash
# Generate OKH manifest with LLM
ome okh generate-from-url https://github.com/example/project --use-llm

# Match facilities with LLM enhancement
ome match requirements --okh-file manifest.okh.json --use-llm
```

### 3. API Usage

```python
from src.core.llm.service import LLMService, LLMServiceConfig
from src.core.llm.providers.base import LLMProviderType

# Create LLM service
config = LLMServiceConfig(
    default_provider=LLMProviderType.ANTHROPIC,
    default_model="claude-3-5-sonnet-20241022"
)
llm_service = LLMService("MyService", config)
await llm_service.initialize()

# Generate content
response = await llm_service.generate(
    prompt="Analyze this hardware project...",
    request_type=LLMRequestType.GENERATION
)
```

## Documentation Sections

- [Configuration](configuration.md) - LLM provider setup and configuration
- [API Reference](api.md) - REST API endpoints for LLM operations
- [CLI Commands](cli.md) - Command-line interface for LLM features
- [Generation Layer](generation.md) - OKH manifest generation with LLM
- [Matching Layer](matching.md) - Facility matching with LLM enhancement
- [Examples](examples.md) - Usage examples and best practices

## Architecture

The LLM integration follows a modular architecture:

```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   Generation    │    │   Matching      │    │   API/CLI       │
│   Layer         │    │   Layer         │    │   Interface     │
└─────────┬───────┘    └─────────┬───────┘    └─────────┬───────┘
          │                      │                      │
          └──────────────────────┼──────────────────────┘
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

## Features

### Multi-Provider Support
- **Anthropic Claude**: High-quality analysis and generation
- **OpenAI GPT**: Fast and cost-effective processing
- **Google Gemini**: Alternative provider option
- **Local Models**: Ollama and other local LLM support

### Intelligent Processing
- **Context-Aware Analysis**: Understands project structure and content
- **Schema Compliance**: Generates OKH manifests that follow standards
- **Quality Scoring**: Provides confidence scores for generated content
- **Error Recovery**: Graceful handling of API failures

### Cost Management
- **Usage Tracking**: Monitor token usage and costs
- **Budget Controls**: Set limits on per-request costs
- **Provider Optimization**: Choose most cost-effective providers
- **Analytics**: Detailed usage reports and insights

## Getting Help

- **Documentation**: Browse the sections below for detailed information
- **Examples**: See [Examples](examples.md) for common use cases
- **API Reference**: Check [API Reference](api.md) for endpoint details
- **CLI Help**: Use `ome --help` for command-line assistance

## Next Steps

1. [Configure LLM providers](configuration.md)
2. [Try the CLI commands](cli.md)
3. [Explore the API](api.md)
4. [See examples](examples.md)
