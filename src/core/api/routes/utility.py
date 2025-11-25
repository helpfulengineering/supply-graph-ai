from fastapi import APIRouter, Path, Depends, Request, status, HTTPException
from typing import Optional, List, Any
from datetime import datetime

# Import new standardized components
from ..models.base import (
    ValidationResult, ErrorDetail, ErrorCode
)
from ..decorators import (
    api_endpoint,
    track_performance,
    llm_endpoint,
    cache_response,
    rate_limit
)
from ..error_handlers import create_error_response, create_success_response

# Import consolidated utility models
from ..models.utility.request import (
    DomainFilterRequest,
    ContextFilterRequest
)
from ..models.utility.response import (
    DomainsResponse,
    ContextsResponse,
    Domain,
    Context
)
from ...utils.logging import get_logger
from ...errors.metrics import get_metrics_tracker

# Set up logging
logger = get_logger(__name__)

# Create router with standardized patterns
router = APIRouter(
    prefix="/api/utility",
    tags=["utility"],
    responses={
        400: {"description": "Bad Request"},
        401: {"description": "Unauthorized"},
        422: {"description": "Validation Error"},
        500: {"description": "Internal Server Error"}
    }
)


@router.get(
    "/domains", 
    summary="List Available Domains",
    description="""
    Get a list of available domains with enhanced capabilities.
    
    **Features:**
    - Domain filtering and search
    - Enhanced error handling
    - Performance metrics
    - LLM integration support
    - Validation
    - Response caching (5 minutes TTL)
    - Rate limiting (60 requests per minute)
    """
)
@api_endpoint(
    success_message="Domains retrieved successfully",
    include_metrics=True
)
@rate_limit(requests_per_minute=60, per_user=False)
@cache_response(ttl_seconds=300, cache_key_prefix="domains")
@track_performance("utility_domains")
@llm_endpoint(
    default_provider="anthropic",
    default_model="claude-sonnet-4-5",
    track_costs=True
)
async def get_domains(
    filter_params: DomainFilterRequest = Depends(),
    http_request: Request = None
):
    """Enhanced domain listing with standardized patterns."""
    request_id = getattr(http_request.state, 'request_id', None) if http_request else None
    start_time = datetime.now()
    
    try:
        # Get domains from DomainRegistry
        from ...registry.domain_registry import DomainRegistry
        
        # Get all domain metadata
        all_metadata = DomainRegistry.get_all_metadata(include_disabled=False)
        
        # Convert to Domain objects
        domains = []
        for domain_name, metadata in all_metadata.items():
            domain = Domain(
                id=metadata.name,
                name=metadata.display_name,
                description=metadata.description
            )
            domains.append(domain)
        
        # Apply name filter if provided
        if filter_params.name:
            domains = [
                d for d in domains 
                if filter_params.name.lower() in d.name.lower() or 
                   filter_params.name.lower() in d.id.lower()
            ]
        
        # Calculate processing time
        processing_time = (datetime.now() - start_time).total_seconds()
        
        # Validate results (only once)
        validation_results = await _validate_utility_result(domains, request_id)
        
        logger.info(
            f"Domains retrieved successfully",
            extra={
                "request_id": request_id,
                "domain_count": len(domains),
                "processing_time": processing_time,
                "llm_used": filter_params.use_llm
            }
        )
        
        # Return dict for api_endpoint decorator to wrap
        return {
            "domains": [domain.model_dump(mode='json') for domain in domains],
            "processing_time": processing_time,
            "validation_results": [vr.model_dump(mode='json') if hasattr(vr, 'model_dump') else vr for vr in validation_results]
        }
        
    except Exception as e:
        # Use standardized error handler
        error_response = create_error_response(
            error=e,
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            request_id=request_id,
            suggestion="Please try again or contact support if the issue persists"
        )
        logger.error(
            f"Error retrieving domains: {str(e)}",
            extra={
                "request_id": request_id,
                "error": str(e),
                "error_type": type(e).__name__
            },
            exc_info=True
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=error_response.model_dump(mode='json')
        )

