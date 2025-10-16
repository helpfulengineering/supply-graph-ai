"""
Package management commands for OME CLI

This module provides commands for building, managing, and deploying OKH packages.
"""

import asyncio
import click
import json
import yaml
from pathlib import Path
from typing import Optional
from uuid import UUID

from .base import (
    CLIContext, SmartCommand, echo_success, 
    echo_error, echo_info, format_json_output
)
from ..core.models.okh import OKHManifest
from ..core.models.package import BuildOptions
from ..core.services.package_service import PackageService
from ..core.services.storage_service import StorageService
from ..core.packaging.remote_storage import PackageRemoteStorage
from ..config import settings


@click.group()
def package_group():
    """OKH Package Management Commands"""
    pass


@package_group.command()
@click.argument('manifest_file', type=click.Path(exists=True))
@click.option('--output-dir', '-o', help='Output directory for built packages')
@click.option('--no-design-files', is_flag=True, help='Exclude design files')
@click.option('--no-manufacturing-files', is_flag=True, help='Exclude manufacturing files')
@click.option('--no-making-instructions', is_flag=True, help='Exclude making instructions')
@click.option('--no-software', is_flag=True, help='Exclude software')
@click.option('--no-parts', is_flag=True, help='Exclude parts')
@click.option('--no-operating-instructions', is_flag=True, help='Exclude operating instructions')
@click.option('--no-quality-instructions', is_flag=True, help='Exclude quality instructions')
@click.option('--no-risk-assessment', is_flag=True, help='Exclude risk assessment')
@click.option('--no-schematics', is_flag=True, help='Exclude schematics')
@click.option('--no-tool-settings', is_flag=True, help='Exclude tool settings')
@click.option('--no-verify', is_flag=True, help='Skip download verification')
@click.option('--max-concurrent', default=5, help='Maximum concurrent downloads')
@click.pass_context
def build(ctx, manifest_file: str, output_dir: Optional[str], **kwargs):
    """Build an OKH package from a manifest file"""
    cli_ctx = ctx.obj
    
    # Read manifest file
    try:
        manifest_path = Path(manifest_file)
        with open(manifest_path, 'r') as f:
            if manifest_path.suffix.lower() == '.yaml' or manifest_path.suffix.lower() == '.yml':
                manifest_data = yaml.safe_load(f)
            else:
                manifest_data = json.load(f)
    except Exception as e:
        echo_error(f"Failed to read manifest file: {str(e)}")
        return
    
    # Create build options
    options = BuildOptions(
        output_dir=output_dir or "packages",
        include_design_files=not kwargs.get('no_design_files', False),
        include_manufacturing_files=not kwargs.get('no_manufacturing_files', False),
        include_making_instructions=not kwargs.get('no_making_instructions', False),
        include_software=not kwargs.get('no_software', False),
        include_parts=not kwargs.get('no_parts', False),
        include_operating_instructions=not kwargs.get('no_operating_instructions', False),
        include_quality_instructions=not kwargs.get('no_quality_instructions', False),
        include_risk_assessment=not kwargs.get('no_risk_assessment', False),
        include_schematics=not kwargs.get('no_schematics', False),
        include_tool_settings=not kwargs.get('no_tool_settings', False),
        verify_downloads=not kwargs.get('no_verify', True),
        max_concurrent_downloads=kwargs.get('max_concurrent', 5)
    )
    
    async def http_build():
        """Build via HTTP API"""
        payload = {
            "manifest_data": manifest_data,
            "options": options.to_dict()
        }
        response = await cli_ctx.api_client.request("POST", "/api/package/build", json_data=payload)
        return response
    
    async def fallback_build():
        """Build using direct service calls"""
        manifest = OKHManifest.from_dict(manifest_data)
        package_service = await PackageService.get_instance()
        metadata = await package_service.build_package_from_manifest(manifest, options)
        return {
            "status": "success",
            "message": "Package built successfully",
            "metadata": metadata.to_dict()
        }
    
    command = SmartCommand(cli_ctx)
    result = asyncio.run(command.execute_with_fallback(http_build, fallback_build))
    
    if result.get("status") == "success":
        metadata = result.get("metadata", {})
        echo_success(f"Package built successfully: {metadata.get('package_name', 'Unknown')}")
        
        if cli_ctx.output_format == 'json':
            click.echo(format_json_output(result))
        else:
            click.echo(f"📦 Package: {metadata.get('package_name', 'Unknown')}")
            click.echo(f"📁 Location: {metadata.get('package_path', 'Unknown')}")
            click.echo(f"📄 Files: {metadata.get('total_files', 0)}")
            click.echo(f"💾 Size: {metadata.get('total_size_bytes', 0):,} bytes")
    else:
        echo_error("Failed to build package")


