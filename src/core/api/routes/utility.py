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
    llm_endpoint
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
    response_model=DomainsResponse,
    summary="List Available Domains",
    description="""
    Get a list of available domains with enhanced capabilities.
    
    **Features:**
    - Domain filtering and search
    - Enhanced error handling
    - Performance metrics
    - LLM integration support
    - Validation
    """
)
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
        # Placeholder implementation
        domains = [
            Domain(
                id="manufacturing",
                name="Manufacturing Domain",
                description="Hardware manufacturing capabilities"
            ),
            Domain(
                id="cooking",
                name="Cooking Domain",
                description="Food preparation capabilities"
            )
        ]
        
        # Apply name filter if provided
        if filter_params.name:
            domains = [d for d in domains if filter_params.name.lower() in d.name.lower()]
        
        # Calculate processing time
        processing_time = (datetime.now() - start_time).total_seconds()
        
        # Create enhanced response using the proper DomainsResponse structure
        response_data = {
            "domains": [domain.model_dump(mode='json') for domain in domains],
            "processing_time": processing_time,
            "validation_results": await _validate_utility_result(domains, request_id)
        }
        
        logger.info(
            f"Domains retrieved successfully",
            extra={
                "request_id": request_id,
                "domain_count": len(domains),
                "processing_time": processing_time,
                "llm_used": filter_params.use_llm
            }
        )
        
        return DomainsResponse(
            domains=domains,
            message="Domains retrieved successfully",
            processing_time=processing_time,
            validation_results=await _validate_utility_result(domains, request_id)
        )
        
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
        # Placeholder implementation
        if domain == "manufacturing":
            contexts = [
                Context(
                    id="hobby",
                    name="Hobby Manufacturing",
                    description="Non-commercial, limited quality requirements"
                ),
                Context(
                    id="professional",
                    name="Professional Manufacturing",
                    description="Commercial-grade production"
                )
            ]
        elif domain == "cooking":
            contexts = [
                Context(
                    id="home",
                    name="Home Cooking",
                    description="Basic home kitchen capabilities"
                ),
                Context(
                    id="commercial",
                    name="Commercial Kitchen",
                    description="Professional kitchen capabilities"
                )
            ]
        else:
            contexts = []
        
        # Apply name filter if provided
        if filter_params.name:
            contexts = [c for c in contexts if filter_params.name.lower() in c.name.lower()]
        
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