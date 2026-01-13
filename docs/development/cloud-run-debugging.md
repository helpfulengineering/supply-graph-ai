# Cloud Run Debugging Guide

## Important: No Direct Container Access

**Cloud Run does NOT support `exec` into running containers.** This is by design for security and scalability. However, there are several effective debugging methods available.

## Why Logs Might Not Appear in Cloud Logging

### 1. **Log Level Filtering**

Your application defaults to `LOG_LEVEL=INFO`. If you're looking for `DEBUG` logs, they won't appear.

**Solution:** Set `LOG_LEVEL=DEBUG` in your Cloud Run service:

```bash
gcloud run services update supply-graph-ai \
  --region us-west1 \
  --update-env-vars LOG_LEVEL=DEBUG
```

Or add it to your deployment configuration in `deploy/providers/gcp/cloud_run.py`.

### 2. **Log Buffering**

Python's logging may buffer output. Ensure logs are flushed immediately:

```python
import sys
sys.stdout.flush()
sys.stderr.flush()
```

Your current logging setup already uses `StreamHandler` which should flush, but you can add explicit flushing for critical debug statements.

### 3. **Cloud Logging Query Filters**

The Logs Explorer might be filtering out your logs. Try these queries:

**View all logs:**
```
resource.type="cloud_run_revision"
resource.labels.service_name="supply-graph-ai"
```

**View only DEBUG logs:**
```
resource.type="cloud_run_revision"
resource.labels.service_name="supply-graph-ai"
severity="DEBUG"
```

**View logs with specific text:**
```
resource.type="cloud_run_revision"
resource.labels.service_name="supply-graph-ai"
textPayload=~"your-debug-message"
```

**View JSON structured logs:**
```
resource.type="cloud_run_revision"
resource.labels.service_name="supply-graph-ai"
jsonPayload.message=~"your-message"
```

**View logs from matching_service.py specifically:**
```
resource.type="cloud_run_revision"
resource.labels.service_name="supply-graph-ai"
jsonPayload.module="matching_service"
```

**View logs by severity (INFO/WARNING):**
```
resource.type="cloud_run_revision"
resource.labels.service_name="supply-graph-ai"
severity>=INFO
```

## Debugging Methods

### Method 1: Enhanced Logging via Environment Variables

**Set DEBUG mode and lower log level:**

```bash
gcloud run services update supply-graph-ai \
  --region us-west1 \
  --update-env-vars LOG_LEVEL=DEBUG,DEBUG=true
```

**View last 100 log entries:**
```bash
gcloud run services logs read supply-graph-ai \
  --region us-west1 \
  --limit 100
```

**View logs in real-time (streaming):**
```bash
gcloud logging tail "resource.type=cloud_run_revision AND resource.labels.service_name=supply-graph-ai" \
  --format json
```

### Method 2: Add Temporary Debug Endpoints

Add a debug endpoint to your FastAPI app that outputs internal state:

```python
@app.get("/debug/internal-state")
async def debug_internal_state():
    """Temporary debug endpoint - remove in production"""
    import sys
    import logging
    
    logger = logging.getLogger()
    
    return {
        "log_level": logging.getLevelName(logger.level),
        "handlers": [str(h) for h in logger.handlers],
        "stdout_flushable": sys.stdout.flushable,
        "environment": os.getenv("K_SERVICE", "not-cloud-run"),
        "log_config": {
            "LOG_LEVEL": os.getenv("LOG_LEVEL", "INFO"),
            "DEBUG": os.getenv("DEBUG", "False"),
        }
    }
```

### Method 3: Use Cloud Logging Advanced Queries

**Find logs by module/function:**
```
resource.type="cloud_run_revision"
resource.labels.service_name="supply-graph-ai"
jsonPayload.module="matching_service"
jsonPayload.function="your_function_name"
```

**Find logs by severity:**
```
resource.type="cloud_run_revision"
resource.labels.service_name="supply-graph-ai"
severity>=WARNING
```

**Find logs in time range:**
```
resource.type="cloud_run_revision"
resource.labels.service_name="supply-graph-ai"
timestamp>="2026-01-12T23:00:00Z"
timestamp<="2026-01-12T23:59:59Z"
```

### Method 4: Local Testing with Cloud Run Emulator

Test your container locally to verify logging works:

```bash
# Build your image
docker build -t supply-graph-ai:debug .

# Run locally with same environment
docker run -it --rm \
  -e LOG_LEVEL=DEBUG \
  -e DEBUG=true \
  -e K_SERVICE=local-test \
  -p 8080:8080 \
  supply-graph-ai:debug

# Check logs
docker logs <container-id>
```

### Method 5: Add Explicit Log Flushing

If logs aren't appearing, add explicit flushing in critical sections:

```python
import sys
import logging

logger = logging.getLogger(__name__)

def debug_with_flush(message: str):
    """Log and immediately flush to ensure Cloud Run captures it"""
    logger.debug(message)
    sys.stdout.flush()
    sys.stderr.flush()
```

### Method 6: Use Cloud Run Execution Environment Logs

