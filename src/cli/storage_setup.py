"""
Storage Setup CLI Commands

This module provides CLI commands for setting up and managing the storage system.
"""

import asyncio
from uuid import uuid4

from ..config.storage_config import create_storage_config
from ..core.storage.manager import StorageManager
from ..core.storage.organizer import StorageOrganizer
from ..core.storage.smart_discovery import SmartFileDiscovery
from ..core.services.storage_service import StorageService

from src.core.utils.logging import get_logger

logger = get_logger(__name__)

async def setup_storage_structure():
    """Set up the organized directory structure in storage"""
    try:
        # Initialize storage service with local storage
        storage_config = create_storage_config("local", "storage")
        storage_service = await StorageService.get_instance()
        await storage_service.configure(storage_config)
        
        # Create organizer
        organizer = StorageOrganizer(storage_service.manager)
        
        # Create directory structure
        result = await organizer.create_directory_structure()
        
        print("✅ Storage directory structure created successfully!")
        print(f"Created {result['total_created']} directories:")
        for directory in result['created_directories']:
            print(f"  - {directory}")
        
        return result
        
    except Exception as e:
        logger.error(f"Failed to setup storage structure: {e}")
        print(f"❌ Failed to setup storage structure: {e}")
        raise

async def test_smart_discovery():
    """Test the smart discovery system"""
    try:
        # Initialize storage service with local storage
        storage_config = create_storage_config("local", "storage")
        storage_service = await StorageService.get_instance()
        await storage_service.configure(storage_config)
        
        # Create discovery service
        discovery = SmartFileDiscovery(storage_service.manager)
        
        # Test discovery for each file type
        file_types = ['okh', 'okw', 'supply-tree']
        
        print("🔍 Testing smart discovery system...")
        
        for file_type in file_types:
            files = await discovery.discover_files(file_type)
            print(f"  {file_type}: {len(files)} files found")
            
            for file_info in files[:3]:  # Show first 3 files
                print(f"    - {file_info.key} ({file_info.size} bytes)")
        
        return True
        
    except Exception as e:
        logger.error(f"Failed to test smart discovery: {e}")
        print(f"❌ Failed to test smart discovery: {e}")
        raise

async def create_sample_data():
    """Create sample OKH and OKW data for testing"""
    try:
        # Initialize storage service with local storage
        storage_config = create_storage_config("local", "storage")
        storage_service = await StorageService.get_instance()
        await storage_service.configure(storage_config)
        
        # Create organizer
        organizer = StorageOrganizer(storage_service.manager)
        
        print("📝 Creating sample data...")
        
        # Create sample OKH manifest
        sample_okh = {
            "id": str(uuid4()),
            "title": "Sample 3D Printed Bracket",
            "version": "1.0.0",
            "license": {"hardware": "MIT", "documentation": "MIT", "software": "MIT"},
            "licensor": "Test User",
            "documentation_language": "en",
            "function": "Support bracket for mounting components",
            "description": "A simple 3D printed bracket designed for mounting electronic components",
            "keywords": ["3D printing", "bracket", "mounting", "electronics"],
            "manufacturing_processes": ["3DP"],
            "manufacturing_specs": {
                "process_requirements": [
                    {
                        "process_name": "3DP",
                        "parameters": {
                            "layer_height": "0.2mm",
                            "infill_percentage": "20%",
                            "support_material": "required"
                        },
                        "validation_criteria": {
                            "dimensional_accuracy": "±0.1mm",
                            "surface_finish": "standard"
                        },
                        "required_tools": ["3D printer"],
                        "notes": "Standard FDM 3D printing process"
                    }
                ],
                "joining_processes": [],
                "outer_dimensions": {
                    "length": 50,
                    "width": 30,
                    "height": 20,
                    "unit": "mm"
                },
                "quality_standards": ["basic"],
                "notes": "Simple bracket for prototyping"
            },
            "materials": [
                {
                    "material_id": "PLA",
                    "name": "Polylactic Acid",
                    "quantity": 10,
                    "unit": "g",
                    "notes": "Standard PLA filament"
                }
            ]
        }
        
        # Create sample OKW facility
        sample_okw = {
            "id": str(uuid4()),
            "name": "Community Makerspace",
            "location": {
                "address": {
                    "street": "123 Maker Street",
                    "city": "Tech City",
                    "state": "CA",
                    "country": "United States",
                    "postal_code": "12345"
                },
                "coordinates": {
                    "latitude": 37.7749,
                    "longitude": -122.4194
                }
            },
            "facility_status": "Active",
            "access_type": "Public",
            "description": "A community makerspace with 3D printing capabilities",
            "manufacturing_processes": ["3DP", "CNC", "Laser Cutting"],
            "equipment": [
                {
                    "name": "Prusa i3 MK3S",
                    "type": "3D Printer",
                    "capabilities": ["FDM Printing", "PLA", "ABS", "PETG"]
                },
                {
                    "name": "CNC Router",
                    "type": "CNC Machine",
                    "capabilities": ["Wood Cutting", "Plastic Cutting", "Aluminum Cutting"]
                }
            ],
            "typical_materials": ["PLA", "ABS", "Wood", "Aluminum"],
            "typical_batch_size": "1-10",
            "contact": {
                "name": "Makerspace Manager",
                "email": "manager@makerspace.com",
                "phone": "+1-555-0123"
            }
        }
        
        # Store sample data
        okh_path = await organizer.store_okh_manifest(sample_okh)
        okw_path = await organizer.store_okw_facility(sample_okw)
        
        print(f"✅ Created sample OKH manifest: {okh_path}")
        print(f"✅ Created sample OKW facility: {okw_path}")
        
        return {
            "okh_path": okh_path,
            "okw_path": okw_path,
            "okh_id": sample_okh["id"],
            "okw_id": sample_okw["id"]
        }
        
    except Exception as e:
        logger.error(f"Failed to create sample data: {e}")
        print(f"❌ Failed to create sample data: {e}")
        raise

