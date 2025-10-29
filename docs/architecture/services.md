# Service Architecture Documentation

## Overview

The Open Matching Engine (OME) implements a service architecture built around the `BaseService` pattern, providing standardized service management, lifecycle handling, performance tracking, and LLM integration support. This architecture ensures consistency, maintainability, and enterprise-grade capabilities across all services.

## Architecture Principles

### Core Design Principles

1. **Standardization**: All services inherit from `BaseService` for consistent patterns
2. **Lifecycle Management**: service initialization, health monitoring, and shutdown
3. **Performance Tracking**: Built-in metrics collection and request monitoring
4. **Error Handling**: Standardized error handling with context and recovery strategies
5. **LLM Integration Ready**: Prepared interfaces for LLM service integration
6. **Configuration Management**: Dynamic configuration updates and validation
7. **Dependency Management**: Clear service dependencies and health monitoring

## BaseService Architecture

### Core Components

#### BaseService Class (`src/core/services/base.py`)

The foundation of all services providing:

```python
class BaseService(ABC):
    """Base service class providing standardized service patterns and utilities."""
    
    def __init__(self, config: ServiceConfig):
        self.config = config
        self.metrics = ServiceMetrics()
        self.status = ServiceStatus.INITIALIZING
        self.dependencies: Dict[str, BaseService] = {}
        self.health_checks: List[Callable] = []
        self._start_time = time.time()
        self._request_count = 0
        self._error_count = 0
```

**Key Features:**
- **Service Configuration**: Dynamic configuration management with validation
- **Metrics Collection**: Performance tracking, request counting, and error monitoring
- **Status Management**: Service lifecycle status tracking (INITIALIZING, HEALTHY, DEGRADED, ERROR, SHUTDOWN)
- **Dependency Management**: Service dependency tracking and health monitoring
- **Health Checks**: Configurable health check functions
- **Request Tracking**: Built-in request counting and performance monitoring

#### ServiceConfig Class

Standardized service configuration:

```python
@dataclass
class ServiceConfig:
    """Configuration for service instances."""
    name: str
    version: str = "1.0.0"
    timeout: float = 30.0
    max_retries: int = 3
    health_check_interval: float = 60.0
    metrics_retention: int = 1000
    llm_config: Optional[LLMConfig] = None
    custom_config: Dict[str, Any] = field(default_factory=dict)
```

**Configuration Features:**
- **Service Identity**: Name and version tracking
- **Performance Settings**: Timeout and retry configuration
- **Health Monitoring**: Health check intervals and metrics retention
- **LLM Integration**: Optional LLM configuration support
- **Custom Configuration**: Extensible configuration for service-specific settings

#### ServiceMetrics Class

metrics collection:

```python
@dataclass
class ServiceMetrics:
    """Metrics for service performance and usage tracking."""
    request_count: int = 0
    success_count: int = 0
    error_count: int = 0
    average_response_time: float = 0.0
    last_request_time: Optional[datetime] = None
    last_error_time: Optional[datetime] = None
    uptime_seconds: float = 0.0
    llm_requests: int = 0
    llm_tokens_used: int = 0
    llm_cost: float = 0.0
```

**Metrics Features:**
- **Request Tracking**: Total, success, and error request counts
- **Performance Metrics**: Average response time and uptime tracking
- **LLM Metrics**: LLM request tracking, token usage, and cost monitoring
- **Error Tracking**: Error count and last error timestamp
- **Real-time Updates**: Automatic metrics updates during service operation

#### ServiceStatus Enum

Service lifecycle status management:

```python
class ServiceStatus(Enum):
    """Service status enumeration."""
    INITIALIZING = "initializing"
    HEALTHY = "healthy"
    DEGRADED = "degraded"
    ERROR = "error"
    SHUTDOWN = "shutdown"
```

## Service Implementation Patterns

### Standard Service Structure

All services follow this standardized pattern:

```python
class ExampleService(BaseService):
    """Example service implementation."""
    
    def __init__(self, config: ServiceConfig):
        super().__init__(config)
        self._initialize_service()
    
    async def _initialize_service(self):
        """Initialize service-specific components."""
        try:
            # Service-specific initialization
            await self._setup_dependencies()
            await self._configure_components()
            
            # Register health checks
            self.add_health_check(self._check_database_connection)
            self.add_health_check(self._check_external_api)
            
            # Update status
            self.status = ServiceStatus.HEALTHY
            self.log("Service initialized successfully", "info")
            
        except Exception as e:
            self.status = ServiceStatus.ERROR
            self.log(f"Service initialization failed: {e}", "error")
            raise
    
    async def _setup_dependencies(self):
        """Setup service dependencies."""
        # Initialize dependent services
        pass
    
    async def _configure_components(self):
        """Configure service components."""
        # Configure service-specific components
        pass
    
    async def _check_database_connection(self) -> bool:
        """Health check for database connection."""
        try:
            # Check database connectivity
            return True
        except Exception:
            return False
    
    async def _check_external_api(self) -> bool:
        """Health check for external API."""
        try:
            # Check external API connectivity
            return True
        except Exception:
            return False
```

