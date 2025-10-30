#!/usr/bin/env python3
"""
Edge Case Detector for OME Testing Framework

This module identifies problematic patterns, edge cases, and potential bugs
in the OME matching engine based on test results.

Usage:
    from analyzers.edge_case_detector import EdgeCaseDetector
    detector = EdgeCaseDetector()
    edge_cases = detector.detect_edge_cases(test_results)
"""

import json
from collections import defaultdict, Counter
from typing import Dict, List, Set, Any, Tuple
from datetime import datetime

class EdgeCaseDetector:
    """Detects edge cases and problematic patterns in OME matching results"""
    
    def __init__(self):
        # Define edge case patterns and their severity levels
        self.edge_case_patterns = {
            "empty_manufacturing_processes": {
                "severity": "high",
                "description": "OKH manifest has no manufacturing processes specified",
                "impact": "Matching engine cannot determine what needs to be manufactured"
            },
            "empty_okw_capabilities": {
                "severity": "high", 
                "description": "OKW facility has no equipment/capabilities",
                "impact": "No manufacturing capabilities available for matching"
            },
            "invalid_confidence_score": {
                "severity": "medium",
                "description": "Confidence score outside valid range [0,1]",
                "impact": "Invalid confidence scores indicate calculation errors"
            },
            "match_with_no_solutions": {
                "severity": "high",
                "description": "Match outcome but no solutions returned",
                "impact": "Inconsistent matching logic - claims match but provides no solutions"
            },
            "malformed_supply_tree": {
                "severity": "medium",
                "description": "SupplyTree missing required fields",
                "impact": "Generated solutions are incomplete or invalid"
            },
            "missing_metadata": {
                "severity": "low",
                "description": "Solutions missing metadata information",
                "impact": "Reduced traceability and debugging capability"
            },
            "extreme_confidence_scores": {
                "severity": "medium",
                "description": "Confidence scores at extreme values (0.0 or 1.0) consistently",
                "impact": "Matching engine may not be providing nuanced confidence assessment"
            },
            "unexpected_high_confidence": {
                "severity": "medium",
                "description": "High confidence for scenarios that should have low confidence",
                "impact": "Overconfident matching may lead to poor manufacturing decisions"
            },
            "unexpected_low_confidence": {
                "severity": "medium",
                "description": "Low confidence for scenarios that should have high confidence",
                "impact": "Underconfident matching may reject valid manufacturing solutions"
            },
            "inconsistent_outcomes": {
                "severity": "high",
                "description": "Same scenario type producing different outcomes",
                "impact": "Non-deterministic matching behavior"
            },
            "performance_anomalies": {
                "severity": "low",
                "description": "Unusually long processing times",
                "impact": "Performance issues may affect system scalability"
            },
            "field_validation_errors": {
                "severity": "medium",
                "description": "Invalid or malformed field values causing errors",
                "impact": "Data validation issues may cause matching failures"
            }
        }
    
    def detect_edge_cases(self, test_results: List[Dict]) -> Dict:
        """Detect edge cases across all test results"""
        edge_cases = {
            "detected_cases": defaultdict(list),
            "case_statistics": {},
            "severity_summary": {"high": 0, "medium": 0, "low": 0},
            "recommendations": [],
            "critical_issues": [],
            "performance_issues": []
        }
        
        # Analyze each test result for edge cases
        for result in test_results:
            if result.get("edge_case_detected", False):
                edge_case_details = result.get("edge_case_details", {})
                
                for case_type, details in edge_case_details.items():
                    edge_cases["detected_cases"][case_type].append({
                        "scenario_id": result["scenario_id"],
                        "scenario_type": result["scenario_type"],
                        "details": details,
                        "test_result": result
                    })
        
        # Calculate statistics
        edge_cases["case_statistics"] = self._calculate_case_statistics(edge_cases["detected_cases"])
        
        # Calculate severity summary
        for case_type, cases in edge_cases["detected_cases"].items():
            if case_type in self.edge_case_patterns:
                severity = self.edge_case_patterns[case_type]["severity"]
                edge_cases["severity_summary"][severity] += len(cases)
        
        # Detect additional patterns
        edge_cases.update(self._detect_additional_patterns(test_results))
        
        # Generate recommendations
        edge_cases["recommendations"] = self._generate_edge_case_recommendations(edge_cases)
        
        # Identify critical issues
        edge_cases["critical_issues"] = self._identify_critical_issues(edge_cases)
        
        return edge_cases
    
    def _calculate_case_statistics(self, detected_cases: Dict) -> Dict:
        """Calculate statistics for detected edge cases"""
        statistics = {}
        
        for case_type, cases in detected_cases.items():
            if cases:
                statistics[case_type] = {
                    "total_occurrences": len(cases),
                    "unique_scenarios": len(set(case["scenario_id"] for case in cases)),
                    "scenario_types_affected": list(set(case["scenario_type"] for case in cases)),
                    "severity": self.edge_case_patterns.get(case_type, {}).get("severity", "unknown"),
                    "impact": self.edge_case_patterns.get(case_type, {}).get("impact", "Unknown impact")
                }
        
        return statistics
    
    def _detect_additional_patterns(self, test_results: List[Dict]) -> Dict:
        """Detect additional edge case patterns not caught by individual test analysis"""
        additional_patterns = {
            "confidence_anomalies": [],
            "performance_anomalies": [],
            "inconsistent_outcomes": [],
            "field_validation_errors": []
        }
        
        # Analyze confidence score patterns
        confidence_scores = []
        for result in test_results:
            if result.get("actual_confidence") is not None:
                confidence_scores.append({
                    "scenario_id": result["scenario_id"],
                    "scenario_type": result["scenario_type"],
                    "confidence": result["actual_confidence"],
                    "expected_confidence": result.get("expected_confidence"),
                    "success": result.get("success", False)
                })
        
        # Detect extreme confidence scores
        extreme_high = [c for c in confidence_scores if c["confidence"] >= 0.95]
        extreme_low = [c for c in confidence_scores if c["confidence"] <= 0.05]
        
        if len(extreme_high) > len(confidence_scores) * 0.8:  # More than 80% are extreme high
            additional_patterns["confidence_anomalies"].append({
                "pattern": "extreme_confidence_scores",
                "description": "More than 80% of confidence scores are at extreme values",
                "severity": "medium",
                "affected_scenarios": len(extreme_high),
                "examples": extreme_high[:5]
            })
        
        # Detect unexpected confidence patterns
        for conf_data in confidence_scores:
            expected = conf_data.get("expected_confidence")
            actual = conf_data["confidence"]
            
            if expected is not None:
                diff = abs(actual - expected)
                if diff > 0.3:  # Large difference between expected and actual
                    if actual > expected + 0.3:
                        additional_patterns["confidence_anomalies"].append({
                            "pattern": "unexpected_high_confidence",
                            "scenario_id": conf_data["scenario_id"],
                            "expected": expected,
                            "actual": actual,
                            "difference": diff,
                            "severity": "medium"
                        })
                    elif actual < expected - 0.3:
                        additional_patterns["confidence_anomalies"].append({
                            "pattern": "unexpected_low_confidence",
                            "scenario_id": conf_data["scenario_id"],
                            "expected": expected,
                            "actual": actual,
                            "difference": diff,
                            "severity": "medium"
                        })
        
        # Analyze performance patterns
        durations = [r.get("duration", 0) for r in test_results if r.get("duration")]
        if durations:
            avg_duration = sum(durations) / len(durations)
            slow_tests = [r for r in test_results if r.get("duration", 0) > avg_duration * 3]
            
            if slow_tests:
                additional_patterns["performance_anomalies"].append({
                    "pattern": "performance_anomalies",
                    "description": f"{len(slow_tests)} tests took more than 3x average duration",
                    "severity": "low",
                    "average_duration": avg_duration,
                    "slow_tests": [
                        {
                            "scenario_id": t["scenario_id"],
                            "duration": t.get("duration"),
                            "scenario_type": t.get("scenario_type")
                        }
                        for t in slow_tests[:5]
                    ]
                })
        
        # Detect inconsistent outcomes for same scenario types
        scenario_type_outcomes = defaultdict(list)
        for result in test_results:
            scenario_type = result.get("scenario_type")
            outcome = result.get("actual_outcome")
            if scenario_type and outcome:
                scenario_type_outcomes[scenario_type].append(outcome)
        
        for scenario_type, outcomes in scenario_type_outcomes.items():
            unique_outcomes = set(outcomes)
            if len(unique_outcomes) > 1:  # Multiple different outcomes for same type
                outcome_counts = Counter(outcomes)
                additional_patterns["inconsistent_outcomes"].append({
                    "pattern": "inconsistent_outcomes",
                    "scenario_type": scenario_type,
                    "outcomes": dict(outcome_counts),
                    "severity": "high",
                    "description": f"Scenario type '{scenario_type}' produces {len(unique_outcomes)} different outcomes"
                })
        
        # Detect field validation errors
        error_results = [r for r in test_results if r.get("error_message")]
        if error_results:
            error_types = defaultdict(int)
            for result in error_results:
                error_msg = result.get("error_message", "")
                # Categorize error types
                if "validation" in error_msg.lower():
                    error_types["validation_error"] += 1
                elif "not found" in error_msg.lower():
                    error_types["not_found_error"] += 1
                elif "timeout" in error_msg.lower():
                    error_types["timeout_error"] += 1
                else:
                    error_types["other_error"] += 1
            
            additional_patterns["field_validation_errors"].append({
                "pattern": "field_validation_errors",
                "description": f"{len(error_results)} tests failed with errors",
                "severity": "medium",
                "error_types": dict(error_types),
                "examples": [
                    {
                        "scenario_id": r["scenario_id"],
                        "error_message": r.get("error_message", "")[:100] + "..." if len(r.get("error_message", "")) > 100 else r.get("error_message", "")
                    }
                    for r in error_results[:5]
                ]
            })
        
        return additional_patterns
    
    def _generate_edge_case_recommendations(self, edge_cases: Dict) -> List[str]:
        """Generate recommendations based on detected edge cases"""
        recommendations = []
        
        # High severity recommendations
        high_severity_cases = edge_cases["detected_cases"]
        for case_type, cases in high_severity_cases.items():
            if case_type in self.edge_case_patterns:
                severity = self.edge_case_patterns[case_type]["severity"]
                if severity == "high":
                    recommendations.append(
                        f"CRITICAL: Fix {case_type} - {len(cases)} occurrences. "
                        f"{self.edge_case_patterns[case_type]['description']}"
                    )
        
        # Medium severity recommendations
        for case_type, cases in high_severity_cases.items():
            if case_type in self.edge_case_patterns:
                severity = self.edge_case_patterns[case_type]["severity"]
                if severity == "medium" and len(cases) > 5:
                    recommendations.append(
                        f"HIGH: Address {case_type} - {len(cases)} occurrences. "
                        f"{self.edge_case_patterns[case_type]['description']}"
                    )
        
        # Additional pattern recommendations
        if edge_cases.get("confidence_anomalies"):
            recommendations.append(
                "MEDIUM: Review confidence score calculation logic - multiple confidence anomalies detected"
            )
        
        if edge_cases.get("inconsistent_outcomes"):
            recommendations.append(
                "HIGH: Fix inconsistent outcomes for same scenario types - indicates non-deterministic behavior"
            )
        
        if edge_cases.get("performance_anomalies"):
            recommendations.append(
                "LOW: Investigate performance issues - some tests taking unusually long"
            )
        
        if edge_cases.get("field_validation_errors"):
            recommendations.append(
                "MEDIUM: Improve field validation - multiple validation errors detected"
            )
        
        return recommendations
    
    def _identify_critical_issues(self, edge_cases: Dict) -> List[Dict]:
        """Identify the most critical issues that need immediate attention"""
        critical_issues = []
        
        # High severity cases with high occurrence
        for case_type, cases in edge_cases["detected_cases"].items():
            if case_type in self.edge_case_patterns:
                severity = self.edge_case_patterns[case_type]["severity"]
                if severity == "high" and len(cases) >= 3:
                    critical_issues.append({
                        "issue_type": case_type,
                        "severity": "critical",
                        "occurrences": len(cases),
                        "description": self.edge_case_patterns[case_type]["description"],
                        "impact": self.edge_case_patterns[case_type]["impact"],
                        "affected_scenarios": [case["scenario_id"] for case in cases[:5]]
                    })
        
        # Inconsistent outcomes
        for inconsistent in edge_cases.get("inconsistent_outcomes", []):
            critical_issues.append({
                "issue_type": "inconsistent_outcomes",
                "severity": "critical",
                "description": inconsistent["description"],
                "impact": "Non-deterministic matching behavior",
                "scenario_type": inconsistent["scenario_type"],
                "outcomes": inconsistent["outcomes"]
            })
        
        return critical_issues
    
    def generate_edge_case_report(self, test_results: List[Dict]) -> Dict:
        """Generate a edge case detection report"""
        edge_cases = self.detect_edge_cases(test_results)
        
        report = {
            "report_metadata": {
                "generated_at": datetime.now().isoformat(),
                "total_tests_analyzed": len(test_results),
                "detector_version": "1.0.0"
            },
            "summary": {
                "total_edge_cases": sum(len(cases) for cases in edge_cases["detected_cases"].values()),
                "unique_edge_case_types": len(edge_cases["detected_cases"]),
                "high_severity_cases": edge_cases["severity_summary"]["high"],
                "medium_severity_cases": edge_cases["severity_summary"]["medium"],
                "low_severity_cases": edge_cases["severity_summary"]["low"],
                "critical_issues": len(edge_cases["critical_issues"])
            },
            "edge_case_analysis": edge_cases,
            "top_recommendations": edge_cases["recommendations"][:10]  # Top 10 recommendations
        }
        
        return report

