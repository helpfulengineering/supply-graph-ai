"""
Standardized CLI decorators for Open Matching Engine

This module provides decorators for consistent CLI command patterns,
including LLM integration, error handling, and output formatting.
"""

import click
import asyncio
import functools
from typing import Optional, Callable
from datetime import datetime

from .base import CLIContext, echo_error, echo_info


def cli_command(
    name: Optional[str] = None,
    help_text: Optional[str] = None,
    epilog: Optional[str] = None,
    short_help: Optional[str] = None,
    hidden: bool = False,
    deprecated: bool = False
):
    """
    Standardized CLI command decorator with common options and patterns.
    
    Args:
        name: Command name (defaults to function name)
        help_text: Detailed help text
        epilog: Additional help text at the end
        short_help: Short help text for command listing
        hidden: Whether to hide command from help
        deprecated: Whether command is deprecated
    """
    def decorator(func: Callable) -> Callable:
        # Add common options
        func = click.option(
            '--verbose', '-v', 
            is_flag=True, 
            help='Enable verbose output'
        )(func)
        
        func = click.option(
            '--json', 'output_format', 
            flag_value='json',
            help='Output in JSON format'
        )(func)
        
        func = click.option(
            '--table', 'output_format', 
            flag_value='table',
            help='Output in table format'
        )(func)
        
        # Add LLM options
        func = click.option(
            '--use-llm', 
            is_flag=True, 
            help='Enable LLM integration for enhanced processing'
        )(func)
        
        func = click.option(
            '--llm-provider', 
            type=click.Choice(['openai', 'anthropic', 'google', 'azure', 'local']),
            default='anthropic',
            help='LLM provider to use'
        )(func)
        
        func = click.option(
            '--llm-model', 
            help='Specific LLM model to use (provider-specific)'
        )(func)
        
        func = click.option(
            '--quality-level', 
            type=click.Choice(['hobby', 'professional', 'medical']),
            default='professional',
            help='Quality level for LLM processing'
        )(func)
        
        func = click.option(
            '--strict-mode', 
            is_flag=True, 
            help='Enable strict validation mode'
        )(func)
        
        # Set command metadata
        if name:
            func.__name__ = name
        if help_text:
            func.help = help_text
        if epilog:
            func.epilog = epilog
        if short_help:
            func.short_help = short_help
        if hidden:
            func.hidden = True
        if deprecated:
            func.deprecated = True
            
        return func
    return decorator


def async_command(func: Callable) -> Callable:
    """
    Decorator to handle async CLI commands with proper event loop management.
    """
    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        # Extract context if present
        ctx = None
        for arg in args:
            if hasattr(arg, 'obj') and isinstance(arg.obj, CLIContext):
                ctx = arg
                break
        
        # Run async function
        try:
            return asyncio.run(func(*args, **kwargs))
        except Exception as e:
            if ctx and hasattr(ctx, 'obj'):
                echo_error(f"Command failed: {str(e)}")
            else:
                click.echo(f"❌ Command failed: {str(e)}", err=True)
            raise click.Abort()
    
    return wrapper


def with_llm_config(func: Callable) -> Callable:
    """
    Decorator to add LLM configuration to command context.
    """
    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        # Extract context
        ctx = None
        for arg in args:
            if hasattr(arg, 'obj') and isinstance(arg.obj, CLIContext):
                ctx = arg
                break
        
        if ctx and hasattr(ctx, 'obj'):
            # Add LLM configuration to context
            cli_ctx = ctx.obj
            cli_ctx.llm_config = {
                'use_llm': kwargs.get('use_llm', False),
                'llm_provider': kwargs.get('llm_provider', 'anthropic'),
                'llm_model': kwargs.get('llm_model'),
                'quality_level': kwargs.get('quality_level', 'professional'),
                'strict_mode': kwargs.get('strict_mode', False)
            }
            
            # Log LLM configuration if verbose
            if cli_ctx.verbose and cli_ctx.llm_config['use_llm']:
                echo_info(f"LLM Configuration: {cli_ctx.llm_config}")
        
        return func(*args, **kwargs)
    
    return wrapper


def with_error_handling(func: Callable) -> Callable:
    """
    Decorator to add standardized error handling to CLI commands.
    """
    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        try:
            return func(*args, **kwargs)
        except click.ClickException:
            # Re-raise Click exceptions as-is
            raise
        except Exception as e:
            # Extract context for better error reporting
            ctx = None
            for arg in args:
                if hasattr(arg, 'obj') and isinstance(arg.obj, CLIContext):
                    ctx = arg
                    break
            
            if ctx and hasattr(ctx, 'obj'):
                cli_ctx = ctx.obj
                if cli_ctx.verbose:
                    echo_error(f"Detailed error: {str(e)}")
                    import traceback
                    echo_error(f"Traceback: {traceback.format_exc()}")
                else:
                    echo_error(f"Command failed: {str(e)}")
            else:
                echo_error(f"Command failed: {str(e)}")
            
            raise click.Abort()
    
    return wrapper


