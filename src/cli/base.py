"""
Base CLI framework for Open Matching Engine

This module provides the foundation for all CLI commands, including:
- HTTP client management
- Service fallback handling
- Common utilities and error handling
- Configuration management
"""

import httpx
import click
import json
import logging
from typing import Optional, Dict, Any
from contextlib import asynccontextmanager
from datetime import datetime

from ..config import settings
from ..core.services.package_service import PackageService
from ..core.services.okh_service import OKHService
from ..core.services.okw_service import OKWService
from ..core.services.storage_service import StorageService
from ..core.services.matching_service import MatchingService

logger = logging.getLogger(__name__)


class CLIConfig:
    """CLI configuration management with LLM support"""
    
    def __init__(self):
        self.server_url = "http://localhost:8001"
        self.timeout = 120.0
        self.retry_attempts = 3
        self.verbose = False
        
        # LLM configuration
        self.llm_config = {
            'use_llm': False,
            'llm_provider': 'anthropic',
            'llm_model': None,
            'quality_level': 'professional',
            'strict_mode': False
        }
        
    @classmethod
    def from_settings(cls) -> 'CLIConfig':
        """Create config from application settings"""
        config = cls()
        # You can add settings-based configuration here
        return config
    
    def update_llm_config(self, **kwargs):
        """Update LLM configuration"""
        self.llm_config.update(kwargs)
    
    def get_llm_provider(self) -> str:
        """Get current LLM provider"""
        return self.llm_config.get('llm_provider', 'anthropic')
    
    def get_llm_model(self) -> Optional[str]:
        """Get current LLM model"""
        return self.llm_config.get('llm_model')
    
    def is_llm_enabled(self) -> bool:
        """Check if LLM is enabled"""
        return self.llm_config.get('use_llm', False)


