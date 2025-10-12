#!/usr/bin/env python3
"""
Core Test Harness for OME Matching Engine

This module provides the core testing infrastructure for systematically
testing the Open Matching Engine (OME) with synthetic data.

Usage:
    from test_harness_matching import MatchingTestHarness
    harness = MatchingTestHarness()
    results = harness.run_test_scenarios(scenario_files)
"""

import asyncio
import json
import os
import sys
import time
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Any
from uuid import UUID

# Add the src directory to the path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from core.models.okh import OKHManifest
from core.models.okw import ManufacturingFacility
from core.services.matching_service import MatchingService
from core.services.storage_service import StorageService
from core.services.okh_service import OKHService

class TestResult:
    """Represents the result of a single test"""
    
    def __init__(self, scenario_id: str, scenario_type: str):
        self.scenario_id = scenario_id
        self.scenario_type = scenario_type
        self.start_time = None
        self.end_time = None
        self.duration = None
        self.success = False
        self.error_message = None
        self.expected_outcome = None
        self.actual_outcome = None
        self.expected_confidence = None
        self.actual_confidence = None
        self.solutions_count = 0
        self.solutions = []
        self.metadata = {}
        self.field_usage = {}
        self.edge_case_detected = False
        self.edge_case_details = {}
    
    def to_dict(self) -> Dict:
        """Convert to dictionary for JSON serialization"""
        return {
            "scenario_id": self.scenario_id,
            "scenario_type": self.scenario_type,
            "start_time": self.start_time.isoformat() if self.start_time else None,
            "end_time": self.end_time.isoformat() if self.end_time else None,
            "duration": self.duration,
            "success": self.success,
            "error_message": self.error_message,
            "expected_outcome": self.expected_outcome,
            "actual_outcome": self.actual_outcome,
            "expected_confidence": self.expected_confidence,
            "actual_confidence": self.actual_confidence,
            "solutions_count": self.solutions_count,
            "solutions": self.solutions,
            "metadata": self.metadata,
            "field_usage": self.field_usage,
            "edge_case_detected": self.edge_case_detected,
            "edge_case_details": self.edge_case_details
        }