async def test_matching_system():
    """Test the matching system with sample data"""
    try:
        print("🔗 Testing matching system...")
        
        # Test the match endpoint
        import httpx
        
        test_payload = {
            "okh_manifest": {
                "title": "Test 3D Printed Component",
                "version": "1.0.0",
                "license": {"hardware": "MIT"},
                "licensor": "Test User",
                "documentation_language": "en",
                "function": "Test component for matching",
                "manufacturing_processes": ["3DP"],
                "manufacturing_specs": {
                    "process_requirements": [
                        {
                            "process_name": "3DP",
                            "parameters": {}
                        }
                    ]
                }
            }
        }
        
        async with httpx.AsyncClient() as client:
            response = await client.post(
                "http://localhost:8001/v1/match",
                json=test_payload,
                timeout=30.0
            )
            
            if response.status_code == 200:
                result = response.json()
                print(f"✅ Matching system working! Found {result['data']['total_solutions']} solutions")
                print(f"   Processing time: {result['data']['processing_time']:.3f}s")
                print(f"   Matching metrics: {result['data']['matching_metrics']}")
                return True
            else:
                print(f"❌ Matching system failed: {response.status_code} - {response.text}")
                return False
                
    except Exception as e:
        logger.error(f"Failed to test matching system: {e}")
        print(f"❌ Failed to test matching system: {e}")
        return False

async def main():
    """Main setup function"""
    print("🚀 Setting up Supply Graph AI Storage System")
    print("=" * 50)
    
    try:
        # Step 1: Setup directory structure
        print("\n1. Setting up directory structure...")
        await setup_storage_structure()
        
        # Step 2: Test smart discovery
        print("\n2. Testing smart discovery...")
        await test_smart_discovery()
        
        # Step 3: Create sample data
        print("\n3. Creating sample data...")
        sample_data = await create_sample_data()
        
        # Step 4: Test smart discovery with data
        print("\n4. Testing smart discovery with sample data...")
        await test_smart_discovery()
        
        # Step 5: Test matching system
        print("\n5. Testing matching system...")
        matching_success = await test_matching_system()
        
        print("\n" + "=" * 50)
        if matching_success:
            print("🎉 Storage system setup completed successfully!")
            print("✅ Directory structure created")
            print("✅ Smart discovery working")
            print("✅ Sample data created")
            print("✅ Matching system working")
        else:
            print("⚠️  Storage system setup completed with issues")
            print("✅ Directory structure created")
            print("✅ Smart discovery working")
            print("✅ Sample data created")
            print("❌ Matching system needs attention")
        
    except Exception as e:
        print(f"\n❌ Setup failed: {e}")
        raise

if __name__ == "__main__":
    asyncio.run(main())
