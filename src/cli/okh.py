"""
OKH (OpenKnowHow) commands for OME CLI

This module provides commands for managing OKH manifests including
creation, validation, extraction, and storage operations.
"""

import click
import asyncio
import json
from pathlib import Path
from typing import Optional, Dict, Any
from uuid import UUID

from .base import (
    CLIContext, SmartCommand, with_async_context,
    echo_success, echo_error, echo_info, format_json_output
)


@click.group()
def okh_group():
    """OKH (OpenKnowHow) manifest management commands"""
    pass


@okh_group.command()
@click.argument('manifest_file', type=click.Path(exists=True))
@click.option('--quality-level', default='professional',
              type=click.Choice(['hobby', 'professional', 'medical']),
              help='Quality level for validation')
@click.option('--strict-mode', is_flag=True,
              help='Enable strict validation mode')
@click.pass_context
def validate(ctx, manifest_file: str, quality_level: str, strict_mode: bool):
    """Validate an OKH manifest"""
    cli_ctx = ctx.obj
    
    # Read manifest file
    try:
        manifest_path = Path(manifest_file)
        with open(manifest_path, 'r') as f:
            if manifest_path.suffix.lower() == '.yaml' or manifest_path.suffix.lower() == '.yml':
                import yaml
                manifest_data = yaml.safe_load(f)
            else:
                manifest_data = json.load(f)
    except Exception as e:
        echo_error(f"Failed to read manifest file: {str(e)}")
        return
    
    async def http_validate():
        """Validate via HTTP API"""
        payload = {
            "content": manifest_data,
            "validation_context": quality_level
        }
        params = {"strict_mode": strict_mode}
        response = await cli_ctx.api_client.request(
            "POST", "/okh/validate", json_data=payload, params=params
        )
        return response
    
    async def fallback_validate():
        """Validate using direct service calls"""
        from ..core.models.okh import OKHManifest
        from ..core.services.okh_service import OKHService
        
        manifest = OKHManifest.from_dict(manifest_data)
        okh_service = await OKHService.get_instance()
        result = await okh_service.validate(manifest, quality_level, strict_mode)
        return result.to_dict()
    
    command = SmartCommand(cli_ctx)
    result = asyncio.run(command.execute_with_fallback(http_validate, fallback_validate))
    
    if cli_ctx.output_format == 'json':
        click.echo(format_json_output(result))
    else:
        validation = result.get("validation", result)
        is_valid = validation.get("is_valid", False)
        
        if is_valid:
            echo_success("Manifest is valid")
        else:
            echo_error("Manifest validation failed")
        
        # Show validation details
        if validation.get("errors"):
            click.echo("\nErrors:")
            for error in validation["errors"]:
                click.echo(f"  ❌ {error}")
        
        if validation.get("warnings"):
            click.echo("\nWarnings:")
            for warning in validation["warnings"]:
                click.echo(f"  ⚠️  {warning}")
        
        if validation.get("completeness_score"):
            score = validation["completeness_score"]
            click.echo(f"\nCompleteness Score: {score:.1%}")


@okh_group.command()
@click.argument('manifest_file', type=click.Path(exists=True))
@click.option('--output', '-o', help='Output file path')
@click.pass_context
def create(ctx, manifest_file: str, output: Optional[str]):
    """Create and store an OKH manifest"""
    cli_ctx = ctx.obj
    
    # Read manifest file
    try:
        manifest_path = Path(manifest_file)
        with open(manifest_path, 'r') as f:
            if manifest_path.suffix.lower() == '.yaml' or manifest_path.suffix.lower() == '.yml':
                import yaml
                manifest_data = yaml.safe_load(f)
            else:
                manifest_data = json.load(f)
    except Exception as e:
        echo_error(f"Failed to read manifest file: {str(e)}")
        return
    
    async def http_create():
        """Create via HTTP API"""
        payload = {"content": manifest_data}
        response = await cli_ctx.api_client.request("POST", "/okh/create", json_data=payload)
        return response
    
    async def fallback_create():
        """Create using direct service calls"""
        from ..core.models.okh import OKHManifest
        from ..core.services.okh_service import OKHService
        
        manifest = OKHManifest.from_dict(manifest_data)
        okh_service = await OKHService.get_instance()
        result = await okh_service.create(manifest)
        return result.to_dict()
    
    command = SmartCommand(cli_ctx)
    result = asyncio.run(command.execute_with_fallback(http_create, fallback_create))
    
    manifest_id = result.get("id") or result.get("manifest", {}).get("id")
    
    if manifest_id:
        echo_success(f"OKH manifest created with ID: {manifest_id}")
        
        if output:
            # Save result to output file
            with open(output, 'w') as f:
                json.dump(result, f, indent=2, default=str)
            echo_info(f"Result saved to {output}")
        
        if cli_ctx.output_format == 'json':
            click.echo(format_json_output(result))
    else:
        echo_error("Failed to create OKH manifest")


