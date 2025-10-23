#!/usr/bin/env python3
"""
Temporary test to investigate CLI overhaul issues causing 422 errors.

This test investigates the changes made to base.py and decorators.py during the CLI overhaul
that may be causing the 422 validation errors we're seeing in system commands.

Following TDD approach to systematically identify the root cause.
"""

import asyncio
import sys
import traceback
from typing import Dict, Any

async def test_cli_context_creation():
    """Test CLIContext creation and configuration."""
    print("🧪 Testing CLIContext creation and configuration...")
    
    try:
        sys.path.insert(0, 'src')
        from cli.base import CLIContext, CLIConfig
        
        # Test 1: Create basic CLI context
        print("\n1. Testing basic CLI context creation...")
        config = CLIConfig()
        ctx = CLIContext(config)
        print(f"   ✅ Success: CLI context created")
        print(f"   - verbose: {ctx.verbose}")
        print(f"   - config.verbose: {ctx.config.verbose}")
        
        # Test 2: Test verbose flag propagation
        print("\n2. Testing verbose flag propagation...")
        config.verbose = True
        ctx2 = CLIContext(config)
        print(f"   ✅ Success: CLI context with verbose=True")
        print(f"   - verbose: {ctx2.verbose}")
        print(f"   - config.verbose: {ctx2.config.verbose}")
        
        # Test 3: Test manual verbose setting (like we do in commands)
        print("\n3. Testing manual verbose setting...")
        ctx.verbose = True
        ctx.config.verbose = True
        print(f"   ✅ Success: Manual verbose setting")
        print(f"   - verbose: {ctx.verbose}")
        print(f"   - config.verbose: {ctx.config.verbose}")
        
    except Exception as e:
        print(f"   ❌ Error: {e}")
        traceback.print_exc()

async def test_api_client_request_formatting():
    """Test APIClient request formatting and parameters."""
    print("\n🧪 Testing APIClient request formatting...")
    
    try:
        sys.path.insert(0, 'src')
        from cli.base import CLIContext, CLIConfig, APIClient
        
        config = CLIConfig()
        ctx = CLIContext(config)
        
        # Test 1: Test request parameter formatting
        print("\n1. Testing request parameter formatting...")
        
        # Simulate what the system commands are doing
        test_params = {
            'active_only': True,
            'name': 'manufacturing'
        }
        
        print(f"   Test params: {test_params}")
        
        # Test 2: Test base URL construction
        print("\n2. Testing base URL construction...")
        api_client = APIClient(config)
        print(f"   Base URL: {api_client.base_url}")
        print(f"   Expected: {config.server_url}/v1")
        
        # Test 3: Test endpoint path construction
        print("\n3. Testing endpoint path construction...")
        endpoint = "/api/utility/domains"
        full_url = f"{api_client.base_url}{endpoint}"
        print(f"   Full URL: {full_url}")
        
    except Exception as e:
        print(f"   ❌ Error: {e}")
        traceback.print_exc()

async def test_decorator_parameter_handling():
    """Test decorator parameter handling and LLM config."""
    print("\n🧪 Testing decorator parameter handling...")
    
    try:
        sys.path.insert(0, 'src')
        from cli.decorators import with_llm_config, create_llm_request_data
        from cli.base import CLIContext, CLIConfig
        
        config = CLIConfig()
        ctx = CLIContext(config)
        
        # Test 1: Test LLM config creation
        print("\n1. Testing LLM config creation...")
        llm_kwargs = {
            'use_llm': True,
            'llm_provider': 'anthropic',
            'llm_model': 'claude-3-sonnet',
            'quality_level': 'professional',
            'strict_mode': False
        }
        
        ctx.update_llm_config(**llm_kwargs)
        print(f"   ✅ LLM config updated: {ctx.llm_config}")
        
        # Test 2: Test LLM request data creation
        print("\n2. Testing LLM request data creation...")
        base_data = {
            'active_only': True,
            'name': 'manufacturing'
        }
        
        request_data = create_llm_request_data(ctx, base_data)
        print(f"   ✅ Request data: {request_data}")
        
        # Test 3: Test what happens when LLM is disabled
        print("\n3. Testing LLM disabled scenario...")
        ctx2 = CLIContext(config)
        request_data2 = create_llm_request_data(ctx2, base_data)
        print(f"   ✅ Request data (no LLM): {request_data2}")
        
    except Exception as e:
        print(f"   ❌ Error: {e}")
        traceback.print_exc()

