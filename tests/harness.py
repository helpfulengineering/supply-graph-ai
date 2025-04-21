import requests
import json
import os
import time
import logging
import uuid
from datetime import datetime
from typing import Dict, Any, List, Optional, Union

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("tests/test_runs.log"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger("ome-test-harness")

class TestHarness:
    """Test harness for OME API testing"""
    
    def __init__(self, base_url: str = "http://localhost:8000"):
        self.base_url = base_url
        self.session = requests.Session()
        self.test_results = []
        self.current_run_id = str(uuid.uuid4())
        self.run_timestamp = datetime.now().isoformat()
        
        # Create results directory if it doesn't exist
        os.makedirs("tests/results", exist_ok=True)
    
    def run_test(self, test_name: str, endpoint: str, 
                method: str = "GET", data: Optional[Dict] = None,
                expected_status_code: int = 200,
                expected_fields: Optional[List[str]] = None) -> Dict:
        """
        Run a single API test
        
        Args:
            test_name: Name of the test
            endpoint: API endpoint (relative to base_url)
            method: HTTP method to use
            data: Request data for POST/PUT methods
            expected_status_code: Expected HTTP status code
            expected_fields: List of fields that should be in the response
            
        Returns:
            Test result information
        """
        url = f"{self.base_url}/{endpoint.lstrip('/')}"
        start_time = time.time()
        
        logger.info(f"Running test: {test_name}")
        logger.info(f"Request: {method} {url}")
        if data:
            logger.info(f"Request data: {json.dumps(data)}")
        
        # Make request
        try:
            if method.upper() == "GET":
                response = self.session.get(url)
            elif method.upper() == "POST":
                response = self.session.post(url, json=data)
            elif method.upper() == "PUT":
                response = self.session.put(url, json=data)
            elif method.upper() == "DELETE":
                response = self.session.delete(url)
            else:
                raise ValueError(f"Unsupported HTTP method: {method}")
            
            duration = time.time() - start_time
            
            # Process response
            status_code = response.status_code
            try:
                response_data = response.json() if response.text else {}
            except json.JSONDecodeError:
                response_data = {"raw_text": response.text}
            
            # Check expected status code
            status_match = status_code == expected_status_code
            
            # Check expected fields
            fields_match = True
            missing_fields = []
            if expected_fields and status_match:
                for field in expected_fields:
                    if field not in response_data:
                        fields_match = False
                        missing_fields.append(field)
            
            # Determine overall success
            success = status_match and fields_match
            
            # Log results
            if success:
                logger.info(f"Test {test_name} PASSED")
            else:
                logger.error(f"Test {test_name} FAILED")
                if not status_match:
                    logger.error(f"Expected status code {expected_status_code}, got {status_code}")
                if missing_fields:
                    logger.error(f"Missing expected fields: {', '.join(missing_fields)}")
            
            # Save response for analysis
            response_file = f"tests/results/{self.current_run_id}_{test_name.replace(' ', '_')}.json"
            with open(response_file, 'w') as f:
                json.dump({
                    "test_name": test_name,
                    "url": url,
                    "method": method,
                    "request_data": data,
                    "response_code": status_code,
                    "response_data": response_data,
                    "duration_ms": round(duration * 1000, 2)
                }, f, indent=2)
            
            # Prepare result
            result = {
                "test_name": test_name,
                "success": success,
                "status_code": status_code,
                "expected_status_code": expected_status_code,
                "duration_ms": round(duration * 1000, 2),
                "missing_fields": missing_fields,
                "response_file": response_file,
                "timestamp": datetime.now().isoformat()
            }
            
            self.test_results.append(result)
            return result
            
        except Exception as e:
            logger.error(f"Exception during test {test_name}: {str(e)}")
            duration = time.time() - start_time
            
            result = {
                "test_name": test_name,
                "success": False,
                "error": str(e),
                "duration_ms": round(duration * 1000, 2),
                "timestamp": datetime.now().isoformat()
            }
            
            self.test_results.append(result)
            return result
    
    def generate_report(self) -> Dict:
        """Generate summary report for all tests"""
        total_tests = len(self.test_results)
        passed_tests = sum(1 for r in self.test_results if r.get("success", False))
        failed_tests = total_tests - passed_tests
        
        total_duration = sum(r.get("duration_ms", 0) for r in self.test_results)
        
        report = {
            "run_id": self.current_run_id,
            "timestamp": self.run_timestamp,
            "total_tests": total_tests,
            "passed_tests": passed_tests,
            "failed_tests": failed_tests,
            "success_rate": round((passed_tests / total_tests) * 100, 2) if total_tests > 0 else 0,
            "total_duration_ms": total_duration,
            "test_results": self.test_results
        }
        
        # Save report
        report_file = f"tests/results/{self.current_run_id}_report.json"
        with open(report_file, 'w') as f:
            json.dump(report, f, indent=2)
        
        logger.info(f"Test run complete: {passed_tests}/{total_tests} tests passed ({report['success_rate']}%)")
        logger.info(f"Report saved to {report_file}")
        
        return report

class TestSuite:
    """Collection of OME API tests"""
    
    def __init__(self, harness: TestHarness):
        self.harness = harness
    
    def run_health_check(self) -> Dict:
        """Test the health check endpoint"""
        return self.harness.run_test(
            test_name="Health Check",
            endpoint="health",
            method="GET",
            expected_status_code=200,
            expected_fields=["status"]
        )
    
    def run_basic_cooking_match(self) -> Dict:
        """Test basic cooking domain matching"""
        recipe = {
            "type": "recipe",
            "content": {
                "name": "Simple Pasta",
                "ingredients": [
                    {"name": "pasta", "amount": "200g"},
                    {"name": "tomato sauce", "amount": "300g"},
                    {"name": "grated cheese", "amount": "50g"}
                ],
                "instructions": [
                    "Boil water in a large pot.",
                    "Add pasta and cook according to package instructions.",
                    "Drain pasta and return to pot.",
                    "Heat tomato sauce in a separate pan.",
                    "Mix sauce with pasta.",
                    "Serve with grated cheese on top."
                ],
                "equipment": [
                    "large pot",
                    "strainer",
                    "pan"
                ]
            }
        }

        kitchen = {
            "type": "kitchen",
            "content": {
                "name": "Home Kitchen",
                "tools": [
                    "large pot",
                    "strainer",
                    "pan",
                    "knife",
                    "cutting board"
                ],
                "appliances": [
                    "stove",
                    "oven",
                    "refrigerator"
                ],
                "ingredients": [
                    {"name": "pasta", "amount": "500g"},
                    {"name": "tomato sauce", "amount": "500g"},
                    {"name": "grated cheese", "amount": "100g"},
                    {"name": "salt", "amount": "50g"}
                ]
            }
        }
        
        return self.harness.run_test(
            test_name="Basic Cooking Match",
            endpoint="match",
            method="POST",
            data={
                "requirements": recipe,
                "capabilities": kitchen
            },
            expected_status_code=200,
            expected_fields=["id", "domain", "workflows", "confidence", "validation_status"]
        )
    
    def run_invalid_match_test(self) -> Dict:
        """Test with invalid input (missing type field)"""
        return self.harness.run_test(
            test_name="Invalid Match Input",
            endpoint="match",
            method="POST",
            data={
                "requirements": {
                    "content": {"name": "Invalid Recipe"}
                    # Missing type field
                },
                "capabilities": {
                    "type": "kitchen",
                    "content": {"name": "Test Kitchen"}
                }
            },
            expected_status_code=422  # Changed from 400 to 422
        )
    
    def run_all_tests(self) -> Dict:
        """Run all test cases"""
        self.run_health_check()
        self.run_basic_cooking_match()
        self.run_invalid_match_test()
        
        return self.harness.generate_report()