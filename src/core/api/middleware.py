"""
API middleware for request tracking, logging, and standardization.

This module provides middleware components for consistent request handling,
logging, and performance monitoring across all API endpoints.
"""

import time
import uuid
from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from datetime import datetime

from ..utils.logging import get_logger
from ..errors.metrics import MetricsTracker

# Set up logging
logger = get_logger(__name__)


class RequestTrackingMiddleware(BaseHTTPMiddleware):
    """Middleware for tracking requests with unique IDs and performance metrics."""
    
    def __init__(self, app, metrics_tracker=None):
        super().__init__(app)
        self.metrics_tracker = metrics_tracker
    
    async def dispatch(self, request: Request, call_next: RequestResponseEndpoint) -> Response:
        """Process request with tracking and metrics."""
        # Generate unique request ID
        request_id = str(uuid.uuid4())
        request.state.request_id = request_id
        
        # Start timing
        start_time = time.time()
        
        # Log request start
        logger.info(
            f"Request started: {request.method} {request.url.path}",
            extra={
                "request_id": request_id,
                "method": request.method,
                "path": str(request.url.path),
                "query_params": dict(request.query_params),
                "client_ip": request.client.host if request.client else None,
                "user_agent": request.headers.get("user-agent"),
                "content_type": request.headers.get("content-type"),
                "content_length": request.headers.get("content-length")
            }
        )
        
        # Track request start in metrics
        if self.metrics_tracker:
            self.metrics_tracker.start_request(request_id, request.method, str(request.url.path))
        
        try:
            # Process request
            response = await call_next(request)
            
            # Calculate processing time
            processing_time = time.time() - start_time
            
            # Log successful response
            logger.info(
                f"Request completed: {request.method} {request.url.path} - {response.status_code}",
                extra={
                    "request_id": request_id,
                    "method": request.method,
                    "path": str(request.url.path),
                    "status_code": response.status_code,
                    "processing_time": processing_time,
                    "response_size": response.headers.get("content-length")
                }
            )
            
            # Track successful request in metrics
            if self.metrics_tracker:
                self.metrics_tracker.end_request(
                    request_id, 
                    success=True, 
                    status_code=response.status_code,
                    processing_time=processing_time
                )
            
            # Add request ID to response headers
            response.headers["X-Request-ID"] = request_id
            response.headers["X-Processing-Time"] = str(processing_time)
            
            return response
            
        except Exception as e:
            # Calculate processing time
            processing_time = time.time() - start_time
            
            # Log error
            logger.error(
                f"Request failed: {request.method} {request.url.path} - {str(e)}",
                extra={
                    "request_id": request_id,
                    "method": request.method,
                    "path": str(request.url.path),
                    "error": str(e),
                    "error_type": type(e).__name__,
                    "processing_time": processing_time
                },
                exc_info=True
            )
            
            # Track failed request in metrics
            if self.metrics_tracker:
                self.metrics_tracker.end_request(
                    request_id, 
                    success=False, 
                    status_code=500,
                    processing_time=processing_time,
                    error=str(e)
                )
            
            # Re-raise the exception
            raise


class LLMRequestMiddleware(BaseHTTPMiddleware):
    """Middleware for tracking LLM-specific requests and costs."""
    
    def __init__(self, app, metrics_tracker=None):
        super().__init__(app)
        self.metrics_tracker = metrics_tracker
    
    async def dispatch(self, request: Request, call_next: RequestResponseEndpoint) -> Response:
        """Process request with LLM tracking."""
        # Check if this is an LLM request
        is_llm_request = self._is_llm_request(request)
        
        if is_llm_request:
            # Extract LLM parameters
            llm_params = self._extract_llm_params(request)
            
            # Log LLM request start
            logger.info(
                f"LLM request started: {request.method} {request.url.path}",
                extra={
                    "request_id": getattr(request.state, 'request_id', None),
                    "llm_provider": llm_params.get("provider"),
                    "llm_model": llm_params.get("model"),
                    "llm_temperature": llm_params.get("temperature"),
                    "llm_max_tokens": llm_params.get("max_tokens")
                }
            )
            
            # Track LLM request start
            if self.metrics_tracker:
                self.metrics_tracker.start_llm_request(
                    request_id=getattr(request.state, 'request_id', None),
                    provider=llm_params.get("provider"),
                    model=llm_params.get("model")
                )
        
        # Process request
        response = await call_next(request)
        
        if is_llm_request:
            # Extract LLM response data
            llm_response_data = self._extract_llm_response_data(response)
            
            # Log LLM request completion
            logger.info(
                f"LLM request completed: {request.method} {request.url.path}",
                extra={
                    "request_id": getattr(request.state, 'request_id', None),
                    "llm_cost": llm_response_data.get("cost"),
                    "llm_tokens_used": llm_response_data.get("tokens_used"),
                    "llm_processing_time": llm_response_data.get("processing_time")
                }
            )
            
            # Track LLM request completion
            if self.metrics_tracker:
                self.metrics_tracker.end_llm_request(
                    request_id=getattr(request.state, 'request_id', None),
                    cost=llm_response_data.get("cost"),
                    tokens_used=llm_response_data.get("tokens_used"),
                    processing_time=llm_response_data.get("processing_time")
                )
        
        return response
    
    def _is_llm_request(self, request: Request) -> bool:
        """Check if this is an LLM request."""
        # Check for LLM parameters in query params
        if request.query_params.get("use_llm") == "true":
            return True
        
        # Check for LLM parameters in request body (for POST requests)
        if request.method == "POST":
            content_type = request.headers.get("content-type", "")
            if "application/json" in content_type:
                # Note: We can't read the body here without consuming it
                # This is a limitation of middleware - we'll handle this in the route handlers
                pass
        
        return False
    
    def _extract_llm_params(self, request: Request) -> dict:
        """Extract LLM parameters from request."""
        return {
            "provider": request.query_params.get("llm_provider"),
            "model": request.query_params.get("llm_model"),
            "temperature": request.query_params.get("llm_temperature"),
            "max_tokens": request.query_params.get("llm_max_tokens")
        }
    
    def _extract_llm_response_data(self, response: Response) -> dict:
        """Extract LLM response data from response headers."""
        return {
            "cost": response.headers.get("X-LLM-Cost"),
            "tokens_used": response.headers.get("X-LLM-Tokens"),
            "processing_time": response.headers.get("X-LLM-Processing-Time")
        }


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    """Middleware for adding security headers to responses."""
    
    async def dispatch(self, request: Request, call_next: RequestResponseEndpoint) -> Response:
        """Add security headers to response."""
        response = await call_next(request)
        
        # Add security headers
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["X-XSS-Protection"] = "1; mode=block"
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
        response.headers["Permissions-Policy"] = "geolocation=(), microphone=(), camera=()"
        
        # Add CORS headers if not already present
        if "Access-Control-Allow-Origin" not in response.headers:
            response.headers["Access-Control-Allow-Origin"] = "*"
        
        return response


