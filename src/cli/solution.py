"""
Solution management commands for OHM CLI

This module provides commands for managing supply tree solutions,
including save, load, list, delete, check (staleness), extend (TTL), and cleanup.
"""

import json
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, Optional
from uuid import UUID

import click

from .base import CLIContext
from .decorators import standard_cli_command


@click.group()
def solution_group():
    """
    Solution management commands for OHM.

    These commands help you manage supply tree solutions, including
    saving, loading, listing, deleting, checking staleness, extending TTL,
    and cleaning up stale solutions.

    Examples:
      # Save a solution from a file
      ohm solution save solution.json --id {uuid} --tags "production,test" --ttl-days 60

      # Load a solution
      ohm solution load {solution_id} --output solution.json

      # List solutions with filters
      ohm solution list --okh-id {uuid} --matching-mode nested
      ohm solution list --sort-by created_at --sort-order desc
      ohm solution list --max-age-days 7 --only-stale

      # Check solution staleness
      ohm solution check {solution_id}

      # Extend solution TTL
      ohm solution extend {solution_id} --days 30

      # Cleanup stale solutions
      ohm solution cleanup --max-age-days 90 --dry-run
      ohm solution cleanup --max-age-days 90 --archive
      ohm solution cleanup --before-date 2024-01-01
    """
    pass


@solution_group.command()
@click.argument("solution_file", type=click.Path(exists=True))
@click.option(
    "--id",
    "solution_id",
    help="Solution ID (UUID). If not provided, a new UUID will be generated.",
)
@click.option(
    "--ttl-days", "ttl_days", type=int, help="Time-to-live in days for the solution"
)
@click.option("--tags", help="Comma-separated tags to associate with the solution")
@click.pass_context
@standard_cli_command(
    help_text="""
    Save a supply tree solution to storage.
    
    The solution can be provided as a JSON file. The file should contain
    a SupplyTreeSolution object in the standard format.
    
    Examples:
      # Save with auto-generated ID
      ohm solution save solution.json
      
      # Save with specific ID and TTL
      ohm solution save solution.json --id abc123 --ttl-days 60
      
      # Save with tags
      ohm solution save solution.json --tags "production,test"
    """,
    async_cmd=True,
    track_performance=True,
    handle_errors=True,
    format_output=True,
)
async def save(
    ctx,
    solution_file: str,
    solution_id: Optional[str],
    ttl_days: Optional[int],
    tags: Optional[str],
    verbose: bool,
    output_format: str,
    use_llm: bool = False,
    llm_provider: str = "anthropic",
    llm_model: Optional[str] = None,
    quality_level: str = "professional",
    strict_mode: bool = False,
):
    """Save a supply tree solution to storage"""
    cli_ctx: CLIContext = ctx.obj

    try:
        # Read solution file
        cli_ctx.log(f"Reading solution file: {solution_file}", "info")
        with open(solution_file, "r") as f:
            solution_data = json.load(f)

        # Extract solution from wrapped format if needed
        if "solution" in solution_data:
            solution = solution_data["solution"]
        else:
            solution = solution_data

        # Prepare request body
        request_body = {"solution": solution}
        if ttl_days is not None:
            request_body["ttl_days"] = ttl_days
        if tags:
            request_body["tags"] = [tag.strip() for tag in tags.split(",")]

        # Determine solution ID
        if solution_id:
            solution_uuid = solution_id
        else:
            # Generate new UUID if not provided
            from uuid import uuid4

            solution_uuid = str(uuid4())

        # Make API request
        endpoint = f"/api/supply-tree/solution/{solution_uuid}/save"
        response = await cli_ctx.api_client.request(
            "POST", endpoint, json_data=request_body
        )

        if output_format == "json":
            click.echo(json.dumps(response, indent=2))
        else:
            click.echo(f"✓ Solution saved successfully")
            click.echo(f"  Solution ID: {solution_uuid}")
            if "ttl_days" in request_body:
                click.echo(f"  TTL: {request_body['ttl_days']} days")
            if "tags" in request_body:
                click.echo(f"  Tags: {', '.join(request_body['tags'])}")

    except Exception as e:
        cli_ctx.log(f"Error saving solution: {str(e)}", "error")
        raise click.ClickException(f"Failed to save solution: {str(e)}")


