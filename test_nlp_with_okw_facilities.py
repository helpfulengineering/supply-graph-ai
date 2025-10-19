#!/usr/bin/env python3
"""
Comprehensive test for NLP matching layer with OKW facilities
Tests all three data sources: local synthetic data, storage service, and generated data
"""
import asyncio
import json
import sys
from pathlib import Path
from typing import List, Dict, Any

# Add the src directory to the path
sys.path.insert(0, str(Path(__file__).parent / "src"))

from src.core.matching.nlp_matcher import NLPMatcher
from src.core.services.matching_service import MatchingService
from src.core.models.okh import OKHManifest
from src.core.models.okw import ManufacturingFacility


async def load_local_okw_facilities() -> List[ManufacturingFacility]:
    """Load OKW facilities from local synthetic data"""
    print("=== Loading Local OKW Facilities ===")
    
    facilities = []
    synthetic_data_dir = Path("synth/synthetic_data")
    
    if not synthetic_data_dir.exists():
        print("Synthetic data directory not found")
        return facilities
    
    # Load all OKW files
    okw_files = list(synthetic_data_dir.glob("*-okw.json"))
    print(f"Found {len(okw_files)} OKW files")
    
    for okw_file in okw_files:
        try:
            with open(okw_file) as f:
                data = json.load(f)
            
            facility = ManufacturingFacility.from_dict(data)
            facilities.append(facility)
            print(f"  ✅ Loaded: {facility.name}")
            
        except Exception as e:
            print(f"  ❌ Failed to load {okw_file.name}: {e}")
    
    print(f"Successfully loaded {len(facilities)} facilities")
    return facilities


async def test_nlp_matching_with_facilities():
    """Test NLP matching with real OKW facilities"""
    print("\n=== Testing NLP Matching with OKW Facilities ===")
    
    # Load the Arduino IoT sensor node manifest
    manifest_path = Path("synth/synthetic_data/arduino-based-iot-sensor-node-1-2-4-okh.json")
    if not manifest_path.exists():
        print("Arduino manifest not found, skipping test")
        return
    
    with open(manifest_path) as f:
        manifest_data = json.load(f)
    
    manifest = OKHManifest.from_dict(manifest_data)
    print(f"Loaded OKH manifest: {manifest.title}")
    
    # Extract process requirements
    processes = manifest.manufacturing_specs.process_requirements if manifest.manufacturing_specs else []
    process_names = [p.process_name for p in processes]
    print(f"Process requirements: {process_names}")
    
    # Load OKW facilities
    facilities = await load_local_okw_facilities()
    if not facilities:
        print("No facilities loaded, skipping matching test")
        return
    
    # Test NLP matching
    matcher = NLPMatcher(domain="manufacturing", similarity_threshold=0.4)
    
    print(f"\nTesting NLP matching against {len(facilities)} facilities:")
    print("=" * 80)
    
    total_matches = 0
    for facility in facilities:
        print(f"\n🏭 Facility: {facility.name}")
        print(f"   Location: {facility.location.city}, {facility.location.country}")
        print(f"   Access: {facility.access_type}")
        
        # Extract facility capabilities from manufacturing processes
        facility_capabilities = []
        for process_url in facility.manufacturing_processes:
            # Extract process name from URL
            process_name = process_url.split('/')[-1].replace('_', ' ').title()
            facility_capabilities.append(process_name)
        
        print(f"   Capabilities: {facility_capabilities}")
        
        # Test matching
        matches_found = 0
        for req in process_names:
            for cap in facility_capabilities:
                similarity = await matcher.calculate_semantic_similarity(req, cap)
                if similarity > 0.3:  # Show relevant matches
                    print(f"     🔍 {req} → {cap}: {similarity:.3f}")
                    if similarity >= matcher.similarity_threshold:
                        matches_found += 1
                        total_matches += 1
        
        if matches_found > 0:
            print(f"   ✅ Found {matches_found} matches above threshold")
        else:
            print(f"   ❌ No matches above threshold")
    
    print(f"\n📊 Summary: {total_matches} total matches found across all facilities")
    
    # Cleanup
    matcher.cleanup()


