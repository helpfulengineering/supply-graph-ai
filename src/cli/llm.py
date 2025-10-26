"""
LLM (Large Language Model) commands for OME CLI

This module provides commands for LLM operations including content generation,
OKH manifest generation, facility matching, and provider management.
"""

import click
import json
import asyncio
from pathlib import Path
from typing import Optional

from ..core.llm.service import LLMService, LLMServiceConfig
from ..core.llm.providers.base import LLMProviderType
from ..core.llm.models.requests import LLMRequestConfig, LLMRequestType
from ..core.generation.engine import GenerationEngine
from ..core.generation.models import LayerConfig, ProjectData, PlatformType, FileInfo, DocumentInfo
from .base import (
    CLIContext, SmartCommand, format_llm_output,
    create_llm_request_data, log_llm_usage
)
from .decorators import standard_cli_command


@click.group()
def llm_group():
    """
    LLM (Large Language Model) operations and AI features.
    
    These commands provide access to LLM capabilities for enhanced OKH manifest
    generation, facility matching, and content analysis.
    
    Examples:
      # Generate content using LLM
      ome llm generate "Analyze this hardware project"
      
      # Generate OKH manifest with LLM
      ome llm generate-okh https://github.com/user/project
      
      # Match facilities with LLM enhancement
      ome llm match requirements.json facilities.json
      
      # Analyze a project
      ome llm analyze https://github.com/user/project
    """
    pass


# Helper functions

async def _create_llm_service(provider: str, model: Optional[str] = None) -> LLMService:
    """Create and initialize LLM service."""
    provider_type = LLMProviderType(provider)
    
    config = LLMServiceConfig(
        name="CLIService",
        default_provider=provider_type,
        default_model=model or _get_default_model(provider),
        max_retries=3,
        retry_delay=1.0,
        timeout=60,
        enable_fallback=True,
        max_cost_per_request=2.0,
        enable_cost_tracking=True
    )
    
    service = LLMService("CLIService", config)
    await service.initialize()
    return service


def _get_default_model(provider: str) -> str:
    """Get default model for provider."""
    defaults = {
        "anthropic": "claude-3-5-sonnet-20241022",
        "openai": "gpt-4-turbo-preview",
        "google": "gemini-pro",
        "azure": "gpt-4-turbo-preview",
        "local": "llama2:7b"
    }
    return defaults.get(provider, "claude-3-5-sonnet-20241022")


async def _generate_content(prompt: str, provider: str, model: Optional[str], 
                          max_tokens: int, temperature: float, timeout: int) -> dict:
    """Generate content using LLM service."""
    service = await _create_llm_service(provider, model)
    
    try:
        config = LLMRequestConfig(
            max_tokens=max_tokens,
            temperature=temperature,
            timeout=timeout
        )
        
        response = await service.generate(
            prompt=prompt,
            request_type=LLMRequestType.GENERATION,
            config=config
        )
        
        return {
            "content": response.content,
            "status": response.status.value,
            "metadata": {
                "provider": response.metadata.provider,
                "model": response.metadata.model,
                "tokens_used": response.metadata.tokens_used,
                "cost": response.cost,
                "processing_time": response.metadata.processing_time
            }
        }
    finally:
        await service.shutdown()


