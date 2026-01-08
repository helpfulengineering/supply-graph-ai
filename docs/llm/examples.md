# LLM Examples

This document provides practical examples of using LLM features in the Open Hardware Manager.

## Quick Start Examples

### 1. Basic OKH Manifest Generation

Generate an OKH manifest for a hardware project:

```bash
# Generate manifest from GitHub URL
ome okh generate-from-url https://github.com/example/iot-sensor --use-llm

# With specific provider
ome okh generate-from-url https://github.com/example/project \
  --llm-provider anthropic \
  --llm-model claude-sonnet-4-5-20250929

# Save to specific file
ome okh generate-from-url https://github.com/example/project \
  --use-llm \
  --output my_manifest.okh.json
```

### 2. Facility Matching with LLM

Use LLM to enhance facility matching:

```bash
# Match requirements with facilities
ome llm match requirements.json facilities.json

# With confidence threshold
ome llm match requirements.json facilities.json \
  --min-confidence 0.7

# Save results
ome llm match requirements.json facilities.json \
  --output matches.json
```

### 3. Project Analysis

Analyze a hardware project:

```bash
# Basic analysis
ome llm analyze https://github.com/example/project

#  Analysis with code review
ome llm analyze https://github.com/example/project \
  --include-code \
  --include-docs \
  --output analysis.json

# Markdown report
ome llm analyze https://github.com/example/project \
  --output report.md \
  --format markdown
```

## Python Examples

### 1. Basic LLM Service Usage

```python
import asyncio
from src.core.llm.service import LLMService, LLMServiceConfig
from src.core.llm.providers.base import LLMProviderType
from src.core.llm.models.requests import LLMRequestConfig, LLMRequestType

async def basic_llm_example():
    """Basic LLM service usage"""
    
    # Create service configuration
    config = LLMServiceConfig(
        name="ExampleService",
        default_provider=LLMProviderType.ANTHROPIC,
        default_model="claude-sonnet-4-5-20250929",
        max_retries=3,
        retry_delay=1.0,
        timeout=60,
        enable_fallback=True,
        max_cost_per_request=2.0,
        enable_cost_tracking=True
    )
    
    # Create and initialize service
    llm_service = LLMService("ExampleService", config)
    await llm_service.initialize()
    
    # Generate content
    prompt = "Analyze this hardware project and generate an OKH manifest..."
    request_config = LLMRequestConfig(
        max_tokens=4000,
        temperature=0.1,
        timeout=60
    )
    
    response = await llm_service.generate(
        prompt=prompt,
        request_type=LLMRequestType.GENERATION,
        config=request_config
    )
    
    print(f"Generated content: {response.content}")
    print(f"Cost: ${response.cost:.4f}")
    print(f"Tokens used: {response.metadata.tokens_used}")
    
    # Clean up
    await llm_service.shutdown()

# Run the example
asyncio.run(basic_llm_example())
```

### 2. OKH Manifest Generation

```python
import asyncio
from src.core.generation.engine import GenerationEngine
from src.core.generation.models import LayerConfig, ProjectData, PlatformType, FileInfo

async def generate_okh_manifest():
    """Generate OKH manifest with LLM layer"""
    
    # Configure with LLM layer
    config = LayerConfig(
        use_llm=True,
        llm_config={
            "provider": "anthropic",
            "model": "claude-sonnet-4-5-20250929",
            "max_tokens": 4000,
            "temperature": 0.1
        }
    )
    
    # Create generation engine
    engine = GenerationEngine(config)
    
    # Create project data
    project_data = ProjectData(
        platform=PlatformType.GITHUB,
        url="https://github.com/example/iot-sensor",
        metadata={
            "name": "IoT Sensor Node",
            "description": "A low-power IoT sensor node for environmental monitoring",
            "language": "C++",
            "topics": ["iot", "sensor", "arduino", "environmental"]
        },
        files=[
            FileInfo(
                path="README.md",
                content="""# IoT Sensor Node

A low-power IoT sensor node designed for environmental monitoring applications.

## Features
- Temperature and humidity sensing
- WiFi connectivity
- Battery-powered operation
- Arduino compatible

## Hardware
- Arduino Pro Mini
- DHT22 sensor
- ESP8266 WiFi module
- 18650 battery

## Manufacturing
- 3D printed enclosure
- PCB assembly
- Electronic assembly
""",
                size=1000,
                file_type="text"
            )
        ],
        documentation=[],
        raw_content={}
    )
    
    # Generate manifest
    manifest = await engine.generate_manifest_async(project_data)
    
    # Display results
    print(f"Generated fields: {len(manifest.generated_fields)}")
    print(f"Overall quality: {manifest.quality_report.overall_quality}")
    print(f"Missing required: {len(manifest.missing_fields)}")
    
    # Show generated fields
    for field_name, field_gen in manifest.generated_fields.items():
        print(f"{field_name}: {field_gen.value} (confidence: {field_gen.confidence:.2f})")
    
    return manifest

# Run the example
asyncio.run(generate_okh_manifest())
```

