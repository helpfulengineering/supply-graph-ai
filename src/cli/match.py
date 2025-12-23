"""
Enhanced matching commands for OME CLI with standardized patterns

This module provides standardized commands for matching OKH requirements with OKW capabilities,
including LLM integration, enhanced error handling, and consistent output formatting.
"""

import json
from pathlib import Path
from typing import Any, Dict, List, Optional
from urllib.parse import urlparse

import click
import yaml

from ..core.models.base.base_types import NormalizedCapabilities
from ..core.models.okh import OKHManifest
from ..core.services.matching_service import MatchingService
from .base import (
    CLIContext,
    SmartCommand,
    create_llm_request_data,
    format_llm_output,
    log_llm_usage,
)
from .decorators import standard_cli_command


@click.group()
def match_group():
    """
    Matching operations commands for OKH/OKW compatibility.

    These commands help you find manufacturing facilities that can produce
    your OKH designs by matching requirements with capabilities.

    Examples:
      # Match requirements from an OKH file
      ome match requirements my-design.okh.json

      # Match with specific filters
      ome match requirements my-design.okh.json --location "San Francisco" --access-type public

      # Use LLM for enhanced matching
      ome match requirements my-design.okh.json --use-llm --quality-level professional
    """
    pass


@match_group.command()
@click.argument("input_file", type=str)
@click.option(
    "--domain",
    type=click.Choice(["manufacturing", "cooking"]),
    help="Domain override (auto-detected from file if not provided)",
)
@click.option(
    "--facility-file",
    type=click.Path(exists=True),
    help="Local facility file to use for matching (testing/debugging)",
)
@click.option(
    "--access-type",
    type=click.Choice(["public", "private", "restricted"]),
    help="Filter by facility access type",
)
@click.option(
    "--facility-status",
    type=click.Choice(["active", "inactive", "maintenance"]),
    help="Filter by facility status",
)
@click.option("--location", help="Filter by location (city, country, or region)")
@click.option("--capabilities", help="Comma-separated list of required capabilities")
@click.option("--materials", help="Comma-separated list of required materials")
@click.option(
    "--min-confidence",
    type=float,
    default=0.3,
    help="Minimum confidence threshold for matches (0.0-1.0). Default: 0.3 (relaxed)",
)
@click.option(
    "--max-results", type=int, default=10, help="Maximum number of results to return"
)
@click.option(
    "--max-depth",
    type=int,
    default=0,
    help=(
        "Maximum depth for BOM explosion. "
        "0 = single-level matching (default), "
        "> 0 = nested matching with specified depth"
    ),
)
@click.option(
    "--auto-detect-depth",
    "auto_detect_depth",
    is_flag=True,
    default=False,
    help=(
        "Auto-detect if nested matching is needed based on OKH structure. "
        "If nested components detected and max_depth=0, uses configured default depth"
    ),
)
@click.option("--output", "-o", help="Output file path")
@click.option(
    "--save-solution",
    "save_solution",
    is_flag=True,
    default=False,
    help="Automatically save the solution to storage. Returns solution_id in output.",
)
@click.option(
    "--solution-ttl-days",
    "solution_ttl_days",
    type=int,
    default=None,
    help="Time-to-live in days for saved solution (default: 30). Only used if --save-solution is set.",
)
@click.option(
    "--solution-tags",
    "solution_tags",
    type=str,
    default=None,
    help="Comma-separated tags to apply to saved solution. Only used if --save-solution is set.",
)
@standard_cli_command(
    help_text="""
    Match requirements to capabilities (supports both manufacturing and cooking domains).
    
    This command analyzes an input file or URL (OKH manifest for manufacturing or recipe for cooking)
    and finds facilities (OKW facilities or kitchens) that can satisfy the requirements.
    
    Input can be:
    - Local file path (e.g., my-design.okh.json)
    - HTTP/HTTPS URL (e.g., https://example.com/manifest.json)
    
    For manufacturing domain:
    - Process requirements (3D printing, CNC machining, etc.)
    - Material requirements (PLA, metal, etc.)
    - Quality and precision requirements
    - Location and access preferences
    - Facility capabilities and equipment
    
    For cooking domain:
    - Ingredient requirements
    - Equipment requirements
    - Appliance requirements
    - Kitchen capabilities
    
    When LLM is enabled, the matching process uses advanced AI to:
    - Better understand requirements
    - Find creative solutions
    - Provide detailed explanations for matches
    - Suggest alternative approaches
    """,
    epilog="""
    Examples:
      # Match OKH requirements (manufacturing) from local file
      ome match requirements my-design.okh.json
      
      # Match OKH requirements from URL
      ome match requirements https://example.com/manifest.okh.json
      
      # Match recipe requirements (cooking)
      ome match requirements chocolate-chip-cookies-recipe.json
      
      # Match with location filter
      ome match requirements my-design.okh.json --location "Berlin"
      
      # High-confidence matches only
      ome match requirements my-design.okh.json --min-confidence 0.9
      
      # Use LLM for enhanced matching
      ome match requirements my-design.okh.json --use-llm --quality-level professional
      
      # Nested matching with custom depth
      ome match requirements my-design.okh.json --max-depth 5
      
      # Auto-detect nested matching
      ome match requirements my-design.okh.json --auto-detect-depth
      
      # Save results to file
      ome match requirements my-design.okh.json --output matches.json
      
      # Auto-save solution to storage
      ome match requirements my-design.okh.json --max-depth 3 --save-solution
      
      # Auto-save with TTL and tags
      ome match requirements my-design.okh.json --save-solution --solution-ttl-days 60 --solution-tags "production,test"
    """,
    async_cmd=True,
    track_performance=True,
    handle_errors=True,
    format_output=True,
    add_llm_config=True,
)
@click.pass_context
async def requirements(
    ctx,
    input_file: str,
    domain: Optional[str],
    facility_file: Optional[str],
    access_type: Optional[str],
    facility_status: Optional[str],
    location: Optional[str],
    capabilities: Optional[str],
    materials: Optional[str],
    min_confidence: float,
    max_results: int,
    max_depth: int,
    auto_detect_depth: bool,
    output: Optional[str],
    verbose: bool,
    output_format: str,
    use_llm: bool,
    llm_provider: str,
    llm_model: Optional[str],
    quality_level: str,
    strict_mode: bool,
    save_solution: bool = False,
    solution_ttl_days: Optional[int] = None,
    solution_tags: Optional[str] = None,
):
    """Match OKH requirements to OKW capabilities with enhanced LLM support."""
    cli_ctx = ctx.obj
    cli_ctx.start_command_tracking("match-requirements")

    # Update CLI context with parameters from decorator
    cli_ctx.update_llm_config(
        use_llm=use_llm,
        llm_provider=llm_provider,
        llm_model=llm_model,
        quality_level=quality_level,
        strict_mode=strict_mode,
    )

    try:
        # Check if input is a URL
        is_url = _is_url(input_file)

        if is_url:
            cli_ctx.log(f"Detected URL input: {input_file}", "info")
            input_data = None  # URLs will be passed directly to API
        else:
            # Read and validate input file
            cli_ctx.log("Reading input file...", "info")
            input_data = await _read_input_file(input_file)

        # Detect domain from file content if not provided
        # For URLs, default to manufacturing if domain not specified
        if is_url and not domain:
            detected_domain = "manufacturing"  # Default for URLs (most common case)
            cli_ctx.log(f"Using default domain for URL: {detected_domain}", "info")
        elif input_data:
            detected_domain = domain or _detect_domain_from_data(input_data)
            cli_ctx.log(f"Detected domain: {detected_domain}", "info")
        else:
            detected_domain = domain or "manufacturing"
            cli_ctx.log(f"Using domain: {detected_domain}", "info")

        # Parse filter options
        filters = _parse_match_filters(
            access_type,
            facility_status,
            location,
            capabilities,
            materials,
            min_confidence,
            max_results,
        )

        # Add nested matching parameters
        nested_params = {
            "max_depth": max_depth,
            "auto_detect_depth": auto_detect_depth,
        }

        # Add solution storage parameters if requested
        if save_solution:
            nested_params["save_solution"] = True
            if solution_ttl_days:
                nested_params["solution_ttl_days"] = solution_ttl_days
            if solution_tags:
                nested_params["solution_tags"] = [
                    tag.strip() for tag in solution_tags.split(",")
                ]

        # Create request data based on domain and input type
        if detected_domain == "manufacturing":
            if is_url:
                request_data = create_llm_request_data(
                    cli_ctx,
                    {
                        "okh_url": input_file,
                        "domain": detected_domain,
                        **filters,
                        **nested_params,
                    },
                )
            else:
                request_data = create_llm_request_data(
                    cli_ctx,
                    {
                        "okh_manifest": input_data,
                        "domain": detected_domain,
                        **filters,
                        **nested_params,
                    },
                )
        elif detected_domain == "cooking":
            if is_url:
                request_data = create_llm_request_data(
                    cli_ctx,
                    {
                        "recipe_url": input_file,
                        "domain": detected_domain,
                        **filters,
                        **nested_params,
                    },
                )
            else:
                request_data = create_llm_request_data(
                    cli_ctx,
                    {
                        "recipe": input_data,
                        "domain": detected_domain,
                        **filters,
                        **nested_params,
                    },
                )
        else:
            raise click.ClickException(f"Unsupported domain: {detected_domain}")

        # Log LLM usage if enabled
        if cli_ctx.is_llm_enabled():
            log_llm_usage(cli_ctx, "requirements matching")

        async def http_match():
            """Match via HTTP API"""
            # If facility_file is provided, we need to use fallback
            # (HTTP API doesn't support local facility files)
            if facility_file:
                cli_ctx.log(
                    "Local facility file provided - HTTP API doesn't support this, using fallback",
                    "info",
                )
                # Raise exception to trigger fallback
                import httpx

                raise httpx.ConnectError("Use fallback for local facility file")

            # If nested matching with local file, use fallback (BOM file resolution needs manifest path)
            if max_depth > 0 and not is_url:
                cli_ctx.log(
                    "Nested matching with local file - using fallback for BOM file resolution",
                    "info",
                )
                import httpx

                raise httpx.ConnectError(
                    "Use fallback for nested matching with local file"
                )

            cli_ctx.log("Attempting HTTP API matching...", "info")
            try:
                response = await cli_ctx.api_client.request(
                    "POST", "/api/match", json_data=request_data
                )
                # Extract data from wrapped response (api_endpoint decorator wraps it)
                if isinstance(response, dict) and "data" in response:
                    return response["data"]
                return response
            except Exception as e:
                cli_ctx.log(
                    f"HTTP API request failed: {type(e).__name__}: {e}", "debug"
                )
                raise

        async def fallback_match():
            """Match using direct service calls"""
            cli_ctx.log("Using direct service matching...", "info")

            if detected_domain == "manufacturing":
                # Handle URL or local file
                if is_url:
                    # Fetch manifest from URL
                    from ..core.services.okh_service import OKHService

                    okh_service = await OKHService.get_instance()
                    manifest = await okh_service.fetch_from_url(input_file)
                else:
                    manifest = OKHManifest.from_dict(input_data)

                matching_service = await MatchingService.get_instance()

                # Get facilities for matching with filters
                from ..core.services.okw_service import OKWService

                okw_service = await OKWService.get_instance()

                # Build filter_params for okw_service.list() if filters are provided
                filter_params = {}
                if filters.get("access_type"):
                    filter_params["access_type"] = filters.get("access_type")
                if filters.get("facility_status"):
                    filter_params["facility_status"] = filters.get("facility_status")
                if filters.get("location"):
                    filter_params["location"] = filters.get("location")

                facilities, _ = await okw_service.list(
                    filter_params=filter_params if filter_params else None
                )

                # Apply additional filters that aren't supported by okw_service.list()
                # (e.g., capabilities, materials would need more complex matching logic)

                # Determine matching mode based on max_depth
                # Use configured default if auto_detect_depth is enabled
                effective_max_depth = max_depth
                if auto_detect_depth and max_depth == 0:
                    # Check if manifest has nested components
                    from src.config.settings import MAX_DEPTH

                    from ..core.api.routes.match import _has_nested_components

                    if _has_nested_components(manifest):
                        effective_max_depth = MAX_DEPTH
                        cli_ctx.log(
                            f"Auto-detected nested components, using max_depth={MAX_DEPTH}",
                            "info",
                        )

                # Perform matching (nested or single-level)
                if effective_max_depth > 0:
                    # Nested matching
                    from ..core.services.okh_service import OKHService

                    okh_service = await OKHService.get_instance()
                    # Pass manifest path for BOM file resolution
                    manifest_path = input_file if not is_url else None
                    solution = await matching_service.match_with_nested_components(
                        okh_manifest=manifest,
                        facilities=facilities,
                        max_depth=effective_max_depth,
                        domain=detected_domain,
                        okh_service=okh_service,
                        manifest_path=manifest_path,
                    )

                    # Save solution if requested
                    solution_id = None
                    if save_solution:
                        try:
                            from ..config.storage_config import (
                                get_default_storage_config,
                            )
                            from ..core.services.storage_service import StorageService

                            storage_service = await StorageService.get_instance()
                            await storage_service.configure(
                                get_default_storage_config()
                            )

                            # Parse tags if provided
                            tags_list = None
                            if solution_tags:
                                tags_list = [
                                    tag.strip() for tag in solution_tags.split(",")
                                ]

                            # Use default TTL of 30 days if not provided
                            ttl_days = (
                                solution_ttl_days
                                if solution_ttl_days is not None
                                else 30
                            )
                            solution_id = (
                                await storage_service.save_supply_tree_solution(
                                    solution,
                                    ttl_days=ttl_days,
                                    tags=tags_list,
                                )
                            )
                            cli_ctx.log(
                                f"Solution saved to storage with ID: {solution_id}",
                                "info",
                            )
                        except Exception as e:
                            cli_ctx.log(f"Failed to save solution: {str(e)}", "warning")
                            # Continue without failing the match

                    # Convert to response format matching API
                    # For nested solutions, count trees, not solutions
                    solution_dict = solution.to_dict()
                    num_trees = len(solution.all_trees) if solution.all_trees else 0
                    result = {
                        "solutions": [
                            solution_dict
                        ],  # Wrap in array for consistency with display logic
                        "solution": solution_dict,  # Also include singular for API compatibility
                        "total_solutions": num_trees,  # Count trees found, not solution count
                        "matching_mode": "nested",
                        "processing_time": 0.0,  # Fallback doesn't track time
                    }
                    if solution_id:
                        result["solution_id"] = str(solution_id)
                    return result
                else:
                    # Single-level matching
                    results = await matching_service.find_matches_with_manifest(
                        manifest, facilities, explicit_domain=detected_domain
                    )

                    # Convert Set to List
                    results_list = list(results)

                    # Apply min_confidence filter if provided
                    min_confidence = filters.get("min_confidence", 0.0)
                    if min_confidence > 0.0:
                        results_list = [
                            r for r in results_list if r.score >= min_confidence
                        ]

                    # Apply max_results limit if provided
                    max_results = filters.get("max_results")
                    if max_results and max_results > 0:
                        # Sort by score (descending) before limiting
                        results_list = sorted(
                            results_list, key=lambda x: x.score, reverse=True
                        )[:max_results]

                    # Save solution if requested (save best solution for single-level)
                    solution_id = None
                    if save_solution and results_list:
                        try:
                            from ..config.storage_config import (
                                get_default_storage_config,
                            )
                            from ..core.models.supply_trees import (
                                SupplyTree,
                                SupplyTreeSolution,
                            )
                            from ..core.services.storage_service import StorageService

                            storage_service = await StorageService.get_instance()
                            await storage_service.configure(
                                get_default_storage_config()
                            )

                            # Convert best result to SupplyTreeSolution
                            best_result = results_list[0]  # Already sorted by score
                            tree = SupplyTree.from_dict(best_result.to_dict())

                            solution = SupplyTreeSolution(
                                all_trees=[tree],
                                score=best_result.score,
                                metadata={
                                    "okh_id": (
                                        str(manifest.id)
                                        if hasattr(manifest, "id")
                                        else None
                                    ),
                                    "matching_mode": "single-level",
                                },
                            )

                            # Parse tags if provided
                            tags_list = None
                            if solution_tags:
                                tags_list = [
                                    tag.strip() for tag in solution_tags.split(",")
                                ]

                            # Use default TTL of 30 days if not provided
                            ttl_days = (
                                solution_ttl_days
                                if solution_ttl_days is not None
                                else 30
                            )
                            solution_id = (
                                await storage_service.save_supply_tree_solution(
                                    solution,
                                    ttl_days=ttl_days,
                                    tags=tags_list,
                                )
                            )
                            cli_ctx.log(
                                f"Solution saved to storage with ID: {solution_id}",
                                "info",
                            )
                        except Exception as e:
                            cli_ctx.log(f"Failed to save solution: {str(e)}", "warning")
                            # Continue without failing the match

                    if results_list:
                        result = {
                            "solutions": [r.to_dict() for r in results_list],
                            "total_solutions": len(results_list),
                            "matching_mode": "single-level",
                        }
                        if solution_id:
                            result["solution_id"] = str(solution_id)
                        return result
                    else:
                        return {
                            "solutions": [],
                            "total_solutions": 0,
                            "matching_mode": "single-level",
                            "message": "No matching facilities found",
                        }
            elif detected_domain == "cooking":
                # Use cooking domain extractor and matcher
                from ..config.storage_config import get_default_storage_config
                from ..core.domains.cooking.extractors import CookingExtractor
                from ..core.domains.cooking.matchers import CookingMatcher
                from ..core.services.storage_service import StorageService

                # Handle URL or local file for cooking domain
                if is_url:
                    # Fetch recipe from URL
                    import httpx

                    async with httpx.AsyncClient(timeout=120.0) as client:
                        response = await client.get(input_file)
                        response.raise_for_status()
                        content = response.text
                        if input_file.endswith(
                            (".yaml", ".yml")
                        ) or "yaml" in response.headers.get("content-type", ""):
                            import yaml

                            recipe_data = yaml.safe_load(content)
                        else:
                            recipe_data = json.loads(content)
                else:
                    recipe_data = input_data

                extractor = CookingExtractor()
                matcher = CookingMatcher()

                # Extract requirements from recipe
                extraction_result = extractor.extract_requirements(recipe_data)
                requirements = (
                    extraction_result.data if extraction_result.data else None
                )

                if not requirements:
                    return {
                        "solutions": [],
                        "total_solutions": 0,
                        "message": "Failed to extract requirements from recipe",
                    }

                # Load kitchens - either from local file or from storage
                kitchens = []

                if facility_file:
                    # Use local facility file for testing/debugging
                    cli_ctx.log(f"Using local facility file: {facility_file}", "info")
                    try:
                        with open(facility_file, "r") as f:
                            kitchen_data = json.load(f)
                        kitchens.append(kitchen_data)
                        cli_ctx.log(
                            f"✅ Loaded kitchen from file: {kitchen_data.get('name', 'Unknown')} (ID: {kitchen_data.get('id', 'N/A')[:8]})",
                            "info",
                        )
                        if cli_ctx.verbose:
                            cli_ctx.log(
                                f"Kitchen data: {json.dumps(kitchen_data, indent=2, default=str)[:500]}...",
                                "info",
                            )
                    except Exception as e:
                        cli_ctx.log(f"Failed to load facility file: {e}", "error")
                        raise click.ClickException(f"Failed to load facility file: {e}")
                else:
                    # Load kitchens from storage using OKWService for proper discovery
                    from ..core.services.okw_service import OKWService

                    okw_service = await OKWService.get_instance()

                    # Get all facilities (OKWService handles discovery properly)
                    facilities, total = await okw_service.list()

                    cli_ctx.log(f"Found {total} total facilities in storage", "info")

                    # Filter for cooking domain facilities (kitchens)
                    for facility in facilities:
                        # Check if facility is in cooking domain
                        facility_dict = facility.to_dict()
                        facility_domain = facility_dict.get("domain", "manufacturing")
                        facility_name = facility_dict.get("name", "").lower()
                        facility_desc = facility_dict.get("description", "").lower()

                        # Include if domain is cooking, or if name/description contains cooking-related keywords
                        is_cooking = (
                            facility_domain == "cooking"
                            or "kitchen" in facility_name
                            or "dessert" in facility_name
                            or "cooking" in facility_desc
                            or "recipe" in facility_desc
                        )

                        if is_cooking:
                            kitchens.append(facility_dict)
                            cli_ctx.log(
                                f"Loaded kitchen: {facility_dict.get('name', 'Unknown')} (ID: {facility_dict.get('id', 'N/A')[:8]}, domain: {facility_domain})",
                                "info",
                            )

                    cli_ctx.log(
                        f"Loaded {len(kitchens)} kitchens from storage (filtered from {total} total facilities)",
                        "info",
                    )

                # Match against each kitchen
                solutions = []
                cli_ctx.log(
                    f"Starting matching process for {len(kitchens)} kitchen(s)...",
                    "info",
                )

                if len(kitchens) == 0:
                    cli_ctx.log(
                        "⚠️  No kitchens loaded - cannot perform matching", "warning"
                    )
                    return {
                        "solutions": [],
                        "total_solutions": 0,
                        "message": "No kitchens found to match against",
                    }

                for kitchen in kitchens:
                    kitchen_name = kitchen.get("name", "Unknown")
                    cli_ctx.log(f"🔍 Matching against kitchen: {kitchen_name}", "info")

                    # Extract requirements (for debugging)
                    if cli_ctx.verbose:
                        req_content = (
                            requirements.content
                            if hasattr(requirements, "content")
                            else requirements
                        )
                        cli_ctx.log(f"Requirements to match: {req_content}", "debug")

                    # Extract capabilities from kitchen
                    cli_ctx.log(f"Extracting capabilities from kitchen data...", "info")
                    capabilities_result = extractor.extract_capabilities(kitchen)
                    capabilities = (
                        capabilities_result.data if capabilities_result.data else None
                    )

                    if not capabilities:
                        cli_ctx.log(
                            f"⚠️  No capabilities extracted from kitchen: {kitchen_name}",
                            "warning",
                        )
                        if cli_ctx.verbose:
                            cli_ctx.log(
                                f"Kitchen data structure: {list(kitchen.keys())}",
                                "info",
                            )
                            cli_ctx.log(
                                f"Kitchen equipment: {kitchen.get('equipment', [])}",
                                "info",
                            )
                            cli_ctx.log(
                                f"Kitchen typical_materials: {kitchen.get('typical_materials', [])}",
                                "info",
                            )
                        # Still try to match with empty capabilities (will result in low confidence)
                        capabilities = NormalizedCapabilities(
                            content={
                                "available_ingredients": [],
                                "available_tools": [],
                                "appliances": [],
                            },
                            domain="cooking",
                        )

                    cap_content = (
                        capabilities.content
                        if hasattr(capabilities, "content")
                        else capabilities
                    )
                    cli_ctx.log(
                        f"✅ Extracted capabilities: ingredients={len(cap_content.get('available_ingredients', []))}, tools={len(cap_content.get('available_tools', []))}, appliances={len(cap_content.get('appliances', []))}",
                        "info",
                    )
                    if cli_ctx.verbose:
                        cli_ctx.log(f"Full capabilities: {cap_content}", "info")
                        req_content = (
                            requirements.content
                            if hasattr(requirements, "content")
                            else requirements
                        )
                        cli_ctx.log(f"Requirements to match: {req_content}", "info")

                    # Get kitchen and recipe names for supply tree
                    recipe_name = recipe_data.get(
                        "title", recipe_data.get("name", "Unknown Recipe")
                    )
                    cli_ctx.log(
                        f"Generating supply tree for recipe '{recipe_name}' and kitchen '{kitchen_name}'...",
                        "info",
                    )

                    try:
                        supply_tree = matcher.generate_supply_tree(
                            requirements, capabilities, kitchen_name, recipe_name
                        )
                        confidence = (
                            supply_tree.confidence_score
                            if hasattr(supply_tree, "confidence_score")
                            else 0.8
                        )
                        cli_ctx.log(f"✅ Match confidence: {confidence:.2f}", "info")
                    except Exception as e:
                        cli_ctx.log(
                            f"❌ Error generating supply tree: {type(e).__name__}: {e}",
                            "error",
                        )
                        if cli_ctx.verbose:
                            import traceback

                            cli_ctx.log(f"Traceback: {traceback.format_exc()}", "info")
                        continue

                    solution = {
                        "tree": (
                            supply_tree.to_dict()
                            if hasattr(supply_tree, "to_dict")
                            else supply_tree
                        ),
                        "facility": kitchen,
                        "facility_id": kitchen.get(
                            "id", kitchen.get("storage_key", "unknown")
                        ),
                        "facility_name": kitchen_name,
                        "match_type": "cooking",
                        "confidence": confidence,
                        "score": confidence,  # Add score for consistency with manufacturing domain
                    }
                    solutions.append(solution)

                # Apply min_confidence filter if provided
                min_confidence = filters.get("min_confidence", 0.0)
                if min_confidence > 0.0:
                    solutions = [
                        s
                        for s in solutions
                        if s.get("confidence", s.get("score", 0)) >= min_confidence
                    ]

                # Apply max_results limit if provided
                max_results = filters.get("max_results")
                if max_results and max_results > 0:
                    # Sort by confidence (descending) before limiting
                    solutions = sorted(
                        solutions,
                        key=lambda x: x.get("confidence", x.get("score", 0)),
                        reverse=True,
                    )[:max_results]

                return {"solutions": solutions, "total_solutions": len(solutions)}
            else:
                raise click.ClickException(f"Unsupported domain: {detected_domain}")

        # Execute matching with fallback
        command = SmartCommand(cli_ctx)
        result = await command.execute_with_fallback(http_match, fallback_match)

        # Handle None result (when http_match returns None to force fallback)
        if result is None:
            cli_ctx.log("HTTP API returned None, using fallback result", "info")
            result = await fallback_match()

        # Process and display results
        await _display_match_results(cli_ctx, result, output, output_format)

        cli_ctx.end_command_tracking()

    except Exception as e:
        cli_ctx.log(f"Matching failed: {str(e)}", "error")
        raise
    finally:
        # Always cleanup resources (storage service, aiohttp sessions, etc.)
        # This ensures cleanup happens even if there's an error
        try:
            cli_ctx.log("Starting cleanup...", "info")
            await cli_ctx.cleanup()
            cli_ctx.log("Cleanup completed", "info")
        except Exception as e:
            cli_ctx.log(f"Warning during cleanup: {e}", "warning")
            # Continue - cleanup errors shouldn't fail the command


