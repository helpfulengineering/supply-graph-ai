"""
API decorators for standardized route patterns.

This module provides decorators for consistent API route implementation,
error handling, and response formatting across all endpoints.
"""

from functools import wraps
from typing import Callable, List, Optional
import time
from datetime import datetime
from fastapi import HTTPException, status, Request
from fastapi.responses import JSONResponse

from .models.base import (
    APIStatus,
    PaginationParams,
    PaginatedResponse,
    PaginationInfo
)
from .error_handlers import create_error_response
# MetricsTracker is available but not currently used in decorators
# from ..errors.metrics import MetricsTracker
from ..utils.logging import get_logger

# Set up logging
logger = get_logger(__name__)


def api_endpoint(
    success_message: str = "Operation completed successfully",
    include_metrics: bool = True,
    track_llm: bool = False
):
    """
    Decorator for standardizing API endpoint responses.
    
    Args:
        success_message: Default success message
        include_metrics: Whether to include processing metrics
        track_llm: Whether to track LLM usage
        
    Returns:
        Decorated function
    """
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        async def wrapper(*args, **kwargs):
            # Extract request object if available
            request = None
            for arg in args:
                if isinstance(arg, Request):
                    request = arg
                    break
            
            # Also check kwargs for request/http_request
            if not request:
                request = kwargs.get("http_request") or kwargs.get("request")
            
            request_id = getattr(request.state, 'request_id', None) if request else None
            start_time = time.time()
            
            try:
                # Execute the endpoint function
                result = await func(*args, **kwargs)
                
                # If result is already a Pydantic model (like PaginatedResponse), return it directly
                # Check if it's a Pydantic BaseModel instance
                if hasattr(result, 'model_dump') or hasattr(result, 'dict'):
                    # It's a Pydantic model, return it directly (FastAPI will serialize it)
                    # FastAPI can handle Pydantic models directly, so we return it as-is
                    return result
                
                # Calculate processing time
                processing_time = time.time() - start_time
                
                # Create success response
                response_data = {
                    "status": APIStatus.SUCCESS,
                    "message": success_message,
                    "timestamp": datetime.now().isoformat(),
                    "request_id": request_id,
                    "data": result if isinstance(result, dict) else {"result": result},
                    "metadata": {}
                }
                
                # Add processing metrics if requested
                if include_metrics:
                    response_data["metadata"]["processing_time"] = processing_time
                    response_data["metadata"]["timestamp"] = datetime.now().isoformat()
                
                # Add LLM tracking if requested
                if track_llm and hasattr(result, 'llm_used') and result.llm_used:
                    response_data["metadata"]["llm_used"] = True
                    if hasattr(result, 'llm_provider'):
                        response_data["metadata"]["llm_provider"] = result.llm_provider
                    if hasattr(result, 'llm_cost'):
                        response_data["metadata"]["llm_cost"] = result.llm_cost
                
                # Check for rate limit info from rate_limit decorator
                rate_limit_info = getattr(request.state, 'rate_limit_info', None) if request else None
                
                # If rate limit info is present, return JSONResponse with headers
                if rate_limit_info:
                    response = JSONResponse(
                        status_code=status.HTTP_200_OK,
                        content=response_data
                    )
                    response.headers["X-RateLimit-Limit"] = str(rate_limit_info["limit"])
                    response.headers["X-RateLimit-Remaining"] = str(rate_limit_info["remaining"])
                    response.headers["X-RateLimit-Reset"] = str(rate_limit_info["reset_time"])
                    return response
                
                return response_data
                
            except HTTPException as e:
                # Re-raise HTTP exceptions (they'll be handled by error handlers)
                raise
                
            except Exception as e:
                # Log unexpected errors
                logger.error(
                    f"Unexpected error in {func.__name__}: {str(e)}",
                    extra={
                        "request_id": request_id,
                        "function": func.__name__,
                        "error": str(e),
                        "error_type": type(e).__name__
                    },
                    exc_info=True
                )
                
                # Create error response
                error_response = create_error_response(
                    error=e,
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    request_id=request_id,
                    suggestion="An unexpected error occurred. Please try again later."
                )
                
                return JSONResponse(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    content=error_response.dict()
                )
        
        return wrapper
    return decorator


