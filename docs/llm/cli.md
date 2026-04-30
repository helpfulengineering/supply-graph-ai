# LLM CLI Commands

This document describes the command-line interface for LLM operations in the Open Hardware Manager.

## Overview

The LLM CLI provides easy access to LLM features through the `ohm` command-line tool. All LLM commands are prefixed with `llm` and support various options for configuration and output formatting.

## Basic Usage

```bash
# Show LLM help
ohm llm --help

# Show specific command help
ohm llm generate --help
ohm llm match --help
```

## Commands

### Generate Content

Generate content using the LLM service.

```bash
ohm llm generate [OPTIONS] PROMPT
```

**Options:**
- `--provider TEXT`: LLM provider (anthropic, openai, google, local)
- `--model TEXT`: Model name (e.g., claude-sonnet-4-5-20250929)
- `--max-tokens INTEGER`: Maximum tokens to generate (default: 4000)
- `--temperature FLOAT`: Sampling temperature (default: 0.1)
- `--timeout INTEGER`: Request timeout in seconds (default: 60)
- `--output FILE`: Output file (default: stdout)
- `--format TEXT`: Output format (json, text, yaml) (default: text)

**Examples:**

```bash
# Basic generation
ohm llm generate "Analyze this hardware project and generate an OKH manifest"

# With specific provider and model
ohm llm generate "Generate OKH manifest" \
  --provider anthropic \
  --model claude-sonnet-4-5-20250929

# Save to file with JSON format
ohm llm generate "Analyze project" \
  --output manifest.json \
  --format json

# High temperature for creative output
ohm llm generate "Suggest improvements" \
  --temperature 0.7 \
  --max-tokens 2000
```

### Generate OKH Manifest

Generate an OKH manifest for a hardware project.

```bash
ohm llm generate-okh [OPTIONS] PROJECT_URL
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
ohm llm generate-okh https://github.com/example/iot-sensor

# With specific provider
ohm llm generate-okh https://github.com/example/project \
  --provider anthropic \
  --model claude-sonnet-4-5-20250929

# Clone repository for better analysis
ohm llm generate-okh https://github.com/example/project \
  --clone \
  --preserve-context

# Save in different format
ohm llm generate-okh https://github.com/example/project \
  --output manifest.yaml \
  --format yaml
```

### Match Facilities

Use LLM to enhance facility matching.

```bash
ohm llm match [OPTIONS] REQUIREMENTS_FILE FACILITIES_FILE
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
ohm llm match requirements.json facilities.json

# With confidence threshold
ohm llm match requirements.json facilities.json \
  --min-confidence 0.7 \
  --output matches.json

# Table format output
ohm llm match requirements.json facilities.json \
  --format table \
  --min-confidence 0.6
```

### Analyze Project

Analyze a hardware project and extract information.

```bash
ohm llm analyze [OPTIONS] PROJECT_URL
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
ohm llm analyze https://github.com/example/project

# Analysis
ohm llm analyze https://github.com/example/project \
  --include-code \
  --include-docs \
  --output analysis.json \
  --format json

# Markdown report
ohm llm analyze https://github.com/example/project \
  --output report.md \
  --format markdown
```

### Provider Management

Manage LLM providers and configuration.

```bash
ohm llm providers [COMMAND]
```

**Subcommands:**
- `list`: List available providers
- `status`: Show provider status
- `set`: Set active provider
- `test`: Test provider connection

**Examples:**

```bash
# List all providers
ohm llm providers list

# Show provider status
ohm llm providers status

# Set active provider
ohm llm providers set anthropic

# Test provider connection
ohm llm providers test anthropic
```

### Service Management

Manage LLM service and metrics.

```bash
ohm llm service [COMMAND]
```

**Subcommands:**
- `status`: Show service status
- `metrics`: Show usage metrics
- `health`: Check service health
- `reset`: Reset service state

**Examples:**

```bash
# Show service status
ohm llm service status

# Show usage metrics
ohm llm service metrics

# Check health
ohm llm service health

# Reset service
ohm llm service reset
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
export OHM_LLM_DEFAULT_PROVIDER="anthropic"
export OHM_LLM_DEFAULT_MODEL="claude-sonnet-4-5-20250929"
export OHM_LLM_MAX_COST_PER_REQUEST="2.0"
export OHM_LLM_TIMEOUT="60"
```

### Configuration File

Create `~/.ohm/llm_config.yaml` (example path; align with your deployment conventions):

```yaml
llm:
  default_provider: "anthropic"
  default_model: "claude-sonnet-4-5-20250929"
  timeout: 60
  max_retries: 3
  retry_delay: 1.0
  enable_fallback: true
  max_cost_per_request: 2.0
  enable_cost_tracking: true
  
  providers:
    anthropic:
      api_key: "${ANTHROPIC_API_KEY}"
      model: "claude-sonnet-4-5-20250929"
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
ohm llm generate "Analyze project" --format json
```

```json
{
  "content": "Generated content...",
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

### YAML Format

```bash
ohm llm generate "Analyze project" --format yaml
```

```yaml
content: "Generated content..."
status: "success"
metadata:
  provider: "anthropic"
  model: "claude-sonnet-4-5-20250929"
  tokens_used: 1981
  cost: 0.0143
  processing_time: 8.12
```

### Table Format

```bash
ohm llm match requirements.json facilities.json --format table
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
ohm llm analyze https://github.com/example/iot-sensor \
  --output project_analysis.json \
  --format json

# 2. Generate OKH manifest
ohm llm generate-okh https://github.com/example/iot-sensor \
  --output manifest.okh.json \
  --preserve-context

# 3. Match facilities
ohm llm match requirements.json facilities.json \
  --output matches.json \
  --min-confidence 0.7

# 4. Check service metrics
ohm llm service metrics
```

### Batch Processing

```bash
# Process multiple projects
for project in project1 project2 project3; do
  ohm llm generate-okh "https://github.com/example/$project" \
    --output "manifests/${project}.okh.json"
done

# Generate reports
ohm llm analyze https://github.com/example/project1 \
  --output reports/project1_analysis.md \
  --format markdown
```

### Development Workflow

```bash
# Test with local model
ohm llm generate "Test prompt" \
  --provider local \
  --model llama2:7b \
  --timeout 120

# Debug with context preservation
ohm llm generate-okh https://github.com/example/project \
  --preserve-context \
  --output debug_manifest.json

# Check provider status
ohm llm providers status
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
export OHM_LOG_LEVEL=DEBUG

# Run command with verbose output
ohm llm generate "Test prompt" --verbose
```

### Troubleshooting

```bash
# Check service health
ohm llm service health

# Test provider connection
ohm llm providers test anthropic

# Show detailed metrics
ohm llm service metrics --detailed

# Reset service state
ohm llm service reset
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

if ohm llm generate-okh "$PROJECT_URL" --output "$OUTPUT_FILE"; then
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
            "ohm", "llm", "generate-okh",
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
