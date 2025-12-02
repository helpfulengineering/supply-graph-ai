"""
Utility CLI Commands

Commands for utility operations in the Open Matching Engine.
"""

import click
from typing import Optional
from ..core.registry.domain_registry import DomainRegistry

from .base import CLIContext, SmartCommand, format_llm_output, log_llm_usage
from .decorators import standard_cli_command


@click.group()
def utility_group():
    """
    Utility commands for OME.

    These commands provide utility operations for the Open Matching Engine,
    including domain listing, validation context management, system metrics,
    and system information utilities.

    Examples:
      # List available domains
      ome utility domains

      # List validation contexts for a domain
      ome utility contexts manufacturing

      # Get system metrics
      ome utility metrics

      # Use LLM for enhanced analysis
      ome utility domains --use-llm --quality-level professional
    """
    pass


# Helper functions


async def _display_domains_results(
    cli_ctx: CLIContext, result: dict, output_format: str
):
    """Display domains results."""
    domains = result.get("domains", [])

    if output_format == "json":
        output_data = format_llm_output(result, cli_ctx)
        click.echo(output_data)
    else:
        if domains:
            cli_ctx.log(f"Found {len(domains)} domains", "success")
            for domain in domains:
                status_icon = (
                    "✅" if domain.get("status", "active") == "active" else "❌"
                )
                cli_ctx.log(
                    f"{status_icon} {domain['id']}: {domain.get('name', 'Unknown')}",
                    "info",
                )
                if domain.get("description"):
                    cli_ctx.log(f"   {domain['description']}", "info")
        else:
            cli_ctx.log("No domains found", "info")


async def _display_contexts_results(
    cli_ctx: CLIContext, result: dict, domain: str, output_format: str
):
    """Display contexts results."""
    contexts = result.get("contexts", [])

    if output_format == "json":
        output_data = format_llm_output(result, cli_ctx)
        click.echo(output_data)
    else:
        if contexts:
            cli_ctx.log(
                f"Found {len(contexts)} contexts for domain '{domain}'", "success"
            )
            for context in contexts:
                cli_ctx.log(
                    f"✅ {context['id']}: {context.get('name', 'Unknown')}", "info"
                )
                if context.get("description"):
                    cli_ctx.log(f"   {context['description']}", "info")
        else:
            cli_ctx.log(f"No contexts found for domain '{domain}'", "info")