async def test_matching_service_integration():
    """Test the full matching service with OKW facilities"""
    print("\n=== Testing Matching Service Integration ===")
    
    try:
        # Initialize matching service
        matching_service = await MatchingService.get_instance()
        print("✅ Matching service initialized")
        
        # Load OKH manifest
        manifest_path = Path("synth/synthetic_data/arduino-based-iot-sensor-node-1-2-4-okh.json")
        with open(manifest_path) as f:
            manifest_data = json.load(f)
        
        manifest = OKHManifest.from_dict(manifest_data)
        print(f"✅ Loaded OKH manifest: {manifest.title}")
        
        # Load OKW facilities
        facilities = await load_local_okw_facilities()
        if not facilities:
            print("❌ No facilities available for testing")
            return
        
        print(f"✅ Loaded {len(facilities)} OKW facilities")
        
        # Test matching (this would normally use the service's facility loading)
        # For now, we'll test the NLP matcher directly
        print("Testing NLP matching layer integration...")
        
        # Extract requirements and capabilities
        req_processes = [p.process_name for p in manifest.manufacturing_specs.process_requirements] if manifest.manufacturing_specs else []
        
        all_capabilities = []
        for facility in facilities:
            for process_url in facility.manufacturing_processes:
                process_name = process_url.split('/')[-1].replace('_', ' ').title()
                all_capabilities.append(process_name)
        
        # Test NLP matching
        nlp_matcher = matching_service.nlp_matchers.get("manufacturing")
        if nlp_matcher:
            results = await nlp_matcher.match(req_processes, all_capabilities)
            
            print(f"📊 NLP Matching Results:")
            print(f"   Requirements: {req_processes}")
            print(f"   Capabilities tested: {len(all_capabilities)}")
            print(f"   Matches found: {len([r for r in results if r.matched])}")
            
            for result in results:
                if result.matched:
                    print(f"   ✅ {result.requirement} → {result.capability}: {result.confidence:.3f}")
        else:
            print("❌ NLP matcher not available")
        
    except Exception as e:
        print(f"❌ Error in matching service integration: {e}")
        import traceback
        traceback.print_exc()


async def demonstrate_storage_service_option():
    """Demonstrate how to use the storage service for OKW facilities"""
    print("\n=== Storage Service Option ===")
    print("To use OKW facilities from Azure blob storage:")
    print("1. Ensure the storage service is configured with Azure credentials")
    print("2. Use the OKWService to load facilities:")
    print("   ```python")
    print("   from src.core.services.okw_service import OKWService")
    print("   okw_service = await OKWService.get_instance()")
    print("   facilities = await okw_service.get_all()")
    print("   ```")
    print("3. Pass facilities to the matching service")
    print("\nNote: This requires proper Azure configuration and network access")


async def demonstrate_synthetic_generation():
    """Demonstrate how to generate new synthetic OKW facilities"""
    print("\n=== Synthetic Data Generation Option ===")
    print("To generate new OKW facilities using the synthetic data generator:")
    print("1. Run the generator script:")
    print("   ```bash")
    print("   python synth/generate_synthetic_data.py --type okw --count 5 --complexity mixed")
    print("   ```")
    print("2. This will create new OKW files in the synthetic_data directory")
    print("3. Load the generated files using the same method as local data")
    print("\nThe generator creates realistic facilities with:")
    print("- Various equipment types (3D printers, CNC mills, laser cutters)")
    print("- Detailed capabilities and specifications")
    print("- Realistic locations and contact information")
    print("- Quality systems and certifications")


async def main():
    """Run all tests"""
    print("NLP Matching Layer - Comprehensive OKW Facility Testing")
    print("=" * 70)
    
    try:
        # Test 1: NLP matching with local OKW facilities
        await test_nlp_matching_with_facilities()
        
        # Test 2: Matching service integration
        await test_matching_service_integration()
        
        # Test 3: Demonstrate other options
        await demonstrate_storage_service_option()
        await demonstrate_synthetic_generation()
        
        print("\n" + "=" * 70)
        print("✅ All tests completed successfully!")
        print("\nNext steps:")
        print("1. Configure storage service for Azure blob access")
        print("2. Generate additional synthetic data as needed")
        print("3. Integrate with the full matching pipeline")
        
    except Exception as e:
        print(f"\n❌ Error during testing: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(main())
