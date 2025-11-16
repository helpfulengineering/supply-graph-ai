# Metrics & Monitoring Implementation Specification

## Overview

This specification defines the implementation plan for the `MetricsTracker` class that is currently referenced but not implemented. The MetricsTracker will serve as a unified interface for collecting, aggregating, and exposing metrics across the OME API, integrating with existing metrics infrastructure.

## Current State Analysis

### Issue 1: MetricsTracker Not Implemented

**Location**: `src/core/main.py:23,92`
- **Issue**: `MetricsTracker` is commented out and not implemented
- **Context**: Referenced in middleware setup but passed as `None`
- **Severity**: High - Missing functionality

**Location**: `src/core/api/middleware.py:15,26,128`
- **Issue**: Multiple `# TODO: Implement MetricsTracker` comments
- **Context**: `RequestTrackingMiddleware` and `LLMRequestMiddleware` expect MetricsTracker instance
- **Severity**: High - Missing functionality

**Location**: `src/core/api/decorators.py:26`
- **Issue**: `# TODO: Implement MetricsTracker` comment
- **Context**: Decorator module references MetricsTracker but doesn't use it
- **Severity**: High - Missing functionality

### Existing Metrics Infrastructure

The codebase already has comprehensive metrics infrastructure:

1. **ErrorMetrics** (`src/core/errors/metrics.py:92`)
   - Tracks error rates, types, severity, categories
   - Component-level error tracking
   - Error timeline and rate calculations

2. **PerformanceMetrics** (`src/core/errors/metrics.py:195`)
   - Tracks operation durations, throughput
   - Resource usage monitoring
   - Performance statistics (avg, min, max, p95, p99)

3. **LLMMetrics** (`src/core/errors/metrics.py:334`)
   - Tracks LLM usage, costs, tokens
   - Provider and model-level statistics
   - Cost breakdown and timeline

4. **Service-Level Metrics**
   - `ServiceMetrics` in `src/core/services/base.py`
   - `EngineMetrics` in `src/core/generation/engine.py`
   - `MatchingMetrics` in `src/core/matching/layers/base.py`

### Expected Interface

Based on middleware usage, MetricsTracker should provide:

```python
class MetricsTracker:
    def start_request(self, request_id: str, method: str, path: str) -> None:
        """Track HTTP request start"""
        
    def end_request(
        self, 
        request_id: str, 
        success: bool, 
        status_code: int, 
        processing_time: float,
        error: Optional[str] = None
    ) -> None:
        """Track HTTP request completion"""
        
    def start_llm_request(
        self, 
        request_id: str, 
        provider: str, 
        model: str
    ) -> None:
        """Track LLM request start"""
        
    def end_llm_request(
        self, 
        request_id: str, 
        cost: Optional[float] = None,
        tokens_used: Optional[int] = None,
        processing_time: Optional[float] = None
    ) -> None:
        """Track LLM request completion"""
```

## Requirements

### Functional Requirements

1. **HTTP Request Tracking**
   - Track all HTTP requests (start, completion, errors)
   - Record request method, path, status code, processing time
   - Track success/failure rates per endpoint
   - Calculate request statistics (avg, min, max, p95, p99 response times)

2. **LLM Request Tracking**
   - Track LLM requests associated with HTTP requests
   - Record provider, model, cost, tokens, processing time
   - Link LLM metrics to parent HTTP requests
   - Aggregate LLM costs per endpoint

3. **Metrics Aggregation**
   - Aggregate metrics by endpoint (path + method)
   - Aggregate metrics by status code
   - Aggregate metrics by time period (last hour, day, week)
   - Calculate throughput (requests per second/minute)

4. **Metrics Exposure**
   - Provide summary statistics
   - Provide detailed metrics per endpoint
   - Provide LLM cost breakdown
   - Support filtering by time range

5. **Integration with Existing Metrics**
   - Use existing `ErrorMetrics`, `PerformanceMetrics`, `LLMMetrics`
   - Integrate with service-level metrics where appropriate
   - Maintain consistency with existing metrics patterns

### Non-Functional Requirements

1. **Performance**
   - Minimal overhead on request processing (<1ms per request)
   - Thread-safe operations (async-safe)
   - Efficient memory usage (bounded data structures)
   - Automatic cleanup of old metrics data

2. **Reliability**
   - Metrics collection should not fail requests
   - Graceful degradation if metrics collection fails
   - No blocking operations in request path

