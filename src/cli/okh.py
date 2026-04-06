"""
OKH (OpenKnowHow) commands for OHM CLI

This module provides commands for managing OKH manifests including
creation, validation, extraction, and storage operations.
"""

import json
from pathlib import Path
from typing import Any, Dict, Optional
from uuid import UUID

import click

from ..core.generation.built_directory import BuiltDirectoryExporter
from ..core.models.okh import OKHManifest
from ..core.services.okh_service import OKHService
from ..core.validation.auto_fix import auto_fix_okh_manifest
from ..core.validation.model_validator import validate_okh_manifest
from .base import (
    CLIContext,
    SmartCommand,
    create_llm_request_data,
    format_llm_output,
    log_llm_usage,
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
      ohm okh validate my-project.okh.json

      # Generate OKH manifest from GitHub repository
      ohm okh generate-from-url https://github.com/user/project

      # Create and store a manifest
      ohm okh create my-project.okh.json

      # Use LLM for enhanced processing
      ohm okh validate my-project.okh.json --use-llm --quality-level professional
    """
    pass


# Helper functions


async def _read_manifest_file(file_path: str) -> dict:
    """Read and parse manifest file."""
    manifest_path = Path(file_path)

    try:
        with open(manifest_path, "r") as f:
            if manifest_path.suffix.lower() in [".yaml", ".yml"]:
                import yaml

                return yaml.safe_load(f)
            else:
                return json.load(f)
    except Exception as e:
        raise click.ClickException(f"Failed to read manifest file: {str(e)}")


async def _display_validation_results(
    cli_ctx: CLIContext, result: dict, output_format: str
):
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


def _detect_domain_from_manifest_data(data: Dict[str, Any]) -> str:
    """Detect domain from manifest data structure."""
    from src.core.utils.domain_detection import detect_domain

    return detect_domain(data)


async def _display_retrieval_results(
    cli_ctx: CLIContext, result: dict, output: Optional[str], output_format: str
):
    """Display retrieval results."""
    # Extract manifest data from response
    # The API now returns OKHResponse with fields at top level, not nested in "manifest"
    manifest = result.get("manifest", result)

    # If result has top-level fields like "id", "title", etc., use result directly
    if "id" in result and "title" in result:
        manifest = result
    elif "manifest" in result:
        manifest = result["manifest"]

    if manifest and manifest.get("id"):
        manifest_title = manifest.get("title", "Unknown")
        cli_ctx.log(f"Retrieved OKH manifest: {manifest_title}", "success")

        # Save to file if output is specified
        if output:
            with open(output, "w") as f:
                json.dump(manifest, f, indent=2, default=str)
            cli_ctx.log(f"Manifest saved to {output}", "info")

        # Always output full JSON to stdout by default
        # If output_format is explicitly set to sohmthing other than json, still output JSON
        # (the format option is mainly for other commands)
        click.echo(json.dumps(manifest, indent=2, default=str))
    else:
        cli_ctx.log("Manifest not found", "error")


# Commands


@okh_group.command()
@click.argument("manifest_file", type=click.Path(exists=True))
@click.option(
    "--domain",
    type=click.Choice(["manufacturing", "cooking"]),
    help="Domain override (auto-detected from file if not provided)",
)
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
      ohm okh validate my-project.okh.json
      
      # Strict validation with medical quality level
      ohm okh validate my-project.okh.json --quality-level medical --strict-mode
      
      # Use LLM for enhanced validation
      ohm okh validate my-project.okh.json --use-llm --quality-level professional
    """,
    async_cmd=True,
    track_performance=True,
    handle_errors=True,
    format_output=True,
    add_llm_config=True,
)
@click.pass_context
async def validate(
    ctx,
    manifest_file: str,
    domain: Optional[str],
    quality_level: str,
    strict_mode: bool,
    verbose: bool,
    output_format: str,
    use_llm: bool,
    llm_provider: str,
    llm_model: Optional[str],
):
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
        strict_mode=strict_mode,
    )

    try:
        # Read manifest file
        cli_ctx.log("Reading manifest file...", "info")
        manifest_data = await _read_manifest_file(manifest_file)

        # Detect or use explicit domain
        detected_domain = (
            domain or _detect_domain_from_manifest_data(manifest_data)
            if manifest_data
            else None
        )
        if detected_domain:
            cli_ctx.log(f"Using domain: {detected_domain}", "info")
            # Set domain in manifest_data so API can detect it
            if manifest_data and not manifest_data.get("domain"):
                manifest_data["domain"] = detected_domain

        # Create request data with LLM configuration
        # The API expects manifest data wrapped in a 'content' field
        request_data = create_llm_request_data(
            cli_ctx, {"validation_context": quality_level, "strict_mode": strict_mode}
        )
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
            result = await okh_service.validate(
                manifest_data, validation_context=quality_level, strict_mode=strict_mode
            )
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
@click.argument("manifest_id", type=str)
@click.option("--output", "-o", help="Output file path")
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
      ohm okh get 123e4567-e89b-12d3-a456-426614174000
      
      # Get with output file
      ohm okh get 123e4567-e89b-12d3-a456-426614174000 --output manifest.json
      
      # Use LLM for enhanced analysis
      ohm okh get 123e4567-e89b-12d3-a456-426614174000 --use-llm
    """,
    async_cmd=True,
    track_performance=True,
    handle_errors=True,
    format_output=True,
    add_llm_config=True,
)
@click.pass_context
async def get(
    ctx,
    manifest_id: str,
    output: Optional[str],
    verbose: bool,
    output_format: str,
    use_llm: bool,
    llm_provider: str,
    llm_model: Optional[str],
    quality_level: str,
    strict_mode: bool,
):
    """Get an OKH manifest by ID with enhanced LLM support."""
    cli_ctx = ctx.obj
    cli_ctx.start_command_tracking("okh-get")

    # Update CLI context with parameters from decorator
    cli_ctx.update_llm_config(
        use_llm=use_llm,
        llm_provider=llm_provider,
        llm_model=llm_model,
        quality_level=quality_level,
        strict_mode=strict_mode,
    )

    try:
        # Log LLM usage if enabled
        if cli_ctx.is_llm_enabled():
            log_llm_usage(cli_ctx, "OKH retrieval")

        async def http_get():
            """Get via HTTP API"""
            cli_ctx.log("Retrieving via HTTP API...", "info")
            response = await cli_ctx.api_client.request(
                "GET", f"/api/okh/{manifest_id}"
            )
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
@click.argument("manifest_file", type=click.Path(exists=True))
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
      ohm okh extract my-project.okh.json
      
      # Use LLM for enhanced extraction
      ohm okh extract my-project.okh.json --use-llm --quality-level professional
    """,
    async_cmd=True,
    track_performance=True,
    handle_errors=True,
    format_output=True,
    add_llm_config=True,
)
@click.pass_context
async def extract(
    ctx,
    manifest_file: str,
    verbose: bool,
    output_format: str,
    use_llm: bool,
    llm_provider: str,
    llm_model: Optional[str],
    quality_level: str,
    strict_mode: bool,
):
    """Extract requirements from an OKH manifest with enhanced LLM support."""
    cli_ctx = ctx.obj
    cli_ctx.start_command_tracking("okh-extract")

    # Update CLI context with parameters from decorator
    cli_ctx.update_llm_config(
        use_llm=use_llm,
        llm_provider=llm_provider,
        llm_model=llm_model,
        quality_level=quality_level,
        strict_mode=strict_mode,
    )

    try:
        # Read manifest file
        cli_ctx.log("Reading manifest file...", "info")
        manifest_data = await _read_manifest_file(manifest_file)

        # Create request data with LLM configuration
        request_data = create_llm_request_data(cli_ctx, {"content": manifest_data})

        # Log LLM usage if enabled
        if cli_ctx.is_llm_enabled():
            log_llm_usage(cli_ctx, "OKH extraction")

        async def http_extract():
            """Extract via HTTP API"""
            cli_ctx.log("Extracting via HTTP API...", "info")
            response = await cli_ctx.api_client.request(
                "POST", "/api/okh/extract", json_data=request_data
            )
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
                    cli_ctx.log(
                        f"{i}. {req.get('type', 'Unknown')}: {req.get('description', 'No description')}",
                        "info",
                    )
        else:
            cli_ctx.log("No requirements found in manifest", "info")

        cli_ctx.end_command_tracking()

    except Exception as e:
        cli_ctx.log(f"Extraction failed: {str(e)}", "error")
        raise