### 3. Custom LLM Layer

```python
import asyncio
from src.core.generation.layers.llm import LLMGenerationLayer
from src.core.generation.models import LayerConfig, ProjectData, PlatformType, FileInfo

async def custom_llm_layer_example():
    """Custom LLM layer with context preservation"""
    
    # Create custom configuration
    config = LayerConfig(
        use_llm=True,
        llm_config={
            "provider": "anthropic",
            "model": "claude-sonnet-4-5-20250929",
            "max_tokens": 4000,
            "temperature": 0.1
        }
    )
    
    # Create LLM layer with context preservation
    llm_layer = LLMGenerationLayer(
        layer_config=config,
        preserve_context=True  # Save analysis context
    )
    
    # Create project data
    project_data = ProjectData(
        platform=PlatformType.GITHUB,
        url="https://github.com/example/smart-thermostat",
        metadata={
            "name": "Smart Thermostat",
            "description": "WiFi-enabled smart thermostat for home automation",
            "language": "C++",
            "topics": ["iot", "thermostat", "arduino", "smart-home"]
        },
        files=[
            FileInfo(
                path="README.md",
                content="""# Smart Thermostat

An open-source smart thermostat designed for home automation and energy efficiency.

## Features
- Temperature control
- WiFi connectivity
- Mobile app control
- Energy efficiency

## Hardware
- Arduino Uno
- DHT22 sensor
- Relay module
- ESP8266 WiFi module
- LCD display

## Manufacturing
- 3D printed enclosure
- PCB assembly
- Electronic assembly
""",
                size=1200,
                file_type="text"
            )
        ],
        documentation=[],
        raw_content={}
    )
    
    # Process with LLM layer
    result = await llm_layer.process(project_data)
    
    # Display results
    print(f"Processing time: {result.processing_time:.2f}s")
    print(f"Generated fields: {len(result.fields)}")
    print(f"Errors: {len(result.errors)}")
    
    # Show generated fields
    for field_name, field_gen in result.fields.items():
        print(f"{field_name}: {field_gen.value} (confidence: {field_gen.confidence:.2f})")
    
    # Show processing log
    for log_entry in result.processing_log:
        print(f"Log: {log_entry}")
    
    return result

# Run the example
asyncio.run(custom_llm_layer_example())
```

## API Examples

<!-- Temporarily removed: prior examples referenced non-existent /v1/api/llm endpoints. -->

## Advanced Examples

### 1. Batch Processing

```python
import asyncio
from src.core.generation.engine import GenerationEngine
from src.core.generation.models import LayerConfig, ProjectData, PlatformType

async def batch_processing_example():
    """Process multiple projects in batch"""
    
    # Configure engine
    config = LayerConfig(use_llm=True)
    engine = GenerationEngine(config)
    
    # List of projects to process
    projects = [
        "https://github.com/example/iot-sensor",
        "https://github.com/example/smart-thermostat",
        "https://github.com/example/robot-arm",
        "https://github.com/example/drone-controller"
    ]
    
    results = []
    
    for project_url in projects:
        try:
            print(f"Processing: {project_url}")
            
            # Create project data (simplified)
            project_data = ProjectData(
                platform=PlatformType.GITHUB,
                url=project_url,
                metadata={"name": "Project", "description": "Hardware project"},
                files=[],
                documentation=[],
                raw_content={}
            )
            
            # Generate manifest
            manifest = await engine.generate_manifest_async(project_data)
            
            # Store results
            results.append({
                "url": project_url,
                "fields": len(manifest.generated_fields),
                "quality": manifest.quality_report.overall_quality,
                "missing": len(manifest.missing_fields)
            })
            
            print(f"  Generated {len(manifest.generated_fields)} fields")
            print(f"  Quality: {manifest.quality_report.overall_quality:.2f}")
            
        except Exception as e:
            print(f"  Error: {e}")
            results.append({
                "url": project_url,
                "error": str(e)
            })
    
    # Summary
    print(f"\nBatch Processing Summary:")
    print(f"Total projects: {len(projects)}")
    print(f"Successful: {len([r for r in results if 'error' not in r])}")
    print(f"Failed: {len([r for r in results if 'error' in r])}")
    
    return results

# Run the example
asyncio.run(batch_processing_example())
```