def validate_request(request_model: type = None):
    """
    Decorator for validating request models.
    
    Args:
        request_model: Pydantic model for request validation
        
    Returns:
        Decorated function
    """
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        async def wrapper(*args, **kwargs):
            # Extract request object if available
            request = None
            for arg in args:
                if isinstance(arg, Request):
                    request = arg
                    break
            
            request_id = getattr(request.state, 'request_id', None) if request else None
            
            if request_model:
                try:
                    # Validate request data against model
                    # This is a simplified validation - in practice, FastAPI handles this
                    # But we can add additional custom validation here
                    pass
                except Exception as e:
                    error_response = create_error_response(
                        error=f"Request validation failed: {str(e)}",
                        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                        request_id=request_id,
                        suggestion="Please check your request data and try again."
                    )
                    
                    return JSONResponse(
                        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                        content=error_response.dict()
                    )
            
            return await func(*args, **kwargs)
        
        return wrapper
    return decorator


def track_performance(operation_name: str = None):
    """
    Decorator for tracking endpoint performance.
    
    Args:
        operation_name: Name of the operation for metrics tracking
        
    Returns:
        Decorated function
    """
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        async def wrapper(*args, **kwargs):
            # Extract request object if available
            request = None
            for arg in args:
                if isinstance(arg, Request):
                    request = arg
                    break
            
            request_id = getattr(request.state, 'request_id', None) if request else None
            operation = operation_name or func.__name__
            start_time = time.time()
            
            try:
                # Execute the function
                result = await func(*args, **kwargs)
                
                # Calculate processing time
                processing_time = time.time() - start_time
                
                # Log performance metrics
                logger.info(
                    f"Performance: {operation} completed in {processing_time:.3f}s",
                    extra={
                        "request_id": request_id,
                        "operation": operation,
                        "processing_time": processing_time,
                        "success": True
                    }
                )
                
                return result
                
            except Exception as e:
                # Calculate processing time
                processing_time = time.time() - start_time
                
                # Log performance metrics for failed operations
                logger.warning(
                    f"Performance: {operation} failed after {processing_time:.3f}s",
                    extra={
                        "request_id": request_id,
                        "operation": operation,
                        "processing_time": processing_time,
                        "success": False,
                        "error": str(e)
                    }
                )
                
                # Re-raise the exception
                raise
        
        return wrapper
    return decorator


