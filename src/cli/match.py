"""
Enhanced matching commands for OME CLI with standardized patterns

This module provides standardized commands for matching OKH requirements with OKW capabilities,
including LLM integration, enhanced error handling, and consistent output formatting.
"""

import click
import json
from pathlib import Path
from typing import Optional, Dict, Any
from urllib.parse import urlparse

from ..core.models.okh import OKHManifest
from ..core.services.matching_service import MatchingService
from ..core.models.base.base_types import NormalizedCapabilities
from .base import (
    CLIContext, SmartCommand, format_llm_output,
    create_llm_request_data, log_llm_usage
)
from .decorators import standard_cli_command


@click.group()
def match_group():
    """
    Matching operations commands for OKH/OKW compatibility.
    
    These commands help you find manufacturing facilities that can produce
    your OKH designs by matching requirements with capabilities.
    
    Examples:
      # Match requirements from an OKH file
      ome match requirements my-design.okh.json
      
      # Match with specific filters
      ome match requirements my-design.okh.json --location "San Francisco" --access-type public
      
      # Use LLM for enhanced matching
      ome match requirements my-design.okh.json --use-llm --quality-level professional
    """
    pass


@match_group.command()
@click.argument('input_file', type=str)
@click.option('--domain', 
              type=click.Choice(['manufacturing', 'cooking']),
              help='Domain override (auto-detected from file if not provided)')
@click.option('--facility-file',
              type=click.Path(exists=True),
              help='Local facility file to use for matching (testing/debugging)')
@click.option('--access-type', 
              type=click.Choice(['public', 'private', 'restricted']),
              help='Filter by facility access type')
@click.option('--facility-status', 
              type=click.Choice(['active', 'inactive', 'maintenance']),
              help='Filter by facility status')
@click.option('--location', help='Filter by location (city, country, or region)')
@click.option('--capabilities', help='Comma-separated list of required capabilities')
@click.option('--materials', help='Comma-separated list of required materials')
@click.option('--min-confidence', type=float, default=0.3,
              help='Minimum confidence threshold for matches (0.0-1.0). Default: 0.3 (relaxed)')
@click.option('--max-results', type=int, default=10,
              help='Maximum number of results to return')
