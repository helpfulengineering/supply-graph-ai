"""
OKH (OpenKnowHow) commands for OME CLI

This module provides commands for managing OKH manifests including
creation, validation, extraction, and storage operations.
"""

import click
import json
from pathlib import Path
from typing import Optional
from uuid import UUID

from ..core.generation.platforms.github import GitHubExtractor
from ..core.generation.platforms.gitlab import GitLabExtractor
from ..core.generation.models import LayerConfig
from ..core.generation.built_directory import BuiltDirectoryExporter
from ..core.services.okh_service import OKHService
from ..core.models.okh import OKHManifest
from .base import (
    CLIContext, SmartCommand, format_llm_output,
    create_llm_request_data, log_llm_usage
)
from .decorators import standard_cli_command


@click.group()
def okh_group():
    """
    OKH (OpenKnowHow) manifest management commands.
    
    These commands help you create, validate, and manage OKH manifests
    for hardware projects, including generation from repositories and
    validation.
    
    Examples:
      # Validate an OKH manifest
      ome okh validate my-project.okh.json
      
      # Generate OKH manifest from GitHub repository
      ome okh generate-from-url https://github.com/user/project
      
      # Create and store a manifest
      ome okh create my-project.okh.json
      
      # Use LLM for enhanced processing
      ome okh validate my-project.okh.json --use-llm --quality-level professional
    """
    pass


# Helper functions

async def _read_manifest_file(file_path: str) -> dict:
    """Read and parse manifest file."""
    manifest_path = Path(file_path)
    
    try:
        with open(manifest_path, 'r') as f:
            if manifest_path.suffix.lower() in ['.yaml', '.yml']:
                import yaml
                return yaml.safe_load(f)
            else:
                return json.load(f)
    except Exception as e:
        raise click.ClickException(f"Failed to read manifest file: {str(e)}")


async def _display_validation_results(cli_ctx: CLIContext, result: dict, output_format: str):
    """Display validation results."""
    validation = result.get("validation", result)
    is_valid = validation.get("is_valid", False)
    
    if is_valid:
        cli_ctx.log("Manifest is valid", "success")
    else:
        cli_ctx.log("Manifest validation failed", "error")
    
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
    manifest_id = result.get("id") or result.get("manifest", {}).get("id")
    
    if manifest_id:
        cli_ctx.log(f"OKH manifest created with ID: {manifest_id}", "success")
        
        if output:
            # Save result to output file
            with open(output, 'w') as f:
                json.dump(result, f, indent=2, default=str)
            cli_ctx.log(f"Result saved to {output}", "info")
        
        if output_format == "json":
            output_data = format_llm_output(result, cli_ctx)
            click.echo(output_data)
    else:
        cli_ctx.log("Failed to create OKH manifest", "error")


async def _display_retrieval_results(cli_ctx: CLIContext, result: dict, output: Optional[str], output_format: str):
    """Display retrieval results."""
    manifest = result.get("manifest", result)
    
    if manifest:
        cli_ctx.log(f"Retrieved OKH manifest: {manifest.get('title', 'Unknown')}", "success")
        
        if output:
            # Save manifest to output file
            with open(output, 'w') as f:
                json.dump(manifest, f, indent=2, default=str)
            cli_ctx.log(f"Manifest saved to {output}", "info")
        
        if output_format == "json":
            output_data = format_llm_output(result, cli_ctx)
            click.echo(output_data)
        else:
            # Show basic manifest info
            cli_ctx.log(f"Title: {manifest.get('title', 'Unknown')}", "info")
            cli_ctx.log(f"Version: {manifest.get('version', 'Unknown')}", "info")
            cli_ctx.log(f"Organization: {manifest.get('organization', {}).get('name', 'Unknown')}", "info")
    else:
        cli_ctx.log("Manifest not found", "error")


# Commands

@okh_group.command()
@click.argument('manifest_file', type=click.Path(exists=True))
@standard_cli_command(
    help_text="""
    Validate an OKH manifest for compliance and completeness.
    
    This command performs validation of an OKH manifest,
    checking for required fields, proper formatting, and completeness
    according to the OKH specification.
    
    Validation includes:
    - Required field presence and format
    - Manufacturing specification completeness
    - License and legal information
    - Documentation quality assessment
    - BOM structure validation
    
    When LLM is enabled, validation includes:
    - Semantic analysis of descriptions and requirements
    - Quality assessment of manufacturing specifications
    - Suggestions for improvement and missing information
    - Advanced compliance checking
    """,
    epilog="""
    Examples:
      # Basic validation
      ome okh validate my-project.okh.json
      
      # Strict validation with medical quality level
      ome okh validate my-project.okh.json --quality-level medical --strict-mode
      
      # Use LLM for enhanced validation
      ome okh validate my-project.okh.json --use-llm --quality-level professional
    """,
    async_cmd=True,
    track_performance=True,
    handle_errors=True,
    format_output=True,
    add_llm_config=True
)
@click.pass_context
async def validate(ctx, manifest_file: str, quality_level: str, strict_mode: bool,
                  verbose: bool, output_format: str, use_llm: bool,
                  llm_provider: str, llm_model: Optional[str]):
    """Validate an OKH manifest with enhanced LLM support."""
    cli_ctx = ctx.obj
    cli_ctx.start_command_tracking("okh-validate")
    
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
        # Read manifest file
        cli_ctx.log("Reading manifest file...", "info")
        manifest_data = await _read_manifest_file(manifest_file)
    
        # Create request data with LLM configuration
        # The API expects manifest data wrapped in a 'content' field
        request_data = create_llm_request_data(cli_ctx, {
            "validation_context": quality_level,
            "strict_mode": strict_mode
        })
        # Wrap manifest data in 'content' field as expected by API
        request_data["content"] = manifest_data
        
        # Log LLM usage if enabled
        if cli_ctx.is_llm_enabled():
            log_llm_usage(cli_ctx, "OKH validation")
        
        async def http_validate():
            """Validate via HTTP API"""
            cli_ctx.log("Validating via HTTP API...", "info")
            response = await cli_ctx.api_client.request(
                "POST", "/api/okh/validate", json_data=request_data
            )
            return response
        
        async def fallback_validate():
            """Validate using direct service calls"""
            cli_ctx.log("Using direct service validation...", "info")
            # Domains are registered by execute_with_fallback, but ensure here as well for safety
            from .base import ensure_domains_registered
            await ensure_domains_registered()
            
            okh_service = await OKHService.get_instance()
            # validate() expects a dict, not an OKHManifest object
            result = await okh_service.validate(manifest_data, validation_context=quality_level, strict_mode=strict_mode)
            return result
        
        # Execute validation with fallback
        command = SmartCommand(cli_ctx)
        result = await command.execute_with_fallback(http_validate, fallback_validate)
        
        # Display validation results
        await _display_validation_results(cli_ctx, result, output_format)
        
        cli_ctx.end_command_tracking()
        
    except Exception as e:
        cli_ctx.log(f"Validation failed: {str(e)}", "error")
        raise