### Request Tracking Pattern

Services use context managers for request tracking:

```python
async def process_request(self, request_data: Dict[str, Any]) -> Dict[str, Any]:
    """Process a request with automatic tracking."""
    async with self.track_request("process_request") as tracker:
        try:
            # Process the request
            result = await self._do_processing(request_data)
            
            # Update metrics
            tracker.mark_success()
            return result
            
        except Exception as e:
            # Update error metrics
            tracker.mark_error(str(e))
            raise
```

### Health Check Implementation

Standardized health check patterns:

```python
async def health_check(self) -> Dict[str, Any]:
    """health check."""
    health_status = {
        "service": self.config.name,
        "status": self.status.value,
        "uptime": self.get_uptime(),
        "metrics": self.metrics,
        "dependencies": {},
        "checks": {}
    }
    
    # Check dependencies
    for name, service in self.dependencies.items():
        health_status["dependencies"][name] = await service.health_check()
    
    # Run health checks
    for check in self.health_checks:
        try:
            result = await check()
            health_status["checks"][check.__name__] = result
        except Exception as e:
            health_status["checks"][check.__name__] = False
            health_status["status"] = ServiceStatus.DEGRADED.value
    
    return health_status
```

## Implemented Services

### OKHService (`src/core/services/okh_service.py`)

**Purpose**: Manages OpenKnowHow manifest operations

**Key Features:**
- **Manifest Management**: Create, read, update, delete OKH manifests
- **Validation**: manifest validation with quality levels
- **Extraction**: Requirements extraction from manifests
- **Storage Integration**: Azure Blob Storage integration
- **LLM Integration**: LLM-enhanced validation and extraction

**Configuration:**
```python
config = ServiceConfig(
    name="okh_service",
    version="1.0.0",
    timeout=30.0,
    max_retries=3,
    llm_config=LLMConfig(
        provider="anthropic",
        model="claude-3-sonnet",
        quality_level="professional"
    )
)
```

**Health Checks:**
- Database connectivity
- Storage service availability
- LLM provider connectivity (if configured)

### OKWService (`src/core/services/okw_service.py`)

**Purpose**: Manages OpenKnowWhere facility operations

**Key Features:**
- **Facility Management**: Create, read, update, delete OKW facilities
- **Search**: Advanced facility search with filtering
- **Validation**: facility validation
- **Capability Extraction**: Manufacturing capability extraction
- **Storage Integration**: Azure Blob Storage integration

**Configuration:**
```python
config = ServiceConfig(
    name="okw_service",
    version="1.0.0",
    timeout=30.0,
    max_retries=3,
    health_check_interval=60.0
)
```

**Health Checks:**
- Database connectivity
- Storage service availability
- Search index health

### MatchingService (`src/core/services/matching_service.py`)

**Purpose**: Orchestrates matching operations between OKH and OKW

**Key Features:**
- **Multi-layer Matching**: Direct, heuristic, NLP, and LLM matching
- **Domain Support**: Manufacturing and cooking domain support
- **Supply Tree Generation**: Complete supply tree solution generation
- **Performance Optimization**: Matching algorithm optimization
- **LLM Integration**: LLM-enhanced matching capabilities

**Configuration:**
```python
config = ServiceConfig(
    name="matching_service",
    version="1.0.0",
    timeout=60.0,
    max_retries=3,
    llm_config=LLMConfig(
        provider="anthropic",
        model="claude-3-sonnet",
        quality_level="professional"
    )
)
```

**Dependencies:**
- OKHService
- OKWService
- Domain registry services

**Health Checks:**
- OKH service connectivity
- OKW service connectivity
- Domain registry health
- Matching algorithm performance

## Service Lifecycle Management

### Initialization Process

1. **Configuration Loading**: Load and validate service configuration
2. **Dependency Setup**: Initialize and connect to dependent services
3. **Component Configuration**: Configure service-specific components
4. **Health Check Registration**: Register health check functions
5. **Status Update**: Set status to HEALTHY
6. **Metrics Initialization**: Initialize metrics collection

