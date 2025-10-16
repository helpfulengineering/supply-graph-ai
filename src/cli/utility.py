"""
Utility CLI Commands

Commands for utility operations in the Open Matching Engine.
"""

import click
import asyncio
from typing import Optional
from ..core.registry.domain_registry import DomainRegistry

from .base import (
    CLIContext, SmartCommand, 
    echo_success, echo_info, format_json_output
)


@click.group()
def utility_group():
    """Utility commands"""
    pass


@utility_group.command()
@click.option('--name', help='Filter domains by name')
@click.pass_context
def domains(ctx, name: Optional[str]):
    """List available domains"""
    cli_ctx = ctx.obj
    
    async def http_domains():
        """Get domains via HTTP API"""
        params = {}
        if name:
            params["name"] = name
        
        response = await cli_ctx.api_client.request("GET", "/domains", params=params)
        return response
    
    async def fallback_domains():
        """Get domains using direct service calls"""        
        domains = DomainRegistry.get_registered_domains()
        
        # Apply name filter if provided
        if name:
            domains = [d for d in domains if name.lower() in d.lower()]
        
        return {
            "domains": [
                {
                    "id": domain,
                    "name": domain.title(),
                    "description": f"{domain.title()} domain",
                    "status": "active"
                }
                for domain in domains
            ]
        }
    
    command = SmartCommand(cli_ctx)
    result = asyncio.run(command.execute_with_fallback(http_domains, fallback_domains))
    
    domains = result.get("domains", [])
    
    if cli_ctx.output_format == 'json':
        click.echo(format_json_output(result))
    else:
        if domains:
            echo_success(f"Found {len(domains)} domains")
            for domain in domains:
                status_icon = "✅" if domain.get("status", "active") == "active" else "❌"
                click.echo(f"{status_icon} {domain['id']}: {domain.get('name', 'Unknown')}")
                if domain.get('description'):
                    click.echo(f"   {domain['description']}")
        else:
            echo_info("No domains found")


@utility_group.command()
@click.argument('domain')
@click.option('--name', help='Filter contexts by name')
@click.pass_context
def contexts(ctx, domain: str, name: Optional[str]):
    """List validation contexts for a specific domain"""
    cli_ctx = ctx.obj
    
    async def http_contexts():
        """Get contexts via HTTP API"""
        params = {}
        if name:
            params["name"] = name
        
        response = await cli_ctx.api_client.request("GET", f"/contexts/{domain}", params=params)
        return response
    
    async def fallback_contexts():
        """Get contexts using direct service calls"""
        # Get domain-specific contexts
        if domain == "manufacturing":
            contexts = [
                {
                    "id": "hobby",
                    "name": "Hobby Manufacturing",
                    "description": "Non-commercial, limited quality requirements"
                },
                {
                    "id": "professional",
                    "name": "Professional Manufacturing",
                    "description": "Commercial-grade production"
                }
            ]
        elif domain == "cooking":
            contexts = [
                {
                    "id": "home",
                    "name": "Home Cooking",
                    "description": "Basic home kitchen capabilities"
                },
                {
                    "id": "commercial",
                    "name": "Commercial Kitchen",
                    "description": "Professional kitchen capabilities"
                }
            ]
        else:
            contexts = []
        
        # Apply name filter if provided
        if name:
            contexts = [c for c in contexts if name.lower() in c["name"].lower()]
        
        return {
            "contexts": contexts
        }
    
    command = SmartCommand(cli_ctx)
    result = asyncio.run(command.execute_with_fallback(http_contexts, fallback_contexts))
    
    contexts = result.get("contexts", [])
    
    if cli_ctx.output_format == 'json':
        click.echo(format_json_output(result))
    else:
        if contexts:
            echo_success(f"Found {len(contexts)} contexts for domain '{domain}'")
            for context in contexts:
                click.echo(f"✅ {context['id']}: {context.get('name', 'Unknown')}")
                if context.get('description'):
                    click.echo(f"   {context['description']}")
        else:
            echo_info(f"No contexts found for domain '{domain}'")
