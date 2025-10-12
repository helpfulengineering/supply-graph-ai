# OME Testing Framework

This directory contains a comprehensive testing framework for the Open Matching Engine (OME). The framework provides systematic testing capabilities to identify bugs, edge cases, and areas for improvement in the OME matching system.

## Overview

The OME Testing Framework consists of several key components:

1. **Enhanced Synthetic Data Generation** - Generates realistic OKH and OKW files with comprehensive field coverage
2. **Test Scenario Generation** - Creates specific test cases for different matching scenarios
3. **Test Harness** - Executes tests and validates results
4. **Analyzers** - Analyze field coverage, edge cases, and match quality
5. **Reporting** - Generate comprehensive JSON reports with actionable insights

## Quick Start

### 1. Generate Test Scenarios

```bash
# Generate all types of test scenarios (10 of each type)
python tests/run_matching_tests.py --generate-scenarios --count 10 --scenario-output ./test_scenarios

# Generate specific scenario types
python tests/run_matching_tests.py --generate-scenarios --count 20 --scenario-types exact_match,partial_match --scenario-output ./test_scenarios
```

### 2. Run Tests

```bash
# Run all tests and generate comprehensive report
python tests/run_matching_tests.py --scenarios ./test_scenarios --output ./reports

# Run specific scenario types only
python tests/run_matching_tests.py --scenarios ./test_scenarios --scenario-types exact_match,partial_match --output ./reports
```

### 3. View Results

The framework generates several output files:

- `raw_test_results.json` - Raw test execution results
- `comprehensive_report.json` - Complete analysis with recommendations
- `execution_summary.json` - High-level summary of the test run

## Test Scenario Types

### Exact Match Scenarios
- **Purpose**: Test perfect matches between OKH requirements and OKW capabilities
- **Expected Outcome**: High confidence matches
- **Example**: CNC machining requirement matched with CNC machine shop

### Partial Match Scenarios
- **Purpose**: Test scenarios where some requirements match but others don't
- **Expected Outcome**: Partial matches with moderate confidence
- **Example**: Multi-process requirement where only some processes are available

### Near Miss Scenarios
- **Purpose**: Test heuristic matching with typos, case differences, and synonyms
- **Expected Outcome**: Matches found through fuzzy matching
- **Example**: "CNC Machinng" matched with "CNC Machining"

### No Match Scenarios
- **Purpose**: Test scenarios where no matches should be found
- **Expected Outcome**: No matches returned
- **Example**: Advanced composite manufacturing vs basic makerspace

### Edge Case Scenarios
- **Purpose**: Test boundary conditions and unusual inputs
- **Expected Outcome**: Varies (may reveal bugs or edge case handling)
- **Examples**: Empty manufacturing processes, extreme precision requirements

## Framework Components

### Test Harness (`test_harness_matching.py`)

The core testing infrastructure that:
- Loads test scenarios from files
- Executes matching operations through the OME API
- Validates responses against expected outcomes
- Captures detailed results for analysis

**Key Features:**
- Async execution for performance
- Progress reporting
- Error handling and recovery
- Field usage analysis
- Edge case detection

### Field Coverage Analyzer (`analyzers/field_coverage.py`)

Analyzes which OKH and OKW fields are being used in matching:

**Metrics:**
- Field utilization rates
- Unused fields identification
- Critical field coverage analysis
- Field effectiveness scoring

**Output:**
- Fields that are never checked
- Fields that are underutilized
- Recommendations for field implementation

### Edge Case Detector (`analyzers/edge_case_detector.py`)

Identifies problematic patterns and potential bugs:

**Detected Patterns:**
- Empty manufacturing processes
- Invalid confidence scores
- Malformed SupplyTree objects
- Inconsistent outcomes
- Performance anomalies

**Severity Levels:**
- **High**: Critical issues requiring immediate attention
- **Medium**: Important issues that should be addressed
- **Low**: Minor issues for future consideration

### Match Quality Analyzer (`analyzers/match_quality.py`)

Evaluates matching accuracy and confidence calibration:

**Quality Metrics:**
- Overall accuracy rate
- Precision and recall
- Confidence score distribution
- False positive/negative analysis
- Confidence calibration error

**Performance Metrics:**
- Average processing time
- Duration distribution
- Slow test identification

### JSON Reporter (`reporters/json_reporter.py`)

Generates comprehensive reports combining all analyses:

**Report Sections:**
- Executive summary with health score
- Field coverage analysis
- Edge case detection results
- Match quality assessment
- Integrated recommendations
- Top priorities for improvement

## Usage Examples

### Basic Testing Workflow

```bash
# 1. Generate test scenarios
python tests/run_matching_tests.py --generate-scenarios --count 20 --scenario-output ./scenarios

# 2. Run tests
python tests/run_matching_tests.py --scenarios ./scenarios --output ./reports

# 3. View results
cat ./reports/execution_summary.json | jq '.system_health'
```

### Focused Testing