@click.option('--output', '-o', help='Output file path')
@standard_cli_command(
    help_text="""
    Match requirements to capabilities (supports both manufacturing and cooking domains).
    
    This command analyzes an input file or URL (OKH manifest for manufacturing or recipe for cooking)
    and finds facilities (OKW facilities or kitchens) that can satisfy the requirements.
    
    Input can be:
    - Local file path (e.g., my-design.okh.json)
    - HTTP/HTTPS URL (e.g., https://example.com/manifest.json)
    
    For manufacturing domain:
    - Process requirements (3D printing, CNC machining, etc.)
    - Material requirements (PLA, metal, etc.)
    - Quality and precision requirements
    - Location and access preferences
    - Facility capabilities and equipment
    
    For cooking domain:
    - Ingredient requirements
    - Equipment requirements
    - Appliance requirements
    - Kitchen capabilities
    
    When LLM is enabled, the matching process uses advanced AI to:
    - Better understand requirements
    - Find creative solutions
    - Provide detailed explanations for matches
    - Suggest alternative approaches
    """,
    epilog="""
    Examples:
      # Match OKH requirements (manufacturing) from local file
      ome match requirements my-design.okh.json
      
      # Match OKH requirements from URL
      ome match requirements https://example.com/manifest.okh.json
      
      # Match recipe requirements (cooking)
      ome match requirements chocolate-chip-cookies-recipe.json
      
      # Match with location filter
      ome match requirements my-design.okh.json --location "Berlin"
      
      # High-confidence matches only
      ome match requirements my-design.okh.json --min-confidence 0.9
      
      # Use LLM for enhanced matching
      ome match requirements my-design.okh.json --use-llm --quality-level professional
      
      # Save results to file
      ome match requirements my-design.okh.json --output matches.json
    """,
    async_cmd=True,
    track_performance=True,
    handle_errors=True,
    format_output=True,
    add_llm_config=True
)
@click.pass_context
async def requirements(ctx, input_file: str, domain: Optional[str],
                      facility_file: Optional[str],
                      access_type: Optional[str], 
                      facility_status: Optional[str], location: Optional[str],
                      capabilities: Optional[str], materials: Optional[str],
                      min_confidence: float, max_results: int, output: Optional[str],
                      verbose: bool, output_format: str, use_llm: bool,
                      llm_provider: str, llm_model: Optional[str],
                      quality_level: str, strict_mode: bool):
    """Match OKH requirements to OKW capabilities with enhanced LLM support."""
    cli_ctx = ctx.obj
    cli_ctx.start_command_tracking("match-requirements")
    
    # Update CLI context with parameters from decorator
    cli_ctx.update_llm_config(
        use_llm=use_llm,
        llm_provider=llm_provider,
        llm_model=llm_model,
        quality_level=quality_level,
        strict_mode=strict_mode
    )
    
    try:
        # Check if input is a URL
        is_url = _is_url(input_file)
        
        if is_url:
            cli_ctx.log(f"Detected URL input: {input_file}", "info")
            input_data = None  # URLs will be passed directly to API
        else:
            # Read and validate input file
            cli_ctx.log("Reading input file...", "info")
            input_data = await _read_input_file(input_file)
        
        # Detect domain from file content if not provided
        # For URLs, default to manufacturing if domain not specified
        if is_url and not domain:
            detected_domain = "manufacturing"  # Default for URLs (most common case)
            cli_ctx.log(f"Using default domain for URL: {detected_domain}", "info")
        elif input_data:
            detected_domain = domain or _detect_domain_from_data(input_data)
            cli_ctx.log(f"Detected domain: {detected_domain}", "info")
        else:
            detected_domain = domain or "manufacturing"
            cli_ctx.log(f"Using domain: {detected_domain}", "info")
        
        # Parse filter options
        filters = _parse_match_filters(
            access_type, facility_status, location, 
            capabilities, materials, min_confidence, max_results
        )
        
        # Create request data based on domain and input type
        if detected_domain == "manufacturing":
            if is_url:
                request_data = create_llm_request_data(cli_ctx, {
                    "okh_url": input_file,
                    "domain": detected_domain,
                    **filters
                })
            else:
                request_data = create_llm_request_data(cli_ctx, {
                    "okh_manifest": input_data,
                    "domain": detected_domain,
                    **filters
                })
        elif detected_domain == "cooking":
            if is_url:
                request_data = create_llm_request_data(cli_ctx, {
                    "recipe_url": input_file,
                    "domain": detected_domain,
                    **filters
                })
            else:
                request_data = create_llm_request_data(cli_ctx, {
                    "recipe": input_data,
                    "domain": detected_domain,
                    **filters
                })
        else:
            raise click.ClickException(f"Unsupported domain: {detected_domain}")
        
        # Log LLM usage if enabled
        if cli_ctx.is_llm_enabled():
            log_llm_usage(cli_ctx, "requirements matching")
        
        async def http_match():
            """Match via HTTP API"""
            # If facility_file is provided, we need to use fallback
            # (HTTP API doesn't support local facility files)
            if facility_file:
                cli_ctx.log("Local facility file provided - HTTP API doesn't support this, using fallback", "info")
                # Raise exception to trigger fallback
                import httpx
                raise httpx.ConnectError("Use fallback for local facility file")
            
            cli_ctx.log("Attempting HTTP API matching...", "info")
            try:
                response = await cli_ctx.api_client.request(
                    "POST", "/api/match", json_data=request_data
                )
                # Extract data from wrapped response (api_endpoint decorator wraps it)
                if isinstance(response, dict) and "data" in response:
                    return response["data"]
                return response
            except Exception as e:
                cli_ctx.log(f"HTTP API request failed: {type(e).__name__}: {e}", "debug")
                raise
        
        async def fallback_match():
            """Match using direct service calls"""
            cli_ctx.log("Using direct service matching...", "info")
            
            if detected_domain == "manufacturing":
                # Handle URL or local file
                if is_url:
                    # Fetch manifest from URL
                    from ..core.services.okh_service import OKHService
                    okh_service = await OKHService.get_instance()
                    manifest = await okh_service.fetch_from_url(input_file)
                else:
                    manifest = OKHManifest.from_dict(input_data)
                
                matching_service = await MatchingService.get_instance()
                
                # Get facilities for matching with filters
                from ..core.services.okw_service import OKWService
                okw_service = await OKWService.get_instance()
                
                # Build filter_params for okw_service.list() if filters are provided
                filter_params = {}
                if filters.get("access_type"):
                    filter_params["access_type"] = filters.get("access_type")
                if filters.get("facility_status"):
                    filter_params["facility_status"] = filters.get("facility_status")
                if filters.get("location"):
                    filter_params["location"] = filters.get("location")
                
                facilities, _ = await okw_service.list(filter_params=filter_params if filter_params else None)
                
                # Apply additional filters that aren't supported by okw_service.list()
                # (e.g., capabilities, materials would need more complex matching logic)
                
                results = await matching_service.find_matches_with_manifest(
                    manifest, facilities, explicit_domain=detected_domain
                )
                
                # Convert Set to List
                results_list = list(results)
                
                # Apply min_confidence filter if provided
                min_confidence = filters.get("min_confidence", 0.0)
                if min_confidence > 0.0:
                    results_list = [r for r in results_list if r.score >= min_confidence]
                
                # Apply max_results limit if provided
                max_results = filters.get("max_results")
                if max_results and max_results > 0:
                    # Sort by score (descending) before limiting
                    results_list = sorted(results_list, key=lambda x: x.score, reverse=True)[:max_results]
                
                if results_list:
                    return {"solutions": [r.to_dict() for r in results_list], "total_solutions": len(results_list)}
                else:
                    return {"solutions": [], "total_solutions": 0, "message": "No matching facilities found"}
            elif detected_domain == "cooking":
                # Use cooking domain extractor and matcher
                from ..core.domains.cooking.extractors import CookingExtractor
                from ..core.domains.cooking.matchers import CookingMatcher
                from ..core.services.storage_service import StorageService
                from ..config.storage_config import get_default_storage_config
                
                # Handle URL or local file for cooking domain
                if is_url:
                    # Fetch recipe from URL
                    import httpx
                    async with httpx.AsyncClient(timeout=120.0) as client:
                        response = await client.get(input_file)
                        response.raise_for_status()
                        content = response.text
                        if input_file.endswith(('.yaml', '.yml')) or 'yaml' in response.headers.get('content-type', ''):
                            import yaml
                            recipe_data = yaml.safe_load(content)
                        else:
                            recipe_data = json.loads(content)
                else:
                    recipe_data = input_data
                
                extractor = CookingExtractor()
                matcher = CookingMatcher()
                
                # Extract requirements from recipe
                extraction_result = extractor.extract_requirements(recipe_data)
                requirements = extraction_result.data if extraction_result.data else None
                
                if not requirements:
                    return {"solutions": [], "total_solutions": 0, "message": "Failed to extract requirements from recipe"}
                
                # Load kitchens - either from local file or from storage
                kitchens = []
                
                if facility_file:
                    # Use local facility file for testing/debugging
                    cli_ctx.log(f"Using local facility file: {facility_file}", "info")
                    try:
                        with open(facility_file, 'r') as f:
                            kitchen_data = json.load(f)
                        kitchens.append(kitchen_data)
                        cli_ctx.log(f"✅ Loaded kitchen from file: {kitchen_data.get('name', 'Unknown')} (ID: {kitchen_data.get('id', 'N/A')[:8]})", "info")
                        if cli_ctx.verbose:
                            cli_ctx.log(f"Kitchen data: {json.dumps(kitchen_data, indent=2, default=str)[:500]}...", "info")
                    except Exception as e:
                        cli_ctx.log(f"Failed to load facility file: {e}", "error")
                        raise click.ClickException(f"Failed to load facility file: {e}")
                else:
                    # Load kitchens from storage using OKWService for proper discovery
                    from ..core.services.okw_service import OKWService
                    okw_service = await OKWService.get_instance()
                    
                    # Get all facilities (OKWService handles discovery properly)
                    facilities, total = await okw_service.list()
                    
                    cli_ctx.log(f"Found {total} total facilities in storage", "info")
                    
                    # Filter for cooking domain facilities (kitchens)
                    for facility in facilities:
                        # Check if facility is in cooking domain
                        facility_dict = facility.to_dict()
                        facility_domain = facility_dict.get("domain", "manufacturing")
                        facility_name = facility_dict.get("name", "").lower()
                        facility_desc = facility_dict.get("description", "").lower()
                        
                        # Include if domain is cooking, or if name/description contains cooking-related keywords
                        is_cooking = (
                            facility_domain == "cooking" or 
                            "kitchen" in facility_name or
                            "dessert" in facility_name or
                            "cooking" in facility_desc or
                            "recipe" in facility_desc
                        )
                        
                        if is_cooking:
                            kitchens.append(facility_dict)
                            cli_ctx.log(f"Loaded kitchen: {facility_dict.get('name', 'Unknown')} (ID: {facility_dict.get('id', 'N/A')[:8]}, domain: {facility_domain})", "info")
                    
                    cli_ctx.log(f"Loaded {len(kitchens)} kitchens from storage (filtered from {total} total facilities)", "info")
                
                # Match against each kitchen
                solutions = []
                cli_ctx.log(f"Starting matching process for {len(kitchens)} kitchen(s)...", "info")
                
                if len(kitchens) == 0:
                    cli_ctx.log("⚠️  No kitchens loaded - cannot perform matching", "warning")
                    return {"solutions": [], "total_solutions": 0, "message": "No kitchens found to match against"}
                
                for kitchen in kitchens:
                    kitchen_name = kitchen.get('name', 'Unknown')
                    cli_ctx.log(f"🔍 Matching against kitchen: {kitchen_name}", "info")
                    
                    # Extract requirements (for debugging)
                    if cli_ctx.verbose:
                        req_content = requirements.content if hasattr(requirements, 'content') else requirements
                        cli_ctx.log(f"Requirements to match: {req_content}", "debug")
                    
                    # Extract capabilities from kitchen
                    cli_ctx.log(f"Extracting capabilities from kitchen data...", "info")
                    capabilities_result = extractor.extract_capabilities(kitchen)
                    capabilities = capabilities_result.data if capabilities_result.data else None
                    
                    if not capabilities:
                        cli_ctx.log(f"⚠️  No capabilities extracted from kitchen: {kitchen_name}", "warning")
                        if cli_ctx.verbose:
                            cli_ctx.log(f"Kitchen data structure: {list(kitchen.keys())}", "info")
                            cli_ctx.log(f"Kitchen equipment: {kitchen.get('equipment', [])}", "info")
                            cli_ctx.log(f"Kitchen typical_materials: {kitchen.get('typical_materials', [])}", "info")
                        # Still try to match with empty capabilities (will result in low confidence)
                        capabilities = NormalizedCapabilities(content={"available_ingredients": [], "available_tools": [], "appliances": []}, domain="cooking")
                    
                    cap_content = capabilities.content if hasattr(capabilities, 'content') else capabilities
                    cli_ctx.log(f"✅ Extracted capabilities: ingredients={len(cap_content.get('available_ingredients', []))}, tools={len(cap_content.get('available_tools', []))}, appliances={len(cap_content.get('appliances', []))}", "info")
                    if cli_ctx.verbose:
                        cli_ctx.log(f"Full capabilities: {cap_content}", "info")
                        req_content = requirements.content if hasattr(requirements, 'content') else requirements
                        cli_ctx.log(f"Requirements to match: {req_content}", "info")
                    
                    # Get kitchen and recipe names for supply tree
                    recipe_name = recipe_data.get("title", recipe_data.get("name", "Unknown Recipe"))
                    cli_ctx.log(f"Generating supply tree for recipe '{recipe_name}' and kitchen '{kitchen_name}'...", "info")
                    
                    try:
                        supply_tree = matcher.generate_supply_tree(requirements, capabilities, kitchen_name, recipe_name)
                        confidence = supply_tree.confidence_score if hasattr(supply_tree, 'confidence_score') else 0.8
                        cli_ctx.log(f"✅ Match confidence: {confidence:.2f}", "info")
                    except Exception as e:
                        cli_ctx.log(f"❌ Error generating supply tree: {type(e).__name__}: {e}", "error")
                        if cli_ctx.verbose:
                            import traceback
                            cli_ctx.log(f"Traceback: {traceback.format_exc()}", "info")
                        continue
                    
                    solution = {
                        "tree": supply_tree.to_dict() if hasattr(supply_tree, 'to_dict') else supply_tree,
                        "facility": kitchen,
                        "facility_id": kitchen.get("id", kitchen.get("storage_key", "unknown")),
                        "facility_name": kitchen_name,
                        "match_type": "cooking",
                        "confidence": confidence,
                        "score": confidence  # Add score for consistency with manufacturing domain
                    }
                    solutions.append(solution)
                
                # Apply min_confidence filter if provided
                min_confidence = filters.get("min_confidence", 0.0)
                if min_confidence > 0.0:
                    solutions = [s for s in solutions if s.get("confidence", s.get("score", 0)) >= min_confidence]
                
                # Apply max_results limit if provided
                max_results = filters.get("max_results")
                if max_results and max_results > 0:
                    # Sort by confidence (descending) before limiting
                    solutions = sorted(solutions, key=lambda x: x.get("confidence", x.get("score", 0)), reverse=True)[:max_results]
                
                return {"solutions": solutions, "total_solutions": len(solutions)}
            else:
                raise click.ClickException(f"Unsupported domain: {detected_domain}")
        
        # Execute matching with fallback
        command = SmartCommand(cli_ctx)
        result = await command.execute_with_fallback(http_match, fallback_match)
        
        # Handle None result (when http_match returns None to force fallback)
        if result is None:
            cli_ctx.log("HTTP API returned None, using fallback result", "info")
            result = await fallback_match()
        
        # Process and display results
        await _display_match_results(cli_ctx, result, output, output_format)
        
        # Cleanup storage service if it was used
        if detected_domain == "cooking":
            try:
                from ..core.services.storage_service import StorageService
                storage_service = await StorageService.get_instance()
                if storage_service and hasattr(storage_service, 'cleanup'):
                    await storage_service.cleanup()
            except Exception:
                pass  # Ignore cleanup errors
        
        cli_ctx.end_command_tracking()
        
    except Exception as e:
        cli_ctx.log(f"Matching failed: {str(e)}", "error")
        raise


