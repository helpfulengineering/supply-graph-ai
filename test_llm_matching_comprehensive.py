#!/usr/bin/env python3
"""
Comprehensive LLM Matching Layer Test with Synthetic Data

This script tests the LLM matching layer using real synthetic OKH and OKW data
to validate the matching system's performance with realistic scenarios.
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
from src.core.matching.layers.base import MatchingLayer, MatchQuality


class SyntheticDataLoader:
    """Loads and processes synthetic OKH and OKW data for testing."""
    
    def __init__(self, data_dir: str = "synth/synthetic_data"):
        self.data_dir = Path(data_dir)
        self.okh_files = []
        self.okw_files = []
        self._load_data_files()
    
    def _load_data_files(self):
        """Load all OKH and OKW files from the data directory."""
        if not self.data_dir.exists():
            print(f"❌ Data directory not found: {self.data_dir}")
            return
        
        # Find all OKH and OKW files
        for file_path in self.data_dir.glob("*.json"):
            if file_path.name.endswith("-okh.json"):
                self.okh_files.append(file_path)
            elif file_path.name.endswith("-okw.json"):
                self.okw_files.append(file_path)
        
        print(f"📁 Found {len(self.okh_files)} OKH files and {len(self.okw_files)} OKW files")
    
    def load_okh_manifest(self, file_path: Path) -> Dict[str, Any]:
        """Load an OKH manifest from file."""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception as e:
            print(f"❌ Error loading OKH file {file_path}: {e}")
            return {}
    
    def load_okw_facility(self, file_path: Path) -> Dict[str, Any]:
        """Load an OKW facility from file."""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception as e:
            print(f"❌ Error loading OKW file {file_path}: {e}")
            return {}
    
    def extract_requirements_from_okh(self, okh_data: Dict[str, Any]) -> List[str]:
        """Extract manufacturing requirements from OKH manifest."""
        requirements = []
        
        # Extract manufacturing processes
        if "manufacturing_processes" in okh_data:
            for process in okh_data["manufacturing_processes"]:
                if isinstance(process, str):
                    requirements.append(process)
                elif isinstance(process, dict) and "process_name" in process:
                    requirements.append(process["process_name"])
        
        # Extract material requirements
        if "materials" in okh_data:
            for material in okh_data["materials"]:
                if isinstance(material, dict):
                    if "name" in material:
                        requirements.append(f"Material: {material['name']}")
                    elif "material_id" in material:
                        requirements.append(f"Material: {material['material_id']}")
        
        # Extract tool requirements
        if "tool_list" in okh_data:
            for tool in okh_data["tool_list"]:
                if isinstance(tool, str):
                    requirements.append(f"Tool: {tool}")
        
        # Extract manufacturing specifications
        if "manufacturing_specs" in okh_data:
            mfg_specs = okh_data["manufacturing_specs"]
            if isinstance(mfg_specs, dict):
                # Extract process requirements
                if "process_requirements" in mfg_specs:
                    for proc_req in mfg_specs["process_requirements"]:
                        if isinstance(proc_req, dict) and "process_name" in proc_req:
                            requirements.append(proc_req["process_name"])
                
                # Extract quality standards
                if "quality_standards" in mfg_specs:
                    for standard in mfg_specs["quality_standards"]:
                        if isinstance(standard, str):
                            requirements.append(f"Quality: {standard}")
        
        return requirements
    
    def extract_capabilities_from_okw(self, okw_data: Dict[str, Any]) -> List[str]:
        """Extract manufacturing capabilities from OKW facility."""
        capabilities = []
        
        # Extract manufacturing processes
        if "manufacturing_processes" in okw_data:
            for process in okw_data["manufacturing_processes"]:
                if isinstance(process, str):
                    # Extract process name from Wikipedia URL
                    if "wikipedia.org/wiki/" in process:
                        process_name = process.split("/wiki/")[-1].replace("_", " ").title()
                        capabilities.append(process_name)
                    else:
                        capabilities.append(process)
        
        # Extract equipment capabilities
        if "equipment" in okw_data:
            for equipment in okw_data["equipment"]:
                if isinstance(equipment, dict):
                    # Extract equipment type
                    if "equipment_type" in equipment:
                        eq_type = equipment["equipment_type"]
                        if "wikipedia.org/wiki/" in eq_type:
                            eq_name = eq_type.split("/wiki/")[-1].replace("_", " ").title()
                            capabilities.append(eq_name)
                        else:
                            capabilities.append(eq_type)
                    
                    # Extract manufacturing process from equipment
                    if "manufacturing_process" in equipment:
                        process = equipment["manufacturing_process"]
                        if "wikipedia.org/wiki/" in process:
                            process_name = process.split("/wiki/")[-1].replace("_", " ").title()
                            capabilities.append(process_name)
                        else:
                            capabilities.append(process)
                    
                    # Extract materials worked
                    if "materials_worked" in equipment:
                        for material in equipment["materials_worked"]:
                            if isinstance(material, dict) and "material_type" in material:
                                mat_type = material["material_type"]
                                if "wikipedia.org/wiki/" in mat_type:
                                    mat_name = mat_type.split("/wiki/")[-1].replace("_", " ").title()
                                    capabilities.append(f"Material: {mat_name}")
                                else:
                                    capabilities.append(f"Material: {mat_type}")
        
        # Extract batch size capabilities
        if "typical_batch_size" in okw_data:
            batch_size = okw_data["typical_batch_size"]
            if isinstance(batch_size, str):
                capabilities.append(f"Batch size: {batch_size}")
        
        # Extract certifications
        if "certifications" in okw_data:
            for cert in okw_data["certifications"]:
                if isinstance(cert, str):
                    capabilities.append(f"Certification: {cert}")
        
        return capabilities


class LLMMatchingTester:
    """Comprehensive tester for LLM matching layer."""
    
    def __init__(self, data_loader: SyntheticDataLoader):
        self.data_loader = data_loader
        self.matcher = None
        self.test_results = []
    
    async def initialize_matcher(self, domain: str = "manufacturing", preserve_context: bool = True):
        """Initialize the LLM matcher."""
        print("🔧 Initializing LLM Matcher...")
        self.matcher = LLMMatcher(domain=domain, preserve_context=preserve_context)
        print("✅ LLM Matcher initialized")
    
    async def test_single_okh_okw_pair(self, okh_file: Path, okw_file: Path) -> Dict[str, Any]:
        """Test matching between a single OKH manifest and OKW facility."""
        print(f"\n🧪 Testing: {okh_file.name} vs {okw_file.name}")
        
        # Load data
        okh_data = self.data_loader.load_okh_manifest(okh_file)
        okw_data = self.data_loader.load_okw_facility(okw_file)
        
        if not okh_data or not okw_data:
            return {"error": "Failed to load data"}
        
        # Extract requirements and capabilities
        requirements = self.data_loader.extract_requirements_from_okh(okh_data)
        capabilities = self.data_loader.extract_capabilities_from_okw(okw_data)
        
        print(f"   📋 Requirements: {len(requirements)} items")
        print(f"   🏭 Capabilities: {len(capabilities)} items")
        
        if not requirements or not capabilities:
            return {"error": "No requirements or capabilities found"}
        
        # Run matching
        start_time = time.time()
        try:
            results = await self.matcher.match(requirements, capabilities)
            processing_time = time.time() - start_time
            
            # Analyze results
            matches = [r for r in results if r.matched]
            total_matches = len(matches)
            avg_confidence = sum(r.confidence for r in matches) / len(matches) if matches else 0
            
            # Get quality distribution
            quality_dist = {}
            for result in results:
                quality = result.metadata.quality.value
                quality_dist[quality] = quality_dist.get(quality, 0) + 1
            
            test_result = {
                "okh_file": okh_file.name,
                "okw_file": okw_file.name,
                "okh_title": okh_data.get("title", "Unknown"),
                "okw_name": okw_data.get("name", "Unknown"),
                "requirements_count": len(requirements),
                "capabilities_count": len(capabilities),
                "total_results": len(results),
                "matches_found": total_matches,
                "match_rate": total_matches / len(results) if results else 0,
                "avg_confidence": avg_confidence,
                "processing_time": processing_time,
                "quality_distribution": quality_dist,
                "sample_matches": [
                    {
                        "requirement": r.requirement,
                        "capability": r.capability,
                        "confidence": r.confidence,
                        "quality": r.metadata.quality.value,
                        "reasons": r.metadata.reasons
                    }
                    for r in matches[:5]  # Top 5 matches
                ]
            }
            
            print(f"   ✅ Found {total_matches} matches ({total_matches/len(results)*100:.1f}% match rate)")
            print(f"   ⏱️  Processing time: {processing_time:.2f}s")
            print(f"   📊 Average confidence: {avg_confidence:.3f}")
            
            return test_result
            
        except Exception as e:
            print(f"   ❌ Matching failed: {e}")
            return {"error": str(e)}
    
    async def test_comprehensive_matching(self, max_tests: int = 10) -> List[Dict[str, Any]]:
        """Run comprehensive matching tests."""
        print("🚀 Starting Comprehensive LLM Matching Tests")
        print("=" * 60)
        
        if not self.matcher:
            await self.initialize_matcher()
        
        test_results = []
        test_count = 0
        
        # Test combinations of OKH and OKW files
        for okh_file in self.data_loader.okh_files[:5]:  # Limit to first 5 OKH files
            if test_count >= max_tests:
                break
                
            for okw_file in self.data_loader.okw_files[:3]:  # Limit to first 3 OKW files per OKH
                if test_count >= max_tests:
                    break
                
                result = await self.test_single_okh_okw_pair(okh_file, okw_file)
                if "error" not in result:
                    test_results.append(result)
                
                test_count += 1
                
                # Add delay between tests to avoid overwhelming the API
                await asyncio.sleep(2)
        
        return test_results
    
    def analyze_results(self, results: List[Dict[str, Any]]):
        """Analyze and summarize test results."""
        if not results:
            print("❌ No results to analyze")
            return
        
        print("\n📊 Test Results Analysis")
        print("=" * 60)
        
        # Overall statistics
        total_tests = len(results)
        total_matches = sum(r["matches_found"] for r in results)
        total_results = sum(r["total_results"] for r in results)
        avg_processing_time = sum(r["processing_time"] for r in results) / total_tests
        avg_confidence = sum(r["avg_confidence"] for r in results) / total_tests
        
        print(f"📈 Overall Statistics:")
        print(f"   Total tests: {total_tests}")
        print(f"   Total matches found: {total_matches}")
        print(f"   Total requirement-capability pairs: {total_results}")
        print(f"   Overall match rate: {total_matches/total_results*100:.1f}%")
        print(f"   Average processing time: {avg_processing_time:.2f}s")
        print(f"   Average confidence: {avg_confidence:.3f}")
        
        # Quality distribution
        quality_dist = {}
        for result in results:
            for quality, count in result["quality_distribution"].items():
                quality_dist[quality] = quality_dist.get(quality, 0) + count
        
        print(f"\n🎯 Quality Distribution:")
        for quality, count in sorted(quality_dist.items()):
            percentage = count / total_results * 100
            print(f"   {quality}: {count} ({percentage:.1f}%)")
        
        # Best performing tests
        print(f"\n🏆 Best Performing Tests:")
        sorted_results = sorted(results, key=lambda x: x["match_rate"], reverse=True)
        for i, result in enumerate(sorted_results[:3]):
            print(f"   {i+1}. {result['okh_title']} vs {result['okw_name']}")
            print(f"      Match rate: {result['match_rate']*100:.1f}%")
            print(f"      Confidence: {result['avg_confidence']:.3f}")
            print(f"      Time: {result['processing_time']:.2f}s")
        
        # Sample matches
        print(f"\n💡 Sample High-Confidence Matches:")
        all_matches = []
        for result in results:
            all_matches.extend(result["sample_matches"])
        
        high_conf_matches = [m for m in all_matches if m["confidence"] > 0.7]
        for i, match in enumerate(high_conf_matches[:5]):
            print(f"   {i+1}. {match['requirement']} ↔ {match['capability']}")
            print(f"      Confidence: {match['confidence']:.3f} ({match['quality']})")
            print(f"      Reasons: {', '.join(match['reasons'][:2])}")
    
    async def test_specific_scenarios(self):
        """Test specific matching scenarios."""
        print("\n🎯 Testing Specific Scenarios")
        print("=" * 60)
        
        # Scenario 1: 3D Printing requirements
        print("Scenario 1: 3D Printing Requirements")
        requirements_3dp = [
            "3D printing",
            "PLA material",
            "Layer height 0.2mm",
            "Support structures"
        ]
        capabilities_3dp = [
            "3D printer",
            "Fused deposition modeling",
            "PLA filament",
            "Build plate"
        ]
        
        results = await self.matcher.match(requirements_3dp, capabilities_3dp)
        matches = [r for r in results if r.matched]
        print(f"   3D Printing matches: {len(matches)}/{len(results)}")
        for match in matches[:3]:
            print(f"   ✅ {match.requirement} ↔ {match.capability} ({match.confidence:.3f})")
        
        # Scenario 2: CNC Machining requirements
        print("\nScenario 2: CNC Machining Requirements")
        requirements_cnc = [
            "CNC machining",
            "Aluminum 6061",
            "Tolerance ±0.01mm",
            "Surface finish Ra 1.6μm"
        ]
        capabilities_cnc = [
            "CNC mill",
            "Computer numerical control",
            "Aluminum",
            "Precision machining"
        ]
        
        results = await self.matcher.match(requirements_cnc, capabilities_cnc)
        matches = [r for r in results if r.matched]
        print(f"   CNC Machining matches: {len(matches)}/{len(results)}")
        for match in matches[:3]:
            print(f"   ✅ {match.requirement} ↔ {match.capability} ({match.confidence:.3f})")


async def main():
    """Main test function."""
    print("🧪 Comprehensive LLM Matching Layer Test")
    print("=" * 60)
    
    # Check API key
    if not os.getenv('ANTHROPIC_API_KEY'):
        print("⚠️  Warning: ANTHROPIC_API_KEY not found in environment")
        print("   LLM matching will fail without a valid API key")
        print("   Set ANTHROPIC_API_KEY in your .env file or environment")
        print()
    
    # Initialize data loader
    data_loader = SyntheticDataLoader()
    if not data_loader.okh_files or not data_loader.okw_files:
        print("❌ No synthetic data files found. Please run the data generator first.")
        return
    
    # Initialize tester
    tester = LLMMatchingTester(data_loader)
    
    try:
        # Run comprehensive tests
        print("🚀 Running comprehensive matching tests...")
        results = await tester.test_comprehensive_matching(max_tests=6)
        
        # Analyze results
        tester.analyze_results(results)
        
        # Test specific scenarios
        await tester.test_specific_scenarios()
        
        print("\n🎉 Comprehensive testing completed!")
        
    except Exception as e:
        print(f"❌ Test failed: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(main())
