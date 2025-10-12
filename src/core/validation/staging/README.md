# Legacy Validation Infrastructure (Staged)

This directory contains the existing validation infrastructure that has been temporarily moved to avoid conflicts during the implementation of the new domain-integrated validation framework.

## Files Staged

- `manufacturing_okh_validator_legacy.py` - Original OKH validator for manufacturing domain
- `cooking_validators_legacy.py` - Original cooking domain validators

## Migration Plan

1. **Phase 1**: New validation framework implemented alongside staged files
2. **Phase 2**: Existing validators enhanced to work with new framework
3. **Phase 3**: Staged files integrated back into new structure
4. **Phase 4**: Legacy files removed after successful migration

## Backward Compatibility

- All existing validation endpoints continue to work during migration
- New framework provides enhanced functionality while maintaining existing interfaces
- Gradual migration ensures no breaking changes

## Original File Locations

- `src/core/domains/manufacturing/okh_validator.py` → `manufacturing_okh_validator_legacy.py`
- `src/core/domains/cooking/validators.py` → `cooking_validators_legacy.py`
- `src/core/services/validation_service.py` → Deleted (was empty placeholder)

## Integration Points

The staged files will be referenced during implementation to:
- Understand existing validation logic
- Ensure compatibility with current validation patterns
- Preserve domain-specific validation rules
- Maintain existing validation interfaces

## Cleanup Timeline

These files will be removed after:
- ✅ All tests are passing consistently
- ✅ The changes they were testing are working correctly
- ✅ The user explicitly agrees to cleanup
- ✅ The functionality is properly covered by existing or permanent tests

## Notes

- Files are preserved for reference during development
- Original validation logic will be enhanced, not replaced
- Domain-specific validation patterns will be maintained
- Integration with existing domain system will be preserved