@solution_group.command()
@click.argument("solution_id", type=str)
@click.option(
    "--output",
    "-o",
    type=click.Path(),
    help="Output file path. If not provided, outputs to stdout.",
)
@click.pass_context
@standard_cli_command(
    help_text="""
    Load a supply tree solution from storage.
    
    The solution can be written to a file or output to stdout in JSON format.
    
    Examples:
      # Load to stdout
      ohm solution load {solution_id}
      
      # Load to file
      ohm solution load {solution_id} --output solution.json
      
      # Load as JSON
      ohm solution load {solution_id} --json
    """,
    async_cmd=True,
    track_performance=True,
    handle_errors=True,
    format_output=True,
)
async def load(
    ctx,
    solution_id: str,
    output: Optional[str],
    verbose: bool,
    output_format: str,
    use_llm: bool = False,
    llm_provider: str = "anthropic",
    llm_model: Optional[str] = None,
    quality_level: str = "professional",
    strict_mode: bool = False,
):
    """Load a supply tree solution from storage"""
    cli_ctx: CLIContext = ctx.obj

    try:
        # Make API request
        endpoint = f"/api/supply-tree/solution/{solution_id}"
        response = await cli_ctx.api_client.request("GET", endpoint)

        # Extract solution data
        solution_data = response.get("data") or response.get("result") or response
        if isinstance(solution_data, dict) and "result" in solution_data:
            solution_data = solution_data["result"]

        # Write to file or stdout
        if output:
            cli_ctx.log(f"Writing solution to: {output}", "info")
            with open(output, "w") as f:
                json.dump(solution_data, f, indent=2)
            click.echo(f"✓ Solution loaded and saved to {output}")
        else:
            if output_format == "json":
                click.echo(json.dumps(solution_data, indent=2))
            else:
                click.echo(json.dumps(solution_data, indent=2))

    except Exception as e:
        cli_ctx.log(f"Error loading solution: {str(e)}", "error")
        raise click.ClickException(f"Failed to load solution: {str(e)}")


@solution_group.command(name="list")
@click.pass_context
@click.option("--okh-id", help="Filter by OKH ID")
@click.option(
    "--matching-mode",
    type=click.Choice(["single-level", "nested"]),
    help="Filter by matching mode",
)
@click.option(
    "--sort-by",
    type=click.Choice(["created_at", "updated_at", "score", "age_days"]),
    help="Sort field",
)
@click.option(
    "--sort-order",
    type=click.Choice(["asc", "desc"]),
    default="desc",
    help="Sort order",
)
@click.option("--min-age-days", type=int, help="Filter by minimum age in days")
@click.option("--max-age-days", type=int, help="Filter by maximum age in days")
@click.option("--only-stale", is_flag=True, help="Show only stale solutions")
@click.option("--include-stale", is_flag=True, help="Include stale solutions")
@click.option("--limit", type=int, help="Maximum number of results")
@click.option("--offset", type=int, help="Number of results to skip")
@standard_cli_command(
    help_text="""
    List supply tree solutions with optional filtering and sorting.
    
    Examples:
      # List all solutions
      ohm solution list
      
      # List with filters
      ohm solution list --okh-id {uuid} --matching-mode nested
      ohm solution list --sort-by created_at --sort-order desc
      ohm solution list --max-age-days 7 --only-stale
    """,
    async_cmd=True,
    track_performance=True,
    handle_errors=True,
    format_output=True,
)
async def list_solutions(
    ctx,
    okh_id: Optional[str],
    matching_mode: Optional[str],
    sort_by: Optional[str],
    sort_order: str,
    min_age_days: Optional[int],
    max_age_days: Optional[int],
    only_stale: bool,
    include_stale: bool,
    limit: Optional[int],
    offset: Optional[int],
    verbose: bool,
    output_format: str,
    use_llm: bool = False,
    llm_provider: str = "anthropic",
    llm_model: Optional[str] = None,
    quality_level: str = "professional",
    strict_mode: bool = False,
):
    """List supply tree solutions"""
    cli_ctx: CLIContext = ctx.obj

    try:
        # Build query parameters
        params = {}
        if okh_id:
            params["okh_id"] = okh_id
        if matching_mode:
            params["matching_mode"] = matching_mode
        if sort_by:
            params["sort_by"] = sort_by
        if sort_order:
            params["sort_order"] = sort_order
        if min_age_days is not None:
            params["min_age_days"] = min_age_days
        if max_age_days is not None:
            params["max_age_days"] = max_age_days
        if only_stale:
            params["only_stale"] = True
        if include_stale:
            params["include_stale"] = True
        if limit:
            params["limit"] = limit
        if offset:
            params["offset"] = offset

        # Make API request
        endpoint = "/api/supply-tree/solutions"
        response = await cli_ctx.api_client.request("GET", endpoint, params=params)

        # Extract solutions list
        data = response.get("data") or response.get("result") or response
        if isinstance(data, dict) and "result" in data:
            solutions = data["result"]
        elif isinstance(data, list):
            solutions = data
        else:
            solutions = []

        if output_format == "json":
            click.echo(json.dumps(solutions, indent=2))
        else:
            if not solutions:
                click.echo("No solutions found")
            else:
                click.echo(f"Found {len(solutions)} solution(s):\n")
                for sol in solutions:
                    sol_id = sol.get("id", "unknown")
                    title = sol.get("okh_title") or sol.get("metadata", {}).get(
                        "okh_title", "N/A"
                    )
                    mode = sol.get("metadata", {}).get("matching_mode", "unknown")
                    tree_count = len(sol.get("all_trees", []))
                    created = sol.get("created_at", "N/A")
                    click.echo(f"  ID: {sol_id}")
                    click.echo(f"  Title: {title}")
                    click.echo(f"  Mode: {mode}")
                    click.echo(f"  Trees: {tree_count}")
                    click.echo(f"  Created: {created}")
                    click.echo()

    except Exception as e:
        cli_ctx.log(f"Error listing solutions: {str(e)}", "error")
        raise click.ClickException(f"Failed to list solutions: {str(e)}")