@match_group.command()
@click.argument('okh_file', type=click.Path(exists=True))
@click.option('--domain', 
              type=click.Choice(['manufacturing', 'cooking']),
              help='Domain override (auto-detected from file if not provided)')
@click.option('--output', '-o', help='Output file path')
@standard_cli_command(
    help_text="""
    Validate OKH manifest for matching compatibility.
    
    This command validates that an OKH manifest contains all necessary
    information for successful matching operations.
    
    Validation checks include:
    - Required fields are present
    - Process requirements are properly specified
    - Material requirements are valid
    - Manufacturing specifications are complete
    - File format and structure are correct
    
    When LLM is enabled, validation includes:
    - Semantic analysis of requirements
    - Suggestions for missing information
    - Quality assessment of specifications
    - Recommendations for improvement
    """,
    async_cmd=True,
    track_performance=True,
    handle_errors=True,
    format_output=True,
    add_llm_config=True
)
@click.pass_context
async def validate(ctx, okh_file: str, domain: Optional[str], output: Optional[str],
                  verbose: bool, output_format: str, use_llm: bool,
                  llm_provider: str, llm_model: Optional[str],
                  quality_level: str, strict_mode: bool):
    """Validate OKH manifest for matching compatibility."""
    cli_ctx = ctx.obj
    cli_ctx.start_command_tracking("validate-okh")
    
    # Update CLI context with parameters from decorator
    cli_ctx.update_llm_config(
        use_llm=use_llm,
        llm_provider=llm_provider,
        llm_model=llm_model,
        quality_level=quality_level,
        strict_mode=strict_mode
    )
    
    try:
        # Read input file
        cli_ctx.log("Reading input file...", "info")
        input_data = await _read_input_file(okh_file)
        
        # Detect or use explicit domain
        detected_domain = domain or _detect_domain_from_data(input_data) if input_data else None
        if detected_domain:
            cli_ctx.log(f"Using domain: {detected_domain}", "info")
            # Set domain in input_data so API can detect it
            if input_data and not input_data.get("domain"):
                input_data["domain"] = detected_domain
        
        # Log LLM usage if enabled
        if cli_ctx.is_llm_enabled():
            log_llm_usage(cli_ctx, "OKH validation")
        
        async def http_validate():
            """Validate via HTTP API (using OKH validate endpoint)"""
            cli_ctx.log("Validating via HTTP API...", "info")
            # Use OKH validate endpoint which accepts content directly
            request_data = create_llm_request_data(cli_ctx, {
                "content": input_data,
                "validation_context": quality_level
            })
            response = await cli_ctx.api_client.request(
                "POST", "/api/okh/validate", json_data=request_data, params={"quality_level": quality_level, "strict_mode": strict_mode}
            )
            return response
        
        async def fallback_validate():
            """Validate using direct service calls"""
            cli_ctx.log("Using direct service validation...", "info")
            manifest = OKHManifest.from_dict(input_data)
            
            # Basic validation
            validation_result = {
                "is_valid": True,
                "errors": [],
                "warnings": [],
                "suggestions": []
            }
            
            # Check required fields
            required_fields = ["title", "version"]
            for field in required_fields:
                if field not in input_data:
                    validation_result["errors"].append(f"Missing required field: {field}")
                    validation_result["is_valid"] = False
            
            # Check for manufacturing_specs or manufacturing_processes for manufacturing domain
            if input_data.get("domain") == "manufacturing" or (not input_data.get("domain") and "manufacturing_processes" in input_data):
                if "manufacturing_specs" not in input_data and "manufacturing_processes" not in input_data:
                    validation_result["warnings"].append("Missing manufacturing_specs or manufacturing_processes (recommended for manufacturing domain)")
            
            return validation_result
        
        # Execute validation with fallback
        command = SmartCommand(cli_ctx)
        result = await command.execute_with_fallback(http_validate, fallback_validate)
        
        # Display validation results
        await _display_validation_results(cli_ctx, result, output, output_format)
        
        cli_ctx.end_command_tracking()
        
    except Exception as e:
        cli_ctx.log(f"Validation failed: {str(e)}", "error")
        raise


