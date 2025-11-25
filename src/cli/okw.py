"""
OKW (OpenKnowWhere) commands for OME CLI

This module provides commands for managing OKW facilities including
creation, validation, listing, and matching operations.
"""

import click
import json
from pathlib import Path
from typing import Optional
from uuid import UUID

from ..core.models.okw import ManufacturingFacility
from ..core.services.okw_service import OKWService
from ..core.services.storage_service import StorageService
from ..core.validation.auto_fix import auto_fix_okw_facility
from ..core.validation.model_validator import validate_okw_facility
from .base import (
    CLIContext, SmartCommand, format_llm_output,
    create_llm_request_data, log_llm_usage
)
from .decorators import standard_cli_command


@click.group()
def okw_group():
    """
    OKW (OpenKnowWhere) facility management commands.
    
    These commands help you create, validate, and manage OKW facilities
    for manufacturing capabilities, including facility registration,
    capability extraction, and facility search operations.
    
    Examples:
      # Validate an OKW facility
      ome okw validate my-facility.okw.json
      
      # Create and store a facility
      ome okw create my-facility.okw.json
      
      # Search for facilities by capability
      ome okw search --capability "PCB Assembly" --location "San Francisco"
      
      # Use LLM for enhanced processing
      ome okw validate my-facility.okw.json --use-llm --quality-level professional
    """
    pass


# Helper functions

async def _read_facility_file(file_path: str) -> dict:
    """Read and parse facility file."""
    facility_path = Path(file_path)
    
    try:
        with open(facility_path, 'r') as f:
            if facility_path.suffix.lower() in ['.yaml', '.yml']:
                import yaml
                return yaml.safe_load(f)
            else:
                return json.load(f)
    except Exception as e:
        raise click.ClickException(f"Failed to read facility file: {str(e)}")


async def _display_validation_results(cli_ctx: CLIContext, result: dict, output_format: str):
    """Display validation results."""
    validation = result.get("validation", result)
    is_valid = validation.get("is_valid", False)
    
    if is_valid:
        cli_ctx.log("Facility is valid", "success")
    else:
        cli_ctx.log("Facility validation failed", "error")
    
    # Display errors
    if validation.get("errors"):
        for error in validation["errors"]:
            cli_ctx.log(f"Error: {error}", "error")
    
    # Display warnings
    if validation.get("warnings"):
        for warning in validation["warnings"]:
            cli_ctx.log(f"Warning: {warning}", "warning")
    
    # Display completeness score
    if validation.get("completeness_score"):
        score = validation["completeness_score"]
        cli_ctx.log(f"Completeness Score: {score:.1%}", "info")
    
    # Format output based on format preference
    if output_format == "json":
        output_data = format_llm_output(result, cli_ctx)
        click.echo(output_data)


async def _display_creation_results(cli_ctx: CLIContext, result: dict, output: Optional[str], output_format: str):
    """Display creation results."""
    facility_id = result.get("id") or result.get("facility", {}).get("id")
    
    if facility_id:
        cli_ctx.log(f"OKW facility created with ID: {facility_id}", "success")
        
        if output:
            # Save result to output file
            with open(output, 'w') as f:
                json.dump(result, f, indent=2, default=str)
            cli_ctx.log(f"Result saved to {output}", "info")
        
        if output_format == "json":
            output_data = format_llm_output(result, cli_ctx)
            click.echo(output_data)
    else:
        cli_ctx.log("Failed to create OKW facility", "error")


async def _display_retrieval_results(cli_ctx: CLIContext, result: dict, output: Optional[str], output_format: str):
    """Display retrieval results."""
    # Extract facility data from response
    # The API now returns OKWResponse with fields at top level, not nested in "facility"
    facility = result.get("facility", result)
    
    # If result has top-level fields like "id", "name", etc., use result directly
    if "id" in result and "name" in result:
        facility = result
    elif "facility" in result:
        facility = result["facility"]
    
    if facility and facility.get("id"):
        facility_name = facility.get('name', 'Unknown')
        cli_ctx.log(f"Retrieved OKW facility: {facility_name}", "success")
        
        # Save to file if output is specified
        if output:
            with open(output, 'w') as f:
                json.dump(facility, f, indent=2, default=str)
            cli_ctx.log(f"Facility saved to {output}", "info")
        
        # Always output full JSON to stdout by default
        # If output_format is explicitly set to something other than json, still output JSON
        # (the format option is mainly for other commands)
        click.echo(json.dumps(facility, indent=2, default=str))
    else:
        cli_ctx.log("Facility not found", "error")


# Commands

@okw_group.command()
@click.argument('facility_file', type=click.Path(exists=True))
@standard_cli_command(
    help_text="""
    Validate an OKW facility for compliance and completeness.
    
    This command performs validation of an OKW facility,
    checking for required fields, proper formatting, and completeness
    according to the OKW specification.
    
    Validation includes:
    - Required field presence and format
    - Facility information completeness
    - Capability specification validation
    - Location and contact information
    - Equipment and process validation
    
    When LLM is enabled, validation includes:
    - Semantic analysis of facility descriptions and capabilities
    - Quality assessment of manufacturing specifications
    - Suggestions for improvement and missing information
    - Advanced compliance checking
    """,
    epilog="""
    Examples:
      # Basic validation
      ome okw validate my-facility.okw.json
      
      # Strict validation with medical quality level
      ome okw validate my-facility.okw.json --quality-level medical --strict-mode
      
      # Use LLM for enhanced validation
      ome okw validate my-facility.okw.json --use-llm --quality-level professional
    """,
    async_cmd=True,
    track_performance=True,
    handle_errors=True,
    format_output=True,
    add_llm_config=True
)
@click.pass_context
async def validate(ctx, facility_file: str, quality_level: str, strict_mode: bool,
                  verbose: bool, output_format: str, use_llm: bool,
                  llm_provider: str, llm_model: Optional[str]):
    """Validate an OKW facility with enhanced LLM support."""
    cli_ctx = ctx.obj
    cli_ctx.start_command_tracking("okw-validate")
    
    # Fix: Update verbose from the command parameter
    cli_ctx.verbose = verbose
    cli_ctx.config.verbose = verbose
    
    # Update CLI context with parameters from decorator
    cli_ctx.update_llm_config(
        use_llm=use_llm,
        llm_provider=llm_provider,
        llm_model=llm_model,
        quality_level=quality_level,
        strict_mode=strict_mode
    )
    
    try:
        # Read facility file
        cli_ctx.log("Reading facility file...", "info")
        facility_data = await _read_facility_file(facility_file)
    
        # Create request data with LLM configuration
        # The API expects facility data wrapped in a 'content' field
        request_data = create_llm_request_data(cli_ctx, {
            "validation_context": quality_level,
            "strict_mode": strict_mode
        })
        # Wrap facility data in 'content' field as expected by API
        request_data["content"] = facility_data
        
        # Log LLM usage if enabled
        if cli_ctx.is_llm_enabled():
            log_llm_usage(cli_ctx, "OKW validation")
        
        async def http_validate():
            """Validate via HTTP API"""
            cli_ctx.log("Validating via HTTP API...", "info")
            response = await cli_ctx.api_client.request(
                "POST", "/api/okw/validate", json_data=request_data
            )
            return response
        
        async def fallback_validate():
            """Validate using direct service calls"""
            cli_ctx.log("Using direct service validation...", "info")
            facility = ManufacturingFacility.from_dict(facility_data)
            okw_service = await OKWService.get_instance()
            result = await okw_service.validate(facility, quality_level, strict_mode)
            return result.to_dict()
        
        # Execute validation with fallback
        command = SmartCommand(cli_ctx)
        result = await command.execute_with_fallback(http_validate, fallback_validate)
        
        # Display validation results
        await _display_validation_results(cli_ctx, result, output_format)
        
        cli_ctx.end_command_tracking()
        
    except Exception as e:
        cli_ctx.log(f"Validation failed: {str(e)}", "error")
        raise


