#!/usr/bin/env python3
"""
Temporary test to investigate datetime serialization issues throughout the application.

This test systematically identifies all patterns that cause datetime serialization errors
and develops a universal strategy for handling datetime objects safely.

Following TDD approach to comprehensively address this issue.
"""

import json
import sys
import traceback
from datetime import datetime
from typing import Dict, Any, List

def test_datetime_serialization_patterns():
    """Test various datetime serialization patterns to identify issues."""
    print("🧪 Testing datetime serialization patterns...")
    
    # Test 1: Direct datetime serialization
    print("\n1. Testing direct datetime serialization...")
    try:
        dt = datetime.now()
        json.dumps({"timestamp": dt})
        print("   ❌ Should have failed - datetime not JSON serializable")
    except TypeError as e:
        print(f"   ✅ Expected error: {e}")
    
    # Test 2: datetime.isoformat() serialization
    print("\n2. Testing datetime.isoformat() serialization...")
    try:
        dt = datetime.now()
        json.dumps({"timestamp": dt.isoformat()})
        print("   ✅ Success: datetime.isoformat() works")
    except Exception as e:
        print(f"   ❌ Error: {e}")
    
    # Test 3: datetime in nested objects
    print("\n3. Testing datetime in nested objects...")
    try:
        dt = datetime.now()
        data = {
            "user": {
                "name": "test",
                "created_at": dt
            }
        }
        json.dumps(data)
        print("   ❌ Should have failed - nested datetime not serializable")
    except TypeError as e:
        print(f"   ✅ Expected error: {e}")
    
    # Test 4: datetime in lists
    print("\n4. Testing datetime in lists...")
    try:
        dt = datetime.now()
        data = {
            "events": [
                {"name": "event1", "time": dt},
                {"name": "event2", "time": dt}
            ]
        }
        json.dumps(data)
        print("   ❌ Should have failed - datetime in list not serializable")
    except TypeError as e:
        print(f"   ✅ Expected error: {e}")

def test_pydantic_datetime_handling():
    """Test how Pydantic handles datetime objects."""
    print("\n🧪 Testing Pydantic datetime handling...")
    
    try:
        sys.path.insert(0, 'src')
        from pydantic import BaseModel, Field
        from datetime import datetime
        
        # Test 1: Pydantic model with datetime field
        print("\n1. Testing Pydantic model with datetime field...")
        try:
            class TestModel(BaseModel):
                name: str
                timestamp: datetime = Field(default_factory=datetime.now)
            
            model = TestModel(name="test")
            print(f"   ✅ Model created: {model}")
            
            # Test serialization
            json_str = model.model_dump_json()
            print(f"   ✅ JSON serialization: {json_str}")
            
            # Test deserialization
            parsed = TestModel.model_validate_json(json_str)
            print(f"   ✅ JSON deserialization: {parsed}")
            
        except Exception as e:
            print(f"   ❌ Error: {e}")
            traceback.print_exc()
        
        # Test 2: Pydantic model with datetime in nested structure
        print("\n2. Testing Pydantic model with nested datetime...")
        try:
            class NestedModel(BaseModel):
                timestamp: datetime = Field(default_factory=datetime.now)
            
            class ParentModel(BaseModel):
                name: str
                nested: NestedModel
            
            model = ParentModel(name="test", nested=NestedModel())
            print(f"   ✅ Nested model created: {model}")
            
            # Test serialization
            json_str = model.model_dump_json()
            print(f"   ✅ Nested JSON serialization: {json_str}")
            
        except Exception as e:
            print(f"   ❌ Error: {e}")
            traceback.print_exc()
            
    except ImportError as e:
        print(f"   ❌ Import Error: {e}")

def test_application_datetime_patterns():
    """Test datetime patterns used in our application."""
    print("\n🧪 Testing application datetime patterns...")
    
    try:
        sys.path.insert(0, 'src')
        from core.api.models.base import BaseAPIResponse, SuccessResponse
        from datetime import datetime
        
        # Test 1: BaseAPIResponse with datetime
        print("\n1. Testing BaseAPIResponse with datetime...")
        try:
            response = BaseAPIResponse(
                status="success",
                message="Test message"
            )
            print(f"   ✅ BaseAPIResponse created: {response}")
            
            # Test serialization
            json_str = response.model_dump_json()
            print(f"   ✅ BaseAPIResponse JSON: {json_str}")
            
        except Exception as e:
            print(f"   ❌ Error: {e}")
            traceback.print_exc()
        
        # Test 2: SuccessResponse with datetime
        print("\n2. Testing SuccessResponse with datetime...")
        try:
            response = SuccessResponse(
                message="Test message"
            )
            print(f"   ✅ SuccessResponse created: {response}")
            
            # Test serialization
            json_str = response.model_dump_json()
            print(f"   ✅ SuccessResponse JSON: {json_str}")
            
        except Exception as e:
            print(f"   ❌ Error: {e}")
            traceback.print_exc()
            
    except ImportError as e:
        print(f"   ❌ Import Error: {e}")