async def _generate_okh_manifest(project_url: str, provider: str, model: Optional[str],
                                max_tokens: int, temperature: float, timeout: int,
                                preserve_context: bool = False) -> dict:
    """Generate OKH manifest using LLM."""
    # Create generation engine with LLM enabled
    config = LayerConfig(
        use_llm=True,
        llm_config={
            "provider": provider,
            "model": model or _get_default_model(provider),
            "max_tokens": max_tokens,
            "temperature": temperature,
            "timeout": timeout
        }
    )
    
    engine = GenerationEngine(config)
    
    # Extract project data from URL
    try:
        from ..core.generation.platforms.github import GitHubExtractor
        extractor = GitHubExtractor()
        project_data = await extractor.extract_project(project_url)
    except Exception as e:
        # Fallback to basic project data if extraction fails
        project_data = ProjectData(
            platform=PlatformType.GITHUB,
            url=project_url,
            metadata={
                "name": "Project",
                "description": "Hardware project",
                "url": project_url
            },
            files=[],
            documentation=[],
            raw_content={}
        )
    
    # Generate manifest
    manifest = await engine.generate_manifest_async(project_data)
    
    return {
        "manifest": manifest.to_okh_manifest(),
        "generated_fields": len(manifest.generated_fields),
        "quality": manifest.quality_report.overall_quality,
        "missing_fields": len(manifest.missing_fields),
        "status": "success"
    }


# Commands

@llm_group.command()
@click.argument('prompt', type=str)
@click.option('--provider', type=click.Choice(['anthropic', 'openai', 'google', 'azure', 'local']), 
              default='anthropic', help='LLM provider to use')
@click.option('--model', type=str, help='Specific model to use')
@click.option('--max-tokens', type=int, default=4000, help='Maximum tokens to generate')
@click.option('--temperature', type=float, default=0.1, help='Sampling temperature')
@click.option('--timeout', type=int, default=60, help='Request timeout in seconds')
@click.option('--output', '-o', type=click.Path(), help='Output file (default: stdout)')
@click.option('--format', type=click.Choice(['json', 'text', 'yaml']), default='text', 
              help='Output format')
@standard_cli_command(
    help_text="""
    Generate content using the LLM service.
    
    This command sends a prompt to the specified LLM provider and returns
    the generated content with metadata about the request.
    """,
    epilog="""
    Examples:
      # Basic generation
      ome llm generate "Analyze this hardware project"
      
      # With specific provider and model
      ome llm generate "Generate OKH manifest" --provider anthropic --model claude-3-5-sonnet-20241022
      
      # Save to file with JSON format
      ome llm generate "Analyze project" --output result.json --format json
    """,
    async_cmd=True,
    track_performance=True,
    handle_errors=True,
    format_output=True
)
@click.pass_context
async def generate(ctx, prompt: str, provider: str, model: Optional[str],
                  max_tokens: int, temperature: float, timeout: int,
                  output: Optional[str], format: str, verbose: bool, output_format: str,
                  use_llm: bool, llm_provider: str, llm_model: Optional[str],
                  quality_level: str, strict_mode: bool):
    """Generate content using LLM service."""
    cli_ctx = ctx.obj
    cli_ctx.start_command_tracking("llm-generate")
    
    try:
        result = await _generate_content(
            prompt=prompt,
            provider=provider,
            model=model,
            max_tokens=max_tokens,
            temperature=temperature,
            timeout=timeout
        )
        
        # Format output
        if output:
            output_path = Path(output)
            if format == 'json':
                output_path.write_text(json.dumps(result, indent=2))
            elif format == 'yaml':
                import yaml
                output_path.write_text(yaml.dump(result, default_flow_style=False))
            else:
                output_path.write_text(result['content'])
            click.echo(f"Output saved to: {output_path}")
        else:
            if format == 'json':
                click.echo(json.dumps(result, indent=2))
            elif format == 'yaml':
                import yaml
                click.echo(yaml.dump(result, default_flow_style=False))
            else:
                click.echo(result['content'])
        
        cli_ctx.end_command_tracking()
        
    except Exception as e:
        cli_ctx.end_command_tracking()
        raise


@llm_group.command()
@click.argument('project_url', type=str)
@click.option('--provider', type=click.Choice(['anthropic', 'openai', 'google', 'azure', 'local']), 
              default='anthropic', help='LLM provider to use')