@okw_group.command()
@click.argument('facility_file', type=click.Path(exists=True))
@click.option('--output', '-o', help='Output file path')
@standard_cli_command(
    help_text="""
    Create and store an OKW facility in the system.
    
    This command reads an OKW facility file and stores it in the system
    for later retrieval, validation, and processing.
    
    The facility is validated before storage to ensure it meets
    the OKW specification requirements.
    
    When LLM is enabled, creation includes:
    - Enhanced validation with semantic analysis
    - Automatic field completion and suggestions
    - Quality assessment and recommendations
    - Advanced compliance checking
    """,
    epilog="""
    Examples:
      # Create and store a facility
      ome okw create my-facility.okw.json
      
      # Create with output file
      ome okw create my-facility.okw.json --output result.json
      
      # Use LLM for enhanced processing
      ome okw create my-facility.okw.json --use-llm --quality-level professional
    """,
    async_cmd=True,
    track_performance=True,
    handle_errors=True,
    format_output=True,
    add_llm_config=True
)
@click.pass_context
async def create(ctx, facility_file: str, output: Optional[str],
                verbose: bool, output_format: str, use_llm: bool,
                llm_provider: str, llm_model: Optional[str],
                quality_level: str, strict_mode: bool):
    """Create and store an OKW facility with enhanced LLM support."""
    cli_ctx = ctx.obj
    cli_ctx.start_command_tracking("okw-create")
    
    # Update CLI context with parameters from decorator
    cli_ctx.update_llm_config(
        use_llm=use_llm,
        llm_provider=llm_provider,
        llm_model=llm_model,
        quality_level=quality_level,
        strict_mode=strict_mode
    )
    
    try:
        # Read facility file
        cli_ctx.log("Reading facility file...", "info")
        facility_data = await _read_facility_file(facility_file)
    
        # Create request data with LLM configuration
        # Merge facility data with LLM config (facility fields go directly, not wrapped in 'content')
        request_data = create_llm_request_data(cli_ctx, {})
        # Add facility fields directly to the request
        request_data.update(facility_data)
        
        # Log LLM usage if enabled
        if cli_ctx.is_llm_enabled():
            log_llm_usage(cli_ctx, "OKW creation")
        
        async def http_create():
            """Create via HTTP API"""
            cli_ctx.log("Creating via HTTP API...", "info")
            response = await cli_ctx.api_client.request("POST", "/api/okw/create", json_data=request_data)
            return response
        
        async def fallback_create():
            """Create using direct service calls"""
            cli_ctx.log("Using direct service creation...", "info")
            okw_service = await OKWService.get_instance()
            result = await okw_service.create(facility_data)
            return result.to_dict()
        
        # Execute creation with fallback
        command = SmartCommand(cli_ctx)
        result = await command.execute_with_fallback(http_create, fallback_create)
        
        # Display creation results
        await _display_creation_results(cli_ctx, result, output, output_format)
        
        cli_ctx.end_command_tracking()
        
    except Exception as e:
        cli_ctx.log(f"Creation failed: {str(e)}", "error")
        raise


@okw_group.command()
@click.argument('facility_id', type=str)
@click.option('--output', '-o', help='Output file path')
@standard_cli_command(
    help_text="""
    Retrieve an OKW facility by ID from the system.
    
    This command fetches a previously stored OKW facility using its
    unique identifier and displays the facility information.
    
    When LLM is enabled, retrieval includes:
    - Enhanced facility analysis and summary
    - Quality assessment of the retrieved facility
    - Suggestions for improvement
    - Advanced metadata extraction
    """,
    epilog="""
    Examples:
      # Get a facility by ID
      ome okw get 123e4567-e89b-12d3-a456-426614174000
      
      # Get with output file
      ome okw get 123e4567-e89b-12d3-a456-426614174000 --output facility.json
      
      # Use LLM for enhanced analysis
      ome okw get 123e4567-e89b-12d3-a456-426614174000 --use-llm
    """,
    async_cmd=True,
    track_performance=True,
    handle_errors=True,
    format_output=True,
    add_llm_config=True
)
@click.pass_context
async def get(ctx, facility_id: str, output: Optional[str],
             verbose: bool, output_format: str, use_llm: bool,
             llm_provider: str, llm_model: Optional[str],
             quality_level: str, strict_mode: bool):
    """Get an OKW facility by ID with enhanced LLM support."""
    cli_ctx = ctx.obj
    cli_ctx.start_command_tracking("okw-get")
    
    # Update CLI context with parameters from decorator
    cli_ctx.update_llm_config(
        use_llm=use_llm,
        llm_provider=llm_provider,
        llm_model=llm_model,
        quality_level=quality_level,
        strict_mode=strict_mode
    )
    
    try:
        # Log LLM usage if enabled
        if cli_ctx.is_llm_enabled():
            log_llm_usage(cli_ctx, "OKW retrieval")
        
        async def http_get():
            """Get via HTTP API"""
            cli_ctx.log("Retrieving via HTTP API...", "info")
            response = await cli_ctx.api_client.request("GET", f"/api/okw/{facility_id}")
            return response
        
        async def fallback_get():
            """Get using direct service calls"""
            cli_ctx.log("Using direct service retrieval...", "info")
            okw_service = await OKWService.get_instance()
            facility = await okw_service.get_by_id(UUID(facility_id))
            if facility:
                return facility.to_dict()
            else:
                raise click.ClickException("Facility not found")
        
        # Execute retrieval with fallback
        command = SmartCommand(cli_ctx)
        result = await command.execute_with_fallback(http_get, fallback_get)
        
        # Display retrieval results
        await _display_retrieval_results(cli_ctx, result, output, output_format)
        
        cli_ctx.end_command_tracking()
        
    except Exception as e:
        cli_ctx.log(f"Retrieval failed: {str(e)}", "error")
        raise


