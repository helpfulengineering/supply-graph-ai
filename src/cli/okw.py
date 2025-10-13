"""
OKW (OpenKnowWhere) commands for OME CLI

This module provides commands for managing OKW facilities including
creation, validation, listing, and matching operations.
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
def okw_group():
    """OKW (OpenKnowWhere) facility management commands"""
    pass


@okw_group.command()
@click.argument('facility_file', type=click.Path(exists=True))
@click.option('--quality-level', default='professional',
              type=click.Choice(['hobby', 'professional', 'medical']),
              help='Quality level for validation')
@click.option('--strict-mode', is_flag=True,
              help='Enable strict validation mode')
@click.pass_context
def validate(ctx, facility_file: str, quality_level: str, strict_mode: bool):
    """Validate an OKW facility"""
    cli_ctx = ctx.obj
    
    # Read facility file
    try:
        facility_path = Path(facility_file)
        with open(facility_path, 'r') as f:
            if facility_path.suffix.lower() == '.yaml' or facility_path.suffix.lower() == '.yml':
                import yaml
                facility_data = yaml.safe_load(f)
            else:
                facility_data = json.load(f)
    except Exception as e:
        echo_error(f"Failed to read facility file: {str(e)}")
        return
    
    async def http_validate():
        """Validate via HTTP API"""
        payload = {
            "content": facility_data,
            "validation_context": quality_level
        }
        params = {"strict_mode": strict_mode}
        response = await cli_ctx.api_client.request(
            "POST", "/okw/validate", json_data=payload, params=params
        )
        return response
    
    async def fallback_validate():
        """Validate using direct service calls"""
        from ..core.models.okw import OKWFacility
        from ..core.services.okw_service import OKWService
        
        facility = OKWFacility.from_dict(facility_data)
        okw_service = await OKWService.get_instance()
        result = await okw_service.validate(facility, quality_level, strict_mode)
        return result.to_dict()
    
    command = SmartCommand(cli_ctx)
    result = asyncio.run(command.execute_with_fallback(http_validate, fallback_validate))
    
    if cli_ctx.output_format == 'json':
        click.echo(format_json_output(result))
    else:
        validation = result.get("validation", result)
        is_valid = validation.get("is_valid", False)
        
        if is_valid:
            echo_success("Facility is valid")
        else:
            echo_error("Facility validation failed")
        
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


@okw_group.command()
@click.argument('facility_file', type=click.Path(exists=True))
@click.option('--output', '-o', help='Output file path')
@click.pass_context
def create(ctx, facility_file: str, output: Optional[str]):
    """Create and store an OKW facility"""
    cli_ctx = ctx.obj
    
    # Read facility file
    try:
        facility_path = Path(facility_file)
        with open(facility_path, 'r') as f:
            if facility_path.suffix.lower() == '.yaml' or facility_path.suffix.lower() == '.yml':
                import yaml
                facility_data = yaml.safe_load(f)
            else:
                facility_data = json.load(f)
    except Exception as e:
        echo_error(f"Failed to read facility file: {str(e)}")
        return
    
    async def http_create():
        """Create via HTTP API"""
        payload = {"content": facility_data}
        response = await cli_ctx.api_client.request("POST", "/okw/create", json_data=payload)
        return response
    
    async def fallback_create():
        """Create using direct service calls"""
        from ..core.models.okw import OKWFacility
        from ..core.services.okw_service import OKWService
        
        facility = OKWFacility.from_dict(facility_data)
        okw_service = await OKWService.get_instance()
        result = await okw_service.create(facility)
        return result.to_dict()
    
    command = SmartCommand(cli_ctx)
    result = asyncio.run(command.execute_with_fallback(http_create, fallback_create))
    
    facility_id = result.get("id") or result.get("facility", {}).get("id")
    
    if facility_id:
        echo_success(f"OKW facility created with ID: {facility_id}")
        
        if output:
            # Save result to output file
            with open(output, 'w') as f:
                json.dump(result, f, indent=2, default=str)
            echo_info(f"Result saved to {output}")
        
        if cli_ctx.output_format == 'json':
            click.echo(format_json_output(result))
    else:
        echo_error("Failed to create OKW facility")


@okw_group.command()
@click.argument('facility_id', type=str)
@click.option('--output', '-o', help='Output file path')
@click.pass_context
def get(ctx, facility_id: str, output: Optional[str]):
    """Get an OKW facility by ID"""
    cli_ctx = ctx.obj
    
    async def http_get():
        """Get via HTTP API"""
        response = await cli_ctx.api_client.request("GET", f"/okw/{facility_id}")
        return response
    
    async def fallback_get():
        """Get using direct service calls"""
        from ..core.services.okw_service import OKWService
        
        okw_service = await OKWService.get_instance()
        facility = await okw_service.get_by_id(UUID(facility_id))
        if facility:
            return facility.to_dict()
        else:
            raise click.ClickException("Facility not found")
    
    command = SmartCommand(cli_ctx)
    result = asyncio.run(command.execute_with_fallback(http_get, fallback_get))
    
    facility = result.get("facility", result)
    
    if facility:
        echo_success(f"Retrieved OKW facility: {facility.get('name', 'Unknown')}")
        
        if output:
            # Save facility to output file
            with open(output, 'w') as f:
                json.dump(facility, f, indent=2, default=str)
            echo_info(f"Facility saved to {output}")
        
        if cli_ctx.output_format == 'json':
            click.echo(format_json_output(result))
        else:
            # Show basic facility info
            click.echo(f"Name: {facility.get('name', 'Unknown')}")
            click.echo(f"Type: {facility.get('facility_type', 'Unknown')}")
            click.echo(f"Location: {facility.get('location', {}).get('address', 'Unknown')}")
            click.echo(f"Status: {facility.get('status', 'Unknown')}")
    else:
        echo_error("Facility not found")


@okw_group.command()
@click.option('--limit', default=10, help='Maximum number of facilities to list')
@click.option('--offset', default=0, help='Number of facilities to skip')
@click.option('--facility-type', help='Filter by facility type')
@click.option('--status', help='Filter by facility status')
@click.option('--location', help='Filter by location')
@click.pass_context
def list_facilities(ctx, limit: int, offset: int, facility_type: Optional[str], 
                         status: Optional[str], location: Optional[str]):
    """List stored OKW facilities"""
    cli_ctx = ctx.obj
    
    async def http_list():
        """List via HTTP API"""
        params = {
            "limit": limit, 
            "offset": offset,
            "facility_type": facility_type,
            "status": status,
            "location": location
        }
        # Remove None values
        params = {k: v for k, v in params.items() if v is not None}
        response = await cli_ctx.api_client.request("GET", "/okw/list", params=params)
        return response
    
    async def fallback_list():
        """List using direct service calls"""
        from ..core.services.okw_service import OKWService
        
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
    
    command = SmartCommand(cli_ctx)
    result = asyncio.run(command.execute_with_fallback(http_list, fallback_list))
    
    facilities = result.get("facilities", [])
    total = result.get("total", len(facilities))
    
    if facilities:
        echo_success(f"Found {total} OKW facilities")
        
        if cli_ctx.output_format == 'json':
            click.echo(format_json_output(result))
        else:
            for facility in facilities:
                click.echo(f"🏭 {facility.get('id', 'Unknown')}")
                click.echo(f"   Name: {facility.get('name', 'Unknown')}")
                click.echo(f"   Type: {facility.get('facility_type', 'Unknown')}")
                click.echo(f"   Status: {facility.get('status', 'Unknown')}")
                click.echo(f"   Location: {facility.get('location', {}).get('address', 'Unknown')}")
                click.echo()
    else:
        echo_info("No OKW facilities found")


@okw_group.command()
@click.argument('facility_id', type=str)
@click.option('--force', is_flag=True, help='Force deletion without confirmation')
@click.pass_context
def delete(ctx, facility_id: str, force: bool):
    """Delete an OKW facility"""
    cli_ctx = ctx.obj
    
    if not force:
        if not click.confirm(f"Are you sure you want to delete facility {facility_id}?"):
            echo_info("Deletion cancelled")
            return
    
    async def http_delete():
        """Delete via HTTP API"""
        response = await cli_ctx.api_client.request("DELETE", f"/okw/{facility_id}")
        return response
    
    async def fallback_delete():
        """Delete using direct service calls"""
        from ..core.services.okw_service import OKWService
        
        okw_service = await OKWService.get_instance()
        success = await okw_service.delete(UUID(facility_id))
        return {"success": success}
    
    command = SmartCommand(cli_ctx)
    result = asyncio.run(command.execute_with_fallback(http_delete, fallback_delete))
    
    if result.get("success", True):  # HTTP API returns success by default
        echo_success(f"OKW facility {facility_id} deleted successfully")
    else:
        echo_error(f"Failed to delete OKW facility {facility_id}")


@okw_group.command()
@click.argument('facility_file', type=click.Path(exists=True))
@click.pass_context
def extract_capabilities(ctx, facility_file: str):
    """Extract capabilities from an OKW facility"""
    cli_ctx = ctx.obj
    
    # Read facility file
    try:
        facility_path = Path(facility_file)
        with open(facility_path, 'r') as f:
            if facility_path.suffix.lower() == '.yaml' or facility_path.suffix.lower() == '.yml':
                import yaml
                facility_data = yaml.safe_load(f)
            else:
                facility_data = json.load(f)
    except Exception as e:
        echo_error(f"Failed to read facility file: {str(e)}")
        return
    
    async def http_extract():
        """Extract via HTTP API"""
        payload = {"content": facility_data}
        response = await cli_ctx.api_client.request("POST", "/okw/extract", json_data=payload)
        return response
    
    async def fallback_extract():
        """Extract using direct service calls"""
        from ..core.models.okw import OKWFacility
        from ..core.services.okw_service import OKWService
        
        facility = OKWFacility.from_dict(facility_data)
        okw_service = await OKWService.get_instance()
        capabilities = await okw_service.extract_capabilities(facility)
        return {"capabilities": capabilities}
    
    command = SmartCommand(cli_ctx)
    result = asyncio.run(command.execute_with_fallback(http_extract, fallback_extract))
    
    capabilities = result.get("capabilities", [])
    
    if capabilities:
        echo_success(f"Extracted {len(capabilities)} capabilities")
        
        if cli_ctx.output_format == 'json':
            click.echo(format_json_output(result))
        else:
            for i, cap in enumerate(capabilities, 1):
                click.echo(f"{i}. {cap.get('type', 'Unknown')}: {cap.get('description', 'No description')}")
    else:
        echo_info("No capabilities found in facility")


@okw_group.command()
@click.argument('file_path', type=click.Path(exists=True))
@click.option('--quality-level', default='basic', type=click.Choice(['basic', 'standard', 'premium']), help='Validation quality level')
@click.option('--strict-mode', is_flag=True, help='Enable strict validation mode')
@click.pass_context
def upload(ctx, file_path: str, quality_level: str, strict_mode: bool):
    """Upload and validate an OKW facility file"""
    cli_ctx = ctx.obj
    
    async def http_upload():
        """Upload facility via HTTP API"""
        with open(file_path, 'r') as f:
            content = f.read()
        
        payload = {
            "content": content,
            "quality_level": quality_level,
            "strict_mode": strict_mode
        }
        response = await cli_ctx.api_client.request("POST", "/okw/upload", json_data=payload)
        return response
    
    async def fallback_upload():
        """Fallback upload using direct services"""
        with open(file_path, 'r') as f:
            content = f.read()
        
        facility = OKWFacility.from_json(content)
        okw_service = await OKWService.get_instance()
        result = await okw_service.create(facility)
        return result.to_dict()
    
    command = SmartCommand(cli_ctx)
    result = asyncio.run(command.execute_with_fallback(http_upload, fallback_upload))
    
    facility_id = result.get("id") or result.get("facility", {}).get("id")
    
    if facility_id:
        echo_success(f"OKW facility uploaded with ID: {facility_id}")
    else:
        echo_error("Failed to upload OKW facility")


@okw_group.command()
@click.option('--query', '-q', help='Search query')
@click.option('--domain', help='Filter by domain')
@click.option('--capability', help='Filter by capability type')
@click.option('--location', help='Filter by location')
@click.option('--limit', default=10, type=int, help='Maximum number of results')
@click.pass_context
def search(ctx, query: str, domain: str, capability: str, location: str, limit: int):
    """Search OKW facilities"""
    cli_ctx = ctx.obj
    
    async def http_search():
        """Search facilities via HTTP API"""
        params = {
            "query": query,
            "domain": domain,
            "capability": capability,
            "location": location,
            "limit": limit
        }
        # Remove None values
        params = {k: v for k, v in params.items() if v is not None}
        
        response = await cli_ctx.api_client.request("GET", "/okw/search", params=params)
        return response
    
    async def fallback_search():
        """Fallback search using direct services"""
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
    
    command = SmartCommand(cli_ctx)
    result = asyncio.run(command.execute_with_fallback(http_search, fallback_search))
    
    facilities = result.get("facilities", [])
    total = result.get("total", len(facilities))
    
    if facilities:
        echo_success(f"Found {total} facilities")
        for i, facility in enumerate(facilities, 1):
            click.echo(f"{i}. {facility.get('name', 'Unknown')} - {facility.get('location', 'Unknown location')}")
    else:
        echo_info("No facilities found matching criteria")
