#!/usr/bin/env python3
"""
Match Quality Analyzer for OME Testing Framework

This module evaluates the quality and accuracy of matching results,
analyzing confidence scores, false positives/negatives, and overall
matching performance.

Usage:
    from analyzers.match_quality import MatchQualityAnalyzer
    analyzer = MatchQualityAnalyzer()
    quality_report = analyzer.analyze_match_quality(test_results)
"""

import json
from collections import defaultdict, Counter
from typing import Dict, List, Set, Any, Tuple
from datetime import datetime
import statistics

class MatchQualityAnalyzer:
    """Analyzes the quality and accuracy of OME matching results"""
    
    def __init__(self):
        # Define quality metrics thresholds
        self.quality_thresholds = {
            "excellent_confidence": 0.9,
            "good_confidence": 0.7,
            "acceptable_confidence": 0.5,
            "poor_confidence": 0.3
        }
        
        # Define expected outcomes for different scenario types
        self.expected_outcomes = {
            "exact_match": "match",
            "partial_match": "partial_match", 
            "near_miss": "match",
            "no_match": "no_match",
            "edge_case": "unknown"  # Edge cases may have unpredictable outcomes
        }
    
    def analyze_match_quality(self, test_results: List[Dict]) -> Dict:
        """Analyze match quality across all test results"""
        quality_analysis = {
            "overall_metrics": {},
            "confidence_analysis": {},
            "accuracy_analysis": {},
            "scenario_type_analysis": {},
            "false_positives": [],
            "false_negatives": [],
            "confidence_calibration": {},
            "performance_metrics": {},
            "quality_recommendations": []
        }
        
        # Calculate overall metrics
        quality_analysis["overall_metrics"] = self._calculate_overall_metrics(test_results)
        
        # Analyze confidence scores
        quality_analysis["confidence_analysis"] = self._analyze_confidence_scores(test_results)
        
        # Analyze accuracy
        quality_analysis["accuracy_analysis"] = self._analyze_accuracy(test_results)
        
        # Analyze by scenario type
        quality_analysis["scenario_type_analysis"] = self._analyze_by_scenario_type(test_results)
        
        # Identify false positives and negatives
        quality_analysis["false_positives"], quality_analysis["false_negatives"] = self._identify_false_results(test_results)
        
        # Analyze confidence calibration
        quality_analysis["confidence_calibration"] = self._analyze_confidence_calibration(test_results)
        
        # Calculate performance metrics
        quality_analysis["performance_metrics"] = self._calculate_performance_metrics(test_results)
        
        # Generate quality recommendations
        quality_analysis["quality_recommendations"] = self._generate_quality_recommendations(quality_analysis)
        
        return quality_analysis
    
    def _calculate_overall_metrics(self, test_results: List[Dict]) -> Dict:
        """Calculate overall quality metrics"""
        total_tests = len(test_results)
        if total_tests == 0:
            return {}
        
        successful_tests = sum(1 for r in test_results if r.get("success", False))
        failed_tests = total_tests - successful_tests
        
        # Calculate confidence statistics
        confidence_scores = [r.get("actual_confidence", 0) for r in test_results if r.get("actual_confidence") is not None]
        
        confidence_stats = {}
        if confidence_scores:
            confidence_stats = {
                "mean": statistics.mean(confidence_scores),
                "median": statistics.median(confidence_scores),
                "std_dev": statistics.stdev(confidence_scores) if len(confidence_scores) > 1 else 0,
                "min": min(confidence_scores),
                "max": max(confidence_scores),
                "count": len(confidence_scores)
            }
        
        # Calculate outcome distribution
        outcome_counts = Counter(r.get("actual_outcome", "unknown") for r in test_results)
        
        return {
            "total_tests": total_tests,
            "successful_tests": successful_tests,
            "failed_tests": failed_tests,
            "success_rate": successful_tests / total_tests,
            "confidence_statistics": confidence_stats,
            "outcome_distribution": dict(outcome_counts)
        }
    
    def _analyze_confidence_scores(self, test_results: List[Dict]) -> Dict:
        """Analyze confidence score patterns and quality"""
        confidence_analysis = {
            "score_distribution": {},
            "quality_categories": {},
            "confidence_trends": {},
            "anomalies": []
        }
        
        # Get all confidence scores
        confidence_data = []
        for result in test_results:
            if result.get("actual_confidence") is not None:
                confidence_data.append({
                    "confidence": result["actual_confidence"],
                    "scenario_type": result.get("scenario_type", "unknown"),
                    "success": result.get("success", False),
                    "scenario_id": result.get("scenario_id", "")
                })
        
        if not confidence_data:
            return confidence_analysis
        
        # Analyze score distribution
        scores = [d["confidence"] for d in confidence_data]
        confidence_analysis["score_distribution"] = {
            "excellent": len([s for s in scores if s >= self.quality_thresholds["excellent_confidence"]]),
            "good": len([s for s in scores if self.quality_thresholds["good_confidence"] <= s < self.quality_thresholds["excellent_confidence"]]),
            "acceptable": len([s for s in scores if self.quality_thresholds["acceptable_confidence"] <= s < self.quality_thresholds["good_confidence"]]),
            "poor": len([s for s in scores if s < self.quality_thresholds["acceptable_confidence"]])
        }
        
        # Analyze by quality categories
        for category, threshold in self.quality_thresholds.items():
            if category == "excellent_confidence":
                category_scores = [d for d in confidence_data if d["confidence"] >= threshold]
            elif category == "good_confidence":
                category_scores = [d for d in confidence_data if threshold <= d["confidence"] < self.quality_thresholds["excellent_confidence"]]
            elif category == "acceptable_confidence":
                category_scores = [d for d in confidence_data if threshold <= d["confidence"] < self.quality_thresholds["good_confidence"]]
            else:  # poor_confidence
                category_scores = [d for d in confidence_data if d["confidence"] < self.quality_thresholds["acceptable_confidence"]]
            
            if category_scores:
                success_rate = sum(1 for d in category_scores if d["success"]) / len(category_scores)
                confidence_analysis["quality_categories"][category] = {
                    "count": len(category_scores),
                    "success_rate": success_rate,
                    "avg_confidence": statistics.mean([d["confidence"] for d in category_scores])
                }
        
        # Analyze confidence trends by scenario type
        scenario_confidence = defaultdict(list)
        for d in confidence_data:
            scenario_confidence[d["scenario_type"]].append(d["confidence"])
        
        for scenario_type, scores in scenario_confidence.items():
            if scores:
                confidence_analysis["confidence_trends"][scenario_type] = {
                    "mean": statistics.mean(scores),
                    "median": statistics.median(scores),
                    "std_dev": statistics.stdev(scores) if len(scores) > 1 else 0,
                    "count": len(scores)
                }
        
        # Detect confidence anomalies
        confidence_analysis["anomalies"] = self._detect_confidence_anomalies(confidence_data)
        
        return confidence_analysis
    
    def _analyze_accuracy(self, test_results: List[Dict]) -> Dict:
        """Analyze matching accuracy and correctness"""
        accuracy_analysis = {
            "correct_predictions": 0,
            "incorrect_predictions": 0,
            "accuracy_rate": 0.0,
            "precision": 0.0,
            "recall": 0.0,
            "f1_score": 0.0,
            "scenario_accuracy": {}
        }
        
        # Calculate overall accuracy
        correct = 0
        total = 0
        
        for result in test_results:
            expected = result.get("expected_outcome")
            actual = result.get("actual_outcome")
            
            if expected and actual:
                total += 1
                if expected == actual:
                    correct += 1
        
        if total > 0:
            accuracy_analysis["correct_predictions"] = correct
            accuracy_analysis["incorrect_predictions"] = total - correct
            accuracy_analysis["accuracy_rate"] = correct / total
        
        # Calculate precision, recall, F1 for match predictions
        true_positives = 0
        false_positives = 0
        false_negatives = 0
        
        for result in test_results:
            expected = result.get("expected_outcome")
            actual = result.get("actual_outcome")
            
            if expected == "match" and actual == "match":
                true_positives += 1
            elif expected != "match" and actual == "match":
                false_positives += 1
            elif expected == "match" and actual != "match":
                false_negatives += 1
        
        if true_positives + false_positives > 0:
            accuracy_analysis["precision"] = true_positives / (true_positives + false_positives)
        
        if true_positives + false_negatives > 0:
            accuracy_analysis["recall"] = true_positives / (true_positives + false_negatives)
        
        if accuracy_analysis["precision"] + accuracy_analysis["recall"] > 0:
            accuracy_analysis["f1_score"] = 2 * (accuracy_analysis["precision"] * accuracy_analysis["recall"]) / (accuracy_analysis["precision"] + accuracy_analysis["recall"])
        
        # Calculate accuracy by scenario type
        scenario_accuracy = defaultdict(lambda: {"correct": 0, "total": 0})
        
        for result in test_results:
            scenario_type = result.get("scenario_type", "unknown")
            expected = result.get("expected_outcome")
            actual = result.get("actual_outcome")
            
            if expected and actual:
                scenario_accuracy[scenario_type]["total"] += 1
                if expected == actual:
                    scenario_accuracy[scenario_type]["correct"] += 1
        
        for scenario_type, stats in scenario_accuracy.items():
            if stats["total"] > 0:
                accuracy_analysis["scenario_accuracy"][scenario_type] = {
                    "accuracy": stats["correct"] / stats["total"],
                    "correct": stats["correct"],
                    "total": stats["total"]
                }
        
        return accuracy_analysis
    
    def _analyze_by_scenario_type(self, test_results: List[Dict]) -> Dict:
        """Analyze quality metrics by scenario type"""
        scenario_analysis = {}
        
        # Group results by scenario type
        by_scenario_type = defaultdict(list)
        for result in test_results:
            scenario_type = result.get("scenario_type", "unknown")
            by_scenario_type[scenario_type].append(result)
        
        # Analyze each scenario type
        for scenario_type, results in by_scenario_type.items():
            if not results:
                continue
            
            # Calculate metrics for this scenario type
            total = len(results)
            successful = sum(1 for r in results if r.get("success", False))
            
            # Confidence analysis
            confidences = [r.get("actual_confidence", 0) for r in results if r.get("actual_confidence") is not None]
            
            # Outcome analysis
            outcomes = [r.get("actual_outcome", "unknown") for r in results]
            outcome_counts = Counter(outcomes)
            
            scenario_analysis[scenario_type] = {
                "total_tests": total,
                "successful_tests": successful,
                "success_rate": successful / total,
                "confidence_stats": {
                    "mean": statistics.mean(confidences) if confidences else 0,
                    "median": statistics.median(confidences) if confidences else 0,
                    "std_dev": statistics.stdev(confidences) if len(confidences) > 1 else 0,
                    "count": len(confidences)
                },
                "outcome_distribution": dict(outcome_counts),
                "expected_vs_actual": self._analyze_expected_vs_actual(results)
            }
        
        return scenario_analysis
    
    def _analyze_expected_vs_actual(self, results: List[Dict]) -> Dict:
        """Analyze expected vs actual outcomes for a set of results"""
        expected_vs_actual = {
            "matches": 0,
            "mismatches": 0,
            "match_rate": 0.0,
            "mismatch_details": []
        }
        
        for result in results:
            expected = result.get("expected_outcome")
            actual = result.get("actual_outcome")
            
            if expected and actual:
                if expected == actual:
                    expected_vs_actual["matches"] += 1
                else:
                    expected_vs_actual["mismatches"] += 1
                    expected_vs_actual["mismatch_details"].append({
                        "scenario_id": result.get("scenario_id", ""),
                        "expected": expected,
                        "actual": actual,
                        "confidence": result.get("actual_confidence", 0)
                    })
        
        total = expected_vs_actual["matches"] + expected_vs_actual["mismatches"]
        if total > 0:
            expected_vs_actual["match_rate"] = expected_vs_actual["matches"] / total
        
        return expected_vs_actual
    
    def _identify_false_results(self, test_results: List[Dict]) -> Tuple[List[Dict], List[Dict]]:
        """Identify false positives and false negatives"""
        false_positives = []
        false_negatives = []
        
        for result in test_results:
            expected = result.get("expected_outcome")
            actual = result.get("actual_outcome")
            
            if expected == "no_match" and actual == "match":
                # False positive: expected no match but got a match
                false_positives.append({
                    "scenario_id": result.get("scenario_id", ""),
                    "scenario_type": result.get("scenario_type", ""),
                    "confidence": result.get("actual_confidence", 0),
                    "solutions_count": result.get("solutions_count", 0)
                })
            elif expected == "match" and actual == "no_match":
                # False negative: expected a match but got no match
                false_negatives.append({
                    "scenario_id": result.get("scenario_id", ""),
                    "scenario_type": result.get("scenario_type", ""),
                    "expected_confidence": result.get("expected_confidence", 0)
                })
        
        return false_positives, false_negatives
    
    def _analyze_confidence_calibration(self, test_results: List[Dict]) -> Dict:
        """Analyze how well confidence scores are calibrated"""
        calibration_analysis = {
            "calibration_error": 0.0,
            "reliability_diagram": {},
            "overconfident_predictions": 0,
            "underconfident_predictions": 0
        }
        
        # Group predictions by confidence bins
        confidence_bins = defaultdict(list)
        
        for result in test_results:
            confidence = result.get("actual_confidence", 0)
            success = result.get("success", False)
            
            # Bin confidence scores
            bin_key = f"{int(confidence * 10) / 10:.1f}-{int(confidence * 10) / 10 + 0.1:.1f}"
            confidence_bins[bin_key].append(success)
        
        # Calculate calibration error
        total_error = 0.0
        total_predictions = 0
        
        for bin_key, successes in confidence_bins.items():
            if successes:
                bin_confidence = float(bin_key.split('-')[0]) + 0.05  # Midpoint of bin
                actual_success_rate = sum(successes) / len(successes)
                error = abs(bin_confidence - actual_success_rate)
                total_error += error * len(successes)
                total_predictions += len(successes)
                
                calibration_analysis["reliability_diagram"][bin_key] = {
                    "expected_success_rate": bin_confidence,
                    "actual_success_rate": actual_success_rate,
                    "calibration_error": error,
                    "count": len(successes)
                }
        
        if total_predictions > 0:
            calibration_analysis["calibration_error"] = total_error / total_predictions
        
        # Count overconfident and underconfident predictions
        for bin_key, successes in confidence_bins.items():
            if successes:
                bin_confidence = float(bin_key.split('-')[0]) + 0.05
                actual_success_rate = sum(successes) / len(successes)
                
                if bin_confidence > actual_success_rate + 0.1:
                    calibration_analysis["overconfident_predictions"] += len(successes)
                elif bin_confidence < actual_success_rate - 0.1:
                    calibration_analysis["underconfident_predictions"] += len(successes)
        
        return calibration_analysis
    
    def _calculate_performance_metrics(self, test_results: List[Dict]) -> Dict:
        """Calculate performance-related metrics"""
        performance_metrics = {
            "average_duration": 0.0,
            "duration_distribution": {},
            "slow_tests": [],
            "fast_tests": []
        }
        
        durations = [r.get("duration", 0) for r in test_results if r.get("duration")]
        
        if durations:
            performance_metrics["average_duration"] = statistics.mean(durations)
            
            # Duration distribution
            performance_metrics["duration_distribution"] = {
                "min": min(durations),
                "max": max(durations),
                "median": statistics.median(durations),
                "std_dev": statistics.stdev(durations) if len(durations) > 1 else 0
            }
            
            # Identify slow and fast tests
            avg_duration = performance_metrics["average_duration"]
            
            for result in test_results:
                duration = result.get("duration", 0)
                if duration > avg_duration * 2:  # More than 2x average
                    performance_metrics["slow_tests"].append({
                        "scenario_id": result.get("scenario_id", ""),
                        "duration": duration,
                        "scenario_type": result.get("scenario_type", "")
                    })
                elif duration < avg_duration * 0.5:  # Less than half average
                    performance_metrics["fast_tests"].append({
                        "scenario_id": result.get("scenario_id", ""),
                        "duration": duration,
                        "scenario_type": result.get("scenario_type", "")
                    })
        
        return performance_metrics
    
    def _detect_confidence_anomalies(self, confidence_data: List[Dict]) -> List[Dict]:
        """Detect anomalies in confidence scores"""
        anomalies = []
        
        if not confidence_data:
            return anomalies
        
        scores = [d["confidence"] for d in confidence_data]
        
        # Detect extreme values
        if len(scores) > 1:
            mean_score = statistics.mean(scores)
            std_dev = statistics.stdev(scores)
            
            for d in confidence_data:
                z_score = abs(d["confidence"] - mean_score) / std_dev if std_dev > 0 else 0
                
                if z_score > 2:  # More than 2 standard deviations from mean
                    anomalies.append({
                        "type": "extreme_confidence",
                        "scenario_id": d["scenario_id"],
                        "confidence": d["confidence"],
                        "z_score": z_score,
                        "scenario_type": d["scenario_type"]
                    })
        
        # Detect confidence-success mismatches
        for d in confidence_data:
            if d["confidence"] > 0.8 and not d["success"]:
                anomalies.append({
                    "type": "high_confidence_failure",
                    "scenario_id": d["scenario_id"],
                    "confidence": d["confidence"],
                    "scenario_type": d["scenario_type"]
                })
            elif d["confidence"] < 0.2 and d["success"]:
                anomalies.append({
                    "type": "low_confidence_success",
                    "scenario_id": d["scenario_id"],
                    "confidence": d["confidence"],
                    "scenario_type": d["scenario_type"]
                })
        
        return anomalies
    
    def _generate_quality_recommendations(self, quality_analysis: Dict) -> List[str]:
        """Generate recommendations based on quality analysis"""
        recommendations = []
        
        # Overall quality recommendations
        overall_metrics = quality_analysis["overall_metrics"]
        if overall_metrics.get("success_rate", 0) < 0.8:
            recommendations.append(
                f"HIGH: Improve overall success rate - currently {overall_metrics['success_rate']:.2%}, target is 80%+"
            )
        
        # Confidence calibration recommendations
        calibration = quality_analysis["confidence_calibration"]
        if calibration.get("calibration_error", 0) > 0.1:
            recommendations.append(
                f"MEDIUM: Improve confidence calibration - calibration error is {calibration['calibration_error']:.3f}, target is <0.1"
            )
        
        # Accuracy recommendations
        accuracy = quality_analysis["accuracy_analysis"]
        if accuracy.get("accuracy_rate", 0) < 0.9:
            recommendations.append(
                f"HIGH: Improve prediction accuracy - currently {accuracy['accuracy_rate']:.2%}, target is 90%+"
            )
        
        # False positive/negative recommendations
        false_positives = quality_analysis["false_positives"]
        false_negatives = quality_analysis["false_negatives"]
        
        if len(false_positives) > 5:
            recommendations.append(
                f"MEDIUM: Reduce false positives - {len(false_positives)} cases where no match was expected but match was found"
            )
        
        if len(false_negatives) > 5:
            recommendations.append(
                f"MEDIUM: Reduce false negatives - {len(false_negatives)} cases where match was expected but no match was found"
            )
        
        # Scenario-specific recommendations
        scenario_analysis = quality_analysis["scenario_type_analysis"]
        for scenario_type, analysis in scenario_analysis.items():
            if analysis.get("success_rate", 0) < 0.7:
                recommendations.append(
                    f"MEDIUM: Improve {scenario_type} scenario success rate - currently {analysis['success_rate']:.2%}"
                )
        
        return recommendations
    
    def generate_quality_report(self, test_results: List[Dict]) -> Dict:
        """Generate a comprehensive match quality report"""
        quality_analysis = self.analyze_match_quality(test_results)
        
        report = {
            "report_metadata": {
                "generated_at": datetime.now().isoformat(),
                "total_tests_analyzed": len(test_results),
                "analyzer_version": "1.0.0"
            },
            "summary": {
                "overall_success_rate": quality_analysis["overall_metrics"].get("success_rate", 0),
                "overall_accuracy": quality_analysis["accuracy_analysis"].get("accuracy_rate", 0),
                "average_confidence": quality_analysis["overall_metrics"].get("confidence_statistics", {}).get("mean", 0),
                "calibration_error": quality_analysis["confidence_calibration"].get("calibration_error", 0),
                "false_positives": len(quality_analysis["false_positives"]),
                "false_negatives": len(quality_analysis["false_negatives"])
            },
            "quality_analysis": quality_analysis,
            "top_recommendations": quality_analysis["quality_recommendations"][:10]
        }
        
        return report

