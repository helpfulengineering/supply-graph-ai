# LLM API Reference

This document describes the REST API endpoints for LLM operations in the Open Matching Engine.

## Base URL

All LLM API endpoints are available under the `/v1/api/llm` prefix:

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
  "status": "healthy",
  "providers": {
    "anthropic": {
      "status": "active",
      "model": "claude-sonnet-4-5-20250929",
      "last_check": "2024-12-25T10:30:00Z"
    },
    "openai": {
      "status": "inactive",
      "error": "API key not configured"
    }
  },
  "metrics": {
    "total_requests": 150,
    "successful_requests": 148,
    "failed_requests": 2,
    "average_response_time": 2.5,
    "total_cost": 0.45
  }
}
```

### Generate Content

Generate content using the LLM service.

```http
POST /v1/api/llm/generate
```

**Request Body:**
```json
{
  "prompt": "Analyze this hardware project and generate an OKH manifest...",
  "request_type": "generation",
  "config": {
    "max_tokens": 4000,
    "temperature": 0.1,
    "timeout": 60
  },
  "provider": "anthropic",
  "model": "claude-sonnet-4-5-20250929"
}
```

**Response:**
```json
{
  "content": "Generated OKH manifest content...",
  "status": "success",
  "metadata": {
    "provider": "anthropic",
    "model": "claude-sonnet-4-5-20250929",
    "tokens_used": 1981,
    "cost": 0.0143,
    "processing_time": 8.12,
    "request_id": "req_123456789",
    "response_id": "resp_987654321",
    "created_at": "2024-12-25T10:30:00Z"
  }
}
```

### Generate OKH Manifest

Generate an OKH manifest for a hardware project.

```http
POST /v1/api/llm/generate-okh
```

**Request Body:**
```json
{
  "project_data": {
    "name": "IoT Sensor Node",
    "description": "A low-power IoT sensor node for environmental monitoring",
    "url": "https://github.com/example/iot-sensor",
    "files": [
      {
        "path": "README.md",
        "content": "# IoT Sensor Node\n\nA low-power...",
        "file_type": "text"
      }
    ],
    "metadata": {
      "language": "C++",
      "topics": ["iot", "sensor", "arduino"]
    }
  },
  "config": {
    "max_tokens": 4000,
    "temperature": 0.1,
    "timeout": 60
  }
}
```

**Response:**
```json
{
  "manifest": {
    "title": "IoT Sensor Node",
    "version": "1.0.0",
    "license": {
      "hardware": "MIT",
      "documentation": "MIT",
      "software": "MIT"
    },
    "licensor": "example/iot-sensor",
    "documentation_language": "en",
    "function": "Environmental monitoring sensor node",
    "description": "A low-power IoT sensor node designed for environmental monitoring applications...",
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
    "description": 1.0
  },
  "status": "success",
  "metadata": {
    "provider": "anthropic",
    "model": "claude-sonnet-4-5-20250929",
    "tokens_used": 1981,
    "cost": 0.0143,
    "processing_time": 8.12
  }
}
```

### Match Facilities

Use LLM to enhance facility matching.

```http
POST /v1/api/llm/match-facilities
```

**Request Body:**
```json
{
  "requirements": {
    "processes": ["3D printing", "laser cutting"],
    "materials": ["PLA", "acrylic"],
    "capabilities": ["rapid prototyping", "small batch production"]
  },
  "facilities": [
    {
      "name": "TechShop",
      "capabilities": ["3D printing", "laser cutting", "CNC machining"],
      "materials": ["PLA", "ABS", "acrylic", "wood"],
      "description": "Community makerspace with full fabrication capabilities"
    }
  ],
  "config": {
    "max_tokens": 2000,
    "temperature": 0.1,
    "timeout": 30
  }
}
```

**Response:**
```json
{
  "matches": [
    {
      "facility": "TechShop",
      "confidence": 0.85,
      "reasoning": "TechShop provides both required processes (3D printing, laser cutting) and materials (PLA, acrylic). The community makerspace model is ideal for small batch production and rapid prototyping.",
      "capabilities_used": ["3D printing", "laser cutting", "rapid prototyping"],
      "materials_available": ["PLA", "acrylic"],
      "match_type": "llm_enhanced"
    }
  ],
  "status": "success",
  "metadata": {
    "provider": "anthropic",
    "model": "claude-sonnet-4-5-20250929",
    "tokens_used": 1205,
    "cost": 0.0087,
    "processing_time": 4.23
  }
}
```

### Get Available Providers

List all configured LLM providers.

```http
GET /v1/api/llm/providers
```

**Response:**
```json
{
  "providers": [
    {
      "name": "anthropic",
      "type": "anthropic",
      "status": "active",
      "model": "claude-sonnet-4-5-20250929",
      "capabilities": ["generation", "matching", "analysis"],
      "cost_per_1k_tokens": 0.003
    },
    {
      "name": "openai",
      "type": "openai",
      "status": "inactive",
      "error": "API key not configured",
      "capabilities": ["generation", "matching", "analysis"],
      "cost_per_1k_tokens": 0.01
    }
  ],
  "default_provider": "anthropic"
}
```

### Get Service Metrics

Retrieve LLM service usage metrics and statistics.

```http
GET /v1/api/llm/metrics
```

**Response:**
```json
{
  "total_requests": 150,
  "successful_requests": 148,
  "failed_requests": 2,
  "success_rate": 0.987,
  "average_response_time": 2.5,
  "total_cost": 0.45,
  "average_cost_per_request": 0.003,
  "provider_usage": {
    "anthropic": {
      "requests": 120,
      "cost": 0.36,
      "average_response_time": 2.8
    },
    "openai": {
      "requests": 28,
      "cost": 0.09,
      "average_response_time": 1.9
    }
  },
  "request_history": [
    {
      "timestamp": "2024-12-25T10:30:00Z",
      "provider": "anthropic",
      "model": "claude-sonnet-4-5-20250929",
      "tokens_used": 1981,
      "cost": 0.0143,
      "status": "success"
    }
  ]
}
```

### Set Active Provider

Change the active LLM provider.

```http
POST /v1/api/llm/provider
```

**Request Body:**
```json
{
  "provider": "openai",
  "model": "gpt-4-turbo-preview"
}
```

**Response:**
```json
{
  "status": "success",
  "active_provider": "openai",
  "model": "gpt-4-turbo-preview",
  "message": "Provider changed successfully"
}
```

## Error Responses

All endpoints may return error responses in the following format:

```json
{
  "error": "Error message",
  "error_code": "ERROR_CODE",
  "status": "error",
  "details": {
    "field": "Additional error details"
  }
}
```

### Common Error Codes

| Code | Description | Solution |
|------|-------------|----------|
| `INVALID_REQUEST` | Request body is invalid | Check request format and required fields |
| `PROVIDER_UNAVAILABLE` | LLM provider is not available | Check provider configuration and API keys |
| `RATE_LIMITED` | API rate limit exceeded | Wait and retry, or switch providers |
| `COST_LIMIT_EXCEEDED` | Request cost exceeds limit | Increase cost limit or optimize prompt |
| `TIMEOUT` | Request timed out | Increase timeout or retry |
| `AUTHENTICATION_FAILED` | Invalid API key | Check authentication credentials |

## Rate Limiting

LLM endpoints are rate-limited to prevent abuse:

- **Default limit**: 100 requests per minute per API key
- **Burst limit**: 20 requests per second
- **Headers**: Rate limit information is included in response headers

```http
X-RateLimit-Limit: 100
X-RateLimit-Remaining: 95
X-RateLimit-Reset: 1640995200
```

## WebSocket Support

For real-time streaming responses, use WebSocket connections:

```javascript
const ws = new WebSocket('wss://your-domain.com/v1/api/llm/stream');