@okw_group.command()
@click.option('--limit', default=10, help='Maximum number of facilities to list')
@click.option('--offset', default=0, help='Number of facilities to skip')
@click.option('--facility-type', help='Filter by facility type')
@click.option('--status', help='Filter by facility status')
@click.option('--location', help='Filter by location')
@standard_cli_command(
    help_text="""
    List stored OKW facilities in the system.
    
    This command retrieves and displays a list of all OKW facilities
    stored in the system, with pagination and filtering support.
    
    When LLM is enabled, listing includes:
    - Enhanced facility analysis and categorization
    - Quality assessment of stored facilities
    - Intelligent filtering and sorting suggestions
    - Advanced metadata extraction
    """,
    epilog="""
    Examples:
      # List all facilities
      ome okw list
      
      # List with pagination and filters
      ome okw list --limit 20 --offset 10 --facility-type "Manufacturing"
      
      # Use LLM for enhanced analysis
      ome okw list --use-llm --limit 50
    """,
    async_cmd=True,
    track_performance=True,
    handle_errors=True,
    format_output=True,
    add_llm_config=True
)
@click.pass_context
async def list_facilities(ctx, limit: int, offset: int, facility_type: Optional[str], 
                         status: Optional[str], location: Optional[str],
                         verbose: bool, output_format: str, use_llm: bool,
                         llm_provider: str, llm_model: Optional[str],
                         quality_level: str, strict_mode: bool):
    """List stored OKW facilities with enhanced LLM support."""
    cli_ctx = ctx.obj
    cli_ctx.start_command_tracking("okw-list")
    
    # Update CLI context with parameters from decorator
    cli_ctx.update_llm_config(
        use_llm=use_llm,
        llm_provider=llm_provider,
        llm_model=llm_model,
        quality_level=quality_level,
        strict_mode=strict_mode
    )
    
    try:
        # Log LLM usage if enabled
        if cli_ctx.is_llm_enabled():
            log_llm_usage(cli_ctx, "OKW listing")
        
        async def http_list():
            """List via HTTP API"""
            cli_ctx.log("Listing via HTTP API...", "info")
            params = {
                "limit": limit, 
                "offset": offset,
                "facility_type": facility_type,
                "status": status,
                "location": location
            }
            # Remove None values
            params = {k: v for k, v in params.items() if v is not None}
            response = await cli_ctx.api_client.request("GET", "/api/okw/", params=params)
            return response
        
        async def fallback_list():
            """List using direct service calls"""
            cli_ctx.log("Using direct service listing...", "info")
            okw_service = await OKWService.get_instance()
            facilities = await okw_service.list_facilities(
                limit=limit, 
                offset=offset,
                facility_type=facility_type,
                status=status,
                location=location
            )
            return {
                "facilities": [facility.to_dict() for facility in facilities],
                "total": len(facilities)
            }
        
        # Execute listing with fallback
        command = SmartCommand(cli_ctx)
        result = await command.execute_with_fallback(http_list, fallback_list)
        
        # Display listing results
        facilities = result.get("facilities", [])
        total = result.get("total", len(facilities))
        
        if facilities:
            click.echo(f"✅ Found {total} OKW facilities")
            
            if output_format == "json":
                output_data = format_llm_output(result, cli_ctx)
                click.echo(output_data)
            else:
                for facility in facilities:
                    click.echo(f"🏭 {facility.get('id', 'Unknown')}")
                    click.echo(f"   Name: {facility.get('name', 'Unknown')}")
                    click.echo(f"   Type: {facility.get('facility_type', 'Unknown')}")
                    click.echo(f"   Status: {facility.get('status', 'Unknown')}")
                    click.echo(f"   Location: {facility.get('location', {}).get('address', 'Unknown')}")
                    click.echo("")  # Empty line for spacing
        else:
            click.echo("No OKW facilities found")
        
        cli_ctx.end_command_tracking()
        
    except Exception as e:
        cli_ctx.log(f"Listing failed: {str(e)}", "error")
        raise


@okw_group.command()
@click.argument('facility_id', type=str)
@click.option('--force', is_flag=True, help='Force deletion without confirmation')
@standard_cli_command(
    help_text="""
    Delete an OKW facility from the system.
    
    This command removes a previously stored OKW facility from the system.
    Use with caution as this action cannot be undone.
    
    When LLM is enabled, deletion includes:
    - Enhanced impact analysis before deletion
    - Dependency checking and warnings
    - Backup suggestions and safety checks
    - Advanced metadata cleanup
    """,
    epilog="""
    Examples:
      # Delete a facility (with confirmation)
      ome okw delete 123e4567-e89b-12d3-a456-426614174000
      
      # Force deletion without confirmation
      ome okw delete 123e4567-e89b-12d3-a456-426614174000 --force
      
      # Use LLM for enhanced analysis
      ome okw delete 123e4567-e89b-12d3-a456-426614174000 --use-llm
    """,
    async_cmd=True,
    track_performance=True,
    handle_errors=True,
    format_output=True,
    add_llm_config=True
)
@click.pass_context
async def delete(ctx, facility_id: str, force: bool,
                verbose: bool, output_format: str, use_llm: bool,
                llm_provider: str, llm_model: Optional[str],
                quality_level: str, strict_mode: bool):
    """Delete an OKW facility with enhanced LLM support."""
    cli_ctx = ctx.obj
    cli_ctx.start_command_tracking("okw-delete")
    
    # Update CLI context with parameters from decorator
    cli_ctx.update_llm_config(
        use_llm=use_llm,
        llm_provider=llm_provider,
        llm_model=llm_model,
        quality_level=quality_level,
        strict_mode=strict_mode
    )
    
    try:
        if not force:
            if not click.confirm(f"Are you sure you want to delete facility {facility_id}?"):
                cli_ctx.log("Deletion cancelled", "info")
                return
        
        # Log LLM usage if enabled
        if cli_ctx.is_llm_enabled():
            log_llm_usage(cli_ctx, "OKW deletion")
        
        async def http_delete():
            """Delete via HTTP API"""
            cli_ctx.log("Deleting via HTTP API...", "info")
            response = await cli_ctx.api_client.request("DELETE", f"/api/okw/{facility_id}")
            return response
        
        async def fallback_delete():
            """Delete using direct service calls"""
            cli_ctx.log("Using direct service deletion...", "info")
            okw_service = await OKWService.get_instance()
            success = await okw_service.delete(UUID(facility_id))
            return {"success": success}
        
        # Execute deletion with fallback
        command = SmartCommand(cli_ctx)
        result = await command.execute_with_fallback(http_delete, fallback_delete)
        
        # Display deletion results
        if result.get("success", True):  # HTTP API returns success by default
            cli_ctx.log(f"OKW facility {facility_id} deleted successfully", "success")
        else:
            cli_ctx.log(f"Failed to delete OKW facility {facility_id}", "error")
        
        cli_ctx.end_command_tracking()
        
    except Exception as e:
        cli_ctx.log(f"Deletion failed: {str(e)}", "error")
        raise


