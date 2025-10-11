#!/usr/bin/env python3
"""
Field Coverage Analyzer for OME Testing Framework

This module analyzes which OKH and OKW fields are being used in the matching
process and identifies fields that are not being utilized.

Usage:
    from analyzers.field_coverage import FieldCoverageAnalyzer
    analyzer = FieldCoverageAnalyzer()
    coverage_report = analyzer.analyze_test_results(test_results)
"""

import json
from collections import defaultdict, Counter
from typing import Dict, List, Set, Any
from datetime import datetime

class FieldCoverageAnalyzer:
    """Analyzes field coverage in OME matching results"""
    
    def __init__(self):
        # Define all possible OKH fields
        self.okh_fields = {
            "title", "version", "license", "licensor", "documentation_language", "function",
            "description", "intended_use", "keywords", "project_link", "health_safety_notice",
            "contact", "contributors", "organization", "image", "version_date", "readme",
            "contribution_guide", "development_stage", "attestation", "technology_readiness_level",
            "documentation_readiness_level", "manufacturing_files", "documentation_home",
            "archive_download", "design_files", "making_instructions", "operating_instructions",
            "tool_list", "manufacturing_processes", "materials", "manufacturing_specs", "bom",
            "standards_used", "cpc_patent_class", "tsdc", "parts", "derivative_of", "variant_of",
            "sub_parts", "software", "metadata"
        }
        
        # Define all possible OKW fields
        self.okw_fields = {
            "name", "location", "facility_status", "owner", "contact", "affiliations",
            "opening_hours", "description", "date_founded", "access_type", "wheelchair_accessibility",
            "equipment", "manufacturing_processes", "typical_batch_size", "floor_size",
            "storage_capacity", "typical_materials", "certifications", "backup_generator",
            "uninterrupted_power_supply", "road_access", "loading_dock", "maintenance_schedule",
            "typical_products", "partners_funders", "customer_reviews", "circular_economy",
            "human_capacity", "innovation_space", "record_data"
        }
        
        # Define critical fields that should definitely be used in matching
        self.critical_okh_fields = {
            "manufacturing_processes", "materials", "tool_list", "standards_used",
            "manufacturing_specs", "parts"
        }
        
        self.critical_okw_fields = {
            "manufacturing_processes", "equipment", "typical_materials", "certifications",
            "typical_batch_size", "access_type", "facility_status"
        }
    
    def analyze_test_results(self, test_results: List[Dict]) -> Dict:
        """Analyze field coverage across all test results"""
        coverage_data = {
            "okh_field_usage": defaultdict(int),
            "okw_field_usage": defaultdict(int),
            "okh_fields_available": defaultdict(int),
            "okw_fields_available": defaultdict(int),
            "field_utilization_rates": {},
            "unused_fields": {"okh": [], "okw": []},
            "underutilized_fields": {"okh": [], "okw": []},
            "critical_field_coverage": {"okh": {}, "okw": {}},
            "field_effectiveness": {},
            "recommendations": []
        }
        
        total_tests = len(test_results)
        if total_tests == 0:
            return coverage_data
        
        # Analyze each test result
        for result in test_results:
            if "field_usage" in result:
                field_usage = result["field_usage"]
                
                # Track available fields
                for field, value in field_usage.get("okh_fields_available", {}).items():
                    if value:  # Field has a value
                        coverage_data["okh_fields_available"][field] += 1
                
                for field, value in field_usage.get("okw_fields_available", {}).items():
                    if value:  # Field has a value
                        coverage_data["okw_fields_available"][field] += 1
                
                # Track used fields
                for field in field_usage.get("fields_used_in_matching", []):
                    coverage_data["okh_field_usage"][field] += 1
                    coverage_data["okw_field_usage"][field] += 1
                
                # Track unused fields
                for field in field_usage.get("fields_not_used", []):
                    if field in self.okh_fields:
                        coverage_data["unused_fields"]["okh"].append(field)
                    elif field in self.okw_fields:
                        coverage_data["unused_fields"]["okw"].append(field)
        
        # Calculate utilization rates
        coverage_data["field_utilization_rates"] = self._calculate_utilization_rates(
            coverage_data["okh_fields_available"], coverage_data["okh_field_usage"]
        )
        
        # Identify unused and underutilized fields
        coverage_data["unused_fields"]["okh"] = self._find_unused_fields(
            coverage_data["okh_fields_available"], coverage_data["okh_field_usage"], total_tests
        )
        coverage_data["unused_fields"]["okw"] = self._find_unused_fields(
            coverage_data["okw_fields_available"], coverage_data["okw_field_usage"], total_tests
        )
        
        coverage_data["underutilized_fields"]["okh"] = self._find_underutilized_fields(
            coverage_data["okh_fields_available"], coverage_data["okh_field_usage"], total_tests
        )
        coverage_data["underutilized_fields"]["okw"] = self._find_underutilized_fields(
            coverage_data["okw_fields_available"], coverage_data["okw_field_usage"], total_tests
        )
        
        # Analyze critical field coverage
        coverage_data["critical_field_coverage"] = self._analyze_critical_fields(
            coverage_data["okh_fields_available"], coverage_data["okw_fields_available"],
            coverage_data["okh_field_usage"], coverage_data["okw_field_usage"], total_tests
        )
        
        # Calculate field effectiveness
        coverage_data["field_effectiveness"] = self._calculate_field_effectiveness(test_results)
        
        # Generate recommendations
        coverage_data["recommendations"] = self._generate_recommendations(coverage_data)
        
        return coverage_data
    
    def _calculate_utilization_rates(self, available_fields: Dict, used_fields: Dict) -> Dict:
        """Calculate utilization rates for fields"""
        utilization_rates = {}
        
        for field in self.okh_fields.union(self.okw_fields):
            available_count = available_fields.get(field, 0)
            used_count = used_fields.get(field, 0)
            
            if available_count > 0:
                utilization_rates[field] = used_count / available_count
            else:
                utilization_rates[field] = 0.0
        
        return utilization_rates
    
    def _find_unused_fields(self, available_fields: Dict, used_fields: Dict, total_tests: int) -> List[str]:
        """Find fields that are never used in matching"""
        unused_fields = []
        
        for field in self.okh_fields.union(self.okw_fields):
            available_count = available_fields.get(field, 0)
            used_count = used_fields.get(field, 0)
            
            # Field is unused if it's available but never used
            if available_count > 0 and used_count == 0:
                unused_fields.append(field)
        
        return unused_fields
    
    def _find_underutilized_fields(self, available_fields: Dict, used_fields: Dict, total_tests: int) -> List[str]:
        """Find fields that are underutilized (used less than 50% of the time when available)"""
        underutilized_fields = []
        
        for field in self.okh_fields.union(self.okw_fields):
            available_count = available_fields.get(field, 0)
            used_count = used_fields.get(field, 0)
            
            if available_count > 0:
                utilization_rate = used_count / available_count
                # Consider underutilized if used less than 50% of the time
                if utilization_rate < 0.5:
                    underutilized_fields.append(field)
        
        return underutilized_fields
    
    def _analyze_critical_fields(self, okh_available: Dict, okw_available: Dict, 
                               okh_used: Dict, okw_used: Dict, total_tests: int) -> Dict:
        """Analyze coverage of critical fields"""
        critical_coverage = {"okh": {}, "okw": {}}
        
        # Analyze critical OKH fields
        for field in self.critical_okh_fields:
            available_count = okh_available.get(field, 0)
            used_count = okh_used.get(field, 0)
            
            critical_coverage["okh"][field] = {
                "available_in_tests": available_count,
                "used_in_tests": used_count,
                "utilization_rate": used_count / available_count if available_count > 0 else 0.0,
                "is_well_covered": used_count / available_count >= 0.8 if available_count > 0 else False
            }
        
        # Analyze critical OKW fields
        for field in self.critical_okw_fields:
            available_count = okw_available.get(field, 0)
            used_count = okw_used.get(field, 0)
            
            critical_coverage["okw"][field] = {
                "available_in_tests": available_count,
                "used_in_tests": used_count,
                "utilization_rate": used_count / available_count if available_count > 0 else 0.0,
                "is_well_covered": used_count / available_count >= 0.8 if available_count > 0 else False
            }
        
        return critical_coverage
    
    def _calculate_field_effectiveness(self, test_results: List[Dict]) -> Dict:
        """Calculate effectiveness of fields in producing successful matches"""
        field_effectiveness = defaultdict(lambda: {"successful_matches": 0, "total_matches": 0})
        
        for result in test_results:
            if "field_usage" in result and "fields_used_in_matching" in result["field_usage"]:
                used_fields = result["field_usage"]["fields_used_in_matching"]
                is_successful = result.get("success", False)
                
                for field in used_fields:
                    field_effectiveness[field]["total_matches"] += 1
                    if is_successful:
                        field_effectiveness[field]["successful_matches"] += 1
        
        # Calculate effectiveness rates
        effectiveness_rates = {}
        for field, stats in field_effectiveness.items():
            if stats["total_matches"] > 0:
                effectiveness_rates[field] = {
                    "success_rate": stats["successful_matches"] / stats["total_matches"],
                    "total_matches": stats["total_matches"],
                    "successful_matches": stats["successful_matches"]
                }
        
        return effectiveness_rates
    
    def _generate_recommendations(self, coverage_data: Dict) -> List[str]:
        """Generate recommendations based on field coverage analysis"""
        recommendations = []
        
        # Check for unused critical fields
        unused_okh_critical = set(coverage_data["unused_fields"]["okh"]) & self.critical_okh_fields
        unused_okw_critical = set(coverage_data["unused_fields"]["okw"]) & self.critical_okw_fields
        
        if unused_okh_critical:
            recommendations.append(
                f"CRITICAL: Implement matching for unused OKH fields: {', '.join(unused_okh_critical)}"
            )
        
        if unused_okw_critical:
            recommendations.append(
                f"CRITICAL: Implement matching for unused OKW fields: {', '.join(unused_okw_critical)}"
            )
        
        # Check for underutilized critical fields
        underutilized_okh_critical = set(coverage_data["underutilized_fields"]["okh"]) & self.critical_okh_fields
        underutilized_okw_critical = set(coverage_data["underutilized_fields"]["okw"]) & self.critical_okw_fields
        
        if underutilized_okh_critical:
            recommendations.append(
                f"HIGH: Improve matching logic for underutilized OKH fields: {', '.join(underutilized_okh_critical)}"
            )
        
        if underutilized_okw_critical:
            recommendations.append(
                f"HIGH: Improve matching logic for underutilized OKW fields: {', '.join(underutilized_okw_critical)}"
            )
        
        # Check for low effectiveness fields
        low_effectiveness_fields = [
            field for field, stats in coverage_data["field_effectiveness"].items()
            if stats["success_rate"] < 0.5 and stats["total_matches"] >= 5
        ]
        
        if low_effectiveness_fields:
            recommendations.append(
                f"MEDIUM: Review matching logic for low-effectiveness fields: {', '.join(low_effectiveness_fields)}"
            )
        
        # Check for completely unused fields
        all_unused = coverage_data["unused_fields"]["okh"] + coverage_data["unused_fields"]["okw"]
        if len(all_unused) > 10:
            recommendations.append(
                f"LOW: Consider implementing matching for {len(all_unused)} unused fields to improve coverage"
            )
        
        # Check critical field coverage
        okh_critical_coverage = coverage_data["critical_field_coverage"]["okh"]
        okw_critical_coverage = coverage_data["critical_field_coverage"]["okw"]
        
        poorly_covered_okh = [
            field for field, stats in okh_critical_coverage.items()
            if not stats["is_well_covered"] and stats["available_in_tests"] > 0
        ]
        
        poorly_covered_okw = [
            field for field, stats in okw_critical_coverage.items()
            if not stats["is_well_covered"] and stats["available_in_tests"] > 0
        ]
        
        if poorly_covered_okh:
            recommendations.append(
                f"HIGH: Improve coverage of critical OKH fields: {', '.join(poorly_covered_okh)}"
            )
        
        if poorly_covered_okw:
            recommendations.append(
                f"HIGH: Improve coverage of critical OKW fields: {', '.join(poorly_covered_okw)}"
            )
        
        return recommendations
    
    def generate_coverage_report(self, test_results: List[Dict]) -> Dict:
        """Generate a comprehensive field coverage report"""
        coverage_data = self.analyze_test_results(test_results)
        
        report = {
            "report_metadata": {
                "generated_at": datetime.now().isoformat(),
                "total_tests_analyzed": len(test_results),
                "analyzer_version": "1.0.0"
            },
            "summary": {
                "total_okh_fields": len(self.okh_fields),
                "total_okw_fields": len(self.okw_fields),
                "unused_okh_fields": len(coverage_data["unused_fields"]["okh"]),
                "unused_okw_fields": len(coverage_data["unused_fields"]["okw"]),
                "underutilized_okh_fields": len(coverage_data["underutilized_fields"]["okh"]),
                "underutilized_okw_fields": len(coverage_data["underutilized_fields"]["okw"]),
                "critical_fields_well_covered": sum(
                    1 for field_stats in coverage_data["critical_field_coverage"]["okh"].values()
                    if field_stats["is_well_covered"]
                ) + sum(
                    1 for field_stats in coverage_data["critical_field_coverage"]["okw"].values()
                    if field_stats["is_well_covered"]
                ),
                "total_critical_fields": len(self.critical_okh_fields) + len(self.critical_okw_fields)
            },
            "field_analysis": coverage_data,
            "top_recommendations": coverage_data["recommendations"][:5]  # Top 5 recommendations
        }
        
        return report