@package_group.command()
@click.argument('manifest_id')
@click.option('--output-dir', '-o', help='Output directory for built packages')
@click.option('--no-design-files', is_flag=True, help='Exclude design files')
@click.option('--no-manufacturing-files', is_flag=True, help='Exclude manufacturing files')
@click.option('--no-making-instructions', is_flag=True, help='Exclude making instructions')
@click.option('--no-software', is_flag=True, help='Exclude software')
@click.option('--no-parts', is_flag=True, help='Exclude parts')
@click.option('--no-operating-instructions', is_flag=True, help='Exclude operating instructions')
@click.option('--no-quality-instructions', is_flag=True, help='Exclude quality instructions')
@click.option('--no-risk-assessment', is_flag=True, help='Exclude risk assessment')
@click.option('--no-schematics', is_flag=True, help='Exclude schematics')
@click.option('--no-tool-settings', is_flag=True, help='Exclude tool settings')
@click.option('--no-verify', is_flag=True, help='Skip download verification')
@click.option('--max-concurrent', default=5, help='Maximum concurrent downloads')
@click.pass_context
def build_from_storage(ctx, manifest_id: str, output_dir: Optional[str], **kwargs):
    """Build an OKH package from a stored manifest"""
    cli_ctx = ctx.obj
    
    # Create build options
    options = BuildOptions(
        output_dir=output_dir or "packages",
        include_design_files=not kwargs.get('no_design_files', False),
        include_manufacturing_files=not kwargs.get('no_manufacturing_files', False),
        include_making_instructions=not kwargs.get('no_making_instructions', False),
        include_software=not kwargs.get('no_software', False),
        include_parts=not kwargs.get('no_parts', False),
        include_operating_instructions=not kwargs.get('no_operating_instructions', False),
        include_quality_instructions=not kwargs.get('no_quality_instructions', False),
        include_risk_assessment=not kwargs.get('no_risk_assessment', False),
        include_schematics=not kwargs.get('no_schematics', False),
        include_tool_settings=not kwargs.get('no_tool_settings', False),
        verify_downloads=not kwargs.get('no_verify', True),
        max_concurrent_downloads=kwargs.get('max_concurrent', 5)
    )
    
    async def http_build_from_storage():
        """Build from storage via HTTP API"""
        payload = {"options": options.to_dict()}
        response = await cli_ctx.api_client.request("POST", f"/api/package/build/{manifest_id}", json_data=payload)
        return response
    
    async def fallback_build_from_storage():
        """Build from storage using direct service calls"""
        package_service = await PackageService.get_instance()
        metadata = await package_service.build_package_from_storage(UUID(manifest_id), options)
        return {
            "status": "success",
            "message": "Package built successfully",
            "metadata": metadata.to_dict()
        }
    
    command = SmartCommand(cli_ctx)
    result = asyncio.run(command.execute_with_fallback(http_build_from_storage, fallback_build_from_storage))
    
    if result.get("status") == "success":
        metadata = result.get("metadata", {})
        echo_success(f"Package built successfully: {metadata.get('package_name', 'Unknown')}")
        
        if cli_ctx.output_format == 'json':
            click.echo(format_json_output(result))
        else:
            click.echo(f"📦 Package: {metadata.get('package_name', 'Unknown')}")
            click.echo(f"📁 Location: {metadata.get('package_path', 'Unknown')}")
            click.echo(f"📄 Files: {metadata.get('total_files', 0)}")
            click.echo(f"💾 Size: {metadata.get('total_size_bytes', 0):,} bytes")
    else:
        echo_error("Failed to build package")


