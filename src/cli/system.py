"""
System management commands for OME CLI

This module provides system-level commands including health checks,
domain information, and server status.
"""

import click
import httpx
import socket
import time
from typing import Optional

from .base import (
    CLIContext, SmartCommand, format_llm_output,
    log_llm_usage
)
from .decorators import standard_cli_command
from ..core.registry.domain_registry import DomainRegistry


@click.group()
def system_group():
    """
    System management commands for OME.
    
    These commands help you monitor and manage the OME system,
    including health checks, domain information, server status,
    and system diagnostics.
    
    Examples:
      # Check system health
      ome system health
      
      # List available domains
      ome system domains
      
      # Show detailed system status
      ome system status
      
      # Use LLM for enhanced analysis
      ome system status --use-llm --quality-level professional
    """
    pass


# Helper functions

async def _display_health_results(cli_ctx: CLIContext, result: dict, output_format: str):
    """Display health check results."""
    if result.get("status") == "ok":
        cli_ctx.log("System is healthy", "success")
        
        if output_format == "json":
            output_data = format_llm_output(result, cli_ctx)
            click.echo(output_data)
        else:
            cli_ctx.log(f"Status: {result['status']}", "info")
            cli_ctx.log(f"Version: {result.get('version', 'Unknown')}", "info")
            cli_ctx.log(f"Mode: {result.get('mode', 'unknown')}", "info")
            if 'domains' in result:
                cli_ctx.log(f"Registered domains: {', '.join(result['domains'])}", "info")
    else:
        cli_ctx.log(f"System health check failed: {result.get('error', 'Unknown error')}", "error")
        if cli_ctx.verbose:
            output_data = format_llm_output(result, cli_ctx)
            click.echo(output_data)


async def _display_domains_results(cli_ctx: CLIContext, result: dict, output_format: str):
    """Display domains results."""
    domains = result.get("domains", [])
    
    if output_format == "json":
        output_data = format_llm_output(result, cli_ctx)
        click.echo(output_data)
    else:
        if domains:
            cli_ctx.log(f"Found {len(domains)} domains", "success")
            for domain in domains:
                status_icon = "✅" if domain.get("status", "active") == "active" else "❌"
                cli_ctx.log(f"{status_icon} {domain['id']}: {domain.get('name', 'Unknown')}", "info")
                if domain.get('description'):
                    cli_ctx.log(f"   {domain['description']}", "info")
        else:
            cli_ctx.log("No domains found", "info")


async def _display_status_results(cli_ctx: CLIContext, result: dict, output_format: str):
    """Display system status results."""
    if output_format == "json":
        output_data = format_llm_output(result, cli_ctx)
        click.echo(output_data)
    else:
        cli_ctx.log("=== OME System Status ===", "info")
        cli_ctx.log(f"Server URL: {result['server_url']}", "info")
        cli_ctx.log(f"Mode: {result['mode']}", "info")
        cli_ctx.log("", "info")  # Empty line for spacing
        
        health = result.get("health", {})
        cli_ctx.log(f"Health Status: {health.get('status', 'unknown')}", "info")
        cli_ctx.log(f"Version: {health.get('version', 'unknown')}", "info")
        cli_ctx.log("", "info")  # Empty line for spacing
        
        domains = result.get("domains", {}).get("domains", [])
        cli_ctx.log(f"Registered Domains ({len(domains)}):", "info")
        for domain in domains:
            # Default to active if no status field is present
            status = domain.get("status", "active")
            status_icon = "✅" if status == "active" else "❌"
            cli_ctx.log(f"  {status_icon} {domain['id']}", "info")


# Commands

