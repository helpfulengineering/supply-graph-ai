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
    facility = result.get("facility", result)
    
    if facility:
        cli_ctx.log(f"Retrieved OKW facility: {facility.get('name', 'Unknown')}", "success")
        
        if output:
            # Save facility to output file
            with open(output, 'w') as f:
                json.dump(facility, f, indent=2, default=str)
            cli_ctx.log(f"Facility saved to {output}", "info")
        
        if output_format == "json":
            output_data = format_llm_output(result, cli_ctx)
            click.echo(output_data)
        else:
            # Show basic facility info
            cli_ctx.log(f"Name: {facility.get('name', 'Unknown')}", "info")
            cli_ctx.log(f"Type: {facility.get('facility_type', 'Unknown')}", "info")
            cli_ctx.log(f"Location: {facility.get('location', {}).get('address', 'Unknown')}", "info")
            cli_ctx.log(f"Status: {facility.get('status', 'Unknown')}", "info")
    else:
        cli_ctx.log("Facility not found", "error")


# Commands

@okw_group.command()
@click.argument('facility_file', type=click.Path(exists=True))
@standard_cli_command(
    help_text="""
    Validate an OKW facility for compliance and completeness.
    
    This command performs comprehensive validation of an OKW facility,
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


@okw_group.command()
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
      ome okw extract-capabilities my-facility.okw.json
      
      # Use LLM for enhanced extraction
      ome okw extract-capabilities my-facility.okw.json --use-llm --quality-level professional
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
        capabilities = result.get("capabilities", [])
        
        if capabilities:
            cli_ctx.log(f"Extracted {len(capabilities)} capabilities", "success")
            
            if output_format == "json":
                output_data = format_llm_output(result, cli_ctx)
                click.echo(output_data)
            else:
                for i, cap in enumerate(capabilities, 1):
                    cli_ctx.log(f"{i}. {cap.get('type', 'Unknown')}: {cap.get('description', 'No description')}", "info")
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
    comprehensive validation to ensure it meets the OKW specification.
    
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
        facility_id = result.get("id") or result.get("facility", {}).get("id")
        
        if facility_id:
            cli_ctx.log(f"OKW facility uploaded with ID: {facility_id}", "success")
        else:
            cli_ctx.log("Failed to upload OKW facility", "error")
        
        cli_ctx.end_command_tracking()
        
    except Exception as e:
        cli_ctx.log(f"Upload failed: {str(e)}", "error")
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