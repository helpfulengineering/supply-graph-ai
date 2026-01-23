"""
Package management commands for OHM CLI

This module provides commands for building, managing, and deploying OKH packages.
"""

import json
from pathlib import Path
from typing import Optional
from uuid import UUID

import click
import yaml

from ..config import settings
from ..core.models.okh import OKHManifest
from ..core.models.package import BuildOptions
from ..core.packaging.remote_storage import PackageRemoteStorage
from ..core.services.package_service import PackageService
from ..core.services.storage_service import StorageService
from .base import (
    CLIContext,
    SmartCommand,
    create_llm_request_data,
    format_llm_output,
    log_llm_usage,
)
from .decorators import standard_cli_command


@click.group()
def package_group():
    """
    OKH Package Management Commands.

    These commands help you build, manage, and deploy OKH packages,
    including package creation, verification, remote storage operations,
    and package lifecycle management.

    Examples:
      # Build a package from manifest
      ohm package build my-project.okh.json

      # List all built packages
      ohm package list

      # Push package to remote storage
      ohm package push my-project 1.0.0

      # Use LLM for enhanced processing
      ohm package build my-project.okh.json --use-llm --quality-level professional
    """
    pass


# Helper functions


async def _read_manifest_file(file_path: str) -> dict:
    """Read and parse manifest file."""
    manifest_path = Path(file_path)

    try:
        with open(manifest_path, "r") as f:
            if manifest_path.suffix.lower() in [".yaml", ".yml"]:
                return yaml.safe_load(f)
            else:
                return json.load(f)
    except Exception as e:
        raise click.ClickException(f"Failed to read manifest file: {str(e)}")


async def _display_build_results(cli_ctx: CLIContext, result: dict, output_format: str):
    """Display build results."""
    if result.get("status") == "success":
        # Fix: Handle API response format (data.package) and fallback format (metadata)
        metadata = (
            result.get("data", {}).get("package")
            or result.get("package")
            or result.get("metadata", {})
        )

        # Fix: Extract package name from available fields
        package_name = (
            metadata.get("package_name")
            or metadata.get("name")
            or metadata.get("title")
            or metadata.get("id")
            or "Unknown"
        )

        cli_ctx.log(f"Package built successfully: {package_name}", "success")

        if output_format == "json":
            output_data = format_llm_output(result, cli_ctx)
            click.echo(output_data)
        else:
            cli_ctx.log(f"📦 Package: {package_name}", "info")
            cli_ctx.log(
                f"📁 Location: {metadata.get('package_path', 'Unknown')}", "info"
            )
            cli_ctx.log(f"📄 Files: {metadata.get('total_files', 0)}", "info")
            cli_ctx.log(
                f"💾 Size: {metadata.get('total_size_bytes', 0):,} bytes", "info"
            )
    else:
        cli_ctx.log("Failed to build package", "error")


async def _display_verification_results(
    cli_ctx: CLIContext,
    result: dict,
    package_name: str,
    version: str,
    output_format: str,
):
    """Display verification results."""
    verification = result.get("verification", {})
    is_valid = verification.get("valid", False)

    if is_valid:
        cli_ctx.log(f"Package {package_name}:{version} is valid", "success")
    else:
        cli_ctx.log(f"Package {package_name}:{version} verification failed", "error")

    if output_format == "json":
        output_data = format_llm_output(result, cli_ctx)
        click.echo(output_data)
    else:
        if verification.get("missing_files"):
            cli_ctx.log(f"Missing files: {len(verification['missing_files'])}", "error")
            for file in verification["missing_files"]:
                cli_ctx.log(f"  ❌ {file}", "error")

        if verification.get("extra_files"):
            cli_ctx.log(f"Extra files: {len(verification['extra_files'])}", "warning")
            for file in verification["extra_files"]:
                cli_ctx.log(f"  ⚠️  {file}", "warning")


# Commands