def require_authentication(required_permissions: List[str] = None):
    """
    Decorator for requiring authentication and permissions.
    
    Args:
        required_permissions: List of required permissions. If None, only authentication required.
        
    Usage:
        @require_authentication()
        async def endpoint(user: AuthenticatedUser = Depends(get_current_user)):
            ...
            
        @require_authentication(required_permissions=["write"])
        async def write_endpoint(user: AuthenticatedUser = Depends(get_current_user)):
            ...
    """
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        async def wrapper(*args, **kwargs):
            # Extract AuthenticatedUser from kwargs (injected by FastAPI dependency)
            user = None
            for key, value in kwargs.items():
                from ..models.auth import AuthenticatedUser
                if isinstance(value, AuthenticatedUser):
                    user = value
                    break
            
            # Extract request object if available for request_id
            request = None
            for arg in args:
                if isinstance(arg, Request):
                    request = arg
                    break
            
            request_id = getattr(request.state, 'request_id', None) if request else None
            
            if not user:
                # If no user found, check if endpoint uses get_current_user dependency
                # This is a fallback - ideally endpoints should use Depends(get_current_user)
                error_response = create_error_response(
                    error="Authentication required",
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    request_id=request_id,
                    suggestion="This endpoint requires authentication. Use Depends(get_current_user) in your endpoint."
                )
                return JSONResponse(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    content=error_response.model_dump(mode='json')
                )
            
            # Check permissions if required
            if required_permissions:
                from ..services.auth_service import AuthenticationService
                auth_service = await AuthenticationService.get_instance()
                has_permission = await auth_service.check_permission(
                    user,
                    required_permissions
                )
                
                if not has_permission:
                    error_response = create_error_response(
                        error="Insufficient permissions",
                        status_code=status.HTTP_403_FORBIDDEN,
                        request_id=request_id,
                        suggestion=f"This endpoint requires the following permissions: {', '.join(required_permissions)}"
                    )
                    return JSONResponse(
                        status_code=status.HTTP_403_FORBIDDEN,
                        content=error_response.model_dump(mode='json')
                    )
            
            return await func(*args, **kwargs)
        
        return wrapper
    return decorator


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
            import hashlib
            import json
            
            # Extract request object if available
            request = None
            for arg in args:
                if isinstance(arg, Request):
                    request = arg
                    break
            
            # Also check kwargs for request/http_request
            if not request:
                request = kwargs.get("http_request") or kwargs.get("request")
            
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
                # Add cache indicator if response is a dict
                if isinstance(cached_response, dict):
                    cached_response["_cached"] = True
                # Note: rate_limit_info should already be set by rate_limit decorator
                # (which executes before cache_response in the decorator chain)
                # So we can safely return the cached response
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
            
            # Extract request object if available
            request = None
            for arg in args:
                if isinstance(arg, Request):
                    request = arg
                    break
            
            # Also check kwargs for request/http_request
            if not request:
                request = kwargs.get("http_request") or kwargs.get("request")
            
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
                    content=error_response.model_dump(mode='json')
                )
                
                # Add rate limit headers
                response.headers["X-RateLimit-Limit"] = str(rate_limit_info["limit"])
                response.headers["X-RateLimit-Remaining"] = str(rate_limit_info["remaining"])
                response.headers["X-RateLimit-Reset"] = str(rate_limit_info["reset_time"])
                
                return response
            
            # Store rate limit info in request state for api_endpoint to use
            # This must be set BEFORE calling func() in case cache_response returns early
            if request:
                request.state.rate_limit_info = rate_limit_info
            
            # Execute function
            result = await func(*args, **kwargs)
            
            # Add rate limit headers to response if it's already a JSONResponse
            if isinstance(result, JSONResponse):
                result.headers["X-RateLimit-Limit"] = str(rate_limit_info["limit"])
                result.headers["X-RateLimit-Remaining"] = str(rate_limit_info["remaining"])
                result.headers["X-RateLimit-Reset"] = str(rate_limit_info["reset_time"])
            # If result is a dict, api_endpoint decorator will handle headers via request.state.rate_limit_info
            
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
    
    # Add non-request kwargs (excluding request objects)
    other_kwargs = {
        k: v for k, v in kwargs.items()
        if k not in ("request", "http_request") and not isinstance(v, Request)
    }
    
    # Handle Pydantic models and other serializable objects
    serializable_kwargs = {}
    for k, v in other_kwargs.items():
        try:
            # Try to serialize Pydantic models
            if hasattr(v, 'model_dump'):
                serializable_kwargs[k] = v.model_dump()
            elif hasattr(v, 'dict'):
                serializable_kwargs[k] = v.dict()
            else:
                serializable_kwargs[k] = v
        except (TypeError, AttributeError):
            # Fallback to string representation
            serializable_kwargs[k] = str(v)
    
    if serializable_kwargs:
        key_parts.append(json.dumps(serializable_kwargs, sort_keys=True, default=str))
    
    # Combine and hash
    key_string = "|".join(str(part) for part in key_parts)
    key_hash = hashlib.md5(key_string.encode()).hexdigest()
    
    return f"cache:{key_hash}"


def llm_endpoint(
    default_provider: str = None,
    default_model: str = None,
    track_costs: bool = True
):
    """
    Decorator for LLM-enabled endpoints.
    
    Args:
        default_provider: Default LLM provider
        default_model: Default LLM model
        track_costs: Whether to track LLM costs
        
    Returns:
        Decorated function
    """
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        async def wrapper(*args, **kwargs):
            # Extract request object if available
            request = None
            for arg in args:
                if isinstance(arg, Request):
                    request = arg
                    break
            
            request_id = getattr(request.state, 'request_id', None) if request else None
            
            # Extract LLM parameters from request
            llm_params = {
                "use_llm": request.query_params.get("use_llm", "false").lower() == "true" if request else False,
                "provider": request.query_params.get("llm_provider", default_provider) if request else default_provider,
                "model": request.query_params.get("llm_model", default_model) if request else default_model,
                "temperature": request.query_params.get("llm_temperature") if request else None,
                "max_tokens": request.query_params.get("llm_max_tokens") if request else None
            }
            
            # Log LLM request if enabled
            if llm_params["use_llm"]:
                logger.info(
                    f"LLM request initiated: {func.__name__}",
                    extra={
                        "request_id": request_id,
                        "llm_provider": llm_params["provider"],
                        "llm_model": llm_params["model"],
                        "llm_temperature": llm_params["temperature"],
                        "llm_max_tokens": llm_params["max_tokens"]
                    }
                )
            
            # Execute the function with LLM parameters (only if function accepts it)
            import inspect
            sig = inspect.signature(func)
            if 'llm_params' in sig.parameters:
                result = await func(*args, **kwargs, llm_params=llm_params)
            else:
                result = await func(*args, **kwargs)
            
            # Add LLM information to response if LLM was used
            if llm_params["use_llm"] and isinstance(result, dict):
                result["llm_used"] = True
                result["llm_provider"] = llm_params["provider"]
                result["llm_model"] = llm_params["model"]
                
                if track_costs and hasattr(result, 'llm_cost'):
                    result["llm_cost"] = result.llm_cost
                if hasattr(result, 'llm_tokens_used'):
                    result["llm_tokens_used"] = result.llm_tokens_used
            
            return result
        
        return wrapper
    return decorator