3. **Scalability**
   - Support high request volumes
   - Bounded memory usage (sliding windows, max data retention)
   - Efficient aggregation algorithms

4. **Maintainability**
   - Clear separation of concerns
   - Well-documented API
   - Type hints and validation

## Design Decisions

### Architecture

**Facade Pattern:**
- `MetricsTracker` acts as a facade over existing metrics classes
- Delegates to `ErrorMetrics`, `PerformanceMetrics`, `LLMMetrics`
- Provides unified interface for middleware

**Request Tracking:**
- Track active requests in memory (request_id -> request_data)
- Store completed requests in bounded collections (deque with maxlen)
- Aggregate metrics on-demand rather than pre-computing

**Data Retention:**
- Keep detailed request data for last 1 hour (configurable)
- Keep aggregated statistics for last 24 hours
- Keep summary statistics indefinitely (reset on restart)

### Storage Strategy

**In-Memory Only (Phase 1):**
- All metrics stored in memory
- Suitable for single-instance deployments
- Fast access, no external dependencies

**Future: Persistent Storage (Phase 2):**
- Optional persistence to storage service
- Metrics export/import capabilities
- Historical metrics analysis

### Metrics Granularity

**Request-Level:**
- Individual request tracking (request_id)
- Method, path, status code, processing time
- Error details if applicable

**Endpoint-Level:**
- Aggregated by (method, path) combination
- Statistics: count, success rate, avg/min/max/p95/p99 times
- Error breakdown by status code

**Time-Based:**
- Per-minute aggregates (last hour)
- Per-hour aggregates (last 24 hours)
- Per-day aggregates (last 30 days)

## Implementation Specification

### 1. Data Models

**File: `src/core/errors/metrics.py` (additions)**

```python
from dataclasses import dataclass, field
from typing import Dict, Optional, List
from datetime import datetime
from collections import defaultdict, deque

@dataclass
class RequestMetrics:
    """Metrics for a single HTTP request"""
    request_id: str
    method: str
    path: str
    start_time: datetime
    end_time: Optional[datetime] = None
    status_code: Optional[int] = None
    processing_time: Optional[float] = None
    success: Optional[bool] = None
    error: Optional[str] = None
    llm_requests: List['LLMRequestMetrics'] = field(default_factory=list)

@dataclass
class LLMRequestMetrics:
    """Metrics for a single LLM request within an HTTP request"""
    request_id: str
    parent_request_id: str
    provider: str
    model: str
    start_time: datetime
    end_time: Optional[datetime] = None
    cost: Optional[float] = None
    tokens_input: Optional[int] = None
    tokens_output: Optional[int] = None
    processing_time: Optional[float] = None
    success: Optional[bool] = None

@dataclass
class EndpointMetrics:
    """Aggregated metrics for an endpoint (method + path)"""
    method: str
    path: str
    total_requests: int = 0
    successful_requests: int = 0
    failed_requests: int = 0
    processing_times: List[float] = field(default_factory=list)
    status_codes: Dict[int, int] = field(default_factory=lambda: defaultdict(int))
    total_llm_cost: float = 0.0
    total_llm_tokens: int = 0
    last_request_time: Optional[datetime] = None
    
    @property
    def success_rate(self) -> float:
        if self.total_requests == 0:
            return 0.0
        return (self.successful_requests / self.total_requests) * 100.0
    
    @property
    def avg_processing_time(self) -> float:
        if not self.processing_times:
            return 0.0
        return sum(self.processing_times) / len(self.processing_times)
    
    @property
    def p95_processing_time(self) -> float:
        if len(self.processing_times) < 20:
            return max(self.processing_times) if self.processing_times else 0.0
        sorted_times = sorted(self.processing_times)
        index = int(len(sorted_times) * 0.95)
        return sorted_times[index]
    
    @property
    def p99_processing_time(self) -> float:
        if len(self.processing_times) < 100:
            return max(self.processing_times) if self.processing_times else 0.0
        sorted_times = sorted(self.processing_times)
        index = int(len(sorted_times) * 0.99)
        return sorted_times[index]
```

### 2. MetricsTracker Implementation

**File: `src/core/errors/metrics.py` (additions)**