@package_group.command()
@click.argument("manifest_file", type=click.Path(exists=True))
@click.option("--output-dir", "-o", help="Output directory for built packages")
@click.option("--no-design-files", is_flag=True, help="Exclude design files")
@click.option(
    "--no-manufacturing-files", is_flag=True, help="Exclude manufacturing files"
)
@click.option(
    "--no-making-instructions", is_flag=True, help="Exclude making instructions"
)
@click.option("--no-software", is_flag=True, help="Exclude software")
@click.option("--no-parts", is_flag=True, help="Exclude parts")
@click.option(
    "--no-operating-instructions", is_flag=True, help="Exclude operating instructions"
)
@click.option(
    "--no-quality-instructions",
    is_flag=True,
    help="Exclude technical specifications (includes quality instructions)",
)
@click.option("--no-risk-assessment", is_flag=True, help="Exclude risk assessment")
@click.option("--no-schematics", is_flag=True, help="Exclude schematics")
@click.option(
    "--no-tool-settings",
    is_flag=True,
    help="Exclude making instructions (includes tool settings)",
)
@click.option("--no-verify", is_flag=True, help="Skip download verification")
@click.option("--max-concurrent", default=5, help="Maximum concurrent downloads")
@standard_cli_command(
    help_text="""
    Build an OKH package from a manifest file.
    
    This command creates a complete OKH package by downloading and organizing
    all the files referenced in the manifest according to the OKH specification.
    
    The build process includes:
    - Downloading all referenced files and resources
    - Organizing files according to OKH directory structure
    - Validating file integrity and completeness
    - Creating package metadata and manifest
    - Generating package verification checksums
    
    When LLM is enabled, building includes:
    - Enhanced file analysis and organization
    - Intelligent dependency resolution
    - Quality assessment of package contents
    - Suggestions for package optimization
    """,
    epilog="""
    Examples:
      # Build a complete package
      ohm package build my-project.okh.json
      
      # Build with custom output directory
      ohm package build my-project.okh.json --output-dir ./packages
      
      # Build excluding certain file types
      ohm package build my-project.okh.json --no-software --no-parts
      
      # Use LLM for enhanced processing
      ohm package build my-project.okh.json --use-llm --quality-level professional
    """,
    async_cmd=True,
    track_performance=True,
    handle_errors=True,
    format_output=True,
    add_llm_config=True,
)
@click.pass_context
async def build(
    ctx,
    manifest_file: str,
    output_dir: Optional[str],
    verbose: bool,
    output_format: str,
    use_llm: bool,
    llm_provider: str,
    llm_model: Optional[str],
    quality_level: str,
    strict_mode: bool,
    **kwargs,
):
    """Build an OKH package from a manifest file with enhanced LLM support."""
    cli_ctx = ctx.obj
    cli_ctx.start_command_tracking("package-build")

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

        # Create build options
        options = BuildOptions(
            output_dir=output_dir or "packages",
            include_design_files=not kwargs.get("no_design_files", False),
            include_manufacturing_files=not kwargs.get("no_manufacturing_files", False),
            include_making_instructions=not kwargs.get("no_making_instructions", False),
            include_software=not kwargs.get("no_software", False),
            include_parts=not kwargs.get("no_parts", False),
            include_operating_instructions=not kwargs.get(
                "no_operating_instructions", False
            ),
            include_quality_instructions=not kwargs.get(
                "no_quality_instructions", False
            ),
            include_risk_assessment=not kwargs.get("no_risk_assessment", False),
            include_schematics=not kwargs.get("no_schematics", False),
            include_tool_settings=not kwargs.get("no_tool_settings", False),
            verify_downloads=not kwargs.get("no_verify", True),
            max_concurrent_downloads=kwargs.get("max_concurrent", 5),
        )

        # Create request data with LLM configuration
        request_data = create_llm_request_data(
            cli_ctx, {"manifest_data": manifest_data, "options": options.to_dict()}
        )

        # Log LLM usage if enabled
        if cli_ctx.is_llm_enabled():
            log_llm_usage(cli_ctx, "Package building")

        async def http_build():
            """Build via HTTP API"""
            cli_ctx.log("Building via HTTP API...", "info")
            response = await cli_ctx.api_client.request(
                "POST", "/api/package/build", json_data=request_data
            )
            return response

        async def fallback_build():
            """Build using direct service calls"""
            cli_ctx.log("Using direct service building...", "info")
            manifest = OKHManifest.from_dict(manifest_data)
            package_service = await PackageService.get_instance()
            metadata = await package_service.build_package_from_manifest(
                manifest, options
            )
            return {
                "status": "success",
                "message": "Package built successfully",
                "metadata": metadata.to_dict(),
            }

        # Execute build with fallback
        command = SmartCommand(cli_ctx)
        result = await command.execute_with_fallback(http_build, fallback_build)

        # Display build results
        await _display_build_results(cli_ctx, result, output_format)

        cli_ctx.end_command_tracking()

    except Exception as e:
        cli_ctx.log(f"Build failed: {str(e)}", "error")
        raise


