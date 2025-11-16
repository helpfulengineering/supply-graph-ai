# Caching & Rate Limiting Implementation Specification

## Overview

This specification defines the implementation plan for completing the caching and rate limiting decorators that are currently placeholders. These features are critical for API performance, security, and resource management.

## Current State Analysis

### Issue 1: Cache Response Decorator Placeholder

**Location**: `src/core/api/decorators.py:311`

**Current Implementation:**
```python
def cache_response(ttl_seconds: int = 300, cache_key_prefix: str = None):
    # ...
    # TODO: Implement actual caching logic
    # This is a placeholder for future implementation
    # For now, just execute the function normally
    return await func(*args, **kwargs)
```

**Problems:**
- No caching logic implemented
- Decorator exists but doesn't cache responses
- Missing cache key generation
- Missing cache storage/retrieval
- Missing TTL enforcement

**Context:**
- Decorator accepts `ttl_seconds` and `cache_key_prefix` parameters
- Should cache API responses based on request parameters
- Should respect TTL for cache invalidation

### Issue 2: Rate Limit Decorator Placeholder

**Location**: `src/core/api/decorators.py:344`

**Current Implementation:**
```python
def rate_limit(requests_per_minute: int = 60, per_user: bool = False):
    # ...
    # TODO: Implement actual rate limiting logic
    # This is a placeholder for future implementation
    # For now, just execute the function normally
    return await func(*args, **kwargs)
```

**Problems:**
- No rate limiting logic implemented
- Decorator exists but doesn't enforce limits
- Missing per-user rate limiting (when `per_user=True`)
- Missing rate limit tracking
- Missing rate limit headers in responses

**Context:**
- Decorator accepts `requests_per_minute` and `per_user` parameters
- Should track requests per IP or per user
- Should return 429 status when limit exceeded
- Should include rate limit headers in responses

### Existing Infrastructure

**RateLimitingMiddleware** (`src/core/api/middleware.py:243`):
- Implements basic IP-based rate limiting
- Uses in-memory dictionary (not suitable for production/multi-instance)
- Comment: "In production, use Redis or similar"
- Currently active in middleware stack

**Caching Examples:**
- `GitHubExtractor` has file-based caching for API responses
- `FileCategorizationService` has in-memory cache for categorization results
- `LLMConfig` has `response_caching_enabled` and `cache_ttl_seconds` settings

## Requirements

### Functional Requirements

1. **Response Caching**
   - Cache API responses based on request parameters
   - Support configurable TTL per endpoint
   - Generate cache keys from request (method, path, query params, body)
   - Support cache invalidation
   - Support cache key prefixes for namespacing
   - Return cached responses when available and valid

2. **Rate Limiting**
   - Track requests per IP address (default)
   - Track requests per authenticated user (when `per_user=True`)
   - Enforce requests per minute limit
   - Return 429 status code when limit exceeded
   - Include rate limit headers in responses (X-RateLimit-*)
   - Support different limits per endpoint

3. **Integration**
   - Work with existing middleware
   - Integrate with authentication (when available)
   - Support async operations
   - Thread-safe operations

### Non-Functional Requirements

1. **Performance**
   - Cache lookup should be fast (<1ms)
   - Rate limit check should be fast (<1ms)
   - Minimal overhead on request processing

2. **Scalability**
   - In-memory implementation for Phase 1 (single instance)
   - Design for future Redis/distributed cache support
   - Bounded memory usage (cache size limits, TTL cleanup)

3. **Reliability**
   - Cache failures should not break requests
   - Rate limit failures should fail securely (allow request)
   - Graceful degradation

4. **Maintainability**
   - Clear separation of concerns
   - Configurable behavior
   - Well-documented

## Design Decisions

### Caching Strategy

**Phase 1: In-Memory Cache**
- Use `functools.lru_cache` or custom in-memory cache
- Store cache entries with TTL
- Automatic cleanup of expired entries
- Bounded cache size (max entries)

**Cache Key Generation:**
- Include: HTTP method, path, query parameters, request body hash
- Exclude: Headers (except auth if needed), timestamps
- Use hash of serialized request parameters

**Cache Storage:**
- In-memory dictionary: `Dict[str, Tuple[Any, datetime]]` (key -> (value, expiry))
- Periodic cleanup of expired entries
- Max cache size with LRU eviction

