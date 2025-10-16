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
@click.pass_context
def cli(ctx, server_url: str, timeout: float, verbose: bool, output_format: Optional[str]):
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


if __name__ == '__main__':
    cli()
