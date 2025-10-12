# Validation System Testing with cURL Commands

## Server Setup

First, start the server on port 8001:

```bash
conda activate supply-graph-ai && python -m uvicorn src.core.main:app --host 0.0.0.0 --port 8001 --reload
```

## Test 1: OKH Validation - Basic Valid Data

Test with a complete OKH manifest that should pass validation:

```bash
curl -X POST "http://localhost:8001/v1/okh/validate" \
  -H "Content-Type: application/json" \
  -d '{
    "content": {
      "title": "Arduino-based IoT Sensor Node",
      "version": "1.2.4",
      "license": {
        "hardware": "MIT",
        "documentation": "MIT",
        "software": "MIT"
      },
      "licensor": "Open Hardware Foundation",
      "documentation_language": "en",
      "function": "Environmental monitoring sensor node with wireless connectivity",
      "description": "A complete IoT sensor node for environmental monitoring",
      "manufacturing_processes": [
        "https://en.wikipedia.org/wiki/3D_printing",
        "https://en.wikipedia.org/wiki/PCB_assembly"
      ],
      "materials": [
        {
          "material_type": "https://en.wikipedia.org/wiki/PLA",
          "manufacturer": "Generic",
          "brand": "PLA+"
        }
      ],
      "tool_list": [
        "3D printer",
        "Soldering iron",
        "Multimeter"
      ],
      "manufacturing_specs": {
        "tolerance": "0.1mm",
        "layer_height": "0.2mm",
        "infill_percentage": 20
      },
      "quality_standards": ["ISO 9001"],
      "certifications": ["CE marking"],
      "regulatory_compliance": ["RoHS", "REACH"]
    },
    "validation_context": "manufacturing"
  }' | jq .
```

**Expected Result**: Should return `valid: true` with high completeness score and minimal warnings.

## Test 2: OKH Validation - Missing Required Fields (Professional Quality)

Test with incomplete data that should fail professional quality validation:

```bash
curl -X POST "http://localhost:8001/v1/okh/validate" \
  -H "Content-Type: application/json" \
  -d '{
    "content": {
      "title": "Incomplete OKH Manifest",
      "version": "1.0.0",
      "license": {
        "hardware": "MIT",
        "documentation": "MIT",
        "software": "MIT"
      },
      "licensor": "Test Author",
      "documentation_language": "en",
      "function": "Test function description"
    },
    "validation_context": "manufacturing"
  }' | jq .
```

**Expected Result**: Should return `valid: false` with errors for missing required fields like:
- `manufacturing_specs` (required for professional quality)
- `manufacturing_processes` (required for professional quality)
- `materials` (required for professional quality)
- `tool_list` (required for professional quality)

## Test 3: OKH Validation - Hobby Quality Level

Test the same incomplete data but with hobby quality level (should be more lenient):

```bash
curl -X POST "http://localhost:8001/v1/okh/validate" \
  -H "Content-Type: application/json" \
  -d '{
    "content": {
      "title": "Hobby OKH Manifest",
      "version": "1.0.0",
      "license": {
        "hardware": "MIT",
        "documentation": "MIT",
        "software": "MIT"
      },
      "licensor": "Hobby Maker",
      "documentation_language": "en",
      "function": "Simple hobby project"
    },
    "validation_context": "hobby"
  }' | jq .
```

**Expected Result**: Should return `valid: true` with warnings for missing optional fields, but no errors since hobby quality has relaxed requirements.

## Test 4: OKH Validation - Medical Quality Level

Test with data that should pass professional but fail medical quality:

```bash
curl -X POST "http://localhost:8001/v1/okh/validate" \
  -H "Content-Type: application/json" \
  -d '{
    "content": {
      "title": "Medical Device Component",
      "version": "2.0.0",
      "license": {
        "hardware": "MIT",
        "documentation": "MIT",
        "software": "MIT"
      },
      "licensor": "Medical Device Corp",
      "documentation_language": "en",
      "function": "Medical device component for patient monitoring",
      "manufacturing_processes": [
        "https://en.wikipedia.org/wiki/CNC_mill",
        "https://en.wikipedia.org/wiki/3D_printing"
      ],
      "materials": [
        {
          "material_type": "https://en.wikipedia.org/wiki/Medical_grade_plastic",
          "manufacturer": "Medical Materials Inc",
          "brand": "MedPlast"
        }
      ],
      "tool_list": [
        "CNC mill",
        "3D printer",
        "Quality control equipment"
      ],
      "manufacturing_specs": {
        "tolerance": "0.01mm",
        "surface_finish": "Ra 0.8",
        "sterilization_compatible": true
      },
      "quality_standards": ["ISO 13485", "ISO 9001"]
    },
    "validation_context": "medical"
  }'
```

**Expected Result**: Should return `valid: false` with errors for missing medical-specific requirements like:
- `certifications` (required for medical quality)
- `regulatory_compliance` (required for medical quality)
- `traceability` (required for medical quality)
- `testing_procedures` (required for medical quality)

## Test 5: OKW Validation - Valid Manufacturing Facility

Test OKW validation with a complete manufacturing facility:

```bash
curl -X POST "http://localhost:8001/v1/okw/validate" \
  -H "Content-Type: application/json" \
  -d '{
    "content": {
      "name": "Advanced Manufacturing Hub",
      "location": "123 Industrial Blvd, Tech City, TC 12345",
      "facility_status": "operational",
      "equipment": [
        {
          "name": "CNC Mill VF-2",
          "type": "cnc_mill",
          "specifications": {
            "capacity": "762x406x508mm",
            "spindle_speed": "12000 RPM",
            "accuracy": "0.005mm"
          },
          "location": "Machine Shop A",
          "materials_worked": [
            "https://en.wikipedia.org/wiki/Aluminum",
            "https://en.wikipedia.org/wiki/Steel"
          ]
        },
        {
          "name": "3D Printer Ultimaker S5",
          "type": "3d_printer",
          "specifications": {
            "build_volume": "330x240x300mm",
            "layer_resolution": "0.02mm",
            "materials": ["PLA", "ABS", "PETG"]
          }
        }
      ],
      "manufacturing_processes": [
        "https://en.wikipedia.org/wiki/CNC_mill",
        "https://en.wikipedia.org/wiki/3D_printing",
        "https://en.wikipedia.org/wiki/CNC_lathe"
      ],
      "typical_materials": [
        {
          "material_type": "https://en.wikipedia.org/wiki/Aluminum",
          "manufacturer": "Alcoa",
          "brand": "6061-T6",
          "supplier_location": "North America"
        },
        {
          "material_type": "https://en.wikipedia.org/wiki/PLA",
          "manufacturer": "NatureWorks",
          "brand": "Ingeo",
          "supplier_location": "Global"
        }
      ],
      "certifications": ["ISO 9001:2015", "AS9100D"],
      "quality_standards": ["ISO 9001", "AS9100"],
      "regulatory_compliance": ["RoHS", "REACH", "ITAR"]
    }
  }' | jq .
```

**Expected Result**: Should return `valid: true` with high capability score and minimal warnings.

## Test 6: OKW Validation - Incomplete Facility

Test OKW validation with missing required fields:

```bash
curl -X POST "http://localhost:8001/v1/okw/validate" \
  -H "Content-Type: application/json" \
  -d '{
    "content": {
      "name": "Incomplete Manufacturing Facility",
      "location": "456 Test St, Test City, TC 54321"
    }
  }'
```

**Expected Result**: Should return `valid: false` with errors for missing required fields:
- `facility_status` (required)
- `equipment` (required for professional quality)
- `manufacturing_processes` (required for professional quality)

## Test 7: Supply Tree Validation

Test supply tree validation (currently placeholder, but shows the endpoint):

```bash
curl -X POST "http://localhost:8001/v1/match/validate" \
  -H "Content-Type: application/json" \
  -d '{
    "okh_id": "123e4567-e89b-12d3-a456-426614174000",
    "supply_tree_id": "987fcdeb-51a2-43d1-b789-123456789abc",
    "validation_criteria": {
      "cost_threshold": 1000,
      "time_threshold": 48,
      "quality_threshold": 0.8
    }
  }' | jq .
```

**Expected Result**: Currently returns placeholder response with `valid: true` and `confidence: 0.8`.

## Test 8: Domain Contexts

Test getting validation contexts for different domains:

```bash
# Get manufacturing domain contexts
curl -X GET "http://localhost:8001/v1/contexts/manufacturing"

# Get cooking domain contexts  
curl -X GET "http://localhost:8001/v1/contexts/cooking"
```

**Expected Result**: Should return available validation contexts for each domain with their quality levels and validation rules.

## Test 9: Available Domains

Test getting list of available domains:

```bash
curl -X GET "http://localhost:8001/v1/domains"
```

**Expected Result**: Should return list of registered domains (manufacturing, cooking).

## Test 10: Error Handling

Test validation with invalid data to see error handling:

```bash
curl -X POST "http://localhost:8001/v1/okh/validate" \
  -H "Content-Type: application/json" \
  -d '{
    "content": {
      "title": 123,
      "version": null,
      "license": "invalid_license_format"
    }
  }'
```

**Expected Result**: Should return validation errors for:
- Invalid data types (title should be string, not number)
- Missing required fields
- Invalid license format

## Expected Validation Features Demonstrated

These tests should demonstrate:

1. **Quality Level Validation**: Different strictness levels (hobby, professional, medical)
2. **Domain-Specific Rules**: Manufacturing vs cooking domain validation
3. **Comprehensive Error Reporting**: Detailed error messages with field paths and codes
4. **Warning System**: Optional field recommendations
5. **Completeness Scoring**: Numerical scores for data completeness
6. **Context-Aware Validation**: Validation rules based on domain and quality level
7. **Structured Responses**: Consistent error/warning format across all endpoints

## Notes

- The OKH validation endpoint uses the new validation framework through the compatibility layer
- OKW validation is currently a placeholder but will be enhanced in Phase 3
- Supply tree validation is placeholder but shows the endpoint structure
- All validation responses include structured error/warning information
- Quality levels affect validation strictness and required fields
