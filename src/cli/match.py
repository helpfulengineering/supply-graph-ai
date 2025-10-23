"""
Enhanced matching commands for OME CLI with standardized patterns

This module provides standardized commands for matching OKH requirements with OKW capabilities,
including LLM integration, enhanced error handling, and consistent output formatting.
"""

import click
import json
from pathlib import Path
from typing import Optional, Dict, Any

from ..core.models.okh import OKHManifest
from ..core.services.matching_service import MatchingService
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
@click.argument('okh_file', type=click.Path(exists=True))
@click.option('--access-type', 
              type=click.Choice(['public', 'private', 'restricted']),
              help='Filter by facility access type')
@click.option('--facility-status', 
              type=click.Choice(['active', 'inactive', 'maintenance']),
              help='Filter by facility status')
@click.option('--location', help='Filter by location (city, country, or region)')
@click.option('--capabilities', help='Comma-separated list of required capabilities')
@click.option('--materials', help='Comma-separated list of required materials')
@click.option('--min-confidence', type=float, default=0.7,
              help='Minimum confidence threshold for matches (0.0-1.0)')
@click.option('--max-results', type=int, default=10,
              help='Maximum number of results to return')
@click.option('--output', '-o', help='Output file path')
@standard_cli_command(
    help_text="""
    Match OKH requirements to OKW capabilities.
    
    This command analyzes an OKH manifest file and finds manufacturing facilities
    that can produce the design based on their capabilities and requirements.
    
    The matching process considers:
    - Process requirements (3D printing, CNC machining, etc.)
    - Material requirements (PLA, metal, etc.)
    - Quality and precision requirements
    - Location and access preferences
    - Facility capabilities and equipment
    
    When LLM is enabled, the matching process uses advanced AI to:
    - Better understand process requirements
    - Find creative solutions for complex designs
    - Provide detailed explanations for matches
    - Suggest alternative manufacturing approaches
    """,
    epilog="""
    Examples:
      # Basic matching
      ome match requirements my-design.okh.json
      
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
async def requirements(ctx, okh_file: str, access_type: Optional[str], 
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
        # Read and validate OKH file
        cli_ctx.log("Reading OKH file...", "info")
        okh_data = await _read_okh_file(okh_file)
        
        # Parse filter options
        filters = _parse_match_filters(
            access_type, facility_status, location, 
            capabilities, materials, min_confidence, max_results
        )
        
        # Create request data with LLM configuration
        request_data = create_llm_request_data(cli_ctx, {
            "okh_manifest": okh_data,
            "filters": filters
        })
        
        # Log LLM usage if enabled
        if cli_ctx.is_llm_enabled():
            log_llm_usage(cli_ctx, "requirements matching")
        
        async def http_match():
            """Match via HTTP API"""
            cli_ctx.log("Attempting HTTP API matching...", "info")
            response = await cli_ctx.api_client.request(
                "POST", "/match", json_data=request_data
            )
            return response
        
        async def fallback_match():
            """Match using direct service calls"""
            cli_ctx.log("Using direct service matching...", "info")
            manifest = OKHManifest.from_dict(okh_data)
            matching_service = await MatchingService.get_instance()
            
            # Get facilities for matching
            from ..core.services.okw_service import OKWService
            okw_service = await OKWService.get_instance()
            facilities, _ = await okw_service.list()
            
            # Create match request
            from ..core.api.models.match.request import MatchRequest
            match_request = MatchRequest(
                okh_manifest=okh_data,
                access_type=filters.get("access_type"),
                facility_status=filters.get("facility_status"),
                location=filters.get("location"),
                capabilities=filters.get("capabilities"),
                materials=filters.get("materials"),
                min_confidence=filters.get("min_confidence"),
                max_results=filters.get("max_results")
            )
            
            results = await matching_service.find_matches_with_manifest(manifest, facilities)
            # Convert Set to List and return first result for CLI compatibility
            results_list = list(results)
            if results_list:
                return results_list[0].to_dict()
            else:
                return {"message": "No matching facilities found"}
        
        # Execute matching with fallback
        command = SmartCommand(cli_ctx)
        result = await command.execute_with_fallback(http_match, fallback_match)
        
        # Process and display results
        await _display_match_results(cli_ctx, result, output, output_format)
        
        cli_ctx.end_command_tracking()
        
    except Exception as e:
        cli_ctx.log(f"Matching failed: {str(e)}", "error")
        raise


@match_group.command()
@click.argument('okh_file', type=click.Path(exists=True))
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
async def validate(ctx, okh_file: str, output: Optional[str],
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
        # Read OKH file
        cli_ctx.log("Reading OKH file...", "info")
        okh_data = await _read_okh_file(okh_file)
        
        # Create request data with LLM configuration
        request_data = create_llm_request_data(cli_ctx, {
            "okh_content": okh_data
        })
        
        # Log LLM usage if enabled
        if cli_ctx.is_llm_enabled():
            log_llm_usage(cli_ctx, "OKH validation")
        
        async def http_validate():
            """Validate via HTTP API"""
            cli_ctx.log("Validating via HTTP API...", "info")
            response = await cli_ctx.api_client.request(
                "POST", "/match/validate", json_data=request_data
            )
            return response
        
        async def fallback_validate():
            """Validate using direct service calls"""
            cli_ctx.log("Using direct service validation...", "info")
            manifest = OKHManifest.from_dict(okh_data)
            
            # Basic validation
            validation_result = {
                "is_valid": True,
                "errors": [],
                "warnings": [],
                "suggestions": []
            }
            
            # Check required fields
            required_fields = ["title", "version", "manufacturing_specs"]
            for field in required_fields:
                if field not in okh_data:
                    validation_result["errors"].append(f"Missing required field: {field}")
                    validation_result["is_valid"] = False
            
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
                "GET", "/match/domains", params=request_data
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

async def _read_okh_file(file_path: str) -> Dict[str, Any]:
    """Read and parse OKH file."""
    okh_path = Path(file_path)
    
    try:
        with open(okh_path, 'r') as f:
            if okh_path.suffix.lower() in ['.yaml', '.yml']:
                import yaml
                return yaml.safe_load(f)
            else:
                return json.load(f)
    except Exception as e:
        raise click.ClickException(f"Failed to read OKH file: {str(e)}")


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
    matches = result.get("matches", [])
    total_matches = len(matches)
    
    if total_matches == 0:
        cli_ctx.log("No matching facilities found", "warning")
        return
    
    cli_ctx.log(f"Found {total_matches} matching facilities", "success")
    
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
        for i, match in enumerate(matches, 1):
            click.echo(f"\n{i}. {match.get('name', 'Unknown Facility')}")
            click.echo(f"   Location: {match.get('location', 'Unknown')}")
            click.echo(f"   Confidence: {match.get('confidence', 0):.2f}")
            click.echo(f"   Capabilities: {', '.join(match.get('capabilities', []))}")


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
