#!/usr/bin/env python3
"""
Synthetic Data Analysis for LLM Matching Layer

This script analyzes the synthetic data to understand what requirements and capabilities
are available for testing, without making actual LLM API calls.
"""

import json
import os
import sys
from pathlib import Path
from collections import Counter
from typing import List, Dict, Any, Set

# Add the project root to the Python path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))


class SyntheticDataAnalyzer:
    """Analyzes synthetic OKH and OKW data to understand available test scenarios."""
    
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
    
    def load_json_file(self, file_path: Path) -> Dict[str, Any]:
        """Load a JSON file."""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception as e:
            print(f"❌ Error loading file {file_path}: {e}")
            return {}
    
    def extract_requirements_from_okh(self, okh_data: Dict[str, Any]) -> List[str]:
        """Extract manufacturing requirements from OKH manifest."""
        requirements = []
        
        # Extract manufacturing processes
        if "manufacturing_processes" in okh_data:
            for process in okh_data["manufacturing_processes"]:
                if isinstance(process, str):
                    requirements.append(process)
        
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
    
    def analyze_all_data(self):
        """Analyze all synthetic data to understand available test scenarios."""
        print("🔍 Analyzing Synthetic Data")
        print("=" * 60)
        
        all_requirements = []
        all_capabilities = []
        okh_summaries = []
        okw_summaries = []
        
        # Analyze OKH files
        print("📋 Analyzing OKH Manifests:")
        for okh_file in self.okh_files:
            okh_data = self.load_json_file(okh_file)
            if not okh_data:
                continue
            
            requirements = self.extract_requirements_from_okh(okh_data)
            all_requirements.extend(requirements)
            
            okh_summary = {
                "file": okh_file.name,
                "title": okh_data.get("title", "Unknown"),
                "requirements_count": len(requirements),
                "requirements": requirements[:5]  # First 5 requirements
            }
            okh_summaries.append(okh_summary)
            
            print(f"   📄 {okh_data.get('title', 'Unknown')}")
            print(f"      Requirements: {len(requirements)}")
            print(f"      Sample: {', '.join(requirements[:3])}")
        
        # Analyze OKW files
        print(f"\n🏭 Analyzing OKW Facilities:")
        for okw_file in self.okw_files:
            okw_data = self.load_json_file(okw_file)
            if not okw_data:
                continue
            
            capabilities = self.extract_capabilities_from_okw(okw_data)
            all_capabilities.extend(capabilities)
            
            okw_summary = {
                "file": okw_file.name,
                "name": okw_data.get("name", "Unknown"),
                "capabilities_count": len(capabilities),
                "capabilities": capabilities[:5]  # First 5 capabilities
            }
            okw_summaries.append(okw_summary)
            
            print(f"   🏢 {okw_data.get('name', 'Unknown')}")
            print(f"      Capabilities: {len(capabilities)}")
            print(f"      Sample: {', '.join(capabilities[:3])}")
        
        # Analyze patterns
        print(f"\n📊 Data Analysis Summary:")
        print(f"   Total OKH manifests: {len(okh_summaries)}")
        print(f"   Total OKW facilities: {len(okw_summaries)}")
        print(f"   Total requirements: {len(all_requirements)}")
        print(f"   Total capabilities: {len(all_capabilities)}")
        
        # Most common requirements
        req_counter = Counter(all_requirements)
        print(f"\n🔝 Most Common Requirements:")
        for req, count in req_counter.most_common(10):
            print(f"   {req}: {count} occurrences")
        
        # Most common capabilities
        cap_counter = Counter(all_capabilities)
        print(f"\n🔝 Most Common Capabilities:")
        for cap, count in cap_counter.most_common(10):
            print(f"   {cap}: {count} occurrences")
        
        # Identify potential matches
        print(f"\n🎯 Potential High-Confidence Matches:")
        potential_matches = []
        
        # Look for direct matches
        req_set = set(all_requirements)
        cap_set = set(all_capabilities)
        direct_matches = req_set.intersection(cap_set)
        
        if direct_matches:
            print(f"   Direct matches found: {len(direct_matches)}")
            for match in list(direct_matches)[:5]:
                print(f"   ✅ {match}")
        
        # Look for semantic matches (simple keyword matching)
        semantic_matches = []
        for req in req_counter.most_common(20):
            req_text = req[0].lower()
            for cap in cap_counter.most_common(20):
                cap_text = cap[0].lower()
                
                # Simple keyword matching
                req_words = set(req_text.split())
                cap_words = set(cap_text.split())
                common_words = req_words.intersection(cap_words)
                
                if len(common_words) >= 2:  # At least 2 common words
                    semantic_matches.append((req[0], cap[0], len(common_words)))
        
        if semantic_matches:
            print(f"   Semantic matches found: {len(semantic_matches)}")
            for req, cap, score in semantic_matches[:5]:
                print(f"   🔍 {req} ↔ {cap} (score: {score})")
        
        return {
            "okh_summaries": okh_summaries,
            "okw_summaries": okw_summaries,
            "requirements_counter": req_counter,
            "capabilities_counter": cap_counter,
            "direct_matches": direct_matches,
            "semantic_matches": semantic_matches
        }
    
    def generate_test_scenarios(self, analysis_results: Dict[str, Any]):
        """Generate specific test scenarios based on analysis."""
        print(f"\n🧪 Generated Test Scenarios")
        print("=" * 60)
        
        scenarios = []
        
        # Scenario 1: Direct matches
        if analysis_results["direct_matches"]:
            print("Scenario 1: Direct Matches")
            direct_matches = list(analysis_results["direct_matches"])[:5]
            scenarios.append({
                "name": "Direct Matches",
                "requirements": direct_matches,
                "capabilities": direct_matches,
                "expected_confidence": "High (0.8-1.0)"
            })
            print(f"   Requirements: {direct_matches}")
            print(f"   Expected: High confidence matches")
        
        # Scenario 2: 3D Printing
        print("\nScenario 2: 3D Printing")
        printing_reqs = [req for req in analysis_results["requirements_counter"] if "3d" in req.lower() or "printing" in req.lower()]
        printing_caps = [cap for cap in analysis_results["capabilities_counter"] if "3d" in cap.lower() or "printing" in cap.lower()]
        
        if printing_reqs and printing_caps:
            scenarios.append({
                "name": "3D Printing",
                "requirements": printing_reqs[:3],
                "capabilities": printing_caps[:3],
                "expected_confidence": "High (0.7-0.9)"
            })
            print(f"   Requirements: {printing_reqs[:3]}")
            print(f"   Capabilities: {printing_caps[:3]}")
            print(f"   Expected: High confidence matches")
        
        # Scenario 3: CNC Machining
        print("\nScenario 3: CNC Machining")
        cnc_reqs = [req for req in analysis_results["requirements_counter"] if "cnc" in req.lower() or "machining" in req.lower()]
        cnc_caps = [cap for cap in analysis_results["capabilities_counter"] if "cnc" in cap.lower() or "machining" in cap.lower()]
        
        if cnc_reqs and cnc_caps:
            scenarios.append({
                "name": "CNC Machining",
                "requirements": cnc_reqs[:3],
                "capabilities": cnc_caps[:3],
                "expected_confidence": "High (0.7-0.9)"
            })
            print(f"   Requirements: {cnc_reqs[:3]}")
            print(f"   Capabilities: {cnc_caps[:3]}")
            print(f"   Expected: High confidence matches")
        
        # Scenario 4: Material matching
        print("\nScenario 4: Material Matching")
        material_reqs = [req for req in analysis_results["requirements_counter"] if "material" in req.lower()]
        material_caps = [cap for cap in analysis_results["capabilities_counter"] if "material" in cap.lower()]
        
        if material_reqs and material_caps:
            scenarios.append({
                "name": "Material Matching",
                "requirements": material_reqs[:3],
                "capabilities": material_caps[:3],
                "expected_confidence": "Medium (0.5-0.8)"
            })
            print(f"   Requirements: {material_reqs[:3]}")
            print(f"   Capabilities: {material_caps[:3]}")
            print(f"   Expected: Medium confidence matches")
        
        # Scenario 5: Challenging matches
        print("\nScenario 5: Challenging Matches")
        challenging_reqs = [req for req in analysis_results["requirements_counter"] if req not in analysis_results["direct_matches"]][:3]
        challenging_caps = [cap for cap in analysis_results["capabilities_counter"] if cap not in analysis_results["direct_matches"]][:3]
        
        if challenging_reqs and challenging_caps:
            scenarios.append({
                "name": "Challenging Matches",
                "requirements": challenging_reqs,
                "capabilities": challenging_caps,
                "expected_confidence": "Low-Medium (0.3-0.7)"
            })
            print(f"   Requirements: {challenging_reqs}")
            print(f"   Capabilities: {challenging_caps}")
            print(f"   Expected: Low-Medium confidence matches")
        
        return scenarios


def main():
    """Main analysis function."""
    print("🔍 Synthetic Data Analysis for LLM Matching")
    print("=" * 60)
    
    # Initialize analyzer
    analyzer = SyntheticDataAnalyzer()
    
    if not analyzer.okh_files or not analyzer.okw_files:
        print("❌ No synthetic data files found.")
        print("   Please run: python synth/generate_synthetic_data.py --type okh --count 5")
        print("   And: python synth/generate_synthetic_data.py --type okw --count 5")
        return
    
    # Analyze data
    analysis_results = analyzer.analyze_all_data()
    
    # Generate test scenarios
    scenarios = analyzer.generate_test_scenarios(analysis_results)
    
    print(f"\n📝 Summary:")
    print(f"   Found {len(scenarios)} test scenarios")
    print(f"   Ready for LLM matching tests")
    print(f"   Run: python test_llm_matching_comprehensive.py")


if __name__ == "__main__":
    main()