@okh_group.command()
@click.argument('manifest_file', type=click.Path(exists=True))
@click.option('--output', '-o', help='Output file path')
@standard_cli_command(
    help_text="""
    Create and store an OKH manifest in the system.
    
    This command reads an OKH manifest file and stores it in the system
    for later retrieval, validation, and processing.
    
    The manifest is validated before storage to ensure it meets
    the OKH specification requirements.
    
    When LLM is enabled, creation includes:
    - Enhanced validation with semantic analysis
    - Automatic field completion and suggestions
    - Quality assessment and recommendations
    - Advanced compliance checking
    """,
    epilog="""
    Examples:
      # Create and store a manifest
      ome okh create my-project.okh.json
      
      # Create with output file
      ome okh create my-project.okh.json --output result.json
      
      # Use LLM for enhanced processing
      ome okh create my-project.okh.json --use-llm --quality-level professional
    """,
    async_cmd=True,
    track_performance=True,
    handle_errors=True,
    format_output=True,
    add_llm_config=True
)
@click.pass_context
async def create(ctx, manifest_file: str, output: Optional[str],
                verbose: bool, output_format: str, use_llm: bool,
                llm_provider: str, llm_model: Optional[str],
                quality_level: str, strict_mode: bool):
    """Create and store an OKH manifest with enhanced LLM support."""
    cli_ctx = ctx.obj
    cli_ctx.start_command_tracking("okh-create")
    
    # Update CLI context with parameters from decorator
    cli_ctx.update_llm_config(
        use_llm=use_llm,
        llm_provider=llm_provider,
        llm_model=llm_model,
        quality_level=quality_level,
        strict_mode=strict_mode
    )
    
    try:
        # Read manifest file
        cli_ctx.log("Reading manifest file...", "info")
        manifest_data = await _read_manifest_file(manifest_file)
    
        # Create request data with LLM configuration
        # Merge manifest data with LLM config (manifest fields go directly, not wrapped in 'content')
        request_data = create_llm_request_data(cli_ctx, {})
        # Add manifest fields directly to the request
        request_data.update(manifest_data)
        
        # Log LLM usage if enabled
        if cli_ctx.is_llm_enabled():
            log_llm_usage(cli_ctx, "OKH creation")
        
        async def http_create():
            """Create via HTTP API"""
            cli_ctx.log("Creating via HTTP API...", "info")
            response = await cli_ctx.api_client.request("POST", "/api/okh/create", json_data=request_data)
            return response
        
        async def fallback_create():
            """Create using direct service calls"""
            cli_ctx.log("Using direct service creation...", "info")
            manifest = OKHManifest.from_dict(manifest_data)
            okh_service = await OKHService.get_instance()
            result = await okh_service.create(manifest)
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


@okh_group.command()
@click.argument('manifest_id', type=str)
@click.option('--output', '-o', help='Output file path')
@standard_cli_command(
    help_text="""
    Retrieve an OKH manifest by ID from the system.
    
    This command fetches a previously stored OKH manifest using its
    unique identifier and displays the manifest information.
    
    When LLM is enabled, retrieval includes:
    - Enhanced manifest analysis and summary
    - Quality assessment of the retrieved manifest
    - Suggestions for improvement
    - Advanced metadata extraction
    """,
    epilog="""
    Examples:
      # Get a manifest by ID
      ome okh get 123e4567-e89b-12d3-a456-426614174000
      
      # Get with output file
      ome okh get 123e4567-e89b-12d3-a456-426614174000 --output manifest.json
      
      # Use LLM for enhanced analysis
      ome okh get 123e4567-e89b-12d3-a456-426614174000 --use-llm
    """,
    async_cmd=True,
    track_performance=True,
    handle_errors=True,
    format_output=True,
    add_llm_config=True
)
@click.pass_context
async def get(ctx, manifest_id: str, output: Optional[str],
             verbose: bool, output_format: str, use_llm: bool,
             llm_provider: str, llm_model: Optional[str],
             quality_level: str, strict_mode: bool):
    """Get an OKH manifest by ID with enhanced LLM support."""
    cli_ctx = ctx.obj
    cli_ctx.start_command_tracking("okh-get")
    
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
            log_llm_usage(cli_ctx, "OKH retrieval")
        
        async def http_get():
            """Get via HTTP API"""
            cli_ctx.log("Retrieving via HTTP API...", "info")
            response = await cli_ctx.api_client.request("GET", f"/api/okh/{manifest_id}")
            return response
        
        async def fallback_get():
            """Get using direct service calls"""
            cli_ctx.log("Using direct service retrieval...", "info")
            okh_service = await OKHService.get_instance()
            manifest = await okh_service.get_by_id(UUID(manifest_id))
            if manifest:
                return manifest.to_dict()
            else:
                raise click.ClickException("Manifest not found")
        
        # Execute retrieval with fallback
        command = SmartCommand(cli_ctx)
        result = await command.execute_with_fallback(http_get, fallback_get)
        
        # Display retrieval results
        await _display_retrieval_results(cli_ctx, result, output, output_format)
        
        cli_ctx.end_command_tracking()
        
    except Exception as e:
        cli_ctx.log(f"Retrieval failed: {str(e)}", "error")
        raise