```python
class MetricsTracker:
    """
    Unified metrics tracker for HTTP and LLM requests.
    
    Acts as a facade over ErrorMetrics, PerformanceMetrics, and LLMMetrics,
    providing a unified interface for middleware and API endpoints.
    """
    
    def __init__(
        self,
        max_request_history: int = 10000,
        max_endpoint_history: int = 1000,
        retention_hours: int = 1
    ):
        """
        Initialize metrics tracker.
        
        Args:
            max_request_history: Maximum number of individual requests to track
            max_endpoint_history: Maximum processing times per endpoint to keep
            retention_hours: Hours of detailed request data to retain
        """
        # Existing metrics instances
        self.error_metrics = get_error_metrics()
        self.performance_metrics = get_performance_metrics()
        self.llm_metrics = get_llm_metrics()
        
        # Request tracking
        self._active_requests: Dict[str, RequestMetrics] = {}
        self._request_history: deque = deque(maxlen=max_request_history)
        
        # Endpoint aggregation
        self._endpoint_metrics: Dict[str, EndpointMetrics] = {}
        self._max_endpoint_history = max_endpoint_history
        
        # Time-based retention
        self._retention_hours = retention_hours
        self._last_cleanup = datetime.now()
        
        # Thread safety
        self._lock = threading.Lock()
    
    def start_request(self, request_id: str, method: str, path: str) -> None:
        """
        Track HTTP request start.
        
        Args:
            request_id: Unique request identifier
            method: HTTP method (GET, POST, etc.)
            path: Request path
        """
        try:
            with self._lock:
                request_metrics = RequestMetrics(
                    request_id=request_id,
                    method=method,
                    path=path,
                    start_time=datetime.now()
                )
                self._active_requests[request_id] = request_metrics
                
                # Record in performance metrics
                self.performance_metrics.record_operation(
                    operation=f"{method} {path}",
                    duration_ms=0.0,  # Will be updated on end
                    component="api",
                    success=True,
                    metadata={"request_id": request_id}
                )
        except Exception as e:
            # Don't fail requests if metrics collection fails
            logger.warning(f"Failed to track request start: {e}", exc_info=True)
    
    def end_request(
        self,
        request_id: str,
        success: bool,
        status_code: int,
        processing_time: float,
        error: Optional[str] = None
    ) -> None:
        """
        Track HTTP request completion.
        
        Args:
            request_id: Unique request identifier
            success: Whether request succeeded
            status_code: HTTP status code
            processing_time: Request processing time in seconds
            error: Error message if request failed
        """
        try:
            with self._lock:
                # Get active request
                request_metrics = self._active_requests.pop(request_id, None)
                if not request_metrics:
                    # Request not tracked (shouldn't happen, but handle gracefully)
                    logger.warning(f"Request {request_id} not found in active requests")
                    return
                
                # Update request metrics
                request_metrics.end_time = datetime.now()
                request_metrics.status_code = status_code
                request_metrics.processing_time = processing_time
                request_metrics.success = success
                request_metrics.error = error
                
                # Add to history
                self._request_history.append(request_metrics)
                
                # Update endpoint metrics
                endpoint_key = f"{request_metrics.method} {request_metrics.path}"
                if endpoint_key not in self._endpoint_metrics:
                    self._endpoint_metrics[endpoint_key] = EndpointMetrics(
                        method=request_metrics.method,
                        path=request_metrics.path
                    )
                
                endpoint = self._endpoint_metrics[endpoint_key]
                endpoint.total_requests += 1
                if success:
                    endpoint.successful_requests += 1
                else:
                    endpoint.failed_requests += 1
                
                endpoint.status_codes[status_code] += 1
                endpoint.processing_times.append(processing_time * 1000)  # Convert to ms
                endpoint.last_request_time = datetime.now()
                
                # Keep only recent processing times
                if len(endpoint.processing_times) > self._max_endpoint_history:
                    endpoint.processing_times = endpoint.processing_times[-self._max_endpoint_history:]
                
                # Add LLM costs if any
                for llm_req in request_metrics.llm_requests:
                    if llm_req.cost:
                        endpoint.total_llm_cost += llm_req.cost
                    if llm_req.tokens_input and llm_req.tokens_output:
                        endpoint.total_llm_tokens += (llm_req.tokens_input + llm_req.tokens_output)
                
                # Record in error metrics if failed
                if not success:
                    error_type = f"HTTP_{status_code}"
                    self.error_metrics.record_error(
                        error_type=error_type,
                        component="api",
                        severity=ErrorSeverity.MEDIUM if status_code < 500 else ErrorSeverity.HIGH,
                        category=ErrorCategory.API,
                        details={
                            "method": request_metrics.method,
                            "path": request_metrics.path,
                            "status_code": status_code,
                            "error": error
                        }
                    )
                
                # Record in performance metrics
                self.performance_metrics.record_operation(
                    operation=f"{request_metrics.method} {request_metrics.path}",
                    duration_ms=processing_time * 1000,
                    component="api",
                    success=success,
                    metadata={
                        "request_id": request_id,
                        "status_code": status_code
                    }
                )
                
                # Periodic cleanup
                self._cleanup_old_data()
                
        except Exception as e:
            # Don't fail requests if metrics collection fails
            logger.warning(f"Failed to track request end: {e}", exc_info=True)
    
    def start_llm_request(
        self,
        request_id: str,
        provider: str,
        model: str
    ) -> None:
        """
        Track LLM request start.
        
        Args:
            request_id: Unique request identifier (should match parent HTTP request)
            provider: LLM provider name
            model: LLM model name
        """
        try:
            with self._lock:
                # Find parent HTTP request
                parent_request = self._active_requests.get(request_id)
                if not parent_request:
                    # LLM request without parent HTTP request (shouldn't happen)
                    logger.warning(f"LLM request {request_id} has no parent HTTP request")
                    return
                
                # Create LLM request metrics
                llm_metrics = LLMRequestMetrics(
                    request_id=f"{request_id}_llm_{len(parent_request.llm_requests)}",
                    parent_request_id=request_id,
                    provider=provider,
                    model=model,
                    start_time=datetime.now()
                )
                
                parent_request.llm_requests.append(llm_metrics)
                
        except Exception as e:
            logger.warning(f"Failed to track LLM request start: {e}", exc_info=True)
    
    def end_llm_request(
        self,
        request_id: str,
        cost: Optional[float] = None,
        tokens_used: Optional[int] = None,
        processing_time: Optional[float] = None
    ) -> None:
        """
        Track LLM request completion.
        
        Args:
            request_id: Unique request identifier (should match parent HTTP request)
            cost: LLM request cost
            tokens_used: Total tokens used (input + output)
            processing_time: LLM processing time in seconds
        """
        try:
            with self._lock:
                # Find parent HTTP request
                parent_request = self._active_requests.get(request_id)
                if not parent_request or not parent_request.llm_requests:
                    logger.warning(f"LLM request {request_id} not found or has no active LLM requests")
                    return
                
                # Get most recent LLM request (last one started)
                llm_metrics = parent_request.llm_requests[-1]
                llm_metrics.end_time = datetime.now()
                llm_metrics.cost = cost
                llm_metrics.processing_time = processing_time
                
                # Split tokens (assume 50/50 if not specified)
                if tokens_used:
                    llm_metrics.tokens_input = tokens_used // 2
                    llm_metrics.tokens_output = tokens_used - llm_metrics.tokens_input
                
                # Record in LLM metrics
                self.llm_metrics.record_llm_request(
                    provider=llm_metrics.provider,
                    model=llm_metrics.model,
                    tokens_input=llm_metrics.tokens_input or 0,
                    tokens_output=llm_metrics.tokens_output or 0,
                    cost=cost or 0.0,
                    duration_ms=(processing_time * 1000) if processing_time else 0.0,
                    success=True  # Assume success if we got here
                )
                
        except Exception as e:
            logger.warning(f"Failed to track LLM request end: {e}", exc_info=True)
    
    def get_summary(self) -> Dict[str, Any]:
        """
        Get overall metrics summary.
        
        Returns:
            Dictionary with summary statistics
        """
        with self._lock:
            total_requests = len(self._request_history)
            recent_requests = [
                r for r in self._request_history
                if r.end_time and (datetime.now() - r.end_time).total_seconds() < 3600
            ]
            
            return {
                "total_requests": total_requests,
                "recent_requests_1h": len(recent_requests),
                "active_requests": len(self._active_requests),
                "endpoints_tracked": len(self._endpoint_metrics),
                "error_summary": self.error_metrics.get_error_summary(),
                "performance_summary": self.performance_metrics.get_performance_summary(),
                "llm_summary": self.llm_metrics.get_llm_summary()
            }
    
    def get_endpoint_metrics(self, method: Optional[str] = None, path: Optional[str] = None) -> Dict[str, Any]:
        """
        Get metrics for specific endpoint(s).
        
        Args:
            method: HTTP method to filter by (optional)
            path: Path to filter by (optional)
            
        Returns:
            Dictionary with endpoint metrics
        """
        with self._lock:
            if method and path:
                endpoint_key = f"{method} {path}"
                endpoint = self._endpoint_metrics.get(endpoint_key)
                if endpoint:
                    return {
                        "method": endpoint.method,
                        "path": endpoint.path,
                        "total_requests": endpoint.total_requests,
                        "successful_requests": endpoint.successful_requests,
                        "failed_requests": endpoint.failed_requests,
                        "success_rate": endpoint.success_rate,
                        "avg_processing_time_ms": endpoint.avg_processing_time,
                        "p95_processing_time_ms": endpoint.p95_processing_time,
                        "p99_processing_time_ms": endpoint.p99_processing_time,
                        "min_processing_time_ms": min(endpoint.processing_times) if endpoint.processing_times else 0.0,
                        "max_processing_time_ms": max(endpoint.processing_times) if endpoint.processing_times else 0.0,
                        "status_codes": dict(endpoint.status_codes),
                        "total_llm_cost": endpoint.total_llm_cost,
                        "total_llm_tokens": endpoint.total_llm_tokens,
                        "last_request_time": endpoint.last_request_time.isoformat() if endpoint.last_request_time else None
                    }
                return {}
            
            # Return all endpoints
            return {
                key: {
                    "method": endpoint.method,
                    "path": endpoint.path,
                    "total_requests": endpoint.total_requests,
                    "success_rate": endpoint.success_rate,
                    "avg_processing_time_ms": endpoint.avg_processing_time,
                    "total_llm_cost": endpoint.total_llm_cost
                }
                for key, endpoint in self._endpoint_metrics.items()
            }
    
    def _cleanup_old_data(self) -> None:
        """Clean up old request data (called periodically)"""
        # Cleanup every 5 minutes
        if (datetime.now() - self._last_cleanup).total_seconds() < 300:
            return
        
        cutoff_time = datetime.now() - timedelta(hours=self._retention_hours)
        
        # Remove old requests from history (deque handles this automatically via maxlen)
        # But we can clean up endpoint metrics if needed
        
        self._last_cleanup = datetime.now()


# Global MetricsTracker instance
_metrics_tracker: Optional[MetricsTracker] = None


def get_metrics_tracker() -> MetricsTracker:
    """Get global MetricsTracker instance"""
    global _metrics_tracker
    if _metrics_tracker is None:
        _metrics_tracker = MetricsTracker()
    return _metrics_tracker
```