class RateLimitingMiddleware(BaseHTTPMiddleware):
    """Middleware for basic rate limiting."""
    
    def __init__(self, app, requests_per_minute: int = 60):
        super().__init__(app)
        self.requests_per_minute = requests_per_minute
        self.request_counts = {}  # In production, use Redis or similar
    
    async def dispatch(self, request: Request, call_next: RequestResponseEndpoint) -> Response:
        """Apply rate limiting to requests."""
        client_ip = request.client.host if request.client else "unknown"
        current_time = time.time()
        
        # Clean old entries (older than 1 minute)
        self.request_counts = {
            ip: count for ip, count in self.request_counts.items()
            if current_time - count["last_reset"] < 60
        }
        
        # Check rate limit
        if client_ip in self.request_counts:
            if self.request_counts[client_ip]["count"] >= self.requests_per_minute:
                logger.warning(
                    f"Rate limit exceeded for IP: {client_ip}",
                    extra={
                        "client_ip": client_ip,
                        "request_count": self.request_counts[client_ip]["count"],
                        "limit": self.requests_per_minute
                    }
                )
                
                from fastapi import HTTPException, status
                raise HTTPException(
                    status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                    detail="Rate limit exceeded. Please try again later."
                )
            
            self.request_counts[client_ip]["count"] += 1
        else:
            self.request_counts[client_ip] = {
                "count": 1,
                "last_reset": current_time
            }
        
        return await call_next(request)


class RequestLoggingMiddleware(BaseHTTPMiddleware):
    """Middleware for detailed request/response logging."""
    
    def __init__(self, app, log_requests: bool = True, log_responses: bool = False):
        super().__init__(app)
        self.log_requests = log_requests
        self.log_responses = log_responses
    
    async def dispatch(self, request: Request, call_next: RequestResponseEndpoint) -> Response:
        """Log request and response details."""
        request_id = getattr(request.state, 'request_id', None)
        
        if self.log_requests:
            # Log request details
            request_data = {
                "method": request.method,
                "url": str(request.url),
                "headers": dict(request.headers),
                "query_params": dict(request.query_params),
                "path_params": dict(request.path_params)
            }
            
            logger.debug(
                f"Request details for {request_id}",
                extra={
                    "request_id": request_id,
                    "request_data": request_data
                }
            )
        
        # Process request
        response = await call_next(request)
        
        if self.log_responses:
            # Log response details
            response_data = {
                "status_code": response.status_code,
                "headers": dict(response.headers)
            }
            
            logger.debug(
                f"Response details for {request_id}",
                extra={
                    "request_id": request_id,
                    "response_data": response_data
                }
            )
        
        return response


def setup_api_middleware(app, metrics_tracker=None):
    """
    Set up all API middleware components.
    
    Args:
        app: FastAPI application instance
        metrics_tracker: Metrics tracker instance
    """
    # Add middleware in reverse order (last added is first executed)
    
    # Security headers (first to execute)
    app.add_middleware(SecurityHeadersMiddleware)
    
    # Rate limiting
    app.add_middleware(RateLimitingMiddleware, requests_per_minute=100)
    
    # Request logging (optional, for debugging)
    app.add_middleware(RequestLoggingMiddleware, log_requests=False, log_responses=False)
    
    # LLM request tracking
    app.add_middleware(LLMRequestMiddleware, metrics_tracker=metrics_tracker)
    
    # Request tracking (last to execute, first to be added)
    app.add_middleware(RequestTrackingMiddleware, metrics_tracker=metrics_tracker)
    
    logger.info("API middleware setup completed")
