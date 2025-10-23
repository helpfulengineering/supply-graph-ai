#!/usr/bin/env python3
"""
Temporary test to investigate 500 Internal Server Error on /v1/api/utility/domains.

This test focuses specifically on the utility domains endpoint that's causing 500 errors
after our fixes to the BaseAPIRequest validation.

Following TDD approach to systematically identify the root cause.
"""

import asyncio
import httpx
import json
import sys
from typing import Dict, Any

async def test_utility_domains_endpoint_directly():
    """Test the utility domains endpoint directly to reproduce the 500 error."""
    print("🧪 Testing utility domains endpoint directly...")
    
    base_url = "http://localhost:8001"
    
    async with httpx.AsyncClient() as client:
        # Test 1: Basic request to reproduce the 500 error
        print("\n1. Testing basic request to /v1/api/utility/domains...")
        try:
            response = await client.get(f"{base_url}/v1/api/utility/domains")
            print(f"   Status: {response.status_code}")
            print(f"   Response: {response.text}")
            
            if response.status_code == 500:
                print("   ❌ 500 Error reproduced!")
            else:
                print("   ✅ No 500 error")
                
        except Exception as e:
            print(f"   Error: {e}")
        
        # Test 2: Request with query parameters
        print("\n2. Testing request with query parameters...")
        try:
            params = {
                'active_only': True,
                'name': 'manufacturing'
            }
            response = await client.get(f"{base_url}/v1/api/utility/domains", params=params)
            print(f"   Status: {response.status_code}")
            print(f"   Response: {response.text}")
            
            if response.status_code == 500:
                print("   ❌ 500 Error with params!")
            else:
                print("   ✅ No 500 error with params")
                
        except Exception as e:
            print(f"   Error: {e}")

async def test_domains_response_model_validation():
    """Test the DomainsResponse model validation after our changes."""
    print("\n🧪 Testing DomainsResponse model validation...")
    
    try:
        sys.path.insert(0, 'src')
        from core.api.models.utility.response import DomainsResponse, Domain
        
        # Test 1: Create DomainsResponse with all required fields
        print("\n1. Testing DomainsResponse with all required fields...")
        try:
            domains = [
                Domain(
                    id="manufacturing",
                    name="Manufacturing Domain",
                    description="Hardware manufacturing capabilities"
                )
            ]
            
            response = DomainsResponse(
                domains=domains,
                message="Domains retrieved successfully"
            )
            print(f"   ✅ Success: {response}")
        except Exception as e:
            print(f"   ❌ Error: {e}")
        
        # Test 2: Test what the endpoint is actually returning
        print("\n2. Testing endpoint return format...")
        try:
            # This is what the endpoint should return
            endpoint_data = {
                "domains": [d.model_dump() for d in domains],
                "message": "Domains retrieved successfully",
                "total": len(domains)
            }
            
            # Try to create DomainsResponse from this data
            response = DomainsResponse(**endpoint_data)
            print(f"   ✅ Success: {response}")
        except Exception as e:
            print(f"   ❌ Error: {e}")
            
    except ImportError as e:
        print(f"   ❌ Import Error: {e}")

async def test_domain_filter_request_validation():
    """Test the DomainFilterRequest model validation after our changes."""
    print("\n🧪 Testing DomainFilterRequest model validation...")
    
    try:
        sys.path.insert(0, 'src')
        from core.api.models.utility.request import DomainFilterRequest
        
        # Test 1: Create DomainFilterRequest with minimal data
        print("\n1. Testing DomainFilterRequest with minimal data...")
        try:
            request = DomainFilterRequest()
            print(f"   ✅ Success: {request}")
        except Exception as e:
            print(f"   ❌ Error: {e}")
        
        # Test 2: Create DomainFilterRequest with query parameters
        print("\n2. Testing DomainFilterRequest with query parameters...")
        try:
            request = DomainFilterRequest(
                active_only=True,
                name="manufacturing",
                use_llm=False,
                llm_provider="anthropic",
                quality_level="professional",
                strict_mode=False
            )
            print(f"   ✅ Success: {request}")
        except Exception as e:
            print(f"   ❌ Error: {e}")
            
        # Test 3: Test what FastAPI would receive as query parameters
        print("\n3. Testing FastAPI query parameter parsing...")
        try:
            # Simulate what FastAPI would parse from query string
            query_params = {
                'active_only': 'true',
                'name': 'manufacturing'
            }
            
            # Convert string values to appropriate types
            parsed_params = {}
            for key, value in query_params.items():
                if key == 'active_only':
                    parsed_params[key] = value.lower() == 'true'
                else:
                    parsed_params[key] = value
            
            request = DomainFilterRequest(**parsed_params)
            print(f"   ✅ Success: {request}")
        except Exception as e:
            print(f"   ❌ Error: {e}")
            
    except ImportError as e:
        print(f"   ❌ Import Error: {e}")

async def test_endpoint_implementation():
    """Test the endpoint implementation logic."""
    print("\n🧪 Testing endpoint implementation logic...")
    
    try:
        sys.path.insert(0, 'src')
        from core.api.models.utility.response import DomainsResponse, Domain
        from core.api.models.utility.request import DomainFilterRequest
        
        # Test 1: Simulate the endpoint logic
        print("\n1. Simulating endpoint logic...")
        try:
            # Simulate what the endpoint does
            filter_params = DomainFilterRequest()
            
            # Placeholder implementation (like in the endpoint)
            domains = [
                Domain(
                    id="manufacturing",
                    name="Manufacturing Domain",
                    description="Hardware manufacturing capabilities"
                ),
                Domain(
                    id="cooking",
                    name="Cooking Domain",
                    description="Food preparation capabilities"
                )
            ]
            
            # Apply name filter if provided
            if filter_params.name:
                domains = [d for d in domains if filter_params.name.lower() in d.name.lower()]
            
            # Create response
            response = DomainsResponse(
                domains=domains,
                message="Domains retrieved successfully"
            )
            
            print(f"   ✅ Success: {response}")
            
        except Exception as e:
            print(f"   ❌ Error: {e}")
            import traceback
            traceback.print_exc()
            
    except ImportError as e:
        print(f"   ❌ Import Error: {e}")

async def main():
    """Run all tests to investigate the 500 error."""
    print("🔬 TDD Investigation of 500 Error on /v1/api/utility/domains")
    print("=" * 70)
    
    await test_utility_domains_endpoint_directly()
    await test_domains_response_model_validation()
    await test_domain_filter_request_validation()
    await test_endpoint_implementation()
    
    print("\n" + "=" * 70)
    print("🏁 Investigation complete")

if __name__ == "__main__":
    asyncio.run(main())
