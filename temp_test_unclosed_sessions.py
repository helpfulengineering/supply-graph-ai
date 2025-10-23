#!/usr/bin/env python3
"""
Temporary test to reproduce unclosed aiohttp session issue.

This test is designed to:
1. Reproduce the unclosed session warnings
2. Identify the exact source of the sessions
3. Validate that our fix resolves the issue

Cleanup: This file should be removed after the session cleanup issue is resolved.
"""

import asyncio
import sys
import os
import warnings
from io import StringIO
from contextlib import redirect_stderr

# Add the src directory to the path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from src.cli.base import CLIContext, CLIConfig
from src.core.services.storage_service import StorageService
from src.core.packaging.remote_storage import PackageRemoteStorage
from src.config import settings


async def test_unclosed_sessions():
    """Test that reproduces the unclosed session issue."""
    print("🔍 Testing for unclosed aiohttp sessions...")
    
    # Capture stderr to check for unclosed session warnings
    stderr_capture = StringIO()
    
    with redirect_stderr(stderr_capture):
        print("📋 Step 1: Creating CLI context...")
        config = CLIConfig()
        cli_ctx = CLIContext(config)
        
        print("📋 Step 2: Initializing storage service...")
        # Simulate the list-remote command that causes the issue
        try:
            storage_service = await StorageService.get_instance()
            await storage_service.configure(settings.STORAGE_CONFIG)
            
            print("📋 Step 3: Creating remote storage...")
            remote_storage = PackageRemoteStorage(storage_service)
            
            print("📋 Step 4: Listing remote packages...")
            packages = await remote_storage.list_remote_packages()
            
            print(f"✅ Found {len(packages)} packages")
            
            print("📋 Step 5: Cleaning up...")
            # Clean up
            try:
                await cli_ctx.cleanup()
                print("✅ CLI cleanup completed")
            except Exception as e:
                print(f"⚠️  CLI cleanup error: {e}")
            
            print("📋 Step 6: Additional storage cleanup...")
            try:
                await storage_service.cleanup()
                print("✅ Storage cleanup completed")
            except Exception as e:
                print(f"⚠️  Storage cleanup error: {e}")
            
        except Exception as e:
            print(f"❌ Error during test: {e}")
    
    # Check for unclosed session warnings
    stderr_output = stderr_capture.getvalue()
    
    if "Unclosed client session" in stderr_output:
        print("❌ UNCLOSED SESSION DETECTED:")
        print(stderr_output)
        return False
    else:
        print("✅ No unclosed session warnings detected")
        return True


async def test_cleanup_effectiveness():
    """Test that our cleanup methods are actually being called."""
    print("\n🔍 Testing cleanup effectiveness...")
    
    stderr_capture = StringIO()
    
    with redirect_stderr(stderr_capture):
        # Create CLI context with verbose mode
        config = CLIConfig()
        config.verbose = True
        cli_ctx = CLIContext(config)
        
        # Initialize services through ServiceFallback (this is what CLI commands do)
        storage_service = await cli_ctx.service_fallback.get_storage_service()
        
        print(f"📋 Services in fallback: {list(cli_ctx.service_fallback._services.keys())}")
        
        # Test cleanup
        await cli_ctx.cleanup()
        
        print("✅ Cleanup test completed")
    
    stderr_output = stderr_capture.getvalue()
    
    if "Unclosed client session" in stderr_output:
        print("❌ CLEANUP IS CREATING UNCLOSED SESSIONS!")
        print(stderr_output)
        return False
    else:
        print("✅ Cleanup test completed without session warnings")
        return True


async def test_azure_sdk_sessions():
    """Test if Azure SDK is creating the unclosed sessions."""
    print("\n🔍 Testing Azure SDK session creation...")
    
    stderr_capture = StringIO()
    
    with redirect_stderr(stderr_capture):
        try:
            # Import Azure modules directly
            from azure.storage.blob.aio import BlobServiceClient
            
            # Create Azure client directly
            conn_str = "DefaultEndpointsProtocol=https;AccountName=test;AccountKey=test;EndpointSuffix=core.windows.net"
            client = BlobServiceClient.from_connection_string(conn_str)
            
            print("📋 Azure client created")
            
            # Try to close it
            await client.close()
            print("📋 Azure client closed")
            
        except Exception as e:
            print(f"⚠️  Azure test error (expected): {e}")
    
    stderr_output = stderr_capture.getvalue()
    
    if "Unclosed client session" in stderr_output:
        print("❌ Azure SDK is creating unclosed sessions!")
        print(stderr_output)
    else:
        print("✅ Azure SDK test completed without session warnings")


