# Matching Engine Demonstration Guide

This guide provides practical curl commands to demonstrate the enhanced matching engine's Direct and Heuristic matching capabilities.

## Prerequisites

1. **Start the API server**:
   ```bash
   python run.py
   ```

2. **Verify the server is running**:
   ```bash
   curl http://localhost:8001/v1/match/domains
   ```

## Quick Test Commands

> **Note**: These tests require synthetic data to be loaded into storage. If you haven't set up test data yet, see the [Setup Test Data](#setup-test-data) section below.

### 🎯 Direct Matching Examples

#### Test 1: Perfect Exact Match
```bash
curl -X POST http://localhost:8001/v1/match \
  -H "Content-Type: application/json" \
  -d '{
    "okh_manifest": {
      "title": "Exact Match Test",
      "version": "1.0.0",
      "manufacturing_processes": ["CNC Machining"],
      "license": {"hardware": "CERN-OHL-S-2.0"},
      "licensor": "Test",
      "documentation_language": "en",
      "function": "Test exact matching"
    }
  }'
```
**Expected**: High confidence (1.0) with `"quality": "perfect"` in metadata.

#### Test 2: Case-Insensitive Match
```bash
curl -X POST http://localhost:8001/v1/match \
  -H "Content-Type: application/json" \
  -d '{
    "okh_manifest": {
      "title": "Case Test",
      "version": "1.0.0",
      "manufacturing_processes": ["cnc MACHINING"],
      "license": {"hardware": "CERN-OHL-S-2.0"},
      "licensor": "Test",
      "documentation_language": "en",
      "function": "Test case handling"
    }
  }'
```
**Expected**: Confidence ~0.95 with `"case_difference": true` in metadata.

#### Test 3: Near-Miss Detection
```bash
curl -X POST http://localhost:8001/v1/match \
  -H "Content-Type: application/json" \
  -d '{
    "okh_manifest": {
      "title": "Typo Test",
      "version": "1.0.0",
      "manufacturing_processes": ["CNC Machinng"],
      "license": {"hardware": "CERN-OHL-S-2.0"},
      "licensor": "Test",
      "documentation_language": "en",
      "function": "Test typo tolerance"
    }
  }'
```
**Expected**: Confidence ~0.8 with `"character_difference": 1` in metadata.

### 🧠 Heuristic Matching Examples

#### Test 4: Manufacturing Process Synonyms
```bash
curl -X POST http://localhost:8001/v1/match \
  -H "Content-Type: application/json" \
  -d '{
    "okh_manifest": {
      "title": "Synonym Test",
      "version": "1.0.0",
      "manufacturing_processes": ["milling"],
      "license": {"hardware": "CERN-OHL-S-2.0"},
      "licensor": "Test",
      "documentation_language": "en",
      "function": "Test process synonyms"
    }
  }'
```
**Expected**: Heuristic match with `"matching_method": "heuristic_cnc_machining_capability"` and confidence ~0.95.

#### Test 5: Surface Treatment Variations
```bash
curl -X POST http://localhost:8001/v1/match \
  -H "Content-Type: application/json" \
  -d '{
    "okh_manifest": {
      "title": "Surface Test",
      "version": "1.0.0",
      "manufacturing_processes": ["surface treatment"],
      "license": {"hardware": "CERN-OHL-S-2.0"},
      "licensor": "Test",
      "documentation_language": "en",
      "function": "Test surface process matching"
    }
  }'
```
**Expected**: Heuristic match to "surface finishing" with confidence ~0.85.

#### Test 6: Cooking Domain
```bash
curl -X POST http://localhost:8001/v1/match \
  -H "Content-Type: application/json" \
  -d '{
    "okh_manifest": {
      "title": "Cooking Test",
      "version": "1.0.0",
      "manufacturing_processes": ["sauté"],
      "license": {"hardware": "CERN-OHL-S-2.0"},
      "licensor": "Test",
      "documentation_language": "en",
      "function": "Test cooking domain"
    }
  }'
```
**Expected**: Heuristic match to "sauté pan" capability with confidence ~0.95.

### 🔄 Mixed Matching Examples

#### Test 7: Direct + Heuristic Combination
```bash
curl -X POST http://localhost:8001/v1/match \
  -H "Content-Type: application/json" \
  -d '{
    "okh_manifest": {
      "title": "Mixed Test",
      "version": "1.0.0",
      "manufacturing_processes": ["CNC Machining", "surface treatment"],
      "license": {"hardware": "CERN-OHL-S-2.0"},
      "licensor": "Test",
      "documentation_language": "en",
      "function": "Test mixed matching"
    }
  }'
```
**Expected**: 
- "CNC Machining" → Direct match (confidence 1.0)
- "surface treatment" → Heuristic match (confidence ~0.85)
- SupplyTree metadata shows both methods used