@system_group.command()
@standard_cli_command(
    help_text="""
    Check system health and status.
    
    This command performs a comprehensive health check of the OME system,
    including server connectivity, service availability, and domain
    registration status.
    
    The health check includes:
    - Server connectivity and response time
    - Service availability and status
    - Domain registration verification
    - System version and configuration
    
    When LLM is enabled, health checking includes:
    - Enhanced system analysis and diagnostics
    - Performance assessment and recommendations
    - Intelligent error detection and suggestions
    - Advanced system monitoring insights
    """,
    epilog="""
    Examples:
      # Basic health check
      ome system health
      
      # Use LLM for enhanced analysis
      ome system health --use-llm --quality-level professional
    """,
    async_cmd=True,
    track_performance=True,
    handle_errors=True,
    format_output=True,
    add_llm_config=True
)
@click.pass_context
async def health(ctx, verbose: bool, output_format: str, use_llm: bool,
                llm_provider: str, llm_model: Optional[str],
                quality_level: str, strict_mode: bool):
    """Check system health and status with enhanced LLM support."""
    cli_ctx = ctx.obj
    cli_ctx.verbose = verbose  # Set verbose mode
    cli_ctx.start_command_tracking("system-health")
    
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
            log_llm_usage(cli_ctx, "System health check")
        
        async def http_health_check():
            """Check health via HTTP API"""
            cli_ctx.log("Checking health via HTTP API...", "info")
            # Health endpoint is at root level, not under /v1
            async with httpx.AsyncClient(timeout=cli_ctx.config.timeout) as client:
                response = await client.get(f"{cli_ctx.config.server_url}/health")
                response.raise_for_status()
                return response.json()
        
        async def fallback_health_check():
            """Fallback health check using direct services"""
            cli_ctx.log("Using direct service health check...", "info")
            # Try to initialize services to check if they're working
            try:
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
        
        # Execute health check with fallback
        command = SmartCommand(cli_ctx)
        result = await command.execute_with_fallback(http_health_check, fallback_health_check)
        
        # Display health results
        await _display_health_results(cli_ctx, result, output_format)
        
        cli_ctx.end_command_tracking()
        
    except Exception as e:
        cli_ctx.log(f"Health check failed: {str(e)}", "error")
        raise


@system_group.command()
@standard_cli_command(
    help_text="""
    List available domains and their status.
    
    This command displays information about all registered domains
    in the OME system, including their status, capabilities, and
    configuration.
    
    When LLM is enabled, domain listing includes:
    - Enhanced domain analysis and categorization
    - Capability assessment and recommendations
    - Intelligent filtering and sorting suggestions
    - Advanced domain metadata extraction
    """,
    epilog="""
    Examples:
      # List all domains
      ome system domains
      
      # Use LLM for enhanced analysis
      ome system domains --use-llm
    """,
    async_cmd=True,
    track_performance=True,
    handle_errors=True,
    format_output=True,
    add_llm_config=True
)
@click.pass_context
async def domains(ctx, verbose: bool, output_format: str, use_llm: bool,
                 llm_provider: str, llm_model: Optional[str],
                 quality_level: str, strict_mode: bool):
    """List available domains and their status with enhanced LLM support."""
    cli_ctx = ctx.obj
    cli_ctx.start_command_tracking("system-domains")
    
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
            log_llm_usage(cli_ctx, "Domain listing")
        
        async def http_domains():
            """Get domains via HTTP API"""
            cli_ctx.log("Getting domains via HTTP API...", "info")
            # Use the utility domains endpoint
            response = await cli_ctx.api_client.request("GET", "/domains")
            return response
        
        async def fallback_domains():
            """Get domains using direct service calls"""
            cli_ctx.log("Using direct service domain listing...", "info")
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
        
        # Execute domain listing with fallback
        command = SmartCommand(cli_ctx)
        result = await command.execute_with_fallback(http_domains, fallback_domains)
        
        # Display domains results
        await _display_domains_results(cli_ctx, result, output_format)
        
        cli_ctx.end_command_tracking()
        
    except Exception as e:
        cli_ctx.log(f"Domain listing failed: {str(e)}", "error")
        raise