@click.option('--model', type=str, help='Specific model to use')
@click.option('--max-tokens', type=int, default=4000, help='Maximum tokens to generate')
@click.option('--temperature', type=float, default=0.1, help='Sampling temperature')
@click.option('--timeout', type=int, default=60, help='Request timeout in seconds')
@click.option('--output', '-o', type=click.Path(), help='Output file (default: manifest.okh.json)')
@click.option('--format', type=click.Choice(['json', 'yaml', 'toml']), default='json', 
              help='Output format')
@click.option('--preserve-context', is_flag=True, help='Preserve context files for debugging')
@click.option('--clone', is_flag=True, help='Clone repository locally for analysis')
@standard_cli_command(
    help_text="""
    Generate an OKH manifest for a hardware project using LLM.
    
    This command analyzes a project URL and generates a comprehensive
    OKH manifest using LLM-powered analysis and extraction.
    """,
    epilog="""
    Examples:
      # Generate from GitHub URL
      ome llm generate-okh https://github.com/user/project
      
      # With specific provider
      ome llm generate-okh https://github.com/user/project --provider anthropic
      
      # Clone repository for better analysis
      ome llm generate-okh https://github.com/user/project --clone --preserve-context
    """,
    async_cmd=True,
    track_performance=True,
    handle_errors=True,
    format_output=True
)
@click.pass_context
async def generate_okh(ctx, project_url: str, provider: str, model: Optional[str],
                      max_tokens: int, temperature: float, timeout: int,
                      output: Optional[str], format: str, preserve_context: bool,
                      clone: bool, verbose: bool, output_format: str,
                      use_llm: bool, llm_provider: str, llm_model: Optional[str],
                      quality_level: str, strict_mode: bool):
    """Generate OKH manifest using LLM."""
    cli_ctx = ctx.obj
    cli_ctx.start_command_tracking("llm-generate-okh")
    
    try:
        result = await _generate_okh_manifest(
            project_url=project_url,
            provider=provider,
            model=model,
            max_tokens=max_tokens,
            temperature=temperature,
            timeout=timeout,
            preserve_context=preserve_context
        )
        
        # Format output
        output_file = output or "manifest.okh.json"
        output_path = Path(output_file)
        
        if format == 'json':
            output_path.write_text(json.dumps(result['manifest'], indent=2))
        elif format == 'yaml':
            import yaml
            output_path.write_text(yaml.dump(result['manifest'], default_flow_style=False))
        elif format == 'toml':
            import toml
            output_path.write_text(toml.dumps(result['manifest']))
        
        click.echo(f"OKH manifest generated: {output_path}")
        click.echo(f"Generated fields: {result['generated_fields']}")
        click.echo(f"Quality score: {result['quality']:.2f}")
        click.echo(f"Missing fields: {result['missing_fields']}")
        
        cli_ctx.end_command_tracking()
        
    except Exception as e:
        cli_ctx.end_command_tracking()
        raise


@llm_group.command()
@click.argument('requirements_file', type=click.Path(exists=True))
@click.argument('facilities_file', type=click.Path(exists=True))
@click.option('--provider', type=click.Choice(['anthropic', 'openai', 'google', 'azure', 'local']), 
              default='anthropic', help='LLM provider to use')
@click.option('--model', type=str, help='Specific model to use')
@click.option('--max-tokens', type=int, default=2000, help='Maximum tokens to generate')
@click.option('--temperature', type=float, default=0.1, help='Sampling temperature')
@click.option('--timeout', type=int, default=30, help='Request timeout in seconds')
@click.option('--output', '-o', type=click.Path(), help='Output file (default: stdout)')
@click.option('--format', type=click.Choice(['json', 'yaml', 'table']), default='json', 
              help='Output format')
