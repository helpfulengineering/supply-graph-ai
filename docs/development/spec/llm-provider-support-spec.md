# LLM & Provider Support Implementation Specification

## Overview

This specification defines the implementation plan for completing LLM service status checking and documenting provider support. These are minor improvements that enhance reliability and clarity.

## Current State Analysis

### Issue 1: Provider Support Documentation

**Location**: `src/core/llm/service.py:128`

**Current Implementation:**
```python
# Provider registry
self._provider_classes: Dict[LLMProviderType, Type[BaseLLMProvider]] = {
    LLMProviderType.ANTHROPIC: AnthropicProvider,
    LLMProviderType.OPENAI: OpenAIProvider,
    LLMProviderType.LOCAL: OllamaProvider,
    # TODO: Add other providers as they're implemented
    # LLMProviderType.GOOGLE: GoogleProvider,
    # LLMProviderType.AZURE_OPENAI: AzureOpenAIProvider,
}
```

**Problems:**
- TODO comment indicates future providers
- Commented-out provider types suggest planned support
- No documentation of current vs. planned provider support
- Unclear which providers are actively supported vs. planned

**Context:**
- Currently supports: Anthropic, OpenAI, Local (Ollama)
- Planned but not implemented: Google, Azure OpenAI
- Provider types exist in enum but implementations don't exist

**Severity**: Low - Future enhancement, documentation issue

### Issue 2: LLM Service Status Check Placeholder

**Location**: `src/core/generation/services/file_categorization_service.py:180`

**Current Implementation:**
```python
def is_llm_available(self) -> bool:
    """
    Check if LLM service is available.
    
    Returns:
        True if LLM service is available and active, False otherwise
    """
    if self.llm_service is None:
        return False
    
    # Check if LLM service is initialized and active
    # TODO: Implement proper LLM service status check
    # For now, just check if service exists
    return True
```

**Problems:**
- Only checks if service exists, not if it's actually available
- Doesn't check if service is initialized
- Doesn't check if any providers are available
- Doesn't check if service is healthy
- May return True even if LLM is disabled or no providers are configured

**Context:**
- Used to determine if LLM categorization should be attempted
- LLMService has `get_status()`, `is_healthy()`, and `get_available_providers()` methods
- Providers have `health_check()` methods
- Should check actual service status, not just existence

**Severity**: Medium - Missing validation, could lead to unnecessary LLM attempts

## Requirements

### Functional Requirements

1. **LLM Service Status Check**
   - Check if LLM service is initialized
   - Check if LLM service is enabled
   - Check if LLM service is healthy
   - Check if at least one provider is available
   - Return accurate availability status

2. **Provider Support Documentation**
   - Document currently supported providers
   - Document planned/future providers
   - Clear distinction between implemented and planned
   - Update TODO comment with better documentation

### Non-Functional Requirements

1. **Performance**
   - Status check should be fast (<100ms)
   - Should not make actual API calls for health check
   - Cache status if needed