@okh_group.command()
@click.argument('manifest_file', type=click.Path(exists=True))
@standard_cli_command(
    help_text="""
    Extract requirements from an OKH manifest.
    
    This command analyzes an OKH manifest and extracts all manufacturing
    requirements, capabilities, and specifications for use in matching
    and supply chain analysis.
    
    When LLM is enabled, extraction includes:
    - Enhanced requirement analysis and categorization
    - Semantic understanding of manufacturing processes
    - Quality assessment of extracted requirements
    - Suggestions for requirement improvement
    """,
    epilog="""
    Examples:
      # Extract requirements from manifest
      ome okh extract my-project.okh.json
      
      # Use LLM for enhanced extraction
      ome okh extract my-project.okh.json --use-llm --quality-level professional
    """,
    async_cmd=True,
    track_performance=True,
    handle_errors=True,
    format_output=True,
    add_llm_config=True
)
@click.pass_context
async def extract(ctx, manifest_file: str,
                 verbose: bool, output_format: str, use_llm: bool,
                 llm_provider: str, llm_model: Optional[str],
                 quality_level: str, strict_mode: bool):
    """Extract requirements from an OKH manifest with enhanced LLM support."""
    cli_ctx = ctx.obj
    cli_ctx.start_command_tracking("okh-extract")
    
    # Update CLI context with parameters from decorator
    cli_ctx.update_llm_config(
        use_llm=use_llm,
        llm_provider=llm_provider,
        llm_model=llm_model,
        quality_level=quality_level,
        strict_mode=strict_mode
    )
    
    try:
        # Read manifest file
        cli_ctx.log("Reading manifest file...", "info")
        manifest_data = await _read_manifest_file(manifest_file)
    
        # Create request data with LLM configuration
        request_data = create_llm_request_data(cli_ctx, {
            "content": manifest_data
        })
        
        # Log LLM usage if enabled
        if cli_ctx.is_llm_enabled():
            log_llm_usage(cli_ctx, "OKH extraction")
        
        async def http_extract():
            """Extract via HTTP API"""
            cli_ctx.log("Extracting via HTTP API...", "info")
            response = await cli_ctx.api_client.request("POST", "/api/okh/extract", json_data=request_data)
            return response
        
        async def fallback_extract():
            """Extract using direct service calls"""
            cli_ctx.log("Using direct service extraction...", "info")
            manifest = OKHManifest.from_dict(manifest_data)
            okh_service = await OKHService.get_instance()
            requirements = await okh_service.extract_requirements(manifest)
            return {"requirements": requirements}
        
        # Execute extraction with fallback
        command = SmartCommand(cli_ctx)
        result = await command.execute_with_fallback(http_extract, fallback_extract)
        
        # Display extraction results
        requirements = result.get("requirements", [])
        
        if requirements:
            cli_ctx.log(f"Extracted {len(requirements)} requirements", "success")
            
            if output_format == "json":
                output_data = format_llm_output(result, cli_ctx)
                click.echo(output_data)
            else:
                for i, req in enumerate(requirements, 1):
                    cli_ctx.log(f"{i}. {req.get('type', 'Unknown')}: {req.get('description', 'No description')}", "info")
        else:
            cli_ctx.log("No requirements found in manifest", "info")
        
        cli_ctx.end_command_tracking()
        
    except Exception as e:
        cli_ctx.log(f"Extraction failed: {str(e)}", "error")
        raise


@okh_group.command()
@click.option('--limit', default=10, help='Maximum number of manifests to list')
@click.option('--offset', default=0, help='Number of manifests to skip')
@standard_cli_command(
    help_text="""
    List stored OKH manifests in the system.
    
    This command retrieves and displays a list of all OKH manifests
    stored in the system, with pagination support for large datasets.
    
    When LLM is enabled, listing includes:
    - Enhanced manifest analysis and categorization
    - Quality assessment of stored manifests
    - Intelligent filtering and sorting suggestions
    - Advanced metadata extraction
    """,
    epilog="""
    Examples:
      # List all manifests
      ome okh list
      
      # List with pagination
      ome okh list --limit 20 --offset 10
      
      # Use LLM for enhanced analysis
      ome okh list --use-llm --limit 50
    """,
    async_cmd=True,
    track_performance=True,
    handle_errors=True,
    format_output=True,
    add_llm_config=True
)
@click.pass_context
async def list_manifests(ctx, limit: int, offset: int,
                        verbose: bool, output_format: str, use_llm: bool,
                        llm_provider: str, llm_model: Optional[str],
                        quality_level: str, strict_mode: bool):
    """List stored OKH manifests with enhanced LLM support."""
    cli_ctx = ctx.obj
    cli_ctx.start_command_tracking("okh-list")
    
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
            log_llm_usage(cli_ctx, "OKH listing")
        
        async def http_list():
            """List via HTTP API"""
            cli_ctx.log("Listing via HTTP API...", "info")
            params = {"limit": limit, "offset": offset}
            response = await cli_ctx.api_client.request("GET", "/api/okh/", params=params)
            return response
        
        async def fallback_list():
            """List using direct service calls"""
            cli_ctx.log("Using direct service listing...", "info")
            okh_service = await OKHService.get_instance()
            manifests = await okh_service.list_manifests(limit=limit, offset=offset)
            return {
                "manifests": [manifest.to_dict() for manifest in manifests],
                "total": len(manifests)
            }
        
        # Execute listing with fallback
        command = SmartCommand(cli_ctx)
        result = await command.execute_with_fallback(http_list, fallback_list)
        
        # Display listing results
        manifests = result.get("manifests", [])
        total = result.get("total", len(manifests))
        
        if manifests:
            cli_ctx.log(f"Found {total} OKH manifests", "success")
            
            if output_format == "json":
                output_data = format_llm_output(result, cli_ctx)
                click.echo(output_data)
            else:
                for manifest in manifests:
                    cli_ctx.log(f"📄 {manifest.get('id', 'Unknown')}", "info")
                    cli_ctx.log(f"   Title: {manifest.get('title', 'Unknown')}", "info")
                    cli_ctx.log(f"   Version: {manifest.get('version', 'Unknown')}", "info")
                    cli_ctx.log(f"   Organization: {manifest.get('organization', {}).get('name', 'Unknown')}", "info")
                    cli_ctx.log("", "info")  # Empty line for spacing
        else:
            cli_ctx.log("No OKH manifests found", "info")
        
        cli_ctx.end_command_tracking()
        
    except Exception as e:
        cli_ctx.log(f"Listing failed: {str(e)}", "error")
        raise