def test_cli_datetime_patterns():
    """Test datetime patterns in CLI code."""
    print("\n🧪 Testing CLI datetime patterns...")
    
    try:
        sys.path.insert(0, 'src')
        from cli.base import CLIContext, CLIConfig
        from datetime import datetime
        
        # Test 1: CLIContext with datetime tracking
        print("\n1. Testing CLIContext datetime tracking...")
        try:
            config = CLIConfig()
            ctx = CLIContext(config)
            
            # Test command tracking
            ctx.start_command_tracking("test-command")
            ctx.end_command_tracking()
            
            print(f"   ✅ CLIContext datetime tracking works")
            
        except Exception as e:
            print(f"   ❌ Error: {e}")
            traceback.print_exc()
        
        # Test 2: CLI performance tracking
        print("\n2. Testing CLI performance tracking...")
        try:
            from cli.decorators import with_performance_tracking
            
            @with_performance_tracking
            def test_function():
                return "test"
            
            result = test_function()
            print(f"   ✅ Performance tracking works: {result}")
            
        except Exception as e:
            print(f"   ❌ Error: {e}")
            traceback.print_exc()
            
    except ImportError as e:
        print(f"   ❌ Import Error: {e}")

def test_datetime_serialization_strategies():
    """Test different strategies for datetime serialization."""
    print("\n🧪 Testing datetime serialization strategies...")
    
    # Test 1: Custom JSON encoder
    print("\n1. Testing custom JSON encoder...")
    try:
        import json
        from datetime import datetime
        
        class DateTimeEncoder(json.JSONEncoder):
            def default(self, obj):
                if isinstance(obj, datetime):
                    return obj.isoformat()
                return super().default(obj)
        
        dt = datetime.now()
        data = {"timestamp": dt, "name": "test"}
        json_str = json.dumps(data, cls=DateTimeEncoder)
        print(f"   ✅ Custom encoder works: {json_str}")
        
    except Exception as e:
        print(f"   ❌ Error: {e}")
    
    # Test 2: Recursive datetime conversion
    print("\n2. Testing recursive datetime conversion...")
    try:
        def convert_datetime_to_iso(obj):
            """Recursively convert datetime objects to ISO strings."""
            if isinstance(obj, datetime):
                return obj.isoformat()
            elif isinstance(obj, dict):
                return {key: convert_datetime_to_iso(value) for key, value in obj.items()}
            elif isinstance(obj, list):
                return [convert_datetime_to_iso(item) for item in obj]
            else:
                return obj
        
        dt = datetime.now()
        data = {
            "timestamp": dt,
            "nested": {
                "created_at": dt,
                "events": [
                    {"time": dt, "name": "event1"},
                    {"time": dt, "name": "event2"}
                ]
            }
        }
        
        converted = convert_datetime_to_iso(data)
        json_str = json.dumps(converted)
        print(f"   ✅ Recursive conversion works: {json_str}")
        
    except Exception as e:
        print(f"   ❌ Error: {e}")
    
    # Test 3: Pydantic model_dump with mode
    print("\n3. Testing Pydantic model_dump with mode...")
    try:
        sys.path.insert(0, 'src')
        from pydantic import BaseModel
        from datetime import datetime
        
        class TestModel(BaseModel):
            name: str
            timestamp: datetime = Field(default_factory=datetime.now)
        
        model = TestModel(name="test")
        
        # Test different serialization modes
        json_data = model.model_dump(mode='json')
        print(f"   ✅ model_dump(mode='json'): {json_data}")
        
        json_str = model.model_dump_json()
        print(f"   ✅ model_dump_json(): {json_str}")
        
    except Exception as e:
        print(f"   ❌ Error: {e}")

def test_application_specific_datetime_issues():
    """Test application-specific datetime serialization issues."""
    print("\n🧪 Testing application-specific datetime issues...")
    
    try:
        sys.path.insert(0, 'src')
        from core.api.models.utility.response import DomainsResponse, Domain
        from datetime import datetime
        
        # Test 1: DomainsResponse serialization
        print("\n1. Testing DomainsResponse serialization...")
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
            
            # Test different serialization methods
            json_data = response.model_dump(mode='json')
            print(f"   ✅ model_dump(mode='json'): {type(json_data)}")
            
            json_str = response.model_dump_json()
            print(f"   ✅ model_dump_json(): {json_str[:100]}...")
            
            # Test if the data can be JSON serialized again
            json.dumps(json_data)
            print(f"   ✅ Double JSON serialization works")
            
        except Exception as e:
            print(f"   ❌ Error: {e}")
            traceback.print_exc()
            
    except ImportError as e:
        print(f"   ❌ Import Error: {e}")

def main():
    """Run all tests to investigate datetime serialization issues."""
    print("🔬 TDD Investigation of Datetime Serialization Issues")
    print("=" * 70)
    
    test_datetime_serialization_patterns()
    test_pydantic_datetime_handling()
    test_application_datetime_patterns()
    test_cli_datetime_patterns()
    test_datetime_serialization_strategies()
    test_application_specific_datetime_issues()
    
    print("\n" + "=" * 70)
    print("🏁 Investigation complete")

if __name__ == "__main__":
    main()