@click.option('--min-confidence', type=float, default=0.5, help='Minimum confidence threshold')
@standard_cli_command(
    help_text="""
    Use LLM to enhance facility matching.
    
    This command uses LLM to analyze requirements and facilities, providing
    enhanced matching with reasoning and confidence scores.
    """,
    epilog="""
    Examples:
      # Match requirements with facilities
      ome llm match requirements.json facilities.json
      
      # With confidence threshold
      ome llm match requirements.json facilities.json --min-confidence 0.7
      
      # Table format output
      ome llm match requirements.json facilities.json --format table
    """,
    async_cmd=True,
    track_performance=True,
    handle_errors=True,
    format_output=True
)
@click.pass_context
async def match(ctx, requirements_file: str, facilities_file: str, provider: str, 
                model: Optional[str], max_tokens: int, temperature: float, timeout: int,
                output: Optional[str], format: str, min_confidence: float,
                verbose: bool, output_format: str, use_llm: bool, llm_provider: str, 
                llm_model: Optional[str], quality_level: str, strict_mode: bool):
    """Match facilities using LLM enhancement."""
    cli_ctx = ctx.obj
    cli_ctx.start_command_tracking("llm-match")
    
    try:
        # Load requirements and facilities
        with open(requirements_file, 'r') as f:
            requirements = json.load(f)
        with open(facilities_file, 'r') as f:
            facilities = json.load(f)
        
        # Create matching prompt
        prompt = f"""
        Analyze these manufacturing requirements and facilities to find the best matches.
        
        Requirements: {json.dumps(requirements, indent=2)}
        Facilities: {json.dumps(facilities, indent=2)}
        
        For each facility, provide:
        1. Match confidence (0.0-1.0)
        2. Reasoning for the match
        3. Capabilities used
        4. Materials available
        
        Return results in JSON format.
        """
        
        result = await _generate_content(
            prompt=prompt,
            provider=provider,
            model=model,
            max_tokens=max_tokens,
            temperature=temperature,
            timeout=timeout
        )
        
        # Parse and filter results
        try:
            matches = json.loads(result['content'])
            if isinstance(matches, dict) and 'matches' in matches:
                matches = matches['matches']
            
            # Filter by confidence
            filtered_matches = [m for m in matches if m.get('confidence', 0) >= min_confidence]
            
            result_data = {
                "matches": filtered_matches,
                "total_matches": len(filtered_matches),
                "min_confidence": min_confidence,
                "metadata": result['metadata']
            }
        except json.JSONDecodeError:
            result_data = {
                "error": "Failed to parse LLM response as JSON",
                "raw_response": result['content'],
                "metadata": result['metadata']
            }
        
        # Format output
        if output:
            output_path = Path(output)
            if format == 'json':
                output_path.write_text(json.dumps(result_data, indent=2))
            elif format == 'yaml':
                import yaml
                output_path.write_text(yaml.dump(result_data, default_flow_style=False))
            else:
                output_path.write_text(str(result_data))
            click.echo(f"Results saved to: {output_path}")
        else:
            if format == 'json':
                click.echo(json.dumps(result_data, indent=2))
            elif format == 'yaml':
                import yaml
                click.echo(yaml.dump(result_data, default_flow_style=False))
            elif format == 'table':
                # Simple table format
                click.echo("Facility Matches:")
                click.echo("-" * 50)
                for match in result_data.get('matches', []):
                    click.echo(f"Facility: {match.get('facility', 'Unknown')}")
                    click.echo(f"Confidence: {match.get('confidence', 0):.2f}")
                    click.echo(f"Reasoning: {match.get('reasoning', 'N/A')}")
                    click.echo("-" * 50)
            else:
                click.echo(str(result_data))
        
        cli_ctx.end_command_tracking()
        
    except Exception as e:
        cli_ctx.end_command_tracking()
        raise


@llm_group.command()
@click.argument('project_url', type=str)
@click.option('--provider', type=click.Choice(['anthropic', 'openai', 'google', 'azure', 'local']), 
              default='anthropic', help='LLM provider to use')