**Future: Distributed Cache (Phase 2)**
- Redis support for multi-instance deployments
- Cache abstraction layer for easy migration

### Rate Limiting Strategy

**Phase 1: In-Memory Rate Limiting**
- Use sliding window algorithm
- Track requests per identifier (IP or user ID)
- Store: `Dict[str, List[float]]` (identifier -> list of request timestamps)

**Sliding Window:**
- Track request timestamps for last minute
- Count requests within window
- Remove timestamps older than 1 minute

**Per-User Rate Limiting:**
- When `per_user=True` and user is authenticated, use user ID
- Fallback to IP if user not authenticated
- Different limits can be configured per user type

**Rate Limit Headers:**
- `X-RateLimit-Limit`: Maximum requests per minute
- `X-RateLimit-Remaining`: Remaining requests in current window
- `X-RateLimit-Reset`: Unix timestamp when limit resets

**Future: Distributed Rate Limiting (Phase 2)**
- Redis-based rate limiting for multi-instance deployments
- Shared rate limit state across instances

### Integration with Middleware

**Relationship:**
- Middleware provides global rate limiting (all endpoints)
- Decorator provides endpoint-specific rate limiting
- Both can be used together (decorator takes precedence for specific endpoints)

**Cache Decorator:**
- Works independently of middleware
- Can be applied to specific endpoints
- Middleware doesn't interfere with caching

## Implementation Specification

### 1. Cache Service

**File: `src/core/services/cache_service.py` (new file)**

```python
"""
Cache service for API response caching.

Provides in-memory caching with TTL support and automatic cleanup.
"""

import time
import hashlib
import json
from typing import Dict, Any, Optional, Tuple
from datetime import datetime, timedelta
from collections import OrderedDict
from threading import Lock
import asyncio

from ..utils.logging import get_logger

logger = get_logger(__name__)


class CacheEntry:
    """Single cache entry with value and expiry time"""
    
    def __init__(self, value: Any, ttl_seconds: int):
        self.value = value
        self.created_at = datetime.now()
        self.expires_at = self.created_at + timedelta(seconds=ttl_seconds)
    
    def is_expired(self) -> bool:
        """Check if cache entry has expired"""
        return datetime.now() >= self.expires_at


class CacheService:
    """
    In-memory cache service with TTL support and automatic cleanup.
    
    Thread-safe cache implementation suitable for single-instance deployments.
    For multi-instance deployments, use Redis-based cache (Phase 2).
    """
    
    def __init__(self, max_size: int = 1000, cleanup_interval_seconds: int = 60):
        """
        Initialize cache service.
        
        Args:
            max_size: Maximum number of cache entries (LRU eviction)
            cleanup_interval_seconds: How often to clean expired entries
        """
        self.max_size = max_size
        self.cleanup_interval = cleanup_interval_seconds
        self._cache: OrderedDict[str, CacheEntry] = OrderedDict()
        self._lock = Lock()
        self._last_cleanup = datetime.now()
    
    def get(self, key: str) -> Optional[Any]:
        """
        Get value from cache.
        
        Args:
            key: Cache key
            
        Returns:
            Cached value if found and not expired, None otherwise
        """
        with self._lock:
            # Periodic cleanup
            self._cleanup_if_needed()
            
            if key not in self._cache:
                return None
            
            entry = self._cache[key]
            
            # Check if expired
            if entry.is_expired():
                del self._cache[key]
                return None
            
            # Move to end (LRU)
            self._cache.move_to_end(key)
            
            return entry.value
    
    def set(self, key: str, value: Any, ttl_seconds: int = 300) -> None:
        """
        Store value in cache.
        
        Args:
            key: Cache key
            value: Value to cache
            ttl_seconds: Time to live in seconds
        """
        with self._lock:
            # Periodic cleanup
            self._cleanup_if_needed()
            
            # Evict if at max size (remove oldest)
            if len(self._cache) >= self.max_size and key not in self._cache:
                self._cache.popitem(last=False)  # Remove oldest
            
            # Store entry
            entry = CacheEntry(value, ttl_seconds)
            self._cache[key] = entry
            self._cache.move_to_end(key)  # Move to end (most recently used)
    
    def delete(self, key: str) -> None:
        """Delete entry from cache"""
        with self._lock:
            self._cache.pop(key, None)
    
    def clear(self) -> None:
        """Clear all cache entries"""
        with self._lock:
            self._cache.clear()
    
    def _cleanup_if_needed(self) -> None:
        """Clean up expired entries if cleanup interval has passed"""
        now = datetime.now()
        if (now - self._last_cleanup).total_seconds() < self.cleanup_interval:
            return
        
        # Remove expired entries
        expired_keys = [
            key for key, entry in self._cache.items()
            if entry.is_expired()
        ]
        
        for key in expired_keys:
            del self._cache[key]
        
        self._last_cleanup = now
        
        if expired_keys:
            logger.debug(f"Cleaned up {len(expired_keys)} expired cache entries")
    
    def get_stats(self) -> Dict[str, Any]:
        """Get cache statistics"""
        with self._lock:
            return {
                "size": len(self._cache),
                "max_size": self.max_size,
                "entries": [
                    {
                        "key": key,
                        "created_at": entry.created_at.isoformat(),
                        "expires_at": entry.expires_at.isoformat(),
                        "is_expired": entry.is_expired()
                    }
                    for key, entry in self._cache.items()
                ]
            }


# Global cache service instance
_cache_service: Optional[CacheService] = None


def get_cache_service() -> CacheService:
    """Get global cache service instance"""
    global _cache_service
    if _cache_service is None:
        _cache_service = CacheService()
    return _cache_service
```

