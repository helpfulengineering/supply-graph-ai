# FastAPI Dependency Injection Patterns

## Problem Summary

We encountered a persistent 422 error in the `update_supply_tree` endpoint that was caused by incorrect FastAPI dependency injection patterns.

## Root Cause Analysis

### The Problem

When using `Depends()` without a callable argument, FastAPI cannot determine what to inject. In certain scenarios, especially when there are multiple parameters that could be body parameters, FastAPI may incorrectly treat the dependency as a body parameter, creating a wrapper schema.

### Specific Issue in `update_supply_tree`

**Before (Broken):**
```python
async def update_supply_tree(
    request: SupplyTreeCreateRequest,
    id: UUID = Path(...),
    http_request: Request = None,
    storage_service: StorageService = Depends(get_storage_service),
    okh_service: OKHService = Depends(),  # ❌ WRONG: No callable
    okw_service: OKWService = Depends()   # ❌ WRONG: No callable
):
```

**What Happened:**
1. FastAPI saw `Depends()` without arguments for `okh_service` and `okw_service`
2. It couldn't infer what to inject (no type annotation inference for services)
3. It treated these as potential body parameters
4. This caused FastAPI to create a wrapper schema: `Body_update_supply_tree_api_supply_tree__id__put`
5. The wrapper schema expected the body to be wrapped: `{"request": {...}, "config": {...}}`
6. But the client was sending the body directly: `{...}`
7. Result: **422 Unprocessable Entity** - "Field required: body.request"

**After (Fixed):**
```python
async def update_supply_tree(
    request: SupplyTreeCreateRequest,
    id: UUID = Path(...),
    http_request: Request = None,
    storage_service: StorageService = Depends(get_storage_service),
    okh_service: OKHService = Depends(get_okh_service),  # ✅ CORRECT: Explicit callable
    okw_service: OKWService = Depends(get_okw_service)   # ✅ CORRECT: Explicit callable
):
```

### Why Pydantic Models Work with `Depends()`

Some uses of `Depends()` without arguments are **safe**:

```python
# ✅ SAFE: Pydantic models are inferred from query parameters
pagination: PaginationParams = Depends()
filter_params: DomainFilterRequest = Depends()
```

**Why this works:**
- FastAPI can infer that `PaginationParams` (a Pydantic model) should be extracted from query parameters
- It automatically creates the dependency injection based on the type annotation
- No ambiguity exists because Pydantic models are clearly not services

**Why services don't work:**
- Service classes (like `OKHService`, `StorageService`) are not Pydantic models
- FastAPI cannot automatically infer how to instantiate them
- Without a callable, FastAPI doesn't know what to inject
- This creates ambiguity that can lead to incorrect body parameter inference

## Correct Patterns

### ✅ Pattern 1: Service Dependencies (Always Use Callable)

```python
# Define dependency function
async def get_okh_service() -> OKHService:
    """Get OKH service instance."""
    return await OKHService.get_instance()

# Use in endpoint
async def my_endpoint(
    okh_service: OKHService = Depends(get_okh_service)  # ✅ Explicit callable
):
    pass
```

### ✅ Pattern 2: Pydantic Model Dependencies (Can Use Empty Depends)

```python
# Pydantic model for query parameters
class PaginationParams(BaseModel):
    page: int = 1
    page_size: int = 20

# Use in endpoint
async def my_endpoint(
    pagination: PaginationParams = Depends()  # ✅ Safe: FastAPI infers from query params
):
    pass
```

### ✅ Pattern 3: Path/Query Parameters (Use Path/Query, Not Depends)

```python
async def my_endpoint(
    id: UUID = Path(...),           # ✅ Use Path for path parameters
    page: int = Query(1)            # ✅ Use Query for query parameters
):
    pass
```

## Response Model Considerations

### The `response_model` Issue

We also removed `response_model=SupplyTreeResponse` from the decorator. Here's why:

