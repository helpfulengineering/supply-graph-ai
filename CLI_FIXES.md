# CLI Issues Fixed

## Issues Identified and Fixed

### Issue 1: Server Availability Check Incorrectly Reports "Server Unavailable"

**Problem**: The CLI was reporting "Server unavailable" even when the API server was running and responding correctly.

**Root Cause**: The `execute_with_fallback` method in `src/cli/base.py` was catching all exceptions too broadly, including HTTP status errors (4xx, 5xx) which indicate the server IS available but the request failed.

**Fix**: Made the error handling more specific:
- Now specifically catches connection-related exceptions: `httpx.ConnectError`, `httpx.TimeoutException`, `httpx.NetworkError`
- HTTP status errors (4xx, 5xx) are now properly re-raised as API errors instead of triggering fallback
- Only actual connection failures trigger the fallback to direct service calls

**Files Changed**:
- `src/cli/base.py` - Updated `execute_with_fallback` method

### Issue 2: Domain Registration Error in Direct Service Mode

**Problem**: When using direct service calls (fallback mode), validation failed with error: "Domain 'manufacturing' is not registered. Available domains: []"

**Root Cause**: Domains are only registered during FastAPI startup (in the `lifespan` function). When CLI commands use direct services, they bypass the FastAPI startup, so domains are never registered. The `ValidationContext` class checks if domains are registered and raises an error if they're not.

**Fix**: 
1. Created `ensure_domains_registered()` function in `src/cli/base.py` that registers domains when needed
2. This function is automatically called by `execute_with_fallback` when falling back to direct services
3. Also added explicit calls in fallback functions for extra safety

**Files Changed**:
- `src/cli/base.py` - Added `ensure_domains_registered()` function and integrated it into `execute_with_fallback`
- `src/cli/system.py` - Added domain registration to fallback health check
- `src/cli/okh.py` - Added domain registration to fallback validate function

### Issue 3: Incorrect Parameter Type in OKH Validate

**Problem**: The `okh_service.validate()` method was being called with an `OKHManifest` object instead of a dictionary.

**Root Cause**: The method signature expects `content: Dict[str, Any]` but the CLI was passing an `OKHManifest` object.

**Fix**: Changed the call to pass `manifest_data` (dict) directly instead of converting to `OKHManifest` first.

**Files Changed**:
- `src/cli/okh.py` - Fixed validate call to pass dict instead of OKHManifest object

## Testing Recommendations

1. **Test Server Availability Detection**:
   ```bash
   # With server running
   python ome system health
   # Should show "Connected to server successfully" (not "Server unavailable")
   
   # With server stopped
   python ome system health
   # Should show "Server unavailable, using direct service calls..."
   ```

2. **Test Domain Registration**:
   ```bash
   # With server stopped, test validation
   python ome okh validate synth/synthetic-data/arduino-based-iot-sensor-node-1-9-0-okh.json
   # Should work without "Domain 'manufacturing' is not registered" error
   ```

3. **Test Validation**:
   ```bash
   # Test with server running
   python ome okh validate synth/synthetic-data/arduino-based-iot-sensor-node-1-9-0-okh.json
   
   # Test with server stopped (fallback mode)
   python ome okh validate synth/synthetic-data/arduino-based-iot-sensor-node-1-9-0-okh.json
   ```

## Additional Notes

- The `ensure_domains_registered()` function is idempotent - it checks if domains are already registered before registering them
- All fallback operations now automatically ensure domains are registered
- The server availability check is now more accurate and won't incorrectly report server as unavailable when it's actually responding

