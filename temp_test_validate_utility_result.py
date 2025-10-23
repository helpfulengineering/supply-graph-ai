#!/usr/bin/env python3
"""
Temporary test to test the _validate_utility_result function directly.

This test focuses on the _validate_utility_result function to see if it's
causing the 500 error.
"""

import asyncio
import sys
import traceback

async def test_validate_utility_result():
    """Test the _validate_utility_result function directly."""
    print("🧪 Testing _validate_utility_result function...")
    
    try:
        sys.path.insert(0, 'src')
        from core.api.models.utility.response import Domain
        from core.api.models.base import ValidationResult
        
        # Import the function from the utility routes
        from core.api.routes.utility import _validate_utility_result
        
        # Test 1: Test with empty list
        print("\n1. Testing with empty list...")
        try:
            result = await _validate_utility_result([], "test-request-id")
            print(f"   ✅ Success: {result}")
        except Exception as e:
            print(f"   ❌ Error: {e}")
            traceback.print_exc()
        
        # Test 2: Test with domain list
        print("\n2. Testing with domain list...")
        try:
            domains = [
                Domain(
                    id="manufacturing",
                    name="Manufacturing Domain",
                    description="Hardware manufacturing capabilities"
                )
            ]
            result = await _validate_utility_result(domains, "test-request-id")
            print(f"   ✅ Success: {result}")
        except Exception as e:
            print(f"   ❌ Error: {e}")
            traceback.print_exc()
        
        # Test 3: Test with None
        print("\n3. Testing with None...")
        try:
            result = await _validate_utility_result(None, "test-request-id")
            print(f"   ✅ Success: {result}")
        except Exception as e:
            print(f"   ❌ Error: {e}")
            traceback.print_exc()
        
        # Test 4: Test with invalid data
        print("\n4. Testing with invalid data...")
        try:
            result = await _validate_utility_result("invalid", "test-request-id")
            print(f"   ✅ Success: {result}")
        except Exception as e:
            print(f"   ❌ Error: {e}")
            traceback.print_exc()
            
    except ImportError as e:
        print(f"   ❌ Import Error: {e}")
        traceback.print_exc()

async def test_endpoint_logic_step_by_step():
    """Test the endpoint logic step by step."""
    print("\n🧪 Testing endpoint logic step by step...")
    
    try:
        sys.path.insert(0, 'src')
        from core.api.models.utility.response import Domain, DomainsResponse
        from core.api.models.utility.request import DomainFilterRequest
        from core.api.routes.utility import _validate_utility_result
        from datetime import datetime
        
        # Test 1: Create filter_params
        print("\n1. Creating filter_params...")
        try:
            filter_params = DomainFilterRequest()
            print(f"   ✅ Success: {filter_params}")
        except Exception as e:
            print(f"   ❌ Error: {e}")
            traceback.print_exc()
            return
        
        # Test 2: Create domains
        print("\n2. Creating domains...")
        try:
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
            print(f"   ✅ Success: {len(domains)} domains")
        except Exception as e:
            print(f"   ❌ Error: {e}")
            traceback.print_exc()
            return
        
        # Test 3: Apply name filter
        print("\n3. Applying name filter...")
        try:
            if filter_params.name:
                domains = [d for d in domains if filter_params.name.lower() in d.name.lower()]
            print(f"   ✅ Success: {len(domains)} domains after filter")
        except Exception as e:
            print(f"   ❌ Error: {e}")
            traceback.print_exc()
            return
        
        # Test 4: Calculate processing time
        print("\n4. Calculating processing time...")
        try:
            start_time = datetime.now()
            processing_time = (datetime.now() - start_time).total_seconds()
            print(f"   ✅ Success: {processing_time} seconds")
        except Exception as e:
            print(f"   ❌ Error: {e}")
            traceback.print_exc()
            return
        
        # Test 5: Validate utility result
        print("\n5. Validating utility result...")
        try:
            validation_results = await _validate_utility_result(domains, "test-request-id")
            print(f"   ✅ Success: {len(validation_results)} validation results")
        except Exception as e:
            print(f"   ❌ Error: {e}")
            traceback.print_exc()
            return
        
        # Test 6: Create DomainsResponse
        print("\n6. Creating DomainsResponse...")
        try:
            response = DomainsResponse(
                domains=domains,
                message="Domains retrieved successfully",
                processing_time=processing_time,
                validation_results=validation_results
            )
            print(f"   ✅ Success: {response}")
        except Exception as e:
            print(f"   ❌ Error: {e}")
            traceback.print_exc()
            return
        
        print("\n✅ All steps completed successfully!")
        
    except Exception as e:
        print(f"   ❌ Error: {e}")
        traceback.print_exc()

async def main():
    """Run all tests to investigate the _validate_utility_result function."""
    print("🔬 TDD Investigation of _validate_utility_result Function")
    print("=" * 70)
    
    await test_validate_utility_result()
    await test_endpoint_logic_step_by_step()
    
    print("\n" + "=" * 70)
    print("🏁 Investigation complete")

if __name__ == "__main__":
    asyncio.run(main())
