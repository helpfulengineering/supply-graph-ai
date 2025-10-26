# LLM CLI Commands

This document describes the command-line interface for LLM operations in the Open Matching Engine.

## Overview

The LLM CLI provides easy access to LLM features through the `ome` command-line tool. All LLM commands are prefixed with `llm` and support various options for configuration and output formatting.

## Basic Usage

```bash
# Show LLM help
ome llm --help

# Show specific command help
ome llm generate --help
ome llm match --help
```

## Commands

### Generate Content

Generate content using the LLM service.

```bash
ome llm generate [OPTIONS] PROMPT
```

**Options:**
- `--provider TEXT`: LLM provider (anthropic, openai, google, local)
- `--model TEXT`: Model name (e.g., claude-3-5-sonnet-20241022)
- `--max-tokens INTEGER`: Maximum tokens to generate (default: 4000)
- `--temperature FLOAT`: Sampling temperature (default: 0.1)
- `--timeout INTEGER`: Request timeout in seconds (default: 60)
- `--output FILE`: Output file (default: stdout)
- `--format TEXT`: Output format (json, text, yaml) (default: text)

**Examples:**

```bash
# Basic generation
ome llm generate "Analyze this hardware project and generate an OKH manifest"

# With specific provider and model
ome llm generate "Generate OKH manifest" \
  --provider anthropic \
  --model claude-3-5-sonnet-20241022

# Save to file with JSON format
ome llm generate "Analyze project" \
  --output manifest.json \
  --format json

# High temperature for creative output
ome llm generate "Suggest improvements" \
  --temperature 0.7 \
  --max-tokens 2000
```

### Generate OKH Manifest

Generate an OKH manifest for a hardware project.

```bash
ome llm generate-okh [OPTIONS] PROJECT_URL
```

**Options:**
- `--provider TEXT`: LLM provider (anthropic, openai, google, local)
- `--model TEXT`: Model name
- `--max-tokens INTEGER`: Maximum tokens to generate
- `--temperature FLOAT`: Sampling temperature
- `--timeout INTEGER`: Request timeout in seconds
- `--output FILE`: Output file (default: manifest.okh.json)
- `--format TEXT`: Output format (json, yaml, toml)
- `--preserve-context`: Preserve context files for debugging
- `--clone`: Clone repository locally for analysis

**Examples:**

```bash
# Generate from GitHub URL
ome llm generate-okh https://github.com/example/iot-sensor

# With specific provider
ome llm generate-okh https://github.com/example/project \
  --provider anthropic \
  --model claude-3-5-sonnet-20241022

# Clone repository for better analysis
ome llm generate-okh https://github.com/example/project \
  --clone \
  --preserve-context

# Save in different format
ome llm generate-okh https://github.com/example/project \
  --output manifest.yaml \
  --format yaml
```

### Match Facilities

Use LLM to enhance facility matching.

```bash
ome llm match [OPTIONS] REQUIREMENTS_FILE FACILITIES_FILE
```

**Options:**
- `--provider TEXT`: LLM provider
- `--model TEXT`: Model name
- `--max-tokens INTEGER`: Maximum tokens to generate
- `--temperature FLOAT`: Sampling temperature
- `--timeout INTEGER`: Request timeout in seconds
- `--output FILE`: Output file (default: stdout)
- `--format TEXT`: Output format (json, yaml, table)
- `--min-confidence FLOAT`: Minimum confidence threshold (default: 0.5)

**Examples:**

```bash
# Match requirements with facilities
ome llm match requirements.json facilities.json

# With confidence threshold
ome llm match requirements.json facilities.json \
  --min-confidence 0.7 \
  --output matches.json

# Table format output
ome llm match requirements.json facilities.json \
  --format table \
  --min-confidence 0.6
```

### Analyze Project

Analyze a hardware project and extract information.

```bash
ome llm analyze [OPTIONS] PROJECT_URL
```

