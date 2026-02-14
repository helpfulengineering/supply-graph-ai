# Open Hardware Manager (OHM) Capabilities Cheatsheet

A quick reference guide for new users to understand the major capabilities of the Open Hardware Manager.

## Capabilities Overview

| Capability | Quick Summary | API Endpoint | CLI Command | Documentation Link |
|------------|---------------|--------------|-------------|-------------------|
| **Matching** | Match requirements (OKH manifests or recipes) with capabilities (OKW facilities or kitchens) across multiple domains using multi-layered matching algorithms | `POST /v1/api/match` | `ohm match` | [Matching Architecture](architecture/matching.md) |
| **Generation** | Generate OKH manifests from external project sources (GitHub, GitLab, etc.) using a 4-layer progressive enhancement system | `POST /v1/api/okh/generate-from-url` | `ohm okh generate-from-url` | [Generation Architecture](architecture/generation.md) |
| **Scaffolding** | Generate OKH-compliant project scaffolds with documentation stubs, MkDocs integration, and manifest templates | `POST /v1/api/okh/scaffold` | `ohm okh scaffold` | [Scaffolding Guide](scaffolding/index.md) |
| **OKH Management** | Create, read, update, delete, validate, fix, and extract requirements from OKH (OpenKnowHow) manifests | `POST /v1/api/okh/create`<br>`GET /v1/api/okh/{id}`<br>`PUT /v1/api/okh/{id}`<br>`DELETE /v1/api/okh/{id}`<br>`POST /v1/api/okh/validate`<br>`POST /v1/api/okh/extract`<br>`GET /v1/api/okh/` | `ohm okh create`<br>`ohm okh get`<br>`ohm okh list-manifests`<br>`ohm okh delete`<br>`ohm okh validate`<br>`ohm okh fix`<br>`ohm okh extract` | [OKH Model](models/okh-docs.md), [OKH API Routes](api/routes.md#okh-routes) |
| **OKW Management** | Create, read, update, delete, validate, fix, search, and extract capabilities from OKW (OpenKnowWhere) facilities | `POST /v1/api/okw/create`<br>`GET /v1/api/okw/{id}`<br>`PUT /v1/api/okw/{id}`<br>`DELETE /v1/api/okw/{id}`<br>`GET /v1/api/okw/search`<br>`POST /v1/api/okw/validate`<br>`POST /v1/api/okw/extract` | `ohm okw create`<br>`ohm okw get`<br>`ohm okw list-files`<br>`ohm okw delete`<br>`ohm okw search`<br>`ohm okw validate`<br>`ohm okw fix`<br>`ohm okw extract` | [OKW Model](models/okw-docs.md), [OKW API Routes](api/routes.md#okw-routes) |
| **Package Management** | Build, verify, list, delete, push, and pull OKH packages with remote storage integration | `POST /v1/api/package/build`<br>`GET /v1/api/package/list`<br>`GET /v1/api/package/{name}/{version}/verify`<br>`DELETE /v1/api/package/{name}/{version}`<br>`POST /v1/api/package/push`<br>`POST /v1/api/package/pull` | `ohm package build`<br>`ohm package list-packages`<br>`ohm package verify`<br>`ohm package delete`<br>`ohm package push`<br>`ohm package pull` | [Package Management](packaging/okh-packages.md) |
| **LLM Operations** | LLM-powered content generation, OKH manifest generation, and enhanced analysis with multiple provider support | `GET /v1/api/llm/health`<br>`GET /v1/api/llm/providers` | `ohm llm generate`<br>`ohm llm generate-okh`<br>`ohm llm providers info` | [LLM Integration](llm/index.md) |
| **Validation** | Domain-aware validation with quality levels (hobby, professional, medical) and strict mode support for OKH, OKW, and supply trees | `POST /v1/api/okh/validate`<br>`POST /v1/api/okw/validate`<br>`POST /v1/api/match/validate` | `ohm okh validate`<br>`ohm okw validate`<br>`ohm match validate` | [Validation Model](models/validation.md), [API Validation](api/routes.md#validation-and-normalization) |
| **Supply Tree Management** | Create, read, update, delete, and validate supply tree solutions that match requirements with capabilities | `POST /v1/api/supply-tree/create`<br>`GET /v1/api/supply-tree/{id}`<br>`PUT /v1/api/supply-tree/{id}`<br>`DELETE /v1/api/supply-tree/{id}`<br>`POST /v1/api/supply-tree/validate` | *Not available in CLI* | [Supply Tree Model](models/supply-tree.md), [Supply Tree API Routes](api/routes.md#supply-tree-routes) |
| **Domain Management** | List domains, get domain information, perform domain health checks, and detect domains from input data | `GET /v1/api/match/domains`<br>`GET /v1/api/match/domains/{name}`<br>`GET /v1/api/match/domains/{name}/health`<br>`POST /v1/api/match/detect-domain` | `ohm utility domains` | [Domains Overview](domains/index.md), [Domain API Routes](api/routes.md#domain-management-routes) |
| **File Upload** | Upload OKH/OKW files for storage and use in matching operations with automatic validation and parsing | `POST /v1/api/okh/upload`<br>`POST /v1/api/okw/upload`<br>`POST /v1/api/match/upload` | `ohm okh upload`<br>`ohm okw upload` | [API Routes - File Upload](api/routes.md#file-upload) |
| **Schema Export** | Export JSON schemas for OKH and OKW domain models in canonical format | `GET /v1/api/okh/export`<br>`GET /v1/api/okw/export` | `ohm okh export-schema`<br>`ohm okw export-schema` | [API Routes - Export Schema](api/routes.md#export-schema) |
| **Process Taxonomy** | Manage the canonical manufacturing process taxonomy used for normalization, matching, and validation. List processes, validate definitions, and reload at runtime | `GET /v1/api/taxonomy`<br>`POST /v1/api/taxonomy/reload`<br>`GET /v1/api/taxonomy/validate` | `ohm taxonomy list`<br>`ohm taxonomy validate`<br>`ohm taxonomy reload` | [Taxonomy ADR](architecture/process-taxonomy-adr.md), [CLI Taxonomy Commands](CLI/index.md#taxonomy-commands), [API Taxonomy Routes](api/routes.md#taxonomy-routes) |
| **System Health** | Monitor system health, check server connectivity, and view system status with diagnostics | `GET /health` | `ohm system health`<br>`ohm system status` | [System Routes](api/routes.md#system-routes) |

## Quick Reference by Use Case

### I want to...

#### Match requirements with capabilities
- **API**: `POST /v1/api/match` with OKH manifest or recipe
- **CLI**: `ohm match <okh-file>`
- **Docs**: [Matching Architecture](architecture/matching.md)

#### Generate an OKH manifest from a GitHub repository
- **API**: `POST /v1/api/okh/generate-from-url` with repository URL
- **CLI**: `ohm okh generate-from-url <url>`
- **Docs**: [Generation Architecture](architecture/generation.md)

#### Create a new OKH project structure
- **API**: `POST /v1/api/okh/scaffold` with project name and options
- **CLI**: `ohm okh scaffold <project-name>`
- **Docs**: [Scaffolding Guide](scaffolding/index.md)

#### Validate an OKH manifest
- **API**: `POST /v1/api/okh/validate?quality_level=professional`
- **CLI**: `ohm okh validate <manifest-file> --quality-level professional`
- **Docs**: [Validation Model](models/validation.md), [API Validation](api/routes.md#validation-and-normalization)

#### Build an OKH package
- **API**: `POST /v1/api/package/build` with manifest file
- **CLI**: `ohm package build <manifest-file>`
- **Docs**: [Package Management](packaging/okh-packages.md)

#### Search for manufacturing facilities
- **API**: `GET /v1/api/okw/search?location=United States&capabilities=CNC`
- **CLI**: `ohm okw search --location "United States" --capabilities CNC`
- **Docs**: [OKW Model](models/okw-docs.md), [OKW API Routes](api/routes.md#okw-routes)

#### Use LLM for enhanced processing
- **API**: Add `use_llm: true` to request body (where supported)
- **CLI**: Add `--use-llm --llm-provider anthropic` to any command
- **Docs**: [LLM Integration](llm/index.md)

#### Manage the process taxonomy
- **API**: `GET /v1/api/taxonomy` to list, `POST /v1/api/taxonomy/reload` to reload
- **CLI**: `ohm taxonomy list`, `ohm taxonomy validate`, `ohm taxonomy reload`
- **Docs**: [Taxonomy ADR](architecture/process-taxonomy-adr.md), [CLI Taxonomy Commands](CLI/index.md#taxonomy-commands)

## Command Groups Summary

The CLI is organized into 8 command groups:

1. **`ohm match`** - Requirements-to-capabilities matching (3 commands)
2. **`ohm okh`** - OKH manifest management (8 commands)
3. **`ohm okw`** - OKW facility management (9 commands)
4. **`ohm package`** - Package management (9 commands)
5. **`ohm llm`** - LLM operations (available if LLM enabled)
6. **`ohm system`** - System administration (5 commands)
7. **`ohm utility`** - Utility operations (2 commands)
8. **`ohm taxonomy`** - Process taxonomy management (3 commands)

## Documentation Links

- **Main Documentation**: [index.md](index.md)
- **API Documentation**: [api/routes.md](api/routes.md)
- **CLI Documentation**: [CLI/index.md](CLI/index.md)
- **Architecture Overview**: [architecture/index.md](architecture/index.md)
- **Matching System**: [architecture/matching.md](architecture/matching.md), [Matching Overview](matching/index.md)
- **Generation System**: [architecture/generation.md](architecture/generation.md)
- **LLM Integration**: [llm/index.md](llm/index.md)
- **Scaffolding**: [scaffolding/index.md](scaffolding/index.md)
- **OKH Model**: [models/okh-docs.md](models/okh-docs.md)
- **OKW Model**: [models/okw-docs.md](models/okw-docs.md)
- **Supply Tree Model**: [models/supply-tree.md](models/supply-tree.md)
- **Validation**: [models/validation.md](models/validation.md)
- **Domains**: [domains/index.md](domains/index.md)

## Notes

- All API endpoints are prefixed with `/v1/api/`
- Most CLI commands support `--use-llm` for enhanced processing
- Quality levels: `hobby`, `professional`, `medical`
- Validation supports `--strict-mode` for maximum validation coverage
- Package operations support remote storage (Azure Blob Storage)
- Matching supports multiple domains (manufacturing, cooking, etc.)

