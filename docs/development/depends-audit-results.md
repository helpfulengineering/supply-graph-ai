# FastAPI `Depends()` Audit Results

## Summary

Audited all 7 instances of `= Depends()` in `src/core/api/routes/` to verify they are safe.

**Result: ✅ All instances are SAFE**

All instances use Pydantic models that FastAPI correctly infers as query parameters. None use service classes or other types that could cause body parameter inference issues.

## Detailed Review

### 1. `PaginationParams = Depends()` (5 instances)

**Locations:**
- `src/core/api/routes/supply_tree.py:394` - `list_supply_trees()`
- `src/core/api/routes/okw.py:490` - `list_okw()`
- `src/core/api/routes/match.py:631` - `list_domains()`
- `src/core/api/routes/package.py:279` - `list_packages()`
- `src/core/api/routes/okh.py:320` - `list_okh()`

**Model Definition:**
```python
class PaginationParams(BaseModel):
    page: int = Field(1, ge=1)
    page_size: int = Field(20, ge=1, le=100)
    sort_by: Optional[str] = None
    sort_order: Optional[str] = Field("asc", pattern="^(asc|desc)$")
```

**Analysis:**
- ✅ All are GET endpoints (no body parameters)
- ✅ `PaginationParams` is a Pydantic `BaseModel`
- ✅ FastAPI correctly infers these as query parameters
- ✅ No ambiguity with body parameters (GET requests don't have bodies)
- ✅ All endpoints use `@paginated_response` decorator which expects this pattern

**Verdict: ✅ SAFE**

### 2. `DomainFilterRequest = Depends()` (1 instance)

**Location:**
- `src/core/api/routes/utility.py:77` - `get_domains()`

**Model Definition:**
```python
class DomainFilterRequest(BaseAPIRequest, LLMRequestMixin):
    name: Optional[str] = None
    active_only: bool = True
    # Inherits from BaseAPIRequest and LLMRequestMixin
```

**Analysis:**
- ✅ GET endpoint (no body parameters)
- ✅ `DomainFilterRequest` is a Pydantic `BaseModel` (inherits from `BaseAPIRequest`)
- ✅ FastAPI correctly infers these as query parameters
- ✅ No ambiguity with body parameters (GET requests don't have bodies)

**Verdict: ✅ SAFE**

### 3. `ContextFilterRequest = Depends()` (1 instance)

**Location:**
- `src/core/api/routes/utility.py:182` - `get_contexts()`

**Model Definition:**
```python
class ContextFilterRequest(BaseAPIRequest, LLMRequestMixin):
    name: Optional[str] = None
    include_deprecated: bool = False
    with_details: bool = False
    # Inherits from BaseAPIRequest and LLMRequestMixin
```

**Analysis:**
- ✅ GET endpoint (no body parameters)
- ✅ `ContextFilterRequest` is a Pydantic `BaseModel` (inherits from `BaseAPIRequest`)
- ✅ FastAPI correctly infers these as query parameters
- ✅ No ambiguity with body parameters (GET requests don't have bodies)

**Verdict: ✅ SAFE**

## Why These Are Safe

### 1. All Are GET Endpoints

All 7 instances are used in GET endpoints, which don't have request bodies. This eliminates any possibility of FastAPI confusing query parameters with body parameters.

### 2. All Use Pydantic Models

All instances use Pydantic `BaseModel` classes:
- `PaginationParams` - Direct `BaseModel` subclass
- `DomainFilterRequest` - Inherits from `BaseAPIRequest` (which is a `BaseModel`)
- `ContextFilterRequest` - Inherits from `BaseAPIRequest` (which is a `BaseModel`)

FastAPI can automatically infer that Pydantic models in `Depends()` should be extracted from query parameters when:
- The endpoint is GET/HEAD/DELETE (no body)
- OR the model is explicitly marked as query parameters
- OR there's no ambiguity with body parameters

### 3. No Service Classes

None of these instances use service classes (like `OKHService`, `StorageService`, etc.), which was the root cause of the original issue.

## Comparison with Problematic Pattern

**❌ Problematic (Original Issue):**
```python
# POST/PUT endpoint with body parameter
async def update_supply_tree(
    request: SupplyTreeCreateRequest,  # Body parameter
    okh_service: OKHService = Depends()  # ❌ Service class, no callable
):
```

**✅ Safe (Current Instances):**
```python
# GET endpoint, no body
async def list_supply_trees(
    pagination: PaginationParams = Depends()  # ✅ Pydantic model, GET endpoint
):
```

## Recommendations

### ✅ No Changes Needed

All instances are safe and follow FastAPI best practices. No changes required.

### 📋 Future Guidelines

When adding new endpoints:

1. **For GET endpoints with query parameters:**
   ```python
   # ✅ Safe: Pydantic model in GET endpoint
   async def my_endpoint(
       params: MyParams = Depends()  # Safe for GET
   ):
   ```

2. **For POST/PUT endpoints with body parameters:**
   ```python
   # ✅ Safe: Explicit callable for services
   async def my_endpoint(
       request: MyRequest,  # Body parameter
       service: MyService = Depends(get_my_service)  # Must use callable
   ):
   ```

3. **When in doubt:**
   - Always use explicit callables for service dependencies
   - Empty `Depends()` is only safe for Pydantic models in GET endpoints
   - For POST/PUT endpoints, prefer explicit callables even for Pydantic models if there's any ambiguity

## Testing Verification

Verified via OpenAPI schema inspection:
- All GET endpoints correctly show query parameters (not requestBody)
- No wrapper schemas created for these dependencies
- FastAPI correctly infers parameter sources

## Conclusion

**All 7 instances of `= Depends()` are safe and require no changes.**

The original issue was specific to:
1. Service classes (not Pydantic models)
2. POST/PUT endpoints (with body parameters)
3. Missing callable arguments

None of the current instances have these characteristics, so they are all safe.