**Options:**
- `--provider TEXT`: LLM provider
- `--model TEXT`: Model name
- `--max-tokens INTEGER`: Maximum tokens to generate
- `--temperature FLOAT`: Sampling temperature
- `--timeout INTEGER`: Request timeout in seconds
- `--output FILE`: Output file (default: stdout)
- `--format TEXT`: Output format (json, yaml, markdown)
- `--include-code`: Include code analysis
- `--include-docs`: Include documentation analysis

**Examples:**

```bash
# Basic project analysis
ome llm analyze https://github.com/example/project

# Comprehensive analysis
ome llm analyze https://github.com/example/project \
  --include-code \
  --include-docs \
  --output analysis.json \
  --format json

# Markdown report
ome llm analyze https://github.com/example/project \
  --output report.md \
  --format markdown
```

### Provider Management

Manage LLM providers and configuration.

```bash
ome llm providers [COMMAND]
```

**Subcommands:**
- `list`: List available providers
- `status`: Show provider status
- `set`: Set active provider
- `test`: Test provider connection

**Examples:**

```bash
# List all providers
ome llm providers list

# Show provider status
ome llm providers status

# Set active provider
ome llm providers set anthropic

# Test provider connection
ome llm providers test anthropic
```

### Service Management

Manage LLM service and metrics.

```bash
ome llm service [COMMAND]
```

**Subcommands:**
- `status`: Show service status
- `metrics`: Show usage metrics
- `health`: Check service health
- `reset`: Reset service state

**Examples:**

```bash
# Show service status
ome llm service status

# Show usage metrics
ome llm service metrics

# Check health
ome llm service health

# Reset service
ome llm service reset
```

## Configuration

### Environment Variables

Set LLM configuration via environment variables:

```bash
# API Keys
export ANTHROPIC_API_KEY="your_anthropic_key"
export OPENAI_API_KEY="your_openai_key"
export GOOGLE_API_KEY="your_google_key"

# Default settings
export OME_LLM_DEFAULT_PROVIDER="anthropic"
export OME_LLM_DEFAULT_MODEL="claude-3-5-sonnet-20241022"
export OME_LLM_MAX_COST_PER_REQUEST="2.0"
export OME_LLM_TIMEOUT="60"
```

### Configuration File

Create `~/.ome/llm_config.yaml`:

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
  
  providers:
    anthropic:
      api_key: "${ANTHROPIC_API_KEY}"
      model: "claude-3-5-sonnet-20241022"
      timeout: 60
      max_tokens: 4000
      temperature: 0.1
      
    openai:
      api_key: "${OPENAI_API_KEY}"
      model: "gpt-4-turbo-preview"
      timeout: 60
      max_tokens: 4000
      temperature: 0.1
```

## Output Formats

### JSON Format

```bash
ome llm generate "Analyze project" --format json
```

```json
{
  "content": "Generated content...",
  "status": "success",
  "metadata": {
    "provider": "anthropic",
    "model": "claude-3-5-sonnet-20241022",
    "tokens_used": 1981,
    "cost": 0.0143,
    "processing_time": 8.12
  }
}
```

### YAML Format

```bash
ome llm generate "Analyze project" --format yaml
```

```yaml
content: "Generated content..."
status: "success"
metadata:
  provider: "anthropic"
  model: "claude-3-5-sonnet-20241022"
  tokens_used: 1981
  cost: 0.0143
  processing_time: 8.12
```

### Table Format

```bash
ome llm match requirements.json facilities.json --format table
```

```
┌─────────────┬──────────────┬─────────────┬─────────────────────────────┐
│ Facility    │ Confidence   │ Match Type  │ Reasoning                   │
├─────────────┼──────────────┼─────────────┼─────────────────────────────┤
│ TechShop    │ 0.85         │ llm_enhanced│ Provides both required      │
│             │              │             │ processes and materials     │
├─────────────┼──────────────┼─────────────┼─────────────────────────────┤
│ FabLab      │ 0.72         │ llm_enhanced│ Good match for rapid        │
│             │              │             │ prototyping needs           │
└─────────────┴──────────────┴─────────────┴─────────────────────────────┘
```

## Examples

### Complete Workflow

```bash
# 1. Analyze a project
ome llm analyze https://github.com/example/iot-sensor \
  --output project_analysis.json \
  --format json

