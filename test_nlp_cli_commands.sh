#!/bin/bash

# Test NLP Matching Layer via CLI
# Make sure you're in the supply-graph-ai directory with conda environment activated

echo "=== Testing NLP Matching Layer via CLI ==="
echo "Make sure conda environment 'supply-graph-ai' is activated"
echo ""

# Test 1: Basic matching with synthetic data
echo "Test 1: Basic matching with synthetic data"
if [ -f "synth/synthetic_data/arduino-based-iot-sensor-node-1-2-4-okh.json" ]; then
    python -m src.cli.main match requirements synth/synthetic_data/arduino-based-iot-sensor-node-1-2-4-okh.json --min-confidence 0.3 --max-results 10
else
    echo "Synthetic data not found, creating a simple test..."
    echo '{
      "title": "CLI Test Design",
      "version": "1.0.0",
      "manufacturing_specs": {
        "process_requirements": [
          {"process_name": "machining", "parameters": {}},
          {"process_name": "3D printing", "parameters": {}}
        ]
      }
    }' > cli_test_manifest.json
    
    python -m src.cli.main match requirements cli_test_manifest.json --min-confidence 0.3 --max-results 5
    rm cli_test_manifest.json
fi

echo -e "\n" + "="*50 + "\n"

# Test 2: Test with different confidence levels
echo "Test 2: Testing different confidence levels"
if [ -f "synth/synthetic_data/arduino-based-iot-sensor-node-1-2-4-okh.json" ]; then
    echo "Low confidence (0.2):"
    python -m src.cli.main match requirements synth/synthetic_data/arduino-based-iot-sensor-node-1-2-4-okh.json --min-confidence 0.2 --max-results 5 2>/dev/null || echo "Command failed, trying alternative..."

    echo "Medium confidence (0.5):"
    python -m src.cli.main match requirements synth/synthetic_data/arduino-based-iot-sensor-node-1-2-4-okh.json --min-confidence 0.5 --max-results 5 2>/dev/null || echo "Command failed, trying alternative..."

    echo "High confidence (0.8):"
    python -m src.cli.main match requirements synth/synthetic_data/arduino-based-iot-sensor-node-1-2-4-okh.json --min-confidence 0.8 --max-results 5 2>/dev/null || echo "Command failed, trying alternative..."
else
    echo "Synthetic data not found, skipping confidence level tests"
fi

echo -e "\n" + "="*50 + "\n"

# Test 3: Test with location filter (if available)
echo "Test 3: Testing with location filter"
if [ -f "synth/synthetic_data/arduino-based-iot-sensor-node-1-2-4-okh.json" ]; then
    python -m src.cli.main match requirements synth/synthetic_data/arduino-based-iot-sensor-node-1-2-4-okh.json --location "San Francisco" --min-confidence 0.3 2>/dev/null || echo "Location filter not available or command failed"
else
    echo "Synthetic data not found, skipping location filter test"
fi

echo -e "\n" + "="*50 + "\n"

# Test 4: Test with access type filter
echo "Test 4: Testing with access type filter"
if [ -f "synth/synthetic_data/arduino-based-iot-sensor-node-1-2-4-okh.json" ]; then
    python -m src.cli.main match requirements synth/synthetic_data/arduino-based-iot-sensor-node-1-2-4-okh.json --access-type public --min-confidence 0.3 2>/dev/null || echo "Access type filter not available or command failed"
else
    echo "Synthetic data not found, skipping access type filter test"
fi

echo -e "\n" + "="*50 + "\n"

# Test 5: Test with verbose output
echo "Test 5: Testing with verbose output"
if [ -f "synth/synthetic_data/arduino-based-iot-sensor-node-1-2-4-okh.json" ]; then
    python -m src.cli.main match requirements synth/synthetic_data/arduino-based-iot-sensor-node-1-2-4-okh.json --min-confidence 0.3 --max-results 3 --verbose 2>/dev/null || echo "Verbose option not available or command failed"
else
    echo "Synthetic data not found, skipping verbose output test"
fi

echo -e "\n" + "="*50 + "\n"
echo "CLI testing completed!"
echo ""
echo "Note: The NLP matching layer is integrated as Layer 3 in the matching system."
echo "Look for NLP-related metrics in the output to verify NLP matching is working."