async def test_azure_provider_cleanup():
    """Test the Azure provider cleanup method specifically."""
    print("\n🔍 Testing Azure provider cleanup...")
    
    stderr_capture = StringIO()
    
    with redirect_stderr(stderr_capture):
        try:
            from src.core.storage.providers.azure import AzureBlobProvider
            from src.core.storage.base import StorageConfig
            
            # Create Azure provider with real config
            config = StorageConfig(
                provider="azure_blob",
                bucket_name="ome",
                credentials={
                    "account_name": "ome",
                    "account_key": "test_key"
                }
            )
            
            provider = AzureBlobProvider(config)
            
            print("📋 Azure provider created")
            
            # Try to connect (this will fail but might create sessions)
            try:
                await provider.connect()
            except Exception as e:
                print(f"⚠️  Connection failed (expected): {e}")
            
            # Clean up
            await provider.cleanup()
            print("📋 Azure provider cleaned up")
            
        except Exception as e:
            print(f"❌ Azure provider test error: {e}")
    
    stderr_output = stderr_capture.getvalue()
    
    if "Unclosed client session" in stderr_output:
        print("❌ Azure provider is creating unclosed sessions!")
        print(stderr_output)
    else:
        print("✅ Azure provider test completed without session warnings")


async def test_event_loop_cleanup():
    """Test if the issue is related to event loop cleanup."""
    print("\n🔍 Testing event loop cleanup...")
    
    # Create a custom event loop to test cleanup
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    
    try:
        # Initialize services
        storage_service = await StorageService.get_instance()
        await storage_service.configure(settings.STORAGE_CONFIG)
        
        # Create remote storage and list packages
        remote_storage = PackageRemoteStorage(storage_service)
        packages = await remote_storage.list_remote_packages()
        print(f"✅ Found {len(packages)} packages")
        
        # Clean up
        await storage_service.cleanup()
        print("✅ Storage cleanup completed")
        
    except Exception as e:
        print(f"❌ Error: {e}")
    finally:
        # Close the event loop
        print("📋 Closing event loop...")
        loop.close()
        print("✅ Event loop closed")


if __name__ == "__main__":
    print("🧪 Running unclosed session tests...")
    
    # Run the tests
    asyncio.run(test_unclosed_sessions())
    asyncio.run(test_cleanup_effectiveness())
    asyncio.run(test_azure_sdk_sessions())
    asyncio.run(test_azure_provider_cleanup())
    asyncio.run(test_event_loop_cleanup())
    
    print("\n📋 Test Summary:")
    print("- If you see 'UNCLOSED SESSION DETECTED', the issue is still present")
    print("- If you see 'No unclosed session warnings', the issue is fixed")
    print("- Check cleanup effectiveness test for any cleanup-related issues")
    print("- Azure SDK test will help identify if the issue is in Azure SDK")
    print("- Event loop test will show if the issue is during loop shutdown")
    print("\n🔍 Final CLI Test:")
    print("Testing actual CLI command to verify functionality...")
    
    # Test that CLI functionality works correctly
    try:
        import subprocess
        result = subprocess.run([
            'python', 'ome', 'package', 'list-remote'
        ], capture_output=True, text=True, cwd='/Users/nathanparker/Documents/workspace/personal/open-hardware-manager/supply-graph-ai')
        
        if result.returncode == 0:
            print("✅ CLI command executed successfully")
            if "Found" in result.stdout and "remote packages" in result.stdout:
                print("✅ CLI functionality is working correctly")
            else:
                print("⚠️  CLI executed but output format may have changed")
        else:
            print(f"❌ CLI command failed with return code {result.returncode}")
            print(f"Error: {result.stderr}")
    except Exception as e:
        print(f"❌ CLI test failed: {e}")
