# LLM API Reference

This document describes the REST API endpoints for LLM operations in the Open Matching Engine.

## Overview

LLM functionality in OME is primarily integrated into domain-specific endpoints rather than exposed as standalone LLM endpoints. This design keeps LLM as an enhancement to core functionality rather than a separate service.

**LLM Integration Points:**
- **OKH Generation**: `POST /v1/api/okh/generate-from-url` - Uses LLM for intelligent file categorization
- **Matching**: `POST /v1/api/match` - Supports LLM-enhanced matching via `@llm_endpoint` decorator
- **Metrics**: `GET /v1/api/utility/metrics` - Includes LLM usage metrics and costs

**For Direct LLM Operations:**
Use the CLI commands for direct LLM access:
- `ome llm generate` - Generic content generation
- `ome llm generate-okh` - OKH manifest generation
- `ome llm providers info` - Provider information

## Base URL

LLM API endpoints are available under the `/v1/api/llm` prefix:

```
https://your-domain.com/v1/api/llm
```

## Authentication

LLM endpoints require authentication. Include your API key in the request headers:

```http
Authorization: Bearer your_api_key
```

## Endpoints

### Health Check

Check LLM service health and provider status.

```http
GET /v1/api/llm/health
```

**Response:**
```json
{
  "status": "success",
  "message": "LLM service health check completed",
  "timestamp": "2024-01-01T12:00:00Z",
  "health_status": "healthy",
  "providers": {
    "anthropic": {
      "name": "anthropic",
      "type": "anthropic",
      "status": "healthy",
      "model": "claude-sonnet-4-5-20250929",
      "is_connected": true,
      "available_models": ["claude-sonnet-4-5-20250929", "claude-3-5-sonnet-latest"]
    },
    "openai": {
      "name": "openai",
      "type": "openai",
      "status": "error",
      "error": "Provider not initialized"
    }
  },
  "metrics": {
    "total_requests": 150,
    "total_cost": 0.45,
    "average_cost_per_request": 0.003,
    "active_provider": "anthropic",
    "available_providers": ["anthropic"]
  }
}
```

**Status:**  **Fully Implemented** - LLM service health check with provider status

### Get Available Providers

List all configured LLM providers and their status.

```http
GET /v1/api/llm/providers
```

**Response:**
```json
{
  "status": "success",
  "message": "Providers retrieved successfully",
  "timestamp": "2024-01-01T12:00:00Z",
  "providers": [
    {
      "name": "anthropic",
      "type": "anthropic",
      "status": "healthy",
      "model": "claude-sonnet-4-5-20250929",
      "is_connected": true,
      "available_models": ["claude-sonnet-4-5-20250929", "claude-3-5-sonnet-latest"]
    },
    {
      "name": "openai",
      "type": "openai",
      "status": "not_available",
      "error": "Provider not initialized"
    }
  ],
  "default_provider": "anthropic",
  "available_providers": ["anthropic"]
}
```

**Status:**  **Fully Implemented** - Provider discovery and status information

## Error Responses

All LLM endpoints may return error responses in the following format:

```json
{
  "error": {
    "code": "error_code",
    "message": "Error message",
    "details": {
      "field": "Additional error details"
    },
    "request_id": "req_123456789"
  }
}
```

### Common Error Codes

| Code | Description | Solution |
|------|-------------|----------|
| `PROVIDER_UNAVAILABLE` | LLM provider is not available | Check provider configuration and API keys |
| `SERVICE_ERROR` | LLM service error | Check service logs and configuration |
| `AUTHENTICATION_FAILED` | Invalid API key | Check authentication credentials |

## Next Steps

- [CLI Commands](cli.md) - Use LLM features from command line
- [Configuration](../../llm/configuration.md) - Set up LLM providers
- [LLM Service Documentation](../../llm/llm-service.md) - Detailed LLM service information