class MatchingTestHarness:
    """Core test harness for OME matching engine"""
    
    def __init__(self, api_base_url: str = "http://localhost:8001"):
        self.api_base_url = api_base_url
        self.matching_service = None
        self.storage_service = None
        self.okh_service = None
        self.test_results = []
        
    async def initialize(self):
        """Initialize the test harness with required services"""
        try:
            # Initialize services
            self.storage_service = await StorageService.get_instance()
            self.okh_service = await OKHService.get_instance()
            self.matching_service = await MatchingService.get_instance(
                okh_service=self.okh_service,
                okw_service=None  # We'll load OKW facilities directly
            )
            print("Test harness initialized successfully")
        except Exception as e:
            print(f"Failed to initialize test harness: {e}")
            raise
    
    def load_test_scenario(self, scenario_dir: str, scenario_id: str) -> Dict:
        """Load a test scenario from files"""
        try:
            # Load metadata
            metadata_file = os.path.join(scenario_dir, f"{scenario_id}_metadata.json")
            with open(metadata_file, 'r', encoding='utf-8') as f:
                metadata = json.load(f)
            
            # Load OKH manifest
            okh_file = os.path.join(scenario_dir, f"{scenario_id}_okh.json")
            with open(okh_file, 'r', encoding='utf-8') as f:
                okh_data = json.load(f)
            okh_manifest = OKHManifest.from_dict(okh_data)
            
            # Load OKW facility
            okw_file = os.path.join(scenario_dir, f"{scenario_id}_okw.json")
            with open(okw_file, 'r', encoding='utf-8') as f:
                okw_data = json.load(f)
            okw_facility = ManufacturingFacility.from_dict(okw_data)
            
            return {
                "metadata": metadata,
                "okh_manifest": okh_manifest,
                "okw_facility": okw_facility
            }
        except Exception as e:
            raise Exception(f"Failed to load scenario {scenario_id}: {e}")
    
    async def run_single_test(self, scenario: Dict) -> TestResult:
        """Run a single test scenario"""
        metadata = scenario["metadata"]
        okh_manifest = scenario["okh_manifest"]
        okw_facility = scenario["okw_facility"]
        
        result = TestResult(
            scenario_id=metadata["scenario_id"],
            scenario_type=metadata["scenario_type"]
        )
        
        result.start_time = datetime.now()
        result.expected_outcome = metadata.get("expected_outcome")
        result.expected_confidence = metadata.get("expected_confidence", 0.0)
        
        try:
            # Run the matching
            solutions = await self.matching_service.find_matches_with_manifest(
                okh_manifest=okh_manifest,
                facilities=[okw_facility],
                optimization_criteria=None
            )
            
            # Analyze results
            result.solutions_count = len(solutions)
            result.solutions = [solution.to_dict() for solution in solutions]
            
            # Determine actual outcome
            if result.solutions_count > 0:
                result.actual_outcome = "match"
                # Calculate average confidence
                if solutions:
                    result.actual_confidence = sum(s.score for s in solutions) / len(solutions)
                else:
                    result.actual_confidence = 0.0
            else:
                result.actual_outcome = "no_match"
                result.actual_confidence = 0.0
            
            # Check if test was successful
            result.success = self._evaluate_test_success(result)
            
            # Analyze field usage
            result.field_usage = self._analyze_field_usage(okh_manifest, okw_facility, solutions)
            
            # Detect edge cases
            result.edge_case_detected, result.edge_case_details = self._detect_edge_cases(
                result, okh_manifest, okw_facility
            )
            
        except Exception as e:
            result.success = False
            result.error_message = str(e)
            result.actual_outcome = "error"
            result.actual_confidence = 0.0
        
        result.end_time = datetime.now()
        result.duration = (result.end_time - result.start_time).total_seconds()
        
        return result
    
    def _evaluate_test_success(self, result: TestResult) -> bool:
        """Evaluate whether a test was successful based on expected vs actual outcomes"""
        if result.error_message:
            return False
        
        # Check outcome match
        outcome_match = result.expected_outcome == result.actual_outcome
        
        # Check confidence within acceptable range (allow ±0.1 tolerance)
        confidence_match = True
        if result.expected_confidence is not None:
            confidence_diff = abs(result.actual_confidence - result.expected_confidence)
            confidence_match = confidence_diff <= 0.1
        
        return outcome_match and confidence_match
    
    def _analyze_field_usage(self, okh_manifest: OKHManifest, okw_facility: ManufacturingFacility, 
                           solutions: List) -> Dict:
        """Analyze which fields were used in matching"""
        field_usage = {
            "okh_fields_available": {},
            "okw_fields_available": {},
            "fields_used_in_matching": {},
            "fields_not_used": []
        }
        
        # Analyze OKH fields
        okh_fields = {
            "title": okh_manifest.title,
            "manufacturing_processes": okh_manifest.manufacturing_processes,
            "materials": [m.name for m in okh_manifest.materials],
            "tool_list": okh_manifest.tool_list,
            "standards_used": [s.standard_title for s in okh_manifest.standards_used],
            "keywords": okh_manifest.keywords,
            "making_instructions": len(okh_manifest.making_instructions),
            "bom": okh_manifest.bom,
            "manufacturing_specs": okh_manifest.manufacturing_specs is not None
        }
        
        # Analyze OKW fields
        okw_fields = {
            "name": okw_facility.name,
            "manufacturing_processes": okw_facility.manufacturing_processes,
            "equipment": [e.equipment_type for e in okw_facility.equipment],
            "typical_materials": [m.material_type for m in okw_facility.typical_materials],
            "certifications": okw_facility.certifications,
            "typical_batch_size": okw_facility.typical_batch_size.value if okw_facility.typical_batch_size else None,
            "access_type": okw_facility.access_type.value,
            "facility_status": okw_facility.facility_status.value
        }
        
        field_usage["okh_fields_available"] = {k: v for k, v in okh_fields.items() if v}
        field_usage["okw_fields_available"] = {k: v for k, v in okw_fields.items() if v}
        
        # Determine which fields were likely used in matching
        # This is a heuristic analysis based on the matching results
        used_fields = []
        
        if solutions:
            # If we have solutions, assume manufacturing_processes was used
            if okh_manifest.manufacturing_processes:
                used_fields.append("manufacturing_processes")
            
            # Check if materials were considered
            if okh_manifest.materials and okw_facility.typical_materials:
                used_fields.append("materials")
            
            # Check if tools were considered
            if okh_manifest.tool_list:
                used_fields.append("tool_list")
        
        field_usage["fields_used_in_matching"] = used_fields
        
        # Find fields that weren't used
        all_okh_fields = set(okh_fields.keys())
        all_okw_fields = set(okw_fields.keys())
        used_fields_set = set(used_fields)
        
        unused_okh = all_okh_fields - used_fields_set
        unused_okw = all_okw_fields - used_fields_set
        
        field_usage["fields_not_used"] = list(unused_okh.union(unused_okw))
        
        return field_usage
    
    def _detect_edge_cases(self, result: TestResult, okh_manifest: OKHManifest, 
                          okw_facility: ManufacturingFacility) -> Tuple[bool, Dict]:
        """Detect edge cases and problematic patterns"""
        edge_case_detected = False
        edge_case_details = {}
        
        # Check for empty manufacturing processes
        if not okh_manifest.manufacturing_processes:
            edge_case_detected = True
            edge_case_details["empty_manufacturing_processes"] = {
                "severity": "high",
                "description": "OKH manifest has no manufacturing processes specified"
            }
        
        # Check for empty OKW capabilities
        if not okw_facility.equipment:
            edge_case_detected = True
            edge_case_details["empty_okw_capabilities"] = {
                "severity": "high",
                "description": "OKW facility has no equipment/capabilities"
            }
        
        # Check for confidence score anomalies
        if result.actual_confidence > 1.0 or result.actual_confidence < 0.0:
            edge_case_detected = True
            edge_case_details["invalid_confidence_score"] = {
                "severity": "medium",
                "description": f"Confidence score {result.actual_confidence} is outside valid range [0,1]"
            }
        
        # Check for unexpected null responses
        if result.actual_outcome == "match" and result.solutions_count == 0:
            edge_case_detected = True
            edge_case_details["match_with_no_solutions"] = {
                "severity": "high",
                "description": "Match outcome but no solutions returned"
            }
        
        # Check for malformed SupplyTree objects
        for solution in result.solutions:
            if "tree" in solution:
                tree = solution["tree"]
                if not tree.get("workflows") or not tree.get("id"):
                    edge_case_detected = True
                    edge_case_details["malformed_supply_tree"] = {
                        "severity": "medium",
                        "description": "SupplyTree missing required fields"
                    }
                    break
        
        # Check for missing metadata
        if result.solutions_count > 0 and not any(s.get("metadata") for s in result.solutions):
            edge_case_detected = True
            edge_case_details["missing_metadata"] = {
                "severity": "low",
                "description": "Solutions missing metadata information"
            }
        
        return edge_case_detected, edge_case_details
    
    async def run_test_scenarios(self, scenario_files: List[str], 
                               progress_callback: Optional[callable] = None) -> List[TestResult]:
        """Run multiple test scenarios"""
        if not self.matching_service:
            await self.initialize()
        
        results = []
        total_scenarios = len(scenario_files)
        
        print(f"Running {total_scenarios} test scenarios...")
        
        for i, scenario_file in enumerate(scenario_files):
            try:
                # Load scenario
                scenario_dir = os.path.dirname(scenario_file)
                scenario_id = os.path.basename(scenario_file).replace('_metadata.json', '')
                scenario = self.load_test_scenario(scenario_dir, scenario_id)
                
                # Run test
                result = await self.run_single_test(scenario)
                results.append(result)
                
                # Progress callback
                if progress_callback:
                    progress_callback(i + 1, total_scenarios, result)
                
                print(f"Completed {i + 1}/{total_scenarios}: {scenario_id} - {'PASS' if result.success else 'FAIL'}")
                
            except Exception as e:
                print(f"Error running scenario {scenario_file}: {e}")
                # Create error result
                error_result = TestResult(
                    scenario_id=os.path.basename(scenario_file).replace('_metadata.json', ''),
                    scenario_type="unknown"
                )
                error_result.success = False
                error_result.error_message = str(e)
                error_result.actual_outcome = "error"
                results.append(error_result)
        
        self.test_results = results
        return results
    
    def get_summary_statistics(self) -> Dict:
        """Get summary statistics from test results"""
        if not self.test_results:
            return {}
        
        total_tests = len(self.test_results)
        successful_tests = sum(1 for r in self.test_results if r.success)
        failed_tests = total_tests - successful_tests
        
        # Group by scenario type
        by_type = {}
        for result in self.test_results:
            scenario_type = result.scenario_type
            if scenario_type not in by_type:
                by_type[scenario_type] = {"total": 0, "successful": 0, "failed": 0}
            by_type[scenario_type]["total"] += 1
            if result.success:
                by_type[scenario_type]["successful"] += 1
            else:
                by_type[scenario_type]["failed"] += 1
        
        # Calculate average confidence
        confidence_scores = [r.actual_confidence for r in self.test_results if r.actual_confidence is not None]
        avg_confidence = sum(confidence_scores) / len(confidence_scores) if confidence_scores else 0.0
        
        # Count edge cases
        edge_cases = sum(1 for r in self.test_results if r.edge_case_detected)
        
        return {
            "total_tests": total_tests,
            "successful_tests": successful_tests,
            "failed_tests": failed_tests,
            "success_rate": successful_tests / total_tests if total_tests > 0 else 0.0,
            "average_confidence": avg_confidence,
            "edge_cases_detected": edge_cases,
            "by_scenario_type": by_type,
            "total_duration": sum(r.duration for r in self.test_results if r.duration),
            "average_duration": sum(r.duration for r in self.test_results if r.duration) / total_tests if total_tests > 0 else 0.0
        }
    
    def save_results(self, output_file: str):
        """Save test results to JSON file"""
        results_data = {
            "test_run_metadata": {
                "timestamp": datetime.now().isoformat(),
                "total_tests": len(self.test_results),
                "api_base_url": self.api_base_url
            },
            "summary": self.get_summary_statistics(),
            "test_results": [result.to_dict() for result in self.test_results]
        }
        
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(results_data, f, indent=2, ensure_ascii=False, default=str)
        
        print(f"Test results saved to: {output_file}")

