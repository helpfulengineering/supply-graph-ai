# Matching API Documentation

## Overview

The Open Matching Engine (OME) provides a comprehensive API for matching requirements to capabilities across multiple domains. The API supports both direct matching and heuristic matching through a multi-layered approach.

## Base URL

```
http://localhost:8001/v1/match
```

## Authentication

Currently, the API does not require authentication. Future versions may include API key authentication.

## Endpoints

### 1. Main Matching Endpoint

**POST** `/v1/match`

Matches requirements to capabilities using the multi-layered matching approach.

#### Request Body

```json
{
  "okh_manifest": {
    "title": "CNC Bracket",
    "manufacturing_processes": ["CNC", "Deburring"],
    "license": {
      "hardware": "CERN-OHL-S-2.0"
    },
    "licensor": "Test Org",
    "documentation_language": "en",
    "function": "Precision bracket"
  }
}
```

#### Response

```json
{
  "solutions": [
    {
      "tree": {
        "id": "supply-tree-123",
        "nodes": [...],
        "edges": [...]
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
    "processing_time_ms": 150,
    "layers_used": ["direct", "heuristic"],
    "domain": "manufacturing"
  }
}
```

#### Example Usage

```bash
curl -X POST http://localhost:8001/v1/match \
  -H "Content-Type: application/json" \
  -d '{
    "okh_manifest": {
      "title": "CNC Bracket",
      "manufacturing_processes": ["CNC", "Deburring"],
      "license": {
        "hardware": "CERN-OHL-S-2.0"
      },
      "licensor": "Test Org",
      "documentation_language": "en",
      "function": "Precision bracket"
    }
  }'
```

### 2. Domain Information

**GET** `/v1/match/domains`

Returns information about all available domains.

#### Response

```json
{
  "domains": [
    {
      "name": "manufacturing",
      "display_name": "Manufacturing",
      "description": "Hardware production and manufacturing capability matching",
      "status": "active",
      "supported_input_types": ["okh", "okw"],
      "supported_output_types": ["supply_tree", "manufacturing_plan"]
    },
    {
      "name": "cooking",
      "display_name": "Cooking",
      "description": "Recipe and kitchen capability matching",
      "status": "active",
      "supported_input_types": ["recipe", "kitchen"],
      "supported_output_types": ["cooking_workflow", "meal_plan"]
    }
  ]
}
```

#### Example Usage

```bash
curl http://localhost:8001/v1/match/domains
```

### 3. Domain Health Check

**GET** `/v1/match/domains/{domain_name}/health`

Returns the health status of a specific domain.

#### Response

```json
{
  "domain": "manufacturing",
  "status": "healthy",
  "components": {
    "direct_matcher": "healthy",
    "heuristic_matcher": "healthy",
    "rule_manager": "healthy"
  },
  "rule_count": 19,
  "last_updated": "2024-01-01T00:00:00Z"
}
```

#### Example Usage

```bash
curl http://localhost:8001/v1/match/domains/manufacturing/health
```

### 4. Domain Detection

**POST** `/v1/match/detect-domain`

Automatically detects the appropriate domain from input data.

#### Request Body

```json
{
  "requirements_data": {
    "type": "okh",
    "content": {
      "manufacturing_processes": ["CNC"]
    }
  },
  "capabilities_data": {
    "type": "okw",
    "content": {
      "equipment": ["CNC mill"]
    }
  }
}
```

#### Response

```json
{
  "detected_domain": "manufacturing",
  "confidence": 0.95,
  "reasoning": [
    "Found manufacturing_processes in requirements",
    "Found equipment in capabilities",
    "Keywords suggest manufacturing domain"
  ]
}
```

#### Example Usage

```bash
curl -X POST http://localhost:8001/v1/match/detect-domain \
  -H "Content-Type: application/json" \
  -d '{
    "requirements_data": {
      "type": "okh",
      "content": {
        "manufacturing_processes": ["CNC"]
      }
    },
    "capabilities_data": {
      "type": "okw",
      "content": {
        "equipment": ["CNC mill"]
      }
    }
  }'
```

