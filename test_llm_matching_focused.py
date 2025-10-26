#!/usr/bin/env python3
"""
Focused LLM Matching Test with Synthetic Data

This script runs focused tests on specific scenarios identified from the synthetic data analysis.
"""

import asyncio
import json
import os
import sys
import time
from pathlib import Path
from typing import List, Dict, Any
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# Add the project root to the Python path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from src.core.matching.llm_matcher import LLMMatcher


async def test_scenario(scenario_name: str, requirements: List[str], capabilities: List[str], expected_confidence: str):
    """Test a specific matching scenario."""
    print(f"\n🧪 Testing: {scenario_name}")
    print(f"   Expected: {expected_confidence}")
    print(f"   Requirements: {requirements}")
    print(f"   Capabilities: {capabilities}")
    
    # Initialize matcher
    matcher = LLMMatcher(domain="manufacturing", preserve_context=True)
    
    # Run matching with timeout
    try:
        start_time = time.time()
        results = await asyncio.wait_for(
            matcher.match(requirements, capabilities), 
            timeout=30.0
        )
        processing_time = time.time() - start_time
        
        # Analyze results
        matches = [r for r in results if r.matched]
        total_matches = len(matches)
        avg_confidence = sum(r.confidence for r in matches) / len(matches) if matches else 0
        
        print(f"   ✅ Results: {total_matches}/{len(results)} matches")
        print(f"   📊 Average confidence: {avg_confidence:.3f}")
        print(f"   ⏱️  Processing time: {processing_time:.2f}s")
        
        # Show top matches
        if matches:
            print(f"   🏆 Top matches:")
            for i, match in enumerate(matches[:3]):
                print(f"      {i+1}. {match.requirement} ↔ {match.capability}")
                print(f"         Confidence: {match.confidence:.3f} ({match.metadata.quality.value})")
                print(f"         Reasons: {', '.join(match.metadata.reasons[:2])}")
        
        return {
            "scenario": scenario_name,
            "matches_found": total_matches,
            "total_pairs": len(results),
            "match_rate": total_matches / len(results) if results else 0,
            "avg_confidence": avg_confidence,
            "processing_time": processing_time,
            "success": True
        }
        
    except asyncio.TimeoutError:
        print(f"   ⏰ Timeout after 30 seconds")
        return {
            "scenario": scenario_name,
            "success": False,
            "error": "Timeout"
        }
    except Exception as e:
        print(f"   ❌ Error: {e}")
        return {
            "scenario": scenario_name,
            "success": False,
            "error": str(e)
        }


async def test_real_data_scenario():
    """Test with actual synthetic data files."""
    print(f"\n🎯 Testing with Real Synthetic Data")
    print("=" * 50)
    
    # Load a specific OKH and OKW file
    data_dir = Path("synth/synthetic_data")
    
    # Find an OKH file
    okh_files = list(data_dir.glob("*-okh.json"))
    if not okh_files:
        print("❌ No OKH files found")
        return
    
    # Find an OKW file
    okw_files = list(data_dir.glob("*-okw.json"))
    if not okw_files:
        print("❌ No OKW files found")
        return
    
    # Load OKH data
    okh_file = okh_files[0]  # Use first OKH file
    with open(okh_file, 'r') as f:
        okh_data = json.load(f)
    
    # Load OKW data
    okw_file = okw_files[0]  # Use first OKW file
    with open(okw_file, 'r') as f:
        okw_data = json.load(f)
    
    print(f"📄 OKH: {okh_data.get('title', 'Unknown')}")
    print(f"🏭 OKW: {okw_data.get('name', 'Unknown')}")
    
    # Extract requirements and capabilities (simplified)
    requirements = []
    capabilities = []
    
    # Extract from OKH
    if "manufacturing_processes" in okh_data:
        requirements.extend(okh_data["manufacturing_processes"])
    
    # Extract from OKW
    if "equipment" in okw_data:
        for equipment in okw_data["equipment"]:
            if "equipment_type" in equipment:
                eq_type = equipment["equipment_type"]
                if "wikipedia.org/wiki/" in eq_type:
                    eq_name = eq_type.split("/wiki/")[-1].replace("_", " ").title()
                    capabilities.append(eq_name)
    
    if not requirements or not capabilities:
        print("❌ No requirements or capabilities found")
        return
    
    # Test with real data
    matcher = LLMMatcher(domain="manufacturing", preserve_context=True)
    
    try:
        start_time = time.time()
        results = await asyncio.wait_for(
            matcher.match(requirements[:5], capabilities[:5]),  # Limit to 5 each
            timeout=45.0
        )
        processing_time = time.time() - start_time
        
        matches = [r for r in results if r.matched]
        print(f"✅ Real data test: {len(matches)}/{len(results)} matches")
        print(f"📊 Processing time: {processing_time:.2f}s")
        
        if matches:
            print(f"🏆 Sample matches:")
            for i, match in enumerate(matches[:3]):
                print(f"   {i+1}. {match.requirement} ↔ {match.capability}")
                print(f"      Confidence: {match.confidence:.3f}")
        
    except asyncio.TimeoutError:
        print("⏰ Real data test timed out")
    except Exception as e:
        print(f"❌ Real data test failed: {e}")