#### Test 8: Complex Multi-Process
```bash
curl -X POST http://localhost:8001/v1/match \
  -H "Content-Type: application/json" \
  -d '{
    "okh_manifest": {
      "title": "Complex Test",
      "version": "1.0.0",
      "manufacturing_processes": ["CNC Machining", "welding", "milling", "surface treatment"],
      "license": {"hardware": "CERN-OHL-S-2.0"},
      "licensor": "Test",
      "documentation_language": "en",
      "function": "Test complex matching"
    }
  }'
```
**Expected**: Mix of direct and heuristic matches with detailed matching summary.

### ❌ Edge Cases

#### Test 9: No Matches
```bash
curl -X POST http://localhost:8001/v1/match \
  -H "Content-Type: application/json" \
  -d '{
    "okh_manifest": {
      "title": "No Match Test",
      "version": "1.0.0",
      "manufacturing_processes": ["quantum_manufacturing"],
      "license": {"hardware": "CERN-OHL-S-2.0"},
      "licensor": "Test",
      "documentation_language": "en",
      "function": "Test no matches"
    }
  }'
```
**Expected**: Empty solutions array with appropriate metadata.

## Understanding the Results

### Response Structure
Each successful match returns:
```json
{
  "solutions": [
    {
      "tree": {
        "id": "uuid",
        "name": "Design Name - Facility Name",
        "node_count": 2,
        "edge_count": 1
      },
      "score": 0.95,
      "metrics": {
        "facility_count": 1,
        "requirement_count": 2,
        "capability_count": 5
      }
    }
  ],
  "metadata": {
    "solution_count": 1,
    "facility_count": 1
  }
}
```

### SupplyTree Metadata
The full SupplyTree includes detailed matching information:
```json
{
  "metadata": {
    "matching_summary": {
      "total_processes": 2,
      "average_confidence": 0.95,
      "direct_matches": 1,
      "heuristic_matches": 1,
      "no_matches": 0
    },
    "matching_layers_used": ["direct", "heuristic"],
    "generation_method": "enhanced_multi_layered_matching"
  }
}
```

### Workflow Node Details
Each process node contains:
```json
{
  "confidence_score": 0.95,
  "substitution_used": false,
  "metadata": {
    "matching_method": "direct_direct_exact",
    "matched_capability": "cnc machining",
    "matching_details": {
      "quality": "perfect",
      "case_difference": false,
      "whitespace_difference": false
    }
  }
}
```

## Testing Checklist

- [ ] **Direct Matching**: Exact matches return confidence 1.0
- [ ] **Case Handling**: Case differences return confidence ~0.95
- [ ] **Near-Miss**: Typos return confidence ~0.8
- [ ] **Heuristic Matching**: Synonyms return appropriate confidence
- [ ] **Domain Separation**: Manufacturing vs cooking rules work correctly
- [ ] **Mixed Matching**: Both layers work together
- [ ] **Metadata**: Detailed matching information is preserved
- [ ] **SupplyTree**: Complete manufacturing solutions are generated
- [ ] **Error Handling**: No matches handled gracefully

## Setup Test Data

To run meaningful tests, you need to have OKW facilities loaded into storage. Here's how to set up test data:

### 1. Generate Synthetic Facilities

```bash
# Generate 5 synthetic OKW facilities
python synth/generate_synthetic_data.py --type okw --count 5 --complexity mixed --output-dir ./test_data
```

### 2. Load Facilities into Storage

The system automatically loads OKW facilities from storage. You can either:

**Option A: Use the existing storage system**
- The API will automatically load facilities from the configured storage location
- Ensure your storage configuration points to where the facilities are stored

**Option B: Manual upload (if needed)**
- Use the storage service to upload the generated facility files
- The matching system will automatically discover and load them

### 3. Verify Data is Loaded

```bash
# Check if facilities are loaded
curl http://localhost:8001/v1/okw/search
```

### 4. Run the Complete Test Suite

```bash
# Run the comprehensive test with real data
./test_matching_with_real_data.sh
```

## Troubleshooting

### Common Issues

1. **Server not running**: Ensure `python run.py` is executed
2. **Port conflicts**: Check if port 8001 is available
3. **JSON syntax**: Validate JSON structure in curl commands
4. **No facilities**: Ensure OKW facilities are loaded in the system

### Debug Commands

```bash
# Check server health
curl http://localhost:8001/v1/match/domains/manufacturing/health

# List available domains
curl http://localhost:8001/v1/match/domains

# Test basic connectivity
curl http://localhost:8001/health
```

## Performance Notes

- **Direct Matching**: Very fast (< 1ms per match)
- **Heuristic Matching**: Fast (~5ms per match)
- **SupplyTree Generation**: Moderate (~50ms for complex trees)
- **Total Response Time**: Typically < 200ms for most requests

This demonstration guide provides a comprehensive way to test and validate the enhanced matching engine's capabilities.
