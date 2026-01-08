# OHM CLI Architecture

## Overview

The OHM CLI is built using a modern, standardized architecture that provides both HTTP API integration and direct service access. The system has been completely refactored with LLM integration support, standardized command patterns, and enterprise-grade error handling. This design ensures reliability, flexibility, and consistency across all 36 CLI commands.

## Architecture Components

### 1. Core CLI Framework (`src/cli/base.py`)

The foundation of the CLI system providing:

- **CLIConfig**: Advanced configuration management with LLM support, server URLs, timeouts, and output formats
- **CLIContext**: Runtime context with LLM configuration, performance tracking, and API client instances
- **APIClient**: HTTP client for communicating with the FastAPI server
- **SmartCommand**: Intelligent command execution with HTTP/fallback logic and performance tracking
- **Output Utilities**: Consistent formatting, error handling, and LLM-specific output formatting
- **LLM Integration**: Built-in support for LLM providers, quality levels, and strict mode validation

```python
# Example usage with LLM support
config = CLIConfig(
    server_url="http://localhost:8001", 
    verbose=True,
    llm_config={
        'use_llm': True,
        'llm_provider': 'anthropic',
        'quality_level': 'professional',
        'strict_mode': False
    }
)
context = CLIContext(config=config, api_client=APIClient(config))
command = SmartCommand(context)
```

### 2. Standardized Command Decorators (`src/cli/decorators.py`)

The CLI uses a decorator system for consistent command patterns:

- **@standard_cli_command**: Main decorator providing LLM options, error handling, performance tracking, and output formatting
- **@with_llm_config**: Adds LLM configuration options to commands
- **@with_error_handling**: Standardized error handling across all commands
- **@with_performance_tracking**: Built-in performance monitoring and command timing
- **@with_output_formatting**: Consistent JSON and table output formatting

```python
@standard_cli_command(
    help_text="Command description with examples",
    epilog="Additional examples and usage",
    async_cmd=True,
    track_performance=True,
    handle_errors=True,
    format_output=True,
    add_llm_config=True
)
async def my_command(ctx, verbose: bool, output_format: str, use_llm: bool,
                    llm_provider: str, llm_model: Optional[str],
                    quality_level: str, strict_mode: bool):
    # Command implementation with automatic LLM support
```

### 3. Command Groups

The CLI is organized into 6 command groups with 36 total commands, each fully standardized:

#### Match Commands (`src/cli/match.py`) - 3 commands
- Requirements-to-capabilities matching with LLM enhancement
- Match validation and result management
- Domain-specific matching operations

#### OKH Commands (`src/cli/okh.py`) - 8 commands
- OpenKnowHow manifest validation and management with LLM support
- Manifest creation, retrieval, and deletion
- Requirement extraction from manifests with enhanced analysis

#### OKW Commands (`src/cli/okw.py`) - 9 commands
- OpenKnowWhere facility validation and management with LLM support
- Facility creation, retrieval, and deletion
- Capability extraction and searching with intelligent analysis

#### Package Commands (`src/cli/package.py`) - 9 commands
- Package building, verification, and management with LLM enhancement
- Remote storage operations (push/pull)
- Local package listing and deletion

#### System Commands (`src/cli/system.py`) - 5 commands
- System health monitoring with diagnostics
- Domain and status information with LLM analysis
- Server connectivity testing and performance monitoring

#### Utility Commands (`src/cli/utility.py`) - 2 commands
- Domain and context listing with enhanced analysis
- Utility operations for system introspection

### 4. Main Entry Point (`src/cli/main.py`)

The main CLI entry point that:
- Registers all 6 command groups with 36 total commands
- Handles global options including LLM configuration
- Provides version and configuration commands
- Sets up the Click framework with help system
- Manages LLM provider options and quality levels

## LLM Integration

### LLM Configuration

The CLI supports LLM integration across all commands:

```bash
# Global LLM options
ohm --use-llm --llm-provider anthropic --quality-level professional [COMMAND]

# Command-specific LLM options
ohm okh validate manifest.json --use-llm --llm-provider openai --strict-mode
```

### Supported LLM Providers

- **OpenAI**: GPT-3.5, GPT-4, and other OpenAI models
- **Anthropic**: Claude models with advanced reasoning
- **Google**: PaLM and other Google AI models
- **Azure OpenAI**: Azure-hosted OpenAI models
- **Local**: Local model support for offline operations

### Quality Levels

- **hobby**: Basic quality for personal projects
- **professional**: Standard quality for commercial use
- **medical**: High quality for medical device applications

### LLM Features