@okw_group.command(name="extract")
@click.argument('facility_file', type=click.Path(exists=True))
@standard_cli_command(
    help_text="""
    Extract capabilities from an OKW facility.
    
    This command analyzes an OKW facility and extracts all manufacturing
    capabilities, equipment, and processes for use in matching
    and supply chain analysis.
    
    When LLM is enabled, extraction includes:
    - Enhanced capability analysis and categorization
    - Semantic understanding of manufacturing processes
    - Quality assessment of extracted capabilities
    - Suggestions for capability improvement
    """,
    epilog="""
    Examples:
      # Extract capabilities from facility
      ome okw extract my-facility.okw.json
      
      # Use LLM for enhanced extraction
      ome okw extract my-facility.okw.json --use-llm --quality-level professional
    """,
    async_cmd=True,
    track_performance=True,
    handle_errors=True,
    format_output=True,
    add_llm_config=True
)
@click.pass_context
async def extract_capabilities(ctx, facility_file: str,
                              verbose: bool, output_format: str, use_llm: bool,
                              llm_provider: str, llm_model: Optional[str],
                              quality_level: str, strict_mode: bool):
    """Extract capabilities from an OKW facility with enhanced LLM support."""
    cli_ctx = ctx.obj
    cli_ctx.start_command_tracking("okw-extract-capabilities")
    
    # Update CLI context with parameters from decorator
    cli_ctx.update_llm_config(
        use_llm=use_llm,
        llm_provider=llm_provider,
        llm_model=llm_model,
        quality_level=quality_level,
        strict_mode=strict_mode
    )
    
    try:
        # Read facility file
        cli_ctx.log("Reading facility file...", "info")
        facility_data = await _read_facility_file(facility_file)
    
        # Create request data with LLM configuration
        request_data = create_llm_request_data(cli_ctx, {
            "content": facility_data
        })
        
        # Log LLM usage if enabled
        if cli_ctx.is_llm_enabled():
            log_llm_usage(cli_ctx, "OKW capability extraction")
        
        async def http_extract():
            """Extract via HTTP API"""
            cli_ctx.log("Extracting via HTTP API...", "info")
            response = await cli_ctx.api_client.request("POST", "/api/okw/extract", json_data=request_data)
            
            # Handle API response structure - may be wrapped in 'data' or direct
            if isinstance(response, dict):
                # Check if response is wrapped in 'data' field
                if "data" in response and isinstance(response["data"], dict):
                    # Response wrapped in standard API format
                    return response["data"]
                elif "capabilities" in response:
                    # Direct response with capabilities
                    return response
                else:
                    # Try to extract from nested structure
                    return response
            return response
        
        async def fallback_extract():
            """Extract using direct service calls"""
            cli_ctx.log("Using direct service extraction...", "info")
            facility = ManufacturingFacility.from_dict(facility_data)
            okw_service = await OKWService.get_instance()
            capabilities = await okw_service.extract_capabilities(facility)
            return {"capabilities": capabilities}
        
        # Execute extraction with fallback
        command = SmartCommand(cli_ctx)
        result = await command.execute_with_fallback(http_extract, fallback_extract)
        
        # Display extraction results
        # Handle both direct capabilities and wrapped response
        capabilities = result.get("capabilities", [])
        
        # If capabilities is not a list, try to extract from nested structure
        if not isinstance(capabilities, list):
            if isinstance(result, dict) and "data" in result:
                capabilities = result["data"].get("capabilities", [])
            else:
                capabilities = []
        
        if capabilities:
            cli_ctx.log(f"Extracted {len(capabilities)} capabilities", "success")
            
            if output_format == "json":
                output_data = format_llm_output(result, cli_ctx)
                click.echo(output_data)
            else:
                # Display capabilities in a readable format
                click.echo(f"\n✅ Extracted {len(capabilities)} capabilities:\n")
                for i, cap in enumerate(capabilities, 1):
                    cap_type = cap.get('type', 'Unknown') if isinstance(cap, dict) else str(cap)
                    cap_params = cap.get('parameters', {}) if isinstance(cap, dict) else {}
                    cap_limitations = cap.get('limitations', {}) if isinstance(cap, dict) else {}
                    
                    click.echo(f"  {i}. {cap_type}")
                    if cap_params:
                        click.echo(f"     Parameters: {cap_params}")
                    if cap_limitations:
                        click.echo(f"     Limitations: {cap_limitations}")
                    click.echo()
        else:
            cli_ctx.log("No capabilities found in facility", "info")
        
        cli_ctx.end_command_tracking()
        
    except Exception as e:
        cli_ctx.log(f"Extraction failed: {str(e)}", "error")
        raise