```bash
# Test only exact matches
python tests/run_matching_tests.py --scenarios ./scenarios --scenario-types exact_match --output ./reports

# Test edge cases specifically
python tests/run_matching_tests.py --scenarios ./scenarios --scenario-types edge_case --output ./reports
```

### Large-Scale Testing

```bash
# Generate and test 100 scenarios of each type
python tests/run_matching_tests.py --generate-scenarios --count 100 --scenario-output ./large_test
python tests/run_matching_tests.py --scenarios ./large_test --output ./large_reports
```

## Interpreting Results

### Health Score (0-100)

The framework calculates an overall health score based on:
- **Success Rate (40%)**: Percentage of tests that passed
- **Accuracy (30%)**: How often expected outcomes match actual outcomes
- **Field Coverage (20%)**: Percentage of available fields being used
- **Edge Cases (10%)**: Penalty for detected edge cases

**Health Score Ranges:**
- **80-100**: HEALTHY - System is performing well
- **60-79**: NEEDS_ATTENTION - Some issues need addressing
- **0-59**: CRITICAL - Major issues require immediate attention

### Key Metrics

**Success Rate**: Percentage of tests that met their expected outcomes
**Match Accuracy**: How often the matching engine correctly predicts outcomes
**Field Coverage**: Percentage of OKH/OKW fields being utilized in matching
**Confidence Calibration**: How well confidence scores reflect actual match quality

### Recommendations

The framework provides prioritized recommendations:

- **CRITICAL**: Issues that must be fixed immediately
- **HIGH**: Important issues that should be addressed soon
- **MEDIUM**: Issues that should be addressed in the next development cycle
- **LOW**: Minor issues for future consideration

## Configuration

### API Configuration

The framework connects to the OME API. Configure the API URL:

```bash
python tests/run_matching_tests.py --api-url http://localhost:8001 --scenarios ./scenarios
```

### Scenario Generation

Control scenario generation with parameters:

```bash
# Generate specific types
python tests/run_matching_tests.py --generate-scenarios --scenario-types exact_match,partial_match --count 15

# Generate all types
python tests/run_matching_tests.py --generate-scenarios --count 25
```

## Troubleshooting

### Common Issues

**No scenarios found:**
```
Error: No scenario files found in ./scenarios
```
- Ensure scenarios were generated successfully
- Check that the scenario directory contains `*_metadata.json` files

**API connection failed:**
```
Error: Failed to initialize test harness
```
- Verify the OME API is running
- Check the API URL is correct
- Ensure network connectivity

**Test failures:**
```
[1/50] exact_match_001: FAIL
```
- Check the comprehensive report for detailed failure analysis
- Look at edge case detection results
- Review field coverage analysis

### Debug Mode

For detailed debugging, examine the raw test results:

```bash
# View raw results
cat ./reports/raw_test_results.json | jq '.test_results[0]'

# View specific test failure
cat ./reports/raw_test_results.json | jq '.test_results[] | select(.scenario_id == "exact_match_001")'
```

## Extending the Framework

### Adding New Scenario Types

1. Add new scenario generation method to `TestScenarioGenerator`
2. Update scenario type validation in `run_matching_tests.py`
3. Add expected outcomes to `MatchQualityAnalyzer`

### Adding New Analyzers

1. Create new analyzer class in `analyzers/` directory
2. Implement analysis methods
3. Integrate with `JSONReporter`
4. Update `run_matching_tests.py` to use new analyzer

### Custom Field Analysis

1. Modify field lists in `FieldCoverageAnalyzer`
2. Update field usage detection logic
3. Add new field effectiveness metrics

## Best Practices

### Test Data Management

- Use version control for test scenarios
- Maintain separate directories for different test runs
- Archive old test results for comparison

### Continuous Integration

- Run tests automatically on code changes
- Set up alerts for health score drops
- Track metrics over time

### Performance Testing

- Use large scenario counts for performance validation
- Monitor test execution times
- Identify slow test patterns

### Quality Assurance

- Review recommendations regularly
- Prioritize critical and high-priority issues
- Track improvement over time

## File Structure

```
tests/
├── README.md                          # This documentation
├── test_harness_matching.py           # Core test harness
├── run_matching_tests.py              # Main execution script
├── analyzers/
│   ├── field_coverage.py              # Field usage analysis
│   ├── edge_case_detector.py          # Edge case detection
│   └── match_quality.py               # Match quality analysis
└── reporters/
    └── json_reporter.py               # Comprehensive reporting
```

## Dependencies

The testing framework requires:
- Python 3.8+
- OME API running and accessible
- JSON processing capabilities
- Async/await support
- Statistical analysis libraries

## Contributing

When contributing to the testing framework:

1. Follow the existing code structure
2. Add comprehensive documentation
3. Include example usage
4. Test your changes thoroughly
5. Update this README if needed

## Support

For issues with the testing framework:
1. Check this documentation
2. Review the generated reports for insights
3. Examine raw test results for debugging
4. Create issues with detailed error information
