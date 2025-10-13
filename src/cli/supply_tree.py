"""
Supply Tree CLI Commands

Commands for managing supply trees in the Open Matching Engine.
"""

import click
import asyncio
from typing import Optional
from uuid import UUID

from .base import (
    CLIContext, SmartCommand, 
    echo_success, echo_error, echo_info, format_json_output
)


@click.group()
def supply_tree_group():
    """Supply Tree management commands"""
    pass


@supply_tree_group.command()
@click.argument('okh_manifest_id')
@click.argument('okw_facility_id')
@click.option('--context', help='Validation context (e.g., "manufacturing", "hobby")')
@click.option('--quality-level', default='basic', type=click.Choice(['basic', 'standard', 'premium']), help='Validation quality level')
@click.option('--strict-mode', is_flag=True, help='Enable strict validation mode')
@click.pass_context
def create(ctx, okh_manifest_id: str, okw_facility_id: str, context: Optional[str], quality_level: str, strict_mode: bool):
    """Create a new supply tree from OKH manifest and OKW facility"""
    cli_ctx = ctx.obj
    
    async def http_create():
        """Create supply tree via HTTP API"""
        payload = {
            "okh_manifest_id": okh_manifest_id,
            "okw_facility_id": okw_facility_id,
            "context": context,
            "quality_level": quality_level,
            "strict_mode": strict_mode
        }
        response = await cli_ctx.api_client.request("POST", "/supply-tree/create", json_data=payload)
        return response
    
    async def fallback_create():
        """Create supply tree using direct service calls"""
        from ..core.services.supply_tree_service import SupplyTreeService
        from ..core.services.okh_service import OKHService
        from ..core.services.okw_service import OKWService
        
        # Get services
        supply_tree_service = await SupplyTreeService.get_instance()
        okh_service = await OKHService.get_instance()
        okw_service = await OKWService.get_instance()
        
        # Get manifest and facility
        manifest = await okh_service.get(UUID(okh_manifest_id))
        facility = await okw_service.get(UUID(okw_facility_id))
        
        if not manifest:
            raise click.ClickException(f"OKH manifest {okh_manifest_id} not found")
        if not facility:
            raise click.ClickException(f"OKW facility {okw_facility_id} not found")
        
        # Create supply tree
        result = await supply_tree_service.create_supply_tree(manifest, facility, context)
        return result.to_dict()
    
    command = SmartCommand(cli_ctx)
    result = asyncio.run(command.execute_with_fallback(http_create, fallback_create))
    
    supply_tree_id = result.get("id") or result.get("supply_tree", {}).get("id")
    
    if supply_tree_id:
        echo_success(f"Supply tree created with ID: {supply_tree_id}")
        if cli_ctx.output_format == 'json':
            click.echo(format_json_output(result))
    else:
        echo_error("Failed to create supply tree")


@supply_tree_group.command()
@click.argument('supply_tree_id')
@click.pass_context
def get(ctx, supply_tree_id: str):
    """Get a supply tree by ID"""
    cli_ctx = ctx.obj
    
    async def http_get():
        """Get supply tree via HTTP API"""
        response = await cli_ctx.api_client.request("GET", f"/supply-tree/{supply_tree_id}")
        return response
    
    async def fallback_get():
        """Get supply tree using direct service calls"""
        from ..core.services.supply_tree_service import SupplyTreeService
        
        supply_tree_service = await SupplyTreeService.get_instance()
        supply_tree = await supply_tree_service.get(UUID(supply_tree_id))
        
        if supply_tree:
            return supply_tree.to_dict()
        else:
            raise click.ClickException("Supply tree not found")
    
    command = SmartCommand(cli_ctx)
    result = asyncio.run(command.execute_with_fallback(http_get, fallback_get))
    
    supply_tree = result.get("supply_tree", result)
    
    if supply_tree:
        echo_success(f"Retrieved supply tree: {supply_tree.get('id', 'Unknown')}")
        if cli_ctx.output_format == 'json':
            click.echo(format_json_output(result))
        else:
            # Display key information
            click.echo(f"ID: {supply_tree.get('id', 'Unknown')}")
            click.echo(f"Status: {supply_tree.get('status', 'Unknown')}")
            click.echo(f"Created: {supply_tree.get('created_at', 'Unknown')}")
    else:
        echo_error("Supply tree not found")


