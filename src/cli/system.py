"""
System management commands for OME CLI

This module provides system-level commands including health checks,
domain information, and server status.
"""

import click
import asyncio
import httpx
from typing import Optional

from .base import (
    CLIContext, SmartCommand, with_async_context, 
    echo_success, echo_error, echo_info, format_json_output
)


@click.group()
def system_group():
    """System management commands"""
    pass


@system_group.command()
@click.pass_context
def health(ctx):
    """Check system health and status"""
    cli_ctx = ctx.obj
    
    async def http_health_check():
        """Check health via HTTP API"""
        # Health endpoint is at root level, not under /v1
        async with httpx.AsyncClient(timeout=cli_ctx.config.timeout) as client:
            response = await client.get(f"{cli_ctx.config.server_url}/health")
            response.raise_for_status()
            return response.json()
    
    async def fallback_health_check():
        """Fallback health check using direct services"""
        # Try to initialize services to check if they're working
        try:
            from ..core.registry.domain_registry import DomainRegistry
            domains = list(DomainRegistry.get_registered_domains())
            return {
                "status": "ok",
                "domains": domains,
                "version": "1.0.0",
                "mode": "fallback"
            }
        except Exception as e:
            return {
                "status": "error",
                "error": str(e),
                "mode": "fallback"
            }
    
    command = SmartCommand(cli_ctx)
    result = asyncio.run(command.execute_with_fallback(http_health_check, fallback_health_check))
    
    if result.get("status") == "ok":
        echo_success("System is healthy")
        if cli_ctx.output_format == 'json':
            click.echo(format_json_output(result))
        else:
            click.echo(f"Status: {result['status']}")
            click.echo(f"Version: {result.get('version', 'Unknown')}")
            click.echo(f"Mode: {result.get('mode', 'unknown')}")
            if 'domains' in result:
                click.echo(f"Registered domains: {', '.join(result['domains'])}")
    else:
        echo_error(f"System health check failed: {result.get('error', 'Unknown error')}")
        if cli_ctx.verbose:
            click.echo(format_json_output(result))


@system_group.command()
@click.pass_context
def domains(ctx):
    """List available domains and their status"""
    cli_ctx = ctx.obj
    
    async def http_domains():
        """Get domains via HTTP API"""
        # Use the utility domains endpoint
        response = await cli_ctx.api_client.request("GET", "/domains")
        return response
    
    async def fallback_domains():
        """Get domains using direct service calls"""
        from ..core.registry.domain_registry import DomainRegistry
        domains = DomainRegistry.get_registered_domains()
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


@system_group.command()
@click.pass_context
def status(ctx):
    """Show detailed system status"""
    cli_ctx = ctx.obj
    
    async def http_status():
        """Get status via HTTP API"""
        # Get multiple endpoints for comprehensive status
        health_response = await cli_ctx.api_client.request("GET", "/health")
        domains_response = await cli_ctx.api_client.request("GET", "/utility/domains")
        
        return {
            "health": health_response,
            "domains": domains_response,
            "server_url": cli_ctx.config.server_url,
            "mode": "http"
        }
    
    async def fallback_status():
        """Get status using direct service calls"""
        from ..core.registry.domain_registry import DomainRegistry
        
        domains = list(DomainRegistry.get_registered_domains())
        
        return {
            "health": {
                "status": "ok",
                "domains": domains,
                "version": "1.0.0"
            },
            "domains": {
                "domains": [
                    {
                        "id": domain,
                        "name": domain.title(),
                        "description": f"{domain.title()} domain",
                        "status": "active"
                    }
                    for domain in domains
                ]
            },
            "server_url": "N/A (direct mode)",
            "mode": "fallback"
        }
    
    command = SmartCommand(cli_ctx)
    result = asyncio.run(command.execute_with_fallback(http_status, fallback_status))
    
    if cli_ctx.output_format == 'json':
        click.echo(format_json_output(result))
    else:
        click.echo("=== OME System Status ===")
        click.echo(f"Server URL: {result['server_url']}")
        click.echo(f"Mode: {result['mode']}")
        click.echo()
        
        health = result.get("health", {})
        click.echo(f"Health Status: {health.get('status', 'unknown')}")
        click.echo(f"Version: {health.get('version', 'unknown')}")
        click.echo()
        
        domains = result.get("domains", {}).get("domains", [])
        click.echo(f"Registered Domains ({len(domains)}):")
        for domain in domains:
            status_icon = "✅" if domain.get("status") == "active" else "❌"
            click.echo(f"  {status_icon} {domain['id']}")


@system_group.command()
@click.option('--port', default=8001, help='Port to check')
@click.option('--timeout', default=5, help='Connection timeout in seconds')
@click.pass_context
def ping(ctx, port: int, timeout: int):
    """Ping the OME server"""
    import socket
    import time
    
    cli_ctx = ctx.obj
    server_host = cli_ctx.config.server_url.replace('http://', '').replace('https://', '').split(':')[0]
    
    try:
        start_time = time.time()
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(timeout)
        result = sock.connect_ex((server_host, port))
        sock.close()
        
        if result == 0:
            response_time = (time.time() - start_time) * 1000
            echo_success(f"Server is reachable (response time: {response_time:.2f}ms)")
        else:
            echo_error(f"Server is not reachable on {server_host}:{port}")
    except Exception as e:
        echo_error(f"Ping failed: {str(e)}")


@system_group.command()
@click.pass_context
def info(ctx):
    """Show OME system information"""
    from . import __version__
    
    click.echo("=== Open Matching Engine (OME) ===")
    click.echo(f"CLI Version: {__version__}")
    click.echo(f"Server URL: {ctx.obj.config.server_url}")
    click.echo(f"Timeout: {ctx.obj.config.timeout}s")
    click.echo(f"Verbose Mode: {ctx.obj.config.verbose}")
    click.echo()
    click.echo("Available Commands:")
    click.echo("  package  - Package management (build, push, pull, list)")
    click.echo("  okh      - OKH manifest operations")
    click.echo("  okw      - OKW facility operations") 
    click.echo("  match    - Matching operations")
    click.echo("  system   - System management")
    click.echo()
    click.echo("For more information, use: ome <command> --help")