# 2. Generate OKH manifest
ome llm generate-okh https://github.com/example/iot-sensor \
  --output manifest.okh.json \
  --preserve-context

# 3. Match facilities
ome llm match requirements.json facilities.json \
  --output matches.json \
  --min-confidence 0.7

# 4. Check service metrics
ome llm service metrics
```

### Batch Processing

```bash
# Process multiple projects
for project in project1 project2 project3; do
  ome llm generate-okh "https://github.com/example/$project" \
    --output "manifests/${project}.okh.json"
done

# Generate reports
ome llm analyze https://github.com/example/project1 \
  --output reports/project1_analysis.md \
  --format markdown
```

### Development Workflow

```bash
# Test with local model
ome llm generate "Test prompt" \
  --provider local \
  --model llama2:7b \
  --timeout 120

# Debug with context preservation
ome llm generate-okh https://github.com/example/project \
  --preserve-context \
  --output debug_manifest.json

# Check provider status
ome llm providers status
```

## Error Handling

### Common Errors

**1. API Key Not Found**
```bash
Error: ANTHROPIC_API_KEY not found in environment
```
**Solution:** Set the environment variable or configuration file.

**2. Provider Not Available**
```bash
Error: Provider 'openai' not available
```
**Solution:** Check provider configuration and API keys.

**3. Rate Limiting**
```bash
Error: Rate limit exceeded. Try again later.
```
**Solution:** Wait and retry, or switch providers.

**4. Cost Limit Exceeded**
```bash
Error: Cost limit exceeded for request
```
**Solution:** Increase cost limit or optimize prompt.

### Debug Mode

Enable debug output:

```bash
# Set debug level
export OME_LOG_LEVEL=DEBUG

# Run command with verbose output
ome llm generate "Test prompt" --verbose
```

### Troubleshooting

```bash
# Check service health
ome llm service health

# Test provider connection
ome llm providers test anthropic

# Show detailed metrics
ome llm service metrics --detailed

# Reset service state
ome llm service reset
```

## Integration Examples

### Shell Scripts

```bash
#!/bin/bash
# Generate OKH manifest with error handling

PROJECT_URL="$1"
OUTPUT_FILE="${2:-manifest.okh.json}"

if [ -z "$PROJECT_URL" ]; then
  echo "Usage: $0 <project_url> [output_file]"
  exit 1
fi

echo "Generating OKH manifest for: $PROJECT_URL"

if ome llm generate-okh "$PROJECT_URL" --output "$OUTPUT_FILE"; then
  echo "✅ Manifest generated successfully: $OUTPUT_FILE"
else
  echo "❌ Failed to generate manifest"
  exit 1
fi
```

### Python Integration

```python
import subprocess
import json

def generate_okh_manifest(project_url, output_file="manifest.okh.json"):
    """Generate OKH manifest using CLI"""
    try:
        result = subprocess.run([
            "ome", "llm", "generate-okh",
            project_url,
            "--output", output_file,
            "--format", "json"
        ], capture_output=True, text=True, check=True)
        
        return {"success": True, "output": result.stdout}
    except subprocess.CalledProcessError as e:
        return {"success": False, "error": e.stderr}

# Usage
result = generate_okh_manifest("https://github.com/example/project")
if result["success"]:
    print("Manifest generated successfully")
else:
    print(f"Error: {result['error']}")
```

## Next Steps

- [API Reference](api.md) - Learn about LLM API endpoints
- [Configuration](configuration.md) - Set up LLM providers
- [Examples](examples.md) - See practical usage examples