@match_group.command()
@click.option('--domain', help='Filter by specific domain')
@click.option('--active-only', is_flag=True, help='Show only active domains')
@standard_cli_command(
    help_text="""
    List available matching domains.
    
    This command shows all available domains that can be used for matching
    operations, such as manufacturing, cooking, etc.
    
    Each domain provides specific matching capabilities and algorithms
    tailored to that domain's requirements and constraints.
    """,
    async_cmd=True,
    track_performance=True,
    handle_errors=True,
    format_output=True,
    add_llm_config=True
)
@click.pass_context
async def domains(ctx, domain: Optional[str], active_only: bool,
                 verbose: bool, output_format: str, use_llm: bool,
                 llm_provider: str, llm_model: Optional[str],
                 quality_level: str, strict_mode: bool):
    """List available matching domains."""
    cli_ctx = ctx.obj
    cli_ctx.start_command_tracking("list-domains")
    
    # Update CLI context with parameters from decorator
    cli_ctx.update_llm_config(
        use_llm=use_llm,
        llm_provider=llm_provider,
        llm_model=llm_model,
        quality_level=quality_level,
        strict_mode=strict_mode
    )
    
    try:
        # Create request data with LLM configuration
        request_data = create_llm_request_data(cli_ctx, {
            "domain": domain,
            "active_only": active_only
        })
        
        async def http_domains():
            """Get domains via HTTP API"""
            cli_ctx.log("Fetching domains via HTTP API...", "info")
            response = await cli_ctx.api_client.request(
                "GET", "/api/match/domains", params=request_data
            )
            return response
        
        async def fallback_domains():
            """Get domains using direct service calls"""
            cli_ctx.log("Using direct service for domains...", "info")
            matching_service = await MatchingService.get_instance()
            domains = await matching_service.get_available_domains()
            
            return {
                "domains": domains,  # domains are already dictionaries
                "total_count": len(domains)
            }
        
        # Execute with fallback
        command = SmartCommand(cli_ctx)
        result = await command.execute_with_fallback(http_domains, fallback_domains)
        
        # Display domains
        await _display_domains(cli_ctx, result, output_format)
        
        cli_ctx.end_command_tracking()
        
    except Exception as e:
        cli_ctx.log(f"Failed to list domains: {str(e)}", "error")
        raise


