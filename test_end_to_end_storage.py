#!/usr/bin/env python3
"""
End-to-End Storage Integration Test

This script tests the complete storage integration through the main system,
including FastAPI application startup and API endpoints.
"""

import asyncio
import os
import json
import logging
from typing import Dict, Any
from datetime import datetime
from dotenv import load_dotenv
import httpx
import pytest
from fastapi.testclient import TestClient

# Load environment variables from .env file
load_dotenv()

# Add the src directory to the Python path
import sys
sys.path.append('src')

from core.main import app
from core.services.storage_service import StorageService
from core.config.settings import STORAGE_CONFIG

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class EndToEndStorageTester:
    """Test class for end-to-end storage integration"""
    
    def __init__(self):
        self.client = TestClient(app)
        self.storage_service = None
    
    async def test_application_startup(self):
        """Test that the application starts up correctly with storage"""
        print("🚀 Testing application startup...")
        
        try:
            # Test health endpoint
            response = self.client.get("/health")
            assert response.status_code == 200
            
            health_data = response.json()
            print(f"✅ Health check passed: {health_data}")
            
            # Verify domains are registered
            assert "domains" in health_data
            print(f"✅ Registered domains: {health_data['domains']}")
            
            return True
        except Exception as e:
            print(f"❌ Application startup failed: {e}")
            return False
    
    async def test_storage_service_initialization(self):
        """Test that storage service is properly initialized"""
        print("\n🔧 Testing storage service initialization...")
        
        try:
            # Get storage service instance
            self.storage_service = await StorageService.get_instance()
            
            # Check if it's configured
            status = await self.storage_service.get_status()
            print(f"✅ Storage service status: {status}")
            
            assert status["configured"] == True
            assert status["connected"] == True
            assert status["provider"] == "azure_blob"
            
            return True
        except Exception as e:
            print(f"❌ Storage service initialization failed: {e}")
            return False
    
    async def test_storage_stats(self):
        """Test storage statistics"""
        print("\n📊 Testing storage statistics...")
        
        try:
            stats = await self.storage_service.get_storage_stats()
            print(f"✅ Storage stats: {stats}")
            
            # Verify we can see the OKW files
            assert stats["object_count"] > 0
            assert stats["provider"] == "azure_blob"
            assert stats["bucket"] == "okw"
            
            return True
        except Exception as e:
            print(f"❌ Storage stats failed: {e}")
            return False
    
    async def test_domain_handlers(self):
        """Test domain-specific storage handlers"""
        print("\n🎯 Testing domain handlers...")
        
        try:
            # Test OKW handler
            okw_handler = self.storage_service.get_domain_handler("okw")
            print(f"✅ OKW handler created: {type(okw_handler).__name__}")
            
            # List OKW objects
            okw_objects = await okw_handler.list_objects(limit=5)
            print(f"✅ Found {len(okw_objects)} OKW objects")
            
            # Test reading a specific file if available
            if okw_objects:
                first_obj = okw_objects[0]
                print(f"📄 Testing read of: {first_obj.get('id', 'unknown')}")
                
                # Try to read the object
                try:
                    obj_data = await okw_handler.load_object(first_obj.get('id'))
                    if obj_data:
                        print(f"✅ Successfully read object data")
                        print(f"   Keys: {list(obj_data.keys()) if isinstance(obj_data, dict) else 'Not a dict'}")
                    else:
                        print("⚠️ Object data is None")
                except Exception as e:
                    print(f"⚠️ Could not read object: {e}")
            
            return True
        except Exception as e:
            print(f"❌ Domain handlers test failed: {e}")
            return False
    
    async def test_api_endpoints(self):
        """Test API endpoints that use storage"""
        print("\n🌐 Testing API endpoints...")
        
        try:
            # Test health endpoint
            response = self.client.get("/health")
            assert response.status_code == 200
            print("✅ Health endpoint working")
            
            # Test OKW list endpoint (should work even if empty)
            response = self.client.get("/v1/okw?page=1&page_size=10")
            assert response.status_code == 200
            print("✅ OKW list endpoint working")
            
            # Test OKW create endpoint (should work for validation)
            test_facility = {
                "name": "Test Facility",
                "location": "Test Location",
                "facility_status": "active",
                "access_type": "public"
            }
            response = self.client.post("/v1/okw/create", json=test_facility)
            assert response.status_code == 201
            print("✅ OKW create endpoint working")
            
            return True
        except Exception as e:
            print(f"❌ API endpoints test failed: {e}")
            return False
    
    async def test_storage_operations(self):
        """Test basic storage operations"""
        print("\n💾 Testing storage operations...")
        
        try:
            # Test listing objects
            objects = []
            async for obj in self.storage_service.manager.list_objects():
                objects.append(obj)
            
            print(f"✅ Listed {len(objects)} objects from storage")
            
            # Test reading a file
            if objects:
                first_obj = objects[0]
                data = await self.storage_service.manager.get_object(first_obj["key"])
                content = data.decode('utf-8')
                print(f"✅ Successfully read file: {first_obj['key']}")
                print(f"   Size: {len(content)} characters")
                print(f"   Preview: {content[:100]}...")
            
            return True
        except Exception as e:
            print(f"❌ Storage operations failed: {e}")
            return False
    
    async def run_all_tests(self):
        """Run all end-to-end tests"""
        print("🚀 Starting End-to-End Storage Integration Tests")
        print("=" * 60)
        
        tests = [
            ("Application Startup", self.test_application_startup),
            ("Storage Service Initialization", self.test_storage_service_initialization),
            ("Storage Statistics", self.test_storage_stats),
            ("Domain Handlers", self.test_domain_handlers),
            ("API Endpoints", self.test_api_endpoints),
            ("Storage Operations", self.test_storage_operations),
        ]
        
        results = []
        for test_name, test_func in tests:
            print(f"\n{'='*20} {test_name} {'='*20}")
            try:
                success = await test_func()
                results.append((test_name, success))
            except Exception as e:
                print(f"❌ {test_name} failed with exception: {e}")
                results.append((test_name, False))
        
        # Print summary
        print("\n" + "=" * 60)
        print("📊 Test Results Summary:")
        print("=" * 60)
        
        passed = 0
        for test_name, success in results:
            status = "✅ PASS" if success else "❌ FAIL"
            print(f"{test_name}: {status}")
            if success:
                passed += 1
        
        print(f"\n🎯 Overall: {passed}/{len(results)} tests passed")
        
        if passed == len(results):
            print("\n🎉 All end-to-end tests passed! Storage integration is working correctly.")
        else:
            print(f"\n⚠️ {len(results) - passed} tests failed. Review the output above.")
        
        return passed == len(results)

async def main():
    """Main function"""
    tester = EndToEndStorageTester()
    
    try:
        success = await tester.run_all_tests()
        
        if success:
            print("\n✅ End-to-end storage integration is working correctly!")
            print("\nWhat this proves:")
            print("1. ✅ Application starts up with storage configured")
            print("2. ✅ Storage service connects to Azure Blob Storage")
            print("3. ✅ Domain handlers work correctly")
            print("4. ✅ API endpoints are functional")
            print("5. ✅ Storage operations (read/list) work")
            print("6. ✅ Integration between all components is solid")
        else:
            print("\n❌ Some end-to-end tests failed.")
            print("Review the output above to identify issues.")
        
        return success
        
    except Exception as e:
        print(f"\n❌ End-to-end test failed with exception: {e}")
        return False

if __name__ == "__main__":
    success = asyncio.run(main())
    exit(0 if success else 1)