**Problem:**
- `response_model` tells FastAPI to validate the response against the model
- `SupplyTreeResponse` inherits from `BaseAPIResponse`, which requires `status`, `message`, `timestamp` fields
- But the endpoint returns a raw dictionary with supply tree data
- The `@api_endpoint` decorator is designed to wrap this dictionary into a `SuccessResponse`
- Having `response_model` caused FastAPI to validate before the decorator could wrap it
- Result: **ResponseValidationError** - "Field required: response.message"

**Solution:**
- Remove `response_model` from endpoints that use `@api_endpoint` decorator
- Let the decorator handle response wrapping and validation
- FastAPI will still serialize the response correctly

**When to use `response_model`:**
- Use when the endpoint directly returns a Pydantic model
- Use when you want FastAPI to validate the response structure
- **Don't use** when `@api_endpoint` decorator handles response wrapping

## Code Audit Results

### ✅ Safe Uses of `Depends()` (Pydantic Models)

These are safe because FastAPI can infer they're query parameter models:

- `src/core/api/routes/supply_tree.py:394` - `PaginationParams = Depends()`
- `src/core/api/routes/utility.py:77` - `DomainFilterRequest = Depends()`
- `src/core/api/routes/utility.py:182` - `ContextFilterRequest = Depends()`
- `src/core/api/routes/okw.py:490` - `PaginationParams = Depends()`
- `src/core/api/routes/match.py:631` - `PaginationParams = Depends()`
- `src/core/api/routes/package.py:279` - `PaginationParams = Depends()`
- `src/core/api/routes/okh.py:320` - `PaginationParams = Depends()`

### ✅ Correct Service Dependencies

All service dependencies now use explicit callables:

- `Depends(get_storage_service)`
- `Depends(get_okh_service)`
- `Depends(get_okw_service)`
- `Depends(get_matching_service)`
- `Depends(get_package_service)`

## Best Practices

1. **Always use explicit callables for service dependencies**
   ```python
   # ✅ Good
   service: MyService = Depends(get_my_service)
   
   # ❌ Bad
   service: MyService = Depends()
   ```

2. **Empty `Depends()` is safe only for Pydantic models**
   ```python
   # ✅ Safe: Pydantic model
   params: MyParams = Depends()
   
   # ❌ Unsafe: Service class
   service: MyService = Depends()
   ```

3. **Use `response_model` carefully**
   - Only when endpoint directly returns a Pydantic model
   - Not when using `@api_endpoint` decorator (it handles wrapping)

4. **Define dependency functions explicitly**
   ```python
   # ✅ Good: Explicit dependency function
   async def get_my_service() -> MyService:
       return await MyService.get_instance()
   ```

## Testing for This Issue

To detect this issue in the future:

1. **Check OpenAPI schema:**
   ```bash
   curl http://localhost:8001/v1/openapi.json | jq '.paths."/api/supply-tree/{id}".put.requestBody'
   ```
   - Should reference the direct model: `"$ref": "#/components/schemas/SupplyTreeCreateRequest"`
   - Should NOT reference a wrapper: `"$ref": "#/components/schemas/Body_..."`

2. **Integration tests:**
   - Test endpoints with multiple dependencies
   - Verify request body is accepted directly (not wrapped)
   - Check for 422 errors that suggest body structure issues

3. **Code review checklist:**
   - [ ] All service dependencies use explicit callables
   - [ ] No `Depends()` without arguments for services
   - [ ] `response_model` only used when appropriate

## Related Issues

- FastAPI issue: When multiple body-like parameters exist, FastAPI can get confused about which is the actual body
- Solution: Always be explicit about dependencies and use `Body(...)` when needed

## References

- [FastAPI Dependencies Documentation](https://fastapi.tiangolo.com/tutorial/dependencies/)
- [FastAPI Request Body Documentation](https://fastapi.tiangolo.com/tutorial/body/)
- Internal fix: `src/core/api/routes/supply_tree.py:522-523`