def main():
    """Example usage of the match quality analyzer"""
    import argparse
    
    parser = argparse.ArgumentParser(description="Analyze match quality from test results")
    parser.add_argument("--test-results", required=True, help="JSON file containing test results")
    parser.add_argument("--output", default="match_quality_report.json", help="Output file for quality report")
    
    args = parser.parse_args()
    
    # Load test results
    with open(args.test_results, 'r', encoding='utf-8') as f:
        test_data = json.load(f)
    
    test_results = test_data.get("test_results", [])
    
    # Analyze match quality
    analyzer = MatchQualityAnalyzer()
    report = analyzer.generate_quality_report(test_results)
    
    # Save report
    with open(args.output, 'w', encoding='utf-8') as f:
        json.dump(report, f, indent=2, ensure_ascii=False)
    
    print(f"Match quality report saved to: {args.output}")
    
    # Print summary
    summary = report["summary"]
    print(f"\nMatch Quality Summary:")
    print(f"Overall success rate: {summary['overall_success_rate']:.2%}")
    print(f"Overall accuracy: {summary['overall_accuracy']:.2%}")
    print(f"Average confidence: {summary['average_confidence']:.3f}")
    print(f"Calibration error: {summary['calibration_error']:.3f}")
    print(f"False positives: {summary['false_positives']}")
    print(f"False negatives: {summary['false_negatives']}")
    
    print(f"\nTop Recommendations:")
    for i, rec in enumerate(report["top_recommendations"], 1):
        print(f"{i}. {rec}")

if __name__ == "__main__":
    main()
