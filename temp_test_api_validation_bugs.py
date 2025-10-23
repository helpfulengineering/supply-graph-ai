#!/usr/bin/env python3
"""
Temporary test to investigate API validation bugs in utility endpoints.

This test reproduces the validation errors we're seeing in the server logs:
1. 422 Error: Missing 'extra_data' query parameter
2. 500 Error: Missing 'message' field in DomainsResponse

Following TDD approach to systematically identify and fix these issues.
"""

import asyncio
import httpx
import json
from typing import Dict, Any

async def test_utility_domains_endpoint():
    """Test the utility domains endpoint to reproduce validation errors."""
    print("🧪 Testing utility domains endpoint...")
    
    base_url = "http://localhost:8001"
    
    async with httpx.AsyncClient() as client:
        # Test 1: Basic request without parameters
        print("\n1. Testing basic request without parameters...")
        try:
            response = await client.get(f"{base_url}/v1/api/utility/domains")
            print(f"   Status: {response.status_code}")
            print(f"   Response: {response.text}")
        except Exception as e:
            print(f"   Error: {e}")
        
        # Test 2: Request with extra_data parameter
        print("\n2. Testing request with extra_data parameter...")
        try:
            response = await client.get(f"{base_url}/v1/api/utility/domains?extra_data=true")
            print(f"   Status: {response.status_code}")
            print(f"   Response: {response.text}")
        except Exception as e:
            print(f"   Error: {e}")
        
        # Test 3: Request with other parameters
        print("\n3. Testing request with other parameters...")
        try:
            response = await client.get(f"{base_url}/v1/api/utility/domains?active_only=true&name=manufacturing")
            print(f"   Status: {response.status_code}")
            print(f"   Response: {response.text}")
        except Exception as e:
            print(f"   Error: {e}")

async def test_domains_response_model():
    """Test the DomainsResponse model to understand validation requirements."""
    print("\n🧪 Testing DomainsResponse model...")
    
    # Import the response model
    try:
        import sys
        sys.path.insert(0, 'src')
        from core.api.models.utility.response import DomainsResponse, Domain
        
        # Test creating a DomainsResponse with minimal data
        print("\n1. Testing DomainsResponse with minimal data...")
        try:
            domains = [
                Domain(
                    id="manufacturing",
                    name="Manufacturing Domain",
                    description="Hardware manufacturing capabilities"
                )
            ]
            
            response = DomainsResponse(
                domains=domains
            )
            print(f"   ✅ Success: {response}")
        except Exception as e:
            print(f"   ❌ Error: {e}")
        
        # Test creating a DomainsResponse with all fields
        print("\n2. Testing DomainsResponse with all fields...")
        try:
            response = DomainsResponse(
                domains=domains,
                message="Domains retrieved successfully",
                total=1,
                metadata={}
            )
            print(f"   ✅ Success: {response}")
        except Exception as e:
            print(f"   ❌ Error: {e}")
            
    except ImportError as e:
        print(f"   ❌ Import Error: {e}")

async def test_domain_filter_request():
    """Test the DomainFilterRequest model to understand validation requirements."""
    print("\n🧪 Testing DomainFilterRequest model...")
    
    try:
        import sys
        sys.path.insert(0, 'src')
        from core.api.models.utility.request import DomainFilterRequest
        
        # Test creating a DomainFilterRequest with minimal data
        print("\n1. Testing DomainFilterRequest with minimal data...")
        try:
            request = DomainFilterRequest()
            print(f"   ✅ Success: {request}")
        except Exception as e:
            print(f"   ❌ Error: {e}")
        
        # Test creating a DomainFilterRequest with extra_data
        print("\n2. Testing DomainFilterRequest with extra_data...")
        try:
            request = DomainFilterRequest(extra_data=True)
            print(f"   ✅ Success: {request}")
        except Exception as e:
            print(f"   ❌ Error: {e}")
            
    except ImportError as e:
        print(f"   ❌ Import Error: {e}")

async def main():
    """Run all tests to investigate API validation bugs."""
    print("🔬 TDD Investigation of API Validation Bugs")
    print("=" * 50)
    
    await test_utility_domains_endpoint()
    await test_domains_response_model()
    await test_domain_filter_request()
    
    print("\n" + "=" * 50)
    print("🏁 Investigation complete")

if __name__ == "__main__":
    asyncio.run(main())