### 2. Rate Limiting Service

**File: `src/core/services/rate_limit_service.py` (new file)**

```python
"""
Rate limiting service for API endpoints.

Provides sliding window rate limiting with per-IP and per-user support.
"""

import time
from typing import Dict, List, Optional, Tuple
from collections import defaultdict
from threading import Lock
from datetime import datetime

from ..utils.logging import get_logger

logger = get_logger(__name__)


class RateLimitService:
    """
    Rate limiting service using sliding window algorithm.
    
    Thread-safe rate limiting suitable for single-instance deployments.
    For multi-instance deployments, use Redis-based rate limiting (Phase 2).
    """
    
    def __init__(self, cleanup_interval_seconds: int = 60):
        """
        Initialize rate limit service.
        
        Args:
            cleanup_interval_seconds: How often to clean old request timestamps
        """
        self.cleanup_interval = cleanup_interval_seconds
        # Store request timestamps per identifier (IP or user ID)
        self._request_timestamps: Dict[str, List[float]] = defaultdict(list)
        self._lock = Lock()
        self._last_cleanup = time.time()
    
    def check_rate_limit(
        self,
        identifier: str,
        requests_per_minute: int,
        current_time: Optional[float] = None
    ) -> Tuple[bool, Dict[str, int]]:
        """
        Check if request is within rate limit.
        
        Args:
            identifier: Unique identifier (IP address or user ID)
            requests_per_minute: Maximum requests per minute
            current_time: Current timestamp (for testing)
            
        Returns:
            Tuple of (is_allowed, rate_limit_info)
            rate_limit_info contains: limit, remaining, reset_time
        """
        if current_time is None:
            current_time = time.time()
        
        with self._lock:
            # Periodic cleanup
            self._cleanup_if_needed(current_time)
            
            # Get request timestamps for this identifier
            timestamps = self._request_timestamps[identifier]
            
            # Remove timestamps older than 1 minute
            cutoff_time = current_time - 60.0
            timestamps[:] = [ts for ts in timestamps if ts > cutoff_time]
            
            # Check if limit exceeded
            request_count = len(timestamps)
            is_allowed = request_count < requests_per_minute
            
            # Calculate reset time (1 minute from oldest request, or now if no requests)
            if timestamps:
                oldest_request = min(timestamps)
                reset_time = int(oldest_request + 60.0)
            else:
                reset_time = int(current_time + 60.0)
            
            # If allowed, add current request timestamp
            if is_allowed:
                timestamps.append(current_time)
            
            rate_limit_info = {
                "limit": requests_per_minute,
                "remaining": max(0, requests_per_minute - request_count - (1 if is_allowed else 0)),
                "reset_time": reset_time
            }
            
            return is_allowed, rate_limit_info
    
    def _cleanup_if_needed(self, current_time: float) -> None:
        """Clean up old request timestamps if cleanup interval has passed"""
        if current_time - self._last_cleanup < self.cleanup_interval:
            return
        
        # Remove timestamps older than 1 minute for all identifiers
        cutoff_time = current_time - 60.0
        identifiers_to_remove = []
        
        for identifier, timestamps in self._request_timestamps.items():
            # Remove old timestamps
            self._request_timestamps[identifier] = [
                ts for ts in timestamps if ts > cutoff_time
            ]
            
            # Remove identifier if no timestamps left
            if not self._request_timestamps[identifier]:
                identifiers_to_remove.append(identifier)
        
        for identifier in identifiers_to_remove:
            del self._request_timestamps[identifier]
        
        self._last_cleanup = current_time
    
    def get_stats(self) -> Dict[str, Any]:
        """Get rate limiting statistics"""
        with self._lock:
            current_time = time.time()
            cutoff_time = current_time - 60.0
            
            active_identifiers = {}
            for identifier, timestamps in self._request_timestamps.items():
                recent_timestamps = [ts for ts in timestamps if ts > cutoff_time]
                if recent_timestamps:
                    active_identifiers[identifier] = len(recent_timestamps)
            
            return {
                "active_identifiers": len(active_identifiers),
                "total_identifiers": len(self._request_timestamps),
                "identifier_counts": active_identifiers
            }


# Global rate limit service instance
_rate_limit_service: Optional[RateLimitService] = None


def get_rate_limit_service() -> RateLimitService:
    """Get global rate limit service instance"""
    global _rate_limit_service
    if _rate_limit_service is None:
        _rate_limit_service = RateLimitService()
    return _rate_limit_service
```