### Health Monitoring

Services continuously monitor their health through:

1. **Periodic Health Checks**: Configurable interval health checks
2. **Dependency Monitoring**: Monitor dependent service health
3. **Performance Monitoring**: Track response times and error rates
4. **Resource Monitoring**: Monitor memory, CPU, and network usage
5. **Status Updates**: Automatic status updates based on health

### Shutdown Process

1. **Graceful Shutdown**: Stop accepting new requests
2. **Request Completion**: Wait for in-flight requests to complete
3. **Dependency Cleanup**: Clean up dependent service connections
4. **Resource Cleanup**: Release allocated resources
5. **Status Update**: Set status to SHUTDOWN
6. **Metrics Finalization**: Finalize metrics collection

## Performance Monitoring

### Built-in Metrics

All services automatically collect:

- **Request Metrics**: Total, success, and error counts
- **Performance Metrics**: Average response time and uptime
- **LLM Metrics**: LLM request tracking, token usage, and costs
- **Error Metrics**: Error count and last error timestamp
- **Dependency Metrics**: Dependent service health and performance

### Metrics Collection

```python
# Automatic metrics collection
async with self.track_request("operation_name") as tracker:
    # Service operation
    result = await self._perform_operation()
    
    # Automatic metrics updates
    tracker.mark_success()  # Updates success_count
    # tracker.mark_error()  # Updates error_count if needed
```

### Performance Analysis

Services provide performance analysis:

```python
# Get service performance summary
performance = await service.get_performance_summary()

# Example output:
{
    "service": "okh_service",
    "uptime": 3600.0,
    "request_count": 150,
    "success_rate": 0.98,
    "average_response_time": 0.25,
    "error_count": 3,
    "llm_requests": 45,
    "llm_tokens_used": 12500,
    "llm_cost": 0.15
}
```

## Error Handling

### Standardized Error Types

Services use a error hierarchy:

```python
class ServiceError(OMEError):
    """Base service error."""
    pass

class ServiceInitializationError(ServiceError):
    """Service initialization error."""
    pass

class ServiceHealthError(ServiceError):
    """Service health check error."""
    pass

class ServiceDependencyError(ServiceError):
    """Service dependency error."""
    pass
```

### Error Recovery Strategies

Services implement automatic error recovery:

1. **Retry Logic**: Configurable retry attempts for transient errors
2. **Circuit Breaker**: Automatic service degradation for persistent errors
3. **Fallback Mechanisms**: Graceful degradation when dependencies fail
4. **Error Context**: Rich error context for debugging and monitoring

### Error Reporting

```python
try:
    result = await service.operation()
except ServiceError as e:
    # Automatic error tracking
    service.metrics.error_count += 1
    service.metrics.last_error_time = datetime.now()
    
    # Rich error context
    error_context = {
        "service": service.config.name,
        "operation": "operation_name",
        "error": str(e),
        "timestamp": datetime.now(),
        "request_id": request_id
    }
    
    # Log error with context
    service.log(f"Service error: {e}", "error", context=error_context)
```

## LLM Integration

### LLM Configuration

Services support LLM configuration:

```python
llm_config = LLMConfig(
    provider="anthropic",
    model="claude-3-sonnet",
    quality_level="professional",
    max_tokens=4000,
    temperature=0.1,
    timeout=30.0
)

service_config = ServiceConfig(
    name="example_service",
    llm_config=llm_config
)
```

### LLM Request Tracking

Services automatically track LLM usage:

```python
async def llm_enhanced_operation(self, data: Dict[str, Any]) -> Dict[str, Any]:
    """LLM-enhanced operation with automatic tracking."""
    if not self.config.llm_config:
        return await self._standard_operation(data)
    
    async with self.track_llm_request("llm_enhanced_operation") as tracker:
        # LLM operation
        result = await self._call_llm_provider(data)
        
        # Automatic LLM metrics updates
        tracker.mark_llm_usage(
            tokens_used=result.tokens_used,
            cost=result.cost,
            provider=self.config.llm_config.provider
        )
        
        return result
```

### LLM Metrics

Services collect LLM metrics:

- **Request Count**: Total LLM requests made
- **Token Usage**: Tokens consumed per provider
- **Cost Tracking**: Cost per provider and operation
- **Performance Metrics**: LLM response times
- **Error Tracking**: LLM-specific error rates

## Configuration Management

### Dynamic Configuration Updates

Services support dynamic configuration updates:

```python
# Update service configuration
new_config = ServiceConfig(
    name="updated_service",
    timeout=60.0,
    max_retries=5
)

await service.update_config(new_config)
```

### Configuration Validation

All configuration updates are validated:

```python
def validate_config(self, config: ServiceConfig) -> bool:
    """Validate service configuration."""
    if config.timeout <= 0:
        raise ValueError("Timeout must be positive")
    
    if config.max_retries < 0:
        raise ValueError("Max retries must be non-negative")
    
    return True
```

### Environment Integration

Services integrate with environment variables:

```python
# Load configuration from environment
config = ServiceConfig.from_env(
    prefix="OKH_SERVICE_",
    defaults={
        "timeout": 30.0,
        "max_retries": 3
    }
)
```

## Testing and Validation

### Service Testing Patterns

Services include testing support:

```python
class TestOKHService:
    """Test suite for OKHService."""
    
    async def test_service_initialization(self):
        """Test service initialization."""
        config = ServiceConfig(name="test_okh_service")
        service = OKHService(config)
        
        assert service.status == ServiceStatus.HEALTHY
        assert service.config.name == "test_okh_service"
    
    async def test_health_check(self):
        """Test service health check."""
        service = await self.create_test_service()
        health = await service.health_check()
        
        assert health["status"] == "healthy"
        assert "metrics" in health
        assert "dependencies" in health
    
    async def test_request_tracking(self):
        """Test request tracking."""
        service = await self.create_test_service()
        
        async with service.track_request("test_operation") as tracker:
            # Simulate operation
            await asyncio.sleep(0.1)
            tracker.mark_success()
        
        assert service.metrics.request_count == 1
        assert service.metrics.success_count == 1
```

### Integration Testing

Services support integration testing:

```python
async def test_service_integration(self):
    """Test service integration."""
    # Create service with dependencies
    okh_service = OKHService(okh_config)
    okw_service = OKWService(okw_config)
    matching_service = MatchingService(matching_config)
    
    # Setup dependencies
    matching_service.add_dependency("okh", okh_service)
    matching_service.add_dependency("okw", okw_service)
    
    # Test integrated operation
    result = await matching_service.match_requirements(okh_data, okw_data)
    
    assert result is not None
    assert "solutions" in result
```

## Best Practices

### Service Design

1. **Single Responsibility**: Each service should have a single, well-defined responsibility
2. **Dependency Injection**: Use dependency injection for service dependencies
3. **Configuration Management**: Use ServiceConfig for all configuration
4. **Health Monitoring**: Implement health checks
5. **Error Handling**: Use standardized error types and recovery strategies

### Performance Optimization

1. **Request Tracking**: Use context managers for automatic request tracking
2. **Metrics Collection**: Leverage built-in metrics for performance monitoring
3. **Caching**: Implement appropriate caching strategies
4. **Async Operations**: Use async/await for all I/O operations
5. **Resource Management**: Properly manage resources and connections

### Monitoring and Observability

1. **Health Checks**: Implement health check functions
2. **Metrics**: Use built-in metrics for performance monitoring
3. **Logging**: Use structured logging with appropriate levels
4. **Error Tracking**: Track and report errors with context
5. **Dependency Monitoring**: Monitor dependent service health

## Future Enhancements

### Planned Features

1. **Service Discovery**: Automatic service discovery and registration
2. **Load Balancing**: Built-in load balancing for service instances
3. **Circuit Breaker**: Advanced circuit breaker patterns
4. **Distributed Tracing**: Distributed tracing support
5. **Service Mesh**: Integration with service mesh technologies

### LLM Integration Enhancements

1. **Multi-Provider Support**: Support for multiple LLM providers
2. **Cost Optimization**: Intelligent LLM provider selection
3. **Caching**: LLM response caching for cost optimization
4. **Quality Assessment**: Automatic LLM response quality assessment
5. **Fallback Strategies**: Graceful fallback when LLM services are unavailable

## Conclusion

The OME service architecture provides a robust, standardized foundation for building scalable, maintainable services. The BaseService pattern ensures consistency across all services while providing features for monitoring, error handling, and LLM integration.

Key benefits of this architecture:

- **Consistency**: Standardized patterns across all services
- **Maintainability**: Clear separation of concerns and standardized interfaces
- **Observability**: monitoring and metrics collection
- **Reliability**: Built-in error handling and recovery strategies
- **Scalability**: Designed for horizontal scaling and load distribution
- **LLM Ready**: Prepared for LLM integration

This architecture forms the foundation for the OME system's service layer and provides a solid base for future enhancements and LLM integration.