def paginated_response(
    default_page_size: int = 20,
    max_page_size: int = 100
):
    """
    Decorator for paginated responses.
    
    Args:
        default_page_size: Default number of items per page
        max_page_size: Maximum number of items per page
        
    Returns:
        Decorated function
    """
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        async def wrapper(*args, **kwargs):
            try:
                # Extract request object if available
                request = None
                for arg in args:
                    if isinstance(arg, Request):
                        request = arg
                        break
                
                request_id = getattr(request.state, 'request_id', None) if request else None
                
                # Extract pagination parameters
                page = int(request.query_params.get("page", 1)) if request else 1
                page_size = int(request.query_params.get("page_size", default_page_size)) if request else default_page_size
                
                # Validate pagination parameters
                if page < 1:
                    page = 1
                if page_size < 1:
                    page_size = default_page_size
                if page_size > max_page_size:
                    page_size = max_page_size
                
                # Create PaginationParams object
                pagination = PaginationParams(page=page, page_size=page_size)
                
                # Execute the function with pagination parameters (only if function doesn't already have pagination)
                import inspect
                sig = inspect.signature(func)
                if 'pagination' in sig.parameters and 'pagination' not in kwargs:
                    result = await func(*args, **kwargs, pagination=pagination)
                else:
                    result = await func(*args, **kwargs)
            except HTTPException:
                raise
            except Exception as e:
                logger.error(f"Error in paginated_response decorator: {e}", exc_info=True)
                raise
            
            # If result is already a PaginatedResponse, return as-is
            if isinstance(result, PaginatedResponse):
                return result
            
            # If result is a dict with 'items' key, extract items for pagination
            items = None
            if isinstance(result, dict) and 'items' in result:
                items = result['items']
            elif isinstance(result, (list, tuple)):
                items = list(result)
            
            # If we have items to paginate, apply pagination
            if items is not None:
                total_items = len(items)
                total_pages = (total_items + page_size - 1) // page_size if total_items > 0 else 0
                
                # Calculate slice indices
                start_idx = (page - 1) * page_size
                end_idx = start_idx + page_size
                paginated_items = items[start_idx:end_idx]
                
                # Convert items to dict format if needed (PaginatedResponse expects List[Dict[str, Any]])
                # If items are already dicts, keep them; otherwise convert
                converted_items = []
                for item in paginated_items:
                    try:
                        if isinstance(item, dict):
                            # Ensure all values in dict are JSON-serializable
                            serializable_item = {}
                            for k, v in item.items():
                                if isinstance(v, datetime):
                                    serializable_item[k] = v.isoformat()
                                else:
                                    serializable_item[k] = v
                            converted_items.append(serializable_item)
                        else:
                            # Convert to dict - try to_dict() method first, then fallback to simple conversion
                            if hasattr(item, 'to_dict'):
                                converted_items.append(item.to_dict())
                            elif hasattr(item, 'model_dump'):
                                converted_items.append(item.model_dump())
                            elif hasattr(item, 'dict'):
                                converted_items.append(item.dict())
                            else:
                                # For primitive types, wrap in a simple dict
                                converted_items.append({"value": item})
                    except Exception as e:
                        logger.error(f"Error converting item to dict: {e}", exc_info=True)
                        # Skip items that can't be converted
                        continue
                
                # Create PaginationInfo
                pagination_info = PaginationInfo(
                    page=page,
                    page_size=page_size,
                    total_items=total_items,
                    total_pages=total_pages,
                    has_next=page < total_pages,
                    has_previous=page > 1
                )
                
                # Create PaginatedResponse
                return PaginatedResponse(
                    items=converted_items,
                    pagination=pagination_info,
                    message="Items retrieved successfully",
                    request_id=request_id
                )
            
            # For non-list results, return as-is
            return result
        
        return wrapper
    return decorator
