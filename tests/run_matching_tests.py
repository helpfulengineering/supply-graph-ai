#!/usr/bin/env python3
"""
Main Test Execution Script for OME Testing Framework

This script orchestrates the entire testing process:
1. Generates test scenarios (if needed)
2. Runs the test harness
3. Analyzes results
4. Generates comprehensive reports

Usage:
    python run_matching_tests.py --scenarios ./test_scenarios --output ./reports
    python run_matching_tests.py --generate-scenarios --count 50 --output ./reports
    python run_matching_tests.py --scenarios ./test_scenarios --scenario-types exact_match,partial_match
"""

import argparse
import asyncio
import json
import os
import sys
import time
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Optional

# Add the src directory to the path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

# Import test harness and analyzers
from test_harness_matching import MatchingTestHarness, find_scenario_files
from reporters.json_reporter import JSONReporter

# Import scenario generator
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'synth'))
from test_scenarios import TestScenarioGenerator

class OMETestRunner:
    """Main test runner for OME testing framework"""
    
    def __init__(self, api_base_url: str = "http://localhost:8001"):
        self.api_base_url = api_base_url
        self.test_harness = MatchingTestHarness(api_base_url)
        self.reporter = JSONReporter()
        self.scenario_generator = TestScenarioGenerator()
        
    async def run_tests(self, scenario_dir: str, output_dir: str, 
                       scenario_types: Optional[List[str]] = None,
                       progress_callback: Optional[callable] = None) -> Dict:
        """Run the complete testing process"""
        
        print(f"Starting OME testing process...")
        print(f"Scenario directory: {scenario_dir}")
        print(f"Output directory: {output_dir}")
        print(f"API base URL: {self.api_base_url}")
        
        # Ensure output directory exists
        os.makedirs(output_dir, exist_ok=True)
        
        # Find scenario files
        scenario_files = find_scenario_files(scenario_dir)
        
        if not scenario_files:
            print(f"No scenario files found in {scenario_dir}")
            return {"error": "No scenario files found"}
        
        # Filter by scenario types if specified
        if scenario_types:
            filtered_files = []
            for file_path in scenario_files:
                scenario_id = os.path.basename(file_path).replace('_metadata.json', '')
                # Extract scenario type from scenario_id
                scenario_type = scenario_id.split('_')[0] + '_' + scenario_id.split('_')[1]
                if scenario_type in scenario_types:
                    filtered_files.append(file_path)
            scenario_files = filtered_files
            
            print(f"Filtered to {len(scenario_files)} scenarios of types: {scenario_types}")
        
        print(f"Found {len(scenario_files)} scenario files to test")
        
        # Run test harness
        print("\n" + "="*60)
        print("RUNNING TEST HARNESS")
        print("="*60)
        
        start_time = time.time()
        
        def harness_progress_callback(current, total, result):
            if progress_callback:
                progress_callback(current, total, result)
            else:
                status = "PASS" if result.success else "FAIL"
                print(f"[{current}/{total}] {result.scenario_id}: {status}")
        
        test_results = await self.test_harness.run_test_scenarios(
            scenario_files, harness_progress_callback
        )
        
        harness_duration = time.time() - start_time
        
        print(f"\nTest harness completed in {harness_duration:.2f} seconds")
        
        # Save raw test results
        raw_results_file = os.path.join(output_dir, "raw_test_results.json")
        self.test_harness.save_results(raw_results_file)
        
        # Generate comprehensive report
        print("\n" + "="*60)
        print("GENERATING COMPREHENSIVE REPORT")
        print("="*60)
        
        report_start_time = time.time()
        
        test_run_metadata = {
            "test_run_id": f"test_run_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
            "start_time": datetime.now().isoformat(),
            "api_base_url": self.api_base_url,
            "scenario_directory": scenario_dir,
            "total_scenarios": len(scenario_files),
            "scenario_types": scenario_types,
            "harness_duration_seconds": harness_duration
        }
        
        comprehensive_report = self.reporter.generate_comprehensive_report(
            test_results, test_run_metadata
        )
        
        report_duration = time.time() - report_start_time
        
        # Save comprehensive report
        comprehensive_report_file = os.path.join(output_dir, "comprehensive_report.json")
        self.reporter.save_report(comprehensive_report, comprehensive_report_file)
        
        print(f"Report generation completed in {report_duration:.2f} seconds")
        
        # Generate summary
        total_duration = time.time() - start_time
        summary = self._generate_execution_summary(
            test_results, comprehensive_report, total_duration, harness_duration, report_duration
        )
        
        # Save summary
        summary_file = os.path.join(output_dir, "execution_summary.json")
        with open(summary_file, 'w', encoding='utf-8') as f:
            json.dump(summary, f, indent=2, ensure_ascii=False, default=str)
        
        print(f"\nExecution summary saved to: {summary_file}")
        
        return {
            "success": True,
            "test_results": test_results,
            "comprehensive_report": comprehensive_report,
            "summary": summary,
            "files_generated": {
                "raw_results": raw_results_file,
                "comprehensive_report": comprehensive_report_file,
                "summary": summary_file
            }
        }
    
    def generate_test_scenarios(self, output_dir: str, count_per_type: int = 10,
                              scenario_types: Optional[List[str]] = None) -> Dict:
        """Generate test scenarios"""
        
        print(f"Generating test scenarios...")
        print(f"Output directory: {output_dir}")
        print(f"Count per type: {count_per_type}")
        
        # Ensure output directory exists
        os.makedirs(output_dir, exist_ok=True)
        
        # Generate scenarios
        if scenario_types:
            all_scenarios = []
            for scenario_type in scenario_types:
                print(f"Generating {count_per_type} {scenario_type} scenarios...")
                if scenario_type == "exact_match":
                    scenarios = self.scenario_generator.generate_exact_match_scenario(count_per_type)
                elif scenario_type == "partial_match":
                    scenarios = self.scenario_generator.generate_partial_match_scenario(count_per_type)
                elif scenario_type == "near_miss":
                    scenarios = self.scenario_generator.generate_near_miss_scenario(count_per_type)
                elif scenario_type == "no_match":
                    scenarios = self.scenario_generator.generate_no_match_scenario(count_per_type)
                elif scenario_type == "edge_case":
                    scenarios = self.scenario_generator.generate_edge_case_scenario(count_per_type)
                else:
                    print(f"Unknown scenario type: {scenario_type}")
                    continue
                
                all_scenarios.extend(scenarios)
        else:
            print(f"Generating all scenario types...")
            all_scenarios = self.scenario_generator.generate_all_scenarios(count_per_type)
        
        # Save scenarios
        saved_count = 0
        for scenario in all_scenarios:
            try:
                from test_scenarios import save_scenario
                okh_file, okw_file = save_scenario(scenario, output_dir)
                saved_count += 1
            except Exception as e:
                print(f"Error saving scenario {scenario['scenario_id']}: {e}")
        
        print(f"Successfully generated {saved_count} test scenarios")
        
        return {
            "success": True,
            "total_scenarios": len(all_scenarios),
            "saved_scenarios": saved_count,
            "output_directory": output_dir
        }
    
    def _generate_execution_summary(self, test_results: List[Dict], comprehensive_report: Dict,
                                  total_duration: float, harness_duration: float, 
                                  report_duration: float) -> Dict:
        """Generate execution summary"""
        
        executive_summary = comprehensive_report.get("executive_summary", {})
        summary_stats = comprehensive_report.get("summary_statistics", {})
        
        return {
            "execution_metadata": {
                "total_duration_seconds": total_duration,
                "harness_duration_seconds": harness_duration,
                "report_duration_seconds": report_duration,
                "completed_at": datetime.now().isoformat()
            },
            "test_results_summary": {
                "total_tests": len(test_results),
                "successful_tests": summary_stats.get("successful_tests", 0),
                "failed_tests": summary_stats.get("failed_tests", 0),
                "success_rate": summary_stats.get("overall_success_rate", 0)
            },
            "system_health": {
                "health_score": executive_summary.get("health_score", 0),
                "overall_status": executive_summary.get("overall_status", "UNKNOWN"),
                "key_metrics": executive_summary.get("key_metrics", {})
            },
            "top_priorities": executive_summary.get("top_priorities", []),
            "recommendations_count": len(comprehensive_report.get("integrated_recommendations", [])),
            "critical_issues": len(comprehensive_report.get("edge_case_analysis", {}).get("edge_case_analysis", {}).get("critical_issues", []))
        }