async def _display_metrics_results(
    cli_ctx: CLIContext,
    result: dict,
    output_format: str,
    endpoint: Optional[str] = None,
):
    """Display metrics results."""
    # Extract data from wrapped API response
    # The API wraps responses in a structure with 'data', 'status', 'message', etc.
    if isinstance(result, dict) and "data" in result:
        metrics_data = result["data"]
    else:
        metrics_data = result

    # Ensure we have a dict to work with
    if not isinstance(metrics_data, dict):
        cli_ctx.log(f"Unexpected response format: {type(metrics_data)}", "error")
        if output_format != "json":
            cli_ctx.log("Use --json to see raw response", "info")
        return

    if output_format == "json":
        output_data = format_llm_output(result, cli_ctx)
        click.echo(output_data)
    else:
        if endpoint:
            # Display specific endpoint metrics
            if not metrics_data or metrics_data == {}:
                cli_ctx.log(f"No metrics found for endpoint: {endpoint}", "warning")
                return

            click.echo(f"Metrics for endpoint: {endpoint}")
            click.echo(f"  Method: {metrics_data.get('method', 'N/A')}")
            click.echo(f"  Path: {metrics_data.get('path', 'N/A')}")
            click.echo(f"  Total Requests: {metrics_data.get('total_requests', 0)}")
            click.echo(f"  Successful: {metrics_data.get('successful_requests', 0)}")
            click.echo(f"  Failed: {metrics_data.get('failed_requests', 0)}")
            click.echo(f"  Success Rate: {metrics_data.get('success_rate', 0):.2f}%")
            click.echo(
                f"  Avg Processing Time: {metrics_data.get('avg_processing_time_ms', 0):.2f} ms"
            )

            if "p95_processing_time_ms" in metrics_data:
                click.echo(
                    f"  P95 Processing Time: {metrics_data.get('p95_processing_time_ms', 0):.2f} ms"
                )
            if "p99_processing_time_ms" in metrics_data:
                click.echo(
                    f"  P99 Processing Time: {metrics_data.get('p99_processing_time_ms', 0):.2f} ms"
                )
            if "min_processing_time_ms" in metrics_data:
                click.echo(
                    f"  Min Processing Time: {metrics_data.get('min_processing_time_ms', 0):.2f} ms"
                )
            if "max_processing_time_ms" in metrics_data:
                click.echo(
                    f"  Max Processing Time: {metrics_data.get('max_processing_time_ms', 0):.2f} ms"
                )

            if "status_codes" in metrics_data and metrics_data["status_codes"]:
                click.echo("  Status Codes:")
                for code, count in metrics_data["status_codes"].items():
                    click.echo(f"    {code}: {count}")

            if (
                "total_llm_cost" in metrics_data
                and metrics_data.get("total_llm_cost", 0) > 0
            ):
                click.echo(
                    f"  Total LLM Cost: ${metrics_data.get('total_llm_cost', 0):.4f}"
                )
            if (
                "total_llm_tokens" in metrics_data
                and metrics_data.get("total_llm_tokens", 0) > 0
            ):
                click.echo(
                    f"  Total LLM Tokens: {metrics_data.get('total_llm_tokens', 0):,}"
                )
        else:
            # Display summary or all endpoints
            if "endpoints" in metrics_data:
                # Detailed view with endpoints
                summary = metrics_data.get("summary", {})
                endpoints = metrics_data.get("endpoints", {})

                click.echo("System Metrics Summary")
                click.echo(f"  Total Requests: {summary.get('total_requests', 0)}")
                click.echo(
                    f"  Recent Requests (1h): {summary.get('recent_requests_1h', 0)}"
                )
                click.echo(f"  Active Requests: {summary.get('active_requests', 0)}")
                click.echo(
                    f"  Endpoints Tracked: {summary.get('endpoints_tracked', 0)}"
                )

                if endpoints:
                    click.echo("\nEndpoint Metrics:")
                    for endpoint_key, endpoint_metrics in endpoints.items():
                        click.echo(f"  {endpoint_key}")
                        click.echo(
                            f"    Requests: {endpoint_metrics.get('total_requests', 0)}"
                        )
                        click.echo(
                            f"    Success Rate: {endpoint_metrics.get('success_rate', 0):.2f}%"
                        )
                        click.echo(
                            f"    Avg Time: {endpoint_metrics.get('avg_processing_time_ms', 0):.2f} ms"
                        )
                        if endpoint_metrics.get("total_llm_cost", 0) > 0:
                            click.echo(
                                f"    LLM Cost: ${endpoint_metrics.get('total_llm_cost', 0):.4f}"
                            )
            else:
                # Summary only - display all available summary fields
                cli_ctx.log("System Metrics Summary", "success")

                # Core metrics - always display these (use click.echo directly)
                total_requests = metrics_data.get("total_requests", 0)
                recent_requests = metrics_data.get("recent_requests_1h", 0)
                active_requests = metrics_data.get("active_requests", 0)
                endpoints_tracked = metrics_data.get("endpoints_tracked", 0)

                click.echo(f"  Total Requests: {total_requests}")
                click.echo(f"  Recent Requests (1h): {recent_requests}")
                click.echo(f"  Active Requests: {active_requests}")
                click.echo(f"  Endpoints Tracked: {endpoints_tracked}")

                # Error summary
                error_summary = metrics_data.get("error_summary", {})
                if error_summary and isinstance(error_summary, dict):
                    total_errors = error_summary.get("total_errors", 0)
                    if total_errors > 0:
                        click.echo(f"\n  Total Errors: {total_errors}")
                    else:
                        click.echo("\n  No errors recorded")

                # Performance summary
                perf_summary = metrics_data.get("performance_summary", {})
                if perf_summary and isinstance(perf_summary, dict):
                    operation_stats = perf_summary.get("operation_stats", {})
                    if operation_stats:
                        click.echo("\n  Performance Metrics:")
                        for operation, stats in operation_stats.items():
                            if isinstance(stats, dict):
                                count = stats.get("count", 0)
                                avg_duration = stats.get("avg_duration_ms", 0)
                                click.echo(
                                    f"    {operation}: {count} operations, avg {avg_duration:.2f} ms"
                                )

                # LLM summary
                llm_summary = metrics_data.get("llm_summary", {})
                if llm_summary and isinstance(llm_summary, dict):
                    overview = llm_summary.get("overview", {})
                    if overview and isinstance(overview, dict):
                        total_cost = overview.get("total_cost", 0)
                        total_llm_requests = overview.get("total_requests", 0)
                        total_tokens = overview.get("total_tokens", 0)

                        if total_cost > 0 or total_llm_requests > 0:
                            click.echo("\n  LLM Usage:")
                            click.echo(f"    Total Cost: ${total_cost:.4f}")
                            click.echo(f"    Total Requests: {total_llm_requests}")
                            click.echo(f"    Total Tokens: {total_tokens:,}")
                        else:
                            click.echo("\n  No LLM usage recorded")


# Commands