### 3. Update Main Application

**File: `src/core/main.py`**

**Changes:**

1. **Uncomment and initialize MetricsTracker:**
   ```python
   from src.core.errors.metrics import get_metrics_tracker
   
   # In lifespan or before middleware setup:
   metrics_tracker = get_metrics_tracker()
   setup_api_middleware(app, metrics_tracker)
   ```

2. **Remove TODO comments**

### 4. Update Middleware

**File: `src/core/api/middleware.py`**

**Changes:**

1. **Remove TODO comments**
2. **Update imports:**
   ```python
   from ..errors.metrics import MetricsTracker
   ```

### 5. Update Decorators

**File: `src/core/api/decorators.py`**

**Changes:**

1. **Remove TODO comment** (line 26)
2. **Optionally integrate MetricsTracker** if decorators need metrics (currently not used)

### 6. API Endpoint for Metrics (Optional)

**File: `src/core/api/routes/system.py` (new or existing)**

Add endpoint to expose metrics:

```python
@router.get("/metrics", tags=["system"])
async def get_metrics(
    endpoint: Optional[str] = None,
    summary: bool = True
):
    """
    Get system metrics.
    
    Args:
        endpoint: Optional endpoint filter (format: "METHOD /path")
        summary: If True, return summary; if False, return detailed metrics
    """
    tracker = get_metrics_tracker()
    
    if endpoint:
        method, path = endpoint.split(" ", 1)
        return tracker.get_endpoint_metrics(method=method, path=path)
    
    if summary:
        return tracker.get_summary()
    
    return {
        "summary": tracker.get_summary(),
        "endpoints": tracker.get_endpoint_metrics()
    }
```

