# REST API

The OME REST API provides HTTP endpoints for matching requirements to capabilities, managing domains, and working with Supply Trees.

## API Base URL

When running locally, the API is available at:
http://localhost:8000

## API Documentation

FastAPI automatically generates interactive documentation:

- Swagger UI: `http://localhost:8000/docs`

## Key Endpoints

### Health Check
GET /health

Returns the server status and available domains.

#### Example Response

```json
{
  "status": "ok",
  "domains": ["cooking", "manufacturing"]
}
```

### Matching Endpoint
POST /match

The primary endpoint for matching requirements to capabilities.

Request Body

```json
{
  "requirements": {
    "content": {
      "title": "Example Recipe",
      "ingredients": ["flour", "water", "salt"],
      "instructions": ["Mix ingredients", "Knead dough", "Bake"]
    },
    "domain": "cooking",
    "type": "recipe"
  },
  "capabilities": {
    "content": {
      "name": "Home Kitchen",
      "tools": ["mixing bowl", "oven", "knife"],
      "ingredients": ["flour", "water", "salt", "sugar"]
    },
    "domain": "cooking",
    "type": "kitchen"
  }
}
```

Response Body

```json
{
  "id": "550e8400-e29b-41d4-a716-446655440000",
  "domain": "cooking",
  "workflows": {
    "550e8400-e29b-41d4-a716-446655440001": {
      "id": "550e8400-e29b-41d4-a716-446655440001",
      "name": "Cooking Workflow",
      "nodes": {
        "550e8400-e29b-41d4-a716-446655440002": {
          "id": "550e8400-e29b-41d4-a716-446655440002",
          "name": "Step 1: Mix ingredients",
          "inputs": ["flour", "water", "salt"],
          "outputs": ["dough"],
          "requirements": {
            "tools": ["mixing bowl"]
          },
          "capabilities": {
            "available_tools": ["mixing bowl"]
          }
        }
      },
      "edges": [
        {
          "source": "550e8400-e29b-41d4-a716-446655440002",
          "target": "550e8400-e29b-41d4-a716-446655440003"
        }
      ]
    }
  },
  "confidence": 0.85,
  "validation_status": true,
  "metadata": {
    "matching_time_ms": 45,
    "match_count": 3
  }
}
```

## Planned Endpoints

### Domain Management: 
GET /domains
List available domains and their capabilities.

POST /domains
Register a new domain with its extractors, matchers, and validators.

### Supply Tree Operations: 
GET /supply-trees/{id}
Retrieve a specific Supply Tree.

PUT /supply-trees/{id}
Update a Supply Tree.

DELETE /supply-trees/{id}
Delete a Supply Tree.

### Validation
POST /validate
Validate a Supply Tree against specific validation contexts.

### Error Handling
The API uses standard HTTP status codes:

200 OK: Successful operation
400 Bad Request: Invalid input
404 Not Found: Resource not found
500 Internal Server Error: Server error

Error responses include a detail message:
```json
{
  "detail": "Error message describing what went wrong"
}
```

Rate Limiting
In production deployments, rate limiting may be applied to prevent abuse.