@okw_group.command()
@click.argument('file_path', type=click.Path(exists=True))
@standard_cli_command(
    help_text="""
    Upload and validate an OKW facility file.
    
    This command uploads an OKW facility file to the system and performs
 validation to ensure it meets the OKW specification.
    
    When LLM is enabled, upload includes:
    - Enhanced validation with semantic analysis
    - Automatic field completion and suggestions
    - Quality assessment and recommendations
    - Advanced compliance checking
    """,
    epilog="""
    Examples:
      # Upload and validate a facility
      ome okw upload my-facility.okw.json
      
      # Upload with premium quality validation
      ome okw upload my-facility.okw.json --quality-level premium --strict-mode
      
      # Use LLM for enhanced processing
      ome okw upload my-facility.okw.json --use-llm --quality-level standard
    """,
    async_cmd=True,
    track_performance=True,
    handle_errors=True,
    format_output=True,
    add_llm_config=True
)
@click.pass_context
async def upload(ctx, file_path: str, verbose: bool, output_format: str, use_llm: bool,
                llm_provider: str, llm_model: Optional[str],
                quality_level: str, strict_mode: bool):
    """Upload and validate an OKW facility file with enhanced LLM support."""
    cli_ctx = ctx.obj
    cli_ctx.start_command_tracking("okw-upload")
    
    # Update CLI context with parameters from decorator
    cli_ctx.update_llm_config(
        use_llm=use_llm,
        llm_provider=llm_provider,
        llm_model=llm_model,
        quality_level=quality_level,
        strict_mode=strict_mode
    )
    
    try:
        # Log LLM usage if enabled
        if cli_ctx.is_llm_enabled():
            log_llm_usage(cli_ctx, "OKW upload")
        
        async def http_upload():
            """Upload facility via HTTP API"""
            cli_ctx.log("Uploading via HTTP API...", "info")
            
            # Prepare form data for file upload
            form_data = {
                "validation_context": quality_level,
                "description": f"Uploaded OKW facility with {quality_level} validation"
            }
            
            response = await cli_ctx.api_client.upload_file(
                "POST", 
                "/api/okw/upload", 
                file_path,
                file_field_name="okw_file",
                form_data=form_data
            )
            return response
        
        async def fallback_upload():
            """Fallback upload using direct services"""
            cli_ctx.log("Using direct service upload...", "info")
            with open(file_path, 'r') as f:
                content = f.read()
            
            # Parse JSON content to dict, then create facility
            import json
            facility_data = json.loads(content)
            okw_service = await OKWService.get_instance()
            result = await okw_service.create(facility_data)
            return result.to_dict()
        
        # Execute upload with fallback
        command = SmartCommand(cli_ctx)
        result = await command.execute_with_fallback(http_upload, fallback_upload)
        
        # Display upload results
        # Handle both OKWUploadResponse format (has "okw" field) and direct OKWResponse format
        if isinstance(result, dict):
            facility_id = result.get("id") or (result.get("okw", {}) or {}).get("id") or (result.get("facility", {}) or {}).get("id")
        else:
            facility_id = getattr(result, "id", None) or getattr(getattr(result, "okw", None), "id", None)
        
        if facility_id:
            cli_ctx.log(f"✅ OKW facility uploaded with ID: {facility_id}", "success")
        else:
            cli_ctx.log(f"⚠️  Upload completed but no facility ID found in response", "warning")
            if cli_ctx.verbose:
                cli_ctx.log(f"Response structure: {type(result).__name__}", "info")
                cli_ctx.log(f"Response keys/attrs: {list(result.keys()) if isinstance(result, dict) else dir(result)[:10]}", "info")
        
        cli_ctx.end_command_tracking()
        
    except Exception as e:
        cli_ctx.log(f"Upload failed: {str(e)}", "error")
        raise


@okw_group.command()
@click.option('--output', '-o', type=click.Path(), help='Output file path for the JSON schema')
@standard_cli_command(
    help_text="""
    Export the JSON schema for the OKW (OpenKnowWhere) domain model.
    
    This command generates and exports the JSON schema for the ManufacturingFacility
    dataclass in canonical JSON Schema format (draft-07). The schema represents
    the complete structure of the OKW domain model including all fields, types,
    and constraints.
    
    The exported schema can be used for:
    - Validation of OKW facilities
    - Documentation generation
    - API contract specification
    - Integration with other systems
    """,
    epilog="""
    Examples:
      # Export schema to console
      ome okw export
      
      # Export schema to file
      ome okw export --output okw-schema.json
      
      # Export with JSON output format
      ome okw export --output okw-schema.json --json
    """,
    async_cmd=True,
    track_performance=True,
    handle_errors=True,
    format_output=True,
    add_llm_config=False  # Export doesn't need LLM
)
@click.pass_context
async def export(ctx, output: Optional[str], verbose: bool, output_format: str,
                 use_llm: bool = False, llm_provider: str = 'anthropic',
                 llm_model: Optional[str] = None, quality_level: str = 'professional',
                 strict_mode: bool = False):
    """Export OKW domain model as JSON schema."""
    cli_ctx = ctx.obj
    cli_ctx.start_command_tracking("okw-export")
    
    try:
        cli_ctx.log("Exporting OKW JSON schema...", "info")
        
        async def http_export():
            """Export via HTTP API"""
            cli_ctx.log("Exporting via HTTP API...", "info")
            response = await cli_ctx.api_client.request("GET", "/api/okw/export")
            return response
        
        async def fallback_export():
            """Export using direct schema generation"""
            cli_ctx.log("Using direct schema generation...", "info")
            from ..core.models.okw import ManufacturingFacility
            from ..core.utils.schema_generator import generate_json_schema
            
            schema = generate_json_schema(ManufacturingFacility, title="ManufacturingFacility")
            return {
                "success": True,
                "message": "OKW schema exported successfully",
                "schema": schema,
                "schema_version": schema.get("$schema", "http://json-schema.org/draft-07/schema#"),
                "model_name": "ManufacturingFacility"
            }
        
        # Execute export with fallback
        command = SmartCommand(cli_ctx)
        result = await command.execute_with_fallback(http_export, fallback_export)
        
        # Extract schema from result
        schema = result.get("schema", result)
        
        # Save to file if output specified
        if output:
            output_path = Path(output)
            with open(output_path, 'w') as f:
                json.dump(schema, f, indent=2)
            cli_ctx.log(f"✅ Schema exported to: {output_path}", "success")
        else:
            # Display schema
            if output_format == "json":
                output_data = format_llm_output(result, cli_ctx)
                click.echo(output_data)
            else:
                cli_ctx.log("✅ OKW JSON Schema exported successfully", "success")
                cli_ctx.log(f"   Schema Version: {result.get('schema_version', 'N/A')}", "info")
                cli_ctx.log(f"   Model Name: {result.get('model_name', 'ManufacturingFacility')}", "info")
                cli_ctx.log(f"   Use --output to save to file", "info")
        
        cli_ctx.end_command_tracking()
        
    except Exception as e:
        cli_ctx.log(f"❌ Export failed: {str(e)}", "error")
        if cli_ctx.verbose:
            import traceback
            click.echo(traceback.format_exc())
        raise