### 3. Update Cache Response Decorator

**File: `src/core/api/decorators.py`**

**Update `cache_response` decorator:**

```python
def cache_response(ttl_seconds: int = 300, cache_key_prefix: str = None):
    """
    Decorator for caching API responses.
    
    Args:
        ttl_seconds: Time to live for cached responses
        cache_key_prefix: Prefix for cache keys
        
    Returns:
        Decorated function
    """
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        async def wrapper(*args, **kwargs):
            from ..services.cache_service import get_cache_service
            from fastapi import Request
            import hashlib
            import json
            
            # Extract request object if available
            request = None
            for arg in args:
                if isinstance(arg, Request):
                    request = arg
                    break
            
            request_id = getattr(request.state, 'request_id', None) if request else None
            
            # Generate cache key
            cache_key = _generate_cache_key(
                func=func,
                request=request,
                args=args,
                kwargs=kwargs,
                prefix=cache_key_prefix
            )
            
            # Try to get from cache
            cache_service = get_cache_service()
            cached_response = cache_service.get(cache_key)
            
            if cached_response is not None:
                logger.debug(
                    f"Cache hit for {func.__name__}",
                    extra={"request_id": request_id, "cache_key": cache_key}
                )
                # Add cache header
                if isinstance(cached_response, dict):
                    cached_response["_cached"] = True
                return cached_response
            
            # Cache miss - execute function
            logger.debug(
                f"Cache miss for {func.__name__}",
                extra={"request_id": request_id, "cache_key": cache_key}
            )
            result = await func(*args, **kwargs)
            
            # Cache the result
            try:
                cache_service.set(cache_key, result, ttl_seconds=ttl_seconds)
            except Exception as e:
                # Don't fail request if caching fails
                logger.warning(
                    f"Failed to cache response for {func.__name__}: {e}",
                    extra={"request_id": request_id, "cache_key": cache_key}
                )
            
            return result
        
        return wrapper
    return decorator


def _generate_cache_key(
    func: Callable,
    request: Optional[Request],
    args: tuple,
    kwargs: dict,
    prefix: Optional[str] = None
) -> str:
    """
    Generate cache key from function and request parameters.
    
    Args:
        func: Function being cached
        request: FastAPI request object
        args: Function arguments
        kwargs: Function keyword arguments
        prefix: Optional cache key prefix
        
    Returns:
        Cache key string
    """
    import hashlib
    import json
    
    # Build key components
    key_parts = []
    
    # Add prefix if provided
    if prefix:
        key_parts.append(prefix)
    
    # Add function name
    key_parts.append(func.__name__)
    
    # Add request method and path
    if request:
        key_parts.append(request.method)
        key_parts.append(str(request.url.path))
        
        # Add query parameters (sorted for consistency)
        if request.query_params:
            query_dict = dict(request.query_params)
            key_parts.append(json.dumps(query_dict, sort_keys=True))
        
        # Add request body hash (if POST/PUT/PATCH)
        if request.method in ["POST", "PUT", "PATCH"]:
            # Note: Body may have been consumed, so we use kwargs if available
            if "request" in kwargs:
                # Try to get body from kwargs
                body_data = kwargs.get("request")
                if body_data:
                    try:
                        body_str = json.dumps(body_data, sort_keys=True, default=str)
                        body_hash = hashlib.md5(body_str.encode()).hexdigest()
                        key_parts.append(body_hash)
                    except (TypeError, ValueError):
                        pass
    
    # Add non-request kwargs (excluding request object)
    other_kwargs = {
        k: v for k, v in kwargs.items()
        if k != "request" and k != "http_request"
    }
    if other_kwargs:
        key_parts.append(json.dumps(other_kwargs, sort_keys=True, default=str))
    
    # Combine and hash
    key_string = "|".join(str(part) for part in key_parts)
    key_hash = hashlib.md5(key_string.encode()).hexdigest()
    
    return f"cache:{key_hash}"
```