2. **Reliability**
   - Accurate status reporting
   - Graceful handling of service unavailability
   - No false positives (saying LLM is available when it's not)

3. **Maintainability**
   - Clear documentation
   - Easy to update when new providers are added

## Design Decisions

### Status Check Strategy

**Comprehensive Check:**
1. Check if service exists (not None)
2. Check if service is initialized (using `get_status()`)
3. Check if service is healthy (using `is_healthy()`)
4. Check if at least one provider is available (using `get_available_providers()`)

**Performance Consideration:**
- Don't call `health_check()` on providers (could be slow)
- Use cached provider availability status
- Check service status, not individual provider health

### Provider Documentation Strategy

**Update TODO Comment:**
- Replace TODO with clear documentation comment
- List currently supported providers
- List planned providers with status
- Reference documentation for adding new providers

**Documentation Location:**
- Update comment in code
- Consider adding to module docstring
- Consider adding to README or LLM documentation

## Implementation Specification

### 1. Update LLM Service Status Check

**File: `src/core/generation/services/file_categorization_service.py`**

**Update `is_llm_available` method:**

```python
def is_llm_available(self) -> bool:
    """
    Check if LLM service is available and ready to use.
    
    This method performs a comprehensive check to determine if LLM
    categorization can be used:
    - Service must exist and be initialized
    - Service must be enabled and healthy
    - At least one provider must be available
    
    Returns:
        True if LLM service is available and active, False otherwise
    """
    if self.llm_service is None:
        return False
    
    try:
        # Check if service is initialized and healthy
        # LLMService extends BaseService which has get_status() and is_healthy()
        if not hasattr(self.llm_service, 'get_status'):
            # Service doesn't have status methods, assume not available
            return False
        
        # Check service status
        service_status = self.llm_service.get_status()
        if service_status != ServiceStatus.ACTIVE:
            # Service is not active (not initialized, error, etc.)
            return False
        
        # Check if service is healthy
        if not self.llm_service.is_healthy():
            # Service is not healthy
            return False
        
        # Check if LLM is enabled in configuration
        # LLMService has config that indicates if LLM is enabled
        if hasattr(self.llm_service, 'config'):
            config = self.llm_service.config
            if hasattr(config, 'enabled') and not config.enabled:
                # LLM is disabled in configuration
                return False
        
        # Check if at least one provider is available
        # Use async method if available, otherwise check providers dict
        if hasattr(self.llm_service, 'get_available_providers'):
            # This is async, but we're in sync method
            # For sync check, we can check if _providers dict has entries
            if hasattr(self.llm_service, '_providers'):
                available_providers = self.llm_service._providers
                if not available_providers or len(available_providers) == 0:
                    # No providers available
                    return False
        else:
            # Can't check providers, assume not available
            return False
        
        # All checks passed
        return True
        
    except Exception as e:
        # If any check fails, assume LLM is not available
        self.logger.warning(
            f"Error checking LLM service availability: {e}",
            exc_info=True
        )
        return False
```

**Alternative: Async Version (if method can be async):**

If the method can be made async, a better implementation would be:

```python
async def is_llm_available(self) -> bool:
    """
    Check if LLM service is available and ready to use.
    
    This method performs a comprehensive check to determine if LLM
    categorization can be used:
    - Service must exist and be initialized
    - Service must be enabled and healthy
    - At least one provider must be available
    
    Returns:
        True if LLM service is available and active, False otherwise
    """
    if self.llm_service is None:
        return False
    
    try:
        # Check if service is initialized and healthy
        if not hasattr(self.llm_service, 'get_status'):
            return False
        
        service_status = self.llm_service.get_status()
        if service_status != ServiceStatus.ACTIVE:
            return False
        
        if not self.llm_service.is_healthy():
            return False
        
        # Check if LLM is enabled in configuration
        if hasattr(self.llm_service, 'config'):
            config = self.llm_service.config
            if hasattr(config, 'enabled') and not config.enabled:
                return False
        
        # Check if at least one provider is available (async)
        if hasattr(self.llm_service, 'get_available_providers'):
            available_providers = await self.llm_service.get_available_providers()
            if not available_providers or len(available_providers) == 0:
                return False
        else:
            # Fallback: check _providers dict
            if hasattr(self.llm_service, '_providers'):
                providers = self.llm_service._providers
                if not providers or len(providers) == 0:
                    return False
            else:
                return False
        
        return True
        
    except Exception as e:
        self.logger.warning(
            f"Error checking LLM service availability: {e}",
            exc_info=True
        )
        return False
```

**Note:** Check if `is_llm_available` is called from async or sync context. If it's only called from async contexts, use the async version.

### 2. Update Provider Support Documentation

**File: `src/core/llm/service.py`**

**Update provider registry with documentation:**

```python
# Provider registry
# Currently supported providers:
# - ANTHROPIC: Anthropic Claude models (via AnthropicProvider)
# - OPENAI: OpenAI GPT models (via OpenAIProvider)
# - LOCAL: Local models via Ollama (via OllamaProvider)
#
# Planned providers (not yet implemented):
# - GOOGLE: Google Gemini models (GoogleProvider - TODO)
# - AZURE_OPENAI: Azure OpenAI service (AzureOpenAIProvider - TODO)
#
# To add a new provider:
# 1. Create provider class extending BaseLLMProvider
# 2. Implement required abstract methods
# 3. Add provider type to LLMProviderType enum
# 4. Register provider class in _provider_classes dict below
# 5. Update LLMConfig to support provider configuration
self._provider_classes: Dict[LLMProviderType, Type[BaseLLMProvider]] = {
    LLMProviderType.ANTHROPIC: AnthropicProvider,
    LLMProviderType.OPENAI: OpenAIProvider,
    LLMProviderType.LOCAL: OllamaProvider,
    # Planned providers (uncomment when implemented):
    # LLMProviderType.GOOGLE: GoogleProvider,
    # LLMProviderType.AZURE_OPENAI: AzureOpenAIProvider,
}
```

**Update module docstring:**

```python
"""
LLM Service for the Open Matching Engine (OME).

This service provides centralized management of LLM providers, including:
- Provider selection and routing
- Request handling and load balancing
- Fallback mechanisms and error recovery
- Cost tracking and usage analytics
- Integration with existing service patterns

Supported Providers:
- Anthropic: Claude models (claude-3-5-sonnet, claude-3-opus, etc.)
- OpenAI: GPT models (gpt-4, gpt-3.5-turbo, etc.)
- Local: Open-source models via Ollama (llama2, mistral, etc.)

Planned Providers:
- Google: Gemini models (not yet implemented)
- Azure OpenAI: Azure-hosted OpenAI models (not yet implemented)

The LLM service follows the BaseService pattern and provides a unified
interface for all LLM operations across the system.
"""
```

### 3. Add Helper Method to LLMService (Optional Enhancement)

**File: `src/core/llm/service.py`**

**Add method to check if service is ready:**

```python
def is_ready(self) -> bool:
    """
    Check if LLM service is ready to handle requests.
    
    Returns:
        True if service is initialized, healthy, and has at least one provider
    """
    if self.status != ServiceStatus.ACTIVE:
        return False
    
    if not self.is_healthy():
        return False
    
    # Check if at least one provider is available
    if not self._providers or len(self._providers) == 0:
        return False
    
    return True

async def is_ready_async(self) -> bool:
    """
    Async version of is_ready that also checks provider availability.
    
    Returns:
        True if service is ready and has available providers
    """
    if not self.is_ready():
        return False
    
    # Check if at least one provider is actually available
    available_providers = await self.get_available_providers()
    return len(available_providers) > 0
```

**Then update FileCategorizationService to use this:**

```python
def is_llm_available(self) -> bool:
    """
    Check if LLM service is available and ready to use.
    
    Returns:
        True if LLM service is available and active, False otherwise
    """
    if self.llm_service is None:
        return False
    
    try:
        # Use LLMService.is_ready() if available
        if hasattr(self.llm_service, 'is_ready'):
            return self.llm_service.is_ready()
        
        # Fallback to manual checks
        if not hasattr(self.llm_service, 'get_status'):
            return False
        
        service_status = self.llm_service.get_status()
        if service_status != ServiceStatus.ACTIVE:
            return False
        
        if not self.llm_service.is_healthy():
            return False
        
        if hasattr(self.llm_service, '_providers'):
            providers = self.llm_service._providers
            if not providers or len(providers) == 0:
                return False
        
        return True
        
    except Exception as e:
        self.logger.warning(
            f"Error checking LLM service availability: {e}",
            exc_info=True
        )
        return False
```

### 4. Update Documentation

**File: `docs/llm/llm-service.md` or similar**

**Add provider support section:**

```markdown
## Supported Providers

The OME LLM service currently supports the following providers:

### Anthropic
- **Provider Type**: `anthropic`
- **Models**: Claude 3.5 Sonnet, Claude 3 Opus, Claude 3 Haiku
- **Configuration**: Set `ANTHROPIC_API_KEY` environment variable
- **Status**: ✅ Fully supported

### OpenAI
- **Provider Type**: `openai`
- **Models**: GPT-4, GPT-3.5-turbo, GPT-4-turbo
- **Configuration**: Set `OPENAI_API_KEY` environment variable
- **Status**: ✅ Fully supported

### Local (Ollama)
- **Provider Type**: `local`
- **Models**: Any model supported by Ollama (llama2, mistral, etc.)
- **Configuration**: Requires Ollama running locally on port 11434
- **Status**: ✅ Fully supported

## Planned Providers

The following providers are planned but not yet implemented:

### Google
- **Provider Type**: `google`
- **Models**: Gemini Pro, Gemini Ultra
- **Status**: 🚧 Planned

### Azure OpenAI
- **Provider Type**: `azure_openai`
- **Models**: Azure-hosted OpenAI models
- **Status**: 🚧 Planned
```

## Integration Points

### 1. File Categorization Service

- Uses `is_llm_available()` to decide if LLM categorization should be attempted
- Accurate status prevents unnecessary LLM calls
- Improves error handling and user experience

### 2. LLM Service

- Provides status and health checking methods
- Tracks provider availability
- Manages service lifecycle

### 3. Base Service

- LLMService extends BaseService
- Inherits `get_status()`, `is_healthy()` methods
- Follows service pattern

## Testing Considerations

### Unit Tests

1. **Status Check Tests:**
   - Test when service is None
   - Test when service is not initialized
   - Test when service is not healthy
   - Test when no providers available
   - Test when LLM is disabled in config
   - Test when service is ready

2. **Provider Documentation Tests:**
   - Verify supported providers are documented
   - Verify planned providers are clearly marked

### Integration Tests

1. **End-to-End LLM Availability:**
   - Test LLM categorization with available service
   - Test LLM categorization with unavailable service
   - Test fallback to Layer 1 when LLM unavailable

## Migration Plan

### Phase 1: Implementation (Current)
- Update `is_llm_available()` method
- Update provider documentation
- Add helper methods if needed

### Phase 2: Enhancement (Future)
- Add provider health checking
- Add provider availability caching
- Add provider status monitoring

## Success Criteria

1. ✅ LLM service status check is comprehensive
2. ✅ Provider support is clearly documented
3. ✅ TODO comments are resolved or improved
4. ✅ Status check accurately reflects LLM availability
5. ✅ No false positives (saying LLM available when it's not)
6. ✅ Tests pass

## Open Questions / Future Enhancements

1. **Provider Health Checking:**
   - Should we check individual provider health?
   - Could be slow if checking all providers
   - May want to cache health status

2. **Provider Availability Caching:**
   - Cache provider availability status
   - Refresh periodically
   - Invalidate on configuration changes

3. **Provider Status Monitoring:**
   - Track provider availability over time
   - Alert on provider failures
   - Automatic failover

4. **Adding New Providers:**
   - Document process for adding providers
   - Create provider template/boilerplate
   - Add provider tests

## Dependencies

### No New Dependencies

- Uses existing LLMService methods
- Uses existing BaseService methods
- No external libraries required

## Implementation Order

1. Update `is_llm_available()` method in FileCategorizationService
2. Update provider documentation in LLMService
3. Add `is_ready()` helper method to LLMService (optional)
4. Update module docstrings
5. Update external documentation
6. Write tests
7. Verify integration

## Notes

### Async vs Sync

- `is_llm_available()` is currently a sync method
- `get_available_providers()` is async
- For sync version, check `_providers` dict directly
- For async version, can call `get_available_providers()`
- Check call sites to determine which is appropriate

### Service Status

- `ServiceStatus.ACTIVE` means service is initialized and running
- `is_healthy()` checks if service is functioning correctly
- Both should be checked for comprehensive status

### Provider Availability

- Providers may be registered but not available (no API key, not connected)
- `get_available_providers()` returns providers that are actually usable
- `_providers` dict contains all initialized providers
- Check availability, not just initialization