@okw_group.command()
@click.option('--query', '-q', help='Search query')
@click.option('--domain', help='Filter by domain')
@click.option('--capability', help='Filter by capability type')
@click.option('--location', help='Filter by location')
@click.option('--limit', default=10, type=int, help='Maximum number of results')
@standard_cli_command(
    help_text="""
    Search OKW facilities by various criteria.
    
    This command searches through stored OKW facilities using text queries,
    domain filters, capability types, and location filters to find
    facilities that match your requirements.
    
    When LLM is enabled, search includes:
    - Enhanced semantic search capabilities
    - Intelligent query understanding and expansion
    - Quality assessment of search results
    - Advanced filtering and ranking suggestions
    """,
    epilog="""
    Examples:
      # Search by capability
      ome okw search --capability "PCB Assembly"
      
      # Search with multiple filters
      ome okw search --query "electronics" --location "San Francisco" --limit 20
      
      # Use LLM for enhanced search
      ome okw search --query "precision manufacturing" --use-llm
    """,
    async_cmd=True,
    track_performance=True,
    handle_errors=True,
    format_output=True,
    add_llm_config=True
)
@click.pass_context
async def search(ctx, query: str, domain: str, capability: str, location: str, limit: int,
                verbose: bool, output_format: str, use_llm: bool,
                llm_provider: str, llm_model: Optional[str],
                quality_level: str, strict_mode: bool):
    """Search OKW facilities with enhanced LLM support."""
    cli_ctx = ctx.obj
    cli_ctx.start_command_tracking("okw-search")
    
    # Update CLI context with parameters from decorator
    cli_ctx.update_llm_config(
        use_llm=use_llm,
        llm_provider=llm_provider,
        llm_model=llm_model,
        quality_level=quality_level,
        strict_mode=strict_mode
    )
    
    try:
        # Log LLM usage if enabled
        if cli_ctx.is_llm_enabled():
            log_llm_usage(cli_ctx, "OKW search")
        
        async def http_search():
            """Search facilities via HTTP API"""
            cli_ctx.log("Searching via HTTP API...", "info")
            params = {
                "query": query,
                "domain": domain,
                "capability": capability,
                "location": location,
                "limit": limit
            }
            # Remove None values
            params = {k: v for k, v in params.items() if v is not None}
            
            response = await cli_ctx.api_client.request("GET", "/api/okw/search", params=params)
            return response
        
        async def fallback_search():
            """Fallback search using direct services"""
            cli_ctx.log("Using direct service search...", "info")
            okw_service = await OKWService.get_instance()
            facilities = await okw_service.list_facilities()
            
            # Simple filtering (in a real implementation, this would be more sophisticated)
            filtered_facilities = []
            for facility in facilities:
                if query and query.lower() not in facility.name.lower():
                    continue
                if domain and domain.lower() not in facility.domain.lower():
                    continue
                if location and location.lower() not in facility.location.lower():
                    continue
                
                filtered_facilities.append(facility)
            
            return {
                "facilities": [facility.to_dict() for facility in filtered_facilities[:limit]],
                "total": len(filtered_facilities)
            }
        
        # Execute search with fallback
        command = SmartCommand(cli_ctx)
        result = await command.execute_with_fallback(http_search, fallback_search)
        
        # Display search results
        facilities = result.get("facilities", [])
        total = result.get("total", len(facilities))
        
        if facilities:
            cli_ctx.log(f"Found {total} facilities", "success")
            
            if output_format == "json":
                output_data = format_llm_output(result, cli_ctx)
                click.echo(output_data)
            else:
                for i, facility in enumerate(facilities, 1):
                    cli_ctx.log(f"{i}. {facility.get('name', 'Unknown')} - {facility.get('location', 'Unknown location')}", "info")
        else:
            cli_ctx.log("No facilities found matching criteria", "info")
        
        cli_ctx.end_command_tracking()
        
    except Exception as e:
        cli_ctx.log(f"Search failed: {str(e)}", "error")
        raise


@okw_group.command()
@click.argument('facility_file', type=click.Path(exists=True))
@click.option('--output', '-o', type=click.Path(), help='Output file path (default: overwrites input file)')
@click.option('--dry-run', is_flag=True, help='Preview fixes without applying them')
@click.option('--backup', is_flag=True, help='Create backup of original file before fixing')
@click.option('--confidence-threshold', type=float, default=0.7, help='Minimum confidence to apply a fix (0.0-1.0, default: 0.7)')
@click.option('--domain', 
              type=click.Choice(['manufacturing', 'cooking']),
              help='Domain override (auto-detected from file if not provided)')