### 7. Configuration

**File: `src/config/settings.py`**

**Add optional settings:**

```python
# Metrics Configuration
METRICS_ENABLED = os.getenv("METRICS_ENABLED", "true").lower() in ("true", "1", "t")
METRICS_MAX_REQUEST_HISTORY = int(os.getenv("METRICS_MAX_REQUEST_HISTORY", "10000"))
METRICS_MAX_ENDPOINT_HISTORY = int(os.getenv("METRICS_MAX_ENDPOINT_HISTORY", "1000"))
METRICS_RETENTION_HOURS = int(os.getenv("METRICS_RETENTION_HOURS", "1"))
```

**File: `env.template`**

**Add:**

```bash
# Metrics Configuration
METRICS_ENABLED=true
METRICS_MAX_REQUEST_HISTORY=10000
METRICS_MAX_ENDPOINT_HISTORY=1000
METRICS_RETENTION_HOURS=1
```

## Integration Points

### 1. Existing Metrics Classes

- **ErrorMetrics**: Used for error tracking
- **PerformanceMetrics**: Used for operation performance tracking
- **LLMMetrics**: Used for LLM-specific metrics

### 2. Middleware Integration

- `RequestTrackingMiddleware` calls `start_request()` and `end_request()`
- `LLMRequestMiddleware` calls `start_llm_request()` and `end_llm_request()`

