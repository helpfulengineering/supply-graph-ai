#!/bin/bash
 
# Test NLP Matching Layer via API Server
# Make sure the API server is running on port 8001

echo "=== Testing NLP Matching Layer via API ==="
echo "Server should be running on http://localhost:8001"
echo ""

# Test 1: Basic matching with OKH manifest
echo "Test 1: Basic matching with OKH manifest"
curl -X POST "http://localhost:8001/v1/match" \
  -H "Content-Type: application/json" \
  -d '{
    "okh_manifest": {
      "title": "NLP Test Design",
      "version": "1.0.0",
      "manufacturing_specs": {
        "process_requirements": [
          {
            "process_name": "machining",
            "parameters": {}
          },
          {
            "process_name": "3D printing", 
            "parameters": {}
          }
        ]
      }
    },
    "min_confidence": 0.5,
    "max_results": 5
  }' | jq '.'

echo -e "\n" + "="*50 + "\n"

# Test 2: Test with semantic similarity (lower threshold)
echo "Test 2: Testing semantic similarity with lower threshold"
curl -X POST "http://localhost:8001/v1/match" \
  -H "Content-Type: application/json" \
  -d '{
    "okh_manifest": {
      "title": "Semantic Similarity Test",
      "version": "1.0.0", 
      "manufacturing_specs": {
        "process_requirements": [
          {
            "process_name": "Computer Numerical Control machining",
            "parameters": {}
          },
          {
            "process_name": "Additive manufacturing",
            "parameters": {}
          },
          {
            "process_name": "Surface finishing",
            "parameters": {}
          }
        ]
      }
    },
    "min_confidence": 0.3,
    "max_results": 10
  }' | jq '.'

echo -e "\n" + "="*50 + "\n"

# Test 3: Test with cooking domain (if available)
echo "Test 3: Testing cooking domain matching"
curl -X POST "http://localhost:8001/v1/match" \
  -H "Content-Type: application/json" \
  -d '{
    "okh_manifest": {
      "title": "Cooking Test Recipe",
      "version": "1.0.0",
      "manufacturing_specs": {
        "process_requirements": [
          {
            "process_name": "cooking",
            "parameters": {}
          },
          {
            "process_name": "baking",
            "parameters": {}
          }
        ]
      }
    },
    "min_confidence": 0.5,
    "max_results": 5
  }' | jq '.'

echo -e "\n" + "="*50 + "\n"

# Test 4: Test with very specific manufacturing terms
echo "Test 4: Testing specific manufacturing terms"
curl -X POST "http://localhost:8001/v1/match" \
  -H "Content-Type: application/json" \
  -d '{
    "okh_manifest": {
      "title": "Specific Manufacturing Test",
      "version": "1.0.0",
      "manufacturing_specs": {
        "process_requirements": [
          {
            "process_name": "laser cutting",
            "parameters": {}
          },
          {
            "process_name": "laser engraving", 
            "parameters": {}
          },
          {
            "process_name": "assembly",
            "parameters": {}
          },
          {
            "process_name": "product assembly",
            "parameters": {}
          }
        ]
      }
    },
    "min_confidence": 0.4,
    "max_results": 10
  }' | jq '.'

echo -e "\n" + "="*50 + "\n"

# Test 5: Test with real synthetic data
echo "Test 5: Testing with real synthetic data (Arduino IoT Sensor Node)"
if [ -f "synth/synthetic_data/arduino-based-iot-sensor-node-1-2-4-okh.json" ]; then
    # Create a temporary file with the proper JSON structure
    cat > /tmp/test_request.json << EOF
{
  "okh_manifest": $(cat synth/synthetic_data/arduino-based-iot-sensor-node-1-2-4-okh.json),
  "min_confidence": 0.3,
  "max_results": 10
}
EOF
    
    curl -X POST "http://localhost:8001/v1/match" \
      -H "Content-Type: application/json" \
      -d @/tmp/test_request.json | jq '.'
    
    rm /tmp/test_request.json
else
    echo "Test 5: Skipped (synthetic data not found)"
fi

echo -e "\n" + "="*50 + "\n"
echo "API testing completed!"
echo ""
echo "Note: The NLP matching layer is now integrated as Layer 3 in the matching system."
echo "Look for 'nlp_matches' in the response metrics to see NLP matching results."