## Matching Layers

The API uses a multi-layered matching approach:

### Layer 1: Direct Matching
- **Purpose**: Exact and near-exact string matches
- **Confidence**: 0.7-1.0
- **Speed**: Very fast
- **Use Cases**: Standard terminology, exact specifications

### Layer 2: Heuristic Matching (Capability-Centric)
- **Purpose**: Rule-based matching using capability-centric rules
- **Confidence**: 0.7-0.95
- **Speed**: Fast
- **Use Cases**: Variations in terminology, domain-specific knowledge

### Layer 3: NLP Matching (Future)
- **Purpose**: Natural language understanding
- **Confidence**: 0.5-0.8
- **Speed**: Moderate
- **Use Cases**: Complex descriptions, semantic similarity

### Layer 4: AI/ML Matching (Future)
- **Purpose**: Machine learning-based matching
- **Confidence**: 0.3-0.9
- **Speed**: Slow
- **Use Cases**: Complex patterns, historical learning

## Error Handling

### HTTP Status Codes

- **200 OK**: Successful request
- **400 Bad Request**: Invalid request format
- **404 Not Found**: Resource not found
- **422 Unprocessable Entity**: Validation error
- **500 Internal Server Error**: Server error

### Error Response Format

```json
{
  "error": {
    "code": "VALIDATION_ERROR",
    "message": "Invalid request format",
    "details": {
      "field": "okh_manifest",
      "issue": "Missing required field: title"
    }
  }
}
```

### Common Error Codes

- **VALIDATION_ERROR**: Request validation failed
- **DOMAIN_NOT_FOUND**: Specified domain not found
- **PROCESSING_ERROR**: Error during matching processing
- **CONFIGURATION_ERROR**: System configuration error

## Rate Limiting

Currently, there are no rate limits. Future versions may include rate limiting based on API keys.

## Response Times

Typical response times for different operations:

- **Domain Information**: < 10ms
- **Health Checks**: < 50ms
- **Domain Detection**: < 100ms
- **Matching**: 100-500ms (depending on complexity)

## Examples

### Manufacturing Domain Example

```bash
curl -X POST http://localhost:8001/v1/match \
  -H "Content-Type: application/json" \
  -d '{
    "okh_manifest": {
      "title": "Precision Bracket",
      "manufacturing_processes": ["milling", "surface finish", "assembly"],
      "materials": ["aluminum", "stainless steel"],
      "license": {
        "hardware": "CERN-OHL-S-2.0"
      },
      "licensor": "Manufacturing Corp",
      "documentation_language": "en",
      "function": "Precision mounting bracket"
    }
  }'
```

### Cooking Domain Example

```bash
curl -X POST http://localhost:8001/v1/match \
  -H "Content-Type: application/json" \
  -d '{
    "recipe": {
      "title": "Chicken Stir Fry",
      "techniques": ["sauté", "stir-fry"],
      "equipment": ["wok", "stove"],
      "ingredients": ["chicken", "vegetables", "soy sauce"],
      "cooking_time": "15 minutes",
      "servings": 4
    }
  }'
```

## SDK Examples

### Python SDK

```python
import requests

# Initialize client
base_url = "http://localhost:8001/v1/match"

# Match requirements to capabilities
def match_requirements(okh_manifest):
    response = requests.post(
        f"{base_url}",
        json={"okh_manifest": okh_manifest}
    )
    return response.json()

# Example usage
okh_manifest = {
    "title": "CNC Bracket",
    "manufacturing_processes": ["CNC", "Deburring"],
    "license": {"hardware": "CERN-OHL-S-2.0"},
    "licensor": "Test Org",
    "documentation_language": "en",
    "function": "Precision bracket"
}

result = match_requirements(okh_manifest)
print(f"Found {len(result['solutions'])} solutions")
```

### JavaScript SDK