### 2. Cost Monitoring

```python
import asyncio
from src.core.llm.service import LLMService, LLMServiceConfig
from src.core.llm.providers.base import LLMProviderType

async def cost_monitoring_example():
    """Monitor LLM service costs and usage"""
    
    # Create service with cost tracking
    config = LLMServiceConfig(
        name="CostMonitoringService",
        default_provider=LLMProviderType.ANTHROPIC,
        max_cost_per_request=1.0,  # $1.00 per request limit
        enable_cost_tracking=True
    )
    
    llm_service = LLMService("CostMonitoringService", config)
    await llm_service.initialize()
    
    # Make several requests
    prompts = [
        "Analyze this hardware project...",
        "Generate OKH manifest...",
        "Extract manufacturing processes...",
        "Identify materials used...",
        "Generate project description..."
    ]
    
    for i, prompt in enumerate(prompts):
        try:
            print(f"Request {i+1}: {prompt[:50]}...")
            
            response = await llm_service.generate(
                prompt=prompt,
                request_type=LLMRequestType.GENERATION
            )
            
            print(f"  Cost: ${response.cost:.4f}")
            print(f"  Tokens: {response.metadata.tokens_used}")
            
        except Exception as e:
            print(f"  Error: {e}")
    
    # Get service metrics
    metrics = await llm_service.get_service_metrics()
    
    print(f"\nService Metrics:")
    print(f"Total requests: {metrics.total_requests}")
    print(f"Successful requests: {metrics.successful_requests}")
    print(f"Failed requests: {metrics.failed_requests}")
    print(f"Total cost: ${metrics.total_cost:.4f}")
    print(f"Average cost per request: ${metrics.average_cost_per_request:.4f}")
    
    # Clean up
    await llm_service.shutdown()

# Run the example
asyncio.run(cost_monitoring_example())
```

### 3. Custom Provider

```python
import asyncio
from src.core.llm.providers.base import BaseLLMProvider, LLMProviderConfig, LLMProviderType
from src.core.llm.models.requests import LLMRequest, LLMRequestConfig
from src.core.llm.models.responses import LLMResponse, LLMResponseStatus, LLMResponseMetadata

class CustomLLMProvider(BaseLLMProvider):
    """Custom LLM provider example"""
    
    def __init__(self, config: LLMProviderConfig):
        super().__init__(config)
        self._connected = False
    
    async def connect(self) -> None:
        """Connect to custom LLM service"""
        # Implement connection logic
        self._connected = True
        self.logger.info("Connected to custom LLM service")
    
    async def disconnect(self) -> None:
        """Disconnect from custom LLM service"""
        self._connected = False
        self.logger.info("Disconnected from custom LLM service")
    
    async def generate(self, request: LLMRequest) -> LLMResponse:
        """Generate content using custom LLM service"""
        if not self._connected:
            raise RuntimeError("Provider not connected")
        
        # Implement custom LLM logic
        # This is a mock implementation
        content = f"Custom LLM response for: {request.prompt[:50]}..."
        
        metadata = LLMResponseMetadata(
            provider="custom",
            model=self.config.model,
            tokens_used=100,
            cost=0.001,
            processing_time=0.5
        )
        
        return LLMResponse(
            content=content,
            status=LLMResponseStatus.SUCCESS,
            metadata=metadata
        )
    
    async def health_check(self) -> bool:
        """Check provider health"""
        return self._connected
    
    def get_available_models(self) -> list:
        """Get available models"""
        return ["custom-model-1", "custom-model-2"]
    
    def estimate_cost(self, request: LLMRequest) -> float:
        """Estimate request cost"""
        return 0.001  # $0.001 per request

async def custom_provider_example():
    """Example using custom LLM provider"""
    
    # Create custom provider configuration
    config = LLMProviderConfig(
        provider_type=LLMProviderType.CUSTOM,
        api_key="custom_key",
        model="custom-model-1",
        timeout=60
    )
    
    # Create custom provider
    provider = CustomLLMProvider(config)
    await provider.connect()
    
    # Create request
    request = LLMRequest(
        prompt="Test custom provider",
        request_type=LLMRequestType.GENERATION,
        config=LLMRequestConfig(max_tokens=100, temperature=0.1)
    )
    
    # Generate response
    response = await provider.generate(request)
    
    print(f"Custom provider response: {response.content}")
    print(f"Cost: ${response.cost:.4f}")
    print(f"Status: {response.status}")
    
    # Clean up
    await provider.disconnect()

# Run the example
asyncio.run(custom_provider_example())
```

