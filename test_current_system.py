#!/usr/bin/env python3
"""
Test script for the current Open Matching Engine system
Demonstrates the enhanced matching capabilities
"""

import requests
import json
import time
from typing import Dict, Any

class OMETester:
    def __init__(self, base_url: str = "http://localhost:8001"):
        self.base_url = base_url
        self.session = requests.Session()
    
    def test_health(self) -> Dict[str, Any]:
        """Test system health"""
        print("🏥 Testing Health Check...")
        try:
            response = self.session.get(f"{self.base_url}/health")
            if response.status_code == 200:
                data = response.json()
                print(f"✅ Health Check: {data['status']}")
                print(f"   Domains: {', '.join(data['domains'])}")
                print(f"   Version: {data['version']}")
                return {"success": True, "data": data}
            else:
                print(f"❌ Health Check Failed: {response.status_code}")
                return {"success": False, "error": response.text}
        except Exception as e:
            print(f"❌ Health Check Exception: {e}")
            return {"success": False, "error": str(e)}
    
    def test_domains(self) -> Dict[str, Any]:
        """Test available domains"""
        print("\n🌍 Testing Available Domains...")
        try:
            response = self.session.get(f"{self.base_url}/v1/domains")
            if response.status_code == 200:
                data = response.json()
                print(f"✅ Available Domains: {len(data['domains'])}")
                for domain in data['domains']:
                    print(f"   - {domain['id']}: {domain['name']}")
                return {"success": True, "data": data}
            else:
                print(f"❌ Domains Test Failed: {response.status_code}")
                return {"success": False, "error": response.text}
        except Exception as e:
            print(f"❌ Domains Test Exception: {e}")
            return {"success": False, "error": str(e)}
    
    def test_enhanced_matching(self) -> Dict[str, Any]:
        """Test the enhanced matching endpoint"""
        print("\n🎯 Testing Enhanced Matching...")
        
        # Sample OKH manifest for manufacturing (with required fields)
        okh_manifest = {
            "title": "Demo Hardware Project",
            "repo": "https://github.com/example/demo-hardware",
            "version": "1.0.0",
            "license": {
                "hardware": "CERN-OHL-S-2.0",
                "software": "MIT",
                "documentation": "CC-BY-SA-4.0"
            },
            "licensor": "Demo Organization",
            "documentation_language": "en",
            "function": "A demonstration hardware project for testing the matching system",
            "description": "This is a test hardware project to demonstrate the enhanced matching capabilities",
            "manufacturing_processes": ["3D Printing", "CNC Milling"]
        }
        
        # Test different scenarios
        test_cases = [
            {
                "name": "Basic Matching",
                "data": {
                    "okh_manifest": okh_manifest
                }
            },
            {
                "name": "With OKW Filters",
                "data": {
                    "okh_manifest": okh_manifest,
                    "okw_filters": {
                        "access_type": "public",
                        "capabilities": ["3D Printing", "CNC Milling"]
                    }
                }
            },
            {
                "name": "With Optimization Criteria",
                "data": {
                    "okh_manifest": okh_manifest,
                    "okw_filters": {
                        "location": {
                            "country": "United States"
                        }
                    },
                    "optimization_criteria": {
                        "cost": 0.4,
                        "quality": 0.4,
                        "speed": 0.2
                    }
                }
            }
        ]
        
        results = []
        for test_case in test_cases:
            print(f"\n   🧪 {test_case['name']}...")
            try:
                start_time = time.time()
                response = self.session.post(
                    f"{self.base_url}/v1/match",
                    json=test_case['data'],
                    timeout=30
                )
                duration = time.time() - start_time
                
                if response.status_code == 200:
                    data = response.json()
                    solution_count = len(data.get('solutions', []))
                    print(f"   ✅ Success! Found {solution_count} solutions in {duration:.2f}s")
                    
                    if data.get('metadata'):
                        metadata = data['metadata']
                        print(f"      Facility Count: {metadata.get('facility_count', 'N/A')}")
                        print(f"      Solution Count: {metadata.get('solution_count', 'N/A')}")
                    
                    results.append({
                        "name": test_case['name'],
                        "success": True,
                        "solutions": solution_count,
                        "duration": duration,
                        "data": data
                    })
                else:
                    print(f"   ❌ Failed: {response.status_code}")
                    print(f"      Error: {response.text[:200]}...")
                    results.append({
                        "name": test_case['name'],
                        "success": False,
                        "error": response.text,
                        "status_code": response.status_code
                    })
                    
            except Exception as e:
                print(f"   ❌ Exception: {e}")
                results.append({
                    "name": test_case['name'],
                    "success": False,
                    "error": str(e)
                })
        
        return {"success": True, "results": results}
    
    def test_okw_listing(self) -> Dict[str, Any]:
        """Test OKW facility listing"""
        print("\n🏭 Testing OKW Facility Listing...")
        try:
            response = self.session.get(f"{self.base_url}/v1/okw")
            if response.status_code == 200:
                data = response.json()
                total = data.get('total', 0)
                print(f"✅ OKW Facilities: {total} total")
                if total > 0:
                    print(f"   Page: {data.get('page', 1)}")
                    print(f"   Page Size: {data.get('page_size', 20)}")
                return {"success": True, "data": data}
            else:
                print(f"❌ OKW Listing Failed: {response.status_code}")
                return {"success": False, "error": response.text}
        except Exception as e:
            print(f"❌ OKW Listing Exception: {e}")
            return {"success": False, "error": str(e)}
    
    def run_all_tests(self) -> Dict[str, Any]:
        """Run all tests"""
        print("🚀 Starting Open Matching Engine Tests")
        print("=" * 50)
        
        start_time = time.time()
        
        # Run tests
        health_result = self.test_health()
        domains_result = self.test_domains()
        okw_result = self.test_okw_listing()
        matching_result = self.test_enhanced_matching()
        
        total_duration = time.time() - start_time
        
        # Summary
        print("\n" + "=" * 50)
        print("📊 TEST SUMMARY")
        print("=" * 50)
        
        tests = [
            ("Health Check", health_result),
            ("Domains", domains_result),
            ("OKW Listing", okw_result),
            ("Enhanced Matching", matching_result)
        ]
        
        passed = 0
        total = len(tests)
        
        for test_name, result in tests:
            status = "✅ PASS" if result.get("success") else "❌ FAIL"
            print(f"{test_name:20} {status}")
            if result.get("success"):
                passed += 1
        
        print(f"\nTotal Tests: {total}")
        print(f"Passed: {passed}")
        print(f"Failed: {total - passed}")
        print(f"Success Rate: {(passed/total)*100:.1f}%")
        print(f"Total Duration: {total_duration:.2f}s")
        
        # API Documentation reminder
        print(f"\n📚 API Documentation: {self.base_url}/v1/docs")
        print(f"🏥 Health Check: {self.base_url}/health")
        
        return {
            "total_tests": total,
            "passed_tests": passed,
            "failed_tests": total - passed,
            "success_rate": (passed/total)*100,
            "total_duration": total_duration,
            "results": {
                "health": health_result,
                "domains": domains_result,
                "okw": okw_result,
                "matching": matching_result
            }
        }

def main():
    """Main function"""
    tester = OMETester()
    results = tester.run_all_tests()
    
    # Save results
    with open("test_results.json", "w") as f:
        json.dump(results, f, indent=2)
    
    print(f"\n💾 Results saved to: test_results.json")

if __name__ == "__main__":
    main()
