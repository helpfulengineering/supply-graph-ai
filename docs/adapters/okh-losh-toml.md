# OKH-LOSH v2.4 TOML Conversion

OKH-LOSH v2.4 is the TOML-based OKH manifest format defined by
[iop-alliance/OpenKnowHow](https://github.com/iop-alliance/OpenKnowHow). It
uses kebab-case field names and a few shapes (a repeatable `[[image]]` table,
a top-level `[outer-dimensions]` table, a top-level `mass`) that have no
direct equivalent in OHM's canonical model.

Conversion is **one-way** (TOML → OKH). Nothing in OHM needs to export a
manifest back to OKH-LOSH TOML.

## Field Mapping

| OKH-LOSH v2.4 field | OKH field | Notes |
|---|---|---|
| `okhv` | `okhv` | Passed through literally; not validated by OHM |
| `name` | `title` | Rename |
| `repo`, `license`, `function`, `version`, `licensor`, `organization`, `attestation`, `bom`, `readme` | Same names | Passed straight through; `license` bare strings and `licensor`/`organization` `"Name <email>"` strings/lists are already handled by `OKHManifest.from_dict()` |
| `documentation-language` | `documentation_language` | Rename |
| `technology-readiness-level` | `technology_readiness_level` | Rename |
| `documentation-readiness-level` | `documentation_readiness_level` | Rename |
| `cpc-patent-class` | `cpc_patent_class` | Rename |
| `contribution-guide` | `contribution_guide` | Rename |
| `tsdc` | `tsdc` | Wrapped in a list if given as a bare string |
| `standard-compliance` | `standards_used` | Wrapped in a list if given as a bare string |
| `manufacturing-instructions` | `making_instructions` | Each entry becomes a `DocumentRef` (`path` = the URL/file, `type=making-instructions`) |
| `user-manual` | `operating_instructions` | Same pattern, `type=operating-instructions` |
| `publication` | `publications` | Same pattern, `type=publications` |
| `source` | `design_files` | Same pattern, `type=design-files` |
| `[[software]]` | `software` | Structurally identical; `installation-guide` (kebab in the source) is renamed to `installation_guide` |
| `[outer-dimensions]` | `manufacturing_specs.outer_dimensions` | Untyped dict on both sides; `width`/`depth`/`height` keys preserved as-is |
| `[[image]]` | `image` + `metadata.images` | See below |
| `mass` | `metadata.mass` | No top-level equivalent in OHM (only nested under a part's `mass`) |
| `release` | `metadata.release` | Different concept from OHM's `Software.release` |

### Image handling

OKH-LOSH's `[[image]]` is a repeatable table (`location`, `depicts`, `slots`,
`tags`); OHM's canonical model has a single scalar `image: Optional[str]`.
The converter:

1. Picks one **primary** image for the `image` field — preferring the entry
   tagged with the `photo-thing-main` slot, falling back to the first image
   with a `location`.
2. Preserves the **full array** (all entries, with their `slots`/`tags`/
   `depicts`) under `metadata.images`, so nothing is lost even though only
   one image is a first-class field.

## Access Methods

- **CLI**: `ohm convert from-okh-losh`
- **API**: `POST /v1/api/convert/from-okh-losh`
- **Python**: `OkhLoshConverter` class in `src.core.services.okh_losh_converter`

## Quick Start

### CLI

```bash
# Convert an OKH-LOSH TOML manifest → OKH manifest (JSON)
ohm convert from-okh-losh my-project.okh.toml -o my-project.okh.json

# Output as YAML
ohm convert from-okh-losh my-project.okh.toml --format yaml
```

### API

```bash
# OKH-LOSH TOML → OKH (upload .toml, get JSON back)
curl -X POST http://localhost:8001/v1/api/convert/from-okh-losh \
  -F "toml_file=@my-project.okh.toml"
```

### Python

```python
from src.core.services.okh_losh_converter import OkhLoshConverter

converter = OkhLoshConverter()
manifest = converter.okh_losh_to_okh("my-project.okh.toml")
print(manifest.title)
```

## CLI Reference

### `ohm convert from-okh-losh`

```
Usage: ohm convert from-okh-losh [OPTIONS] TOML_FILE

  Convert an OKH-LOSH v2.4 TOML manifest to an OKH manifest.

Options:
  -o, --output PATH     Output file path
  --format [json|yaml]  Output format (default: json)
  -v, --verbose         Enable verbose output
  --json                Output in JSON format
```

## API Reference

### `POST /v1/api/convert/from-okh-losh`

Accepts an OKH-LOSH `.toml` file upload and returns the parsed OKH manifest
as JSON.

**Request**: Multipart form upload with a `toml_file` field.

**Response**: `ConvertFromOkhLoshResponse` containing the full manifest and
conversion metadata.

## Bulk Import

For importing a directory of many OKH-LOSH TOML files at once (rather than
one file via the CLI/API), see `scripts/import_okh_losh_batch.py`
(`scripts/registry.toml` entry `import_okh_losh_batch`), which converts each
file, validates and auto-fixes it, and persists it through
`OKHService.create()`.