## Integration Examples

### 1. Flask Web Application

```python
from flask import Flask, request, jsonify
from src.core.llm.service import LLMService, LLMServiceConfig
from src.core.llm.providers.base import LLMProviderType

app = Flask(__name__)

# Initialize LLM service
llm_service = None

async def init_llm_service():
    global llm_service
    config = LLMServiceConfig(
        name="WebAppService",
        default_provider=LLMProviderType.ANTHROPIC,
        enable_cost_tracking=True
    )
    llm_service = LLMService("WebAppService", config)
    await llm_service.initialize()

@app.route('/api/generate', methods=['POST'])
async def generate_content():
    """Generate content endpoint"""
    data = request.get_json()
    
    try:
        response = await llm_service.generate(
            prompt=data['prompt'],
            request_type=data.get('request_type', 'generation')
        )
        
        return jsonify({
            'content': response.content,
            'cost': response.cost,
            'tokens_used': response.metadata.tokens_used,
            'status': 'success'
        })
    
    except Exception as e:
        return jsonify({
            'error': str(e),
            'status': 'error'
        }), 500

@app.route('/api/metrics', methods=['GET'])
async def get_metrics():
    """Get service metrics endpoint"""
    try:
        metrics = await llm_service.get_service_metrics()
        return jsonify({
            'total_requests': metrics.total_requests,
            'total_cost': metrics.total_cost,
            'success_rate': metrics.success_rate,
            'status': 'success'
        })
    
    except Exception as e:
        return jsonify({
            'error': str(e),
            'status': 'error'
        }), 500

if __name__ == '__main__':
    # Initialize LLM service
    asyncio.run(init_llm_service())
    
    # Start Flask app
    app.run(debug=True)
```

### 2. Django Integration

```python
# views.py
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods
import asyncio
from src.core.llm.service import LLMService, LLMServiceConfig
from src.core.llm.providers.base import LLMProviderType

# Global LLM service
llm_service = None

async def init_llm_service():
    global llm_service
    config = LLMServiceConfig(
        name="DjangoService",
        default_provider=LLMProviderType.ANTHROPIC
    )
    llm_service = LLMService("DjangoService", config)
    await llm_service.initialize()

@csrf_exempt
@require_http_methods(["POST"])
def generate_content(request):
    """Generate content view"""
    data = request.json
    
    try:
        # Run async function in sync context
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        
        response = loop.run_until_complete(
            llm_service.generate(
                prompt=data['prompt'],
                request_type=data.get('request_type', 'generation')
            )
        )
        
        return JsonResponse({
            'content': response.content,
            'cost': response.cost,
            'status': 'success'
        })
    
    except Exception as e:
        return JsonResponse({
            'error': str(e),
            'status': 'error'
        }, status=500)

# Initialize LLM service on startup
asyncio.run(init_llm_service())
```

## Next Steps

- [Configuration](configuration.md) - Set up LLM providers
- [API Reference](api.md) - Learn about LLM API endpoints
- [CLI Commands](cli.md) - Use LLM features from command line
- [Generation Layer](generation.md) - Understand OKH manifest generation