async def main():
    """Main test function."""
    print("🧪 Focused LLM Matching Test")
    print("=" * 60)
    
    # Check API key
    if not os.getenv('ANTHROPIC_API_KEY'):
        print("⚠️  Warning: ANTHROPIC_API_KEY not found in environment")
        print("   LLM matching will fail without a valid API key")
        print("   Set ANTHROPIC_API_KEY in your .env file or environment")
        print()
    
    # Define test scenarios based on analysis
    scenarios = [
        {
            "name": "3D Printing Match",
            "requirements": ["3DP", "PLA material", "Layer height 0.2mm"],
            "capabilities": ["3D Printer", "Fused deposition modeling", "PLA filament"],
            "expected": "High confidence (0.8-0.9)"
        },
        {
            "name": "CNC Machining Match",
            "requirements": ["CNC", "Aluminum 6061", "Tolerance ±0.01mm"],
            "capabilities": ["Cnc Mill", "Computer numerical control", "Aluminum"],
            "expected": "High confidence (0.7-0.9)"
        },
        {
            "name": "Material Substitution",
            "requirements": ["Material: Hardwood", "Wood processing"],
            "capabilities": ["Material: Aluminum", "Metal processing"],
            "expected": "Medium confidence (0.4-0.7)"
        },
        {
            "name": "Challenging Match",
            "requirements": ["LASER cutting", "Acrylic sheet"],
            "capabilities": ["Pick And Place", "Electronics assembly"],
            "expected": "Low confidence (0.2-0.5)"
        }
    ]
    
    results = []
    
    # Test each scenario
    for scenario in scenarios:
        result = await test_scenario(
            scenario["name"],
            scenario["requirements"],
            scenario["capabilities"],
            scenario["expected"]
        )
        results.append(result)
        
        # Add delay between tests
        await asyncio.sleep(3)
    
    # Test with real data
    await test_real_data_scenario()
    
    # Summary
    print(f"\n📊 Test Summary")
    print("=" * 60)
    
    successful_tests = [r for r in results if r.get("success", False)]
    failed_tests = [r for r in results if not r.get("success", False)]
    
    print(f"✅ Successful tests: {len(successful_tests)}")
    print(f"❌ Failed tests: {len(failed_tests)}")
    
    if successful_tests:
        avg_confidence = sum(r["avg_confidence"] for r in successful_tests) / len(successful_tests)
        avg_time = sum(r["processing_time"] for r in successful_tests) / len(successful_tests)
        print(f"📈 Average confidence: {avg_confidence:.3f}")
        print(f"⏱️  Average processing time: {avg_time:.2f}s")
    
    if failed_tests:
        print(f"\n❌ Failed tests:")
        for test in failed_tests:
            print(f"   - {test['scenario']}: {test.get('error', 'Unknown error')}")
    
    print(f"\n🎉 Focused testing completed!")


if __name__ == "__main__":
    asyncio.run(main())
