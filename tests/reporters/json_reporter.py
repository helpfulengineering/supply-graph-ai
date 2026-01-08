#!/usr/bin/env python3
"""
JSON Report Generator for OHM Testing Framework

This module generates JSON reports combining test results,
field coverage analysis, edge case detection, and match quality analysis.

Usage:
    from reporters.json_reporter import JSONReporter
    reporter = JSONReporter()
    report = reporter.generate_comprehensive_report(test_results, analyzers)
"""

import json
import os
from datetime import datetime
from typing import Dict, List, Any, Optional
from pathlib import Path

# Import analyzers
import sys
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))

from analyzers.field_coverage import FieldCoverageAnalyzer
from analyzers.edge_case_detector import EdgeCaseDetector
from analyzers.match_quality import MatchQualityAnalyzer

class JSONReporter:
    """Generates JSON reports for OHM testing"""
    
    def __init__(self):
        self.field_analyzer = FieldCoverageAnalyzer()
        self.edge_case_detector = EdgeCaseDetector()
        self.quality_analyzer = MatchQualityAnalyzer()
    
    def generate_comprehensive_report(self, test_results: List[Dict], 
                                    test_run_metadata: Optional[Dict] = None) -> Dict:
        """Generate a report combining all analyses"""
        
        # Run all analyses
        print("Running field coverage analysis...")
        field_coverage_report = self.field_analyzer.generate_coverage_report(test_results)
        
        print("Running edge case detection...")
        edge_case_report = self.edge_case_detector.generate_edge_case_report(test_results)
        
        print("Running match quality analysis...")
        quality_report = self.quality_analyzer.generate_quality_report(test_results)
        
        # Generate summary statistics
        summary_stats = self._generate_summary_statistics(test_results)
        
        # Create report
        comprehensive_report = {
            "report_metadata": {
                "generated_at": datetime.now().isoformat(),
                "report_type": "comprehensive_ome_testing_report",
                "version": "1.0.0",
                "total_tests_analyzed": len(test_results)
            },
            "test_run_metadata": test_run_metadata or {},
            "executive_summary": self._generate_executive_summary(
                summary_stats, field_coverage_report, edge_case_report, quality_report
            ),
            "summary_statistics": summary_stats,
            "field_coverage_analysis": field_coverage_report,
            "edge_case_analysis": edge_case_report,
            "match_quality_analysis": quality_report,
            "integrated_recommendations": self._generate_integrated_recommendations(
                field_coverage_report, edge_case_report, quality_report
            ),
            "test_results": test_results
        }
        
        return comprehensive_report
    
    def _generate_summary_statistics(self, test_results: List[Dict]) -> Dict:
        """Generate high-level summary statistics"""
        if not test_results:
            return {}
        
        total_tests = len(test_results)
        successful_tests = sum(1 for r in test_results if r.get("success", False))
        failed_tests = total_tests - successful_tests
        
        # Calculate confidence statistics
        confidence_scores = [r.get("actual_confidence", 0) for r in test_results if r.get("actual_confidence") is not None]
        
        # Group by scenario type
        scenario_type_stats = {}
        for result in test_results:
            scenario_type = result.get("scenario_type", "unknown")
            if scenario_type not in scenario_type_stats:
                scenario_type_stats[scenario_type] = {"total": 0, "successful": 0, "failed": 0}
            
            scenario_type_stats[scenario_type]["total"] += 1
            if result.get("success", False):
                scenario_type_stats[scenario_type]["successful"] += 1
            else:
                scenario_type_stats[scenario_type]["failed"] += 1
        
        # Calculate success rates by scenario type
        for stats in scenario_type_stats.values():
            stats["success_rate"] = stats["successful"] / stats["total"] if stats["total"] > 0 else 0
        
        # Calculate outcome distribution
        outcome_counts = {}
        for result in test_results:
            outcome = result.get("actual_outcome", "unknown")
            outcome_counts[outcome] = outcome_counts.get(outcome, 0) + 1
        
        # Calculate duration statistics
        durations = [r.get("duration", 0) for r in test_results if r.get("duration")]
        
        return {
            "total_tests": total_tests,
            "successful_tests": successful_tests,
            "failed_tests": failed_tests,
            "overall_success_rate": successful_tests / total_tests if total_tests > 0 else 0,
            "confidence_statistics": {
                "mean": sum(confidence_scores) / len(confidence_scores) if confidence_scores else 0,
                "min": min(confidence_scores) if confidence_scores else 0,
                "max": max(confidence_scores) if confidence_scores else 0,
                "count": len(confidence_scores)
            },
            "scenario_type_statistics": scenario_type_stats,
            "outcome_distribution": outcome_counts,
            "duration_statistics": {
                "total_duration": sum(durations),
                "average_duration": sum(durations) / len(durations) if durations else 0,
                "min_duration": min(durations) if durations else 0,
                "max_duration": max(durations) if durations else 0
            }
        }
    
    def _generate_executive_summary(self, summary_stats: Dict, field_coverage_report: Dict,
                                  edge_case_report: Dict, quality_report: Dict) -> Dict:
        """Generate an executive summary of the testing results"""
        
        # Overall health score (0-100)
        health_score = self._calculate_health_score(summary_stats, field_coverage_report, 
                                                  edge_case_report, quality_report)
        
        # Key metrics
        key_metrics = {
            "overall_success_rate": summary_stats.get("overall_success_rate", 0),
            "match_accuracy": quality_report.get("summary", {}).get("overall_accuracy", 0),
            "field_coverage_rate": self._calculate_field_coverage_rate(field_coverage_report),
            "edge_cases_detected": edge_case_report.get("summary", {}).get("total_edge_cases", 0),
            "critical_issues": edge_case_report.get("summary", {}).get("critical_issues", 0)
        }
        
        # Health assessment
        health_assessment = self._assess_system_health(key_metrics)
        
        # Top priorities
        top_priorities = self._identify_top_priorities(field_coverage_report, edge_case_report, quality_report)
        
        return {
            "health_score": health_score,
            "health_assessment": health_assessment,
            "key_metrics": key_metrics,
            "top_priorities": top_priorities,
            "overall_status": "HEALTHY" if health_score >= 80 else "NEEDS_ATTENTION" if health_score >= 60 else "CRITICAL"
        }
    
    def _calculate_health_score(self, summary_stats: Dict, field_coverage_report: Dict,
                              edge_case_report: Dict, quality_report: Dict) -> float:
        """Calculate overall system health score (0-100)"""
        
        # Success rate component (40% weight)
        success_rate = summary_stats.get("overall_success_rate", 0)
        success_score = success_rate * 40
        
        # Accuracy component (30% weight)
        accuracy = quality_report.get("summary", {}).get("overall_accuracy", 0)
        accuracy_score = accuracy * 30
        
        # Field coverage component (20% weight)
        field_coverage_rate = self._calculate_field_coverage_rate(field_coverage_report)
        coverage_score = field_coverage_rate * 20
        
        # Edge case component (10% weight) - lower is better
        total_edge_cases = edge_case_report.get("summary", {}).get("total_edge_cases", 0)
        total_tests = summary_stats.get("total_tests", 1)
        edge_case_rate = total_edge_cases / total_tests if total_tests > 0 else 0
        edge_case_score = max(0, 10 - (edge_case_rate * 50))  # Penalize high edge case rates
        
        return success_score + accuracy_score + coverage_score + edge_case_score
    
    def _calculate_field_coverage_rate(self, field_coverage_report: Dict) -> float:
        """Calculate field coverage rate"""
        summary = field_coverage_report.get("summary", {})
        total_fields = summary.get("total_okh_fields", 0) + summary.get("total_okw_fields", 0)
        unused_fields = summary.get("unused_okh_fields", 0) + summary.get("unused_okw_fields", 0)
        
        if total_fields == 0:
            return 0.0
        
        return (total_fields - unused_fields) / total_fields
    
    def _assess_system_health(self, key_metrics: Dict) -> Dict:
        """Assess system health based on key metrics"""
        assessments = {}
        
        # Success rate assessment
        success_rate = key_metrics.get("overall_success_rate", 0)
        if success_rate >= 0.9:
            assessments["success_rate"] = "EXCELLENT"
        elif success_rate >= 0.8:
            assessments["success_rate"] = "GOOD"
        elif success_rate >= 0.7:
            assessments["success_rate"] = "ACCEPTABLE"
        else:
            assessments["success_rate"] = "POOR"
        
        # Accuracy assessment
        accuracy = key_metrics.get("match_accuracy", 0)
        if accuracy >= 0.95:
            assessments["accuracy"] = "EXCELLENT"
        elif accuracy >= 0.9:
            assessments["accuracy"] = "GOOD"
        elif accuracy >= 0.8:
            assessments["accuracy"] = "ACCEPTABLE"
        else:
            assessments["accuracy"] = "POOR"
        
        # Field coverage assessment
        coverage_rate = key_metrics.get("field_coverage_rate", 0)
        if coverage_rate >= 0.8:
            assessments["field_coverage"] = "EXCELLENT"
        elif coverage_rate >= 0.6:
            assessments["field_coverage"] = "GOOD"
        elif coverage_rate >= 0.4:
            assessments["field_coverage"] = "ACCEPTABLE"
        else:
            assessments["field_coverage"] = "POOR"
        
        # Edge case assessment
        edge_cases = key_metrics.get("edge_cases_detected", 0)
        if edge_cases == 0:
            assessments["edge_cases"] = "EXCELLENT"
        elif edge_cases <= 5:
            assessments["edge_cases"] = "GOOD"
        elif edge_cases <= 15:
            assessments["edge_cases"] = "ACCEPTABLE"
        else:
            assessments["edge_cases"] = "POOR"
        
        return assessments
    
    def _identify_top_priorities(self, field_coverage_report: Dict, edge_case_report: Dict,
                               quality_report: Dict) -> List[Dict]:
        """Identify top priorities for improvement"""
        priorities = []
        
        # Critical issues from edge case analysis
        critical_issues = edge_case_report.get("edge_case_analysis", {}).get("critical_issues", [])
        for issue in critical_issues[:3]:  # Top 3 critical issues
            priorities.append({
                "priority": "CRITICAL",
                "category": "Edge Cases",
                "description": issue.get("description", ""),
                "impact": issue.get("impact", ""),
                "occurrences": issue.get("occurrences", 0)
            })
        
        # High priority field coverage issues
        field_recommendations = field_coverage_report.get("field_analysis", {}).get("recommendations", [])
        for rec in field_recommendations[:2]:  # Top 2 field recommendations
            if "CRITICAL" in rec or "HIGH" in rec:
                priorities.append({
                    "priority": "HIGH",
                    "category": "Field Coverage",
                    "description": rec,
                    "impact": "Improved matching accuracy and field utilization"
                })
        
        # Quality issues
        quality_recommendations = quality_report.get("quality_analysis", {}).get("quality_recommendations", [])
        for rec in quality_recommendations[:2]:  # Top 2 quality recommendations
            if "HIGH" in rec:
                priorities.append({
                    "priority": "HIGH",
                    "category": "Match Quality",
                    "description": rec,
                    "impact": "Improved matching accuracy and confidence calibration"
                })
        
        return priorities
    
    def _generate_integrated_recommendations(self, field_coverage_report: Dict, 
                                           edge_case_report: Dict, quality_report: Dict) -> List[Dict]:
        """Generate integrated recommendations combining all analyses"""
        integrated_recommendations = []
        
        # Combine recommendations from all analyses
        all_recommendations = []
        
        # Field coverage recommendations
        field_recs = field_coverage_report.get("field_analysis", {}).get("recommendations", [])
        for rec in field_recs:
            all_recommendations.append({
                "source": "field_coverage",
                "priority": self._extract_priority(rec),
                "recommendation": rec,
                "category": "Field Coverage"
            })
        
        # Edge case recommendations
        edge_recs = edge_case_report.get("edge_case_analysis", {}).get("recommendations", [])
        for rec in edge_recs:
            all_recommendations.append({
                "source": "edge_case_detection",
                "priority": self._extract_priority(rec),
                "recommendation": rec,
                "category": "Edge Cases"
            })
        
        # Quality recommendations
        quality_recs = quality_report.get("quality_analysis", {}).get("quality_recommendations", [])
        for rec in quality_recs:
            all_recommendations.append({
                "source": "match_quality",
                "priority": self._extract_priority(rec),
                "recommendation": rec,
                "category": "Match Quality"
            })
        
        # Sort by priority
        priority_order = {"CRITICAL": 0, "HIGH": 1, "MEDIUM": 2, "LOW": 3}
        all_recommendations.sort(key=lambda x: priority_order.get(x["priority"], 4))
        
        # Group by category and priority
        grouped_recommendations = {}
        for rec in all_recommendations:
            key = f"{rec['category']}_{rec['priority']}"
            if key not in grouped_recommendations:
                grouped_recommendations[key] = {
                    "category": rec["category"],
                    "priority": rec["priority"],
                    "recommendations": []
                }
            grouped_recommendations[key]["recommendations"].append(rec["recommendation"])
        
        # Convert to list and limit to top recommendations
        integrated_recommendations = list(grouped_recommendations.values())[:10]
        
        return integrated_recommendations
    
    def _extract_priority(self, recommendation: str) -> str:
        """Extract priority level from recommendation text"""
        if "CRITICAL" in recommendation:
            return "CRITICAL"
        elif "HIGH" in recommendation:
            return "HIGH"
        elif "MEDIUM" in recommendation:
            return "MEDIUM"
        elif "LOW" in recommendation:
            return "LOW"
        else:
            return "MEDIUM"  # Default priority
    
    def save_report(self, report: Dict, output_file: str):
        """Save the comprehensive report to a JSON file"""
        # Ensure output directory exists
        output_dir = os.path.dirname(output_file)
        if output_dir:
            os.makedirs(output_dir, exist_ok=True)
        
        # Save the report
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(report, f, indent=2, ensure_ascii=False, default=str)
        
        print(f"Comprehensive report saved to: {output_file}")
        
        # Print executive summary
        executive_summary = report.get("executive_summary", {})
        print(f"\nExecutive Summary:")
        print(f"Health Score: {executive_summary.get('health_score', 0):.1f}/100")
        print(f"Overall Status: {executive_summary.get('overall_status', 'UNKNOWN')}")
        print(f"Success Rate: {executive_summary.get('key_metrics', {}).get('overall_success_rate', 0):.2%}")
        print(f"Match Accuracy: {executive_summary.get('key_metrics', {}).get('match_accuracy', 0):.2%}")
        
        # Print top priorities
        top_priorities = executive_summary.get("top_priorities", [])
        if top_priorities:
            print(f"\nTop Priorities:")
            for i, priority in enumerate(top_priorities[:3], 1):
                print(f"{i}. [{priority['priority']}] {priority['description']}")

def main():
    """Example usage of the JSON reporter"""
    import argparse
    
    parser = argparse.ArgumentParser(description="Generate comprehensive JSON report from test results")
    parser.add_argument("--test-results", required=True, help="JSON file containing test results")
    parser.add_argument("--output", default="comprehensive_report.json", help="Output file for report")
    parser.add_argument("--metadata", help="JSON file containing test run metadata")
    
    args = parser.parse_args()
    
    # Load test results
    with open(args.test_results, 'r', encoding='utf-8') as f:
        test_data = json.load(f)
    
    test_results = test_data.get("test_results", [])
    test_run_metadata = test_data.get("test_run_metadata", {})
    
    # Load additional metadata if provided
    if args.metadata:
        with open(args.metadata, 'r', encoding='utf-8') as f:
            additional_metadata = json.load(f)
        test_run_metadata.update(additional_metadata)
    
    # Generate report
    reporter = JSONReporter()
    report = reporter.generate_comprehensive_report(test_results, test_run_metadata)
    
    # Save report
    reporter.save_report(report, args.output)

if __name__ == "__main__":
    main()