@utility_group.command()
@click.option("--name", help="Filter domains by name")
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
    add_llm_config=True,
)
@click.pass_context
async def domains(
    ctx,
    name: Optional[str],
    verbose: bool,
    output_format: str,
    use_llm: bool,
    llm_provider: str,
    llm_model: Optional[str],
    quality_level: str,
    strict_mode: bool,
):
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
        strict_mode=strict_mode,
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

            response = await cli_ctx.api_client.request(
                "GET", "/api/utility/domains", params=params
            )
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
                        "status": "active",
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
@click.argument("domain")
@click.option("--name", help="Filter contexts by name")
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
    add_llm_config=True,
)
@click.pass_context
async def contexts(
    ctx,
    domain: str,
    name: Optional[str],
    verbose: bool,
    output_format: str,
    use_llm: bool,
    llm_provider: str,
    llm_model: Optional[str],
    quality_level: str,
    strict_mode: bool,
):
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
        strict_mode=strict_mode,
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

            response = await cli_ctx.api_client.request(
                "GET", f"/api/utility/contexts/{domain}", params=params
            )
            return response

        async def fallback_contexts():
            """Get contexts using direct service calls"""
            cli_ctx.log("Using direct service context listing...", "info")

            # Validate domain name
            valid_domains = ["manufacturing", "cooking"]
            if domain not in valid_domains:
                raise ValueError(
                    f"Invalid domain '{domain}'. Valid domains are: {', '.join(valid_domains)}"
                )

            # Get domain-specific contexts
            if domain == "manufacturing":
                contexts = [
                    {
                        "id": "hobby",
                        "name": "Hobby Manufacturing",
                        "description": "Non-commercial, limited quality requirements",
                    },
                    {
                        "id": "professional",
                        "name": "Professional Manufacturing",
                        "description": "Commercial-grade production",
                    },
                ]
            elif domain == "cooking":
                contexts = [
                    {
                        "id": "home",
                        "name": "Home Cooking",
                        "description": "Basic home kitchen capabilities",
                    },
                    {
                        "id": "commercial",
                        "name": "Commercial Kitchen",
                        "description": "Professional kitchen capabilities",
                    },
                ]
            else:
                contexts = []

            # Apply name filter if provided
            if name:
                contexts = [c for c in contexts if name.lower() in c["name"].lower()]

            return {"contexts": contexts}

        # Execute context listing with fallback
        command = SmartCommand(cli_ctx)
        result = await command.execute_with_fallback(http_contexts, fallback_contexts)

        # Display contexts results
        await _display_contexts_results(cli_ctx, result, domain, output_format)

        cli_ctx.end_command_tracking()

    except Exception as e:
        cli_ctx.log(f"Context listing failed: {str(e)}", "error")
        raise


@utility_group.command()
@click.option("--endpoint", help='Filter metrics by endpoint (format: "METHOD /path")')
@click.option(
    "--summary/--no-summary", default=True, help="Show summary only (default: True)"
)
@standard_cli_command(
    help_text="""
    Get system metrics including request tracking, performance, and LLM usage.
    
    This command provides access to the MetricsTracker data, including:
    - Overall request statistics
    - Endpoint-level metrics with processing times
    - Error summaries
    - Performance metrics
    - LLM usage and costs
    
    Metrics are only available when connected to the API server.
    """,
    epilog="""
    Examples:
      # Get overall metrics summary
      ome utility metrics
      
      # Get detailed metrics with all endpoints
      ome utility metrics --no-summary
      
      # Get metrics for a specific endpoint
      ome utility metrics --endpoint "GET /health"
      
      # Get metrics for a specific API endpoint
      ome utility metrics --endpoint "POST /v1/api/match"
      
      # Output in JSON format
      ome utility metrics --json
    """,
    async_cmd=True,
    track_performance=False,  # Don't track metrics for the metrics command itself
    handle_errors=True,
    format_output=True,
    add_llm_config=False,  # Metrics don't need LLM
)
@click.pass_context
async def metrics(
    ctx,
    endpoint: Optional[str],
    summary: bool,
    verbose: bool,
    output_format: str,
    use_llm: bool,
    llm_provider: str,
    llm_model: Optional[str],
    quality_level: str,
    strict_mode: bool,
):
    """Get system metrics with request tracking and performance data."""
    cli_ctx = ctx.obj
    cli_ctx.verbose = verbose
    cli_ctx.start_command_tracking("utility-metrics")

    try:

        async def http_metrics():
            """Get metrics via HTTP API"""
            cli_ctx.log("Getting metrics via HTTP API...", "info")
            params = {}
            if endpoint:
                params["endpoint"] = endpoint
            if not summary:
                params["summary"] = "false"

            response = await cli_ctx.api_client.request(
                "GET", "/api/utility/metrics", params=params
            )
            return response

        async def fallback_metrics():
            """Fallback - metrics are only available via API"""
            cli_ctx.log(
                "Metrics are only available when connected to the API server.",
                "warning",
            )
            cli_ctx.log(
                "Please ensure the OME server is running and accessible.", "info"
            )
            raise click.ClickException(
                "Metrics endpoint requires API server connection. "
                "Please start the server or check your connection."
            )

        # Execute metrics retrieval with fallback
        command = SmartCommand(cli_ctx)
        result = await command.execute_with_fallback(http_metrics, fallback_metrics)

        # Display metrics results
        await _display_metrics_results(cli_ctx, result, output_format, endpoint)

        cli_ctx.end_command_tracking()

    except Exception as e:
        cli_ctx.log(f"Metrics retrieval failed: {str(e)}", "error")
        raise