@supply_tree_group.command()
@click.option('--limit', default=10, type=int, help='Maximum number of results')
@click.option('--offset', default=0, type=int, help='Number of results to skip')
@click.option('--status', help='Filter by status')
@click.pass_context
def list(ctx, limit: int, offset: int, status: Optional[str]):
    """List all supply trees"""
    cli_ctx = ctx.obj
    
    async def http_list():
        """List supply trees via HTTP API"""
        params = {
            "limit": limit,
            "offset": offset
        }
        if status:
            params["status"] = status
        
        response = await cli_ctx.api_client.request("GET", "/supply-tree/", params=params)
        return response
    
    async def fallback_list():
        """List supply trees using direct service calls"""
        from ..core.services.supply_tree_service import SupplyTreeService
        
        supply_tree_service = await SupplyTreeService.get_instance()
        supply_trees = await supply_tree_service.list_supply_trees(limit=limit, offset=offset, status=status)
        
        return {
            "supply_trees": [st.to_dict() for st in supply_trees],
            "total": len(supply_trees)
        }
    
    command = SmartCommand(cli_ctx)
    result = asyncio.run(command.execute_with_fallback(http_list, fallback_list))
    
    supply_trees = result.get("supply_trees", [])
    total = result.get("total", len(supply_trees))
    
    if supply_trees:
        echo_success(f"Found {total} supply trees")
        if cli_ctx.output_format == 'json':
            click.echo(format_json_output(result))
        else:
            for i, st in enumerate(supply_trees, 1):
                click.echo(f"{i}. {st.get('id', 'Unknown')} - {st.get('status', 'Unknown status')}")
    else:
        echo_info("No supply trees found")


@supply_tree_group.command()
@click.argument('supply_tree_id')
@click.pass_context
def delete(ctx, supply_tree_id: str):
    """Delete a supply tree"""
    cli_ctx = ctx.obj
    
    async def http_delete():
        """Delete supply tree via HTTP API"""
        response = await cli_ctx.api_client.request("DELETE", f"/supply-tree/{supply_tree_id}")
        return response
    
    async def fallback_delete():
        """Delete supply tree using direct service calls"""
        from ..core.services.supply_tree_service import SupplyTreeService
        
        supply_tree_service = await SupplyTreeService.get_instance()
        success = await supply_tree_service.delete(UUID(supply_tree_id))
        return {"success": success}
    
    command = SmartCommand(cli_ctx)
    result = asyncio.run(command.execute_with_fallback(http_delete, fallback_delete))
    
    if result.get("success", True):  # HTTP API returns success by default
        echo_success(f"Supply tree {supply_tree_id} deleted successfully")
    else:
        echo_error(f"Failed to delete supply tree {supply_tree_id}")


@supply_tree_group.command()
@click.argument('supply_tree_id')
@click.option('--context', help='Validation context')
@click.option('--quality-level', default='basic', type=click.Choice(['basic', 'standard', 'premium']), help='Validation quality level')
@click.option('--strict-mode', is_flag=True, help='Enable strict validation mode')
@click.pass_context
def validate(ctx, supply_tree_id: str, context: Optional[str], quality_level: str, strict_mode: bool):
    """Validate a supply tree"""
    cli_ctx = ctx.obj
    
    async def http_validate():
        """Validate supply tree via HTTP API"""
        payload = {
            "context": context,
            "quality_level": quality_level,
            "strict_mode": strict_mode
        }
        response = await cli_ctx.api_client.request("POST", f"/supply-tree/{supply_tree_id}/validate", json_data=payload)
        return response
    
    async def fallback_validate():
        """Validate supply tree using direct service calls"""
        from ..core.services.supply_tree_service import SupplyTreeService
        
        supply_tree_service = await SupplyTreeService.get_instance()
        supply_tree = await supply_tree_service.get(UUID(supply_tree_id))
        
        if not supply_tree:
            raise click.ClickException("Supply tree not found")
        
        result = await supply_tree_service.validate_supply_tree(supply_tree, context, quality_level, strict_mode)
        return result.to_dict()
    
    command = SmartCommand(cli_ctx)
    result = asyncio.run(command.execute_with_fallback(http_validate, fallback_validate))
    
    validation = result.get("validation", result)
    
    if cli_ctx.output_format == 'json':
        click.echo(format_json_output(result))
    else:
        if validation.get("is_valid", False):
            echo_success("Supply tree validation passed")
        else:
            echo_error("Supply tree validation failed")
        
        if cli_ctx.config.verbose:
            click.echo(f"Validation details: {validation.get('details', 'No details available')}")