def main():
    """Main function"""
    parser = argparse.ArgumentParser(description="Run OME matching tests")
    
    # Main options
    parser.add_argument("--scenarios", help="Directory containing test scenarios")
    parser.add_argument("--output", default="./test_reports", help="Output directory for reports")
    parser.add_argument("--api-url", default="http://localhost:8001", help="API base URL")
    
    # Scenario generation options
    parser.add_argument("--generate-scenarios", action="store_true", 
                       help="Generate test scenarios before running tests")
    parser.add_argument("--scenario-output", default="./test_scenarios", 
                       help="Output directory for generated scenarios")
    parser.add_argument("--count", type=int, default=10, 
                       help="Number of scenarios to generate per type")
    parser.add_argument("--scenario-types", 
                       help="Comma-separated list of scenario types to generate/run")
    
    # Test execution options
    parser.add_argument("--run-tests", action="store_true", default=True,
                       help="Run the test harness (default: True)")
    parser.add_argument("--generate-report", action="store_true", default=True,
                       help="Generate comprehensive report (default: True)")
    
    args = parser.parse_args()
    
    # Validate arguments
    if not args.generate_scenarios and not args.scenarios:
        print("Error: Must specify either --generate-scenarios or --scenarios")
        return 1
    
    if args.generate_scenarios and not args.scenario_output:
        print("Error: Must specify --scenario-output when generating scenarios")
        return 1
    
    # Parse scenario types
    scenario_types = None
    if args.scenario_types:
        scenario_types = [t.strip() for t in args.scenario_types.split(',')]
        valid_types = ["exact_match", "partial_match", "near_miss", "no_match", "edge_case"]
        invalid_types = [t for t in scenario_types if t not in valid_types]
        if invalid_types:
            print(f"Error: Invalid scenario types: {invalid_types}")
            print(f"Valid types: {valid_types}")
            return 1
    
    # Initialize test runner
    runner = OMETestRunner(api_base_url=args.api_url)
    
    try:
        # Generate scenarios if requested
        if args.generate_scenarios:
            print("="*60)
            print("GENERATING TEST SCENARIOS")
            print("="*60)
            
            generation_result = runner.generate_test_scenarios(
                args.scenario_output, args.count, scenario_types
            )
            
            if not generation_result["success"]:
                print("Failed to generate test scenarios")
                return 1
            
            # Use generated scenarios for testing
            scenarios_dir = args.scenario_output
        
        # Use provided scenarios directory
        else:
            scenarios_dir = args.scenarios
        
        # Run tests if requested
        if args.run_tests:
            print("="*60)
            print("RUNNING TESTS")
            print("="*60)
            
            async def progress_callback(current, total, result):
                status = "PASS" if result.success else "FAIL"
                print(f"[{current}/{total}] {result.scenario_id}: {status}")
            
            result = await runner.run_tests(
                scenarios_dir, args.output, scenario_types, progress_callback
            )
            
            if not result["success"]:
                print("Test execution failed")
                return 1
            
            print("\n" + "="*60)
            print("TESTING COMPLETED SUCCESSFULLY")
            print("="*60)
            
            # Print final summary
            summary = result["summary"]
            print(f"Total duration: {summary['execution_metadata']['total_duration_seconds']:.2f} seconds")
            print(f"Tests run: {summary['test_results_summary']['total_tests']}")
            print(f"Success rate: {summary['test_results_summary']['success_rate']:.2%}")
            print(f"System health score: {summary['system_health']['health_score']:.1f}/100")
            print(f"Overall status: {summary['system_health']['overall_status']}")
            
            if summary['top_priorities']:
                print(f"\nTop Priorities:")
                for i, priority in enumerate(summary['top_priorities'][:3], 1):
                    print(f"{i}. [{priority['priority']}] {priority['description']}")
        
        return 0
        
    except KeyboardInterrupt:
        print("\nTest execution interrupted by user")
        return 1
    except Exception as e:
        print(f"Error during test execution: {e}")
        import traceback
        traceback.print_exc()
        return 1

if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)