# Helper functions

def _is_url(path: str) -> bool:
    """Check if the given path is a URL."""
    try:
        result = urlparse(path)
        return result.scheme in ('http', 'https')
    except Exception:
        return False


async def _read_input_file(file_path: str) -> Optional[Dict[str, Any]]:
    """
    Read and parse input file (OKH or recipe) from local file or URL.
    
    Returns None if the input is a URL (to indicate it should be passed as okh_url).
    Returns the parsed data if it's a local file.
    """
    # Check if it's a URL
    if _is_url(file_path):
        # Return None to indicate this is a URL that should be passed directly
        return None
    
    # Handle local file
    input_path = Path(file_path)
    
    # Check if file exists
    if not input_path.exists():
        raise click.ClickException(f"File not found: {file_path}")
    
    try:
        with open(input_path, 'r') as f:
            if input_path.suffix.lower() in ['.yaml', '.yml']:
                import yaml
                return yaml.safe_load(f)
            else:
                return json.load(f)
    except Exception as e:
        raise click.ClickException(f"Failed to read input file: {str(e)}")


def _detect_domain_from_data(data: Dict[str, Any]) -> str:
    """Detect domain from input data structure."""
    # First check for explicit domain field
    if "domain" in data and data["domain"]:
        return data["domain"]
    
    # Check for OKH/manufacturing indicators
    if "title" in data and "version" in data and ("manufacturing_specs" in data or "manufacturing_processes" in data):
        return "manufacturing"
    
    # Check for recipe/cooking indicators
    if "ingredients" in data and "instructions" in data and "name" in data:
        return "cooking"
    
    # Default to manufacturing for backward compatibility
    return "manufacturing"