### 4. Update Rate Limit Decorator

**File: `src/core/api/decorators.py`**

**Update `rate_limit` decorator:**

```python
def rate_limit(requests_per_minute: int = 60, per_user: bool = False):
    """
    Decorator for rate limiting endpoints.
    
    Args:
        requests_per_minute: Maximum requests per minute
        per_user: Whether to apply rate limiting per user or globally (per IP)
        
    Returns:
        Decorated function
    """
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        async def wrapper(*args, **kwargs):
            from ..services.rate_limit_service import get_rate_limit_service
            from fastapi import Request, HTTPException, status
            
            # Extract request object if available
            request = None
            for arg in args:
                if isinstance(arg, Request):
                    request = arg
                    break
            
            request_id = getattr(request.state, 'request_id', None) if request else None
            
            if not request:
                # No request object - can't rate limit, just execute
                logger.warning(
                    f"Rate limit decorator on {func.__name__} but no request object found"
                )
                return await func(*args, **kwargs)
            
            # Determine identifier (user ID or IP address)
            identifier = None
            
            if per_user:
                # Try to get authenticated user
                # This will work once authentication is implemented
                user = getattr(request.state, 'user', None)
                if user and hasattr(user, 'key_id'):
                    identifier = str(user.key_id)
                elif user and hasattr(user, 'id'):
                    identifier = str(user.id)
            
            # Fallback to IP address
            if not identifier:
                identifier = request.client.host if request.client else "unknown"
            
            # Check rate limit
            rate_limit_service = get_rate_limit_service()
            is_allowed, rate_limit_info = rate_limit_service.check_rate_limit(
                identifier=identifier,
                requests_per_minute=requests_per_minute
            )
            
            if not is_allowed:
                logger.warning(
                    f"Rate limit exceeded for {identifier} on {func.__name__}",
                    extra={
                        "request_id": request_id,
                        "identifier": identifier,
                        "limit": rate_limit_info["limit"],
                        "remaining": rate_limit_info["remaining"]
                    }
                )
                
                # Create error response with rate limit headers
                error_response = create_error_response(
                    error="Rate limit exceeded",
                    status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                    request_id=request_id,
                    suggestion=f"Please try again after {rate_limit_info['reset_time']}"
                )
                
                response = JSONResponse(
                    status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                    content=error_response.dict()
                )
                
                # Add rate limit headers
                response.headers["X-RateLimit-Limit"] = str(rate_limit_info["limit"])
                response.headers["X-RateLimit-Remaining"] = str(rate_limit_info["remaining"])
                response.headers["X-RateLimit-Reset"] = str(rate_limit_info["reset_time"])
                
                return response
            
            # Execute function
            result = await func(*args, **kwargs)
            
            # Add rate limit headers to response
            if isinstance(result, JSONResponse):
                result.headers["X-RateLimit-Limit"] = str(rate_limit_info["limit"])
                result.headers["X-RateLimit-Remaining"] = str(rate_limit_info["remaining"])
                result.headers["X-RateLimit-Reset"] = str(rate_limit_info["reset_time"])
            elif isinstance(result, dict):
                # If result is a dict, we can't add headers directly
                # The response will be wrapped by api_endpoint decorator
                # Headers should be added at the response level
                pass
            
            return result
        
        return wrapper
    return decorator
```