@okh_group.command()
@click.option("--limit", default=10, help="Maximum number of manifests to list")
@click.option("--offset", default=0, help="Number of manifests to skip")
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
      ohm okh list
      
      # List with pagination
      ohm okh list --limit 20 --offset 10
      
      # Use LLM for enhanced analysis
      ohm okh list --use-llm --limit 50
    """,
    async_cmd=True,
    track_performance=True,
    handle_errors=True,
    format_output=True,
    add_llm_config=True,
)
@click.pass_context
async def list_manifests(
    ctx,
    limit: int,
    offset: int,
    verbose: bool,
    output_format: str,
    use_llm: bool,
    llm_provider: str,
    llm_model: Optional[str],
    quality_level: str,
    strict_mode: bool,
):
    """List stored OKH manifests with enhanced LLM support."""
    cli_ctx = ctx.obj
    cli_ctx.start_command_tracking("okh-list")

    # Update CLI context with parameters from decorator
    cli_ctx.update_llm_config(
        use_llm=use_llm,
        llm_provider=llm_provider,
        llm_model=llm_model,
        quality_level=quality_level,
        strict_mode=strict_mode,
    )

    try:
        # Log LLM usage if enabled
        if cli_ctx.is_llm_enabled():
            log_llm_usage(cli_ctx, "OKH listing")

        async def http_list():
            """List via HTTP API"""
            cli_ctx.log("Listing via HTTP API...", "info")
            params = {"limit": limit, "offset": offset}
            response = await cli_ctx.api_client.request(
                "GET", "/api/okh/", params=params
            )
            return response

        async def fallback_list():
            """List using direct service calls"""
            cli_ctx.log("Using direct service listing...", "info")
            okh_service = await OKHService.get_instance()
            manifests = await okh_service.list_manifests(limit=limit, offset=offset)
            return {
                "manifests": [manifest.to_dict() for manifest in manifests],
                "total": len(manifests),
            }

        # Execute listing with fallback
        command = SmartCommand(cli_ctx)
        result = await command.execute_with_fallback(http_list, fallback_list)

        # Handle both API response format (PaginatedResponse with 'items') and fallback format (with 'manifests')
        # API response may have nested 'data' field or top-level 'items'
        if "data" in result and isinstance(result["data"], dict):
            # Handle nested data structure
            manifests = result["data"].get("items", result["data"].get("manifests", []))
            pagination = result["data"].get("pagination", {})
            total = pagination.get("total_items", len(manifests))
        else:
            # Handle top-level items or manifests
            manifests = result.get("items", result.get("manifests", []))
            pagination = result.get("pagination", {})
            total = pagination.get("total_items", result.get("total", len(manifests)))

        # Display results
        if output_format == "json":
            output_data = format_llm_output(result, cli_ctx)
            click.echo(output_data)
        else:
            # Display manifest list in text format (similar to okw list-files)
            if manifests and len(manifests) > 0:
                click.echo(f"\n📄 Found {total} OKH manifest(s):\n")
                for i, manifest in enumerate(manifests, 1):
                    manifest_id = manifest.get("id", "Unknown")
                    title = manifest.get("title", "Unknown")
                    version = manifest.get("version", "Unknown")
                    organization = manifest.get("organization", {})
                    org_name = (
                        organization.get("name", "Unknown")
                        if isinstance(organization, dict)
                        else str(organization) if organization else "Unknown"
                    )

                    click.echo(f"  {i}. {title}")
                    click.echo(f"     Manifest ID: {manifest_id}")
                    click.echo(f"     Version: {version} | Organization: {org_name}")
                    if i < len(manifests):
                        click.echo()  # Empty line between items
                click.echo(f"\nTotal: {total} manifest(s)")
            elif total > 0:
                # Total indicates there are manifests, but they might be on a different page
                click.echo(
                    f"\n📄 Found {total} OKH manifest(s) (not shown - may be on a different page)\n"
                )
            else:
                click.echo("\nNo OKH manifests found\n")

        cli_ctx.end_command_tracking()

    except Exception as e:
        cli_ctx.log(f"Listing failed: {str(e)}", "error")
        raise


@okh_group.command()
@click.argument("manifest_id", type=str)
@click.option("--force", is_flag=True, help="Force deletion without confirmation")
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
      ohm okh delete 123e4567-e89b-12d3-a456-426614174000
      
      # Force deletion without confirmation
      ohm okh delete 123e4567-e89b-12d3-a456-426614174000 --force
      
      # Use LLM for enhanced analysis
      ohm okh delete 123e4567-e89b-12d3-a456-426614174000 --use-llm
    """,
    async_cmd=True,
    track_performance=True,
    handle_errors=True,
    format_output=True,
    add_llm_config=True,
)
@click.pass_context
async def delete(
    ctx,
    manifest_id: str,
    force: bool,
    verbose: bool,
    output_format: str,
    use_llm: bool,
    llm_provider: str,
    llm_model: Optional[str],
    quality_level: str,
    strict_mode: bool,
):
    """Delete an OKH manifest with enhanced LLM support."""
    cli_ctx = ctx.obj
    cli_ctx.start_command_tracking("okh-delete")

    # Update CLI context with parameters from decorator
    cli_ctx.update_llm_config(
        use_llm=use_llm,
        llm_provider=llm_provider,
        llm_model=llm_model,
        quality_level=quality_level,
        strict_mode=strict_mode,
    )

    try:
        if not force:
            if not click.confirm(
                f"Are you sure you want to delete manifest {manifest_id}?"
            ):
                cli_ctx.log("Deletion cancelled", "info")
                return

        # Log LLM usage if enabled
        if cli_ctx.is_llm_enabled():
            log_llm_usage(cli_ctx, "OKH deletion")

        async def http_delete():
            """Delete via HTTP API"""
            cli_ctx.log("Deleting via HTTP API...", "info")
            response = await cli_ctx.api_client.request(
                "DELETE", f"/api/okh/{manifest_id}"
            )
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
@click.argument("file_path", type=click.Path(exists=True))
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
      ohm okh upload my-project.okh.json
      
      # Upload with premium quality validation
      ohm okh upload my-project.okh.json --quality-level premium --strict-mode
      
      # Use LLM for enhanced processing
      ohm okh upload my-project.okh.json --use-llm --quality-level standard
    """,
    async_cmd=True,
    track_performance=True,
    handle_errors=True,
    format_output=True,
    add_llm_config=True,
)
@click.pass_context
async def upload(
    ctx,
    file_path: str,
    verbose: bool,
    output_format: str,
    use_llm: bool,
    llm_provider: str,
    llm_model: Optional[str],
    quality_level: str,
    strict_mode: bool,
):
    """Upload and validate an OKH manifest file with enhanced LLM support."""
    cli_ctx = ctx.obj
    cli_ctx.start_command_tracking("okh-upload")

    # Update CLI context with parameters from decorator
    cli_ctx.update_llm_config(
        use_llm=use_llm,
        llm_provider=llm_provider,
        llm_model=llm_model,
        quality_level=quality_level,
        strict_mode=strict_mode,
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
                "description": f"Uploaded OKH manifest with {quality_level} validation",
            }

            response = await cli_ctx.api_client.upload_file(
                "POST",
                "/api/okh/upload",
                file_path,
                file_field_name="okh_file",
                form_data=form_data,
            )
            return response

        async def fallback_upload():
            """Fallback upload using direct services"""
            cli_ctx.log("Using direct service upload...", "info")
            with open(file_path, "r") as f:
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
@click.argument("url_or_path", metavar="URL_OR_PATH", type=str)
@click.option(
    "--output",
    "-o",
    type=click.Path(),
    help="Output directory for built files (enables BOM export)",
)
@click.option(
    "--format",
    "-f",
    type=click.Choice(["json", "yaml", "okh", "api"]),
    default="okh",
    help="Output format: okh (OKH manifest), api (API wrapper), json/yaml (legacy)",
)
@click.option(
    "--bom-formats",
    multiple=True,
    type=click.Choice(["json", "md", "csv", "components"]),
    default=["json", "md"],
    help="BOM export formats (only when --output is specified)",
)
@click.option(
    "--unified-bom",
    is_flag=True,
    help="Include full BOM in manifest instead of compressed summary (default: compressed summary)",
)
@click.option(
    "--no-review",
    is_flag=True,
    help="Skip interactive review and generate manifest directly",
)
@click.option(
    "--github-token",
    type=str,
    help="GitHub personal access token (increases rate limit from 60 to 5,000 requests/hour)",
)
@click.option(
    "--clone",
    is_flag=True,
    help="Clone repository locally for extraction (faster, more reliable, eliminates API limits)",
)
@click.option(
    "--save-clone",
    "save_clone",
    type=click.Path(),
    default=None,
    help="Persist the cloned repository to this directory after generation (use with --clone). "
    "Allows subsequent runs to pass the saved path as input instead of re-cloning.",
)
@click.option(
    "--bom-output",
    "bom_output",
    type=click.Path(),
    default=None,
    help="Write the generated BOM to this file path as JSON. "
    "Required when using --json without --output, since the manifest references "
    "an external BOM file but has no output directory to write it to.",
)
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
    - documentation_hohm: Main project documentation (README.md)
    
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
      ohm okh generate-from-url https://github.com/user/project

      # Generate with local cloning (faster, more reliable)
      ohm okh generate-from-url https://github.com/user/project --clone

      # Clone, generate (3-layer), save clone and BOM alongside the manifest
      ohm okh generate-from-url https://github.com/user/project \
        --clone --save-clone ./clones/my-project \
        --bom-output ./clones/my-project-bom.json \
        --format okh --no-review --json > ./clones/my-project.json

      # Generate (4-layer with LLM) from the saved clone — no network required
      ohm okh generate-from-url ./clones/my-project \
        --bom-output ./clones/my-project-4L-bom.json \
        --format okh --no-review --use-llm --json > ./clones/my-project-4L.json

      # Generate with BOM export
      ohm okh generate-from-url https://github.com/user/project --output ./output

      # Use LLM for enhanced generation
      ohm okh generate-from-url https://github.com/user/project --use-llm --quality-level professional
    """,
    async_cmd=True,
    track_performance=True,
    handle_errors=True,
    format_output=True,
    add_llm_config=True,
)
@click.pass_context
async def generate_from_url(
    ctx,
    url_or_path: str,
    output: str,
    format: str,
    bom_formats: tuple,
    unified_bom: bool,
    no_review: bool,
    github_token: str,
    clone: bool,
    save_clone: Optional[str],
    bom_output: Optional[str],
    verbose: bool,
    output_format: str,
    use_llm: bool,
    llm_provider: str,
    llm_model: Optional[str],
    quality_level: str,
    strict_mode: bool,
):
    """Generate OKH manifest from repository URL or local clone path with enhanced LLM support."""
    cli_ctx = ctx.obj
    cli_ctx.start_command_tracking("okh-generate-from-url")

    # Normalise: treat as a plain string throughout; detect local vs remote below
    url = url_or_path

    # Update CLI context with parameters from decorator
    cli_ctx.update_llm_config(
        use_llm=use_llm,
        llm_provider=llm_provider,
        llm_model=llm_model,
        quality_level=quality_level,
        strict_mode=strict_mode,
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
            response = await cli_ctx.api_client.request(
                "POST", "/api/okh/generate-from-url", json_data=payload
            )
            return response

        async def fallback_generate():
            """Generate using direct service calls"""
            from pathlib import Path as _Path

            cli_ctx.log("Using direct service generation...", "info")
            from ..core.generation.engine import GenerationEngine
            from ..core.generation.models import (
                LayerConfig,
                PlatformType,
            )
            from ..core.generation.platforms.github import GitHubExtractor
            from ..core.generation.platforms.gitlab import GitLabExtractor
            from ..core.generation.review import ReviewInterface
            from ..core.generation.url_router import URLRouter

            router = URLRouter()

            # --- Local path input: skip cloning, process directory directly ---
            local_input = _Path(url)
            if local_input.is_dir():
                cli_ctx.log(
                    f"Local path detected — extracting from existing clone: {local_input}",
                    "info",
                )
                from ..core.generation.platforms.local_git import LocalGitExtractor

                extractor = LocalGitExtractor()
                project_data = await extractor.extract_from_local_path(local_input)

            else:
                # --- URL input ---
                if not router.validate_url(url):
                    raise ValueError(f"Invalid URL or path does not exist: {url}")

                platform = router.detect_platform(url)
                if platform is None:
                    raise ValueError(f"Unsupported platform for URL: {url}")

                cli_ctx.log(f"Detected platform: {platform.value}", "info")
                cli_ctx.log("Fetching project data...", "info")

                # Choose extraction method based on clone flag
                use_clone = clone
                if use_clone:
                    cli_ctx.log("Using local Git cloning for extraction...", "info")
                    if not router.supports_local_cloning(url):
                        cli_ctx.log(
                            "Warning: URL doesn't support local cloning, falling back to API extraction",
                            "warning",
                        )
                        use_clone = False
                    else:
                        persist_path = _Path(save_clone) if save_clone else None
                        if persist_path:
                            cli_ctx.log(
                                f"Clone will be saved to: {persist_path}", "info"
                            )
                        generator = router.route_to_local_git_extractor()
                        project_data = await generator.extract_project(
                            url, persist_path=persist_path
                        )

                if not use_clone:
                    if platform == PlatformType.GITHUB:
                        generator = GitHubExtractor(github_token=github_token)
                    elif platform == PlatformType.GITLAB:
                        generator = GitLabExtractor()
                    else:
                        raise ValueError(f"Unsupported platform: {platform}")

                    project_data = await generator.extract_project(url)

            # Generate manifest from project data
            config = LayerConfig()
            config.use_llm = (
                use_llm  # Honour --use-llm flag (off by default = 3-layer mode)
            )
            config.use_bom_normalization = True  # Enable BOM normalization
            engine = GenerationEngine(config=config)
            cli_ctx.log("Generating manifest fields...", "info")

            # Pass verbose flag to control file metadata inclusion
            result = await engine.generate_manifest_async(
                project_data, include_file_metadata=verbose
            )

            if not no_review:
                cli_ctx.log("Starting interactive review...", "info")
                review_interface = ReviewInterface(result)
                result = await review_interface.review()
            return result

        # Store the raw result for BOM export
        raw_result = await fallback_generate()

        # Set unified BOM mode if requested
        if unified_bom and hasattr(raw_result, "unified_bom_mode"):
            raw_result.unified_bom_mode = True

        # Convert to appropriate format
        if format == "okh":
            result = (
                raw_result.to_okh_manifest(include_field_confidence=verbose)
                if hasattr(raw_result, "to_okh_manifest")
                else raw_result
            )
        elif format == "api":
            result = {
                "success": True,
                "message": "Manifest generated successfully",
                "manifest": (
                    raw_result.to_okh_manifest(include_field_confidence=verbose)
                    if hasattr(raw_result, "to_okh_manifest")
                    else raw_result.to_dict()
                ),
                "quality_report": {
                    "overall_quality": raw_result.quality_report.overall_quality,
                    "required_fields_complete": raw_result.quality_report.required_fields_complete,
                    "missing_required_fields": raw_result.quality_report.missing_required_fields,
                    "recommendations": raw_result.quality_report.recommendations,
                },
            }
        else:
            # For json/yaml formats, use to_okh_manifest() to get full OKH structure
            result = (
                raw_result.to_okh_manifest(include_field_confidence=verbose)
                if hasattr(raw_result, "to_okh_manifest")
                else raw_result.to_dict()
            )

        # Handle output
        if output:
            output_path = Path(output)

            # Create output directory if it doesn't exist
            output_path.mkdir(parents=True, exist_ok=True)

            # Export manifest
            manifest_path = output_path / "manifest.okh.json"
            if format == "yaml":
                import yaml

                with open(manifest_path, "w") as f:
                    yaml.dump(result, f, default_flow_style=False)
            else:
                with open(manifest_path, "w") as f:
                    json.dump(result, f, indent=2)

            # Export BOM if available, formats specified, and NOT in unified mode
            if (
                bom_formats
                and raw_result
                and hasattr(raw_result, "full_bom")
                and raw_result.full_bom
                and not getattr(raw_result, "unified_bom_mode", False)
            ):
                try:
                    # Use the full BOM object from the raw result
                    bom = raw_result.full_bom

                    # Export BOM in specified formats
                    exporter = BuiltDirectoryExporter(output_path)
                    await exporter._export_bom_formats(bom)

                    cli_ctx.log(
                        f"✅ Manifest and BOM exported to: {output_path}", "success"
                    )
                    cli_ctx.log(f"📁 BOM formats: {', '.join(bom_formats)}", "info")
                except Exception as e:
                    cli_ctx.log(f"⚠️  BOM export failed: {e}", "warning")
                    cli_ctx.log(f"✅ Manifest saved to: {manifest_path}", "success")
            else:
                if getattr(raw_result, "unified_bom_mode", False):
                    cli_ctx.log(
                        f"✅ Unified manifest (with full BOM) saved to: {manifest_path}",
                        "success",
                    )
                else:
                    cli_ctx.log(f"✅ Manifest saved to: {manifest_path}", "success")
        else:
            if (
                output_format == "json"
                or (cli_ctx and cli_ctx.output_format == "json")
                or format
                in [
                    "json",
                    "api",
                ]
            ):
                output_data = format_llm_output(result, cli_ctx)
                click.echo(output_data)
            else:
                # Show summary for OKH format
                if format == "okh":
                    title = result.get("title", "Unknown")
                    version = result.get("version", "Unknown")
                    quality = result.get("metadata", {}).get("generation_confidence", 0)
                    missing_fields = result.get("metadata", {}).get(
                        "missing_required_fields", []
                    )

                    cli_ctx.log(
                        f"✅ Generated OKH manifest for: {title} v{version}", "success"
                    )
                    cli_ctx.log(f"📊 Generation confidence: {quality:.1%}", "info")

                    if missing_fields:
                        cli_ctx.log(
                            f"⚠️  Missing required fields: {', '.join(missing_fields)}",
                            "warning",
                        )
                else:
                    # Legacy format summary
                    title = result.get("title", "Unknown")
                    version = result.get("version", "Unknown")
                    quality = result.get("quality_report", {}).get("overall_quality", 0)

                    cli_ctx.log(
                        f"✅ Generated manifest for: {title} v{version}", "success"
                    )
                    cli_ctx.log(f"📊 Quality score: {quality:.1%}", "info")

                    if result.get("quality_report", {}).get("missing_required_fields"):
                        missing = result["quality_report"]["missing_required_fields"]
                        cli_ctx.log(
                            f"⚠️  Missing required fields: {', '.join(missing)}",
                            "warning",
                        )

        # Write BOM to disk if requested
        if (
            bom_output
            and hasattr(raw_result, "full_bom")
            and raw_result.full_bom is not None
        ):
            import json as _json
            from pathlib import Path as _Path

            bom_path = _Path(bom_output)
            bom_path.parent.mkdir(parents=True, exist_ok=True)
            bom_dict = (
                raw_result.full_bom.to_dict()
                if hasattr(raw_result.full_bom, "to_dict")
                else raw_result.full_bom
            )
            with open(bom_path, "w") as _f:
                _json.dump(bom_dict, _f, indent=2, default=str)
            click.echo(f"✅ BOM saved to: {bom_path}", err=True)
            # Update external_file reference in the manifest to match actual output path
            if isinstance(result, dict) and isinstance(result.get("bom"), dict):
                result["bom"]["external_file"] = str(bom_path)
        elif bom_output:
            click.echo(
                "⚠️  --bom-output specified but no BOM was generated (try --clone with a well-documented repo)",
                err=True,
            )

        cli_ctx.end_command_tracking()

    except Exception as e:
        cli_ctx.log(f"❌ Generation failed: {str(e)}", "error")
        if cli_ctx and cli_ctx.verbose:
            import traceback

            click.echo(traceback.format_exc())
        raise


@okh_group.command()
@click.option(
    "--output", "-o", type=click.Path(), help="Output file path for the JSON schema"
)
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
      ohm okh export
      
      # Export schema to file
      ohm okh export --output okh-schema.json
      
      # Export with JSON output format
      ohm okh export --output okh-schema.json --json
    """,
    async_cmd=True,
    track_performance=True,
    handle_errors=True,
    format_output=True,
    add_llm_config=False,  # Export doesn't need LLM
)
@click.pass_context
async def export(
    ctx,
    output: Optional[str],
    verbose: bool,
    output_format: str,
    use_llm: bool = False,
    llm_provider: str = "anthropic",
    llm_model: Optional[str] = None,
    quality_level: str = "professional",
    strict_mode: bool = False,
):
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
                "schema_version": schema.get(
                    "$schema", "http://json-schema.org/draft-07/schema#"
                ),
                "model_name": "OKHManifest",
            }

        # Execute export with fallback
        command = SmartCommand(cli_ctx)
        result = await command.execute_with_fallback(http_export, fallback_export)

        # Extract schema from result (API returns "json_schema", fallback returns "schema")
        schema = result.get("json_schema") or result.get("schema", result)

        # Save to file if output specified, otherwise print schema to stdout
        if output:
            output_path = Path(output)
            with open(output_path, "w") as f:
                json.dump(schema, f, indent=2)
            cli_ctx.log(f"✅ Schema exported to: {output_path}", "success")
        else:
            click.echo(json.dumps(schema, indent=2))

        cli_ctx.end_command_tracking()

    except Exception as e:
        cli_ctx.log(f"❌ Export failed: {str(e)}", "error")
        if cli_ctx.verbose:
            import traceback

            click.echo(traceback.format_exc())
        raise


@okh_group.command()
@click.argument("project_name", type=str)
@click.option(
    "--version", default="0.1.0", help="Initial project version (semantic recommended)"
)
@click.option(
    "--organization", help="Optional organization name for future packaging alignment"
)
@click.option(
    "--template-level",
    type=click.Choice(["minimal", "standard", "detailed"]),
    default="standard",
    help="Amount of guidance in stub docs",
)
@click.option(
    "--output-format",
    type=click.Choice(["json", "zip", "filesystem"]),
    default="json",
    help="Output format",
)
@click.option(
    "--output-path",
    type=click.Path(),
    help="Output path (required for filesystem format)",
)
@click.option(
    "--include-examples/--no-examples",
    default=True,
    help="Include sample files/content",
)
@click.option("--okh-version", default="OKH-LOSHv1.0", help="OKH schema version tag")
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
      ohm okh scaffold my-awesohm-project
      
      # Generate with detailed templates and ZIP output
      ohm okh scaffold arduino-sensor --template-level detailed --output-format zip
      
      # Generate to filesystem with custom organization
      ohm okh scaffold microscope-stage --organization "University Lab" --output-format filesystem --output-path ./projects
      
      # Generate minimal scaffold for experienced developers
      ohm okh scaffold quick-prototype --template-level minimal --output-format json
    """,
    epilog="""
    The scaffolded projects are designed to work seamlessly with the OHM ecosystem:
    - Generated manifests can be validated using 'ohm okh validate'
    - Projects can be used as OKH requirements in matching operations
    - The structure supports the OHM generation workflow
    - Projects can be stored and retrieved using OHM storage services
    
    For more information, see the Scaffolding Guide in the documentation.
    """,
)
async def scaffold(
    ctx,
    project_name: str,
    version: str,
    organization: Optional[str],
    template_level: str,
    output_format: str,
    output_path: Optional[str],
    include_examples: bool,
    okh_version: str,
    verbose: bool = False,
    use_llm: bool = False,
    llm_provider: str = "anthropic",
    llm_model: Optional[str] = None,
    quality_level: str = "professional",
    strict_mode: bool = False,
):
    """Generate an OKH project scaffold with documentation stubs and manifest template."""
    cli_ctx = ctx.obj
    cli_ctx.start_command_tracking("okh.scaffold")

    try:
        cli_ctx.log(f"🏗️  Generating OKH project scaffold: {project_name}", "info")

        # Prepare request data
        request_data = {
            "project_name": project_name,
            "version": version,
            "template_level": template_level,
            "output_format": output_format,
            "include_examples": include_examples,
            "okh_version": okh_version,
        }

        # Add optional fields if provided
        if organization:
            request_data["organization"] = organization
        if output_path:
            request_data["output_path"] = str(output_path)

        # Make API request
        data = await cli_ctx.api_client.request(
            method="POST", endpoint="/api/okh/scaffold", json_data=request_data
        )

        # Display success message
        cli_ctx.log(f"✅ Scaffold generated successfully!", "success")

        # Display project information
        if cli_ctx.output_format == "json":
            click.echo(json.dumps(data, indent=2))
        else:
            # Display key information
            click.echo(f"\n📁 Project: {data.get('project_name')}")
            click.echo(f"📋 Template Level: {template_level}")
            click.echo(f"📦 Output Format: {output_format}")

            # Display structure information
            structure = data.get("structure", {})
            if structure:
                project_dir = structure.get(project_name, {})
                if project_dir:
                    click.echo(f"\n📂 Generated Structure:")
                    _display_structure(project_dir, indent=2)

            # Display manifest template information
            manifest_template = data.get("manifest_template", {})
            if manifest_template:
                click.echo(f"\n📄 OKH Manifest Template:")
                click.echo(f"   Title: {manifest_template.get('title', 'N/A')}")
                click.echo(f"   Version: {manifest_template.get('version', 'N/A')}")
                click.echo(f"   OKH Version: {manifest_template.get('okhv', 'N/A')}")
                click.echo(
                    f"   Required Fields: {len([k for k, v in manifest_template.items() if '[REQUIRED]' in str(v)])}"
                )

            # Display output information
            if output_format == "zip" and data.get("download_url"):
                click.echo(f"\n📥 Download URL: {data.get('download_url')}")
            elif output_format == "filesystem" and data.get("filesystem_path"):
                click.echo(f"\n📁 Filesystem Path: {data.get('filesystem_path')}")
            elif output_format == "json":
                click.echo(f"\n💡 Use --json flag to see full structure data")

            # Display next steps
            click.echo(f"\n🚀 Next Steps:")
            click.echo(f"   1. Customize the generated manifest template")
            click.echo(f"   2. Add your hardware designs and documentation")
            click.echo(f"   3. Use 'ohm okh validate' to check OKH compliance")
            click.echo(
                f"   4. Use 'ohm match requirements' to find manufacturing capabilities"
            )

            if template_level in ["standard", "detailed"]:
                click.echo(
                    f"   5. Use 'mkdocs serve' to build professional documentation"
                )

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
            icon = "📄" if name.endswith(".md") else "📄"
            click.echo(f"{prefix}{icon} {name}")