@package_group.command()
@click.pass_context
def list_packages(ctx):
    """List all built packages"""
    cli_ctx = ctx.obj
    
    async def http_list():
        """List via HTTP API"""
        response = await cli_ctx.api_client.request("GET", "/api/package/list")
        return response
    
    async def fallback_list():
        """List using direct service calls"""
        package_service = await PackageService.get_instance()
        packages = await package_service.list_built_packages()
        return {
            "status": "success",
            "packages": [pkg.to_dict() for pkg in packages],
            "total": len(packages)
        }
    
    command = SmartCommand(cli_ctx)
    result = asyncio.run(command.execute_with_fallback(http_list, fallback_list))
    
    packages = result.get("packages", [])
    total = result.get("total", len(packages))
    
    if packages:
        echo_success(f"Found {total} built packages")
        
        if cli_ctx.output_format == 'json':
            click.echo(format_json_output(result))
        else:
            for pkg in packages:
                click.echo(f"📦 {pkg.get('package_name', 'Unknown')}/{pkg.get('version', 'Unknown')}")
                click.echo(f"   📁 {pkg.get('package_path', 'Unknown')}")
                click.echo(f"   📄 {pkg.get('total_files', 0)} files, {pkg.get('total_size_bytes', 0):,} bytes")
                click.echo(f"   🕒 Built: {pkg.get('build_timestamp', 'Unknown')}")
                click.echo()
    else:
        echo_info("No packages found")


@package_group.command()
@click.argument('package_name')
@click.argument('version')
@click.pass_context
def verify(ctx, package_name: str, version: str):
    """Verify a package's integrity"""
    cli_ctx = ctx.obj
    
    async def http_verify():
        """Verify via HTTP API"""
        response = await cli_ctx.api_client.request("GET", f"/api/package/{package_name}/{version}/verify")
        return response
    
    async def fallback_verify():
        """Verify using direct service calls"""
        package_service = await PackageService.get_instance()
        results = await package_service.verify_package(package_name, version)
        return {
            "status": "success",
            "verification": results
        }
    
    command = SmartCommand(cli_ctx)
    result = asyncio.run(command.execute_with_fallback(http_verify, fallback_verify))
    
    verification = result.get("verification", {})
    is_valid = verification.get("valid", False)
    
    if is_valid:
        echo_success(f"Package {package_name}:{version} is valid")
    else:
        echo_error(f"Package {package_name}:{version} verification failed")
    
    if cli_ctx.output_format == 'json':
        click.echo(format_json_output(result))
    else:
        if verification.get("missing_files"):
            click.echo(f"Missing files: {len(verification['missing_files'])}")
            for file in verification["missing_files"]:
                click.echo(f"  ❌ {file}")
        
        if verification.get("extra_files"):
            click.echo(f"Extra files: {len(verification['extra_files'])}")
            for file in verification["extra_files"]:
                click.echo(f"  ⚠️  {file}")


@package_group.command()
@click.argument('package_name')
@click.argument('version')
@click.option('--force', is_flag=True, help='Force deletion without confirmation')
@click.pass_context
def delete(ctx, package_name: str, version: str, force: bool):
    """Delete a package"""
    cli_ctx = ctx.obj
    
    if not force:
        if not click.confirm(f"Are you sure you want to delete package {package_name}:{version}?"):
            echo_info("Deletion cancelled")
            return
    
    async def http_delete():
        """Delete via HTTP API"""
        response = await cli_ctx.api_client.request("DELETE", f"/api/package/{package_name}/{version}")
        return response
    
    async def fallback_delete():
        """Delete using direct service calls"""
        package_service = await PackageService.get_instance()
        success = await package_service.delete_package(package_name, version)
        return {
            "status": "success" if success else "error",
            "message": f"Package {package_name}:{version} deleted successfully" if success else "Package not found"
        }
    
    command = SmartCommand(cli_ctx)
    result = asyncio.run(command.execute_with_fallback(http_delete, fallback_delete))
    
    if result.get("status") == "success":
        echo_success(result.get("message", "Package deleted successfully"))
    else:
        echo_error(result.get("message", "Failed to delete package"))


@package_group.command()
@click.argument('package_name')
@click.argument('version')
@click.pass_context
def push(ctx, package_name: str, version: str):
    """Push a local package to remote storage"""
    cli_ctx = ctx.obj
    
    async def http_push():
        """Push package via HTTP API"""
        payload = {
            "package_name": package_name,
            "version": version
        }
        response = await cli_ctx.api_client.request("POST", "/api/package/push", json_data=payload)
        return response
    
    async def fallback_push():
        """Push using direct service calls"""
        package_service = await PackageService.get_instance()
        storage_service = await StorageService.get_instance()
        await storage_service.configure(settings.STORAGE_CONFIG)
        
        remote_storage = PackageRemoteStorage(storage_service)
        
        # Get package metadata
        metadata = await package_service.get_package_metadata(package_name, version)
        if not metadata:
            raise click.ClickException(f"Package {package_name}:{version} not found locally")
        
        package_path = Path(metadata.package_path)
        if not package_path.exists():
            raise click.ClickException(f"Package directory not found: {package_path}")
        
        # Push package
        result = await remote_storage.push_package(metadata, package_path)
        return {
            "status": "success",
            "message": f"Successfully pushed {package_name}:{version}",
            "result": result
        }
    
    command = SmartCommand(cli_ctx)
    result = asyncio.run(command.execute_with_fallback(http_push, fallback_push))
    
    if result.get("status") == "success":
        echo_success(result.get("message"))
        
        push_result = result.get("result", {})
        if cli_ctx.output_format == 'json':
            click.echo(format_json_output(result))
        else:
            click.echo(f"📄 Uploaded {len(push_result.get('uploaded_files', []))} files")
            click.echo(f"💾 Total size: {push_result.get('total_size', 0):,} bytes")
            
            if push_result.get('failed_files'):
                click.echo(f"⚠️  {len(push_result['failed_files'])} files failed to upload")
    else:
        echo_error(result.get("message", "Failed to push package"))