@package_group.command()
@click.argument("manifest_id")
@click.option("--output-dir", "-o", help="Output directory for built packages")
@click.option("--no-design-files", is_flag=True, help="Exclude design files")
@click.option(
    "--no-manufacturing-files", is_flag=True, help="Exclude manufacturing files"
)
@click.option(
    "--no-making-instructions", is_flag=True, help="Exclude making instructions"
)
@click.option("--no-software", is_flag=True, help="Exclude software")
@click.option("--no-parts", is_flag=True, help="Exclude parts")
@click.option(
    "--no-operating-instructions", is_flag=True, help="Exclude operating instructions"
)
@click.option(
    "--no-quality-instructions",
    is_flag=True,
    help="Exclude technical specifications (includes quality instructions)",
)
@click.option("--no-risk-assessment", is_flag=True, help="Exclude risk assessment")
@click.option("--no-schematics", is_flag=True, help="Exclude schematics")
@click.option(
    "--no-tool-settings",
    is_flag=True,
    help="Exclude making instructions (includes tool settings)",
)
@click.option("--no-verify", is_flag=True, help="Skip download verification")
@click.option("--max-concurrent", default=5, help="Maximum concurrent downloads")
@standard_cli_command(
    help_text="""
    Build an OKH package from a stored manifest.
    
    This command creates a complete OKH package by retrieving a previously
    stored manifest and building the package according to the OKH specification.
    
    When LLM is enabled, building includes:
    - Enhanced manifest analysis and optimization
    - Intelligent dependency resolution
    - Quality assessment of package contents
    - Suggestions for package improvement
    """,
    epilog="""
    Examples:
      # Build from stored manifest
      ohm package build-from-storage 123e4567-e89b-12d3-a456-426614174000
      
      # Build with custom options
      ohm package build-from-storage 123e4567-e89b-12d3-a456-426614174000 --no-software
      
      # Use LLM for enhanced processing
      ohm package build-from-storage 123e4567-e89b-12d3-a456-426614174000 --use-llm
    """,
    async_cmd=True,
    track_performance=True,
    handle_errors=True,
    format_output=True,
    add_llm_config=True,
)
@click.pass_context
async def build_from_storage(
    ctx,
    manifest_id: str,
    output_dir: Optional[str],
    verbose: bool,
    output_format: str,
    use_llm: bool,
    llm_provider: str,
    llm_model: Optional[str],
    quality_level: str,
    strict_mode: bool,
    **kwargs,
):
    """Build an OKH package from a stored manifest with enhanced LLM support."""
    cli_ctx = ctx.obj
    cli_ctx.start_command_tracking("package-build-from-storage")

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
        # Create build options
        options = BuildOptions(
            output_dir=output_dir or "packages",
            include_design_files=not kwargs.get("no_design_files", False),
            include_manufacturing_files=not kwargs.get("no_manufacturing_files", False),
            include_making_instructions=not kwargs.get("no_making_instructions", False),
            include_software=not kwargs.get("no_software", False),
            include_parts=not kwargs.get("no_parts", False),
            include_operating_instructions=not kwargs.get(
                "no_operating_instructions", False
            ),
            include_quality_instructions=not kwargs.get(
                "no_quality_instructions", False
            ),
            include_risk_assessment=not kwargs.get("no_risk_assessment", False),
            include_schematics=not kwargs.get("no_schematics", False),
            include_tool_settings=not kwargs.get("no_tool_settings", False),
            verify_downloads=not kwargs.get("no_verify", True),
            max_concurrent_downloads=kwargs.get("max_concurrent", 5),
        )

        # Create request data with LLM configuration
        request_data = create_llm_request_data(cli_ctx, {"options": options.to_dict()})

        # Log LLM usage if enabled
        if cli_ctx.is_llm_enabled():
            log_llm_usage(cli_ctx, "Package building from storage")

        async def http_build_from_storage():
            """Build from storage via HTTP API"""
            cli_ctx.log("Building from storage via HTTP API...", "info")
            response = await cli_ctx.api_client.request(
                "POST", f"/api/package/build/{manifest_id}", json_data=request_data
            )
            return response

        async def fallback_build_from_storage():
            """Build from storage using direct service calls"""
            cli_ctx.log("Using direct service building from storage...", "info")
            package_service = await PackageService.get_instance()
            metadata = await package_service.build_package_from_storage(
                UUID(manifest_id), options
            )
            return {
                "status": "success",
                "message": "Package built successfully",
                "metadata": metadata.to_dict(),
            }

        # Execute build with fallback
        command = SmartCommand(cli_ctx)
        result = await command.execute_with_fallback(
            http_build_from_storage, fallback_build_from_storage
        )

        # Display build results
        await _display_build_results(cli_ctx, result, output_format)

        cli_ctx.end_command_tracking()

    except Exception as e:
        cli_ctx.log(f"Build from storage failed: {str(e)}", "error")
        raise