@router.get(
    "/contexts/{domain}", 
    response_model=ContextsResponse,
    summary="List Validation Contexts",
    description="""
    Get validation contexts for a specific domain with enhanced capabilities.
    
    **Features:**
    - Context filtering and search
    - Enhanced error handling
    - Performance metrics
    - LLM integration support
    - Validation
    """
)
@track_performance("utility_contexts")
@llm_endpoint(
    default_provider="anthropic",
    default_model="claude-sonnet-4-5",
    track_costs=True
)
async def get_contexts(
    domain: str = Path(..., title="The domain to get contexts for"),
    filter_params: ContextFilterRequest = Depends(),
    http_request: Request = None
):
    """Enhanced context listing with standardized patterns."""
    request_id = getattr(http_request.state, 'request_id', None) if http_request else None
    start_time = datetime.now()
    
    try:
        # Validate domain exists
        from ...registry.domain_registry import DomainRegistry
        
        try:
            domain_metadata = DomainRegistry.get_domain_metadata(domain)
        except ValueError:
            error_response = create_error_response(
                error=f"Domain '{domain}' not found",
                status_code=status.HTTP_404_NOT_FOUND,
                request_id=request_id,
                suggestion=f"Available domains: {', '.join(DomainRegistry.list_domains())}"
            )
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=error_response.model_dump(mode='json')
            )
        
        # Get contexts based on validation framework quality levels
        # Quality levels map to contexts per domain
        quality_levels_map = {
            "manufacturing": ["hobby", "professional", "medical"],
            "cooking": ["home", "commercial", "professional"]
        }
        
        # Get quality levels for this domain, default to professional if unknown
        quality_levels = quality_levels_map.get(domain, ["professional"])
        
        contexts = []
        for level in quality_levels:
            # Map quality level to context
            context_id = level
            # Create context name from quality level and domain
            context_name = level.title() + " " + domain_metadata.display_name.split()[0]
            # Create context description
            context_description = f"{level.title()} level validation and matching for {domain_metadata.display_name}"
            
            context = Context(
                id=context_id,
                name=context_name,
                description=context_description
            )
            contexts.append(context)
        
        # Apply name filter if provided
        if filter_params.name:
            contexts = [
                c for c in contexts 
                if filter_params.name.lower() in c.name.lower() or 
                   filter_params.name.lower() in c.id.lower()
            ]
        
        # Calculate processing time
        processing_time = (datetime.now() - start_time).total_seconds()
        
        # Create enhanced response using the proper ContextsResponse structure
        response_data = {
            "contexts": [context.model_dump(mode='json') for context in contexts],
            "processing_time": processing_time,
            "validation_results": await _validate_utility_result(contexts, request_id)
        }
        
        logger.info(
            f"Contexts retrieved successfully for domain: {domain}",
            extra={
                "request_id": request_id,
                "domain": domain,
                "context_count": len(contexts),
                "processing_time": processing_time,
                "llm_used": filter_params.use_llm
            }
        )
        
        return ContextsResponse(
            contexts=contexts,
            message="Contexts retrieved successfully",
            processing_time=processing_time,
            validation_results=await _validate_utility_result(contexts, request_id)
        )
        
    except HTTPException:
        raise
    except Exception as e:
        # Use standardized error handler
        error_response = create_error_response(
            error=e,
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            request_id=request_id,
            suggestion="Please try again or contact support if the issue persists"
        )
        logger.error(
            f"Error retrieving contexts for domain {domain}: {str(e)}",
            extra={
                "request_id": request_id,
                "domain": domain,
                "error": str(e),
                "error_type": type(e).__name__
            },
            exc_info=True
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=error_response.model_dump(mode='json')
        )

# Helper functions
async def _validate_utility_result(
    result: Any,
    request_id: str
) -> List[ValidationResult]:
    """Validate utility operation result."""
    try:
        validation_results = []
        
        # Basic validation
        is_valid = True
        errors = []
        warnings = []
        suggestions = []
        
        # Check if result exists
        if not result:
            is_valid = False
            errors.append(ErrorDetail(
                code=ErrorCode.VALIDATION_ERROR,
                message="No result returned from operation"
            ))
        
        # Check if result is a list and has items
        if isinstance(result, list):
            if len(result) == 0:
                warnings.append("No items found in result")
            
            # Check each item has required fields
            for i, item in enumerate(result):
                if hasattr(item, 'id') and not item.id:
                    warnings.append(f"Item {i} missing ID")
                if hasattr(item, 'name') and not item.name:
                    warnings.append(f"Item {i} missing name")
        
        # Generate suggestions
        if not is_valid:
            suggestions.append("Review the input data and try again")
        elif len(result) == 0:
            suggestions.append("Try adjusting your filter criteria")
        
        validation_result = ValidationResult(
            is_valid=is_valid,
            score=1.0 if is_valid else 0.5,
            errors=errors,
            warnings=warnings,
            suggestions=suggestions
        )
        
        validation_results.append(validation_result)
        
        return validation_results
        
    except Exception as e:
        logger.error(
            f"Error validating utility result: {str(e)}",
            extra={"request_id": request_id, "error": str(e)},
            exc_info=True
        )
        return []


@router.get(
    "/metrics",
    summary="Get System Metrics",
    description="""
    Get system metrics including request tracking, performance, and LLM usage.
    
    This endpoint provides access to the MetricsTracker data, including:
    - Overall request statistics
    - Endpoint-level metrics
    - Error summaries
    - Performance metrics
    - LLM usage and costs
    
    Args:
        endpoint: Optional endpoint filter (format: "METHOD /path")
        summary: If True, return summary only; if False, return detailed metrics
    """
)
@api_endpoint(
    success_message="Metrics retrieved successfully",
    include_metrics=False  # Don't track metrics for the metrics endpoint itself
)
async def get_metrics(
    endpoint: Optional[str] = None,
    summary: bool = True,
    http_request: Request = None
):
    """
    Get system metrics.
    
    Args:
        endpoint: Optional endpoint filter (format: "METHOD /path")
        summary: If True, return summary; if False, return detailed metrics
    """
    try:
        tracker = get_metrics_tracker()
        
        if endpoint:
            # Parse endpoint format: "METHOD /path"
            parts = endpoint.split(" ", 1)
            if len(parts) != 2:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Endpoint format must be 'METHOD /path'"
                )
            method, path = parts
            return tracker.get_endpoint_metrics(method=method, path=path)
        
        if summary:
            return tracker.get_summary()
        
        return {
            "summary": tracker.get_summary(),
            "endpoints": tracker.get_endpoint_metrics()
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting metrics: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error retrieving metrics: {str(e)}"
        )