"""
Matching commands for OME CLI

This module provides commands for matching OKH requirements with OKW capabilities,
including direct matching, heuristic matching, and validation operations.
"""

import click
import asyncio
import json
from pathlib import Path
from typing import Optional, Dict, Any, List

from .base import (
    CLIContext, SmartCommand, with_async_context,
    echo_success, echo_error, echo_info, format_json_output
)


@click.group()
def match_group():
    """Matching operations commands"""
    pass


@match_group.command()
@click.argument('okh_file', type=click.Path(exists=True))
@click.option('--access-type', help='Filter by access type')
@click.option('--facility-status', help='Filter by facility status')
@click.option('--location', help='Filter by location')
@click.option('--capabilities', help='Comma-separated list of required capabilities')
@click.option('--materials', help='Comma-separated list of required materials')
@click.option('--output', '-o', help='Output file path')
@click.pass_context
def requirements(ctx, okh_file: str, access_type: Optional[str], 
                      facility_status: Optional[str], location: Optional[str],
                      capabilities: Optional[str], materials: Optional[str],
                      output: Optional[str]):
    """Match OKH requirements to OKW capabilities"""
    cli_ctx = ctx.obj
    
    # Read OKH file
    try:
        okh_path = Path(okh_file)
        with open(okh_path, 'r') as f:
            if okh_path.suffix.lower() == '.yaml' or okh_path.suffix.lower() == '.yml':
                import yaml
                okh_data = yaml.safe_load(f)
            else:
                okh_data = json.load(f)
    except Exception as e:
        echo_error(f"Failed to read OKH file: {str(e)}")
        return
    
    # Parse comma-separated lists
    capabilities_list = capabilities.split(',') if capabilities else None
    materials_list = materials.split(',') if materials else None
    
    async def http_match():
        """Match via HTTP API"""
        payload = {
            "okh_content": okh_data,
            "filters": {
                "access_type": access_type,
                "facility_status": facility_status,
                "location": location,
                "capabilities": capabilities_list,
                "materials": materials_list
            }
        }
        response = await cli_ctx.api_client.request("POST", "/match/requirements", json_data=payload)
        return response
    
    async def fallback_match():
        """Match using direct service calls"""
        from ..core.models.okh import OKHManifest
        from ..core.services.matching_service import MatchingService
        
        manifest = OKHManifest.from_dict(okh_data)
        matching_service = await MatchingService.get_instance()
        
        # Create match request
        from ..core.api.models.match.request import MatchRequest
        match_request = MatchRequest(
            okh_content=okh_data,
            filters={
                "access_type": access_type,
                "facility_status": facility_status,
                "location": location,
                "capabilities": capabilities_list,
                "materials": materials_list
            }
        )
        
        result = await matching_service.match_requirements_to_capabilities(match_request)
        return result.to_dict()
    
    command = SmartCommand(cli_ctx)
    result = asyncio.run(command.execute_with_fallback(http_match, fallback_match))
    
    matches = result.get("matches", [])
    total_matches = len(matches)
    
    if total_matches > 0:
        echo_success(f"Found {total_matches} matching facilities")
        
        if output:
            # Save result to output file
            with open(output, 'w') as f:
                json.dump(result, f, indent=2, default=str)
            echo_info(f"Match results saved to {output}")
        
        if cli_ctx.output_format == 'json':
            click.echo(format_json_output(result))
        else:
            # Show match summary
            for i, match in enumerate(matches, 1):
                facility = match.get("facility", {})
                confidence = match.get("confidence", 0)
                click.echo(f"{i}. {facility.get('name', 'Unknown Facility')}")
                click.echo(f"   Confidence: {confidence:.1%}")
                click.echo(f"   Type: {facility.get('facility_type', 'Unknown')}")
                click.echo(f"   Location: {facility.get('location', {}).get('address', 'Unknown')}")
                click.echo()
    else:
        echo_info("No matching facilities found")


@match_group.command()
@click.argument('match_result_file', type=click.Path(exists=True))
@click.option('--quality-level', default='professional',
              type=click.Choice(['hobby', 'professional', 'medical']),
              help='Quality level for validation')
@click.option('--strict-mode', is_flag=True,
              help='Enable strict validation mode')
@click.pass_context
def validate(ctx, match_result_file: str, quality_level: str, strict_mode: bool):
    """Validate a match result"""
    cli_ctx = ctx.obj
    
    # Read match result file
    try:
        with open(match_result_file, 'r') as f:
            match_data = json.load(f)
    except Exception as e:
        echo_error(f"Failed to read match result file: {str(e)}")
        return
    
    async def http_validate():
        """Validate via HTTP API"""
        payload = {
            "match_result": match_data,
            "validation_context": quality_level
        }
        params = {"strict_mode": strict_mode}
        response = await cli_ctx.api_client.request(
            "POST", "/match/validate", json_data=payload, params=params
        )
        return response
    
    async def fallback_validate():
        """Validate using direct service calls"""
        from ..core.services.matching_service import MatchingService
        
        matching_service = await MatchingService.get_instance()
        result = await matching_service.validate_match(match_data, quality_level, strict_mode)
        return result.to_dict()
    
    command = SmartCommand(cli_ctx)
    result = asyncio.run(command.execute_with_fallback(http_validate, fallback_validate))
    
    if cli_ctx.output_format == 'json':
        click.echo(format_json_output(result))
    else:
        validation = result.get("validation", result)
        is_valid = validation.get("is_valid", False)
        
        if is_valid:
            echo_success("Match result is valid")
        else:
            echo_error("Match result validation failed")
        
        # Show validation details
        if validation.get("errors"):
            click.echo("\nErrors:")
            for error in validation["errors"]:
                click.echo(f"  ❌ {error}")
        
        if validation.get("warnings"):
            click.echo("\nWarnings:")
            for warning in validation["warnings"]:
                click.echo(f"  ⚠️  {warning}")
        
        if validation.get("confidence_score"):
            score = validation["confidence_score"]
            click.echo(f"\nConfidence Score: {score:.1%}")


