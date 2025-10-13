"""
Base CLI framework for Open Matching Engine

This module provides the foundation for all CLI commands, including:
- HTTP client management
- Service fallback handling
- Common utilities and error handling
- Configuration management
"""

import asyncio
import httpx
import click
import json
import logging
from typing import Optional, Dict, Any, Union
from pathlib import Path
from contextlib import asynccontextmanager

from ..config import settings
from ..core.services.package_service import PackageService
from ..core.services.okh_service import OKHService
from ..core.services.okw_service import OKWService
from ..core.services.storage_service import StorageService
from ..core.services.matching_service import MatchingService

logger = logging.getLogger(__name__)


class CLIConfig:
    """CLI configuration management"""
    
    def __init__(self):
        self.server_url = "http://localhost:8001"
        self.timeout = 30.0
        self.retry_attempts = 3
        self.verbose = False
        
    @classmethod
    def from_settings(cls) -> 'CLIConfig':
        """Create config from application settings"""
        config = cls()
        # You can add settings-based configuration here
        return config


class APIClient:
    """HTTP client for communicating with FastAPI server"""
    
    def __init__(self, config: CLIConfig):
        self.config = config
        self.base_url = f"{config.server_url}/v1"
        
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
    """Context object passed to all CLI commands"""
    
    def __init__(self, config: CLIConfig):
        self.config = config
        self.api_client = APIClient(config)
        self.service_fallback = ServiceFallback()
        self.verbose = config.verbose
    
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


def with_cli_context(f):
    """Decorator to inject CLI context into commands"""
    def wrapper(*args, **kwargs):
        config = CLIConfig.from_settings()
        ctx = CLIContext(config)
        return f(ctx, *args, **kwargs)
    return wrapper


def with_async_context(f):
    """Decorator to handle async command execution"""
    def wrapper(*args, **kwargs):
        return asyncio.run(f(*args, **kwargs))
    return wrapper


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
        except click.ClickException as e:
            if "Could not connect to server" in str(e):
                # Fallback to direct service calls
                self.ctx.log("Server unavailable, using direct service calls...", "warning")
                return await fallback_operation()
            else:
                # Re-raise other HTTP errors
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


# Global CLI configuration
cli_config = CLIConfig.from_settings()