@package_group.command()
@standard_cli_command(
    help_text="""
    List all built packages in the system.
    
    This command displays information about all packages that have been
    built and are available in the local package storage.
    
    When LLM is enabled, listing includes:
    - Enhanced package analysis and categorization
    - Quality assessment of built packages
    - Intelligent filtering and sorting suggestions
    - Advanced metadata extraction
    """,
    epilog="""
    Examples:
      # List all packages
      ohm package list
      
      # Use LLM for enhanced analysis
      ohm package list --use-llm
    """,
    async_cmd=True,
    track_performance=True,
    handle_errors=True,
    format_output=True,
    add_llm_config=True,
)
@click.pass_context
async def list_packages(
    ctx,
    verbose: bool,
    output_format: str,
    use_llm: bool,
    llm_provider: str,
    llm_model: Optional[str],
    quality_level: str,
    strict_mode: bool,
):
    """List all built packages with enhanced LLM support."""
    cli_ctx = ctx.obj
    cli_ctx.start_command_tracking("package-list")

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
            log_llm_usage(cli_ctx, "Package listing")

        async def http_list():
            """List via HTTP API"""
            cli_ctx.log("Listing via HTTP API...", "info")
            response = await cli_ctx.api_client.request("GET", "/api/package/list")
            return response

        async def fallback_list():
            """List using direct service calls"""
            cli_ctx.log("Using direct service listing...", "info")
            package_service = await PackageService.get_instance()
            packages = await package_service.list_built_packages()
            return {
                "status": "success",
                "packages": [pkg.to_dict() for pkg in packages],
                "total": len(packages),
            }

        # Execute listing with fallback
        command = SmartCommand(cli_ctx)
        result = await command.execute_with_fallback(http_list, fallback_list)

        # Display listing results
        # Fix: Handle both API response format (items) and fallback format (packages)
        if "items" in result:
            packages = result.get("items", [])
            total = result.get("pagination", {}).get("total_items", len(packages))
        else:
            packages = result.get("packages", [])
            total = result.get("total", len(packages))

        if packages:
            cli_ctx.log(f"Found {total} built packages", "success")

            if output_format == "json":
                output_data = format_llm_output(result, cli_ctx)
                click.echo(output_data)
            else:
                for pkg in packages:
                    package_name = pkg.get("package_name", "Unknown")
                    version = pkg.get("version", "Unknown")
                    click.echo(f"📦 {package_name}")
                    click.echo(f"   📌 Version: {version}")
                    click.echo(f"   📁 {pkg.get('package_path', 'Unknown')}")
                    cli_ctx.log(
                        f"   📄 {pkg.get('total_files', 0)} files, {pkg.get('total_size_bytes', 0):,} bytes",
                        "info",
                    )
                    cli_ctx.log(
                        f"   🕒 Built: {pkg.get('build_timestamp', 'Unknown')}", "info"
                    )
                    cli_ctx.log("", "info")  # Empty line for spacing
        else:
            cli_ctx.log("No packages found", "info")

        cli_ctx.end_command_tracking()

    except Exception as e:
        cli_ctx.log(f"Listing failed: {str(e)}", "error")
        raise


@package_group.command()
@click.argument("package_name", type=str, metavar="PACKAGE_NAME")
@click.argument("version", type=str, metavar="VERSION")
@standard_cli_command(
    help_text="""
    Verify a package's integrity and completeness.
    
    This command performs verification of a built package,
    checking file integrity, completeness, and compliance with the
    OKH specification.
    
    **Arguments:**
    - PACKAGE_NAME: Package name in format "org/project" (e.g., "fourthievesvinegar/solderless-microlab")
    - VERSION: Package version (e.g., "1.0.0")
    
    Use 'ohm package list-packages' to see available packages and their versions.
    
    When LLM is enabled, verification includes:
    - Enhanced integrity analysis and validation
    - Quality assessment of package contents
    - Suggestions for package improvement
    - Advanced compliance checking
    """,
    epilog="""
    Examples:
      # Verify a package
      ohm package verify fourthievesvinegar/solderless-microlab 1.0.0
      
      # Use LLM for enhanced verification
      ohm package verify fourthievesvinegar/solderless-microlab 1.0.0 --use-llm
    """,
    async_cmd=True,
    track_performance=True,
    handle_errors=True,
    format_output=True,
    add_llm_config=True,
)
@click.pass_context
async def verify(
    ctx,
    package_name: str,
    version: str,
    verbose: bool,
    output_format: str,
    use_llm: bool,
    llm_provider: str,
    llm_model: Optional[str],
    quality_level: str,
    strict_mode: bool,
):
    """Verify a package's integrity with enhanced LLM support."""
    cli_ctx = ctx.obj
    cli_ctx.start_command_tracking("package-verify")

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
        # Log LLM usage if enabled
        if cli_ctx.is_llm_enabled():
            log_llm_usage(cli_ctx, "Package verification")

        async def http_verify():
            """Verify via HTTP API"""
            cli_ctx.log("Verifying via HTTP API...", "info")
            response = await cli_ctx.api_client.request(
                "GET", f"/api/package/{package_name}/{version}/verify"
            )
            return response

        async def fallback_verify():
            """Verify using direct service calls"""
            cli_ctx.log("Using direct service verification...", "info")
            package_service = await PackageService.get_instance()
            results = await package_service.verify_package(package_name, version)
            return {"status": "success", "verification": results}

        # Execute verification with fallback
        command = SmartCommand(cli_ctx)
        result = await command.execute_with_fallback(http_verify, fallback_verify)

        # Display verification results
        await _display_verification_results(
            cli_ctx, result, package_name, version, output_format
        )

        cli_ctx.end_command_tracking()

    except Exception as e:
        cli_ctx.log(f"Verification failed: {str(e)}", "error")
        raise