### 3. Logging

- Uses existing logging infrastructure
- Logs warnings if metrics collection fails (doesn't fail requests)

### 4. Thread Safety

- Uses `threading.Lock()` for thread-safe operations
- All public methods are thread-safe

## Testing Considerations

### Unit Tests

1. **MetricsTracker Tests:**
   - Request tracking (start/end)
   - LLM request tracking
   - Endpoint aggregation
   - Data cleanup
   - Thread safety

2. **Endpoint Metrics Tests:**
   - Statistics calculation (avg, p95, p99)
   - Success rate calculation
   - Status code aggregation

### Integration Tests

1. **Middleware Integration:**
   - Verify metrics are collected during request processing
   - Verify LLM metrics are linked to HTTP requests

2. **Metrics Exposure:**
   - Test metrics API endpoint (if implemented)
   - Verify summary and detailed metrics

### Performance Tests

1. **Overhead Measurement:**
   - Measure metrics collection overhead
   - Verify <1ms per request

2. **Memory Usage:**
   - Verify bounded memory usage
   - Test cleanup behavior

## Migration Plan

### Phase 1: Implementation (Current)
- Implement MetricsTracker class
- Integrate with middleware
- Update main application
- Remove TODO comments

### Phase 2: Metrics API (Optional)
- Add metrics endpoint
- Add metrics dashboard (future)
- Add metrics export (future)

### Phase 3: Persistence (Future)
- Optional metrics persistence
- Historical metrics analysis
- Metrics aggregation service

## Success Criteria

1. ✅ MetricsTracker class implemented
2. ✅ All TODO comments removed
3. ✅ Middleware successfully tracks requests
4. ✅ LLM requests are tracked and linked to HTTP requests
5. ✅ Endpoint-level metrics are aggregated
6. ✅ Integration with existing metrics classes works
7. ✅ Performance overhead is minimal (<1ms per request)
8. ✅ Thread-safe operations
9. ✅ Memory usage is bounded
10. ✅ No request failures due to metrics collection

## Open Questions / Future Enhancements

1. **Metrics Persistence:**
   - Should metrics be persisted to storage?
   - How long should historical metrics be kept?

2. **Metrics Export:**
   - Export to Prometheus format?
   - Export to other monitoring systems?

3. **Real-time Metrics:**
   - WebSocket endpoint for real-time metrics?
   - Metrics streaming?

4. **Advanced Aggregations:**
   - Per-user metrics (if authentication is added)
   - Per-domain metrics
   - Custom metric dimensions

5. **Alerting:**
   - Alert on high error rates?
   - Alert on slow endpoints?
   - Alert on high LLM costs?

## Dependencies

### Existing Dependencies

- `threading` - Thread safety (stdlib)
- `collections.deque` - Bounded collections (stdlib)
- `datetime` - Time tracking (stdlib)
- Existing metrics classes (`ErrorMetrics`, `PerformanceMetrics`, `LLMMetrics`)

### No New Dependencies

- Uses only standard library and existing codebase components

## Implementation Order

1. Add data models (`RequestMetrics`, `LLMRequestMetrics`, `EndpointMetrics`) to `src/core/errors/metrics.py`
2. Implement `MetricsTracker` class in `src/core/errors/metrics.py`
3. Add `get_metrics_tracker()` function
4. Update `src/core/main.py` to initialize and use MetricsTracker
5. Update `src/core/api/middleware.py` to remove TODO comments
6. Update `src/core/api/decorators.py` to remove TODO comment
7. Add configuration options (optional)
8. Write unit tests
9. Write integration tests
10. Add metrics API endpoint (optional, Phase 2)