@okh_group.command()
@click.argument('manifest_id', type=str)
@click.option('--output', '-o', help='Output file path')
@click.pass_context
def get(ctx, manifest_id: str, output: Optional[str]):
    """Get an OKH manifest by ID"""
    cli_ctx = ctx.obj
    
    async def http_get():
        """Get via HTTP API"""
        response = await cli_ctx.api_client.request("GET", f"/okh/{manifest_id}")
        return response
    
    async def fallback_get():
        """Get using direct service calls"""
        from ..core.services.okh_service import OKHService
        
        okh_service = await OKHService.get_instance()
        manifest = await okh_service.get_by_id(UUID(manifest_id))
        if manifest:
            return manifest.to_dict()
        else:
            raise click.ClickException("Manifest not found")
    
    command = SmartCommand(cli_ctx)
    result = asyncio.run(command.execute_with_fallback(http_get, fallback_get))
    
    manifest = result.get("manifest", result)
    
    if manifest:
        echo_success(f"Retrieved OKH manifest: {manifest.get('title', 'Unknown')}")
        
        if output:
            # Save manifest to output file
            with open(output, 'w') as f:
                json.dump(manifest, f, indent=2, default=str)
            echo_info(f"Manifest saved to {output}")
        
        if cli_ctx.output_format == 'json':
            click.echo(format_json_output(result))
        else:
            # Show basic manifest info
            click.echo(f"Title: {manifest.get('title', 'Unknown')}")
            click.echo(f"Version: {manifest.get('version', 'Unknown')}")
            click.echo(f"Organization: {manifest.get('organization', {}).get('name', 'Unknown')}")
    else:
        echo_error("Manifest not found")


@okh_group.command()
@click.argument('manifest_file', type=click.Path(exists=True))
@click.pass_context
def extract(ctx, manifest_file: str):
    """Extract requirements from an OKH manifest"""
    cli_ctx = ctx.obj
    
    # Read manifest file
    try:
        manifest_path = Path(manifest_file)
        with open(manifest_path, 'r') as f:
            if manifest_path.suffix.lower() == '.yaml' or manifest_path.suffix.lower() == '.yml':
                import yaml
                manifest_data = yaml.safe_load(f)
            else:
                manifest_data = json.load(f)
    except Exception as e:
        echo_error(f"Failed to read manifest file: {str(e)}")
        return
    
    async def http_extract():
        """Extract via HTTP API"""
        payload = {"content": manifest_data}
        response = await cli_ctx.api_client.request("POST", "/okh/extract", json_data=payload)
        return response
    
    async def fallback_extract():
        """Extract using direct service calls"""
        from ..core.models.okh import OKHManifest
        from ..core.services.okh_service import OKHService
        
        manifest = OKHManifest.from_dict(manifest_data)
        okh_service = await OKHService.get_instance()
        requirements = await okh_service.extract_requirements(manifest)
        return {"requirements": requirements}
    
    command = SmartCommand(cli_ctx)
    result = asyncio.run(command.execute_with_fallback(http_extract, fallback_extract))
    
    requirements = result.get("requirements", [])
    
    if requirements:
        echo_success(f"Extracted {len(requirements)} requirements")
        
        if cli_ctx.output_format == 'json':
            click.echo(format_json_output(result))
        else:
            for i, req in enumerate(requirements, 1):
                click.echo(f"{i}. {req.get('type', 'Unknown')}: {req.get('description', 'No description')}")
    else:
        echo_info("No requirements found in manifest")