@package_group.command()
@click.argument("package_name", type=str, metavar="PACKAGE_NAME")
@click.argument("version", type=str, metavar="VERSION")
@standard_cli_command(
    help_text="""
    Show detailed information about a built package.
    
    This command displays comprehensive information about a specific package,
    including metadata, file inventory, build options, and package path.
    
    **Arguments:**
    - PACKAGE_NAME: Package name in format "org/project" (e.g., "fourthievesvinegar/solderless-microlab")
    - VERSION: Package version (e.g., "1.0.0")
    
    Use 'ohm package list-packages' to see available packages and their versions.
    """,
    epilog="""
    Examples:
      # Describe a package
      ohm package describe fourthievesvinegar/solderless-microlab 1.0.0
      
      # Describe with JSON output
      ohm package describe fourthievesvinegar/solderless-microlab 1.0.0 --output-format json
    """,
    async_cmd=True,
    track_performance=True,
    handle_errors=True,
    format_output=True,
    add_llm_config=False,
)
@click.pass_context
async def describe(
    ctx,
    package_name: str,
    version: str,
    verbose: bool,
    output_format: str,
):
    """Show detailed information about a built package."""
    cli_ctx = ctx.obj
    cli_ctx.start_command_tracking("package-describe")

    try:

        async def http_describe():
            """Get package info via HTTP API"""
            cli_ctx.log("Fetching package info via HTTP API...", "info")
            response = await cli_ctx.api_client.request(
                "GET", f"/api/package/{package_name}/{version}"
            )
            return response

        async def fallback_describe():
            """Get package info using direct service calls"""
            cli_ctx.log("Using direct service...", "info")
            package_service = await PackageService.get_instance()
            metadata = await package_service.get_package_metadata(package_name, version)

            if not metadata:
                raise click.ClickException(
                    f"Package {package_name}:{version} not found"
                )

            return {
                "status": "success",
                "package": metadata.to_dict(),
            }

        # Execute with fallback
        command = SmartCommand(cli_ctx)
        result = await command.execute_with_fallback(http_describe, fallback_describe)

        # Extract package data
        if "data" in result:
            pkg = result.get("data", {}).get("package", result.get("data", {}))
        elif "package" in result:
            pkg = result.get("package")
        else:
            pkg = result

        if output_format == "json":
            import json

            click.echo(json.dumps(pkg, indent=2, default=str))
        else:
            # Display formatted package information
            click.echo(f"📦 Package: {pkg.get('package_name', 'Unknown')}")
            click.echo(f"   📌 Version: {pkg.get('version', 'Unknown')}")
            click.echo(
                f"   🆔 OKH Manifest ID: {pkg.get('okh_manifest_id', 'Unknown')}"
            )
            click.echo(f"   📁 Path: {pkg.get('package_path', 'Unknown')}")
            click.echo(f"   📄 Files: {pkg.get('total_files', 0):,}")
            click.echo(
                f"   💾 Size: {pkg.get('total_size_bytes', 0):,} bytes ({pkg.get('total_size_bytes', 0) / 1024 / 1024:.2f} MB)"
            )
            click.echo(f"   🕒 Built: {pkg.get('build_timestamp', 'Unknown')}")
            click.echo(f"   🔧 OHM Version: {pkg.get('ohm_version', 'Unknown')}")

            # Show build options if available
            build_options = pkg.get("build_options", {})
            if build_options:
                click.echo(f"\n   Build Options:")
                click.echo(
                    f"      Output Directory: {build_options.get('output_dir', 'Default')}"
                )
                click.echo(
                    f"      Include Design Files: {build_options.get('include_design_files', False)}"
                )
                click.echo(
                    f"      Include Manufacturing Files: {build_options.get('include_manufacturing_files', False)}"
                )
                click.echo(
                    f"      Include Software: {build_options.get('include_software', False)}"
                )
                click.echo(
                    f"      Include Parts: {build_options.get('include_parts', False)}"
                )

        cli_ctx.end_command_tracking()

    except Exception as e:
        cli_ctx.log(f"Describe failed: {str(e)}", "error")
        raise