ws.onopen = function() {
  ws.send(JSON.stringify({
    prompt: "Generate OKH manifest...",
    request_type: "generation",
    stream: true
  }));
};

ws.onmessage = function(event) {
  const data = JSON.parse(event.data);
  console.log('Streaming response:', data.content);
};
```

## SDK Examples

### Python

```python
import requests

# Generate content
response = requests.post(
    'https://your-domain.com/v1/api/llm/generate',
    headers={'Authorization': 'Bearer your_api_key'},
    json={
        'prompt': 'Analyze this hardware project...',
        'request_type': 'generation',
        'config': {
            'max_tokens': 4000,
            'temperature': 0.1
        }
    }
)

result = response.json()
print(result['content'])
```

### JavaScript

```javascript
const response = await fetch('https://your-domain.com/v1/api/llm/generate', {
  method: 'POST',
  headers: {
    'Authorization': 'Bearer your_api_key',
    'Content-Type': 'application/json'
  },
  body: JSON.stringify({
    prompt: 'Analyze this hardware project...',
    request_type: 'generation',
    config: {
      max_tokens: 4000,
      temperature: 0.1
    }
  })
});

const result = await response.json();
console.log(result.content);
```

### cURL

```bash
curl -X POST "https://your-domain.com/v1/api/llm/generate" \
  -H "Authorization: Bearer your_api_key" \
  -H "Content-Type: application/json" \
  -d '{
    "prompt": "Analyze this hardware project...",
    "request_type": "generation",
    "config": {
      "max_tokens": 4000,
      "temperature": 0.1
    }
  }'
```

## Next Steps

- [CLI Commands](cli.md) - Use LLM features from command line
- [Configuration](configuration.md) - Set up LLM providers
- [Examples](examples.md) - See practical usage examples