@match_group.command()
@click.argument("okh_file", type=click.Path(exists=True))
@click.option(
    "--domain",
    type=click.Choice(["manufacturing", "cooking"]),
    help="Domain override (auto-detected from file if not provided)",
)
@click.option("--output", "-o", help="Output file path")
@standard_cli_command(
    help_text="""
    Validate OKH manifest for matching compatibility.
    
    This command validates that an OKH manifest contains all necessary
    information for successful matching operations.
    
    Validation checks include:
    - Required fields are present
    - Process requirements are properly specified
    - Material requirements are valid
    - Manufacturing specifications are complete
    - File format and structure are correct
    
    When LLM is enabled, validation includes:
    - Semantic analysis of requirements
    - Suggestions for missing information
    - Quality assessment of specifications
    - Recommendations for improvement
    """,
    async_cmd=True,
    track_performance=True,
    handle_errors=True,
    format_output=True,
    add_llm_config=True,
)
@click.pass_context
async def validate(
    ctx,
    okh_file: str,
    domain: Optional[str],
    output: Optional[str],
    verbose: bool,
    output_format: str,
    use_llm: bool,
    llm_provider: str,
    llm_model: Optional[str],
    quality_level: str,
    strict_mode: bool,
):
    """Validate OKH manifest for matching compatibility."""
    cli_ctx = ctx.obj
    cli_ctx.start_command_tracking("validate-okh")

    # Update CLI context with parameters from decorator
    cli_ctx.update_llm_config(
        use_llm=use_llm,
        llm_provider=llm_provider,
        llm_model=llm_model,
        quality_level=quality_level,
        strict_mode=strict_mode,
    )

    try:
        # Read input file
        cli_ctx.log("Reading input file...", "info")
        input_data = await _read_input_file(okh_file)

        # Detect or use explicit domain
        detected_domain = (
            domain or _detect_domain_from_data(input_data) if input_data else None
        )
        if detected_domain:
            cli_ctx.log(f"Using domain: {detected_domain}", "info")
            # Set domain in input_data so API can detect it
            if input_data and not input_data.get("domain"):
                input_data["domain"] = detected_domain

        # Log LLM usage if enabled
        if cli_ctx.is_llm_enabled():
            log_llm_usage(cli_ctx, "OKH validation")

        async def http_validate():
            """Validate via HTTP API (using OKH validate endpoint)"""
            cli_ctx.log("Validating via HTTP API...", "info")
            # Use OKH validate endpoint which accepts content directly
            request_data = create_llm_request_data(
                cli_ctx, {"content": input_data, "validation_context": quality_level}
            )
            response = await cli_ctx.api_client.request(
                "POST",
                "/api/okh/validate",
                json_data=request_data,
                params={"quality_level": quality_level, "strict_mode": strict_mode},
            )
            return response

        async def fallback_validate():
            """Validate using direct service calls"""
            cli_ctx.log("Using direct service validation...", "info")
            manifest = OKHManifest.from_dict(input_data)

            # Basic validation
            validation_result = {
                "is_valid": True,
                "errors": [],
                "warnings": [],
                "suggestions": [],
            }

            # Check required fields
            required_fields = ["title", "version"]
            for field in required_fields:
                if field not in input_data:
                    validation_result["errors"].append(
                        f"Missing required field: {field}"
                    )
                    validation_result["is_valid"] = False

            # Check for manufacturing_specs or manufacturing_processes for manufacturing domain
            if input_data.get("domain") == "manufacturing" or (
                not input_data.get("domain") and "manufacturing_processes" in input_data
            ):
                if (
                    "manufacturing_specs" not in input_data
                    and "manufacturing_processes" not in input_data
                ):
                    validation_result["warnings"].append(
                        "Missing manufacturing_specs or manufacturing_processes (recommended for manufacturing domain)"
                    )

            return validation_result

        # Execute validation with fallback
        command = SmartCommand(cli_ctx)
        result = await command.execute_with_fallback(http_validate, fallback_validate)

        # Display validation results
        await _display_validation_results(cli_ctx, result, output, output_format)

        cli_ctx.end_command_tracking()

    except Exception as e:
        cli_ctx.log(f"Validation failed: {str(e)}", "error")
        raise