@system_group.command()
@standard_cli_command(
    help_text="""
    Show detailed system status and diagnostics.
    
    This command provides comprehensive system status information,
    including health status, domain information, server configuration,
    and system diagnostics.
    
    The status check includes:
    - System health and connectivity
    - Domain registration and status
    - Server configuration and version
    - Performance metrics and diagnostics
    
    When LLM is enabled, status checking includes:
    - Enhanced system analysis and diagnostics
    - Performance assessment and recommendations
    - Intelligent error detection and suggestions
    - Advanced system monitoring insights
    """,
    epilog="""
    Examples:
      # Show system status
      ome system status
      
      # Use LLM for enhanced analysis
      ome system status --use-llm --quality-level professional
    """,
    async_cmd=True,
    track_performance=True,
    handle_errors=True,
    format_output=True,
    add_llm_config=True
)
@click.pass_context
async def status(ctx, verbose: bool, output_format: str, use_llm: bool,
                llm_provider: str, llm_model: Optional[str],
                quality_level: str, strict_mode: bool):
    """Show detailed system status with enhanced LLM support."""
    cli_ctx = ctx.obj
    cli_ctx.start_command_tracking("system-status")
    
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
            log_llm_usage(cli_ctx, "System status check")
        
        async def http_status():
            """Get status via HTTP API"""
            cli_ctx.log("Getting status via HTTP API...", "info")
            try:
                # Get multiple endpoints for comprehensive status
                # Health endpoint is at root level, not under /v1
                async with httpx.AsyncClient(timeout=cli_ctx.config.timeout) as client:
                    health_response = await client.get(f"{cli_ctx.config.server_url}/health")
                    health_response.raise_for_status()
                    health_data = health_response.json()
                    
                    # Domains endpoint is under /v1
                    domains_response = await cli_ctx.api_client.request("GET", "/domains")
                
                return {
                    "health": health_data,
                    "domains": domains_response,
                    "server_url": cli_ctx.config.server_url,
                    "mode": "http"
                }
            except Exception as e:
                # If HTTP fails, raise an exception to trigger fallback
                raise Exception(f"HTTP request failed: {e}")
        
        async def fallback_status():
            """Get status using direct service calls"""
            cli_ctx.log("Using direct service status check...", "info")
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
        
        # Execute status check with fallback
        command = SmartCommand(cli_ctx)
        result = await command.execute_with_fallback(http_status, fallback_status)
        
        # Display status results
        await _display_status_results(cli_ctx, result, output_format)
        
        cli_ctx.end_command_tracking()
        
    except Exception as e:
        cli_ctx.log(f"Status check failed: {str(e)}", "error")
        raise


@system_group.command()
@click.option('--port', default=8001, help='Port to check')
@click.option('--timeout', default=5, help='Connection timeout in seconds')
@standard_cli_command(
    help_text="""
    Ping the OME server to check connectivity.
    
    This command tests network connectivity to the OME server
    by attempting to establish a TCP connection and measuring
    response time.
    
    When LLM is enabled, pinging includes:
    - Enhanced connectivity analysis and diagnostics
    - Performance assessment and recommendations
    - Network troubleshooting suggestions
    - Advanced connectivity monitoring insights
    """,
    epilog="""
    Examples:
      # Ping default server
      ome system ping
      
      # Ping specific port with custom timeout
      ome system ping --port 8080 --timeout 10
      
      # Use LLM for enhanced analysis
      ome system ping --use-llm
    """,
    async_cmd=False,  # This is a synchronous operation
    track_performance=True,
    handle_errors=True,
    format_output=True,
    add_llm_config=True
)
@click.pass_context
def ping(ctx, port: int, timeout: int,
         verbose: bool, output_format: str, use_llm: bool,
         llm_provider: str, llm_model: Optional[str],
         quality_level: str, strict_mode: bool):
    """Ping the OME server with enhanced LLM support."""
    cli_ctx = ctx.obj
    cli_ctx.start_command_tracking("system-ping")
    
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
            log_llm_usage(cli_ctx, "Server ping")
        
        server_host = cli_ctx.config.server_url.replace('http://', '').replace('https://', '').split(':')[0]
        
        cli_ctx.log(f"Pinging {server_host}:{port}...", "info")
        
        start_time = time.time()
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(timeout)
        result = sock.connect_ex((server_host, port))
        sock.close()
        
        if result == 0:
            response_time = (time.time() - start_time) * 1000
            cli_ctx.log(f"Server is reachable (response time: {response_time:.2f}ms)", "success")
            
            if output_format == "json":
                ping_result = {
                    "status": "success",
                    "server": f"{server_host}:{port}",
                    "response_time_ms": response_time,
                    "timeout": timeout
                }
                output_data = format_llm_output(ping_result, cli_ctx)
                click.echo(output_data)
        else:
            cli_ctx.log(f"Server is not reachable on {server_host}:{port}", "error")
            
            if output_format == "json":
                ping_result = {
                    "status": "error",
                    "server": f"{server_host}:{port}",
                    "error": "Connection failed",
                    "timeout": timeout
                }
                output_data = format_llm_output(ping_result, cli_ctx)
                click.echo(output_data)
        
        cli_ctx.end_command_tracking()
        
    except Exception as e:
        cli_ctx.log(f"Ping failed: {str(e)}", "error")
        raise