class APIClient:
    """HTTP client for communicating with FastAPI server"""
    
    def __init__(self, config: CLIConfig):
        self.config = config
        self.base_url = f"{config.server_url}/v1"  # Use /v1 API prefix
        
    @asynccontextmanager
    async def get_client(self):
        """Get HTTP client with proper configuration"""
        async with httpx.AsyncClient(
            base_url=self.base_url,
            timeout=self.config.timeout,
            follow_redirects=True
        ) as client:
            yield client
    
    async def request(
        self, 
        method: str, 
        endpoint: str, 
        json_data: Optional[Dict[str, Any]] = None,
        params: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """Make HTTP request with error handling"""
        async with self.get_client() as client:
            try:
                response = await client.request(
                    method=method,
                    url=endpoint,
                    json=json_data,
                    params=params
                )
                response.raise_for_status()
                return response.json()
            except httpx.HTTPStatusError as e:
                error_detail = "Unknown error"
                try:
                    error_data = e.response.json()
                    error_detail = error_data.get("detail", str(e))
                except:
                    error_detail = e.response.text or str(e)
                
                raise click.ClickException(f"API Error ({e.response.status_code}): {error_detail}")
            except httpx.ConnectError:
                raise click.ClickException(f"Could not connect to server at {self.config.server_url}")
            except httpx.TimeoutException:
                raise click.ClickException(f"Request timed out after {self.config.timeout}s")
            except Exception as e:
                raise click.ClickException(f"Unexpected error: {str(e)}")


class ServiceFallback:
    """Fallback to direct service calls when server is unavailable"""
    
    def __init__(self):
        self._services = {}
    
    async def get_package_service(self) -> PackageService:
        """Get package service instance"""
        if "package_service" not in self._services:
            self._services["package_service"] = await PackageService.get_instance()
        return self._services["package_service"]
    
    async def get_okh_service(self) -> OKHService:
        """Get OKH service instance"""
        if "okh_service" not in self._services:
            self._services["okh_service"] = await OKHService.get_instance()
        return self._services["okh_service"]
    
    async def get_okw_service(self) -> OKWService:
        """Get OKW service instance"""
        if "okw_service" not in self._services:
            self._services["okw_service"] = await OKWService.get_instance()
        return self._services["okw_service"]
    
    async def get_storage_service(self) -> StorageService:
        """Get storage service instance"""
        if "storage_service" not in self._services:
            storage_service = await StorageService.get_instance()
            await storage_service.configure(settings.STORAGE_CONFIG)
            self._services["storage_service"] = storage_service
        return self._services["storage_service"]
    
    async def get_matching_service(self) -> MatchingService:
        """Get matching service instance"""
        if "matching_service" not in self._services:
            self._services["matching_service"] = await MatchingService.get_instance()
        return self._services["matching_service"]


class CLIContext:
    """Context object passed to all CLI commands with LLM support"""
    
    def __init__(self, config: CLIConfig):
        self.config = config
        self.api_client = APIClient(config)
        self.service_fallback = ServiceFallback()
        self.verbose = config.verbose
        self.output_format = 'text'
        
        # LLM configuration
        self.llm_config = config.llm_config.copy()
        
        # Performance tracking
        self.start_time = None
        self.command_name = None
    
    def log(self, message: str, level: str = "info"):
        """Log message with appropriate level"""
        if self.verbose or level in ["error", "warning"]:
            if level == "error":
                click.echo(f"❌ {message}", err=True)
            elif level == "warning":
                click.echo(f"⚠️  {message}", err=True)
            elif level == "success":
                click.echo(f"✅ {message}")
            else:
                click.echo(f"ℹ️  {message}")
    
    def update_llm_config(self, **kwargs):
        """Update LLM configuration"""
        self.llm_config.update(kwargs)
        self.config.update_llm_config(**kwargs)
    
    def is_llm_enabled(self) -> bool:
        """Check if LLM is enabled"""
        return self.llm_config.get('use_llm', False)
    
    def get_llm_provider(self) -> str:
        """Get current LLM provider"""
        return self.llm_config.get('llm_provider', 'anthropic')
    
    def get_llm_model(self) -> Optional[str]:
        """Get current LLM model"""
        return self.llm_config.get('llm_model')
    
    def get_quality_level(self) -> str:
        """Get current quality level"""
        return self.llm_config.get('quality_level', 'professional')
    
    def is_strict_mode(self) -> bool:
        """Check if strict mode is enabled"""
        return self.llm_config.get('strict_mode', False)
    
    def start_command_tracking(self, command_name: str):
        """Start tracking command execution"""
        self.command_name = command_name
        self.start_time = datetime.now()
        if self.verbose:
            self.log(f"Starting {command_name} command", "info")
    
    def end_command_tracking(self):
        """End tracking command execution"""
        if self.start_time and self.verbose:
            execution_time = (datetime.now() - self.start_time).total_seconds()
            self.log(f"Command {self.command_name} completed in {execution_time:.2f} seconds", "success")
    
    async def cleanup(self):
        """Clean up resources"""
        try:
            if self.verbose:
                self.log("Starting cleanup...", "info")
            
            # Clean up package service if it exists
            if hasattr(self.service_fallback, '_services') and 'package_service' in self.service_fallback._services:
                package_service = self.service_fallback._services['package_service']
                if hasattr(package_service, 'cleanup'):
                    if self.verbose:
                        self.log("Cleaning up package service...", "info")
                    await package_service.cleanup()
            
            # Clean up storage service - handle singleton properly
            storage_service = None
            if hasattr(self.service_fallback, '_services') and 'storage_service' in self.service_fallback._services:
                storage_service = self.service_fallback._services['storage_service']
            else:
                # Clean up singleton instance if it exists
                try:
                    storage_service = await StorageService.get_instance()
                except:
                    pass  # No instance exists
            
            if storage_service and hasattr(storage_service, 'cleanup'):
                if self.verbose:
                    self.log("Cleaning up storage service...", "info")
                await storage_service.cleanup()
                
                # Give a small delay to allow any pending operations to complete
                import asyncio
                await asyncio.sleep(0.1)
                
                # Force cleanup of any remaining aiohttp sessions
                try:
                    import aiohttp
                    # Close all aiohttp sessions that might be lingering
                    if hasattr(aiohttp, '_connector_cleanup'):
                        aiohttp._connector_cleanup()
                except:
                    pass  # Ignore any errors in aiohttp cleanup
            
            if self.verbose:
                self.log("Cleanup completed", "info")
        except Exception as e:
            if self.verbose:
                self.log(f"Warning: Error during cleanup: {e}", "warning")

class SmartCommand:
    """Base class for commands that can use HTTP or direct service calls"""
    
    def __init__(self, ctx: CLIContext):
        self.ctx = ctx
    
    async def execute_with_fallback(self, http_operation, fallback_operation):
        """Execute operation with HTTP first, fallback to direct service calls"""
        try:
            # Try HTTP first
            self.ctx.log("Attempting to connect to server...", "info")
            result = await http_operation()
            self.ctx.log("Connected to server successfully", "success")
            return result
        except (click.ClickException, Exception) as e:
            # Check if it's a connection error
            error_msg = str(e).lower()
            if any(keyword in error_msg for keyword in [
                "connection", "connect", "timeout", "unreachable", 
                "refused", "failed", "not found", "404", "405", "500"
            ]):
                # Fallback to direct service calls
                self.ctx.log("Server unavailable, using direct service calls...", "warning")
                return await fallback_operation()
            else:
                # Re-raise other errors
                raise e


def format_json_output(data: Dict[str, Any], pretty: bool = True) -> str:
    """Format data as JSON output"""
    if pretty:
        return json.dumps(data, indent=2, default=str)
    else:
        return json.dumps(data, default=str)


def format_table_output(data: list, headers: list) -> str:
    """Format data as table output"""
    if not data:
        return "No data available"
    
    # Simple table formatting
    result = []
    result.append(" | ".join(headers))
    result.append("-" * (len(" | ".join(headers))))
    
    for row in data:
        result.append(" | ".join(str(row.get(h, "")) for h in headers))
    
    return "\n".join(result)


def confirm_action(message: str, default: bool = False) -> bool:
    """Ask for user confirmation"""
    return click.confirm(message, default=default)


def echo_success(message: str):
    """Echo success message"""
    click.echo(f"✅ {message}")


def echo_error(message: str):
    """Echo error message"""
    click.echo(f"❌ {message}", err=True)


def echo_warning(message: str):
    """Echo warning message"""
    click.echo(f"⚠️  {message}", err=True)


def echo_info(message: str):
    """Echo info message"""
    click.echo(f"ℹ️  {message}")


def format_llm_output(data: Dict[str, Any], cli_ctx: CLIContext) -> str:
    """Format output with LLM-specific information"""
    if cli_ctx.is_llm_enabled():
        llm_info = {
            "llm_provider": cli_ctx.get_llm_provider(),
            "llm_model": cli_ctx.get_llm_model(),
            "quality_level": cli_ctx.get_quality_level(),
            "strict_mode": cli_ctx.is_strict_mode()
        }
        data["llm_info"] = llm_info
    
    return format_json_output(data, pretty=True)


def create_llm_request_data(cli_ctx: CLIContext, base_data: Dict[str, Any]) -> Dict[str, Any]:
    """Create request data with LLM configuration"""
    request_data = base_data.copy()
    
    if cli_ctx.is_llm_enabled():
        request_data.update({
            "use_llm": True,
            "llm_provider": cli_ctx.get_llm_provider(),
            "llm_model": cli_ctx.get_llm_model(),
            "quality_level": cli_ctx.get_quality_level(),
            "strict_mode": cli_ctx.is_strict_mode()
        })
    
    return request_data


def log_llm_usage(cli_ctx: CLIContext, operation: str, cost: Optional[float] = None):
    """Log LLM usage information"""
    if cli_ctx.is_llm_enabled() and cli_ctx.verbose:
        provider = cli_ctx.get_llm_provider()
        model = cli_ctx.get_llm_model() or "default"
        quality = cli_ctx.get_quality_level()
        
        log_msg = f"LLM {operation} using {provider}/{model} (quality: {quality})"
        if cost:
            log_msg += f" (cost: ${cost:.4f})"
        
        cli_ctx.log(log_msg, "info")


# Global CLI configuration
cli_config = CLIConfig.from_settings()