@click.option('--yes', '-y', is_flag=True, help='Automatically confirm all fixes without prompting')
@standard_cli_command(
    help_text="""
    Automatically fix validation warnings and errors in an OKW facility.
    
    This command analyzes validation warnings and errors and applies automatic
    fixes based on confidence levels. Fixes include:
    - Typo corrections (e.g., 'descroption' → 'description')
    - Case error fixes (e.g., 'Link' → 'link')
    - Data movement from metadata to proper fields
    - Field removal for empty or duplicate data
    
    Fixes are categorized by confidence:
    - High confidence (1.0): Typos and case errors (always applied)
    - Medium confidence (0.7-0.9): Data movement and transformations
    - Low confidence (0.5): Field removal (requires confirmation)
    
    Use --dry-run to preview fixes before applying them.
    """,
    epilog="""
    Examples:
      # Preview fixes without applying
      ome okw fix facility.json --dry-run
      
      # Apply fixes with backup
      ome okw fix facility.json --backup
      
      # Apply fixes to new file
      ome okw fix facility.json --output facility-fixed.json
      
      # Apply all fixes including low-confidence ones
      ome okw fix facility.json --confidence-threshold 0.5 --yes
      
      # Fix with domain override
      ome okw fix facility.json --domain cooking
    """,
    async_cmd=True,
    track_performance=True,
    handle_errors=True,
    format_output=True,
    add_llm_config=False  # Auto-fix doesn't use LLM
)
@click.pass_context
async def fix(ctx, facility_file: str, output: Optional[str], dry_run: bool, backup: bool,
              confidence_threshold: float, domain: Optional[str], yes: bool,
              verbose: bool, output_format: str, quality_level: str, strict_mode: bool,
              use_llm: bool = False, llm_provider: str = 'anthropic', llm_model: Optional[str] = None):
    """Automatically fix validation issues in an OKW facility."""
    cli_ctx = ctx.obj
    cli_ctx.start_command_tracking("okw-fix")
    cli_ctx.verbose = verbose
    cli_ctx.config.verbose = verbose
    
    try:
        # Read facility file
        facility_data = await _read_facility_file(facility_file)
        
        # Detect domain if not provided
        detected_domain = domain
        if not detected_domain:
            if "domain" in facility_data and facility_data["domain"]:
                detected_domain = facility_data["domain"]
            else:
                detected_domain = "manufacturing"  # Default for OKW
        
        cli_ctx.log(f"Using domain: {detected_domain}", "info")
        
        # Validate first to get warnings/errors
        cli_ctx.log("Validating facility...", "info")
        validation_result = validate_okw_facility(
            facility_data,
            quality_level=quality_level,
            strict_mode=strict_mode
        )
        
        if not validation_result.warnings and not validation_result.errors:
            cli_ctx.log("✅ No issues found. Facility is already valid!", "success")
            cli_ctx.end_command_tracking()
            return
        
        cli_ctx.log(f"Found {len(validation_result.warnings)} warnings and {len(validation_result.errors)} errors", "info")
        
        # Run auto-fix
        cli_ctx.log("Analyzing fixes...", "info")
        fixed_content, fix_report = auto_fix_okw_facility(
            facility_data,
            validation_result,
            quality_level=quality_level,
            strict_mode=strict_mode,
            domain=detected_domain,
            dry_run=dry_run,
            fix_confidence_threshold=confidence_threshold
        )
        
        # Display fix report
        cli_ctx.log("\n" + "=" * 70, "info")
        cli_ctx.log("AUTO-FIX REPORT", "info")
        cli_ctx.log("=" * 70, "info")
        cli_ctx.log(f"Fixes applied: {len(fix_report.fixes_applied)}", "info")
        cli_ctx.log(f"Fixes skipped: {len(fix_report.fixes_skipped)}", "info")
        cli_ctx.log(f"Original warnings: {fix_report.original_warnings}", "info")
        cli_ctx.log(f"Original errors: {fix_report.original_errors}", "info")
        cli_ctx.log(f"Remaining warnings: {fix_report.remaining_warnings}", "info")
        cli_ctx.log(f"Remaining errors: {fix_report.remaining_errors}", "info")
        cli_ctx.log(f"Warnings fixed: {fix_report.warnings_fixed}", "success" if fix_report.warnings_fixed > 0 else "info")
        cli_ctx.log(f"Errors fixed: {fix_report.errors_fixed}", "success" if fix_report.errors_fixed > 0 else "info")
        
        if fix_report.fixes_applied:
            cli_ctx.log("\nApplied fixes:", "info")
            for i, fix in enumerate(fix_report.fixes_applied, 1):
                cli_ctx.log(f"  {i}. [{fix.type}] {fix.description}", "success")
        
        if fix_report.fixes_skipped:
            cli_ctx.log("\nSkipped fixes (low confidence or require confirmation):", "warning")
            for i, fix in enumerate(fix_report.fixes_skipped, 1):
                cli_ctx.log(f"  {i}. [{fix.type}] {fix.description} (confidence: {fix.confidence})", "warning")
            
            # Ask for confirmation on low-confidence fixes
            if not dry_run and not yes and fix_report.fixes_skipped:
                low_confidence_fixes = [f for f in fix_report.fixes_skipped if f.confidence < confidence_threshold]
                if low_confidence_fixes:
                    cli_ctx.log(f"\n⚠️  {len(low_confidence_fixes)} fixes require confirmation (confidence < {confidence_threshold})", "warning")
                    if click.confirm("Apply low-confidence fixes?"):
                        # Apply the confirmed fixes directly to the already-fixed content
                        # Parse the facility again to apply fixes
                        facility = ManufacturingFacility.from_dict(fixed_content)
                        
                        # Apply each confirmed fix
                        applied_count = 0
                        for fix in low_confidence_fixes:
                            try:
                                from ..core.validation.auto_fix import _apply_fix_to_facility
                                _apply_fix_to_facility(facility, fix)
                                fix_report.fixes_applied.append(fix)
                                fix_report.fixes_skipped.remove(fix)
                                applied_count += 1
                                cli_ctx.log(f"Applied fix: {fix.description}", "success")
                            except Exception as e:
                                cli_ctx.log(f"Failed to apply fix {fix.description}: {str(e)}", "warning")
                        
                        # Convert back to dict
                        fixed_content = facility.to_dict()
                        
                        # Re-validate to get updated counts
                        temp_validation = validate_okw_facility(
                            fixed_content,
                            quality_level=quality_level,
                            strict_mode=strict_mode
                        )
                        fix_report.remaining_warnings = len(temp_validation.warnings)
                        fix_report.remaining_errors = len(temp_validation.errors)
                        
                        if applied_count > 0:
                            cli_ctx.log(f"✅ Applied {applied_count} additional fixes", "success")
                        else:
                            cli_ctx.log("⚠️  No fixes were applied", "warning")
        
        if dry_run:
            cli_ctx.log("\n🔍 DRY-RUN MODE: No changes were made", "info")
            cli_ctx.log("Run without --dry-run to apply fixes", "info")
        else:
            # Determine output file
            output_file = output or facility_file
            
            # Create backup if requested
            if backup and output_file == facility_file:
                backup_file = f"{facility_file}.backup"
                import shutil
                shutil.copy2(facility_file, backup_file)
                cli_ctx.log(f"Created backup: {backup_file}", "info")
            
            # Write fixed content
            output_path = Path(output_file)
            with open(output_path, 'w') as f:
                json.dump(fixed_content, f, indent=2, ensure_ascii=False)
            
            # Re-validate to show final state
            final_validation = validate_okw_facility(
                fixed_content,
                quality_level=quality_level,
                strict_mode=strict_mode
            )
            
            # Update fix report with final validation results
            fix_report.remaining_warnings = len(final_validation.warnings)
            fix_report.remaining_errors = len(final_validation.errors)
            
            # Display status based on fix report status
            status = fix_report.status
            if status == "complete_success":
                cli_ctx.log(f"\n✅ Complete success! All issues resolved.", "success")
                cli_ctx.log(f"✅ Fixed facility saved to: {output_file}", "success")
            elif status == "partial_success":
                cli_ctx.log(f"\n⚠️  Partial success: Some issues fixed, but {fix_report.remaining_warnings} warnings and {fix_report.remaining_errors} errors remain", "warning")
                cli_ctx.log(f"✅ Updated facility saved to: {output_file}", "success")
            else:  # failure
                cli_ctx.log(f"\n❌ Fix failed: No fixes were applied or errors remain", "error")
                if fix_report.remaining_errors > 0:
                    cli_ctx.log(f"❌ {fix_report.remaining_errors} error(s) remain", "error")
                if fix_report.remaining_warnings > 0:
                    cli_ctx.log(f"⚠️  {fix_report.remaining_warnings} warning(s) remain", "warning")
                cli_ctx.log(f"⚠️  Facility saved to: {output_file} (unchanged or partially fixed)", "warning")
            
            # Show detailed verbose output if requested
            if verbose and (final_validation.warnings or final_validation.errors):
                cli_ctx.log("\n" + "=" * 70, "info")
                cli_ctx.log("REMAINING ISSUES (sorted by severity)", "info")
                cli_ctx.log("=" * 70, "info")
                
                # Display errors first
                if final_validation.errors:
                    cli_ctx.log("\n❌ ERRORS:", "error")
                    for i, error in enumerate(final_validation.errors, 1):
                        # Error can be a string or an object with message/code/field attributes
                        if isinstance(error, str):
                            cli_ctx.log(f"  {i}. {error}", "error")
                        else:
                            error_msg = getattr(error, 'message', str(error))
                            error_code = getattr(error, 'code', "UNKNOWN")
                            cli_ctx.log(f"  {i}. [{error_code}] {error_msg}", "error")
                            if hasattr(error, 'field') and error.field:
                                cli_ctx.log(f"     Field: {error.field}", "error")
                            if hasattr(error, 'suggestion') and error.suggestion:
                                cli_ctx.log(f"     Suggestion: {error.suggestion}", "info")
                
                # Display warnings
                if final_validation.warnings:
                    cli_ctx.log("\n⚠️  WARNINGS:", "warning")
                    for i, warning in enumerate(final_validation.warnings, 1):
                        # Warning can be a string or an object with message/code/field attributes
                        if isinstance(warning, str):
                            cli_ctx.log(f"  {i}. {warning}", "warning")
                        else:
                            warning_msg = getattr(warning, 'message', str(warning))
                            warning_code = getattr(warning, 'code', "UNKNOWN")
                            cli_ctx.log(f"  {i}. [{warning_code}] {warning_msg}", "warning")
                            if hasattr(warning, 'field') and warning.field:
                                cli_ctx.log(f"     Field: {warning.field}", "warning")
                            if hasattr(warning, 'suggestion') and warning.suggestion:
                                cli_ctx.log(f"     Suggestion: {warning.suggestion}", "info")
        
        cli_ctx.end_command_tracking()
        
    except Exception as e:
        cli_ctx.log(f"Fix failed: {str(e)}", "error")
        raise