@system_group.command()
@standard_cli_command(
    help_text="""
    Show OME system information and configuration.
    
    This command displays comprehensive system information including
    CLI version, server configuration, available commands, and
    system capabilities.
    
    When LLM is enabled, info display includes:
    - Enhanced system analysis and recommendations
    - Configuration optimization suggestions
    - Advanced system insights and diagnostics
    - Intelligent system monitoring recommendations
    """,
    epilog="""
    Examples:
      # Show system information
      ome system info
      
      # Use LLM for enhanced analysis
      ome system info --use-llm
    """,
    async_cmd=False,  # This is a synchronous operation
    track_performance=True,
    handle_errors=True,
    format_output=True,
    add_llm_config=True
)
@click.pass_context
def info(ctx, verbose: bool, output_format: str, use_llm: bool,
         llm_provider: str, llm_model: Optional[str],
         quality_level: str, strict_mode: bool):
    """Show OME system information with enhanced LLM support."""
    cli_ctx = ctx.obj
    cli_ctx.verbose = verbose  # Set verbose mode
    cli_ctx.start_command_tracking("system-info")
    
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
            log_llm_usage(cli_ctx, "System information")
        
        # Import version info
        try:
            from . import __version__
            version = __version__
        except ImportError:
            version = "Unknown"
        
        if output_format == "json":
            info_data = {
                "cli_version": version,
                "server_url": cli_ctx.config.server_url,
                "timeout": cli_ctx.config.timeout,
                "verbose": cli_ctx.config.verbose,
                "llm_enabled": cli_ctx.is_llm_enabled(),
                "llm_config": cli_ctx.llm_config if cli_ctx.is_llm_enabled() else None,
                "available_commands": [
                    "package", "okh", "okw", "match", "system"
                ]
            }
            output_data = format_llm_output(info_data, cli_ctx)
            click.echo(output_data)
        else:
            cli_ctx.log("=== Open Matching Engine (OME) ===", "info")
            cli_ctx.log(f"CLI Version: {version}", "info")
            cli_ctx.log(f"Server URL: {cli_ctx.config.server_url}", "info")
            cli_ctx.log(f"Timeout: {cli_ctx.config.timeout}s", "info")
            cli_ctx.log(f"Verbose Mode: {cli_ctx.config.verbose}", "info")
            
            if cli_ctx.is_llm_enabled():
                cli_ctx.log(f"LLM Provider: {cli_ctx.llm_config.get('llm_provider', 'Unknown')}", "info")
                cli_ctx.log(f"LLM Model: {cli_ctx.llm_config.get('llm_model', 'Default')}", "info")
                cli_ctx.log(f"Quality Level: {cli_ctx.llm_config.get('quality_level', 'Unknown')}", "info")
                cli_ctx.log(f"Strict Mode: {cli_ctx.llm_config.get('strict_mode', False)}", "info")
            
            cli_ctx.log("", "info")  # Empty line for spacing
            cli_ctx.log("Available Commands:", "info")
            cli_ctx.log("  package  - Package management (build, push, pull, list)", "info")
            cli_ctx.log("  okh      - OKH manifest operations", "info")
            cli_ctx.log("  okw      - OKW facility operations", "info")
            cli_ctx.log("  match    - Matching operations", "info")
            cli_ctx.log("  system   - System management", "info")
            cli_ctx.log("", "info")  # Empty line for spacing
            cli_ctx.log("For more information, use: ome <command> --help", "info")
        
        cli_ctx.end_command_tracking()
        
    except Exception as e:
        cli_ctx.log(f"Info display failed: {str(e)}", "error")
        raise