@solution_group.command()
@click.argument("solution_id", type=str)
@click.pass_context
@standard_cli_command(
    help_text="""
    Delete a supply tree solution from storage.
    
    Examples:
      # Delete a solution
      ohm solution delete {solution_id}
    """,
    async_cmd=True,
    track_performance=True,
    handle_errors=True,
    format_output=True,
)
async def delete(
    ctx,
    solution_id: str,
    verbose: bool,
    output_format: str,
    use_llm: bool = False,
    llm_provider: str = "anthropic",
    llm_model: Optional[str] = None,
    quality_level: str = "professional",
    strict_mode: bool = False,
):
    """Delete a supply tree solution"""
    cli_ctx: CLIContext = ctx.obj

    try:
        # Make API request
        endpoint = f"/api/supply-tree/solution/{solution_id}"
        response = await cli_ctx.api_client.request("DELETE", endpoint)

        if output_format == "json":
            click.echo(json.dumps(response, indent=2))
        else:
            click.echo(f"✓ Solution {solution_id} deleted successfully")

    except Exception as e:
        cli_ctx.log(f"Error deleting solution: {str(e)}", "error")
        raise click.ClickException(f"Failed to delete solution: {str(e)}")


@solution_group.command()
@click.argument("solution_id", type=str)
@click.option("--max-age-days", type=int, help="Maximum age in days to consider fresh")
@click.pass_context
@standard_cli_command(
    help_text="""
    Check the staleness status of a supply tree solution.
    
    Examples:
      # Check staleness
      ohm solution check {solution_id}
      
      # Check with custom max age
      ohm solution check {solution_id} --max-age-days 7
    """,
    async_cmd=True,
    track_performance=True,
    handle_errors=True,
    format_output=True,
)
async def check(
    ctx,
    solution_id: str,
    max_age_days: Optional[int],
    verbose: bool,
    output_format: str,
    use_llm: bool = False,
    llm_provider: str = "anthropic",
    llm_model: Optional[str] = None,
    quality_level: str = "professional",
    strict_mode: bool = False,
):
    """Check solution staleness"""
    cli_ctx: CLIContext = ctx.obj

    try:
        # Build query parameters
        params = {}
        if max_age_days is not None:
            params["max_age_days"] = max_age_days

        # Make API request
        endpoint = f"/api/supply-tree/solution/{solution_id}/staleness"
        response = await cli_ctx.api_client.request("GET", endpoint, params=params)

        # Extract staleness data
        data = response.get("data") or response.get("result") or response
        if isinstance(data, dict) and "result" in data:
            data = data["result"]

        if output_format == "json":
            click.echo(json.dumps(data, indent=2))
        else:
            is_stale = data.get("is_stale", False)
            age_days = data.get("age_days", 0)
            reason = data.get("staleness_reason")

            if is_stale:
                click.echo(f"⚠ Solution {solution_id} is STALE")
                click.echo(f"  Age: {age_days} days")
                if reason:
                    click.echo(f"  Reason: {reason}")
            else:
                click.echo(f"✓ Solution {solution_id} is FRESH")
                click.echo(f"  Age: {age_days} days")

    except Exception as e:
        cli_ctx.log(f"Error checking solution staleness: {str(e)}", "error")
        raise click.ClickException(f"Failed to check solution staleness: {str(e)}")


