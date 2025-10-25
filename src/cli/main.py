"""
Main CLI entry point for Open Matching Engine

This module provides the main CLI interface with subcommands for different
OME operations including package management, OKH/OKW operations, and matching.
"""

import click
from typing import Optional

from .base import CLIContext, CLIConfig
from .package import package_group
from .okh import okh_group
from .okw import okw_group
from .match import match_group
from .system import system_group
from .utility import utility_group


@click.group()
@click.option('--server-url', default='http://localhost:8001', 
              help='OME server URL')
@click.option('--timeout', default=120.0, type=float,
              help='Request timeout in seconds')
@click.option('--verbose', '-v', is_flag=True,
              help='Enable verbose output')
@click.option('--json', 'output_format', flag_value='json',
              help='Output in JSON format')
@click.option('--table', 'output_format', flag_value='table',
              help='Output in table format')
@click.option('--use-llm', is_flag=True,
              help='Enable LLM integration for enhanced processing')
@click.option('--llm-provider', 
              type=click.Choice(['openai', 'anthropic', 'google', 'azure', 'local']),
              default='anthropic',
              help='LLM provider to use')
@click.option('--llm-model', 
              help='Specific LLM model to use (provider-specific)')
@click.option('--quality-level', 
              type=click.Choice(['hobby', 'professional', 'medical']),
              default='professional',
              help='Quality level for LLM processing')
@click.option('--strict-mode', is_flag=True,
              help='Enable strict validation mode')
@click.pass_context
def cli(ctx, server_url: str, timeout: float, verbose: bool, output_format: Optional[str],
        use_llm: bool, llm_provider: str, llm_model: Optional[str], 
        quality_level: str, strict_mode: bool):
    """
    Open Matching Engine (OME) Command Line Interface
    
    A comprehensive CLI for managing OKH packages, OKW facilities, and matching operations.
    """
    # Ensure context object exists
    ctx.ensure_object(dict)
    
    # Create CLI configuration
    config = CLIConfig()
    config.server_url = server_url
    config.timeout = timeout
    config.verbose = verbose
    
    # Update LLM configuration
    config.update_llm_config(
        use_llm=use_llm,
        llm_provider=llm_provider,
        llm_model=llm_model,
        quality_level=quality_level,
        strict_mode=strict_mode
    )
    
    # Create CLI context
    cli_context = CLIContext(config)
    cli_context.output_format = output_format or 'text'
    
    # Store in context
    ctx.obj = cli_context


# Add subcommand groups
cli.add_command(package_group, name='package')
cli.add_command(okh_group, name='okh')
cli.add_command(okw_group, name='okw')
cli.add_command(match_group, name='match')
cli.add_command(system_group, name='system')
cli.add_command(utility_group, name='utility')


@cli.command()
def version():
    """Show OME version information"""
    from . import __version__
    click.echo(f"Open Matching Engine CLI v{__version__}")


@cli.command()
@click.pass_context
def config(ctx):
    """Show current CLI configuration"""
    config = ctx.obj.config
    click.echo("CLI Configuration:")
    click.echo(f"  Server URL: {config.server_url}")
    click.echo(f"  Timeout: {config.timeout}s")
    click.echo(f"  Verbose: {config.verbose}")
    click.echo(f"  Output Format: {ctx.obj.output_format}")
    click.echo()
    click.echo("LLM Configuration:")
    click.echo(f"  Use LLM: {config.llm_config['use_llm']}")
    click.echo(f"  Provider: {config.llm_config['llm_provider']}")
    click.echo(f"  Model: {config.llm_config['llm_model'] or 'default'}")
    click.echo(f"  Quality Level: {config.llm_config['quality_level']}")
    click.echo(f"  Strict Mode: {config.llm_config['strict_mode']}")


if __name__ == '__main__':
    cli()