@okh_group.command()
@click.option('--limit', default=10, help='Maximum number of manifests to list')
@click.option('--offset', default=0, help='Number of manifests to skip')
@click.pass_context
def list_manifests(ctx, limit: int, offset: int):
    """List stored OKH manifests"""
    cli_ctx = ctx.obj
    
    async def http_list():
        """List via HTTP API"""
        params = {"limit": limit, "offset": offset}
        response = await cli_ctx.api_client.request("GET", "/okh/list", params=params)
        return response
    
    async def fallback_list():
        """List using direct service calls"""
        from ..core.services.okh_service import OKHService
        
        okh_service = await OKHService.get_instance()
        manifests = await okh_service.list_manifests(limit=limit, offset=offset)
        return {
            "manifests": [manifest.to_dict() for manifest in manifests],
            "total": len(manifests)
        }
    
    command = SmartCommand(cli_ctx)
    result = asyncio.run(command.execute_with_fallback(http_list, fallback_list))
    
    manifests = result.get("manifests", [])
    total = result.get("total", len(manifests))
    
    if manifests:
        echo_success(f"Found {total} OKH manifests")
        
        if cli_ctx.output_format == 'json':
            click.echo(format_json_output(result))
        else:
            for manifest in manifests:
                click.echo(f"📄 {manifest.get('id', 'Unknown')}")
                click.echo(f"   Title: {manifest.get('title', 'Unknown')}")
                click.echo(f"   Version: {manifest.get('version', 'Unknown')}")
                click.echo(f"   Organization: {manifest.get('organization', {}).get('name', 'Unknown')}")
                click.echo()
    else:
        echo_info("No OKH manifests found")


@okh_group.command()
@click.argument('manifest_id', type=str)
@click.option('--force', is_flag=True, help='Force deletion without confirmation')
@click.pass_context
def delete(ctx, manifest_id: str, force: bool):
    """Delete an OKH manifest"""
    cli_ctx = ctx.obj
    
    if not force:
        if not click.confirm(f"Are you sure you want to delete manifest {manifest_id}?"):
            echo_info("Deletion cancelled")
            return
    
    async def http_delete():
        """Delete via HTTP API"""
        response = await cli_ctx.api_client.request("DELETE", f"/okh/{manifest_id}")
        return response
    
    async def fallback_delete():
        """Delete using direct service calls"""
        from ..core.services.okh_service import OKHService
        
        okh_service = await OKHService.get_instance()
        success = await okh_service.delete(UUID(manifest_id))
        return {"success": success}
    
    command = SmartCommand(cli_ctx)
    result = asyncio.run(command.execute_with_fallback(http_delete, fallback_delete))
    
    if result.get("success", True):  # HTTP API returns success by default
        echo_success(f"OKH manifest {manifest_id} deleted successfully")
    else:
        echo_error(f"Failed to delete OKH manifest {manifest_id}")


@okh_group.command()
@click.argument('file_path', type=click.Path(exists=True))
@click.option('--quality-level', default='basic', type=click.Choice(['basic', 'standard', 'premium']), help='Validation quality level')
@click.option('--strict-mode', is_flag=True, help='Enable strict validation mode')
@click.pass_context
def upload(ctx, file_path: str, quality_level: str, strict_mode: bool):
    """Upload and validate an OKH manifest file"""
    cli_ctx = ctx.obj
    
    async def http_upload():
        """Upload manifest via HTTP API"""
        with open(file_path, 'r') as f:
            content = f.read()
        
        payload = {
            "content": content,
            "quality_level": quality_level,
            "strict_mode": strict_mode
        }
        response = await cli_ctx.api_client.request("POST", "/okh/upload", json_data=payload)
        return response
    
    async def fallback_upload():
        """Fallback upload using direct services"""
        with open(file_path, 'r') as f:
            content = f.read()
        
        manifest = OKHManifest.from_json(content)
        okh_service = await OKHService.get_instance()
        result = await okh_service.create(manifest)
        return result.to_dict()
    
    command = SmartCommand(cli_ctx)
    result = asyncio.run(command.execute_with_fallback(http_upload, fallback_upload))
    
    manifest_id = result.get("id") or result.get("manifest", {}).get("id")
    
    if manifest_id:
        echo_success(f"OKH manifest uploaded with ID: {manifest_id}")
    else:
        echo_error("Failed to upload OKH manifest")
