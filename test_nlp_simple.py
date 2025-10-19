#!/usr/bin/env python3
"""
Simple test script for NLP matching layer with synthetic data
"""
import asyncio
import json
import sys
from pathlib import Path

# Add the src directory to the path
sys.path.insert(0, str(Path(__file__).parent / "src"))

from src.core.matching.nlp_matcher import NLPMatcher


async def test_nlp_with_synthetic_data():
    """Test NLP matching with synthetic data"""
    print("=== Testing NLP Matching with Synthetic Data ===")
    
    # Load the Arduino IoT sensor node manifest
    manifest_path = Path("synth/synthetic_data/arduino-based-iot-sensor-node-1-2-4-okh.json")
    if not manifest_path.exists():
        print("Synthetic data not found, skipping test")
        return
    
    with open(manifest_path) as f:
        manifest_data = json.load(f)
    
    print(f"Loaded manifest: {manifest_data['title']}")
    
    # Extract process requirements
    processes = manifest_data.get("manufacturing_specs", {}).get("process_requirements", [])
    process_names = [p["process_name"] for p in processes]
    
    print(f"Process requirements: {process_names}")
    
    # Test NLP matching with these processes
    matcher = NLPMatcher(domain="manufacturing", similarity_threshold=0.5)
    
    # Test against some common manufacturing capabilities
    test_capabilities = [
        "PCB Assembly",
        "3D Printing", 
        "CNC Machining",
        "Laser Cutting",
        "Surface Treatment",
        "Electronics Assembly",
        "Prototyping",
        "Manufacturing"
    ]
    
    print("\nTesting semantic matching:")
    for req in process_names:
        print(f"\nTesting '{req}':")
        for cap in test_capabilities:
            similarity = await matcher.calculate_semantic_similarity(req, cap)
            if similarity > 0.3:  # Only show relevant matches
                print(f"  vs '{cap}': {similarity:.3f}")
    
    # Test full matching
    print(f"\nTesting full matching (threshold: {matcher.similarity_threshold}):")
    results = await matcher.match(process_names, test_capabilities)
    
    print(f"Found {len(results)} matches:")
    for result in results:
        if result.matched:
            print(f"  ✅ {result.requirement} -> {result.capability}: "
                  f"confidence={result.confidence:.3f}")
        else:
            print(f"  ❌ {result.requirement} -> {result.capability}: "
                  f"confidence={result.confidence:.3f}")
    
    # Cleanup
    matcher.cleanup()
    print("\nNLP matcher cleanup completed")


async def main():
    """Run the test"""
    print("NLP Matching Layer - Simple Synthetic Data Test")
    print("=" * 60)
    
    try:
        await test_nlp_with_synthetic_data()
        
        print("\n" + "=" * 60)
        print("Test completed successfully!")
        
    except Exception as e:
        print(f"\nError during testing: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(main())