### 5. Configuration

**File: `src/config/settings.py`**

**Add cache and rate limiting settings:**

```python
# Cache Configuration
CACHE_ENABLED = os.getenv("CACHE_ENABLED", "true").lower() in ("true", "1", "t")
CACHE_MAX_SIZE = int(os.getenv("CACHE_MAX_SIZE", "1000"))
CACHE_CLEANUP_INTERVAL = int(os.getenv("CACHE_CLEANUP_INTERVAL", "60"))

# Rate Limiting Configuration
RATE_LIMIT_ENABLED = os.getenv("RATE_LIMIT_ENABLED", "true").lower() in ("true", "1", "t")
RATE_LIMIT_CLEANUP_INTERVAL = int(os.getenv("RATE_LIMIT_CLEANUP_INTERVAL", "60"))
```

**File: `env.template`**

**Add:**

```bash
# Cache Configuration
CACHE_ENABLED=true
CACHE_MAX_SIZE=1000
CACHE_CLEANUP_INTERVAL=60

# Rate Limiting Configuration
RATE_LIMIT_ENABLED=true
RATE_LIMIT_CLEANUP_INTERVAL=60
```

## Integration Points

### 1. Middleware Integration

- `RateLimitingMiddleware` provides global rate limiting
- `rate_limit` decorator provides endpoint-specific rate limiting
- Both can coexist (decorator takes precedence for specific endpoints)

### 2. Authentication Integration

- When authentication is implemented, `per_user=True` will use user ID
- Falls back to IP address if user not authenticated
- Works with `get_current_user` dependency (from auth spec)

### 3. Response Formatting

- Cache decorator works with `api_endpoint` decorator
- Rate limit headers added to responses
- Cache status can be indicated in response metadata

## Testing Considerations

### Unit Tests

1. **Cache Service Tests:**
   - Test get/set/delete operations
   - Test TTL expiration
   - Test LRU eviction
   - Test cleanup
   - Test thread safety

2. **Rate Limit Service Tests:**
   - Test sliding window algorithm
   - Test per-IP rate limiting
   - Test per-user rate limiting
   - Test cleanup
   - Test thread safety

3. **Decorator Tests:**
   - Test cache hit/miss
   - Test cache key generation
   - Test rate limit enforcement
   - Test rate limit headers
   - Test error handling

### Integration Tests

1. **End-to-End Caching:**
   - Test cached responses are returned
   - Test cache invalidation
   - Test cache headers

2. **End-to-End Rate Limiting:**
   - Test rate limit enforcement
   - Test rate limit headers
   - Test 429 responses

## Migration Plan

### Phase 1: Implementation (Current)
- Implement in-memory cache service
- Implement in-memory rate limit service
- Update decorators
- Add configuration

### Phase 2: Distributed Support (Future)
- Redis-based cache
- Redis-based rate limiting
- Shared state across instances

## Success Criteria

1. ✅ Cache decorator caches responses correctly
2. ✅ Rate limit decorator enforces limits correctly
3. ✅ Both decorators are thread-safe
4. ✅ Configuration is documented
5. ✅ All TODOs are resolved
6. ✅ Performance overhead is minimal
7. ✅ Error handling is graceful
8. ✅ Tests pass

## Open Questions / Future Enhancements

1. **Cache Invalidation:**
   - Should we support cache invalidation endpoints?
   - Should we support cache tags for bulk invalidation?

2. **Rate Limiting:**
   - Should we support different limits per user tier?
   - Should we support burst limits?

3. **Distributed Support:**
   - When should we migrate to Redis?
   - Should we support both in-memory and Redis?

## Dependencies

### Existing Dependencies

- `threading` - Thread safety (stdlib)
- `collections.OrderedDict` - LRU cache (stdlib)
- `hashlib` - Cache key hashing (stdlib)
- `json` - Request serialization (stdlib)

### No New Dependencies

- Uses only standard library and existing codebase components

## Implementation Order

1. Create cache service (`src/core/services/cache_service.py`)
2. Create rate limit service (`src/core/services/rate_limit_service.py`)
3. Update `cache_response` decorator
4. Update `rate_limit` decorator
5. Add configuration options
6. Write unit tests
7. Write integration tests
8. Update documentation