@package_group.command()
@click.argument("package_name", type=str, metavar="PACKAGE_NAME")
@click.argument("version", type=str, metavar="VERSION")
@click.option("--force", is_flag=True, help="Force deletion without confirmation")
@standard_cli_command(
    help_text="""
    Delete a package from local storage.
    
    **Arguments:**
    - PACKAGE_NAME: Package name in format "org/project" (e.g., "fourthievesvinegar/solderless-microlab")
    - VERSION: Package version (e.g., "1.0.0")
    
    Use 'ohm package list-packages' to see available packages and their versions.
    
    This command removes a built package from the local package storage.
    Use with caution as this action cannot be undone.
    
    When LLM is enabled, deletion includes:
    - Enhanced impact analysis before deletion
    - Dependency checking and warnings
    - Backup suggestions and safety checks
    - Advanced metadata cleanup
    """,
    epilog="""
    Examples:
      # Delete a package (with confirmation)
      ohm package delete my-project 1.0.0
      
      # Force deletion without confirmation
      ohm package delete my-project 1.0.0 --force
      
      # Use LLM for enhanced analysis
      ohm package delete my-project 1.0.0 --use-llm
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
    package_name: str,
    version: str,
    force: bool,
    verbose: bool,
    output_format: str,
    use_llm: bool,
    llm_provider: str,
    llm_model: Optional[str],
    quality_level: str,
    strict_mode: bool,
):
    """Delete a package with enhanced LLM support."""
    cli_ctx = ctx.obj
    cli_ctx.start_command_tracking("package-delete")

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
        if not force:
            if not click.confirm(
                f"Are you sure you want to delete package {package_name}:{version}?"
            ):
                cli_ctx.log("Deletion cancelled", "info")
                return

        # Log LLM usage if enabled
        if cli_ctx.is_llm_enabled():
            log_llm_usage(cli_ctx, "Package deletion")

        async def http_delete():
            """Delete via HTTP API"""
            cli_ctx.log("Deleting via HTTP API...", "info")
            response = await cli_ctx.api_client.request(
                "DELETE", f"/api/package/{package_name}/{version}"
            )
            return response

        async def fallback_delete():
            """Delete using direct service calls"""
            cli_ctx.log("Using direct service deletion...", "info")
            package_service = await PackageService.get_instance()
            success = await package_service.delete_package(package_name, version)
            return {
                "status": "success" if success else "error",
                "message": (
                    f"Package {package_name}:{version} deleted successfully"
                    if success
                    else "Package not found"
                ),
            }

        # Execute deletion with fallback
        command = SmartCommand(cli_ctx)
        result = await command.execute_with_fallback(http_delete, fallback_delete)

        # Display deletion results
        if result.get("status") == "success":
            cli_ctx.log(
                result.get("message", "Package deleted successfully"), "success"
            )
        else:
            cli_ctx.log(result.get("message", "Failed to delete package"), "error")

        cli_ctx.end_command_tracking()

    except Exception as e:
        cli_ctx.log(f"Deletion failed: {str(e)}", "error")
        raise


@package_group.command()
@click.argument("package_name", type=str, metavar="PACKAGE_NAME")
@click.argument("version", type=str, metavar="VERSION")
@standard_cli_command(
    help_text="""
    Push a local package to remote storage.
    
    This command uploads a locally built package to remote storage,
    making it available for distribution and sharing.
    
    **Arguments:**
    - PACKAGE_NAME: Package name in format "org/project" (e.g., "fourthievesvinegar/solderless-microlab")
    - VERSION: Package version (e.g., "1.0.0")
    
    Use 'ohm package list-packages' to see available packages and their versions.
    Use 'ohm package describe PACKAGE_NAME VERSION' for detailed package information.
    
    When LLM is enabled, pushing includes:
    - Enhanced package analysis before upload
    - Quality assessment and optimization suggestions
    - Intelligent upload strategy and error handling
    - Advanced metadata validation
    """,
    epilog="""
    Examples:
      # Push a package to remote storage
      ohm package push fourthievesvinegar/solderless-microlab 1.0.0
      
      # Use LLM for enhanced processing
      ohm package push fourthievesvinegar/solderless-microlab 1.0.0 --use-llm
      
      # List packages to find the correct name and version
      ohm package list-packages
    """,
    async_cmd=True,
    track_performance=True,
    handle_errors=True,
    format_output=True,
    add_llm_config=True,
)
@click.pass_context
async def push(
    ctx,
    package_name: str,
    version: str,
    verbose: bool,
    output_format: str,
    use_llm: bool,
    llm_provider: str,
    llm_model: Optional[str],
    quality_level: str,
    strict_mode: bool,
):
    """Push a local package to remote storage with enhanced LLM support."""
    cli_ctx = ctx.obj
    cli_ctx.start_command_tracking("package-push")

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
            log_llm_usage(cli_ctx, "Package pushing")

        async def http_push():
            """Push package via HTTP API"""
            cli_ctx.log("Pushing via HTTP API...", "info")
            payload = {"package_name": package_name, "version": version}
            response = await cli_ctx.api_client.request(
                "POST", "/api/package/push", json_data=payload
            )
            return response

        async def fallback_push():
            """Push using direct service calls"""
            cli_ctx.log("Using direct service pushing...", "info")
            package_service = await PackageService.get_instance()
            storage_service = await StorageService.get_instance()
            await storage_service.configure(settings.STORAGE_CONFIG)

            remote_storage = PackageRemoteStorage(storage_service)

            # Validate package name format - detect common mistake where version is included
            if "/" in version or package_name.count("/") > 1:
                # Check if version appears to be in package_name
                if version in package_name:
                    suggested_package_name = package_name.rsplit("/", 1)[0]
                    raise click.ClickException(
                        f"Invalid package name format. It looks like you included the version in the package name.\n"
                        f"Received: package_name='{package_name}', version='{version}'\n"
                        f"Expected format: package_name='org/project' (e.g., 'fourthievesvinegar/solderless-microlab'), version='1.0.0'\n"
                        f"Try: ohm package push {suggested_package_name} {version}"
                    )

            # Validate package name has exactly one slash (org/project format)
            if package_name.count("/") != 1:
                raise click.ClickException(
                    f"Invalid package name format. Package name must be in format 'org/project'.\n"
                    f"Received: '{package_name}'\n"
                    f"Expected: 'organization/project' (e.g., 'fourthievesvinegar/solderless-microlab')\n"
                    f"Use 'ohm package list-packages' to see available packages."
                )

            # Get package metadata
            metadata = await package_service.get_package_metadata(package_name, version)
            if not metadata:
                raise click.ClickException(
                    f"Package {package_name}:{version} not found locally.\n"
                    f"Use 'ohm package list-packages' to see available packages and their versions."
                )

            package_path = Path(metadata.package_path)
            if not package_path.exists():
                raise click.ClickException(
                    f"Package directory not found: {package_path}"
                )

            # Push package
            result = await remote_storage.push_package(metadata, package_path)
            return {
                "status": "success",
                "message": f"Successfully pushed {package_name}:{version}",
                "result": result,
            }

        # Execute push with fallback
        command = SmartCommand(cli_ctx)
        result = await command.execute_with_fallback(http_push, fallback_push)

        # Display push results
        if result.get("status") == "success":
            cli_ctx.log(result.get("message"), "success")

            push_result = result.get("result", {})
            if output_format == "json":
                output_data = format_llm_output(result, cli_ctx)
                click.echo(output_data)
            else:
                cli_ctx.log(
                    f"📄 Uploaded {len(push_result.get('uploaded_files', []))} files",
                    "info",
                )
                cli_ctx.log(
                    f"💾 Total size: {push_result.get('total_size', 0):,} bytes", "info"
                )

                if push_result.get("failed_files"):
                    cli_ctx.log(
                        f"⚠️  {len(push_result['failed_files'])} files failed to upload",
                        "warning",
                    )
        else:
            cli_ctx.log(result.get("message", "Failed to push package"), "error")

        cli_ctx.end_command_tracking()

    except Exception as e:
        cli_ctx.log(f"Push failed: {str(e)}", "error")
        raise


@package_group.command()
@click.argument("package_name", type=str, metavar="PACKAGE_NAME")
@click.argument("version", type=str, metavar="VERSION")
@click.option("--output-dir", "-o", help="Output directory for pulled package")
@standard_cli_command(
    help_text="""
    Pull a remote package to local storage.
    
    This command downloads a package from remote storage to local storage,
    making it available for local use and modification.
    
    **Arguments:**
    - PACKAGE_NAME: Package name in format "org/project" (e.g., "fourthievesvinegar/solderless-microlab")
    - VERSION: Package version (e.g., "1.0.0")
    
    Use 'ohm package list-remote' to see available remote packages and their versions.
    
    When LLM is enabled, pulling includes:
    - Enhanced package analysis and validation
    - Quality assessment of downloaded contents
    - Intelligent download strategy and error handling
    - Advanced metadata verification
    """,
    epilog="""
    Examples:
      # Pull a package from remote storage
      ohm package pull fourthievesvinegar/solderless-microlab 1.0.0
      
      # Pull to custom directory
      ohm package pull fourthievesvinegar/solderless-microlab 1.0.0 --output-dir ./my-packages
      
      # Use LLM for enhanced processing
      ohm package pull fourthievesvinegar/solderless-microlab 1.0.0 --use-llm
    """,
    async_cmd=True,
    track_performance=True,
    handle_errors=True,
    format_output=True,
    add_llm_config=True,
)
@click.pass_context
async def pull(
    ctx,
    package_name: str,
    version: str,
    output_dir: Optional[str],
    verbose: bool,
    output_format: str,
    use_llm: bool,
    llm_provider: str,
    llm_model: Optional[str],
    quality_level: str,
    strict_mode: bool,
):
    """Pull a remote package to local storage with enhanced LLM support."""
    cli_ctx = ctx.obj
    cli_ctx.start_command_tracking("package-pull")

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
            log_llm_usage(cli_ctx, "Package pulling")

        async def http_pull():
            """Pull package via HTTP API"""
            cli_ctx.log("Pulling via HTTP API...", "info")
            payload = {"package_name": package_name, "version": version}
            if output_dir:
                payload["output_dir"] = output_dir

            response = await cli_ctx.api_client.request(
                "POST", "/api/package/pull", json_data=payload
            )
            return response

        async def fallback_pull():
            """Pull using direct service calls"""
            cli_ctx.log("Using direct service pulling...", "info")
            storage_service = await StorageService.get_instance()
            await storage_service.configure(settings.STORAGE_CONFIG)

            remote_storage = PackageRemoteStorage(storage_service)

            # Determine output directory
            if output_dir:
                output_path = Path(output_dir)
            else:
                # Use default packages directory
                repo_root = Path(__file__).parent.parent.parent
                output_path = repo_root / "packages"

            # Pull package
            metadata = await remote_storage.pull_package(
                package_name, version, output_path
            )
            return {
                "status": "success",
                "message": f"Successfully pulled {package_name}:{version}",
                "metadata": metadata.to_dict(),
            }

        # Execute pull with fallback
        command = SmartCommand(cli_ctx)
        result = await command.execute_with_fallback(http_pull, fallback_pull)

        # Display pull results
        if result.get("status") == "success":
            cli_ctx.log(result.get("message"), "success")

            metadata = result.get("metadata", {})
            if output_format == "json":
                output_data = format_llm_output(result, cli_ctx)
                click.echo(output_data)
            else:
                cli_ctx.log(
                    f"📁 Local path: {metadata.get('package_path', 'Unknown')}", "info"
                )
                cli_ctx.log(f"📄 Files: {metadata.get('total_files', 0)}", "info")
                cli_ctx.log(
                    f"💾 Size: {metadata.get('total_size_bytes', 0):,} bytes", "info"
                )
        else:
            cli_ctx.log(result.get("message", "Failed to pull package"), "error")

        cli_ctx.end_command_tracking()

    except Exception as e:
        cli_ctx.log(f"Pull failed: {str(e)}", "error")
        raise


@package_group.command()
@standard_cli_command(
    help_text="""
    List packages available in remote storage.
    
    This command displays information about all packages that are
    available in remote storage for download and use.
    
    When LLM is enabled, listing includes:
    - Enhanced package analysis and categorization
    - Quality assessment of remote packages
    - Intelligent filtering and sorting suggestions
    - Advanced metadata extraction
    """,
    epilog="""
    Examples:
      # List remote packages
      ohm package list-remote
      
      # Use LLM for enhanced analysis
      ohm package list-remote --use-llm
    """,
    async_cmd=True,
    track_performance=True,
    handle_errors=True,
    format_output=True,
    add_llm_config=True,
)
@click.pass_context
async def list_remote(
    ctx,
    verbose: bool,
    output_format: str,
    use_llm: bool,
    llm_provider: str,
    llm_model: Optional[str],
    quality_level: str,
    strict_mode: bool,
):
    """List packages available in remote storage with enhanced LLM support."""
    cli_ctx = ctx.obj

    # Fix: Update verbose from the command parameter
    cli_ctx.verbose = verbose
    cli_ctx.config.verbose = verbose

    cli_ctx.start_command_tracking("package-list-remote")

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
            log_llm_usage(cli_ctx, "Remote package listing")

        async def http_list_remote():
            """List remote packages via HTTP API"""
            cli_ctx.log("Listing remote packages via HTTP API...", "info")
            response = await cli_ctx.api_client.request("GET", "/api/package/remote")
            return response

        async def fallback_list_remote():
            """List remote using direct service calls"""
            cli_ctx.log("Using direct service remote listing...", "info")
            storage_service = await StorageService.get_instance()
            await storage_service.configure(settings.STORAGE_CONFIG)

            remote_storage = PackageRemoteStorage(storage_service)
            packages = await remote_storage.list_remote_packages()

            return {"status": "success", "packages": packages, "total": len(packages)}

        # Execute listing with fallback
        command = SmartCommand(cli_ctx)
        result = await command.execute_with_fallback(
            http_list_remote, fallback_list_remote
        )

        # Display listing results
        # Handle both API response format (data.packages) and fallback format (packages)
        if "data" in result:
            packages = result.get("data", {}).get("packages", [])
            total = result.get("data", {}).get("total", len(packages))
        else:
            packages = result.get("packages", [])
            total = result.get("total", len(packages))

        if packages:
            cli_ctx.log(f"Found {total} remote packages", "success")

            if output_format == "json":
                output_data = format_llm_output(result, cli_ctx)
                click.echo(output_data)
            else:
                # Group by package name
                packages_by_name = {}
                for pkg in packages:
                    name = pkg["package_name"]
                    if name not in packages_by_name:
                        packages_by_name[name] = []
                    packages_by_name[name].append(pkg)

                # Display packages
                for package_name, versions in packages_by_name.items():
                    click.echo(f"\n📦 {package_name}")
                    for pkg in sorted(versions, key=lambda x: x["version"]):
                        size_mb = pkg["size"] / (1024 * 1024) if pkg["size"] else 0
                        click.echo(f"  📄 {pkg['version']} ({size_mb:.1f} MB)")

                        if cli_ctx.verbose and pkg.get("last_modified"):
                            cli_ctx.log(
                                f"    🕒 Modified: {pkg['last_modified']}", "info"
                            )

                cli_ctx.log(f"\nTotal: {total} package versions", "info")
        else:
            cli_ctx.log("No packages found in remote storage", "info")

        cli_ctx.end_command_tracking()

    except Exception as e:
        cli_ctx.log(f"Remote listing failed: {str(e)}", "error")
        raise