@package_group.command()
@click.argument('package_name')
@click.argument('version')
@click.option('--output-dir', '-o', help='Output directory for pulled package')
@click.pass_context
def pull(ctx, package_name: str, version: str, output_dir: Optional[str]):
    """Pull a remote package to local storage"""
    cli_ctx = ctx.obj
    
    async def http_pull():
        """Pull package via HTTP API"""
        payload = {
            "package_name": package_name,
            "version": version
        }
        if output_dir:
            payload["output_dir"] = output_dir
        
        response = await cli_ctx.api_client.request("POST", "/api/package/pull", json_data=payload)
        return response
    
    async def fallback_pull():
        """Pull using direct service calls"""
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
        metadata = await remote_storage.pull_package(package_name, version, output_path)
        return {
            "status": "success",
            "message": f"Successfully pulled {package_name}:{version}",
            "metadata": metadata.to_dict()
        }
    
    command = SmartCommand(cli_ctx)
    result = asyncio.run(command.execute_with_fallback(http_pull, fallback_pull))
    
    if result.get("status") == "success":
        echo_success(result.get("message"))
        
        metadata = result.get("metadata", {})
        if cli_ctx.output_format == 'json':
            click.echo(format_json_output(result))
        else:
            click.echo(f"📁 Local path: {metadata.get('package_path', 'Unknown')}")
            click.echo(f"📄 Files: {metadata.get('total_files', 0)}")
            click.echo(f"💾 Size: {metadata.get('total_size_bytes', 0):,} bytes")
    else:
        echo_error(result.get("message", "Failed to pull package"))


@package_group.command()
@click.pass_context
def list_remote(ctx):
    """List packages available in remote storage"""
    cli_ctx = ctx.obj
    
    async def http_list_remote():
        """List remote packages via HTTP API"""
        response = await cli_ctx.api_client.request("GET", "/api/package/remote")
        return response
    
    async def fallback_list_remote():
        """List remote using direct service calls"""
        storage_service = await StorageService.get_instance()
        await storage_service.configure(settings.STORAGE_CONFIG)
        
        remote_storage = PackageRemoteStorage(storage_service)
        packages = await remote_storage.list_remote_packages()
        
        return {
            "status": "success",
            "packages": packages,
            "total": len(packages)
        }
    
    command = SmartCommand(cli_ctx)
    result = asyncio.run(command.execute_with_fallback(http_list_remote, fallback_list_remote))
    
    packages = result.get("packages", [])
    total = result.get("total", len(packages))
    
    if packages:
        echo_success(f"Found {total} remote packages")
        
        if cli_ctx.output_format == 'json':
            click.echo(format_json_output(result))
        else:
            # Group by package name
            packages_by_name = {}
            for pkg in packages:
                name = pkg['package_name']
                if name not in packages_by_name:
                    packages_by_name[name] = []
                packages_by_name[name].append(pkg)
            
            # Display packages
            for package_name, versions in packages_by_name.items():
                click.echo(f"\n📦 {package_name}")
                for pkg in sorted(versions, key=lambda x: x['version']):
                    size_mb = pkg['size'] / (1024 * 1024) if pkg['size'] else 0
                    click.echo(f"  📄 {pkg['version']} ({size_mb:.1f} MB)")
                    
                    if cli_ctx.verbose and pkg.get('last_modified'):
                        click.echo(f"    🕒 Modified: {pkg['last_modified']}")
            
            click.echo(f"\nTotal: {total} package versions")
    else:
        echo_info("No packages found in remote storage")