@okh_group.command()
@click.argument('manifest_id', type=str)
@click.option('--force', is_flag=True, help='Force deletion without confirmation')
@standard_cli_command(
    help_text="""
    Delete an OKH manifest from the system.
    
    This command removes a previously stored OKH manifest from the system.
    Use with caution as this action cannot be undone.
    
    When LLM is enabled, deletion includes:
    - Enhanced impact analysis before deletion
    - Dependency checking and warnings
    - Backup suggestions and safety checks
    - Advanced metadata cleanup
    """,
    epilog="""
    Examples:
      # Delete a manifest (with confirmation)
      ome okh delete 123e4567-e89b-12d3-a456-426614174000
      
      # Force deletion without confirmation
      ome okh delete 123e4567-e89b-12d3-a456-426614174000 --force
      
      # Use LLM for enhanced analysis
      ome okh delete 123e4567-e89b-12d3-a456-426614174000 --use-llm
    """,
    async_cmd=True,
    track_performance=True,
    handle_errors=True,
    format_output=True,
    add_llm_config=True
)
@click.pass_context
async def delete(ctx, manifest_id: str, force: bool,
                verbose: bool, output_format: str, use_llm: bool,
                llm_provider: str, llm_model: Optional[str],
                quality_level: str, strict_mode: bool):
    """Delete an OKH manifest with enhanced LLM support."""
    cli_ctx = ctx.obj
    cli_ctx.start_command_tracking("okh-delete")
    
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
            if not click.confirm(f"Are you sure you want to delete manifest {manifest_id}?"):
                cli_ctx.log("Deletion cancelled", "info")
                return
        
        # Log LLM usage if enabled
        if cli_ctx.is_llm_enabled():
            log_llm_usage(cli_ctx, "OKH deletion")
        
        async def http_delete():
            """Delete via HTTP API"""
            cli_ctx.log("Deleting via HTTP API...", "info")
            response = await cli_ctx.api_client.request("DELETE", f"/api/okh/{manifest_id}")
            return response
        
        async def fallback_delete():
            """Delete using direct service calls"""
            cli_ctx.log("Using direct service deletion...", "info")
            okh_service = await OKHService.get_instance()
            success = await okh_service.delete(UUID(manifest_id))
            return {"success": success}
        
        # Execute deletion with fallback
        command = SmartCommand(cli_ctx)
        result = await command.execute_with_fallback(http_delete, fallback_delete)
        
        # Display deletion results
        if result.get("success", True):  # HTTP API returns success by default
            cli_ctx.log(f"OKH manifest {manifest_id} deleted successfully", "success")
        else:
            cli_ctx.log(f"Failed to delete OKH manifest {manifest_id}", "error")
        
        cli_ctx.end_command_tracking()
        
    except Exception as e:
        cli_ctx.log(f"Deletion failed: {str(e)}", "error")
        raise