@match_group.command()
@click.argument('okh_file', type=click.Path(exists=True))
@click.option('--output', '-o', help='Output file path')
@click.pass_context
def from_file(ctx, okh_file: str, output: Optional[str]):
    """Match requirements from OKH file (file upload endpoint)"""
    cli_ctx = ctx.ctx
    
    # Read OKH file
    try:
        okh_path = Path(okh_file)
        with open(okh_path, 'rb') as f:
            file_content = f.read()
    except Exception as e:
        echo_error(f"Failed to read OKH file: {str(e)}")
        return
    
    async def http_match_from_file():
        """Match via HTTP file upload API"""
        files = {"okh_file": (okh_path.name, file_content, "application/json")}
        response = await cli_ctx.api_client.request(
            "POST", "/match/from-file", files=files
        )
        return response
    
    async def fallback_match_from_file():
        """Fallback to regular match endpoint"""
        # Read as JSON and use regular match
        with open(okh_path, 'r') as f:
            okh_data = json.load(f)
        
        payload = {"okh_content": okh_data}
        response = await cli_ctx.api_client.request("POST", "/match/requirements", json_data=payload)
        return response
    
    command = SmartCommand(cli_ctx)
    result = asyncio.run(command.execute_with_fallback(http_match_from_file, fallback_match_from_file))
    
    matches = result.get("matches", [])
    total_matches = len(matches)
    
    if total_matches > 0:
        echo_success(f"Found {total_matches} matching facilities")
        
        if output:
            # Save result to output file
            with open(output, 'w') as f:
                json.dump(result, f, indent=2, default=str)
            echo_info(f"Match results saved to {output}")
        
        if cli_ctx.output_format == 'json':
            click.echo(format_json_output(result))
        else:
            # Show match summary
            for i, match in enumerate(matches, 1):
                facility = match.get("facility", {})
                confidence = match.get("confidence", 0)
                click.echo(f"{i}. {facility.get('name', 'Unknown Facility')}")
                click.echo(f"   Confidence: {confidence:.1%}")
                click.echo(f"   Type: {facility.get('facility_type', 'Unknown')}")
                click.echo(f"   Location: {facility.get('location', {}).get('address', 'Unknown')}")
                click.echo()
    else:
        echo_info("No matching facilities found")


@match_group.command()
@click.option('--limit', default=10, help='Maximum number of matches to show')
@click.option('--min-confidence', default=0.0, help='Minimum confidence threshold')
@click.option('--output', '-o', help='Output file path')
@click.pass_context
def list_recent(ctx, limit: int, min_confidence: float, output: Optional[str]):
    """List recent match results"""
    cli_ctx = ctx.obj
    
    async def http_list_recent():
        """List recent matches via HTTP API"""
        params = {"limit": limit, "min_confidence": min_confidence}
        response = await cli_ctx.api_client.request("GET", "/match/recent", params=params)
        return response
    
    async def fallback_list_recent():
        """List recent matches using direct service calls"""
        from ..core.services.matching_service import MatchingService
        
        matching_service = await MatchingService.get_instance()
        matches = await matching_service.get_recent_matches(limit=limit, min_confidence=min_confidence)
        return {
            "matches": [match.to_dict() for match in matches],
            "total": len(matches)
        }
    
    command = SmartCommand(cli_ctx)
    result = asyncio.run(command.execute_with_fallback(http_list_recent, fallback_list_recent))
    
    matches = result.get("matches", [])
    total = result.get("total", len(matches))
    
    if matches:
        echo_success(f"Found {total} recent matches")
        
        if output:
            # Save result to output file
            with open(output, 'w') as f:
                json.dump(result, f, indent=2, default=str)
            echo_info(f"Recent matches saved to {output}")
        
        if cli_ctx.output_format == 'json':
            click.echo(format_json_output(result))
        else:
            for match in matches:
                facility = match.get("facility", {})
                confidence = match.get("confidence", 0)
                created_at = match.get("created_at", "Unknown")
                click.echo(f"📅 {created_at}")
                click.echo(f"   Facility: {facility.get('name', 'Unknown')}")
                click.echo(f"   Confidence: {confidence:.1%}")
                click.echo(f"   Type: {facility.get('facility_type', 'Unknown')}")
                click.echo()
    else:
        echo_info("No recent matches found")