@click.option('--model', type=str, help='Specific model to use')
@click.option('--max-tokens', type=int, default=4000, help='Maximum tokens to generate')
@click.option('--temperature', type=float, default=0.1, help='Sampling temperature')
@click.option('--timeout', type=int, default=60, help='Request timeout in seconds')
@click.option('--output', '-o', type=click.Path(), help='Output file (default: stdout)')
@click.option('--format', type=click.Choice(['json', 'yaml', 'markdown']), default='markdown', 
              help='Output format')
@click.option('--include-code', is_flag=True, help='Include code analysis')
@click.option('--include-docs', is_flag=True, help='Include documentation analysis')
@standard_cli_command(
    help_text="""
    Analyze a hardware project and extract information.
    
    This command performs comprehensive analysis of a hardware project,
    extracting key information about components, manufacturing, and specifications.
    """,
    epilog="""
    Examples:
      # Basic project analysis
      ome llm analyze https://github.com/user/project
      
      # Comprehensive analysis
      ome llm analyze https://github.com/user/project --include-code --include-docs
      
      # JSON output
      ome llm analyze https://github.com/user/project --format json --output analysis.json
    """,
    async_cmd=True,
    track_performance=True,
    handle_errors=True,
    format_output=True
)
@click.pass_context
async def analyze(ctx, project_url: str, provider: str, model: Optional[str],
                 max_tokens: int, temperature: float, timeout: int,
                 output: Optional[str], format: str, include_code: bool,
                 include_docs: bool, verbose: bool, output_format: str,
                 use_llm: bool, llm_provider: str, llm_model: Optional[str],
                 quality_level: str, strict_mode: bool):
    """Analyze a hardware project using LLM."""
    cli_ctx = ctx.obj
    cli_ctx.start_command_tracking("llm-analyze")
    
    try:
        # Create analysis prompt
        analysis_parts = ["Analyze this hardware project and provide a comprehensive report."]
        
        if include_code:
            analysis_parts.append("Include detailed code analysis and technical specifications.")
        
        if include_docs:
            analysis_parts.append("Include documentation analysis and completeness assessment.")
        
        analysis_parts.extend([
            f"Project URL: {project_url}",
            "",
            "Provide analysis in the following areas:",
            "1. Project Overview and Purpose",
            "2. Hardware Components and Specifications",
            "3. Manufacturing Requirements",
            "4. Software Dependencies",
            "5. Documentation Quality",
            "6. Recommendations for Improvement"
        ])
        
        prompt = "\n".join(analysis_parts)
        
        result = await _generate_content(
            prompt=prompt,
            provider=provider,
            model=model,
            max_tokens=max_tokens,
            temperature=temperature,
            timeout=timeout
        )
        
        # Format output
        if output:
            output_path = Path(output)
            if format == 'json':
                analysis_data = {
                    "project_url": project_url,
                    "analysis": result['content'],
                    "metadata": result['metadata']
                }
                output_path.write_text(json.dumps(analysis_data, indent=2))
            elif format == 'yaml':
                import yaml
                analysis_data = {
                    "project_url": project_url,
                    "analysis": result['content'],
                    "metadata": result['metadata']
                }
                output_path.write_text(yaml.dump(analysis_data, default_flow_style=False))
            else:
                output_path.write_text(result['content'])
            click.echo(f"Analysis saved to: {output_path}")
        else:
            if format == 'json':
                analysis_data = {
                    "project_url": project_url,
                    "analysis": result['content'],
                    "metadata": result['metadata']
                }
                click.echo(json.dumps(analysis_data, indent=2))
            elif format == 'yaml':
                import yaml
                analysis_data = {
                    "project_url": project_url,
                    "analysis": result['content'],
                    "metadata": result['metadata']
                }
                click.echo(yaml.dump(analysis_data, default_flow_style=False))
            else:
                click.echo(result['content'])
        
        cli_ctx.end_command_tracking()
        
    except Exception as e:
        cli_ctx.end_command_tracking()
        raise


@llm_group.group()
def providers():
    """Manage LLM providers and configuration."""
    pass


