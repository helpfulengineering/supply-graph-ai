"""
Utility CLI Commands

Commands for utility operations in the Open Matching Engine.
"""

import click
from typing import Optional
from ..core.registry.domain_registry import DomainRegistry

from .base import (
    CLIContext, SmartCommand, format_llm_output,
    log_llm_usage
)
from .decorators import standard_cli_command


@click.group()
def utility_group():
    """
    Utility commands for OME.
    
    These commands provide utility operations for the Open Matching Engine,
    including domain listing, validation context management, and system
    information utilities.
    
    Examples:
      # List available domains
      ome utility domains
      
      # List validation contexts for a domain
      ome utility contexts manufacturing
      
      # Use LLM for enhanced analysis
      ome utility domains --use-llm --quality-level professional
    """
    pass


# Helper functions

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


async def _display_contexts_results(cli_ctx: CLIContext, result: dict, domain: str, output_format: str):
    """Display contexts results."""
    contexts = result.get("contexts", [])
    
    if output_format == "json":
        output_data = format_llm_output(result, cli_ctx)
        click.echo(output_data)
    else:
        if contexts:
            cli_ctx.log(f"Found {len(contexts)} contexts for domain '{domain}'", "success")
            for context in contexts:
                cli_ctx.log(f"✅ {context['id']}: {context.get('name', 'Unknown')}", "info")
                if context.get('description'):
                    cli_ctx.log(f"   {context['description']}", "info")
        else:
            cli_ctx.log(f"No contexts found for domain '{domain}'", "info")


# Commands

@utility_group.command()
@click.option('--name', help='Filter domains by name')
@standard_cli_command(
    help_text="""
    List available domains in the OME system.
    
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
      ome utility domains
      
      # Filter domains by name
      ome utility domains --name manufacturing
      
      # Use LLM for enhanced analysis
      ome utility domains --use-llm --quality-level professional
    """,
    async_cmd=True,
    track_performance=True,
    handle_errors=True,
    format_output=True,
    add_llm_config=True
)
@click.pass_context
async def domains(ctx, name: Optional[str],
                 verbose: bool, output_format: str, use_llm: bool,
                 llm_provider: str, llm_model: Optional[str],
                 quality_level: str, strict_mode: bool):
    """List available domains with enhanced LLM support."""
    cli_ctx = ctx.obj
    cli_ctx.verbose = verbose  # Set verbose mode
    cli_ctx.start_command_tracking("utility-domains")
    
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
            params = {}
            if name:
                params["name"] = name
            
            response = await cli_ctx.api_client.request("GET", "/domains", params=params)
            return response
        
        async def fallback_domains():
            """Get domains using direct service calls"""
            cli_ctx.log("Using direct service domain listing...", "info")
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
        
        # Execute domain listing with fallback
        command = SmartCommand(cli_ctx)
        result = await command.execute_with_fallback(http_domains, fallback_domains)
        
        # Display domains results
        await _display_domains_results(cli_ctx, result, output_format)
        
        cli_ctx.end_command_tracking()
        
    except Exception as e:
        cli_ctx.log(f"Domain listing failed: {str(e)}", "error")
        raise


@utility_group.command()
@click.argument('domain')
@click.option('--name', help='Filter contexts by name')
@standard_cli_command(
    help_text="""
    List validation contexts for a specific domain.
    
    This command displays information about all validation contexts
    available for a specific domain, including their requirements,
    capabilities, and configuration.
    
    When LLM is enabled, context listing includes:
    - Enhanced context analysis and categorization
    - Capability assessment and recommendations
    - Intelligent filtering and sorting suggestions
    - Advanced context metadata extraction
    """,
    epilog="""
    Examples:
      # List contexts for manufacturing domain
      ome utility contexts manufacturing
      
      # Filter contexts by name
      ome utility contexts manufacturing --name professional
      
      # Use LLM for enhanced analysis
      ome utility contexts cooking --use-llm --quality-level professional
    """,
    async_cmd=True,
    track_performance=True,
    handle_errors=True,
    format_output=True,
    add_llm_config=True
)
@click.pass_context
async def contexts(ctx, domain: str, name: Optional[str],
                  verbose: bool, output_format: str, use_llm: bool,
                  llm_provider: str, llm_model: Optional[str],
                  quality_level: str, strict_mode: bool):
    """List validation contexts for a specific domain with enhanced LLM support."""
    cli_ctx = ctx.obj
    cli_ctx.verbose = verbose  # Set verbose mode
    cli_ctx.start_command_tracking("utility-contexts")
    
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
            log_llm_usage(cli_ctx, "Context listing")
        
        async def http_contexts():
            """Get contexts via HTTP API"""
            cli_ctx.log("Getting contexts via HTTP API...", "info")
            params = {}
            if name:
                params["name"] = name
            
            response = await cli_ctx.api_client.request("GET", f"/contexts/{domain}", params=params)
            return response
        
        async def fallback_contexts():
            """Get contexts using direct service calls"""
            cli_ctx.log("Using direct service context listing...", "info")
            
            # Validate domain name
            valid_domains = ["manufacturing", "cooking"]
            if domain not in valid_domains:
                raise ValueError(f"Invalid domain '{domain}'. Valid domains are: {', '.join(valid_domains)}")
            
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
        
        # Execute context listing with fallback
        command = SmartCommand(cli_ctx)
        result = await command.execute_with_fallback(http_contexts, fallback_contexts)
        
        # Display contexts results
        await _display_contexts_results(cli_ctx, result, domain, output_format)
        
        cli_ctx.end_command_tracking()
        
    except Exception as e:
        cli_ctx.log(f"Context listing failed: {str(e)}", "error")
        raise