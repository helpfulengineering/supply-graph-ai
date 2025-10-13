# OME CLI Architecture

## Overview

The OME CLI is built using a modular architecture that provides both HTTP API integration and direct service access. This design ensures reliability and flexibility across different deployment scenarios.

## Architecture Components

### 1. Core CLI Framework (`src/cli/base.py`)

The foundation of the CLI system providing:

- **CLIConfig**: Configuration management for server URLs, timeouts, and output formats
- **CLIContext**: Runtime context holding configuration and API client instances
- **APIClient**: HTTP client for communicating with the FastAPI server
- **SmartCommand**: Intelligent command execution with HTTP/fallback logic
- **Output Utilities**: Consistent formatting and error handling

```python
# Example usage
config = CLIConfig(server_url="http://localhost:8001", verbose=True)
context = CLIContext(config=config, api_client=APIClient(config))
command = SmartCommand(context)
```

### 2. Command Groups

The CLI is organized into 7 command groups, each handling a specific domain:

#### Package Commands (`src/cli/package.py`)
- Package building, verification, and management
- Remote storage operations (push/pull)
- Local package listing and deletion

#### OKH Commands (`src/cli/okh.py`)
- OpenKnowHow manifest validation and management
- Manifest creation, retrieval, and deletion
- Requirement extraction from manifests

#### OKW Commands (`src/cli/okw.py`)
- OpenKnowWhere facility validation and management
- Facility creation, retrieval, and deletion
- Capability extraction and searching

#### Match Commands (`src/cli/match.py`)
- Requirements-to-capabilities matching
- Match validation and result management
- Recent match listing

#### System Commands (`src/cli/system.py`)
- System health monitoring
- Domain and status information
- Server connectivity testing

#### Supply Tree Commands (`src/cli/supply_tree.py`)
- Supply tree creation and management
- Tree validation and retrieval
- Tree listing and deletion

#### Utility Commands (`src/cli/utility.py`)
- Domain and context listing
- Utility operations for system introspection

### 3. Main Entry Point (`src/cli/main.py`)

The main CLI entry point that:
- Registers all command groups
- Handles global options
- Provides version and configuration commands
- Sets up the Click framework

## Execution Modes

### HTTP Mode (Primary)

When the OME server is available, commands use HTTP API endpoints:

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
ome --server-url https://api.ome.org --timeout 60 --verbose package build manifest.json
```

### Configuration Hierarchy

1. **Command-line options** (highest priority)
2. **Environment variables** (medium priority)
3. **Default values** (lowest priority)

### Configuration Options

| Option | Environment Variable | Default | Description |
|--------|---------------------|---------|-------------|
| `--server-url` | `OME_SERVER_URL` | `http://localhost:8001` | OME server URL |
| `--timeout` | `OME_TIMEOUT` | `30.0` | Request timeout in seconds |
| `--verbose` | `OME_VERBOSE` | `False` | Enable verbose output |
| `--json` | `OME_JSON` | `False` | JSON output format |
| `--table` | `OME_TABLE` | `False` | Table output format |

## Error Handling

### Error Types

1. **Connection Errors**: Server unavailable, network issues
2. **Validation Errors**: Invalid input files, missing parameters
3. **File System Errors**: File not found, permission issues
4. **API Errors**: Server-side errors, invalid responses

### Error Handling Strategy

```python
try:
    result = await command.execute_with_fallback(http_operation, fallback_operation)
    if result.get("status") == "error":
        echo_error(f"Operation failed: {result.get('message')}")
        return 1
    else:
        echo_success("Operation completed successfully")
        return 0
except Exception as e:
    echo_error(f"Unexpected error: {e}")
    return 1
```

### User-Friendly Error Messages

The CLI provides clear, actionable error messages:

```bash
# File not found
Error: Package community/nonexistent:1.0.0 not found

# Server connection failed
ℹ️  Server unavailable, using direct mode
✅ Operation completed successfully

# Validation error
Error: Invalid manifest: Missing required field 'title'
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

## Testing Strategy

### Unit Tests

- Individual command testing
- Service integration testing
- Error handling testing

### Integration Tests

- End-to-end workflow testing
- HTTP vs fallback mode testing
- Cross-platform compatibility testing

### Performance Tests

- Load testing with multiple concurrent operations
- Memory usage testing
- Response time benchmarking

## Deployment Considerations

### Standalone Deployment

The CLI can be deployed as a standalone application:

```bash
# Create executable
pip install pyinstaller
pyinstaller --onefile ome

# Deploy executable
./ome system health
```

### Container Deployment

Docker container for consistent deployment:

```dockerfile
FROM python:3.9-slim
COPY . /app
WORKDIR /app
RUN pip install -r requirements.txt
ENTRYPOINT ["./ome"]
```

### CI/CD Integration

The CLI integrates well with CI/CD pipelines:

```yaml
- name: Validate manifests
  run: ome okh validate *.okh.json

- name: Build packages
  run: ome package build *.okh.json

- name: Push to registry
  run: ome package push org/project $VERSION
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

This architecture provides a solid foundation for the OME CLI while maintaining flexibility for future enhancements and improvements.