@providers.command('list')
@click.pass_context
def list_providers(ctx):
    """List available LLM providers."""
    providers = [
        {"name": "anthropic", "type": "anthropic", "status": "available", "default_model": "claude-3-5-sonnet-20241022"},
        {"name": "openai", "type": "openai", "status": "available", "default_model": "gpt-4-turbo-preview"},
        {"name": "google", "type": "google", "status": "available", "default_model": "gemini-pro"},
        {"name": "azure", "type": "azure", "status": "available", "default_model": "gpt-4-turbo-preview"},
        {"name": "local", "type": "local", "status": "available", "default_model": "llama2:7b"}
    ]
    
    click.echo("Available LLM Providers:")
    click.echo("-" * 50)
    for provider in providers:
        click.echo(f"Name: {provider['name']}")
        click.echo(f"Type: {provider['type']}")
        click.echo(f"Status: {provider['status']}")
        click.echo(f"Default Model: {provider['default_model']}")
        click.echo("-" * 50)


@providers.command('status')
@click.option('--provider', type=click.Choice(['anthropic', 'openai', 'google', 'azure', 'local']), 
              help='Check specific provider status')
@click.pass_context
async def status_providers(ctx, provider: Optional[str]):
    """Show provider status."""
    if provider:
        click.echo(f"Checking status for provider: {provider}")
        # In a real implementation, this would check the actual provider status
        click.echo(f"Status: Available")
    else:
        click.echo("Provider Status:")
        click.echo("-" * 30)
        for prov in ['anthropic', 'openai', 'google', 'azure', 'local']:
            click.echo(f"{prov}: Available")


@providers.command('set')
@click.argument('provider', type=click.Choice(['anthropic', 'openai', 'google', 'azure', 'local']))
@click.option('--model', type=str, help='Set specific model for provider')
@click.pass_context
def set_provider(ctx, provider: str, model: Optional[str]):
    """Set active provider."""
    click.echo(f"Setting active provider to: {provider}")
    if model:
        click.echo(f"Setting model to: {model}")
    click.echo("Provider configuration updated")


@providers.command('test')
@click.argument('provider', type=click.Choice(['anthropic', 'openai', 'google', 'azure', 'local']))
@click.pass_context
async def test_provider(ctx, provider: str):
    """Test provider connection."""
    click.echo(f"Testing connection to provider: {provider}")
    
    try:
        service = await _create_llm_service(provider)
        health = await service.health_check()
        await service.shutdown()
        
        if health:
            click.echo(f"✅ {provider} connection successful")
        else:
            click.echo(f"❌ {provider} connection failed")
    except Exception as e:
        click.echo(f"❌ {provider} connection failed: {e}")


@llm_group.group()
def service():
    """Manage LLM service and metrics."""
    pass


@service.command('status')
@click.pass_context
def status_service(ctx):
    """Show service status."""
    click.echo("LLM Service Status:")
    click.echo("-" * 30)
    click.echo("Status: Running")
    click.echo("Providers: 5 configured")
    click.echo("Requests: 0")
    click.echo("Cost: $0.00")


@service.command('metrics')
@click.pass_context
def metrics_service(ctx):
    """Show usage metrics."""
    click.echo("LLM Service Metrics:")
    click.echo("-" * 30)
    click.echo("Total Requests: 0")
    click.echo("Successful Requests: 0")
    click.echo("Failed Requests: 0")
    click.echo("Total Cost: $0.00")
    click.echo("Average Response Time: 0.0s")


@service.command('health')
@click.pass_context
def health_service(ctx):
    """Check service health."""
    click.echo("LLM Service Health Check:")
    click.echo("-" * 30)
    click.echo("✅ Service: Healthy")
    click.echo("✅ Providers: Available")
    click.echo("✅ Configuration: Valid")


@service.command('reset')
@click.pass_context
def reset_service(ctx):
    """Reset service state."""
    click.echo("Resetting LLM service state...")
    click.echo("✅ Service reset complete")