@solution_group.command()
@click.argument("solution_id", type=str)
@click.option(
    "--days", type=int, default=30, help="Additional days to extend TTL (default: 30)"
)
@click.pass_context
@standard_cli_command(
    help_text="""
    Extend the Time-to-Live (TTL) of a supply tree solution.
    
    Examples:
      # Extend by default 30 days
      ohm solution extend {solution_id}
      
      # Extend by specific number of days
      ohm solution extend {solution_id} --days 60
    """,
    async_cmd=True,
    track_performance=True,
    handle_errors=True,
    format_output=True,
)
async def extend(
    ctx,
    solution_id: str,
    days: int,
    verbose: bool,
    output_format: str,
    use_llm: bool = False,
    llm_provider: str = "anthropic",
    llm_model: Optional[str] = None,
    quality_level: str = "professional",
    strict_mode: bool = False,
):
    """Extend solution TTL"""
    cli_ctx: CLIContext = ctx.obj

    try:
        # Prepare request body
        request_body = {"additional_days": days}

        # Make API request
        endpoint = f"/api/supply-tree/solution/{solution_id}/extend"
        response = await cli_ctx.api_client.request(
            "POST", endpoint, json_data=request_body
        )

        if output_format == "json":
            click.echo(json.dumps(response, indent=2))
        else:
            click.echo(f"✓ Solution {solution_id} TTL extended by {days} days")

    except Exception as e:
        cli_ctx.log(f"Error extending solution TTL: {str(e)}", "error")
        raise click.ClickException(f"Failed to extend solution TTL: {str(e)}")


@solution_group.command()
@click.option(
    "--max-age-days", type=int, help="Maximum age in days for solutions to keep"
)
@click.option(
    "--before-date", help="Delete solutions created before this date (YYYY-MM-DD)"
)
@click.option(
    "--dry-run",
    is_flag=True,
    help="Show what would be deleted without actually deleting",
)
@click.option(
    "--archive", is_flag=True, help="Archive stale solutions instead of deleting them"
)
@click.pass_context
@standard_cli_command(
    help_text="""
    Cleanup stale supply tree solutions.
    
    This command removes or archives solutions that are stale based on
    their age, TTL, or expiration date.
    
    Examples:
      # Dry run to see what would be deleted
      ohm solution cleanup --max-age-days 90 --dry-run
      
      # Actually delete stale solutions
      ohm solution cleanup --max-age-days 90
      
      # Archive instead of delete
      ohm solution cleanup --max-age-days 90 --archive
      
      # Delete solutions before a specific date
      ohm solution cleanup --before-date 2024-01-01
    """,
    async_cmd=True,
    track_performance=True,
    handle_errors=True,
    format_output=True,
)
async def cleanup(
    ctx,
    max_age_days: Optional[int],
    before_date: Optional[str],
    dry_run: bool,
    archive: bool,
    verbose: bool,
    output_format: str,
    use_llm: bool = False,
    llm_provider: str = "anthropic",
    llm_model: Optional[str] = None,
    quality_level: str = "professional",
    strict_mode: bool = False,
):
    """Cleanup stale solutions"""
    cli_ctx: CLIContext = ctx.obj

    try:
        # Prepare request body
        request_body = {"dry_run": dry_run}
        if max_age_days is not None:
            request_body["max_age_days"] = max_age_days
        if before_date:
            request_body["before_date"] = before_date

        # Make API request
        endpoint = "/api/supply-tree/solutions/cleanup"
        response = await cli_ctx.api_client.request(
            "POST", endpoint, json_data=request_body
        )

        # Extract cleanup data
        data = response.get("data") or response.get("result") or response
        if isinstance(data, dict) and "result" in data:
            data = data["result"]

        if output_format == "json":
            click.echo(json.dumps(data, indent=2))
        else:
            deleted_count = data.get("deleted_count", 0)
            deleted_ids = data.get("deleted_ids", [])
            is_dry_run = data.get("dry_run", dry_run)

            if is_dry_run:
                click.echo(
                    f"🔍 Dry run: Would {'archive' if archive else 'delete'} {deleted_count} solution(s)"
                )
            else:
                action = "archived" if archive else "deleted"
                click.echo(f"✓ {action.capitalize()} {deleted_count} solution(s)")

            if deleted_ids and verbose:
                click.echo("\nSolution IDs:")
                for sol_id in deleted_ids:
                    click.echo(f"  - {sol_id}")

    except Exception as e:
        cli_ctx.log(f"Error cleaning up solutions: {str(e)}", "error")
        raise click.ClickException(f"Failed to cleanup solutions: {str(e)}")
