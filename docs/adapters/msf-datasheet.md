# MSF Datasheet Conversion

The MSF (Maker Space Foundation) 3D-printed product technical specification datasheet is a structured .docx template widely used in the humanitarian open hardware community for documenting 3D-printed products.

## Template Structure

The MSF datasheet is organised into four sections, implemented as six Word tables:

| Table | Section | Contents |
|-------|---------|----------|
| 0 | Header | Logo and document title |
| 1 | Identity | Internal reference, product name, product stage |
| 2 | **FORM** | Picture, category, dimensions, license, readiness levels |
| 3 | **FIT** | Compatibility, manufacturing instructions, materials, QC |
| 4 | **FUNCTION** | Description, cleaning, packaging, standards |
| 5 | **ATTACHMENTS** | Technical drawings, designed/approved/tested by |

## Field Mapping

The table below shows how MSF datasheet fields map to OKH manifest fields.

### Identity (Table 1)

| MSF Field | OKH Field | Notes |
|-----------|-----------|-------|
| Internal Ref. | `metadata.internal_ref` | Falls back to first 8 chars of `id` |
| Name | `title` | **Required** |
| Product stage | `development_stage` | e.g. "prototype", "production" |

### FORM (Table 2)

| MSF Field | OKH Field | Notes |
|-----------|-----------|-------|
| Product picture | `image` | URL or path |
| Category | `keywords[0]` | First keyword |
| Subcategory | `keywords[1]` | Second keyword |
| Critical item | `metadata.critical_item` | |
| Dangerous goods | `metadata.dangerous_goods` | |
| Short description | `description` | |
| Repository link | `repo` | |
| Overall dimensions (LxWxH) | `manufacturing_specs.outer_dimensions` | Parsed as `{length, width, height}` |
| Single/Multiple use | `metadata.use_type` | |
| Permanent/Temporary solution | `metadata.solution_type` | |
| License | `license.hardware` | SPDX identifier |
| Field readiness | `metadata.field_readiness` | |
| Maker readiness | `metadata.maker_readiness` | |
| User readiness | `metadata.user_readiness` | |
| Technology readiness | `technology_readiness_level` | |
| Risk level | `metadata.risk_level` | |
| Justification | `intended_use` | |
| Why 3D printed | `metadata.justification_3d_print` | |
| Approval required by | `metadata.approval_required_by` | |

### FIT (Table 3)

| MSF Field | OKH Field | Notes |
|-----------|-----------|-------|
| Primary compatibility | `metadata.primary_compatibility` | |
| Compatible accessories | `metadata.compatible_accessories` | |
| Manufacturing instructions | `making_instructions` | As `DocumentRef` list |
| Material and color | `materials` | Comma-separated → `MaterialSpec` list |
| List of other materials | `metadata.other_materials` | |
| 3D Printer | `tool_list` | |
| Slicer settings | `metadata.slicer_settings` | |
| Post processing instructions | `metadata.post_processing` | |
| Assembly instructions | `metadata.assembly_instructions` | |
| Visual inspection | `metadata.visual_inspection` | |
| Dimensional validation | `metadata.dimensional_validation` | |
| Tolerance inspection | `metadata.tolerance_inspection` | |
| Safety validation | `metadata.safety_validation` | |
| Check frequency | `metadata.check_frequency` | |

### FUNCTION (Table 4)

| MSF Field | OKH Field | Notes |
|-----------|-----------|-------|
| Detailed description | `function` | **Required** |
| Cleaning procedures | `metadata.cleaning_procedures` | Also as `operating_instructions` |
| Packaging instructions | `metadata.packaging_instructions` | Also as `operating_instructions` |
| Related links/standards/safety | `standards_used`, `health_safety_notice` | Semicolon-separated |
| Spaulding Classification (IPC) | `metadata.spaulding_classification` | |

### ATTACHMENTS (Table 5)

| MSF Field | OKH Field | Notes |
|-----------|-----------|-------|
| Technical drawings / Photos | `design_files`, `image` | |
| Designed by | `licensor` | |
| Designed date | `version_date` | ISO format |
| Product approved by | `metadata.approved_by` | |
| Product tested by | `metadata.tested_by` | |

## Round-Trip Fidelity

Fields that do not have a direct OKH equivalent are stored in the `metadata` dictionary. This means:

- **OKH → Datasheet → OKH**: All standard OKH fields are preserved. MSF-specific fields (stored in `metadata`) are also round-tripped.
- **Datasheet → OKH → Datasheet**: All datasheet fields that have an OKH mapping are preserved. Fields in the OKH `metadata` dict are written back to their original MSF locations.

!!! note "Metadata convention"
    MSF-specific fields use descriptive keys in the `metadata` dict
    (e.g. `metadata.spaulding_classification`). These keys are stable
    and documented above.

## CLI Reference

### `ohm convert to-datasheet`

```
Usage: ohm convert to-datasheet [OPTIONS] MANIFEST_FILE

  Convert an OKH manifest to an MSF datasheet (.docx).

Options:
  -o, --output PATH     Output .docx file path
  --template PATH       Custom MSF template (.docx)
  -v, --verbose         Enable verbose output
  --json                Output in JSON format
```

### `ohm convert from-datasheet`

```
Usage: ohm convert from-datasheet [OPTIONS] DOCX_FILE

  Convert an MSF datasheet to an OKH manifest.

Options:
  -o, --output PATH     Output file path
  --template PATH       Custom MSF template (.docx)
  --format [json|yaml]  Output format (default: json)
  -v, --verbose         Enable verbose output
  --json                Output in JSON format
```

## API Reference

### `POST /v1/api/convert/to-datasheet`

Accepts an OKH manifest as JSON and returns the populated datasheet as a `.docx` file download.

**Request**: `ConvertToDatasheetRequest` (JSON body with OKH manifest fields)

**Response**: Binary `.docx` file with `Content-Disposition: attachment` header.

### `POST /v1/api/convert/from-datasheet`

Accepts a `.docx` file upload and returns the parsed OKH manifest as JSON.

**Request**: Multipart form upload with `datasheet_file` field.

**Response**: `ConvertFromDatasheetResponse` containing the full manifest and conversion metadata.

## Custom Templates

You can use a custom MSF template by passing the `--template` flag (CLI) or providing a `template_path` in the request. The custom template must follow the same 6-table structure as the standard MSF template.
