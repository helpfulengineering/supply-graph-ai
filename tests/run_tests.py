from harness import TestHarness, TestSuite
import argparse

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Run OHM API tests")
    parser.add_argument("--url", type=str, default="http://localhost:8001", 
                        help="Base URL for API")
    args = parser.parse_args()
    
    # Create test harness
    harness = TestHarness(base_url=args.url)
    suite = TestSuite(harness)
    
    # Run all tests
    report = suite.run_all_tests()
    
    # Print summary
    print("\nTest Summary:")
    print(f"Total Tests: {report['total_tests']}")
    print(f"Passed: {report['passed_tests']}")
    print(f"Failed: {report['failed_tests']}")
    print(f"Success Rate: {report['success_rate']}%")
    print(f"Total Duration: {report['total_duration_ms']}ms")