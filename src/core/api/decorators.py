"""
API decorators for standardized route patterns.

This module provides decorators for consistent API route implementation,
error handling, and response formatting across all endpoints.
"""

from functools import wraps
from typing import Callable, List
import time
from datetime import datetime
from fastapi import HTTPException, status, Request
from fastapi.responses import JSONResponse

from .models.base import (
    BaseAPIRequest, 
    BaseAPIResponse, 
    ErrorResponse, 
    SuccessResponse,
    APIStatus,
    ErrorCode,
    LLMResponseMixin,
    PaginationParams
)
from .error_handlers import create_error_response, create_success_response
# from ..errors.metrics import MetricsTracker  # TODO: Implement MetricsTracker
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
            
            request_id = getattr(request.state, 'request_id', None) if request else None
            start_time = time.time()
            
            try:
                # Execute the endpoint function
                result = await func(*args, **kwargs)
                
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
        required_permissions: List of required permissions
        
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
            
            # Check authentication
            auth_header = request.headers.get("Authorization") if request else None
            if not auth_header:
                error_response = create_error_response(
                    error="Authentication required",
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    request_id=request_id,
                    suggestion="Please provide a valid authentication token."
                )
                
                return JSONResponse(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    content=error_response.dict()
                )
            
            # TODO: Implement actual authentication and permission checking
            # This is a placeholder for future implementation
            
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
            # Extract request object if available
            request = None
            for arg in args:
                if isinstance(arg, Request):
                    request = arg
                    break
            
            request_id = getattr(request.state, 'request_id', None) if request else None
            
            # TODO: Implement actual caching logic
            # This is a placeholder for future implementation
            # For now, just execute the function normally
            
            return await func(*args, **kwargs)
        
        return wrapper
    return decorator


def rate_limit(requests_per_minute: int = 60, per_user: bool = False):
    """
    Decorator for rate limiting endpoints.
    
    Args:
        requests_per_minute: Maximum requests per minute
        per_user: Whether to apply rate limiting per user or globally
        
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
            
            # TODO: Implement actual rate limiting logic
            # This is a placeholder for future implementation
            # For now, just execute the function normally
            
            return await func(*args, **kwargs)
        
        return wrapper
    return decorator


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
            
            # TODO: Implement actual pagination logic
            # This is a placeholder for future implementation
            
            return result
        
        return wrapper
    return decorator