```javascript
// Initialize client
const baseUrl = 'http://localhost:8001/v1/match';

// Match requirements to capabilities
async function matchRequirements(okhManifest) {
    const response = await fetch(baseUrl, {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
        },
        body: JSON.stringify({ okh_manifest: okhManifest })
    });
    return await response.json();
}

// Example usage
const okhManifest = {
    title: "CNC Bracket",
    manufacturing_processes: ["CNC", "Deburring"],
    license: { hardware: "CERN-OHL-S-2.0" },
    licensor: "Test Org",
    documentation_language: "en",
    function: "Precision bracket"
};

matchRequirements(okhManifest)
    .then(result => {
        console.log(`Found ${result.solutions.length} solutions`);
    })
    .catch(error => {
        console.error('Error:', error);
    });
```

## Testing

### Health Check

```bash
# Check if the API is running
curl http://localhost:8001/v1/match/domains/manufacturing/health
```

### Basic Functionality Test

```bash
# Test basic matching functionality
curl -X POST http://localhost:8001/v1/match \
  -H "Content-Type: application/json" \
  -d '{
    "okh_manifest": {
      "title": "Test Part",
      "manufacturing_processes": ["milling"],
      "license": {"hardware": "CERN-OHL-S-2.0"},
      "licensor": "Test",
      "documentation_language": "en",
      "function": "Test"
    }
  }'
```

## Practical Examples: Demonstrating Direct and Heuristic Matching

### Example 1: Direct Matching - Exact Process Names

This example demonstrates **Direct Matching** where the OKH requirements exactly match the facility capabilities:

```bash
# Direct Match Example: Exact process name matching
curl -X POST http://localhost:8001/v1/match \
  -H "Content-Type: application/json" \
  -d '{
    "okh_manifest": {
      "title": "Precision Bracket",
      "version": "1.0.0",
      "manufacturing_processes": ["CNC Machining", "Assembly"],
      "license": {"hardware": "CERN-OHL-S-2.0"},
      "licensor": "Open Hardware Foundation",
      "documentation_language": "en",
      "function": "Structural support bracket"
    }
  }'
```

**Expected Result**: High confidence matches (0.95-1.0) for exact process name matches.

### Example 2: Direct Matching - Case Variations

This example shows how **Direct Matching** handles case differences:

```bash
# Direct Match Example: Case-insensitive matching
curl -X POST http://localhost:8001/v1/match \
  -H "Content-Type: application/json" \
  -d '{
    "okh_manifest": {
      "title": "Metal Housing",
      "version": "1.0.0",
      "manufacturing_processes": ["cnc machining", "SURFACE FINISHING"],
      "license": {"hardware": "CERN-OHL-S-2.0"},
      "licensor": "Manufacturing Co",
      "documentation_language": "en",
      "function": "Protective housing"
    }
  }'
```

**Expected Result**: Matches with confidence ~0.95 due to case differences, with detailed metadata showing case_difference: true.

### Example 3: Heuristic Matching - Process Synonyms

This example demonstrates **Heuristic Matching** where the OKH uses different terminology than the facility capabilities:

```bash
# Heuristic Match Example: Process synonyms
curl -X POST http://localhost:8001/v1/match \
  -H "Content-Type: application/json" \
  -d '{
    "okh_manifest": {
      "title": "Custom Component",
      "version": "1.0.0",
      "manufacturing_processes": ["milling", "surface treatment"],
      "license": {"hardware": "CERN-OHL-S-2.0"},
      "licensor": "Design Studio",
      "documentation_language": "en",
      "function": "Custom mechanical component"
    }
  }'
```

**Expected Result**: 
- "milling" → "cnc machining" (heuristic match, confidence ~0.95)
- "surface treatment" → "surface finishing" (heuristic match, confidence ~0.85)
- Metadata shows rule_used and transformation_details

### Example 4: Heuristic Matching - Cooking Domain

This example shows **Heuristic Matching** in the cooking domain:

