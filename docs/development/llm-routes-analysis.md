# LLM Routes Analysis

## Overview

This document analyzes the 7 LLM routes documented in `docs/api/routes.md` and `docs/llm/api.md` to determine which should be implemented vs. removed from documentation.

## Current State

- **LLM Service**: Fully implemented (`src/core/llm/service.py`)
- **LLM Integration**: LLM is integrated into other endpoints via `@llm_endpoint` decorator
- **CLI Commands**: Full LLM CLI support exists (`src/cli/llm.py`)
- **No Dedicated Routes**: No `src/core/api/routes/llm.py` file exists
- **Metrics**: LLM metrics are included in `/v1/api/utility/metrics`

## Route-by-Route Analysis

### 1. `GET /v1/api/llm/health`

**Purpose**: Check LLM service health and provider status

**Current Implementation**:
- `LLMService.get_provider_status()` method exists
- `LLMService.get_service_metrics()` method exists
- General `/health` endpoint exists but doesn't include LLM-specific details

**Analysis**:
- ✅ **USEFUL**: Provides LLM-specific health information separate from general system health
- ✅ **UNIQUE**: Not redundant with existing endpoints
- ✅ **VALUE**: Useful for monitoring LLM service availability and provider status

**Recommendation**: **IMPLEMENT** - This provides valuable LLM-specific health information

---

### 2. `POST /v1/api/llm/generate`

**Purpose**: Generic content generation using LLM service

**Current Implementation**:
- `LLMService.generate()` method exists
- CLI command `ome llm generate` exists
- This is a low-level LLM operation

**Analysis**:
- ⚠️ **QUESTIONABLE**: Most use cases are covered by domain-specific endpoints
- ⚠️ **LOW-LEVEL**: Direct LLM access may not align with OME's domain-focused architecture
- ⚠️ **REDUNDANT**: CLI already provides this functionality

**Recommendation**: **REMOVE FROM DOCS** - Generic LLM generation is not core to OME's purpose. Users can use CLI or integrate LLM service directly in their code.

---

### 3. `POST /v1/api/llm/generate-okh`

**Purpose**: Generate OKH manifest using LLM

**Current Implementation**:
- ✅ `POST /v1/api/okh/generate-from-url` already exists and does this
- ✅ CLI command `ome llm generate-okh` exists
- ✅ OKH generation endpoint already supports LLM via service integration

**Analysis**:
- ❌ **REDUNDANT**: Functionality already exists in `/v1/api/okh/generate-from-url`
- ❌ **DUPLICATE**: Creates confusion about which endpoint to use

**Recommendation**: **REMOVE FROM DOCS** - This is redundant with existing OKH endpoint

---

### 4. `POST /v1/api/llm/match-facilities`

**Purpose**: Use LLM to enhance facility matching

**Current Implementation**:
- ✅ `POST /v1/api/match` already exists with LLM support via `@llm_endpoint` decorator
- ✅ Matching endpoint already supports LLM enhancement
- ✅ CLI matching commands support LLM

**Analysis**:
- ❌ **REDUNDANT**: Matching endpoint already has LLM integration
- ❌ **DUPLICATE**: Creates confusion about which endpoint to use

**Recommendation**: **REMOVE FROM DOCS** - This is redundant with existing match endpoint

---

### 5. `GET /v1/api/llm/providers`

**Purpose**: List all configured LLM providers

**Current Implementation**:
- ✅ `LLMService.get_available_providers()` method exists
- ✅ `LLMService.get_provider_status()` method exists
- ❌ No API endpoint exists

**Analysis**:
- ✅ **USEFUL**: Helps users discover available providers
- ✅ **UNIQUE**: Not redundant with existing endpoints
- ✅ **VALUE**: Useful for provider discovery and status checking

**Recommendation**: **IMPLEMENT** - This provides valuable provider discovery functionality

---

### 6. `GET /v1/api/llm/metrics`

**Purpose**: Retrieve LLM service usage metrics and statistics

**Current Implementation**:
- ✅ `GET /v1/api/utility/metrics` already includes LLM metrics
- ✅ `MetricsTracker` includes LLM metrics in summary
- ✅ CLI command `ome utility metrics` shows LLM metrics

**Analysis**:
- ❌ **REDUNDANT**: LLM metrics are already included in utility metrics endpoint
- ❌ **DUPLICATE**: Creates confusion about which endpoint to use

**Recommendation**: **REMOVE FROM DOCS** - LLM metrics are already available via `/v1/api/utility/metrics`

---

### 7. `POST /v1/api/llm/provider`

**Purpose**: Change the active LLM provider

**Current Implementation**:
- ✅ `LLMService.set_active_provider()` method exists
- ⚠️ Provider selection is typically done via config/env vars, not runtime
- ⚠️ Provider selection is usually static configuration

**Analysis**:
- ⚠️ **QUESTIONABLE**: Provider selection is typically static configuration
- ⚠️ **RUNTIME CHANGE**: Changing providers at runtime may not be a common use case
- ⚠️ **COMPLEXITY**: Adds state management complexity

**Recommendation**: **REMOVE FROM DOCS** - Provider selection should be done via configuration, not runtime API calls. This adds unnecessary complexity.

---

## Summary

### Routes to IMPLEMENT (2):
1. ✅ `GET /v1/api/llm/health` - LLM-specific health check
2. ✅ `GET /v1/api/llm/providers` - Provider discovery and status

### Routes to REMOVE FROM DOCS (5):
1. ❌ `POST /v1/api/llm/generate` - Redundant with CLI, not core to OME
2. ❌ `POST /v1/api/llm/generate-okh` - Redundant with `/v1/api/okh/generate-from-url`
3. ❌ `POST /v1/api/llm/match-facilities` - Redundant with `/v1/api/match` (has LLM support)
4. ❌ `GET /v1/api/llm/metrics` - Redundant with `/v1/api/utility/metrics`
5. ❌ `POST /v1/api/llm/provider` - Provider selection should be via config, not runtime API

## Rationale

**Why keep health and providers?**
- These are **discovery/monitoring** endpoints that provide unique value
- They help users understand LLM service availability and configuration
- They don't duplicate existing functionality

**Why remove the others?**
- **Generate endpoints**: Redundant with domain-specific endpoints or CLI
- **Match endpoint**: Already has LLM support via decorator
- **Metrics endpoint**: Already included in utility metrics
- **Provider set endpoint**: Configuration should be static, not runtime

## Next Steps

1. Remove 5 redundant routes from documentation
2. Implement 2 useful routes (`/health` and `/providers`)
3. Update code review report to reflect decisions