def _parse_match_filters(access_type: Optional[str], facility_status: Optional[str],
                        location: Optional[str], capabilities: Optional[str],
                        materials: Optional[str], min_confidence: float,
                        max_results: int) -> Dict[str, Any]:
    """Parse and validate match filter options."""
    filters = {
        "access_type": access_type,
        "facility_status": facility_status,
        "location": location,
        "min_confidence": min_confidence,
        "max_results": max_results
    }
    
    # Parse comma-separated lists
    if capabilities:
        filters["capabilities"] = [cap.strip() for cap in capabilities.split(',')]
    if materials:
        filters["materials"] = [mat.strip() for mat in materials.split(',')]
    
    return filters


async def _display_match_results(cli_ctx: CLIContext, result: Dict[str, Any], 
                               output: Optional[str], output_format: str):
    """Display matching results in the specified format."""
    # Handle both old format (matches) and new format (solutions)
    solutions = result.get("solutions", result.get("matches", []))
    total_solutions = result.get("total_solutions", len(solutions))
    
    if total_solutions == 0:
        cli_ctx.log("No matching facilities found", "warning")
        # Still save to output file if requested, even with no results
        if output and output_format == "json":
            output_data = format_llm_output(result, cli_ctx)
            with open(output, 'w') as f:
                f.write(output_data)
            cli_ctx.log(f"Results saved to {output}", "success")
        return
    
    cli_ctx.log(f"Found {total_solutions} matching facilities", "success")
    
    # Format output based on format preference
    if output_format == "json":
        output_data = format_llm_output(result, cli_ctx)
        if output:
            with open(output, 'w') as f:
                f.write(output_data)
            cli_ctx.log(f"Results saved to {output}", "success")
        else:
            click.echo(output_data)
    else:
        # Table format
        for i, solution in enumerate(solutions, 1):
            # Handle both old format (direct match dict) and new format (solution with tree/facility)
            if "facility" in solution:
                facility = solution.get("facility", {})
                facility_name = facility.get("name", "Unknown Facility") if isinstance(facility, dict) else getattr(facility, "name", "Unknown Facility")
                confidence = solution.get("confidence", 0)
            else:
                facility_name = solution.get("name", "Unknown Facility")
                confidence = solution.get("confidence", solution.get("score", 0))
            
            click.echo(f"\n{i}. {facility_name}")
            
            # Show facility ID if available
            facility_id = solution.get("facility_id")
            if facility_id:
                # Show full UUID (needed for subsequent commands like 'okw get')
                click.echo(f"   ID: {facility_id}")
            
            if "facility" in solution and isinstance(solution["facility"], dict):
                location = solution["facility"].get("location", "Unknown")
                if location != "Unknown":
                    click.echo(f"   Location: {location}")
            click.echo(f"   Confidence: {confidence:.2f}")
            
            # Show match type if available
            match_type = solution.get("match_type", "unknown")
            if match_type != "unknown":
                click.echo(f"   Match Type: {match_type}")