def main():
    """Example usage of the edge case detector"""
    import argparse
    
    parser = argparse.ArgumentParser(description="Detect edge cases from test results")
    parser.add_argument("--test-results", required=True, help="JSON file containing test results")
    parser.add_argument("--output", default="edge_case_report.json", help="Output file for edge case report")
    
    args = parser.parse_args()
    
    # Load test results
    with open(args.test_results, 'r', encoding='utf-8') as f:
        test_data = json.load(f)
    
    test_results = test_data.get("test_results", [])
    
    # Detect edge cases
    detector = EdgeCaseDetector()
    report = detector.generate_edge_case_report(test_results)
    
    # Save report
    with open(args.output, 'w', encoding='utf-8') as f:
        json.dump(report, f, indent=2, ensure_ascii=False)
    
    print(f"Edge case report saved to: {args.output}")
    
    # Print summary
    summary = report["summary"]
    print(f"\nEdge Case Detection Summary:")
    print(f"Total edge cases: {summary['total_edge_cases']}")
    print(f"Unique edge case types: {summary['unique_edge_case_types']}")
    print(f"High severity cases: {summary['high_severity_cases']}")
    print(f"Medium severity cases: {summary['medium_severity_cases']}")
    print(f"Low severity cases: {summary['low_severity_cases']}")
    print(f"Critical issues: {summary['critical_issues']}")
    
    print(f"\nTop Recommendations:")
    for i, rec in enumerate(report["top_recommendations"], 1):
        print(f"{i}. {rec}")

if __name__ == "__main__":
    main()
