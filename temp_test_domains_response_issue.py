#!/usr/bin/env python3
"""
Temporary test to isolate the DomainsResponse issue.

This test focuses specifically on the DomainsResponse model and its inheritance
to identify what's causing the 500 error.
"""

import sys
import traceback

def test_domains_response_creation():
    """Test DomainsResponse creation with different approaches."""
    print("🧪 Testing DomainsResponse creation...")
    
    try:
        sys.path.insert(0, 'src')
        from core.api.models.utility.response import DomainsResponse, Domain
        from core.api.models.base import ValidationResult
        
        # Test 1: Create DomainsResponse with minimal data
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
                domains=domains,
                message="Domains retrieved successfully"
            )
            print(f"   ✅ Success: {response}")
        except Exception as e:
            print(f"   ❌ Error: {e}")
            traceback.print_exc()
        
        # Test 2: Create DomainsResponse with validation results
        print("\n2. Testing DomainsResponse with validation results...")
        try:
            validation_results = [
                ValidationResult(
                    is_valid=True,
                    score=1.0,
                    errors=[],
                    warnings=[],
                    suggestions=[]
                )
            ]
            
            response = DomainsResponse(
                domains=domains,
                message="Domains retrieved successfully",
                validation_results=validation_results
            )
            print(f"   ✅ Success: {response}")
        except Exception as e:
            print(f"   ❌ Error: {e}")
            traceback.print_exc()
        
        # Test 3: Test what the endpoint is actually trying to create
        print("\n3. Testing endpoint-style DomainsResponse creation...")
        try:
            # This is exactly what the endpoint is trying to do
            response = DomainsResponse(
                domains=domains,
                message="Domains retrieved successfully",
                processing_time=0.001,
                validation_results=validation_results
            )
            print(f"   ✅ Success: {response}")
        except Exception as e:
            print(f"   ❌ Error: {e}")
            traceback.print_exc()
            
    except ImportError as e:
        print(f"   ❌ Import Error: {e}")
        traceback.print_exc()

def test_inheritance_chain():
    """Test the inheritance chain of DomainsResponse."""
    print("\n🧪 Testing DomainsResponse inheritance chain...")
    
    try:
        sys.path.insert(0, 'src')
        from core.api.models.utility.response import DomainsResponse
        from core.api.models.base import SuccessResponse, LLMResponseMixin
        
        # Test 1: Check inheritance
        print("\n1. Checking inheritance...")
        print(f"   DomainsResponse MRO: {DomainsResponse.__mro__}")
        print(f"   Inherits from SuccessResponse: {issubclass(DomainsResponse, SuccessResponse)}")
        print(f"   Inherits from LLMResponseMixin: {issubclass(DomainsResponse, LLMResponseMixin)}")
        
        # Test 2: Check field definitions
        print("\n2. Checking field definitions...")
        fields = DomainsResponse.__fields__
        print(f"   Fields: {list(fields.keys())}")
        
        # Check for field conflicts
        for field_name, field_info in fields.items():
            print(f"   - {field_name}: {field_info.type_}")
            
    except Exception as e:
        print(f"   ❌ Error: {e}")
        traceback.print_exc()

def test_base_classes():
    """Test the base classes individually."""
    print("\n🧪 Testing base classes individually...")
    
    try:
        sys.path.insert(0, 'src')
        from core.api.models.base import SuccessResponse, LLMResponseMixin, ValidationResult
        
        # Test 1: SuccessResponse
        print("\n1. Testing SuccessResponse...")
        try:
            success_response = SuccessResponse(
                message="Test message"
            )
            print(f"   ✅ SuccessResponse: {success_response}")
        except Exception as e:
            print(f"   ❌ SuccessResponse Error: {e}")
            traceback.print_exc()
        
        # Test 2: LLMResponseMixin
        print("\n2. Testing LLMResponseMixin...")
        try:
            # LLMResponseMixin is a mixin, so we need to create a class that inherits from it
            class TestLLMResponse(LLMResponseMixin):
                pass
            
            llm_response = TestLLMResponse()
            print(f"   ✅ LLMResponseMixin: {llm_response}")
        except Exception as e:
            print(f"   ❌ LLMResponseMixin Error: {e}")
            traceback.print_exc()
        
        # Test 3: ValidationResult
        print("\n3. Testing ValidationResult...")
        try:
            validation_result = ValidationResult(
                is_valid=True,
                score=1.0,
                errors=[],
                warnings=[],
                suggestions=[]
            )
            print(f"   ✅ ValidationResult: {validation_result}")
        except Exception as e:
            print(f"   ❌ ValidationResult Error: {e}")
            traceback.print_exc()
            
    except Exception as e:
        print(f"   ❌ Error: {e}")
        traceback.print_exc()

def main():
    """Run all tests to isolate the DomainsResponse issue."""
    print("🔬 TDD Investigation of DomainsResponse Issue")
    print("=" * 60)
    
    test_domains_response_creation()
    test_inheritance_chain()
    test_base_classes()
    
    print("\n" + "=" * 60)
    print("🏁 Investigation complete")

if __name__ == "__main__":
    main()
