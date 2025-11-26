# Rules Management System - Technical Specification

## Executive Summary

This specification outlines the refactoring of the Capability-Centric Heuristic Rules System to provide a production-ready, user-accessible rules management system with full API and CLI support. The system will enable users to inspect, modify, import, export, and validate matching rules through both programmatic and interactive interfaces.

## Table of Contents

1. [Overview](#overview)
2. [Architecture](#architecture)
3. [Data Model](#data-model)
4. [File Structure](#file-structure)
5. [API Endpoints](#api-endpoints)
6. [CLI Commands](#cli-commands)
7. [Import/Export System](#importexport-system)
8. [Validation System](#validation-system)
9. [Error Handling](#error-handling)
10. [Implementation Plan](#implementation-plan)
11. [Future Enhancements](#future-enhancements)

---

## Overview

### Goals

1. **Accessibility**: Move rules from hidden source code location to accessible configuration directory
2. **User Control**: Enable users to inspect, modify, and manage rules via API and CLI
3. **Data Integrity**: Implement robust validation using enhanced dataclass validation
4. **Production Ready**: Support import/export, validation, rollback, and dry-run operations
5. **Developer Experience**: Provide interactive CLI mode and comprehensive error messages

### Key Requirements

- Rules stored in `src/config/rules/` directory
- Dataclass-based validation (enhanced existing validation)
- Support for YAML and JSON formats
- Partial update support for imports
- Dry-run mode for safe testing
- Rollback capability for failed imports
- Full API and CLI coverage
- Interactive CLI mode

---

## Architecture

### System Components

```
┌─────────────────────────────────────────────────────────────┐
│                    Rules Management System                    │
├─────────────────────────────────────────────────────────────┤
│                                                               │
│  ┌──────────────┐    ┌──────────────┐    ┌──────────────┐  │
│  │   API Layer  │    │   CLI Layer  │    │  File System │  │
│  │  (FastAPI)   │    │   (Click)    │    │   (YAML/JSON)│  │
│  └──────┬───────┘    └──────┬───────┘    └──────┬───────┘  │
│         │                    │                    │          │
│         └────────────────────┼────────────────────┘          │
│                              │                               │
│                    ┌─────────▼─────────┐                     │
│                    │  Rules Service    │                     │
│                    │  (Business Logic) │                     │
│                    └─────────┬─────────┘                     │
│                              │                               │
│         ┌────────────────────┼────────────────────┐          │
│         │                    │                    │          │
│  ┌──────▼──────┐    ┌───────▼──────┐    ┌───────▼──────┐  │
│  │  Validation │    │ Import/Export │    │ Rule Manager │  │
│  │   Service   │    │    Service    │    │   (Core)     │  │
│  └─────────────┘    └───────────────┘    └──────────────┘  │
│                                                               │
│  ┌─────────────────────────────────────────────────────────┐ │
│  │     Dataclass Models (Internal Data + Validation)       │ │
│  │     Pydantic Models (API Request/Response Only)         │ │
│  └─────────────────────────────────────────────────────────┘ │
│                                                               │
└─────────────────────────────────────────────────────────────┘
```

### Component Responsibilities

1. **Rules Service**: Business logic for rule operations (CRUD, import/export, validation)
2. **Validation Service**: Dataclass-based validation using constructor methods
3. **Import/Export Service**: File format conversion and transformation using dataclass serialization
4. **Rule Manager**: Core rule storage and retrieval (existing, enhanced)
5. **API Layer**: RESTful endpoints for all operations (uses Pydantic for request/response only)
6. **CLI Layer**: Command-line interface mirroring API operations

---

## Data Model

### Internal Data Model (Dataclasses)

The system will continue using the existing dataclass-based approach for internal data representation. This keeps the implementation simple, maintains consistency with the existing codebase, and avoids unnecessary complexity.

#### Enhanced Dataclass Validation

The existing `CapabilityRule` and `CapabilityRuleSet` dataclasses already have validation in `__post_init__`. We'll enhance this validation slightly to provide better error messages and catch additional edge cases:

```python
# src/core/matching/capability_rules.py (enhancements)

@dataclass
class CapabilityRule:
    # ... existing fields ...
    
    def __post_init__(self):
        """Validate rule data after initialization"""
        # Enhanced validation with better error messages
        if not self.capability or not self.capability.strip():
            raise ValueError(f"Rule {self.id}: capability cannot be empty or whitespace")
        
        if not self.satisfies_requirements:
            raise ValueError(f"Rule {self.id}: satisfies_requirements cannot be empty")
        
        # Validate each requirement is non-empty
        for i, req in enumerate(self.satisfies_requirements):
            if not isinstance(req, str):
                raise ValueError(
                    f"Rule {self.id}: requirement at index {i} must be a string, got {type(req).__name__}"
                )
            if not req.strip():
                raise ValueError(f"Rule {self.id}: requirement at index {i} cannot be empty or whitespace")
        
        if not 0.0 <= self.confidence <= 1.0:
            raise ValueError(f"Rule {self.id}: confidence must be between 0.0 and 1.0, got {self.confidence}")
        
        if not self.domain or not self.domain.strip():
            raise ValueError(f"Rule {self.id}: domain cannot be empty or whitespace")
        
        # Validate rule ID format (optional but recommended)
        if not self.id or not self.id.strip():
            raise ValueError(f"Rule ID cannot be empty or whitespace")
        
        # Check for duplicate requirements (warning, not error)
        if len(self.satisfies_requirements) != len(set(r.lower().strip() for r in self.satisfies_requirements)):
            logger.warning(f"Rule {self.id}: duplicate requirements detected (case-insensitive)")

@dataclass
class CapabilityRuleSet:
    # ... existing fields ...
    
    def __post_init__(self):
        """Validate rule set data after initialization"""
        if not self.domain or not self.domain.strip():
            raise ValueError("Rule set domain cannot be empty or whitespace")
        
        if not self.rules:
            raise ValueError(f"Rule set for domain '{self.domain}' must contain at least one rule")
        
        # Validate domain consistency
        for rule_id, rule in self.rules.items():
            if rule.domain != self.domain and rule.domain != "general":
                logger.warning(
                    f"Rule {rule_id} has domain '{rule.domain}' but rule set is for domain '{self.domain}'"
                )
        
        # Validate version format (semantic versioning)
        import re
        if not re.match(r'^\d+\.\d+\.\d+$', self.version):
            logger.warning(f"Rule set version '{self.version}' does not follow semantic versioning (X.Y.Z)")
```

#### Serialization Methods

The existing `to_dict()` and `from_dict()` methods are sufficient. We'll add an optional parameter to control metadata inclusion:

```python
# src/core/matching/capability_rules.py (enhancements)

@dataclass
class CapabilityRule:
    # ... existing code ...
    
    def to_dict(self, include_metadata: bool = False) -> Dict[str, Any]:
        """Convert rule to dictionary for serialization"""
        result = {
            "id": self.id,
            "type": self.type.value,
            "capability": self.capability,
            "satisfies_requirements": self.satisfies_requirements,
            "direction": self.direction.value,
            "confidence": self.confidence,
            "domain": self.domain,
            "description": self.description,
            "source": self.source,
            "tags": list(self.tags),
        }
        
        if include_metadata:
            result["created_at"] = self.created_at.isoformat()
            result["updated_at"] = self.updated_at.isoformat()
        
        return result
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'CapabilityRule':
        """Create rule from dictionary with validation"""
        try:
            return cls(
                id=data["id"],
                type=RuleType(data["type"]),
                capability=data["capability"],
                satisfies_requirements=data["satisfies_requirements"],
                direction=RuleDirection(data.get("direction", "bidirectional")),
                confidence=data.get("confidence", 0.9),
                domain=data.get("domain", "general"),
                description=data.get("description", ""),
                source=data.get("source", ""),
                tags=set(data.get("tags", [])),
                created_at=datetime.fromisoformat(data.get("created_at", datetime.now().isoformat())),
                updated_at=datetime.fromisoformat(data.get("updated_at", datetime.now().isoformat()))
            )
        except (KeyError, ValueError, TypeError) as e:
            raise ValueError(f"Invalid rule data: {str(e)}") from e

@dataclass
class CapabilityRuleSet:
    # ... existing code ...
    
    def to_dict(self, include_metadata: bool = False) -> Dict[str, Any]:
        """Convert rule set to dictionary for serialization"""
        result = {
            "domain": self.domain,
            "version": self.version,
            "description": self.description,
            "rules": {rule_id: rule.to_dict(include_metadata=include_metadata) 
                     for rule_id, rule in self.rules.items()},
            "metadata": self.metadata,
        }
        
        if include_metadata:
            result["created_at"] = self.created_at.isoformat()
            result["updated_at"] = self.updated_at.isoformat()
        
        return result
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'CapabilityRuleSet':
        """Create rule set from dictionary with validation"""
        try:
            rule_set = cls(
                domain=data["domain"],
                version=data.get("version", "1.0.0"),
                description=data.get("description", ""),
                metadata=data.get("metadata", {}),
                created_at=datetime.fromisoformat(data.get("created_at", datetime.now().isoformat())),
                updated_at=datetime.fromisoformat(data.get("updated_at", datetime.now().isoformat()))
            )
            
            # Load rules
            for rule_data in data.get("rules", {}).values():
                rule = CapabilityRule.from_dict(rule_data)
                rule_set.add_rule(rule)
            
            return rule_set
        except (KeyError, ValueError, TypeError) as e:
            raise ValueError(f"Invalid rule set data: {str(e)}") from e
```

### API Request/Response Models (Pydantic)

For the API layer, we'll use Pydantic models for request/response validation, following the existing pattern in the codebase. These models will wrap the dataclass data for API serialization.

---

## File Structure

### Directory Layout

```
src/
├── config/
│   └── rules/                          # NEW: User-accessible rules directory
│       ├── manufacturing.yaml          # Moved from src/core/matching/rules/
│       ├── cooking.yaml                # Moved from src/core/matching/rules/
│       └── .gitkeep                    # Ensure directory is tracked
│
├── core/
│   ├── matching/
│   │   ├── rules/                      # NEW: Rules management module
│   │   │   ├── __init__.py
│   │   │   ├── service.py              # Rules business logic service
│   │   │   ├── validation.py           # Validation service (dataclass-based)
│   │   │   └── import_export.py        # Import/export service
│   │   │
│   │   └── capability_rules.py         # Existing (enhanced validation)
│   │
│   └── api/
│       ├── routes/
│       │   └── rules.py                # NEW: Rules API routes
│       └── models/
│           └── rules/                  # NEW: Rules API models
│               ├── __init__.py
│               ├── request.py          # Request models
│               └── response.py         # Response models
│
└── cli/
    └── match.py                        # Enhanced with rules commands
```

### File Migration

1. **Move existing rule files**:
   - `src/core/matching/rules/manufacturing.yaml` → `src/config/rules/manufacturing.yaml`
   - `src/core/matching/rules/cooking.yaml` → `src/config/rules/cooking.yaml`

2. **Update RuleManager default path**:
   - Change `_get_default_rules_directory()` to point to `src/config/rules/`

---

## API Endpoints

### Endpoint Structure

All endpoints will be under `/v1/api/match/rules` to align with the matching domain.

### Request/Response Models

```python
# src/core/api/models/rules/request.py

from pydantic import BaseModel, Field
from typing import Optional, Dict, Any, List
from ..base import BaseAPIRequest

class RuleListRequest(BaseAPIRequest):
    """Request for listing rules"""
    domain: Optional[str] = Field(None, description="Filter by domain")
    tag: Optional[str] = Field(None, description="Filter by tag")
    include_metadata: bool = Field(False, description="Include metadata in response")

class RuleGetRequest(BaseAPIRequest):
    """Request for getting a specific rule"""
    domain: str = Field(..., description="Domain of the rule")
    rule_id: str = Field(..., description="Rule identifier")

class RuleCreateRequest(BaseAPIRequest):
    """Request for creating a new rule"""
    rule: Dict[str, Any] = Field(..., description="Rule data")

class RuleUpdateRequest(BaseAPIRequest):
    """Request for updating an existing rule"""
    domain: str = Field(..., description="Domain of the rule")
    rule_id: str = Field(..., description="Rule identifier")
    rule: Dict[str, Any] = Field(..., description="Updated rule data")

class RuleDeleteRequest(BaseAPIRequest):
    """Request for deleting a rule"""
    domain: str = Field(..., description="Domain of the rule")
    rule_id: str = Field(..., description="Rule identifier")

class RuleImportRequest(BaseAPIRequest):
    """Request for importing rules"""
    file_content: str = Field(..., description="File content (YAML or JSON)")
    file_format: str = Field(..., description="File format: 'yaml' or 'json'")
    domain: Optional[str] = Field(None, description="Target domain (if importing single domain)")
    partial_update: bool = Field(True, description="Allow partial updates")
    dry_run: bool = Field(False, description="Validate without applying changes")

class RuleExportRequest(BaseAPIRequest):
    """Request for exporting rules"""
    domain: Optional[str] = Field(None, description="Export specific domain (all if not specified)")
    format: str = Field("yaml", description="Export format: 'yaml' or 'json'")
    include_metadata: bool = Field(False, description="Include metadata in export")

class RuleValidateRequest(BaseAPIRequest):
    """Request for validating rules"""
    file_content: str = Field(..., description="File content to validate")
    file_format: str = Field(..., description="File format: 'yaml' or 'json'")

class RuleCompareRequest(BaseAPIRequest):
    """Request for comparing rules (dry-run import)"""
    file_content: str = Field(..., description="File content to compare")
    file_format: str = Field(..., description="File format: 'yaml' or 'json'")
    domain: Optional[str] = Field(None, description="Compare specific domain")

class RuleResetRequest(BaseAPIRequest):
    """Request for resetting rules (clear all)"""
    confirm: bool = Field(False, description="Confirmation flag")
```

```python
# src/core/api/models/rules/response.py

from pydantic import BaseModel, Field
from typing import Optional, Dict, Any, List
from ..base import SuccessResponse
from datetime import datetime

class RuleResponse(SuccessResponse):
    """Response containing a single rule"""
    data: Dict[str, Any] = Field(..., description="Rule data")

class RuleListResponse(SuccessResponse):
    """Response containing a list of rules"""
    data: Dict[str, Any] = Field(..., description="Rules data with pagination")
    # data structure: {
    #   "rules": [...],
    #   "total": 42,
    #   "domains": ["manufacturing", "cooking"]
    # }

class RuleImportResponse(SuccessResponse):
    """Response from rule import operation"""
    data: Dict[str, Any] = Field(..., description="Import results")
    # data structure: {
    #   "imported_rules": 10,
    #   "updated_rules": 2,
    #   "errors": [],
    #   "dry_run": false
    # }

class RuleExportResponse(SuccessResponse):
    """Response from rule export operation"""
    data: Dict[str, Any] = Field(..., description="Export data")
    # data structure: {
    #   "content": "...",
    #   "format": "yaml",
    #   "domain": "manufacturing",
    #   "rule_count": 15
    # }

class RuleValidateResponse(SuccessResponse):
    """Response from rule validation"""
    data: Dict[str, Any] = Field(..., description="Validation results")
    # data structure: {
    #   "valid": true,
    #   "errors": [],
    #   "warnings": []
    # }

class RuleCompareResponse(SuccessResponse):
    """Response from rule comparison (dry-run)"""
    data: Dict[str, Any] = Field(..., description="Comparison results")
    # data structure: {
    #   "changes": {
    #     "added": [...],
    #     "updated": [...],
    #     "deleted": [...]
    #   },
    #   "summary": {
    #     "total_added": 5,
    #     "total_updated": 2,
    #     "total_deleted": 1
    #   }
    # }
```

### Endpoint Definitions

```python
# src/core/api/routes/rules.py

from fastapi import APIRouter, HTTPException, Depends, status
from typing import Optional
from ..models.rules.request import *
from ..models.rules.response import *
from ...matching.rules.service import RulesService
from ..error_handlers import create_error_response, create_success_response

router = APIRouter(
    prefix="/api/match/rules",
    tags=["rules"]
)

# Dependency
async def get_rules_service() -> RulesService:
    """Get rules service instance"""
    return await RulesService.get_instance()

# Endpoints

@router.get("/", response_model=RuleListResponse)
async def list_rules(
    request: RuleListRequest = Depends(),
    service: RulesService = Depends(get_rules_service)
):
    """List all rules, optionally filtered by domain or tag"""
    # Implementation

@router.get("/{domain}/{rule_id}", response_model=RuleResponse)
async def get_rule(
    domain: str,
    rule_id: str,
    request: RuleGetRequest = Depends(),
    service: RulesService = Depends(get_rules_service)
):
    """Get a specific rule by domain and ID"""
    # Implementation

@router.post("/", response_model=RuleResponse, status_code=status.HTTP_201_CREATED)
async def create_rule(
    request: RuleCreateRequest,
    service: RulesService = Depends(get_rules_service)
):
    """Create a new rule"""
    # Implementation

@router.put("/{domain}/{rule_id}", response_model=RuleResponse)
async def update_rule(
    domain: str,
    rule_id: str,
    request: RuleUpdateRequest,
    service: RulesService = Depends(get_rules_service)
):
    """Update an existing rule"""
    # Implementation

@router.delete("/{domain}/{rule_id}", response_model=SuccessResponse)
async def delete_rule(
    domain: str,
    rule_id: str,
    request: RuleDeleteRequest = Depends(),
    service: RulesService = Depends(get_rules_service)
):
    """Delete a rule"""
    # Implementation

@router.post("/import", response_model=RuleImportResponse)
async def import_rules(
    request: RuleImportRequest,
    service: RulesService = Depends(get_rules_service)
):
    """Import rules from YAML or JSON file content"""
    # Implementation

@router.post("/export", response_model=RuleExportResponse)
async def export_rules(
    request: RuleExportRequest = Depends(),
    service: RulesService = Depends(get_rules_service)
):
    """Export rules to YAML or JSON format"""
    # Implementation

@router.post("/validate", response_model=RuleValidateResponse)
async def validate_rules(
    request: RuleValidateRequest,
    service: RulesService = Depends(get_rules_service)
):
    """Validate rule file content without importing"""
    # Implementation

@router.post("/compare", response_model=RuleCompareResponse)
async def compare_rules(
    request: RuleCompareRequest,
    service: RulesService = Depends(get_rules_service)
):
    """Compare imported rules with current rules (dry-run)"""
    # Implementation

@router.post("/reset", response_model=SuccessResponse)
async def reset_rules(
    request: RuleResetRequest,
    service: RulesService = Depends(get_rules_service)
):
    """Reset all rules (clear all rule sets)"""
    # Implementation
```

---

## CLI Commands

### Command Structure

All commands will be under the `match` group: `ome match rules <command>`

### Command Definitions

```python
# src/cli/match.py (additions)

@match_group.group()
def rules():
    """Manage matching rules"""
    pass

@rules.command("list")
@click.option('--domain', help='Filter by domain')
@click.option('--tag', help='Filter by tag')
@click.option('--include-metadata', is_flag=True, help='Include metadata')
@standard_cli_command(...)
async def rules_list(ctx, domain, tag, include_metadata, ...):
    """List all rules"""
    # Implementation

@rules.command("get")
@click.argument('domain')
@click.argument('rule_id')
@standard_cli_command(...)
async def rules_get(ctx, domain, rule_id, ...):
    """Get a specific rule"""
    # Implementation

@rules.command("create")
@click.option('--file', type=click.Path(exists=True), help='Rule file (YAML/JSON)')
@click.option('--interactive', '-i', is_flag=True, help='Interactive mode')
@standard_cli_command(...)
async def rules_create(ctx, file, interactive, ...):
    """Create a new rule"""
    # Implementation

@rules.command("update")
@click.argument('domain')
@click.argument('rule_id')
@click.option('--file', type=click.Path(exists=True), help='Updated rule file')
@click.option('--interactive', '-i', is_flag=True, help='Interactive mode')
@standard_cli_command(...)
async def rules_update(ctx, domain, rule_id, file, interactive, ...):
    """Update an existing rule"""
    # Implementation

@rules.command("delete")
@click.argument('domain')
@click.argument('rule_id')
@click.option('--confirm', is_flag=True, help='Skip confirmation prompt')
@standard_cli_command(...)
async def rules_delete(ctx, domain, rule_id, confirm, ...):
    """Delete a rule"""
    # Implementation

@rules.command("import")
@click.argument('file', type=click.Path(exists=True))
@click.option('--domain', help='Target domain (if importing single domain)')
@click.option('--partial-update/--no-partial-update', default=True, help='Allow partial updates')
@click.option('--dry-run', is_flag=True, help='Validate without applying changes')
@standard_cli_command(...)
async def rules_import(ctx, file, domain, partial_update, dry_run, ...):
    """Import rules from YAML or JSON file"""
    # Implementation

@rules.command("export")
@click.argument('output_file', type=click.Path())
@click.option('--domain', help='Export specific domain (all if not specified)')
@click.option('--format', type=click.Choice(['yaml', 'json']), default='yaml', help='Export format')
@click.option('--include-metadata', is_flag=True, help='Include metadata')
@standard_cli_command(...)
async def rules_export(ctx, output_file, domain, format, include_metadata, ...):
    """Export rules to YAML or JSON file"""
    # Implementation

@rules.command("validate")
@click.argument('file', type=click.Path(exists=True))
@standard_cli_command(...)
async def rules_validate(ctx, file, ...):
    """Validate rule file without importing"""
    # Implementation

@rules.command("compare")
@click.argument('file', type=click.Path(exists=True))
@click.option('--domain', help='Compare specific domain')
@standard_cli_command(...)
async def rules_compare(ctx, file, domain, ...):
    """Compare rules file with current rules (dry-run)"""
    # Implementation

@rules.command("reset")
@click.option('--confirm', is_flag=True, help='Skip confirmation prompt')
@standard_cli_command(...)
async def rules_reset(ctx, confirm, ...):
    """Reset all rules (clear all rule sets)"""
    # Implementation
```

### Interactive Mode

For `create` and `update` commands, interactive mode will prompt for rule fields:

```python
def interactive_rule_creation():
    """Interactive rule creation wizard"""
    click.echo("Creating new rule...")
    
    rule_id = click.prompt("Rule ID", type=str)
    capability = click.prompt("Capability", type=str)
    
    requirements = []
    click.echo("Enter requirements (empty line to finish):")
    while True:
        req = click.prompt("Requirement", default="", show_default=False)
        if not req:
            break
        requirements.append(req)
    
    confidence = click.prompt("Confidence (0.0-1.0)", type=float, default=0.9)
    domain = click.prompt("Domain", type=str, default="general")
    description = click.prompt("Description", default="", show_default=False)
    
    # Create and return rule dict
    return {
        "id": rule_id,
        "type": "capability_match",
        "capability": capability,
        "satisfies_requirements": requirements,
        "confidence": confidence,
        "domain": domain,
        "description": description
    }
```

---

## Import/Export System

### Import Service

```python
# src/core/matching/rules/import_export.py

from typing import Dict, Any, Optional, Tuple
from pathlib import Path
import yaml
import json
from .models import CapabilityRuleSetModel
from .validation import ValidationService
from .service import RulesService

class ImportExportService:
    """Service for importing and exporting rules"""
    
    def __init__(self, validation_service: ValidationService, rules_service: RulesService):
        self.validation_service = validation_service
        self.rules_service = rules_service
    
    async def import_rules(
        self,
        file_content: str,
        file_format: str,
        domain: Optional[str] = None,
        partial_update: bool = True,
        dry_run: bool = False
    ) -> Dict[str, Any]:
        """
        Import rules from file content.
        
        Returns:
            Dict with import results including:
            - imported_rules: number of new rules
            - updated_rules: number of updated rules
            - errors: list of errors
            - dry_run: whether this was a dry run
        """
        # Parse file content
        if file_format.lower() == 'yaml':
            data = yaml.safe_load(file_content)
        elif file_format.lower() == 'json':
            data = json.loads(file_content)
        else:
            raise ValueError(f"Unsupported file format: {file_format}")
        
        # Validate using dataclass constructor (will raise ValueError if invalid)
        validation_result = await self.validation_service.validate_rule_set(data)
        if not validation_result['valid']:
            raise ValueError(f"Validation failed: {validation_result['errors']}")
        
        # Convert to dataclass (this also validates)
        rule_set = CapabilityRuleSet.from_dict(data)
        
        # Filter by domain if specified
        if domain and rule_set.domain != domain:
            raise ValueError(f"Rule set domain '{rule_set.domain}' does not match requested domain '{domain}'")
        
        if dry_run:
            # Return comparison results without applying
            return await self._compare_rules(rule_set)
        
        # Apply changes
        return await self.rules_service.import_rule_set(rule_set, partial_update=partial_update)
    
    async def export_rules(
        self,
        domain: Optional[str] = None,
        format: str = "yaml",
        include_metadata: bool = False
    ) -> Tuple[str, Dict[str, Any]]:
        """
        Export rules to file content.
        
        Returns:
            Tuple of (file_content, metadata)
        """
        # Get rules from service
        rule_sets = await self.rules_service.get_rule_sets(domain=domain)
        
        if domain:
            # Export single domain
            rule_set = rule_sets[domain]
            data = rule_set.to_dict(include_metadata=include_metadata)
        else:
            # Export all domains
            data = {
                "domains": {
                    domain: rule_set.to_dict(include_metadata=include_metadata)
                    for domain, rule_set in rule_sets.items()
                }
            }
        
        # Serialize to requested format
        if format.lower() == 'yaml':
            content = yaml.dump(data, default_flow_style=False, sort_keys=False)
        elif format.lower() == 'json':
            content = json.dumps(data, indent=2)
        else:
            raise ValueError(f"Unsupported export format: {format}")
        
        metadata = {
            "format": format,
            "domain": domain or "all",
            "rule_count": sum(len(rs.rules) for rs in rule_sets.values())
        }
        
        return content, metadata
    
    async def _compare_rules(self, new_rule_set: CapabilityRuleSet) -> Dict[str, Any]:
        """Compare new rules with existing rules"""
        existing_rule_set = await self.rules_service.get_rule_set(new_rule_set.domain)
        
        if not existing_rule_set:
            return {
                "changes": {
                    "added": list(new_rule_set.rules.keys()),
                    "updated": [],
                    "deleted": []
                },
                "summary": {
                    "total_added": len(new_rule_set.rules),
                    "total_updated": 0,
                    "total_deleted": 0
                }
            }
        
        added = []
        updated = []
        deleted = []
        
        # Find added and updated rules
        for rule_id, new_rule in new_rule_set.rules.items():
            if rule_id not in existing_rule_set.rules:
                added.append(rule_id)
            else:
                # Compare rules by comparing their dict representations
                existing_rule = existing_rule_set.rules[rule_id]
                # Exclude metadata for comparison
                if new_rule.to_dict(include_metadata=False) != existing_rule.to_dict(include_metadata=False):
                    updated.append(rule_id)
        
        # Find deleted rules
        for rule_id in existing_rule_set.rules:
            if rule_id not in new_rule_set.rules:
                deleted.append(rule_id)
        
        return {
            "changes": {
                "added": added,
                "updated": updated,
                "deleted": deleted
            },
            "summary": {
                "total_added": len(added),
                "total_updated": len(updated),
                "total_deleted": len(deleted)
            }
        }
```

### Export Format Examples

**YAML Export (default, no metadata)**:
```yaml
domain: manufacturing
version: "1.0.0"
description: "Capability-centric rules for manufacturing domain"
rules:
  cnc_machining_capability:
    id: "cnc_machining_capability"
    type: "capability_match"
    capability: "cnc machining"
    satisfies_requirements: ["milling", "machining", "material removal"]
    confidence: 0.95
    domain: "manufacturing"
    description: "CNC machining can satisfy various milling requirements"
    source: "ISO Manufacturing Terminology"
    tags: ["machining", "automation", "subtractive"]
```

**JSON Export (with metadata)**:
```json
{
  "domain": "manufacturing",
  "version": "1.0.0",
  "description": "Capability-centric rules for manufacturing domain",
  "rules": {
    "cnc_machining_capability": {
      "id": "cnc_machining_capability",
      "type": "capability_match",
      "capability": "cnc machining",
      "satisfies_requirements": ["milling", "machining", "material removal"],
      "confidence": 0.95,
      "domain": "manufacturing",
      "description": "CNC machining can satisfy various milling requirements",
      "source": "ISO Manufacturing Terminology",
      "tags": ["machining", "automation", "subtractive"],
      "created_at": "2024-01-01T12:00:00Z",
      "updated_at": "2024-01-15T10:30:00Z"
    }
  },
  "metadata": {
    "maintainer": "OME Manufacturing Team",
    "last_updated": "2024-01-01"
  },
  "created_at": "2024-01-01T12:00:00Z",
  "updated_at": "2024-01-15T10:30:00Z"
}
```

---

## Validation System

### Validation Service

The validation service uses the dataclass constructors to validate data. The `from_dict()` methods will raise `ValueError` with descriptive messages if validation fails.

```python
# src/core/matching/rules/validation.py

from typing import Dict, Any, List
from ..capability_rules import CapabilityRule, CapabilityRuleSet

class ValidationService:
    """Service for validating rule data using dataclass constructors"""
    
    async def validate_rule_set(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Validate rule set data by attempting to construct CapabilityRuleSet.
        
        Returns:
            Dict with validation results:
            - valid: bool
            - errors: list of error messages
            - warnings: list of warning messages
        """
        errors = []
        warnings = []
        
        try:
            # Attempt to construct rule set (this will validate via __post_init__)
            rule_set = CapabilityRuleSet.from_dict(data)
            
            # Additional business logic validations
            warnings.extend(self._validate_business_rules(rule_set))
            
            return {
                "valid": True,
                "errors": [],
                "warnings": warnings
            }
        except ValueError as e:
            # Dataclass validation errors
            errors.append(str(e))
            return {
                "valid": False,
                "errors": errors,
                "warnings": warnings
            }
        except (KeyError, TypeError) as e:
            # Missing required fields or type errors
            errors.append(f"Invalid data structure: {str(e)}")
            return {
                "valid": False,
                "errors": errors,
                "warnings": warnings
            }
        except Exception as e:
            # Unexpected errors
            errors.append(f"Validation error: {str(e)}")
            return {
                "valid": False,
                "errors": errors,
                "warnings": warnings
            }
    
    async def validate_rule(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Validate a single rule by attempting to construct CapabilityRule"""
        errors = []
        warnings = []
        
        try:
            # Attempt to construct rule (this will validate via __post_init__)
            rule = CapabilityRule.from_dict(data)
            
            # Additional business logic validations
            warnings.extend(self._validate_rule_business_rules(rule))
            
            return {
                "valid": True,
                "errors": [],
                "warnings": warnings
            }
        except ValueError as e:
            errors.append(str(e))
            return {
                "valid": False,
                "errors": errors,
                "warnings": warnings
            }
        except (KeyError, TypeError) as e:
            errors.append(f"Invalid data structure: {str(e)}")
            return {
                "valid": False,
                "errors": errors,
                "warnings": warnings
            }
        except Exception as e:
            errors.append(f"Validation error: {str(e)}")
            return {
                "valid": False,
                "errors": errors,
                "warnings": warnings
            }
    
    def _validate_business_rules(self, rule_set: CapabilityRuleSet) -> List[str]:
        """Additional business logic validations"""
        warnings = []
        
        # Check for duplicate rule IDs across domains (future enhancement)
        # Check for conflicting rules (future enhancement)
        
        # Check for rules with very low confidence
        low_confidence_rules = [
            rule_id for rule_id, rule in rule_set.rules.items()
            if rule.confidence < 0.5
        ]
        if low_confidence_rules:
            warnings.append(
                f"Rules with low confidence (< 0.5): {', '.join(low_confidence_rules)}"
            )
        
        return warnings
    
    def _validate_rule_business_rules(self, rule: CapabilityRule) -> List[str]:
        """Additional business logic validations for individual rules"""
        warnings = []
        
        # Check for duplicate requirements (case-insensitive)
        req_lower = [r.lower().strip() for r in rule.satisfies_requirements]
        if len(req_lower) != len(set(req_lower)):
            warnings.append("Duplicate requirements found in satisfies_requirements (case-insensitive)")
        
        # Check confidence thresholds
        if rule.confidence < 0.5:
            warnings.append("Low confidence score (< 0.5) may result in poor matches")
        
        # Check for very long requirement lists (might indicate over-broad rule)
        if len(rule.satisfies_requirements) > 20:
            warnings.append("Rule has many requirements (> 20), consider splitting into multiple rules")
        
        return warnings
```

### Schema Generation (Optional)

For documentation purposes, we can generate a simple JSON schema from the dataclass structure. This is optional and not required for functionality:

```python
# src/core/matching/rules/schema.py (optional)

from typing import Dict, Any
import json

def generate_json_schema() -> Dict[str, Any]:
    """Generate a simple JSON schema from dataclass structure"""
    # This is a simplified schema for documentation
    # Full validation is done via dataclass constructors
    return {
        "type": "object",
        "required": ["domain", "version", "rules"],
        "properties": {
            "domain": {"type": "string", "minLength": 1},
            "version": {"type": "string", "pattern": "^\\d+\\.\\d+\\.\\d+$"},
            "description": {"type": "string"},
            "rules": {
                "type": "object",
                "additionalProperties": {
                    "type": "object",
                    "required": ["id", "type", "capability", "satisfies_requirements"],
                    "properties": {
                        "id": {"type": "string"},
                        "type": {"type": "string", "enum": ["capability_match"]},
                        "capability": {"type": "string", "minLength": 1},
                        "satisfies_requirements": {
                            "type": "array",
                            "items": {"type": "string", "minLength": 1},
                            "minItems": 1
                        },
                        "direction": {"type": "string", "enum": ["bidirectional", "forward", "reverse"]},
                        "confidence": {"type": "number", "minimum": 0.0, "maximum": 1.0},
                        "domain": {"type": "string"},
                        "description": {"type": "string"},
                        "source": {"type": "string"},
                        "tags": {"type": "array", "items": {"type": "string"}}
                    }
                }
            },
            "metadata": {"type": "object"}
        }
    }

def save_schema_to_file(file_path: str):
    """Save JSON schema to file (for documentation)"""
    schema = generate_json_schema()
    with open(file_path, 'w') as f:
        json.dump(schema, f, indent=2)
```

---

## Error Handling

### Error Types

```python
# src/core/matching/rules/exceptions.py

class RulesError(Exception):
    """Base exception for rules operations"""
    pass

class RuleNotFoundError(RulesError):
    """Rule not found"""
    pass

class RuleValidationError(RulesError):
    """Rule validation failed"""
    pass

class RuleImportError(RulesError):
    """Rule import failed"""
    pass

class RuleExportError(RulesError):
    """Rule export failed"""
    pass
```

### Error Response Format

All API errors will follow the standard error response format:

```json
{
  "success": false,
  "status": "error",
  "message": "Human-readable error message",
  "error_code": "RULE_NOT_FOUND",
  "errors": [
    {
      "field": "rule_id",
      "message": "Rule 'invalid_id' not found in domain 'manufacturing'"
    }
  ],
  "request_id": "req_123456789",
  "timestamp": "2024-01-15T10:30:00Z"
}
```

### Rollback Mechanism

For import operations, we'll implement a rollback mechanism:

```python
class RulesService:
    async def import_rule_set(
        self,
        rule_set: CapabilityRuleSetModel,
        partial_update: bool = True
    ) -> Dict[str, Any]:
        """Import rule set with rollback support"""
        # Create backup of current state
        backup = await self._create_backup()
        
        try:
            # Apply changes
            result = await self._apply_rule_set(rule_set, partial_update)
            
            # Validate after import
            validation_result = await self._validate_all_rules()
            if not validation_result['valid']:
                # Rollback on validation failure
                await self._restore_backup(backup)
                raise RuleImportError(f"Validation failed after import: {validation_result['errors']}")
            
            return result
        except Exception as e:
            # Rollback on any error
            await self._restore_backup(backup)
            raise RuleImportError(f"Import failed: {str(e)}")
    
    async def _create_backup(self) -> Dict[str, Any]:
        """Create backup of current rule state"""
        # Export current rules to in-memory structure
        return await self._export_to_dict()
    
    async def _restore_backup(self, backup: Dict[str, Any]):
        """Restore rules from backup"""
        # Clear current rules
        self.rule_manager.rule_sets.clear()
        
        # Restore from backup
        for domain, rule_set_data in backup.items():
            rule_set = CapabilityRuleSetModel(**rule_set_data)
            await self._apply_rule_set(rule_set, partial_update=False)
```

---

## Implementation Plan

### Progress Summary

**Phase 1: Foundation** ✅ **COMPLETED**

All Phase 1 tasks have been successfully completed:

1. ✅ **Enhanced Dataclass Validation**
   - Enhanced `CapabilityRule.__post_init__` with comprehensive validation
   - Enhanced `CapabilityRuleSet.__post_init__` with validation
   - Added `include_metadata` parameter to `to_dict()` methods
   - Improved error messages in `from_dict()` methods

2. ✅ **Moved Rule Files**
   - Created `src/config/rules/` directory
   - Copied existing YAML files to new location
   - Updated `CapabilityRuleManager` default path with backward compatibility

3. ✅ **Created Validation Service**
   - Implemented `ValidationService` at `src/core/matching/validation.py`
   - Added business rule validations (duplicate requirements, low confidence, etc.)
   - Created comprehensive test suite (11 tests, all passing)

**Test Coverage:**
- 40 total tests passing (29 dataclass validation tests + 11 validation service tests)
- All validation edge cases covered
- Business rule warnings implemented

**Files Created/Modified:**
- `src/core/matching/validation.py` (new)
- `src/core/matching/capability_rules.py` (enhanced)
- `src/config/rules/` (new directory with rule files)
- `tests/matching/test_validation_service.py` (new)
- `tests/matching/test_capability_rules_validation.py` (enhanced)

---

### Phase 1: Foundation (Week 1)

1. **Enhance Dataclass Validation** ✅ COMPLETED
   - [x] Enhance `CapabilityRule.__post_init__` with better validation
   - [x] Enhance `CapabilityRuleSet.__post_init__` with better validation
   - [x] Add `include_metadata` parameter to `to_dict()` methods
   - [x] Improve error messages in `from_dict()` methods

2. **Move Rule Files** ✅ COMPLETED
   - [x] Create `src/config/rules/` directory
   - [x] Move existing YAML files to new location
   - [x] Update `CapabilityRuleManager` default path

3. **Create Validation Service** ✅ COMPLETED
   - [x] Implement `ValidationService` using dataclass constructors
   - [x] Add business rule validations
   - [x] Create validation tests

### Phase 2: Core Services (Week 2) ✅ **COMPLETED**

4. **Create Rules Service** ✅ COMPLETED
   - [x] Implement `RulesService` with CRUD operations
   - [x] Use dataclass methods for all operations
   - [x] Add import/export functionality
   - [x] Implement rollback mechanism
   - [x] Create service tests

5. **Create Import/Export Service** ✅ COMPLETED
   - [x] Implement YAML/JSON parsing
   - [x] Use dataclass `from_dict()` and `to_dict()` methods
   - [x] Add comparison functionality
   - [x] Support partial updates
   - [x] Create import/export tests

**Phase 2 Summary:**
- Created `RulesService` at `src/core/matching/rules_service.py` with full CRUD operations
- Created `ImportExportService` at `src/core/matching/import_export_service.py` with import/export functionality
- Implemented rollback mechanism using backup/restore
- All tests passing (14 RulesService tests + 9 ImportExportService tests = 23 tests)
- Services use dataclass methods (`from_dict()`, `to_dict()`) for all data conversions

### Phase 3: API Layer (Week 3) ✅ **COMPLETED**

6. **Create API Models** ✅ COMPLETED
   - [x] Create request models in `src/core/api/models/rules/request.py` (Pydantic)
   - [x] Create response models in `src/core/api/models/rules/response.py` (Pydantic)
   - [x] Models will wrap dataclass data using `to_dict()` method
   - [x] Add model validation and examples

7. **Create API Routes** ✅ COMPLETED
   - [x] Implement all endpoint handlers
   - [x] Convert dataclass objects to dicts using `to_dict()` for responses
   - [x] Convert request dicts to dataclasses using `from_dict()` for processing
   - [x] Add error handling
   - [x] Integrate with Rules Service
   - [x] Create API integration tests

8. **Register Routes** ✅ COMPLETED
   - [x] Add router to main FastAPI app
   - [x] Test all endpoints with integration tests

**Phase 3 Summary:**
- Created API models at `src/core/api/models/rules/` (request.py and response.py)
- Created API routes at `src/core/api/routes/rules.py` with 10 endpoints
- Registered router in main FastAPI app
- All endpoints follow standardized patterns with error handling
- Fixed decorator compatibility issues (added Request parameter for Pydantic models)
- Fixed datetime serialization issues (using `model_dump(mode='json')`)
- Created comprehensive integration tests (15 tests, all passing)
- All endpoints tested and working against live API server on localhost:8001
- Fixed test cleanup to prevent unnecessary 404 errors in server logs
- All 10 endpoints verified: list, get, create, update, delete, import, export, validate, compare, reset

### Phase 4: CLI Layer (Week 4) ✅ **COMPLETED**

9. **Create CLI Commands** ✅ COMPLETED
   - [x] Add rules subcommand group to match commands
   - [x] Implement all CLI commands (list, get, create, update, delete, import, export, validate, compare, reset)
   - [x] Use API client for all operations (calls API endpoints)
   - [x] Add interactive mode for create/update commands
   - [x] Create CLI integration tests (15 tests, all passing)

10. **Integration Testing** ✅ **COMPLETED**
    - [x] End-to-end API tests (15 tests, all passing)
    - [x] End-to-end CLI tests (15 tests, 14 passing, 1 skipped)
    - [x] Cross-layer integration tests (API + Services + CLI)
    - [x] Test dataclass validation edge cases (covered in Phase 1 tests)

**Phase 4 Summary:**
- Added `rules` subcommand group to `match_group` in `src/cli/match.py`
- Implemented all 10 CLI commands mirroring API endpoints
- Commands use `CLIContext.api_client` to call API endpoints
- Interactive mode implemented for `create` and `update` commands using `click.prompt()`
- All commands support `--json` and `--table` output formats
- File reading supports both YAML and JSON formats
- Created comprehensive CLI integration tests (15 tests, 14 passing, 1 skipped)
- Fixed JSON output format issues (success messages only shown in non-JSON mode)
- Fixed export command to properly use query parameters for format specification
- All tests verified against live API server

### Phase 5: Documentation & Polish (Week 5) ✅ **COMPLETED**

12. **Documentation Updates** ✅ COMPLETED
    - [x] Update `docs/api/routes.md`:
      - [x] Add Rules Management Routes section
      - [x] Document all 10 rules endpoints
      - [x] Add request/response examples
      - [x] Update implementation status
      - [x] Update route count (43 → 53)
    - [x] Update `docs/CLI/index.md`:
      - [x] Add Rules Commands subsection under Match Commands
      - [x] Document all 10 rules commands
      - [x] Add interactive mode documentation
      - [x] Add examples and workflows
      - [x] Update command count (43 → 53)
      - [x] Add best practices and troubleshooting
    - [x] Update `docs/matching/heuristic-matching.md`:
      - [x] Update file structure to show new location (`src/config/rules/`)
      - [x] Add Rules Management section
      - [x] Document API and CLI access methods
      - [x] Add import/export workflows
      - [x] Update configuration management section
      - [x] Add migration notes
    - [x] Review and verify all documentation:
      - [x] Test all code examples
      - [x] Verify all file paths and locations
      - [x] Check cross-references
      - [x] Ensure consistency across documents

**Phase 5 Summary:**
- Updated API documentation with complete Rules Management Routes section (10 endpoints)
- Updated CLI documentation with complete Rules Commands section (10 commands)
- Updated Heuristic-Matching documentation with Rules Management section and migration notes
- Updated route/command counts across all documentation (43 → 53)
- Added best practices and troubleshooting sections for rules management
- All documentation cross-references verified and consistent

13. **Final Testing & Bug Fixes** ✅ **COMPLETED**
    - [x] Comprehensive testing (all phases tested)
    - [x] Integration testing (API and CLI)
    - [x] Bug fixes and refinements (JSON output format, export command)
    - [x] Validate error messages are user-friendly
    - [x] Documentation accuracy verification

---

## Documentation Updates

All documentation updates should be completed at the end of the implementation phase to account for any unforeseen changes made during development. The following documentation files must be updated to reflect the new rules management system.

### API Documentation (`docs/api/routes.md`)

#### New Section: Rules Management Routes

Add a new section documenting all rules management API endpoints under the "Matching Routes" section or as a separate "Rules Routes" section:

**Required Updates:**
1. **Add Rules Routes Section** with the following endpoints:
   - `GET /v1/api/match/rules` - List all rules
   - `GET /v1/api/match/rules/{domain}/{rule_id}` - Get specific rule
   - `POST /v1/api/match/rules` - Create new rule
   - `PUT /v1/api/match/rules/{domain}/{rule_id}` - Update existing rule
   - `DELETE /v1/api/match/rules/{domain}/{rule_id}` - Delete rule
   - `POST /v1/api/match/rules/import` - Import rules from file
   - `POST /v1/api/match/rules/export` - Export rules to file
   - `POST /v1/api/match/rules/validate` - Validate rule file
   - `POST /v1/api/match/rules/compare` - Compare rules (dry-run)
   - `POST /v1/api/match/rules/reset` - Reset all rules

2. **For Each Endpoint, Document:**
   - Request format (with examples)
   - Response format (with examples)
   - Query parameters
   - Request body structure
   - Error responses
   - Status codes

3. **Add Examples:**
   - Import rules from YAML
   - Export rules to JSON
   - Validate rule file
   - Compare rules before import
   - Create/update/delete operations

4. **Update Implementation Status:**
   - Mark all rules endpoints as "Fully Implemented" in the implementation status section

5. **Update Route Count:**
   - Update the total route count in the introduction to include the new rules endpoints

#### Update Existing Sections

1. **Matching Routes Section:**
   - Add note about rules management being part of the matching system
   - Reference the new rules endpoints section

2. **Error Handling Section:**
   - Add examples of rules-specific error responses (validation errors, rule not found, etc.)

### CLI Documentation (`docs/CLI/index.md`)

#### New Section: Rules Commands

Add a new subsection under "Match Commands" for rules management:

**Required Updates:**
1. **Add Rules Command Group** (`ome match rules`) with the following commands:
   - `ome match rules list` - List all rules
   - `ome match rules get DOMAIN RULE_ID` - Get specific rule
   - `ome match rules create` - Create new rule (with interactive mode)
   - `ome match rules update DOMAIN RULE_ID` - Update existing rule (with interactive mode)
   - `ome match rules delete DOMAIN RULE_ID` - Delete rule
   - `ome match rules import FILE` - Import rules from file
   - `ome match rules export OUTPUT_FILE` - Export rules to file
   - `ome match rules validate FILE` - Validate rule file
   - `ome match rules compare FILE` - Compare rules (dry-run)
   - `ome match rules reset` - Reset all rules

2. **For Each Command, Document:**
   - Command syntax
   - Arguments and options
   - Examples with different use cases
   - Output format
   - Interactive mode usage (for create/update)

3. **Add Interactive Mode Documentation:**
   - Explain how interactive mode works
   - Show example interactive session
   - Document field prompts and validation

4. **Add Examples Section:**
   - Export rules for backup
   - Import updated rules
   - Validate rules before import
   - Compare rules to see changes
   - Create new rule interactively

5. **Update Command Count:**
   - Update the total command count in the overview to include new rules commands

#### Update Existing Sections

1. **Match Commands Section:**
   - Add note about rules management commands
   - Reference the new rules subsection

2. **Best Practices Section:**
   - Add best practices for rules management:
     - Always validate before importing
     - Use compare to preview changes
     - Export rules as backup before major changes
     - Use interactive mode for complex rule creation

3. **Troubleshooting Section:**
   - Add common issues with rules management:
     - Validation errors
     - Import failures
     - Rule conflicts

### Heuristic Matching Documentation (`docs/matching/heuristic-matching.md`)

#### Update Existing Sections

**Required Updates:**

1. **Overview Section:**
   - Add note about rules being user-configurable
   - Mention rules location (`src/config/rules/`)
   - Reference API and CLI for rules management

2. **Rule Configuration Section:**
   - Update file structure to show new location (`src/config/rules/`)
   - Add note about rules being accessible to users
   - Update examples to reflect current rule structure

3. **Add New Section: Rules Management**

   **Title:** "Rules Management"

   **Content should include:**
   - Overview of rules management capabilities
   - Rules file location and structure
   - How to access rules via API
   - How to access rules via CLI
   - Import/export workflows
   - Validation process
   - Best practices for rule management

   **Subsections:**
   - **Accessing Rules**: How users can view and manage rules
   - **Modifying Rules**: Step-by-step guide for updating rules
   - **Import/Export**: How to backup and restore rules
   - **Validation**: How to validate rules before importing
   - **Troubleshooting**: Common issues and solutions

4. **Update Usage Examples Section:**
   - Add examples showing rules management via API
   - Add examples showing rules management via CLI
   - Show workflow: export → modify → validate → import

5. **Update Configuration Management Section:**
   - Update "Adding New Rules" to reference API/CLI methods
   - Add "Managing Rules via API" subsection
   - Add "Managing Rules via CLI" subsection
   - Update "Adding New Domains" to mention rules management

6. **Add Migration Notes:**
   - Document the move from `src/core/matching/rules/` to `src/config/rules/`
   - Note any breaking changes (if any)
   - Provide migration path for existing users

### Documentation Standards

All documentation updates should follow these standards:

1. **Consistency:**
   - Use consistent terminology across all documentation
   - Match existing documentation style and format
   - Follow existing code example patterns

2. **Completeness:**
   - Include all endpoints/commands
   - Provide request/response examples
   - Document all options and parameters
   - Include error handling examples

3. **Clarity:**
   - Use clear, concise language
   - Provide step-by-step workflows
   - Include practical examples
   - Add troubleshooting guidance

4. **Accuracy:**
   - Verify all examples work with actual implementation
   - Test all code snippets
   - Ensure all paths and file locations are correct
   - Update version numbers and dates

### Documentation Review Checklist

Before finalizing documentation:

- [ ] All API endpoints documented with examples
- [ ] All CLI commands documented with examples
- [ ] File locations updated to reflect new structure
- [ ] All code examples tested and verified
- [ ] Error handling documented
- [ ] Migration notes included (if applicable)
- [ ] Cross-references between documents updated
- [ ] Implementation status updated
- [ ] Route/command counts updated
- [ ] Best practices and troubleshooting sections updated

## Future Enhancements

### Versioning & Audit Trail

**Status**: Future Project

**Description**: Implement versioning and audit trail for rule changes to track:
- Who made changes
- When changes were made
- What changed (diff)
- Ability to revert to previous versions

**Implementation Notes**:
- Store rule history in database or versioned files
- Add `version` field to rules
- Implement diff/compare functionality
- Add API endpoints for version management

### Rule Profiles & Sets

**Status**: Future Project

**Description**: Support multiple rule sets/profiles that can be activated/deactivated:
- Production rules
- Development rules
- Regional/localized rules
- Custom user profiles

**Implementation Notes**:
- Add rule set registry
- Implement activation/deactivation
- Support rule set inheritance
- Add profile management API/CLI

### Localization Support

**Status**: Future Project

**Description**: Support multiple languages and regional variations:
- Language-specific rule sets
- Regional terminology variations
- Automatic language detection
- Translation management

**Implementation Notes**:
- Add locale field to rules
- Implement locale-based rule loading
- Create translation management system
- Add localization API endpoints

### Advanced Validation

**Status**: Future Project

**Description**: Enhanced validation capabilities:
- Conflict detection between rules
- Duplicate rule detection
- Rule dependency validation
- Performance impact analysis

**Implementation Notes**:
- Implement rule conflict detection algorithm
- Add dependency graph analysis
- Create validation rules engine
- Add performance profiling

### Rule Analytics

**Status**: Future Project

**Description**: Analytics and insights for rule usage:
- Rule usage statistics
- Match success rates per rule
- Rule effectiveness metrics
- Recommendations for rule improvements

**Implementation Notes**:
- Add rule usage tracking
- Implement analytics collection
- Create reporting dashboard
- Add recommendation engine

---

## Testing Strategy

### Unit Tests

- Pydantic model validation
- Service layer business logic
- Import/export functionality
- Validation service

### Integration Tests

- API endpoint integration
- CLI command integration
- File system operations
- Rollback mechanism

### End-to-End Tests

- Complete import/export workflows
- API + CLI interoperability
- Error handling scenarios
- Performance under load

---

## Migration Notes

### Breaking Changes

1. **File Location**: Rule files moved from `src/core/matching/rules/` to `src/config/rules/`
2. **API**: New endpoints under `/v1/api/match/rules`
3. **Enhanced Validation**: Stricter validation in dataclass `__post_init__` methods (may catch previously undetected errors)

### Backward Compatibility

- Existing `CapabilityRule` and `CapabilityRuleSet` dataclasses remain the core data model
- All existing code using dataclasses continues to work without changes
- Enhanced validation provides better error messages but maintains same validation logic
- `to_dict()` and `from_dict()` methods remain unchanged (with optional `include_metadata` parameter)
- No adapter layer needed - dataclasses are the single source of truth

---

## Conclusion

This specification provides a comprehensive plan for implementing a production-ready rules management system. The phased approach ensures incremental delivery with testing at each stage. The system is designed to be extensible, with clear paths for future enhancements while maintaining backward compatibility with existing code.