- **Enhanced Analysis**: LLM-powered validation and extraction
- **Intelligent Matching**: Advanced requirement-to-capability matching
- **Quality Assessment**: Automated quality evaluation and recommendations
- **Error Detection**: Intelligent error detection and suggestions
- **Performance Optimization**: LLM-assisted performance improvements

## Execution Modes

### HTTP Mode (Primary)

When the OHM server is available, commands use HTTP API endpoints:

```python
async def http_operation():
    async with httpx.AsyncClient(timeout=config.timeout) as client:
        response = await client.get(f"{config.server_url}/api/endpoint")
        return response.json()
```

**Advantages:**
- Centralized processing
- Consistent with web interface
- Server-side validation and processing
- Better error handling and logging

### Fallback Mode (Secondary)

When the server is unavailable, commands fall back to direct service calls:

```python
async def fallback_operation():
    service = await get_service()
    return await service.direct_operation()
```

**Advantages:**
- Works offline
- No server dependency
- Direct access to services
- Useful for development and testing

### Smart Command Execution

The `SmartCommand` class automatically handles mode selection:

```python
command = SmartCommand(context)
result = await command.execute_with_fallback(http_operation, fallback_operation)
```

This ensures:
- Automatic fallback when server is unavailable
- Consistent error handling
- Transparent mode switching
- User-friendly error messages

## Configuration Management

### Global Configuration

The CLI supports global configuration through command-line options:

```bash
ohm --server-url https://api.ome.org --timeout 60 --verbose package build manifest.json
```

### Configuration Hierarchy

1. **Command-line options** (highest priority)
2. **Environment variables** (medium priority)
3. **Default values** (lowest priority)

### Configuration Options

| Option | Environment Variable | Default | Description |
|--------|---------------------|---------|-------------|
| `--server-url` | `OHM_SERVER_URL` | `http://localhost:8001` | OHM server URL |
| `--timeout` | `OHM_TIMEOUT` | `30.0` | Request timeout in seconds |
| `--verbose` | `OHM_VERBOSE` | `False` | Enable verbose output |
| `--json` | `OHM_JSON` | `False` | JSON output format |
| `--table` | `OHM_TABLE` | `False` | Table output format |
| `--use-llm` | `OHM_USE_LLM` | `False` | Enable LLM integration |
| `--llm-provider` | `OHM_LLM_PROVIDER` | `anthropic` | LLM provider (openai, anthropic, google, azure, local) |
| `--llm-model` | `OHM_LLM_MODEL` | `None` | Specific LLM model to use |
| `--quality-level` | `OHM_QUALITY_LEVEL` | `professional` | Quality level (hobby, professional, medical) |
| `--strict-mode` | `OHM_STRICT_MODE` | `False` | Enable strict validation mode |

## Error Handling

### Standardized Error Handling

The CLI uses an error handling system with:

- **Standardized Error Types**: Consistent error categorization across all commands
- **Helpful Error Messages**: Clear, actionable error messages with suggestions
- **Graceful Degradation**: Automatic fallback when server is unavailable
- **LLM-Enhanced Error Analysis**: Intelligent error detection and recommendations
- **Performance Tracking**: Error tracking and performance monitoring

### Error Types

1. **Connection Errors**: Server unavailable, network issues (with automatic fallback)
2. **Validation Errors**: Invalid input files, missing parameters (with specific suggestions)
3. **File System Errors**: File not found, permission issues (with helpful guidance)
4. **API Errors**: Server-side errors, invalid responses (with retry suggestions)
5. **LLM Errors**: LLM provider issues, model errors (with fallback options)

### Error Handling Strategy

```python
try:
    # Commands automatically handle errors with standardized patterns
    result = await command.execute_with_fallback(http_operation, fallback_operation)
    
    # Standardized success/error handling
    if result.get("status") == "error":
        cli_ctx.log(f"Operation failed: {result.get('message')}", "error")
        return 1
    else:
        cli_ctx.log("Operation completed successfully", "success")
        return 0
        
except ValueError as e:
    # Domain validation errors with helpful messages
    cli_ctx.log(f"Validation error: {e}", "error")
    return 1
except Exception as e:
    # Unexpected errors with debugging information
    cli_ctx.log(f"Unexpected error: {e}", "error")
    if cli_ctx.verbose:
        cli_ctx.log(f"Debug info: {traceback.format_exc()}", "info")
    return 1
```

### User-Friendly Error Messages

The CLI provides clear, actionable error messages with helpful suggestions:

```bash
# File not found
❌ Error: Package community/nonexistent:1.0.0 not found
   Suggestion: Use 'ohm package list-packages' to see available packages

# Server connection failed (with automatic fallback)
⚠️  Server unavailable, using direct service calls...
✅ Operation completed successfully

# Validation error with specific guidance
❌ Error: Invalid domain 'nonexistent-domain'. Valid domains are: manufacturing, cooking
   Suggestion: Use 'ohm utility domains' to see available domains

# LLM configuration error
❌ Error: LLM provider 'invalid-provider' not supported
   Suggestion: Use one of: openai, anthropic, google, azure, local

# Verbose mode with detailed information
ℹ️  Starting system-health command
ℹ️  Attempting to connect to server...
ℹ️  Checking health via HTTP API...
✅ Connected to server successfully
✅ Command system-health completed in 0.08 seconds
```

## Output Formatting

### Text Format (Default)

Human-readable output with icons and formatting:

```
✅ Found 2 built packages
📦 university-of-bath/openflexure-microscope/5.20
   📁 /path/to/package
   📄 15 files, 1,053,656 bytes
   🕒 Built: 2025-10-13T11:06:06.111890
```

### JSON Format

Structured output for scripting and integration:

```json
{
  "status": "success",
  "packages": [
    {
      "name": "university-of-bath/openflexure-microscope",
      "version": "5.20",
      "path": "/path/to/package",
      "file_count": 15,
      "size": 1053656,
      "built_at": "2025-10-13T11:06:06.111890"
    }
  ]
}
```

### Table Format

Tabular output for data analysis:

```
| Name                                    | Version | Files | Size    | Built At                |
|-----------------------------------------|---------|-------|---------|-------------------------|
| university-of-bath/openflexure-microscope | 5.20    | 15    | 1.0 MB  | 2025-10-13T11:06:06     |
| community/simple-test-project           | 1.0.0   | 2     | 58 KB   | 2025-10-13T11:25:23     |
```

## Service Integration

### HTTP API Integration

The CLI integrates with FastAPI endpoints:

```python
# Package endpoints
POST /api/package/build
POST /api/package/push
POST /api/package/pull
GET  /api/package/remote

# System endpoints
GET  /health
GET  /v1/domains
GET  /v1/status

# Utility endpoints
GET  /v1/utility/domains
GET  /v1/utility/contexts
```

### Direct Service Integration

When HTTP mode is unavailable, the CLI uses direct service calls:

```python
# Direct service access
package_service = await get_package_service()
okh_service = await get_okh_service()
okw_service = await get_okw_service()
storage_service = await get_storage_service()
```

## Security Considerations

### Authentication

The CLI supports authentication through:
- API keys in environment variables
- Token-based authentication
- Basic authentication

### Data Protection

- Sensitive data is not logged in verbose mode
- Credentials are handled securely
- File permissions are respected

### Network Security

- HTTPS support for secure connections
- Certificate validation
- Timeout protection against hanging requests

## Performance Optimization

### Connection Pooling

The HTTP client uses connection pooling for efficiency:

```python
async with httpx.AsyncClient(
    timeout=config.timeout,
    limits=httpx.Limits(max_keepalive_connections=20, max_connections=100)
) as client:
    # Reuse connections for multiple requests
```

### Caching

- Configuration caching
- Service instance caching
- Response caching where appropriate

### Async Operations

All operations are asynchronous for better performance:

```python
async def build_package(manifest_file):
    # Non-blocking operations
    manifest = await load_manifest(manifest_file)
    files = await download_files(manifest)
    return await create_package(manifest, files)
```

## Deployment Considerations

### Standalone Deployment

The CLI can be deployed as a standalone application:

```bash
# Create executable
pip install pyinstaller
pyinstaller --onefile ohm

# Deploy executable
./ohm system health
```

### Container Deployment

Docker container for consistent deployment:

```dockerfile
FROM python:3.9-slim
COPY . /app
WORKDIR /app
RUN pip install -r requirements.txt
ENTRYPOINT ["./ohm"]
```

### CI/CD Integration

The CLI integrates well with CI/CD pipelines:

```yaml
- name: Validate manifests
  run: ohm okh validate *.okh.json

- name: Build packages
  run: ohm package build *.okh.json

- name: Push to registry
  run: ohm package push org/project $VERSION
```

## Future Enhancements

### Planned Features

1. **Plugin System**: Support for custom command plugins
2. **Configuration Files**: YAML/JSON configuration file support
3. **Batch Operations**: Enhanced batch processing capabilities
4. **Progress Indicators**: Better progress reporting for long operations
5. **Auto-completion**: Shell completion support

### Architecture Improvements

1. **Modular Commands**: Better command modularity and reusability
2. **Enhanced Error Recovery**: Better error recovery and retry logic
3. **Performance Monitoring**: Built-in performance monitoring
4. **Logging Integration**: Better logging and debugging support