@okh_group.command()
@click.argument("project_path", type=click.Path(exists=True))
@click.option(
    "--apply", is_flag=True, help="Apply cleanup (by default runs as dry-run only)"
)
@click.option(
    "--remove-unmodified-stubs/--keep-unmodified-stubs",
    default=True,
    help="Remove unmodified scaffolding stubs",
)
@click.option(
    "--remove-empty-directories/--keep-empty-directories",
    default=True,
    help="Remove empty directories after cleanup",
)
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
      ohm okh scaffold-cleanup ./projects/my-project
      
      # Apply cleanup changes
      ohm okh scaffold-cleanup ./projects/my-project --apply
      
      # Keep empty directories
      ohm okh scaffold-cleanup ./projects/my-project --apply --keep-empty-directories
    """,
    track_performance=True,
    handle_errors=True,
    format_output=True,
)
async def scaffold_cleanup(
    ctx,
    project_path: str,
    apply: bool,
    remove_unmodified_stubs: bool,
    remove_empty_directories: bool,
    verbose: bool,
    output_format: str,
    use_llm: bool = False,
    llm_provider: str = "anthropic",
    llm_model: Optional[str] = None,
    quality_level: str = "professional",
    strict_mode: bool = False,
):
    """Cleanup OKH scaffold directory by removing unmodified stubs and empty folders."""
    cli_ctx = ctx.obj
    cli_ctx.start_command_tracking("okh.scaffold-cleanup")

    try:
        cli_ctx.log(f"🧹 Cleaning OKH scaffold at: {project_path}", "info")

        payload = {
            "project_path": str(project_path),
            "remove_unmodified_stubs": bool(remove_unmodified_stubs),
            "remove_empty_directories": bool(remove_empty_directories),
            "dry_run": (not apply),
        }

        data = await cli_ctx.api_client.request(
            method="POST", endpoint="/api/okh/scaffold/cleanup", json_data=payload
        )

        # Output
        if cli_ctx.output_format == "json":
            click.echo(json.dumps(data, indent=2))
        else:
            removed_files = data.get("removed_files", [])
            removed_dirs = data.get("removed_directories", [])
            bytes_saved = data.get("bytes_saved", 0)
            dry_run = payload["dry_run"]

            cli_ctx.log(
                "✅ Dry run completed" if dry_run else "✅ Cleanup completed", "success"
            )
            if removed_files:
                click.echo(
                    f"\n🗑️  Files to remove ({len(removed_files)}):"
                    if dry_run
                    else f"\n🗑️  Files removed ({len(removed_files)}):"
                )
                for f in removed_files:
                    click.echo(f"   - {f}")
            if removed_dirs:
                click.echo(
                    f"\n📁 Empty directories to remove ({len(removed_dirs)}):"
                    if dry_run
                    else f"\n📁 Empty directories removed ({len(removed_dirs)}):"
                )
                for d in removed_dirs:
                    click.echo(f"   - {d}")
            if not dry_run:
                click.echo(f"\n💾 Bytes saved: {bytes_saved}")

            warnings = data.get("warnings", [])
            if warnings:
                # Separate broken link warnings from other warnings
                broken_link_warnings = [
                    w
                    for w in warnings
                    if "Broken link" in w or "broken link" in w.lower()
                ]
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


@okh_group.command()
@click.argument("manifest_file", type=click.Path(exists=True))
@click.option(
    "--output",
    "-o",
    type=click.Path(),
    help="Output file path (default: overwrites input file)",
)
@click.option("--dry-run", is_flag=True, help="Preview fixes without applying them")
@click.option(
    "--backup", is_flag=True, help="Create backup of original file before fixing"
)
@click.option(
    "--confidence-threshold",
    type=float,
    default=0.7,
    help="Minimum confidence to apply a fix (0.0-1.0, default: 0.7)",
)
@click.option(
    "--domain",
    type=click.Choice(["manufacturing", "cooking"]),
    help="Domain override (auto-detected from file if not provided)",
)
@click.option(
    "--yes",
    "-y",
    is_flag=True,
    help="Automatically confirm all fixes without prompting",
)
@standard_cli_command(
    help_text="""
    Automatically fix validation warnings and errors in an OKH manifest.
    
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
      ohm okh fix recipe.json --dry-run
      
      # Apply fixes with backup
      ohm okh fix recipe.json --backup
      
      # Apply fixes to new file
      ohm okh fix recipe.json --output recipe-fixed.json
      
      # Apply all fixes including low-confidence ones
      ohm okh fix recipe.json --confidence-threshold 0.5 --yes
      
      # Fix with domain override
      ohm okh fix recipe.json --domain cooking
    """,
    async_cmd=True,
    track_performance=True,
    handle_errors=True,
    format_output=True,
    add_llm_config=False,  # Auto-fix doesn't use LLM
)
@click.pass_context
async def fix(
    ctx,
    manifest_file: str,
    output: Optional[str],
    dry_run: bool,
    backup: bool,
    confidence_threshold: float,
    domain: Optional[str],
    yes: bool,
    verbose: bool,
    output_format: str,
    quality_level: str,
    strict_mode: bool,
    use_llm: bool = False,
    llm_provider: str = "anthropic",
    llm_model: Optional[str] = None,
):
    """Automatically fix validation issues in an OKH manifest."""
    cli_ctx = ctx.obj
    cli_ctx.start_command_tracking("okh-fix")
    cli_ctx.verbose = verbose
    cli_ctx.config.verbose = verbose

    try:
        # Read manifest file
        manifest_data = await _read_manifest_file(manifest_file)

        # Detect domain if not provided
        detected_domain = domain
        if not detected_domain:
            if "domain" in manifest_data and manifest_data["domain"]:
                detected_domain = manifest_data["domain"]
            elif "making_instructions" in manifest_data or "tool_list" in manifest_data:
                detected_domain = "cooking"
            else:
                detected_domain = "manufacturing"

        cli_ctx.log(f"Using domain: {detected_domain}", "info")

        # Validate first to get warnings/errors
        cli_ctx.log("Validating manifest...", "info")
        validation_result = validate_okh_manifest(
            manifest_data,
            quality_level=quality_level,
            strict_mode=strict_mode,
            domain=detected_domain,
        )

        if not validation_result.warnings and not validation_result.errors:
            cli_ctx.log("✅ No issues found. Manifest is already valid!", "success")
            cli_ctx.end_command_tracking()
            return

        cli_ctx.log(
            f"Found {len(validation_result.warnings)} warnings and {len(validation_result.errors)} errors",
            "info",
        )

        # Run auto-fix
        cli_ctx.log("Analyzing fixes...", "info")
        fixed_content, fix_report = auto_fix_okh_manifest(
            manifest_data,
            validation_result,
            quality_level=quality_level,
            strict_mode=strict_mode,
            domain=detected_domain,
            dry_run=dry_run,
            fix_confidence_threshold=confidence_threshold,
        )

        # Display fix report
        cli_ctx.log("\n" + "=" * 70, "info")
        cli_ctx.log("AUTO-FIX REPORT", "info")
        cli_ctx.log("=" * 70, "info")
        cli_ctx.log(f"Fixes applied: {len(fix_report.fixes_applied)}", "info")
        cli_ctx.log(f"Fixes skipped: {len(fix_report.fixes_skipped)}", "info")
        cli_ctx.log(f"Original warnings: {fix_report.original_warnings}", "info")
        cli_ctx.log(f"Remaining warnings: {fix_report.remaining_warnings}", "info")
        cli_ctx.log(
            f"Warnings fixed: {fix_report.original_warnings - fix_report.remaining_warnings}",
            "success",
        )

        if fix_report.fixes_applied:
            cli_ctx.log("\nApplied fixes:", "info")
            for i, fix in enumerate(fix_report.fixes_applied, 1):
                cli_ctx.log(f"  {i}. [{fix.type}] {fix.description}", "success")

        if fix_report.fixes_skipped:
            cli_ctx.log(
                "\nSkipped fixes (low confidence or require confirmation):", "warning"
            )
            for i, fix in enumerate(fix_report.fixes_skipped, 1):
                cli_ctx.log(
                    f"  {i}. [{fix.type}] {fix.description} (confidence: {fix.confidence})",
                    "warning",
                )

            # Ask for confirmation on low-confidence fixes
            if not dry_run and not yes and fix_report.fixes_skipped:
                low_confidence_fixes = [
                    f
                    for f in fix_report.fixes_skipped
                    if f.confidence < confidence_threshold
                ]
                if low_confidence_fixes:
                    cli_ctx.log(
                        f"\n⚠️  {len(low_confidence_fixes)} fixes require confirmation (confidence < {confidence_threshold})",
                        "warning",
                    )
                    if click.confirm("Apply low-confidence fixes?"):
                        # Apply only the skipped fixes to the already-fixed content
                        # We need to re-validate first to get updated warnings
                        temp_validation = validate_okh_manifest(
                            fixed_content,
                            quality_level=quality_level,
                            strict_mode=strict_mode,
                            domain=detected_domain,
                        )
                        # Re-run auto-fix on the already-fixed content with lower threshold
                        fixed_content, additional_fix_report = auto_fix_okh_manifest(
                            fixed_content,
                            temp_validation,
                            quality_level=quality_level,
                            strict_mode=strict_mode,
                            domain=detected_domain,
                            dry_run=False,
                            fix_confidence_threshold=0.5,  # Lower threshold for user-confirmed fixes
                        )
                        # Update the fix report with additional fixes
                        additional_count = len(additional_fix_report.fixes_applied)
                        fix_report.fixes_applied.extend(
                            additional_fix_report.fixes_applied
                        )
                        fix_report.fixes_skipped = additional_fix_report.fixes_skipped
                        fix_report.remaining_warnings = (
                            additional_fix_report.remaining_warnings
                        )
                        fix_report.remaining_errors = (
                            additional_fix_report.remaining_errors
                        )
                        cli_ctx.log(
                            f"Applied {additional_count} additional fixes", "success"
                        )

        if dry_run:
            cli_ctx.log("\n🔍 DRY-RUN MODE: No changes were made", "info")
            cli_ctx.log("Run without --dry-run to apply fixes", "info")
        else:
            # Determine output file
            output_file = output or manifest_file

            # Create backup if requested
            if backup and output_file == manifest_file:
                backup_file = f"{manifest_file}.backup"
                import shutil

                shutil.copy2(manifest_file, backup_file)
                cli_ctx.log(f"Created backup: {backup_file}", "info")

            # Write fixed content
            output_path = Path(output_file)
            with open(output_path, "w") as f:
                json.dump(fixed_content, f, indent=2, ensure_ascii=False)

            cli_ctx.log(f"\n✅ Fixed manifest saved to: {output_file}", "success")

            # Re-validate to show final state
            final_validation = validate_okh_manifest(
                fixed_content,
                quality_level=quality_level,
                strict_mode=strict_mode,
                domain=detected_domain,
            )

            if final_validation.warnings or final_validation.errors:
                cli_ctx.log(
                    f"\n⚠️  Remaining issues: {len(final_validation.warnings)} warnings, {len(final_validation.errors)} errors",
                    "warning",
                )
            else:
                cli_ctx.log(
                    "\n✅ All issues resolved! Manifest is now valid.", "success"
                )

        cli_ctx.end_command_tracking()

    except Exception as e:
        cli_ctx.log(f"Fix failed: {str(e)}", "error")
        raise


@okh_group.command(name="template")
@click.option("--output", "-o", type=click.Path(), help="Save template to file")
@click.option(
    "--output-format",
    default="json",
    type=click.Choice(["json", "toml"]),
    help="Output format",
)
@click.pass_context
def okh_template(ctx, output: Optional[str], output_format: str):
    """Output a blank OKH manifest template.

    Generates a complete, empty OKH manifest with all fields shown at their
    default/null values. Fill in the blanks and use ``ohm okh validate`` to
    check the result.

    \b
    Examples:
      # Print template to stdout
      ohm okh template

      # Save template to file
      ohm okh template --output my-project.okh.json
    """
    from ..core.utils.template_builder import okh_blank_template, strip_none_for_toml

    template = okh_blank_template()

    if output_format == "toml":
        try:
            import tomli_w

            content = tomli_w.dumps(strip_none_for_toml(template))
        except ImportError:
            click.echo(
                "Error: tomli_w is required for TOML output. Install it with: pip install tomli_w",
                err=True,
            )
            raise SystemExit(1)
        output_bytes = content.encode("utf-8")
        if output:
            Path(output).write_bytes(output_bytes)
            click.echo(f"Template saved to: {output}")
        else:
            click.echo(content)
    else:
        content = json.dumps(template, indent=2, default=str)
        if output:
            Path(output).write_text(content)
            click.echo(f"Template saved to: {output}")
        else:
            click.echo(content)


@okh_group.command(name="create-interactive")
@click.option(
    "--output", "-o", type=click.Path(), help="Save result to file instead of storing"
)
@click.option(
    "--store/--no-store",
    default=True,
    help="Store the manifest after creation (default: true)",
)
@click.option(
    "--output-format",
    default="text",
    type=click.Choice(["text", "json"]),
    help="Output format",
)
@click.pass_context
def create_interactive(ctx, output: Optional[str], store: bool, output_format: str):
    """Interactively create an OKH manifest.

    Prompts for required fields, then optional fields (press Enter to skip any
    optional field). The resulting manifest is saved to a file or stored.

    \b
    Examples:
      # Create and store a manifest interactively
      ohm okh create-interactive

      # Create and save to file (without storing)
      ohm okh create-interactive --no-store --output my-manifest.toml
    """
    import asyncio

    from ..core.models.okh import OKHManifest
    from ..core.services.okh_service import OKHService

    cli_ctx = ctx.obj

    click.echo("\n=== OKH Manifest Interactive Creator ===")
    click.echo(
        "Required fields are marked [required]. Press Enter to skip optional fields.\n"
    )

    # --- Required fields ---
    title = click.prompt("Project title [required]")
    version = click.prompt("Version (e.g. 1.0.0) [required]")
    documentation_language = click.prompt(
        "Documentation language [required]", default="en"
    )
    function = click.prompt("Function / purpose [required]")
    licensor_name = click.prompt("Licensor (name) [required]")
    click.echo("Common licenses: MIT, Apache-2.0, GPL-3.0, CC-BY-4.0, CERN-OHL-S-2.0")
    hardware_license = click.prompt("Hardware license [required]")

    # --- Optional fields ---
    click.echo("\n--- Optional fields (Enter to skip) ---")
    repo = click.prompt("Repository URL", default="", show_default=False) or None
    description = click.prompt("Description", default="", show_default=False) or None
    documentation_license = (
        click.prompt("Documentation license", default="", show_default=False) or None
    )
    software_license = (
        click.prompt("Software license", default="", show_default=False) or None
    )
    org_name = click.prompt("Organisation name", default="", show_default=False) or None
    keywords_raw = click.prompt(
        "Keywords (comma-separated)", default="", show_default=False
    )
    keywords = (
        [k.strip() for k in keywords_raw.split(",") if k.strip()]
        if keywords_raw
        else []
    )

    # Build the manifest dict
    license_dict: dict = {"hardware": hardware_license}
    if documentation_license:
        license_dict["documentation"] = documentation_license
    if software_license:
        license_dict["software"] = software_license

    manifest_dict: dict = {
        "title": title,
        "version": version,
        "documentation_language": documentation_language,
        "function": function,
        "licensor": licensor_name,
        "license": license_dict,
    }
    if repo:
        manifest_dict["repo"] = repo
    if description:
        manifest_dict["description"] = description
    if org_name:
        manifest_dict["organisation"] = org_name
    if keywords:
        manifest_dict["keywords"] = keywords

    click.echo("\n=== Review ===")
    click.echo(json.dumps(manifest_dict, indent=2))

    if not click.confirm("\nSave this manifest?", default=True):
        click.echo("Cancelled.")
        return

    # Save to file if requested
    if output:
        output_path = Path(output)
        with open(output_path, "w") as f:
            json.dump(manifest_dict, f, indent=2)
        click.echo(f"Manifest saved to: {output_path}")

    # Store via API/service if requested
    if store:

        async def _store():
            async def http_create():
                response = await cli_ctx.api_client.request(
                    "POST", "/api/okh/create", json_data={"content": manifest_dict}
                )
                return response

            async def fallback_create():
                okh_manifest = OKHManifest.from_dict(manifest_dict)
                okh_service = await OKHService.get_instance()
                result = await okh_service.create(okh_manifest)
                return (
                    result.to_dict()
                    if hasattr(result, "to_dict")
                    else {"success": True, "manifest": result}
                )

            command = SmartCommand(cli_ctx)
            return await command.execute_with_fallback(http_create, fallback_create)

        try:
            result = asyncio.get_event_loop().run_until_complete(_store())
            if output_format == "json":
                click.echo(json.dumps(result, indent=2, default=str))
            else:
                manifest_id = result.get("id") or result.get("manifest_id", "unknown")
                click.echo(f"✅ Manifest created and stored (id: {manifest_id})")
        except Exception as e:
            click.echo(f"❌ Failed to store manifest: {str(e)}", err=True)