def find_scenario_files(scenario_dir: str) -> List[str]:
    """Find all scenario metadata files in a directory"""
    scenario_files = []
    for file in os.listdir(scenario_dir):
        if file.endswith('_metadata.json'):
            scenario_files.append(os.path.join(scenario_dir, file))
    return sorted(scenario_files)

async def main():
    """Example usage of the test harness"""
    import argparse
    
    parser = argparse.ArgumentParser(description="Run OME matching tests")
    parser.add_argument("--scenario-dir", required=True, help="Directory containing test scenarios")
    parser.add_argument("--output", default="test_results.json", help="Output file for results")
    parser.add_argument("--api-url", default="http://localhost:8001", help="API base URL")
    
    args = parser.parse_args()
    
    # Find scenario files
    scenario_files = find_scenario_files(args.scenario_dir)
    if not scenario_files:
        print(f"No scenario files found in {args.scenario_dir}")
        return
    
    print(f"Found {len(scenario_files)} scenario files")
    
    # Initialize and run tests
    harness = MatchingTestHarness(api_base_url=args.api_url)
    
    def progress_callback(current, total, result):
        status = "PASS" if result.success else "FAIL"
        print(f"[{current}/{total}] {result.scenario_id}: {status}")
    
    results = await harness.run_test_scenarios(scenario_files, progress_callback)
    
    # Save results
    harness.save_results(args.output)
    
    # Print summary
    summary = harness.get_summary_statistics()
    print(f"\nTest Summary:")
    print(f"Total tests: {summary['total_tests']}")
    print(f"Successful: {summary['successful_tests']}")
    print(f"Failed: {summary['failed_tests']}")
    print(f"Success rate: {summary['success_rate']:.2%}")
    print(f"Average confidence: {summary['average_confidence']:.3f}")
    print(f"Edge cases detected: {summary['edge_cases_detected']}")

if __name__ == "__main__":
    asyncio.run(main())