async def _display_validation_results(cli_ctx: CLIContext, result: Dict[str, Any],
                                    output: Optional[str], output_format: str):
    """Display validation results."""
    is_valid = result.get("is_valid", False)
    errors = result.get("errors", [])
    warnings = result.get("warnings", [])
    suggestions = result.get("suggestions", [])
    
    if is_valid:
        cli_ctx.log("OKH manifest is valid", "success")
    else:
        cli_ctx.log("OKH manifest has validation errors", "error")
    
    # Display errors
    for error in errors:
        cli_ctx.log(f"Error: {error}", "error")
    
    # Display warnings
    for warning in warnings:
        cli_ctx.log(f"Warning: {warning}", "warning")
    
    # Display suggestions
    for suggestion in suggestions:
        cli_ctx.log(f"Suggestion: {suggestion}", "info")
    
    # Save to file if requested
    if output:
        with open(output, 'w') as f:
            json.dump(result, f, indent=2)
        cli_ctx.log(f"Validation results saved to {output}", "success")


async def _display_domains(cli_ctx: CLIContext, result: Dict[str, Any], output_format: str):
    """Display available domains."""
    # Handle both PaginatedResponse format (from API) and simple dict format (from fallback)
    if "items" in result:
        # PaginatedResponse format from API
        domains = result.get("items", [])
        pagination = result.get("pagination", {})
        total_count = pagination.get("total_items", len(domains))
    elif "data" in result and isinstance(result["data"], dict):
        # Wrapped response format
        data = result["data"]
        if "items" in data:
            domains = data.get("items", [])
            pagination = data.get("pagination", {})
            total_count = pagination.get("total_items", len(domains))
        else:
            domains = data.get("domains", [])
            total_count = len(domains)
    else:
        # Simple dict format (from fallback)
        domains = result.get("domains", [])
        total_count = result.get("total_count", len(domains))
    
    cli_ctx.log(f"Found {total_count} available domains", "success")
    
    if output_format == "json":
        output_data = format_llm_output(result, cli_ctx)
        click.echo(output_data)
    else:
        # Table format
        for domain in domains:
            click.echo(f"\n{domain.get('name', 'Unknown Domain')}")
            click.echo(f"  ID: {domain.get('id', 'unknown')}")
            click.echo(f"  Description: {domain.get('description', 'No description')}")
            click.echo(f"  Status: {domain.get('status', 'unknown')}")