def with_performance_tracking(func: Callable) -> Callable:
    """
    Decorator to add performance tracking to CLI commands.
    """
    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        start_time = datetime.utcnow()
        
        try:
            result = func(*args, **kwargs)
            
            # Calculate execution time
            execution_time = (datetime.utcnow() - start_time).total_seconds()
            
            # Extract context for logging
            ctx = None
            for arg in args:
                if hasattr(arg, 'obj') and isinstance(arg.obj, CLIContext):
                    ctx = arg
                    break
            
            if ctx and hasattr(ctx, 'obj'):
                cli_ctx = ctx.obj
                if cli_ctx.verbose:
                    echo_info(f"Command completed in {execution_time:.2f} seconds")
            
            return result
            
        except Exception as e:
            # Calculate execution time even for errors
            execution_time = (datetime.utcnow() - start_time).total_seconds()
            
            # Extract context for logging
            ctx = None
            for arg in args:
                if hasattr(arg, 'obj') and isinstance(arg.obj, CLIContext):
                    ctx = arg
                    break
            
            if ctx and hasattr(ctx, 'obj'):
                cli_ctx = ctx.obj
                if cli_ctx.verbose:
                    echo_error(f"Command failed after {execution_time:.2f} seconds")
            
            raise
    
    return wrapper


def with_output_formatting(func: Callable) -> Callable:
    """
    Decorator to add standardized output formatting to CLI commands.
    """
    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        # Extract context
        ctx = None
        for arg in args:
            if hasattr(arg, 'obj') and isinstance(arg.obj, CLIContext):
                ctx = arg
                break
        
        if ctx and hasattr(ctx, 'obj'):
            cli_ctx = ctx.obj
            output_format = kwargs.get('output_format', 'text')
            cli_ctx.output_format = output_format
        
        return func(*args, **kwargs)
    
    return wrapper


def cli_group(
    name: Optional[str] = None,
    help_text: Optional[str] = None,
    epilog: Optional[str] = None,
    short_help: Optional[str] = None,
    hidden: bool = False,
    deprecated: bool = False
):
    """
    Standardized CLI group decorator with common options.
    
    Args:
        name: Group name (defaults to function name)
        help_text: Detailed help text
        epilog: Additional help text at the end
        short_help: Short help text for command listing
        hidden: Whether to hide group from help
        deprecated: Whether group is deprecated
    """
    def decorator(func: Callable) -> Callable:
        # Set group metadata
        if name:
            func.__name__ = name
        if help_text:
            func.help = help_text
        if epilog:
            func.epilog = epilog
        if short_help:
            func.short_help = short_help
        if hidden:
            func.hidden = True
        if deprecated:
            func.deprecated = True
            
        return func
    return decorator


def confirm_action(message: str, default: bool = False):
    """
    Decorator to add confirmation prompt to destructive commands.
    
    Args:
        message: Confirmation message
        default: Default response if user just presses Enter
    """
    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            # Extract context
            ctx = None
            for arg in args:
                if hasattr(arg, 'obj') and isinstance(arg.obj, CLIContext):
                    ctx = arg
                    break
            
            if ctx and hasattr(ctx, 'obj'):
                cli_ctx = ctx.obj
                if not cli_ctx.verbose:  # Skip confirmation in verbose mode
                    if not click.confirm(message, default=default):
                        echo_info("Operation cancelled by user")
                        return
            
            return func(*args, **kwargs)
        
        return wrapper
    return decorator


def require_server_connection(func: Callable) -> Callable:
    """
    Decorator to ensure server connection before executing command.
    """
    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        # Extract context
        ctx = None
        for arg in args:
            if hasattr(arg, 'obj') and isinstance(arg.obj, CLIContext):
                ctx = arg
                break
        
        if ctx and hasattr(ctx, 'obj'):
            cli_ctx = ctx.obj
            # This would typically test server connectivity
            # For now, we'll just log the attempt
            if cli_ctx.verbose:
                echo_info(f"Testing connection to {cli_ctx.config.server_url}")
        
        return func(*args, **kwargs)
    
    return wrapper


# Composite decorators for common patterns
def standard_cli_command(
    name: Optional[str] = None,
    help_text: Optional[str] = None,
    epilog: Optional[str] = None,
    short_help: Optional[str] = None,
    hidden: bool = False,
    deprecated: bool = False,
    async_cmd: bool = False,
    track_performance: bool = True,
    handle_errors: bool = True,
    format_output: bool = True,
    add_llm_config: bool = True
):
    """
    Composite decorator that applies all standard CLI patterns.
    
    This is the main decorator to use for most CLI commands.
    """
    def decorator(func: Callable) -> Callable:
        # Apply base command decorator
        func = cli_command(
            name=name,
            help_text=help_text,
            epilog=epilog,
            short_help=short_help,
            hidden=hidden,
            deprecated=deprecated
        )(func)
        
        # Apply additional decorators based on options
        if add_llm_config:
            func = with_llm_config(func)
        
        if format_output:
            func = with_output_formatting(func)
        
        if track_performance:
            func = with_performance_tracking(func)
        
        if handle_errors:
            func = with_error_handling(func)
        
        if async_cmd:
            func = async_command(func)
        
        return func
    
    return decorator


def standard_cli_group(
    name: Optional[str] = None,
    help_text: Optional[str] = None,
    epilog: Optional[str] = None,
    short_help: Optional[str] = None,
    hidden: bool = False,
    deprecated: bool = False
):
    """
    Composite decorator for CLI groups with standard patterns.
    """
    return cli_group(
        name=name,
        help_text=help_text,
        epilog=epilog,
        short_help=short_help,
        hidden=hidden,
        deprecated=deprecated
    )