Cloud Run captures both:
- **Container logs** (stdout/stderr from your app)
- **Execution environment logs** (Cloud Run infrastructure)

View execution environment logs:
```bash
gcloud logging read \
  "resource.type=cloud_run_revision AND resource.labels.service_name=supply-graph-ai" \
  --limit 50 \
  --format json
```

## Troubleshooting Missing Logs

### Check 1: Verify Logs Are Being Written

Add a test endpoint that writes directly to stdout:

```python
@app.get("/debug/test-logging")
async def test_logging():
    import sys
    print("TEST: Direct stdout print", flush=True)
    sys.stdout.write("TEST: Direct stdout write\n")
    sys.stdout.flush()
    
    logger.info("TEST: Logger info message")
    logger.debug("TEST: Logger debug message")
    logger.warning("TEST: Logger warning message")
    
    sys.stdout.flush()
    sys.stderr.flush()
    
    return {"status": "logs written, check Cloud Logging"}
```

### Check 2: Verify Log Level Configuration

```python
@app.get("/debug/log-config")
async def log_config():
    import logging
    logger = logging.getLogger()
    
    return {
        "root_level": logging.getLevelName(logger.level),
        "handlers": [
            {
                "type": type(h).__name__,
                "level": logging.getLevelName(h.level),
                "stream": str(h.stream) if hasattr(h, 'stream') else None
            }
            for h in logger.handlers
        ],
        "env_vars": {
            "LOG_LEVEL": os.getenv("LOG_LEVEL"),
            "DEBUG": os.getenv("DEBUG"),
            "K_SERVICE": os.getenv("K_SERVICE"),
        }
    }
```

### Check 3: Verify JSON Formatting

Your logs use structured JSON. Verify they're being parsed correctly:

```bash
gcloud logging read \
  "resource.type=cloud_run_revision AND resource.labels.service_name=supply-graph-ai" \
  --limit 10 \
  --format json \
  | jq '.[] | select(.jsonPayload) | .jsonPayload'
```

## Best Practices

1. **Use Structured Logging**: Your app already does this ✅
2. **Include Context**: Add request IDs, trace IDs, user IDs
3. **Set Appropriate Levels**: Use DEBUG for development, INFO for production
4. **Flush Critical Logs**: Add explicit flushing for important debug statements
5. **Use Cloud Logging Queries**: Learn the query syntax for efficient log searching
6. **Monitor Log Volume**: Too many DEBUG logs can increase costs

## Quick Reference Commands

```bash
# View last 100 logs (correct command - no 'tail' option)
gcloud run services logs read supply-graph-ai --region us-west1 --limit 100

# View real-time logs (streaming) - use gcloud logging tail
gcloud logging tail "resource.type=cloud_run_revision AND resource.labels.service_name=supply-graph-ai"

# View logs from matching_service.py
gcloud logging read \
  "resource.type=cloud_run_revision AND resource.labels.service_name=supply-graph-ai AND jsonPayload.module=matching_service" \
  --limit 50 \
  --format json

# Update log level
gcloud run services update supply-graph-ai \
  --region us-west1 \
  --update-env-vars LOG_LEVEL=DEBUG

# View logs with gcloud logging (more powerful)
gcloud logging read \
  "resource.type=cloud_run_revision AND resource.labels.service_name=supply-graph-ai AND severity>=INFO" \
  --limit 50 \
  --format json

# Export logs to file
gcloud logging read \
  "resource.type=cloud_run_revision AND resource.labels.service_name=supply-graph-ai" \
  --limit 1000 \
  --format json > cloud-run-logs.json
```

## Alternative: Use Cloud Logging Explorer

Instead of `gcloud`, use the [Google Cloud Console Logs Explorer](https://console.cloud.google.com/logs/query):

1. Go to Cloud Console → Logging → Logs Explorer
2. Select resource type: `Cloud Run Revision`
3. Select service: `supply-graph-ai`
4. Add filters for severity, text, JSON fields, etc.
5. Use "Run query" to see filtered results

## Known Issue Fixed: LOG_LEVEL String Conversion

**Problem:** `LOG_LEVEL` was being passed as a string (e.g., `"INFO"`) to `setup_logging()`, which expects an integer (e.g., `logging.INFO`). This caused logging levels to not be set correctly, preventing INFO/WARNING logs from appearing.

**Solution:** Fixed in `src/core/main.py` and `src/core/utils/logging.py`:
- `setup_logging()` now accepts both string and integer log levels
- Automatic conversion from string to integer logging constant
- Added line buffering for stdout/stderr in container environments to ensure immediate log flushing

## Summary

- ❌ **Cannot exec into Cloud Run containers**
- ✅ **Use Cloud Logging** (stdout/stderr are automatically captured)
- ✅ **LOG_LEVEL bug fixed** - string levels now properly converted to integers
- ✅ **Use structured queries** in Logs Explorer (see examples above for matching_service.py)
- ✅ **Line buffering enabled** for immediate log flushing in containers
- ✅ **Test locally** with Docker to verify logging works
