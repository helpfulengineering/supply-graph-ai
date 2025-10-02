#!/bin/bash

# Matching Engine Test Script with Real Data
# This script tests the enhanced matching engine using realistic data that will actually match

echo "🚀 Matching Engine Test with Real Data"
echo "======================================"
echo ""

# Check if server is running
echo "1. Checking if API server is running..."
if curl -s http://localhost:8001/health > /dev/null; then
    echo "✅ API server is running"
else
    echo "❌ API server is not running. Please start it with: python run.py"
    exit 1
fi

echo ""
echo "2. Testing Direct Matching - CNC Machining (Exact Match)"
echo "--------------------------------------------------------"
curl -X POST http://localhost:8001/v1/match \
  -H "Content-Type: application/json" \
  -d '{
    "okh_manifest": {
      "title": "CNC Machined Bracket",
      "repo": "https://github.com/test/cnc-bracket",
      "version": "1.0.0",
      "manufacturing_processes": ["CNC Machining"],
      "license": {"hardware": "CERN-OHL-S-2.0"},
      "licensor": "Test Manufacturer",
      "documentation_language": "en",
      "function": "Precision mounting bracket"
    }
  }' | jq '.'

echo ""
echo "3. Testing Direct Matching - Case Insensitive (CNC machining)"
echo "-------------------------------------------------------------"
curl -X POST http://localhost:8001/v1/match \
  -H "Content-Type: application/json" \
  -d '{
    "okh_manifest": {
      "title": "Lowercase CNC Test",
      "repo": "https://github.com/test/lowercase-cnc",
      "version": "1.0.0",
      "manufacturing_processes": ["cnc machining"],
      "license": {"hardware": "CERN-OHL-S-2.0"},
      "licensor": "Test Manufacturer",
      "documentation_language": "en",
      "function": "Test case insensitive matching"
    }
  }' | jq '.'

echo ""
echo "4. Testing Heuristic Matching - Milling to CNC Machining"
echo "--------------------------------------------------------"
curl -X POST http://localhost:8001/v1/match \
  -H "Content-Type: application/json" \
  -d '{
    "okh_manifest": {
      "title": "Milled Component",
      "repo": "https://github.com/test/milled-component",
      "version": "1.0.0",
      "manufacturing_processes": ["milling"],
      "license": {"hardware": "CERN-OHL-S-2.0"},
      "licensor": "Test Manufacturer",
      "documentation_language": "en",
      "function": "Test heuristic matching from milling to CNC"
    }
  }' | jq '.'

echo ""
echo "5. Testing Heuristic Matching - Surface Treatment to Surface Finishing"
echo "---------------------------------------------------------------------"
curl -X POST http://localhost:8001/v1/match \
  -H "Content-Type: application/json" \
  -d '{
    "okh_manifest": {
      "title": "Surface Treated Part",
      "repo": "https://github.com/test/surface-treated",
      "version": "1.0.0",
      "manufacturing_processes": ["surface treatment"],
      "license": {"hardware": "CERN-OHL-S-2.0"},
      "licensor": "Test Manufacturer",
      "documentation_language": "en",
      "function": "Test surface treatment matching"
    }
  }' | jq '.'

echo ""
echo "6. Testing Mixed Matching - Direct + Heuristic"
echo "----------------------------------------------"
curl -X POST http://localhost:8001/v1/match \
  -H "Content-Type: application/json" \
  -d '{
    "okh_manifest": {
      "title": "Complex Manufacturing Part",
      "repo": "https://github.com/test/complex-part",
      "version": "1.0.0",
      "manufacturing_processes": ["CNC Machining", "milling", "surface treatment"],
      "license": {"hardware": "CERN-OHL-S-2.0"},
      "licensor": "Test Manufacturer",
      "documentation_language": "en",
      "function": "Test mixed direct and heuristic matching"
    }
  }' | jq '.'

echo ""
echo "7. Testing 3D Printing Capability"
echo "---------------------------------"
curl -X POST http://localhost:8001/v1/match \
  -H "Content-Type: application/json" \
  -d '{
    "okh_manifest": {
      "title": "3D Printed Prototype",
      "repo": "https://github.com/test/3d-printed-prototype",
      "version": "1.0.0",
      "manufacturing_processes": ["3D Printing"],
      "license": {"hardware": "CERN-OHL-S-2.0"},
      "licensor": "Test Manufacturer",
      "documentation_language": "en",
      "function": "Test 3D printing capability matching"
    }
  }' | jq '.'

echo ""
echo "8. Testing Laser Cutting Capability"
echo "-----------------------------------"
curl -X POST http://localhost:8001/v1/match \
  -H "Content-Type: application/json" \
  -d '{
    "okh_manifest": {
      "title": "Laser Cut Acrylic Part",
      "repo": "https://github.com/test/laser-cut-acrylic",
      "version": "1.0.0",
      "manufacturing_processes": ["Laser Cutting"],
      "license": {"hardware": "CERN-OHL-S-2.0"},
      "licensor": "Test Manufacturer",
      "documentation_language": "en",
      "function": "Test laser cutting capability matching"
    }
  }' | jq '.'

echo ""
echo "9. Testing Electronics Assembly (Pick and Place)"
echo "------------------------------------------------"
curl -X POST http://localhost:8001/v1/match \
  -H "Content-Type: application/json" \
  -d '{
    "okh_manifest": {
      "title": "Electronics Assembly",
      "repo": "https://github.com/test/electronics-assembly",
      "version": "1.0.0",
      "manufacturing_processes": ["Pick and Place"],
      "license": {"hardware": "CERN-OHL-S-2.0"},
      "licensor": "Test Manufacturer",
      "documentation_language": "en",
      "function": "Test electronics assembly matching"
    }
  }' | jq '.'

echo ""
echo "10. Testing No Match (Unsupported Process)"
echo "------------------------------------------"
curl -X POST http://localhost:8001/v1/match \
  -H "Content-Type: application/json" \
  -d '{
    "okh_manifest": {
      "title": "Unsupported Process Test",
      "repo": "https://github.com/test/unsupported",
      "version": "1.0.0",
      "manufacturing_processes": ["quantum_manufacturing"],
      "license": {"hardware": "CERN-OHL-S-2.0"},
      "licensor": "Test Manufacturer",
      "documentation_language": "en",
      "function": "Test no match scenario"
    }
  }' | jq '.'

echo ""
echo "🎉 Testing completed!"
echo "===================="
echo ""
echo "Key things to look for in the responses:"
echo "- Direct matches should have high confidence (0.95-1.0)"
echo "- Heuristic matches should show rule_used in metadata"
echo "- SupplyTree metadata should show matching_summary"
echo "- Mixed examples should show both direct and heuristic matches"
echo "- No match examples should return empty solutions array"
echo ""
echo "Expected matches based on uploaded facilities:"
echo "- CNC Machining → Industrial Manufacturing Plant (Direct match)"
echo "- milling → CNC Machining capability (Heuristic match)"
echo "- surface treatment → Surface Finishing capability (Heuristic match)"
echo "- 3D Printing → Community Makerspace (Direct match)"
echo "- Laser Cutting → Community Makerspace (Direct match)"
echo "- Pick and Place → Electronics Assembly House (Direct match)"