@okw_group.command(name="list-files")
@click.option('--prefix', default='okw/', help='Filter by prefix (default: okw/)')
@click.option('--output', '-o', type=click.Path(), help='Save list to file (JSON)')
@click.option('--format', type=click.Choice(['json', 'text']), default='text', help='Output format')
@standard_cli_command(
    help_text="""
    List OKW files in Azure blob storage.
    
    This command lists raw OKW file keys from blob storage, allowing you to
    see what files are available for download and processing.
    
    The output includes:
    - Blob keys (file paths in storage)
    - File sizes
    - Last modified dates
    - File metadata
    """,
    epilog="""
    Examples:
      # List all OKW files
      ome okw list-files
      
      # List with specific prefix
      ome okw list-files --prefix okw/facilities/
      
      # Save list to JSON file
      ome okw list-files --output files.json --format json
    """,
    async_cmd=True,
    track_performance=True,
    handle_errors=True,
    format_output=True,
    add_llm_config=False
)
@click.pass_context
async def list_files(ctx, prefix: str, output: Optional[str], format: str,
                     verbose: bool, output_format: str, quality_level: str, strict_mode: bool,
                     use_llm: bool = False, llm_provider: str = 'anthropic', llm_model: Optional[str] = None):
    """List OKW files in blob storage."""
    cli_ctx = ctx.obj
    cli_ctx.start_command_tracking("okw-list-files")
    cli_ctx.verbose = verbose
    cli_ctx.config.verbose = verbose
    
    storage_service = None
    try:
        # Get storage service
        from ..config import settings
        storage_service = await StorageService.get_instance()
        if not storage_service.manager:
            await storage_service.configure(settings.STORAGE_CONFIG)
        
        if not storage_service.manager:
            cli_ctx.log("❌ Storage service not configured", "error")
            raise click.ClickException("Storage service is not configured. Please configure storage first.")
        
        if cli_ctx.verbose:
            cli_ctx.log(f"Listing files with prefix: {prefix}", "info")
        
        # List objects from storage
        files = []
        async for obj in storage_service.manager.list_objects(prefix=prefix):
            # Filter for OKW file extensions
            key = obj.get("key", "")
            if key.endswith(('.json', '.yaml', '.yml')):
                # Extract facility_id by reading and parsing the file
                facility_id = None
                try:
                    file_data = await storage_service.manager.get_object(key)
                    content = file_data.decode('utf-8')
                    
                    # Parse based on file extension
                    if key.endswith('.json'):
                        import json
                        facility_data = json.loads(content)
                    else:  # yaml or yml
                        import yaml
                        facility_data = yaml.safe_load(content)
                    
                    # Extract ID from the parsed data
                    if facility_data and 'id' in facility_data:
                        facility_id = str(facility_data['id'])
                except Exception as e:
                    # If we can't parse the file, continue without facility_id
                    if cli_ctx.verbose:
                        cli_ctx.log(f"Warning: Could not extract facility_id from {key}: {str(e)}", "warning")
                
                files.append({
                    "key": key,
                    "facility_id": facility_id,
                    "size": obj.get("size", 0),
                    "last_modified": obj.get("last_modified"),
                    "etag": obj.get("etag")
                })
        
        # Prepare output
        result = {
            "files": files,
            "total": len(files),
            "prefix": prefix
        }
        
        # Save to file if requested
        if output:
            with open(output, 'w') as f:
                json.dump(result, f, indent=2, default=str)
            if cli_ctx.verbose:
                cli_ctx.log(f"List saved to: {output}", "info")
        
        # Display results
        if output_format == "json" or format == "json":
            click.echo(json.dumps(result, indent=2, default=str))
        else:
            # Display file list in text format
            if files:
                click.echo(f"\n📁 Found {len(files)} OKW file(s):\n")
                for i, file_info in enumerate(files, 1):
                    size_kb = file_info["size"] / 1024 if file_info["size"] else 0
                    modified = file_info.get("last_modified", "Unknown")
                    if isinstance(modified, str):
                        modified_str = modified
                    else:
                        modified_str = str(modified) if modified else "Unknown"
                    facility_id = file_info.get("facility_id", "Unknown")
                    click.echo(f"  {i}. {file_info['key']}")
                    click.echo(f"     Facility ID: {facility_id}")
                    click.echo(f"     Size: {size_kb:.1f} KB | Modified: {modified_str}")
                click.echo(f"\nTotal: {len(files)} file(s)")
            else:
                click.echo("No OKW files found")
        
        cli_ctx.end_command_tracking()
        
    except Exception as e:
        cli_ctx.log(f"List files failed: {str(e)}", "error")
        raise
    finally:
        # Ensure storage service is cleaned up to close aiohttp sessions
        # This is critical for Azure blob storage which uses aiohttp
        if storage_service:
            try:
                # Register with service_fallback so CLIContext.cleanup() can also clean it up
                if not hasattr(cli_ctx.service_fallback, '_services'):
                    cli_ctx.service_fallback._services = {}
                cli_ctx.service_fallback._services['storage_service'] = storage_service
                
                # Explicitly cleanup to close aiohttp sessions
                await storage_service.cleanup()
            except Exception as cleanup_error:
                if cli_ctx.verbose:
                    cli_ctx.log(f"Warning: Error during storage cleanup: {cleanup_error}", "warning")