def main():
    """Example usage of the field coverage analyzer"""
    import argparse
    
    parser = argparse.ArgumentParser(description="Analyze field coverage from test results")
    parser.add_argument("--test-results", required=True, help="JSON file containing test results")
    parser.add_argument("--output", default="field_coverage_report.json", help="Output file for coverage report")
    
    args = parser.parse_args()
    
    # Load test results
    with open(args.test_results, 'r', encoding='utf-8') as f:
        test_data = json.load(f)
    
    test_results = test_data.get("test_results", [])
    
    # Analyze field coverage
    analyzer = FieldCoverageAnalyzer()
    report = analyzer.generate_coverage_report(test_results)
    
    # Save report
    with open(args.output, 'w', encoding='utf-8') as f:
        json.dump(report, f, indent=2, ensure_ascii=False)
    
    print(f"Field coverage report saved to: {args.output}")
    
    # Print summary
    summary = report["summary"]
    print(f"\nField Coverage Summary:")
    print(f"Total OKH fields: {summary['total_okh_fields']}")
    print(f"Total OKW fields: {summary['total_okw_fields']}")
    print(f"Unused OKH fields: {summary['unused_okh_fields']}")
    print(f"Unused OKW fields: {summary['unused_okw_fields']}")
    print(f"Critical fields well covered: {summary['critical_fields_well_covered']}/{summary['total_critical_fields']}")
    
    print(f"\nTop Recommendations:")
    for i, rec in enumerate(report["top_recommendations"], 1):
        print(f"{i}. {rec}")

if __name__ == "__main__":
    main()