```bash
# Heuristic Match Example: Cooking domain
curl -X POST http://localhost:8001/v1/match \
  -H "Content-Type: application/json" \
  -d '{
    "okh_manifest": {
      "title": "Gourmet Pasta",
      "manufacturing_processes": ["sauté", "boiling"],
      "license": {"hardware": "CERN-OHL-S-2.0"},
      "licensor": "Culinary Institute",
      "documentation_language": "en",
      "function": "Restaurant-quality pasta dish"
    }
  }'
```

**Expected Result**:
- "sauté" → "sauté pan" capability (heuristic match, confidence ~0.95)
- "boiling" → "saucepan" capability (heuristic match, confidence ~0.9)
- Shows cooking domain rule usage

### Example 5: Mixed Matching - Direct + Heuristic

This example shows both matching types working together:

```bash
# Mixed Match Example: Direct + Heuristic
curl -X POST http://localhost:8001/v1/match \
  -H "Content-Type: application/json" \
  -d '{
    "okh_manifest": {
      "title": "Complex Assembly",
      "manufacturing_processes": ["CNC Machining", "welding", "quality control"],
      "license": {"hardware": "CERN-OHL-S-2.0"},
      "licensor": "Advanced Manufacturing",
      "documentation_language": "en",
      "function": "Multi-process manufacturing"
    }
  }'
```

**Expected Result**:
- "CNC Machining" → "cnc machining" (direct match, confidence 1.0)
- "welding" → "welding" (direct match, confidence 1.0)  
- "quality control" → "inspection" (heuristic match, confidence ~0.8)
- SupplyTree metadata shows both matching methods used

### Example 6: Near-Miss Detection

This example demonstrates **Direct Matching** near-miss detection for typos:

```bash
# Near-Miss Example: Typo detection
curl -X POST http://localhost:8001/v1/match \
  -H "Content-Type: application/json" \
  -d '{
    "okh_manifest": {
      "title": "Typo Test Part",
      "manufacturing_processes": ["CNC Machinng", "Assemly"],
      "license": {"hardware": "CERN-OHL-S-2.0"},
      "licensor": "Test Lab",
      "documentation_language": "en",
      "function": "Testing typo tolerance"
    }
  }'
```

**Expected Result**: 
- "CNC Machinng" → "cnc machining" (near-miss, confidence ~0.8)
- "Assemly" → "assembly" (near-miss, confidence ~0.8)
- Metadata shows character_difference: 1

### Example 7: No Matches Found

This example shows what happens when no matches are found:

```bash
# No Match Example: Unsupported processes
curl -X POST http://localhost:8001/v1/match \
  -H "Content-Type: application/json" \
  -d '{
    "okh_manifest": {
      "title": "Unsupported Part",
      "manufacturing_processes": ["quantum_manufacturing", "nano_assembly"],
      "license": {"hardware": "CERN-OHL-S-2.0"},
      "licensor": "Future Tech",
      "documentation_language": "en",
      "function": "Hypothetical manufacturing"
    }
  }'
```

**Expected Result**: Empty solutions array with metadata explaining no matches found.

### Understanding the Response

Each successful match returns a response like this:

```json
{
  "solutions": [
    {
      "tree": {
        "id": "uuid-here",
        "name": "Precision Bracket - Facility Name",
        "description": "Manufacturing solution for Precision Bracket at Facility Name",
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
    "facility_count": 1,
    "optimization_criteria": null
  }
}
```

### SupplyTree Details

To get detailed SupplyTree information, you can access the full tree data which includes:

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
  },
  "workflows": {
    "workflow_id": {
      "nodes": {
        "node_id": {
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
      }
    }
  }
}
```

## Future Enhancements

1. **Authentication**: API key-based authentication
2. **Rate Limiting**: Request rate limiting
3. **Caching**: Response caching for improved performance
4. **Webhooks**: Real-time notifications for long-running operations
5. **Batch Processing**: Support for batch matching operations
6. **GraphQL**: GraphQL endpoint for flexible queries
7. **OpenAPI**: Complete OpenAPI specification
8. **SDKs**: Official SDKs for multiple languages