@match_group.command()
@click.option("--domain", help="Filter by specific domain")
@click.option("--active-only", is_flag=True, help="Show only active domains")
@standard_cli_command(
    help_text="""
    List available matching domains.
    
    This command shows all available domains that can be used for matching
    operations, such as manufacturing, cooking, etc.
    
    Each domain provides specific matching capabilities and algorithms
    tailored to that domain's requirements and constraints.
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
    domain: Optional[str],
    active_only: bool,
    verbose: bool,
    output_format: str,
    use_llm: bool,
    llm_provider: str,
    llm_model: Optional[str],
    quality_level: str,
    strict_mode: bool,
):
    """List available matching domains."""
    cli_ctx = ctx.obj
    cli_ctx.start_command_tracking("list-domains")

    # Update CLI context with parameters from decorator
    cli_ctx.update_llm_config(
        use_llm=use_llm,
        llm_provider=llm_provider,
        llm_model=llm_model,
        quality_level=quality_level,
        strict_mode=strict_mode,
    )

    try:
        # Create request data with LLM configuration
        request_data = create_llm_request_data(
            cli_ctx, {"domain": domain, "active_only": active_only}
        )

        async def http_domains():
            """Get domains via HTTP API"""
            cli_ctx.log("Fetching domains via HTTP API...", "info")
            response = await cli_ctx.api_client.request(
                "GET", "/api/match/domains", params=request_data
            )
            return response

        async def fallback_domains():
            """Get domains using direct service calls"""
            cli_ctx.log("Using direct service for domains...", "info")
            matching_service = await MatchingService.get_instance()
            domains = await matching_service.get_available_domains()

            return {
                "domains": domains,  # domains are already dictionaries
                "total_count": len(domains),
            }

        # Execute with fallback
        command = SmartCommand(cli_ctx)
        result = await command.execute_with_fallback(http_domains, fallback_domains)

        # Display domains
        await _display_domains(cli_ctx, result, output_format)

        cli_ctx.end_command_tracking()

    except Exception as e:
        cli_ctx.log(f"Failed to list domains: {str(e)}", "error")
        raise


# Helper functions


def _is_url(path: str) -> bool:
    """Check if the given path is a URL."""
    try:
        result = urlparse(path)
        return result.scheme in ("http", "https")
    except Exception:
        return False


async def _read_input_file(file_path: str) -> Optional[Dict[str, Any]]:
    """
    Read and parse input file (OKH or recipe) from local file or URL.

    Returns None if the input is a URL (to indicate it should be passed as okh_url).
    Returns the parsed data if it's a local file.
    """
    # Check if it's a URL
    if _is_url(file_path):
        # Return None to indicate this is a URL that should be passed directly
        return None

    # Handle local file
    input_path = Path(file_path)

    # Check if file exists
    if not input_path.exists():
        raise click.ClickException(f"File not found: {file_path}")

    try:
        with open(input_path, "r") as f:
            if input_path.suffix.lower() in [".yaml", ".yml"]:
                import yaml

                return yaml.safe_load(f)
            else:
                return json.load(f)
    except Exception as e:
        raise click.ClickException(f"Failed to read input file: {str(e)}")


def _detect_domain_from_data(data: Dict[str, Any]) -> str:
    """Detect domain from input data structure."""
    # First check for explicit domain field
    if "domain" in data and data["domain"]:
        return data["domain"]

    # Check for OKH/manufacturing indicators
    if (
        "title" in data
        and "version" in data
        and ("manufacturing_specs" in data or "manufacturing_processes" in data)
    ):
        return "manufacturing"

    # Check for recipe/cooking indicators
    if "ingredients" in data and "instructions" in data and "name" in data:
        return "cooking"

    # Default to manufacturing for backward compatibility
    return "manufacturing"


def _parse_match_filters(
    access_type: Optional[str],
    facility_status: Optional[str],
    location: Optional[str],
    capabilities: Optional[str],
    materials: Optional[str],
    min_confidence: float,
    max_results: int,
) -> Dict[str, Any]:
    """Parse and validate match filter options."""
    filters = {
        "access_type": access_type,
        "facility_status": facility_status,
        "location": location,
        "min_confidence": min_confidence,
        "max_results": max_results,
    }

    # Parse comma-separated lists
    if capabilities:
        filters["capabilities"] = [cap.strip() for cap in capabilities.split(",")]
    if materials:
        filters["materials"] = [mat.strip() for mat in materials.split(",")]

    return filters


async def _display_match_results(
    cli_ctx: CLIContext,
    result: Dict[str, Any],
    output: Optional[str],
    output_format: str,
):
    """Display matching results in the specified format."""
    # Handle both old format (matches) and new format (solutions)
    solutions = result.get("solutions", result.get("matches", []))
    total_solutions = result.get("total_solutions", len(solutions))

    # Check if solution was saved (from API response or fallback)
    solution_id = result.get("solution_id")
    if solution_id:
        cli_ctx.log(f"✓ Solution saved to storage with ID: {solution_id}", "success")

    if total_solutions == 0:
        cli_ctx.log("No matching facilities found", "warning")
        # Still save to output file if requested, even with no results
        if output and output_format == "json":
            output_data = format_llm_output(result, cli_ctx)
            with open(output, "w") as f:
                f.write(output_data)
            cli_ctx.log(f"Results saved to {output}", "success")
        return

    cli_ctx.log(f"Found {total_solutions} matching facilities", "success")

    # Format output based on format preference
    if output_format == "json":
        output_data = format_llm_output(result, cli_ctx)
        if output:
            with open(output, "w") as f:
                f.write(output_data)
            cli_ctx.log(f"Results saved to {output}", "success")
        else:
            click.echo(output_data)
    else:
        # Table format
        for i, solution in enumerate(solutions, 1):
            # Handle both old format (direct match dict) and new format (solution with tree/facility)
            if "facility" in solution:
                facility = solution.get("facility", {})
                facility_name = (
                    facility.get("name", "Unknown Facility")
                    if isinstance(facility, dict)
                    else getattr(facility, "name", "Unknown Facility")
                )
                confidence = solution.get("confidence", 0)
            else:
                facility_name = solution.get("name", "Unknown Facility")
                confidence = solution.get("confidence", solution.get("score", 0))

            click.echo(f"\n{i}. {facility_name}")

            # Show facility ID if available
            facility_id = solution.get("facility_id")
            if facility_id:
                # Show full UUID (needed for subsequent commands like 'okw get')
                click.echo(f"   ID: {facility_id}")

            if "facility" in solution and isinstance(solution["facility"], dict):
                location = solution["facility"].get("location", "Unknown")
                if location != "Unknown":
                    click.echo(f"   Location: {location}")
            click.echo(f"   Confidence: {confidence:.2f}")

            # Show match type if available
            match_type = solution.get("match_type", "unknown")
            if match_type != "unknown":
                click.echo(f"   Match Type: {match_type}")


async def _display_validation_results(
    cli_ctx: CLIContext,
    result: Dict[str, Any],
    output: Optional[str],
    output_format: str,
):
    """Display validation results."""
    is_valid = result.get("is_valid", False)
    errors = result.get("errors", [])
    warnings = result.get("warnings", [])
    suggestions = result.get("suggestions", [])

    if is_valid:
        cli_ctx.log("OKH manifest is valid", "success")
    else:
        cli_ctx.log("OKH manifest has validation errors", "error")

    # Display errors
    for error in errors:
        cli_ctx.log(f"Error: {error}", "error")

    # Display warnings
    for warning in warnings:
        cli_ctx.log(f"Warning: {warning}", "warning")

    # Display suggestions
    for suggestion in suggestions:
        cli_ctx.log(f"Suggestion: {suggestion}", "info")

    # Save to file if requested
    if output:
        with open(output, "w") as f:
            json.dump(result, f, indent=2)
        cli_ctx.log(f"Validation results saved to {output}", "success")


async def _display_domains(
    cli_ctx: CLIContext, result: Dict[str, Any], output_format: str
):
    """Display available domains."""
    # Handle both PaginatedResponse format (from API) and simple dict format (from fallback)
    if "items" in result:
        # PaginatedResponse format from API
        domains = result.get("items", [])
        pagination = result.get("pagination", {})
        total_count = pagination.get("total_items", len(domains))
    elif "data" in result and isinstance(result["data"], dict):
        # Wrapped response format
        data = result["data"]
        if "items" in data:
            domains = data.get("items", [])
            pagination = data.get("pagination", {})
            total_count = pagination.get("total_items", len(domains))
        else:
            domains = data.get("domains", [])
            total_count = len(domains)
    else:
        # Simple dict format (from fallback)
        domains = result.get("domains", [])
        total_count = result.get("total_count", len(domains))

    cli_ctx.log(f"Found {total_count} available domains", "success")

    if output_format == "json":
        output_data = format_llm_output(result, cli_ctx)
        click.echo(output_data)
    else:
        # Table format
        for domain in domains:
            click.echo(f"\n{domain.get('name', 'Unknown Domain')}")
            click.echo(f"  ID: {domain.get('id', 'unknown')}")
            click.echo(f"  Description: {domain.get('description', 'No description')}")
            click.echo(f"  Status: {domain.get('status', 'unknown')}")


# ============================================================================
# Rules Management Commands
# ============================================================================


@match_group.group()
def rules():
    """
    Manage matching rules for capability matching.

    These commands allow you to inspect, modify, import, export, and validate
    the rules used for matching requirements to capabilities.

    Examples:
      # List all rules
      ome match rules list

      # Get a specific rule
      ome match rules get manufacturing cnc_machining_capability

      # Create a new rule interactively
      ome match rules create --interactive

      # Import rules from file
      ome match rules import rules.yaml
    """
    pass


def _read_rule_file(file_path: str) -> Dict[str, Any]:
    """Read rule data from YAML or JSON file"""
    path = Path(file_path)
    if not path.exists():
        raise click.ClickException(f"File not found: {file_path}")

    content = path.read_text()

    if path.suffix.lower() in [".yaml", ".yml"]:
        try:
            return yaml.safe_load(content)
        except yaml.YAMLError as e:
            raise click.ClickException(f"Invalid YAML file: {e}")
    elif path.suffix.lower() == ".json":
        try:
            return json.loads(content)
        except json.JSONDecodeError as e:
            raise click.ClickException(f"Invalid JSON file: {e}")
    else:
        raise click.ClickException(
            f"Unsupported file format: {path.suffix}. Use .yaml or .json"
        )


def _interactive_rule_creation() -> Dict[str, Any]:
    """Interactive rule creation wizard"""
    click.echo("\n=== Creating New Rule ===")

    rule_id = click.prompt("Rule ID", type=str)
    capability = click.prompt("Capability", type=str)

    click.echo("\nEnter requirements (one per line, empty line to finish):")
    requirements = []
    while True:
        req = click.prompt("Requirement", default="", show_default=False)
        if not req.strip():
            break
        requirements.append(req.strip())

    if not requirements:
        raise click.ClickException("At least one requirement is required")

    confidence = click.prompt("Confidence (0.0-1.0)", type=float, default=0.9)
    if not 0.0 <= confidence <= 1.0:
        raise click.ClickException("Confidence must be between 0.0 and 1.0")

    domain = click.prompt("Domain", type=str, default="general")
    description = click.prompt("Description", default="", show_default=False)

    tags_input = click.prompt("Tags (comma-separated)", default="", show_default=False)
    tags = [t.strip() for t in tags_input.split(",") if t.strip()] if tags_input else []

    return {
        "id": rule_id,
        "type": "capability_match",
        "capability": capability,
        "satisfies_requirements": requirements,
        "confidence": confidence,
        "domain": domain,
        "description": description,
        "tags": tags,
        "direction": "bidirectional",
    }


@rules.command("list")
@click.option("--domain", help="Filter by domain")
@click.option("--tag", help="Filter by tag")
@click.option("--include-metadata", is_flag=True, help="Include metadata in output")
@standard_cli_command(
    help_text="List all matching rules, optionally filtered by domain or tag.",
    async_cmd=True,
    track_performance=True,
    handle_errors=True,
    format_output=True,
)
@click.pass_context
async def rules_list(
    ctx,
    domain: Optional[str],
    tag: Optional[str],
    include_metadata: bool,
    verbose: bool,
    output_format: str,
    use_llm: bool,
    llm_provider: str,
    llm_model: Optional[str],
    quality_level: str,
    strict_mode: bool,
):
    """List all matching rules"""
    cli_ctx = ctx.obj
    cli_ctx.start_command_tracking("rules-list")

    try:
        params = {}
        if domain:
            params["domain"] = domain
        if tag:
            params["tag"] = tag
        if include_metadata:
            params["include_metadata"] = "true"

        response = await cli_ctx.api_client.request(
            "GET", "/api/match/rules", params=params
        )

        if output_format == "json":
            click.echo(json.dumps(response.get("data", {}), indent=2))
        else:
            data = response.get("data", {})
            rules_data = data.get("rules", [])
            # API returns "total" not "total_rules"
            total = data.get("total", data.get("total_rules", 0))

            # Handle both list and dict formats
            if isinstance(rules_data, list):
                # Flat list format - group by domain
                click.echo(f"\nTotal rules: {total}")
                domains_dict = {}
                for rule in rules_data:
                    rule_domain = rule.get("domain", "unknown")
                    if rule_domain not in domains_dict:
                        domains_dict[rule_domain] = []
                    domains_dict[rule_domain].append(rule)

                for dom, rules in domains_dict.items():
                    click.echo(f"\nDomain: {dom} ({len(rules)} rules)")
                    for rule in rules:
                        rule_id = rule.get("id", "unknown")
                        capability = rule.get("capability", "N/A")
                        # Format: ID (capability) - makes ID clearly visible and usable
                        click.echo(f"  {rule_id} - {capability}")
                        if tag or verbose:
                            click.echo(
                                f"    Requirements: {', '.join(rule.get('satisfies_requirements', []))}"
                            )
            elif isinstance(rules_data, dict):
                # Dict format (grouped by domain)
                click.echo(f"\nTotal rules: {total}")
                for dom, rules in rules_data.items():
                    click.echo(f"\nDomain: {dom} ({len(rules)} rules)")
                    for rule in rules:
                        rule_id = rule.get("id", "unknown")
                        capability = rule.get("capability", "N/A")
                        # Format: ID (capability) - makes ID clearly visible and usable
                        click.echo(f"  {rule_id} - {capability}")
                        if tag or verbose:
                            click.echo(
                                f"    Requirements: {', '.join(rule.get('satisfies_requirements', []))}"
                            )
            else:
                click.echo(f"\nTotal rules: {total}")
                click.echo("No rules found.")

        cli_ctx.end_command_tracking()
    except Exception as e:
        cli_ctx.end_command_tracking()
        raise


@rules.command("get")
@click.argument("domain", type=str)
@click.argument("rule_id", type=str)
@standard_cli_command(
    help_text="Get a specific rule by domain and ID.",
    async_cmd=True,
    track_performance=True,
    handle_errors=True,
    format_output=True,
)
@click.pass_context
async def rules_get(
    ctx,
    domain: str,
    rule_id: str,
    verbose: bool,
    output_format: str,
    use_llm: bool,
    llm_provider: str,
    llm_model: Optional[str],
    quality_level: str,
    strict_mode: bool,
):
    """Get a specific rule"""
    cli_ctx = ctx.obj
    cli_ctx.start_command_tracking("rules-get")

    try:
        response = await cli_ctx.api_client.request(
            "GET", f"/api/match/rules/{domain}/{rule_id}"
        )

        if output_format == "json":
            click.echo(json.dumps(response.get("data", {}), indent=2))
        else:
            rule = response.get("data", {})
            click.echo(f"\nRule: {rule.get('id')}")
            click.echo(f"  Domain: {rule.get('domain')}")
            click.echo(f"  Capability: {rule.get('capability')}")
            click.echo(
                f"  Requirements: {', '.join(rule.get('satisfies_requirements', []))}"
            )
            click.echo(f"  Confidence: {rule.get('confidence')}")
            if rule.get("description"):
                click.echo(f"  Description: {rule.get('description')}")

        cli_ctx.end_command_tracking()
    except Exception as e:
        cli_ctx.end_command_tracking()
        raise


@rules.command("create")
@click.option("--file", type=click.Path(exists=True), help="Rule file (YAML/JSON)")
@click.option("--interactive", "-i", is_flag=True, help="Interactive mode")
@standard_cli_command(
    help_text="Create a new rule from file or interactively.",
    async_cmd=True,
    track_performance=True,
    handle_errors=True,
    format_output=True,
)
@click.pass_context
async def rules_create(
    ctx,
    file: Optional[str],
    interactive: bool,
    verbose: bool,
    output_format: str,
    use_llm: bool,
    llm_provider: str,
    llm_model: Optional[str],
    quality_level: str,
    strict_mode: bool,
):
    """Create a new rule"""
    cli_ctx = ctx.obj
    cli_ctx.start_command_tracking("rules-create")

    try:
        if interactive:
            rule_data = _interactive_rule_creation()
        elif file:
            file_data = _read_rule_file(file)
            # If file contains a rule set, extract first rule or use structure
            if "rules" in file_data:
                # Multi-rule file, use first rule
                rules_dict = file_data["rules"]
                if rules_dict:
                    rule_data = list(rules_dict.values())[0]
                else:
                    raise click.ClickException("No rules found in file")
            elif "id" in file_data and "capability" in file_data:
                # Single rule file
                rule_data = file_data
            else:
                raise click.ClickException("Invalid rule file format")
        else:
            raise click.ClickException(
                "Either --file or --interactive must be specified"
            )

        response = await cli_ctx.api_client.request(
            "POST", "/api/match/rules", json_data={"rule_data": rule_data}
        )

        if output_format == "json":
            click.echo(json.dumps(response.get("data", {}), indent=2))
        else:
            cli_ctx.log("Rule created successfully", "success")
            rule = response.get("data", {})
            click.echo(f"Created rule: {rule.get('id')} in domain {rule.get('domain')}")

        cli_ctx.end_command_tracking()
    except Exception as e:
        cli_ctx.end_command_tracking()
        raise


@rules.command("update")
@click.argument("domain", type=str)
@click.argument("rule_id", type=str)
@click.option("--file", type=click.Path(exists=True), help="Updated rule file")
@click.option("--interactive", "-i", is_flag=True, help="Interactive mode")
@standard_cli_command(
    help_text="Update an existing rule from file or interactively.",
    async_cmd=True,
    track_performance=True,
    handle_errors=True,
    format_output=True,
)
@click.pass_context
async def rules_update(
    ctx,
    domain: str,
    rule_id: str,
    file: Optional[str],
    interactive: bool,
    verbose: bool,
    output_format: str,
    use_llm: bool,
    llm_provider: str,
    llm_model: Optional[str],
    quality_level: str,
    strict_mode: bool,
):
    """Update an existing rule"""
    cli_ctx = ctx.obj
    cli_ctx.start_command_tracking("rules-update")

    try:
        if interactive:
            # Get existing rule first
            try:
                existing_response = await cli_ctx.api_client.request(
                    "GET", f"/api/match/rules/{domain}/{rule_id}"
                )
                existing_rule = existing_response.get("data", {})
            except Exception:
                existing_rule = {}

            click.echo(f"\n=== Updating Rule: {rule_id} ===")
            click.echo("Press Enter to keep existing value, or type new value")

            capability = click.prompt(
                "Capability",
                default=existing_rule.get("capability", ""),
                show_default=True,
            )

            click.echo("\nEnter requirements (one per line, empty line to finish):")
            if existing_rule.get("satisfies_requirements"):
                click.echo(
                    f"Current: {', '.join(existing_rule.get('satisfies_requirements', []))}"
                )
            requirements = []
            while True:
                req = click.prompt("Requirement", default="", show_default=False)
                if not req.strip():
                    break
                requirements.append(req.strip())

            if not requirements:
                requirements = existing_rule.get("satisfies_requirements", [])

            confidence = click.prompt(
                "Confidence (0.0-1.0)",
                type=float,
                default=existing_rule.get("confidence", 0.9),
                show_default=True,
            )

            description = click.prompt(
                "Description",
                default=existing_rule.get("description", ""),
                show_default=True,
            )

            tags_input = click.prompt(
                "Tags (comma-separated)",
                default=", ".join(existing_rule.get("tags", [])),
                show_default=True,
            )
            tags = (
                [t.strip() for t in tags_input.split(",") if t.strip()]
                if tags_input
                else []
            )

            rule_data = {
                "id": rule_id,
                "type": existing_rule.get("type", "capability_match"),
                "capability": capability,
                "satisfies_requirements": requirements,
                "confidence": confidence,
                "domain": domain,
                "description": description,
                "tags": tags,
                "direction": existing_rule.get("direction", "bidirectional"),
            }
        elif file:
            file_data = _read_rule_file(file)
            if "rules" in file_data:
                rules_dict = file_data["rules"]
                if rule_id in rules_dict:
                    rule_data = rules_dict[rule_id]
                else:
                    raise click.ClickException(f"Rule '{rule_id}' not found in file")
            elif "id" in file_data:
                rule_data = file_data
                rule_data["id"] = rule_id
                rule_data["domain"] = domain
            else:
                raise click.ClickException("Invalid rule file format")
        else:
            raise click.ClickException(
                "Either --file or --interactive must be specified"
            )

        response = await cli_ctx.api_client.request(
            "PUT",
            f"/api/match/rules/{domain}/{rule_id}",
            json_data={"rule_data": rule_data},
        )

        if output_format == "json":
            click.echo(json.dumps(response.get("data", {}), indent=2))
        else:
            cli_ctx.log("Rule updated successfully", "success")
            rule = response.get("data", {})
            click.echo(f"Updated rule: {rule.get('id')} in domain {rule.get('domain')}")

        cli_ctx.end_command_tracking()
    except Exception as e:
        cli_ctx.end_command_tracking()
        raise


@rules.command("delete")
@click.argument("domain", type=str)
@click.argument("rule_id", type=str)
@click.option("--confirm", is_flag=True, help="Skip confirmation prompt")
@standard_cli_command(
    help_text="Delete a rule.",
    async_cmd=True,
    track_performance=True,
    handle_errors=True,
    format_output=True,
)
@click.pass_context
async def rules_delete(
    ctx,
    domain: str,
    rule_id: str,
    confirm: bool,
    verbose: bool,
    output_format: str,
    use_llm: bool,
    llm_provider: str,
    llm_model: Optional[str],
    quality_level: str,
    strict_mode: bool,
):
    """Delete a rule"""
    cli_ctx = ctx.obj
    cli_ctx.start_command_tracking("rules-delete")

    try:
        if not confirm:
            if not click.confirm(
                f"Are you sure you want to delete rule '{rule_id}' from domain '{domain}'?"
            ):
                click.echo("Cancelled")
                return

        response = await cli_ctx.api_client.request(
            "DELETE", f"/api/match/rules/{domain}/{rule_id}?confirm=true"
        )

        if output_format == "json":
            click.echo(json.dumps(response, indent=2))
        else:
            cli_ctx.log("Rule deleted successfully", "success")
            click.echo(f"Deleted rule: {rule_id} from domain {domain}")

        cli_ctx.end_command_tracking()
    except Exception as e:
        cli_ctx.end_command_tracking()
        raise


@rules.command("import")
@click.argument("file", type=click.Path(exists=False), required=False)
@click.option("--domain", help="Target domain (if importing/reloading single domain)")
@click.option(
    "--partial-update/--no-partial-update",
    default=True,
    help="Allow partial updates (only for file import)",
)
@click.option(
    "--dry-run",
    is_flag=True,
    help="Validate without applying changes (only for file import)",
)
@standard_cli_command(
    help_text="Import rules from YAML or JSON file, or reload from filesystem if no file provided.",
    async_cmd=True,
    track_performance=True,
    handle_errors=True,
    format_output=True,
)
@click.pass_context
async def rules_import(
    ctx,
    file: Optional[str],
    domain: Optional[str],
    partial_update: bool,
    dry_run: bool,
    verbose: bool,
    output_format: str,
    use_llm: bool,
    llm_provider: str,
    llm_model: Optional[str],
    quality_level: str,
    strict_mode: bool,
):
    """
    Import rules from file or reload from filesystem.

    If FILE is provided, imports rules from that file.
    If FILE is omitted, reloads rules from the filesystem (useful when
    files have been modified while the server is running).
    """
    cli_ctx = ctx.obj
    cli_ctx.start_command_tracking("rules-import")

    try:
        # If no file provided, reload from filesystem
        if not file:
            request_data = {}
            if domain:
                request_data["domain"] = domain

            response = await cli_ctx.api_client.request(
                "POST", "/api/match/rules/import", json_data=request_data
            )

            data = response.get("data", {})

            if output_format == "json":
                click.echo(json.dumps(data, indent=2))
            else:
                cli_ctx.log("Rules reloaded successfully from filesystem", "success")
                click.echo(f"\nReload Results:")
                click.echo(
                    f"  Reloaded domains: {', '.join(data.get('reloaded_domains', []))}"
                )
                click.echo(f"  Total rules: {data.get('total_rules', 0)}")
                if data.get("previous_total_rules") is not None:
                    click.echo(
                        f"  Previous total: {data.get('previous_total_rules', 0)}"
                    )

            cli_ctx.end_command_tracking()
            return

        # Otherwise, import from file
        file_path = Path(file)
        if not file_path.exists():
            raise click.ClickException(f"File not found: {file}")

        file_content = file_path.read_text()

        # Determine format from extension
        if file_path.suffix.lower() in [".yaml", ".yml"]:
            file_format = "yaml"
        elif file_path.suffix.lower() == ".json":
            file_format = "json"
        else:
            raise click.ClickException(f"Unsupported file format: {file_path.suffix}")

        request_data = {
            "file_content": file_content,
            "file_format": file_format,
            "partial_update": partial_update,
            "dry_run": dry_run,
        }
        if domain:
            request_data["domain"] = domain

        response = await cli_ctx.api_client.request(
            "POST", "/api/match/rules/import", json_data=request_data
        )

        data = response.get("data", {})

        if output_format == "json":
            click.echo(json.dumps(data, indent=2))
        else:
            if dry_run:
                cli_ctx.log("Dry-run completed (no changes applied)", "info")
            else:
                cli_ctx.log("Rules imported successfully", "success")
            click.echo(f"\nImport Results:")
            click.echo(f"  Imported: {data.get('imported_rules', 0)}")
            click.echo(f"  Updated: {data.get('updated_rules', 0)}")
            if data.get("errors"):
                click.echo(f"  Errors: {len(data.get('errors', []))}")
                for error in data.get("errors", []):
                    click.echo(f"    - {error}")
            if dry_run and data.get("changes"):
                click.echo(f"\nChanges (dry-run):")
                changes = data.get("changes", {})
                if isinstance(changes, dict) and "summary" in changes:
                    summary = changes["summary"]
                    click.echo(f"  Would add: {summary.get('total_added', 0)}")
                    click.echo(f"  Would update: {summary.get('total_updated', 0)}")
                    click.echo(f"  Would delete: {summary.get('total_deleted', 0)}")

        cli_ctx.end_command_tracking()
    except Exception as e:
        cli_ctx.end_command_tracking()
        raise


@rules.command("export")
@click.argument("output_file", type=click.Path())
@click.option("--domain", help="Export specific domain (all if not specified)")
@click.option(
    "--format",
    type=click.Choice(["yaml", "json"]),
    default="yaml",
    help="Export format",
)
@click.option("--include-metadata", is_flag=True, help="Include metadata")
@standard_cli_command(
    help_text="Export rules to YAML or JSON file.",
    async_cmd=True,
    track_performance=True,
    handle_errors=True,
    format_output=True,
)
@click.pass_context
async def rules_export(
    ctx,
    output_file: str,
    domain: Optional[str],
    format: str,
    include_metadata: bool,
    verbose: bool,
    output_format: str,
    use_llm: bool,
    llm_provider: str,
    llm_model: Optional[str],
    quality_level: str,
    strict_mode: bool,
):
    """Export rules to file"""
    cli_ctx = ctx.obj
    cli_ctx.start_command_tracking("rules-export")

    try:
        # Build query parameters for GET request
        params = {
            "format": format,
            "include_metadata": "true" if include_metadata else "false",
        }
        if domain:
            params["domain"] = domain

        # Build query string
        query_string = "&".join([f"{k}={v}" for k, v in params.items()])
        endpoint = f"/api/match/rules/export?{query_string}"

        response = await cli_ctx.api_client.request("POST", endpoint)

        data = response.get("data", {})
        content = data.get("content", "")

        output_path = Path(output_file)
        output_path.write_text(content)

        if output_format == "json":
            click.echo(
                json.dumps(
                    {
                        "file": str(output_path),
                        "format": format,
                        "domain": domain or "all",
                        "rule_count": data.get("rule_count", 0),
                    },
                    indent=2,
                )
            )
        else:
            cli_ctx.log(f"Rules exported to {output_file}", "success")
            click.echo(f"Exported {data.get('rule_count', 0)} rules to {output_file}")

        cli_ctx.end_command_tracking()
    except Exception as e:
        cli_ctx.end_command_tracking()
        raise


@rules.command("validate")
@click.argument("file", type=click.Path(exists=True))
@standard_cli_command(
    help_text="Validate rule file without importing.",
    async_cmd=True,
    track_performance=True,
    handle_errors=True,
    format_output=True,
)
@click.pass_context
async def rules_validate(
    ctx,
    file: str,
    verbose: bool,
    output_format: str,
    use_llm: bool,
    llm_provider: str,
    llm_model: Optional[str],
    quality_level: str,
    strict_mode: bool,
):
    """Validate rule file"""
    cli_ctx = ctx.obj
    cli_ctx.start_command_tracking("rules-validate")

    try:
        file_path = Path(file)
        file_content = file_path.read_text()

        # Determine format from extension
        if file_path.suffix.lower() in [".yaml", ".yml"]:
            file_format = "yaml"
        elif file_path.suffix.lower() == ".json":
            file_format = "json"
        else:
            raise click.ClickException(f"Unsupported file format: {file_path.suffix}")

        response = await cli_ctx.api_client.request(
            "POST",
            "/api/match/rules/validate",
            json_data={"file_content": file_content, "file_format": file_format},
        )

        data = response.get("data", {})
        if output_format == "json":
            click.echo(json.dumps(data, indent=2))
        else:
            if data.get("valid"):
                cli_ctx.log("Validation passed", "success")
            else:
                cli_ctx.log("Validation failed", "error")
            for error in data.get("errors", []):
                click.echo(f"  Error: {error}")
            for warning in data.get("warnings", []):
                click.echo(f"  Warning: {warning}")

        cli_ctx.end_command_tracking()
    except Exception as e:
        cli_ctx.end_command_tracking()
        raise


@rules.command("compare")
@click.argument("file", type=click.Path(exists=True))
@click.option("--domain", help="Compare specific domain")
@standard_cli_command(
    help_text="Compare rules file with current rules (dry-run).",
    async_cmd=True,
    track_performance=True,
    handle_errors=True,
    format_output=True,
)
@click.pass_context
async def rules_compare(
    ctx,
    file: str,
    domain: Optional[str],
    verbose: bool,
    output_format: str,
    use_llm: bool,
    llm_provider: str,
    llm_model: Optional[str],
    quality_level: str,
    strict_mode: bool,
):
    """Compare rules file with current rules"""
    cli_ctx = ctx.obj
    cli_ctx.start_command_tracking("rules-compare")

    try:
        file_path = Path(file)
        file_content = file_path.read_text()

        # Determine format from extension
        if file_path.suffix.lower() in [".yaml", ".yml"]:
            file_format = "yaml"
        elif file_path.suffix.lower() == ".json":
            file_format = "json"
        else:
            raise click.ClickException(f"Unsupported file format: {file_path.suffix}")

        request_data = {"file_content": file_content, "file_format": file_format}
        if domain:
            request_data["domain"] = domain

        response = await cli_ctx.api_client.request(
            "POST", "/api/match/rules/compare", json_data=request_data
        )

        data = response.get("data", {})
        if output_format == "json":
            click.echo(json.dumps(data, indent=2))
        else:
            changes = data.get("changes", {})
            summary = data.get("summary", {})

            click.echo("\nComparison Results:")
            click.echo(f"  Would add: {summary.get('total_added', 0)}")
            click.echo(f"  Would update: {summary.get('total_updated', 0)}")
            click.echo(f"  Would delete: {summary.get('total_deleted', 0)}")

            if verbose and changes:
                if changes.get("added"):
                    click.echo(
                        f"\n  Added rules: {', '.join(changes.get('added', []))}"
                    )
                if changes.get("updated"):
                    click.echo(
                        f"  Updated rules: {', '.join(changes.get('updated', []))}"
                    )
                if changes.get("deleted"):
                    click.echo(
                        f"  Deleted rules: {', '.join(changes.get('deleted', []))}"
                    )

        cli_ctx.end_command_tracking()
    except Exception as e:
        cli_ctx.end_command_tracking()
        raise


@rules.command("reset")
@click.option("--confirm", is_flag=True, help="Skip confirmation prompt")
@standard_cli_command(
    help_text="Reset all rules (clear all rule sets).",
    async_cmd=True,
    track_performance=True,
    handle_errors=True,
    format_output=True,
)
@click.pass_context
async def rules_reset(
    ctx,
    confirm: bool,
    verbose: bool,
    output_format: str,
    use_llm: bool,
    llm_provider: str,
    llm_model: Optional[str],
    quality_level: str,
    strict_mode: bool,
):
    """Reset all rules"""
    cli_ctx = ctx.obj
    cli_ctx.start_command_tracking("rules-reset")

    try:
        if not confirm:
            if not click.confirm(
                "Are you sure you want to reset ALL rules? This cannot be undone."
            ):
                click.echo("Cancelled")
                return

        # API expects confirm as query parameter, not in body
        endpoint = "/api/match/rules/reset"
        if confirm:
            endpoint += "?confirm=true"

        response = await cli_ctx.api_client.request("POST", endpoint)

        cli_ctx.log("All rules have been reset", "success")
        if output_format == "json":
            click.echo(json.dumps(response, indent=2))
        else:
            click.echo("All rules have been cleared")

        cli_ctx.end_command_tracking()
    except Exception as e:
        cli_ctx.end_command_tracking()
        raise