@okh_group.command()
@click.argument('file_path', type=click.Path(exists=True))
@standard_cli_command(
    help_text="""
    Upload and validate an OKH manifest file.
    
    This command uploads an OKH manifest file to the system and performs
    validation to ensure it meets the OKH specification.
    
    When LLM is enabled, upload includes:
    - Enhanced validation with semantic analysis
    - Automatic field completion and suggestions
    - Quality assessment and recommendations
    - Advanced compliance checking
    """,
    epilog="""
    Examples:
      # Upload and validate a manifest
      ome okh upload my-project.okh.json
      
      # Upload with premium quality validation
      ome okh upload my-project.okh.json --quality-level premium --strict-mode
      
      # Use LLM for enhanced processing
      ome okh upload my-project.okh.json --use-llm --quality-level standard
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
    """Upload and validate an OKH manifest file with enhanced LLM support."""
    cli_ctx = ctx.obj
    cli_ctx.start_command_tracking("okh-upload")
    
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
            log_llm_usage(cli_ctx, "OKH upload")
        
        async def http_upload():
            """Upload manifest via HTTP API"""
            cli_ctx.log("Uploading via HTTP API...", "info")
            
            # Prepare form data for file upload
            form_data = {
                "validation_context": quality_level,
                "description": f"Uploaded OKH manifest with {quality_level} validation"
            }
            
            response = await cli_ctx.api_client.upload_file(
                "POST", 
                "/api/okh/upload", 
                file_path,
                file_field_name="okh_file",
                form_data=form_data
            )
            return response
        
        async def fallback_upload():
            """Fallback upload using direct services"""
            cli_ctx.log("Using direct service upload...", "info")
            with open(file_path, 'r') as f:
                content = f.read()
            
            # Parse JSON content to dict, then create manifest
            import json
            manifest_data = json.loads(content)
            manifest = OKHManifest.from_dict(manifest_data)
            okh_service = await OKHService.get_instance()
            result = await okh_service.create(manifest)
            return result.to_dict()
        
        # Execute upload with fallback
        command = SmartCommand(cli_ctx)
        result = await command.execute_with_fallback(http_upload, fallback_upload)
        
        # Display upload results
        manifest_id = result.get("id") or result.get("manifest", {}).get("id")
        
        if manifest_id:
            cli_ctx.log(f"OKH manifest uploaded with ID: {manifest_id}", "success")
        else:
            cli_ctx.log("Failed to upload OKH manifest", "error")
        
        cli_ctx.end_command_tracking()
        
    except Exception as e:
        cli_ctx.log(f"Upload failed: {str(e)}", "error")
        raise


@okh_group.command()
@click.argument('url', type=str)
@click.option('--output', '-o', type=click.Path(), help='Output directory for built files (enables BOM export)')
@click.option('--format', '-f', type=click.Choice(['json', 'yaml', 'okh', 'api']), default='okh', help='Output format: okh (OKH manifest), api (API wrapper), json/yaml (legacy)')
@click.option('--bom-formats', multiple=True, type=click.Choice(['json', 'md', 'csv', 'components']), default=['json', 'md'], help='BOM export formats (only when --output is specified)')
@click.option('--unified-bom', is_flag=True, help='Include full BOM in manifest instead of compressed summary (default: compressed summary)')
@click.option('--no-review', is_flag=True, help='Skip interactive review and generate manifest directly')
@click.option('--github-token', type=str, help='GitHub personal access token (increases rate limit from 60 to 5,000 requests/hour)')
@click.option('--clone', is_flag=True, help='Clone repository locally for extraction (faster, more reliable, eliminates API limits)')
@standard_cli_command(
    help_text="""
    Generate OKH manifest from repository URL.
    
    This command analyzes a repository URL and generates an OKH manifest by extracting
    project information, documentation, and manufacturing specifications.
    
    **File Categorization**:
    The command uses a two-layer intelligent file categorization system:
    - **Layer 1 (Heuristics)**: Fast rule-based categorization using file extensions,
      directory paths, and filename patterns. Always available and provides fallback.
    - **Layer 2 (LLM)**: Content-aware categorization with semantic understanding.
      Automatically used when LLM is available, gracefully falls back to Layer 1 if unavailable.
    
    Files are automatically categorized into:
    - making_instructions: Assembly/build guides for humans
    - manufacturing_files: Machine-readable files (.stl, .3mf, .gcode)
    - design_files: Source CAD files (.scad, .fcstd, etc.)
    - operating_instructions: User manuals and usage guides
    - technical_specifications: Technical specs and validation reports
    - publications: Research papers and academic publications
    - documentation_home: Main project documentation (README.md)
    
    When LLM is enabled, generation includes:
    - Enhanced project analysis and understanding
    - Intelligent file categorization with content analysis
    - Intelligent field completion and suggestions
    - Quality assessment and recommendations
    - Advanced manufacturing specification extraction
    """,
    epilog="""
    Examples:
      # Generate from GitHub repository
      ome okh generate-from-url https://github.com/user/project
      
      # Generate with local cloning (faster, more reliable)
      ome okh generate-from-url https://github.com/user/project --clone
      
      # Generate with BOM export
      ome okh generate-from-url https://github.com/user/project --output ./output
      
      # Use LLM for enhanced generation
      ome okh generate-from-url https://github.com/user/project --use-llm --quality-level professional
    """,
    async_cmd=True,
    track_performance=True,
    handle_errors=True,
    format_output=True,
    add_llm_config=True
)
@click.pass_context
async def generate_from_url(ctx, url: str, output: str, format: str, bom_formats: tuple, 
                           unified_bom: bool, no_review: bool, github_token: str, clone: bool,
                           verbose: bool, output_format: str, use_llm: bool,
                           llm_provider: str, llm_model: Optional[str],
                           quality_level: str, strict_mode: bool):
    """Generate OKH manifest from repository URL with enhanced LLM support."""
    cli_ctx = ctx.obj
    cli_ctx.start_command_tracking("okh-generate-from-url")
    
    # Update CLI context with parameters from decorator
    cli_ctx.update_llm_config(
        use_llm=use_llm,
        llm_provider=llm_provider,
        llm_model=llm_model,
        quality_level=quality_level,
        strict_mode=strict_mode
    )
    
    try:
        cli_ctx.log(f"🔍 Analyzing repository: {url}", "info")
        
        # Log LLM usage if enabled
        if cli_ctx.is_llm_enabled():
            log_llm_usage(cli_ctx, "OKH generation from URL")
        
        async def http_generate():
            """Generate via HTTP API"""
            cli_ctx.log("Generating via HTTP API...", "info")
            payload = {"url": url, "skip_review": no_review}
            response = await cli_ctx.api_client.request("POST", "/api/okh/generate-from-url", json_data=payload)
            return response
        
        async def fallback_generate():
            """Generate using direct service calls"""
            cli_ctx.log("Using direct service generation...", "info")
            from ..core.generation.url_router import URLRouter
            from ..core.generation.engine import GenerationEngine
            from ..core.generation.review import ReviewInterface
            from ..core.generation.models import GenerationResult, PlatformType, LayerConfig
            from ..core.generation.platforms.github import GitHubExtractor
            from ..core.generation.platforms.gitlab import GitLabExtractor
            
            # Validate and route URL
            router = URLRouter()
            if not router.validate_url(url):
                raise ValueError(f"Invalid URL: {url}")
            
            platform = router.detect_platform(url)
            if platform is None:
                raise ValueError(f"Unsupported platform for URL: {url}")
            
            cli_ctx.log(f"Detected platform: {platform.value}", "info")
            
            # Generate project data from URL
            cli_ctx.log("Fetching project data...", "info")
            
            # Choose extraction method based on clone flag
            use_clone = clone
            if use_clone:
                cli_ctx.log("Using local Git cloning for extraction...", "info")
                if not router.supports_local_cloning(url):
                    cli_ctx.log("Warning: URL doesn't support local cloning, falling back to API extraction", "warning")
                    use_clone = False
                else:
                    generator = router.route_to_local_git_extractor()
                    project_data = await generator.extract_project(url)
            
            if not use_clone:
                # Get platform-specific generator for API-based extraction
                if platform == PlatformType.GITHUB:
                    generator = GitHubExtractor(github_token=github_token)
                elif platform == PlatformType.GITLAB:
                    generator = GitLabExtractor()
                else:
                    raise ValueError(f"Unsupported platform: {platform}")
                
                project_data = await generator.extract_project(url)
            
            # Generate manifest from project data
            config = LayerConfig()
            config.use_bom_normalization = True  # Enable BOM normalization
            engine = GenerationEngine(config=config)
            cli_ctx.log("Generating manifest fields...", "info")
            
            result = await engine.generate_manifest_async(project_data)
            
            if not no_review:
                cli_ctx.log("Starting interactive review...", "info")
                review_interface = ReviewInterface(result)
                result = await review_interface.review()
            return result
        
        # Store the raw result for BOM export
        raw_result = await fallback_generate()
        
        # Set unified BOM mode if requested
        if unified_bom and hasattr(raw_result, 'unified_bom_mode'):
            raw_result.unified_bom_mode = True
        
        # Convert to appropriate format
        if format == 'okh':
            result = raw_result.to_okh_manifest() if hasattr(raw_result, 'to_okh_manifest') else raw_result
        elif format == 'api':
            result = {
                "success": True,
                "message": "Manifest generated successfully",
                "manifest": raw_result.to_dict(),
                "quality_report": {
                    "overall_quality": raw_result.quality_report.overall_quality,
                    "required_fields_complete": raw_result.quality_report.required_fields_complete,
                    "missing_required_fields": raw_result.quality_report.missing_required_fields,
                    "recommendations": raw_result.quality_report.recommendations
                }
            }
        else:
            result = raw_result.to_dict()
        
        # Handle output
        if output:
            output_path = Path(output)
            
            # Create output directory if it doesn't exist
            output_path.mkdir(parents=True, exist_ok=True)
            
            # Export manifest
            manifest_path = output_path / "manifest.okh.json"
            if format == 'yaml':
                import yaml
                with open(manifest_path, 'w') as f:
                    yaml.dump(result, f, default_flow_style=False)
            else:
                with open(manifest_path, 'w') as f:
                    json.dump(result, f, indent=2)
            
            # Export BOM if available, formats specified, and NOT in unified mode
            if (bom_formats and raw_result and hasattr(raw_result, 'full_bom') and 
                raw_result.full_bom and not getattr(raw_result, 'unified_bom_mode', False)):
                try:
                    # Use the full BOM object from the raw result
                    bom = raw_result.full_bom
                    
                    # Export BOM in specified formats
                    exporter = BuiltDirectoryExporter(output_path)
                    await exporter._export_bom_formats(bom)
                    
                    cli_ctx.log(f"✅ Manifest and BOM exported to: {output_path}", "success")
                    cli_ctx.log(f"📁 BOM formats: {', '.join(bom_formats)}", "info")
                except Exception as e:
                    cli_ctx.log(f"⚠️  BOM export failed: {e}", "warning")
                    cli_ctx.log(f"✅ Manifest saved to: {manifest_path}", "success")
            else:
                if getattr(raw_result, 'unified_bom_mode', False):
                    cli_ctx.log(f"✅ Unified manifest (with full BOM) saved to: {manifest_path}", "success")
                else:
                    cli_ctx.log(f"✅ Manifest saved to: {manifest_path}", "success")
        else:
            if (cli_ctx and cli_ctx.output_format == 'json') or format in ['json', 'api']:
                output_data = format_llm_output(result, cli_ctx)
                click.echo(output_data)
            else:
                # Show summary for OKH format
                if format == 'okh':
                    title = result.get('title', 'Unknown')
                    version = result.get('version', 'Unknown')
                    quality = result.get('metadata', {}).get('generation_confidence', 0)
                    missing_fields = result.get('metadata', {}).get('missing_required_fields', [])
                    
                    cli_ctx.log(f"✅ Generated OKH manifest for: {title} v{version}", "success")
                    cli_ctx.log(f"📊 Generation confidence: {quality:.1%}", "info")
                    
                    if missing_fields:
                        cli_ctx.log(f"⚠️  Missing required fields: {', '.join(missing_fields)}", "warning")
                else:
                    # Legacy format summary
                    title = result.get('title', 'Unknown')
                    version = result.get('version', 'Unknown')
                    quality = result.get('quality_report', {}).get('overall_quality', 0)
                    
                    cli_ctx.log(f"✅ Generated manifest for: {title} v{version}", "success")
                    cli_ctx.log(f"📊 Quality score: {quality:.1%}", "info")
                    
                    if result.get('quality_report', {}).get('missing_required_fields'):
                        missing = result['quality_report']['missing_required_fields']
                        cli_ctx.log(f"⚠️  Missing required fields: {', '.join(missing)}", "warning")
        
        cli_ctx.end_command_tracking()
        
    except Exception as e:
        cli_ctx.log(f"❌ Generation failed: {str(e)}", "error")
        if cli_ctx and cli_ctx.verbose:
            import traceback
            click.echo(traceback.format_exc())
        raise


@okh_group.command()
@click.option('--output', '-o', type=click.Path(), help='Output file path for the JSON schema')
@standard_cli_command(
    help_text="""
    Export the JSON schema for the OKH (OpenKnowHow) domain model.
    
    This command generates and exports the JSON schema for the OKHManifest
    dataclass in canonical JSON Schema format (draft-07). The schema represents
    the complete structure of the OKH domain model including all fields, types,
    and constraints.
    
    The exported schema can be used for:
    - Validation of OKH manifests
    - Documentation generation
    - API contract specification
    - Integration with other systems
    """,
    epilog="""
    Examples:
      # Export schema to console
      ome okh export
      
      # Export schema to file
      ome okh export --output okh-schema.json
      
      # Export with JSON output format
      ome okh export --output okh-schema.json --json
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
    """Export OKH domain model as JSON schema."""
    cli_ctx = ctx.obj
    cli_ctx.start_command_tracking("okh-export")
    
    try:
        cli_ctx.log("Exporting OKH JSON schema...", "info")
        
        async def http_export():
            """Export via HTTP API"""
            cli_ctx.log("Exporting via HTTP API...", "info")
            response = await cli_ctx.api_client.request("GET", "/api/okh/export")
            return response
        
        async def fallback_export():
            """Export using direct schema generation"""
            cli_ctx.log("Using direct schema generation...", "info")
            from ..core.models.okh import OKHManifest
            from ..core.utils.schema_generator import generate_json_schema
            
            schema = generate_json_schema(OKHManifest, title="OKHManifest")
            return {
                "success": True,
                "message": "OKH schema exported successfully",
                "schema": schema,
                "schema_version": schema.get("$schema", "http://json-schema.org/draft-07/schema#"),
                "model_name": "OKHManifest"
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
                cli_ctx.log("✅ OKH JSON Schema exported successfully", "success")
                cli_ctx.log(f"   Schema Version: {result.get('schema_version', 'N/A')}", "info")
                cli_ctx.log(f"   Model Name: {result.get('model_name', 'OKHManifest')}", "info")
                cli_ctx.log(f"   Use --output to save to file", "info")
        
        cli_ctx.end_command_tracking()
        
    except Exception as e:
        cli_ctx.log(f"❌ Export failed: {str(e)}", "error")
        if cli_ctx.verbose:
            import traceback
            click.echo(traceback.format_exc())
        raise


@okh_group.command()
@click.argument('project_name', type=str)
@click.option('--version', default='0.1.0', help='Initial project version (semantic recommended)')
@click.option('--organization', help='Optional organization name for future packaging alignment')
@click.option('--template-level', 
              type=click.Choice(['minimal', 'standard', 'detailed']), 
              default='standard',
              help='Amount of guidance in stub docs')
@click.option('--output-format', 
              type=click.Choice(['json', 'zip', 'filesystem']), 
              default='json',
              help='Output format')
@click.option('--output-path', 
              type=click.Path(), 
              help='Output path (required for filesystem format)')
@click.option('--include-examples/--no-examples', 
              default=True,
              help='Include sample files/content')
@click.option('--okh-version', 
              default='OKH-LOSHv1.0',
              help='OKH schema version tag')
@click.pass_context
@standard_cli_command(
    async_cmd=True,
    help_text="""
    Generate an OKH-compliant project scaffold with documentation stubs and manifest template.
    
    This command creates a complete project structure that follows OKH package conventions
    with MkDocs integration, documentation stubs, and an OKH manifest template
    generated by introspecting the OKHManifest dataclass.
    
    The generated project includes:
    - OKH-compliant directory structure
    - MkDocs configuration for professional documentation
    - OKH manifest template with field guidance
    - BOM templates (CSV and Markdown)
    - Assembly and manufacturing guides
    - documentation stubs
    
    Template Levels:
    - minimal: Basic placeholders for experienced developers
    - standard: Detailed guidance with examples (default)
    - detailed: help with best practices
    
    Output Formats:
    - json: Returns structured JSON representation (default)
    - zip: Creates downloadable ZIP file with all project files
    - filesystem: Writes directly to specified directory path
    
    Examples:
      # Generate basic project scaffold
      ome okh scaffold my-awesome-project
      
      # Generate with detailed templates and ZIP output
      ome okh scaffold arduino-sensor --template-level detailed --output-format zip
      
      # Generate to filesystem with custom organization
      ome okh scaffold microscope-stage --organization "University Lab" --output-format filesystem --output-path ./projects
      
      # Generate minimal scaffold for experienced developers
      ome okh scaffold quick-prototype --template-level minimal --output-format json
    """,
    epilog="""
    The scaffolded projects are designed to work seamlessly with the OME ecosystem:
    - Generated manifests can be validated using 'ome okh validate'
    - Projects can be used as OKH requirements in matching operations
    - The structure supports the OME generation workflow
    - Projects can be stored and retrieved using OME storage services
    
    For more information, see the Scaffolding Guide in the documentation.
    """
)
async def scaffold(ctx, project_name: str, version: str, organization: Optional[str], 
                  template_level: str, output_format: str, output_path: Optional[str],
                  include_examples: bool, okh_version: str, verbose: bool = False,
                  use_llm: bool = False, llm_provider: str = 'anthropic', 
                  llm_model: Optional[str] = None, quality_level: str = 'professional',
                  strict_mode: bool = False):
    """Generate an OKH project scaffold with documentation stubs and manifest template."""
    cli_ctx = ctx.obj
    cli_ctx.start_command_tracking('okh.scaffold')
    
    try:
        cli_ctx.log(f"🏗️  Generating OKH project scaffold: {project_name}", "info")
        
        # Prepare request data
        request_data = {
            "project_name": project_name,
            "version": version,
            "template_level": template_level,
            "output_format": output_format,
            "include_examples": include_examples,
            "okh_version": okh_version
        }
        
        # Add optional fields if provided
        if organization:
            request_data["organization"] = organization
        if output_path:
            request_data["output_path"] = str(output_path)
        
        # Make API request
        data = await cli_ctx.api_client.request(
            method='POST',
            endpoint='/api/okh/scaffold',
            json_data=request_data
        )
        
        # Display success message
        cli_ctx.log(f"✅ Scaffold generated successfully!", "success")
        
        # Display project information
        if cli_ctx.output_format == 'json':
            click.echo(json.dumps(data, indent=2))
        else:
            # Display key information
            click.echo(f"\n📁 Project: {data.get('project_name')}")
            click.echo(f"📋 Template Level: {template_level}")
            click.echo(f"📦 Output Format: {output_format}")
            
            # Display structure information
            structure = data.get('structure', {})
            if structure:
                project_dir = structure.get(project_name, {})
                if project_dir:
                    click.echo(f"\n📂 Generated Structure:")
                    _display_structure(project_dir, indent=2)
            
            # Display manifest template information
            manifest_template = data.get('manifest_template', {})
            if manifest_template:
                click.echo(f"\n📄 OKH Manifest Template:")
                click.echo(f"   Title: {manifest_template.get('title', 'N/A')}")
                click.echo(f"   Version: {manifest_template.get('version', 'N/A')}")
                click.echo(f"   OKH Version: {manifest_template.get('okhv', 'N/A')}")
                click.echo(f"   Required Fields: {len([k for k, v in manifest_template.items() if '[REQUIRED]' in str(v)])}")
            
            # Display output information
            if output_format == 'zip' and data.get('download_url'):
                click.echo(f"\n📥 Download URL: {data.get('download_url')}")
            elif output_format == 'filesystem' and data.get('filesystem_path'):
                click.echo(f"\n📁 Filesystem Path: {data.get('filesystem_path')}")
            elif output_format == 'json':
                click.echo(f"\n💡 Use --json flag to see full structure data")
            
            # Display next steps
            click.echo(f"\n🚀 Next Steps:")
            click.echo(f"   1. Customize the generated manifest template")
            click.echo(f"   2. Add your hardware designs and documentation")
            click.echo(f"   3. Use 'ome okh validate' to check OKH compliance")
            click.echo(f"   4. Use 'ome match requirements' to find manufacturing capabilities")
            
            if template_level in ['standard', 'detailed']:
                click.echo(f"   5. Use 'mkdocs serve' to build professional documentation")
        
        cli_ctx.end_command_tracking()
        
    except Exception as e:
        cli_ctx.log(f"❌ Scaffold generation failed: {str(e)}", "error")
        if cli_ctx and cli_ctx.verbose:
            import traceback
            click.echo(traceback.format_exc())
        raise


def _display_structure(structure: dict, indent: int = 0) -> None:
    """Display directory structure in a tree-like format."""
    prefix = "  " * indent
    
    for name, content in structure.items():
        if isinstance(content, dict):
            click.echo(f"{prefix}📁 {name}/")
            _display_structure(content, indent + 1)
        else:
            # It's a file
            icon = "📄" if name.endswith('.md') else "📄"
            click.echo(f"{prefix}{icon} {name}")


@okh_group.command()
@click.argument('project_path', type=click.Path(exists=True))
@click.option('--apply', is_flag=True, help='Apply cleanup (by default runs as dry-run only)')
@click.option('--remove-unmodified-stubs/--keep-unmodified-stubs', default=True, help='Remove unmodified scaffolding stubs')
@click.option('--remove-empty-directories/--keep-empty-directories', default=True, help='Remove empty directories after cleanup')
@click.pass_context
@standard_cli_command(
    async_cmd=True,
    help_text="""
    Clean and optimize a scaffolded OKH project directory.
    
    By default, this runs in dry-run mode and reports the files and directories
    that would be removed. Use --apply to perform the cleanup.
    
    Operations:
    - Remove unmodified documentation stubs generated by scaffolding
    - Remove empty directories after stub removal
    """,
    epilog="""
    Examples:
      # Preview cleanup changes (dry-run)
      ome okh scaffold-cleanup ./projects/my-project
      
      # Apply cleanup changes
      ome okh scaffold-cleanup ./projects/my-project --apply
      
      # Keep empty directories
      ome okh scaffold-cleanup ./projects/my-project --apply --keep-empty-directories
    """,
    track_performance=True,
    handle_errors=True,
    format_output=True,
)
async def scaffold_cleanup(ctx, project_path: str, apply: bool,
                           remove_unmodified_stubs: bool,
                           remove_empty_directories: bool,
                           verbose: bool, output_format: str,
                           use_llm: bool = False, llm_provider: str = 'anthropic',
                           llm_model: Optional[str] = None, quality_level: str = 'professional',
                           strict_mode: bool = False):
    """Cleanup OKH scaffold directory by removing unmodified stubs and empty folders."""
    cli_ctx = ctx.obj
    cli_ctx.start_command_tracking('okh.scaffold-cleanup')

    try:
        cli_ctx.log(f"🧹 Cleaning OKH scaffold at: {project_path}", "info")

        payload = {
            "project_path": str(project_path),
            "remove_unmodified_stubs": bool(remove_unmodified_stubs),
            "remove_empty_directories": bool(remove_empty_directories),
            "dry_run": (not apply),
        }

        data = await cli_ctx.api_client.request(
            method='POST',
            endpoint='/api/okh/scaffold/cleanup',
            json_data=payload
        )

        # Output
        if cli_ctx.output_format == 'json':
            click.echo(json.dumps(data, indent=2))
        else:
            removed_files = data.get('removed_files', [])
            removed_dirs = data.get('removed_directories', [])
            bytes_saved = data.get('bytes_saved', 0)
            dry_run = payload["dry_run"]

            cli_ctx.log("✅ Dry run completed" if dry_run else "✅ Cleanup completed", "success")
            if removed_files:
                click.echo(f"\n🗑️  Files to remove ({len(removed_files)}):" if dry_run else f"\n🗑️  Files removed ({len(removed_files)}):")
                for f in removed_files:
                    click.echo(f"   - {f}")
            if removed_dirs:
                click.echo(f"\n📁 Empty directories to remove ({len(removed_dirs)}):" if dry_run else f"\n📁 Empty directories removed ({len(removed_dirs)}):")
                for d in removed_dirs:
                    click.echo(f"   - {d}")
            if not dry_run:
                click.echo(f"\n💾 Bytes saved: {bytes_saved}")

            warnings = data.get('warnings', [])
            if warnings:
                # Separate broken link warnings from other warnings
                broken_link_warnings = [w for w in warnings if "Broken link" in w or "broken link" in w.lower()]
                other_warnings = [w for w in warnings if w not in broken_link_warnings]
                
                if broken_link_warnings:
                    click.echo("\n🔗 Broken Link Warnings:")
                    for w in broken_link_warnings:
                        # Style broken link warnings more prominently
                        cli_ctx.log(f"   {w}", "warning")
                
                if other_warnings:
                    click.echo("\n⚠️  Other Warnings:")
                    for w in other_warnings:
                        click.echo(f"   - {w}")

        cli_ctx.end_command_tracking()
    except Exception as e:
        cli_ctx.log(f"❌ Cleanup failed: {str(e)}", "error")
        if cli_ctx and cli_ctx.verbose:
            import traceback
            click.echo(traceback.format_exc())
        raise