async def test_system_command_parameter_flow():
    """Test the parameter flow in system commands."""
    print("\n🧪 Testing system command parameter flow...")
    
    try:
        sys.path.insert(0, 'src')
        from cli.base import CLIContext, CLIConfig, create_llm_request_data
        
        config = CLIConfig()
        ctx = CLIContext(config)
        
        # Simulate the system domains command parameter flow
        print("\n1. Simulating system domains command flow...")
        
        # These are the parameters that would come from the decorator
        command_kwargs = {
            'verbose': True,
            'output_format': 'text',
            'use_llm': False,
            'llm_provider': 'anthropic',
            'llm_model': None,
            'quality_level': 'professional',
            'strict_mode': False
        }
        
        print(f"   Command kwargs: {command_kwargs}")
        
        # Apply verbose fix (like we do in the commands)
        ctx.verbose = command_kwargs['verbose']
        ctx.config.verbose = command_kwargs['verbose']
        
        # Update LLM config
        ctx.update_llm_config(
            use_llm=command_kwargs['use_llm'],
            llm_provider=command_kwargs['llm_provider'],
            llm_model=command_kwargs['llm_model'],
            quality_level=command_kwargs['quality_level'],
            strict_mode=command_kwargs['strict_mode']
        )
        
        print(f"   ✅ Context updated:")
        print(f"   - verbose: {ctx.verbose}")
        print(f"   - llm_config: {ctx.llm_config}")
        
        # Test 2: Test what parameters would be sent to API
        print("\n2. Testing API request parameters...")
        
        # This is what would be sent as query parameters
        api_params = {
            'active_only': True,
            'name': None,  # Not provided
            'use_llm': False,
            'llm_provider': 'anthropic',
            'llm_model': None,
            'quality_level': 'professional',
            'strict_mode': False
        }
        
        # Filter out None values
        filtered_params = {k: v for k, v in api_params.items() if v is not None}
        print(f"   ✅ Filtered API params: {filtered_params}")
        
    except Exception as e:
        print(f"   ❌ Error: {e}")
        traceback.print_exc()

async def test_extra_data_parameter_origin():
    """Test where the extra_data parameter requirement might be coming from."""
    print("\n🧪 Testing extra_data parameter origin...")
    
    try:
        sys.path.insert(0, 'src')
        from cli.base import CLIContext, CLIConfig, create_llm_request_data
        
        config = CLIConfig()
        ctx = CLIContext(config)
        
        # Test 1: Test LLM request data with all possible fields
        print("\n1. Testing LLM request data with all fields...")
        
        ctx.update_llm_config(
            use_llm=True,
            llm_provider='anthropic',
            llm_model='claude-3-sonnet',
            quality_level='professional',
            strict_mode=True
        )
        
        base_data = {
            'active_only': True,
            'name': 'manufacturing'
        }
        
        request_data = create_llm_request_data(ctx, base_data)
        print(f"   ✅ Full request data: {request_data}")
        
        # Test 2: Check if any field could be interpreted as extra_data
        print("\n2. Checking for potential extra_data fields...")
        for key, value in request_data.items():
            if 'extra' in key.lower() or 'data' in key.lower():
                print(f"   ⚠️  Potential extra_data field: {key} = {value}")
        
        # Test 3: Test with minimal data
        print("\n3. Testing with minimal data...")
        ctx2 = CLIContext(config)
        minimal_data = {}
        request_data2 = create_llm_request_data(ctx2, minimal_data)
        print(f"   ✅ Minimal request data: {request_data2}")
        
    except Exception as e:
        print(f"   ❌ Error: {e}")
        traceback.print_exc()

async def main():
    """Run all tests to investigate CLI overhaul issues."""
    print("🔬 TDD Investigation of CLI Overhaul Issues")
    print("=" * 60)
    
    await test_cli_context_creation()
    await test_api_client_request_formatting()
    await test_decorator_parameter_handling()
    await test_system_command_parameter_flow()
    await test_extra_data_parameter_origin()
    
    print("\n" + "=" * 60)
    print("🏁 Investigation complete")

if __name__ == "__main__":
    asyncio.run(main())
