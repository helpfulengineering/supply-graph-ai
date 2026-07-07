"""
Main CLI entry point for Open Hardware Manager

This module provides the main CLI interface with subcommands for different
OHM operations including package management, OKH/OKW operations, and matching.
"""

from typing import Optional, cast

import click
from click import Context

from .asset import asset_group
from .base import CLIConfig, CLIContext
from .convert import convert_group
from .federation import federation_group
from .match import match_group
from .okh import okh_group
from .okw import okw_group
from .package import package_group
from .solution import solution_group
from .storage import storage_group
from .system import system_group
from .taxonomy import taxonomy_group
from .utility import utility_group

# Conditional LLM import - only load if LLM is enabled
try:
    from .llm import llm_group

    LLM_AVAILABLE = True
except ImportError:
    LLM_AVAILABLE = False
    llm_group = None


@click.group()
@click.option("--server-url", default="http://localhost:8001", help="OHM server URL")
@click.option("--timeout", default=120.0, type=float, help="Request timeout in seconds")
@click.option("--verbose", "-v", is_flag=True, help="Enable verbose output")
@click.option(
    "--json", "output_format", flag_value="json", help="Output in JSON format"
)
@click.option(
    "--table", "output_format", flag_value="table", help="Output in table format"
)
@click.option(
    "--use-llm", is_flag=True, help="Enable LLM integration for enhanced processing"
)
@click.option(
    "--llm-provider",
    type=click.Choice(["openai", "anthropic", "google", "azure", "local"]),
    default="anthropic",
    help="LLM provider to use",
)
@click.option("--llm-model", help="Specific LLM model to use (provider-specific)")
@click.option(
    "--quality-level",
    type=click.Choice(["hobby", "professional", "medical"]),
    default="professional",
    help="Quality level for LLM processing",
)
@click.option("--strict-mode", is_flag=True, help="Enable strict validation mode")
@click.pass_context
def cli(
    ctx: Context,
    server_url: str,
    timeout: float,
    verbose: bool,
    output_format: Optional[str],
    use_llm: bool,
    llm_provider: str,
    llm_model: Optional[str],
    quality_level: str,
    strict_mode: bool,
) -> None:
    """Open Hardware Manager (OHM) command-line entrypoint.

    Args:
        ctx: Click context; ``ctx.obj`` is set to a :class:`CLIContext` instance.
        server_url: Base URL for API-backed commands.
        timeout: HTTP client timeout in seconds.
        verbose: When True, emit extra diagnostics.
        output_format: ``json``, ``table``, or ``None`` for human-readable text.
        use_llm: Forwarded into LLM-related commands when supported.
        llm_provider: Default LLM provider name.
        llm_model: Optional model override for the provider.
        quality_level: Default quality tier for LLM workflows.
        strict_mode: When True, prefer strict validation where applicable.
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
        strict_mode=strict_mode,
    )

    # Create CLI context
    cli_context = CLIContext(config)
    cli_context.output_format = output_format or "text"

    # Store in context
    ctx.obj = cli_context


# Add subcommand groups
cli.add_command(asset_group, name="asset")
cli.add_command(package_group, name="package")
cli.add_command(okh_group, name="okh")
cli.add_command(okw_group, name="okw")
cli.add_command(match_group, name="match")
if LLM_AVAILABLE and llm_group:
    cli.add_command(llm_group, name="llm")
cli.add_command(system_group, name="system")
cli.add_command(utility_group, name="utility")
cli.add_command(storage_group, name="storage")
cli.add_command(solution_group, name="solution")
cli.add_command(convert_group, name="convert")
cli.add_command(taxonomy_group, name="taxonomy")
cli.add_command(federation_group, name="federation")


@cli.command()
def version() -> None:
    """Show OHM version information."""
    from src.core.version import get_version

    click.echo(f"Open Hardware Manager CLI v{get_version()}")


@cli.command()
@click.pass_context
def config(ctx: Context) -> None:
    """Show current CLI configuration (server URL, output format, LLM flags)."""
    cli_context = cast(CLIContext, ctx.obj)
    config = cli_context.config
    click.echo("CLI Configuration:")
    click.echo(f"  Server URL: {config.server_url}")
    click.echo(f"  Timeout: {config.timeout}s")
    click.echo(f"  Verbose: {config.verbose}")
    click.echo(f"  Output Format: {cli_context.output_format}")
    click.echo()
    click.echo("LLM Configuration:")
    click.echo(f"  Use LLM: {config.llm_config['use_llm']}")
    click.echo(f"  Provider: {config.llm_config['llm_provider']}")
    click.echo(f"  Model: {config.llm_config['llm_model'] or 'default'}")
    click.echo(f"  Quality Level: {config.llm_config['quality_level']}")
    click.echo(f"  Strict Mode: {config.llm_config['strict_mode']}")
    click.echo()
    try:
        from src.config.storage_config import get_mom_config, get_okw_source

        okw_source = get_okw_source()
        mom_cfg = get_mom_config()
        click.echo("OKW Facility Source:")
        click.echo(f"  Source: {okw_source}  (OKW_SOURCE env var, unset → union)")
        mom_active = okw_source in ("union", "mom")
        if mom_active:
            click.echo(f"  MoM SPARQL Endpoint: {mom_cfg['endpoint']}")
        else:
            click.echo(
                f"  MoM SPARQL Endpoint: {mom_cfg['endpoint']}  (inactive — unset OKW_SOURCE or set it to mom to enable)"
            )
    except Exception:
        pass


if __name__ == "__main__":
    cli()
