# Zapier Integration Debugging Guide

## Issue: Internal Server Error (500) from Webhook API

### Problem Description
When sending requests from Zapier to the webhook API, you were receiving 500 Internal Server Error responses even for validation errors that should return 400 Bad Request.

### Root Cause
The exception handling in `src/webhook_service/endpoints.py` had a bug where the broad `except Exception as e:` clause was catching **all** exceptions, including `HTTPException` objects that were meant to pass through with their original status codes.

**Affected Code (lines 198-207, 299-308, 415-428):**
```python
except Exception as e:
    logger.error(f"Unexpected error in create_summary: {e}", exc_info=True)
    raise HTTPException(
        status_code=500,  # ❌ This was converting ALL errors to 500
        detail={
            "error": "INTERNAL_ERROR",
            "message": str(e),
            "request_id": request_id
        }
    )
```

**What Happened:**
1. Code raised `HTTPException(status_code=400, detail={...})` for validation errors
2. The `except Exception` clause caught this HTTPException
3. It re-raised it as a new `HTTPException(status_code=500)`
4. User saw 500 error instead of proper 400 validation error

### The Fix
Added `except HTTPException:` clauses **before** `except Exception:` to allow HTTP exceptions to pass through without modification.

**Fixed Code:**
```python
except SummarizationError as e:
    logger.error(f"Summarization failed: {e}")
    raise HTTPException(
        status_code=500,
        detail={
            "error": e.error_code,
            "message": str(e),
            "request_id": request_id
        }
    )

except HTTPException:
    # ✅ Re-raise HTTPException without modification
    raise

except Exception as e:
    # ✅ Now only catches truly unexpected exceptions
    logger.error(f"Unexpected error in create_summary: {e}", exc_info=True)
    raise HTTPException(
        status_code=500,
        detail={
            "error": "INTERNAL_ERROR",
            "message": str(e),
            "request_id": request_id
        }
    )
```

### Files Modified
- `/workspaces/summarybot-ng/src/webhook_service/endpoints.py`
  - Lines 198-200: Added HTTPException re-raise in `create_summary_from_messages`
  - Lines 299-301: Added HTTPException re-raise in `/summarize` endpoint
  - Lines 415-417: Added HTTPException re-raise in schedule endpoint

### Testing the Fix

#### Before Fix:
```bash
# Empty messages array - should return 400
$ curl -X POST https://summarybot-ng.fly.dev/api/v1/summaries \
  -H "Content-Type: application/json" \
  -H "X-API-Key: test-api-key-12345" \
  -d '{"channel_id":"test","guild_id":"test","messages":[]}'

# Response: HTTP 500 ❌
{
  "detail": {
    "error": "INTERNAL_ERROR",
    "message": "400: {'error': 'INVALID_REQUEST', 'message': 'No messages provided'}",
    "request_id": "req-..."
  }
}
```

#### After Fix:
```bash
# Empty messages array - should return 400
$ curl -X POST https://summarybot-ng.fly.dev/api/v1/summaries \
  -H "Content-Type: application/json" \
  -H "X-API-Key: test-api-key-12345" \
  -d '{"channel_id":"test","guild_id":"test","messages":[]}'

# Response: HTTP 400 ✅
{
  "detail": {
    "error": "INVALID_REQUEST",
    "message": "No messages provided",
    "request_id": "req-1767818484.833637"
  }
}
```

### Verification Steps

1. **Test successful request:**
```bash
curl -X POST https://summarybot-ng.fly.dev/api/v1/summaries \
  -H "Content-Type: application/json" \
  -H "X-API-Key: test-api-key-12345" \
  -d '{
    "messages": [
      {
        "id": "msg-001",
        "author_name": "User",
        "author_id": "123",
        "content": "Test message",
        "timestamp": "2026-01-07T20:00:00"
      }
    ],
    "channel_id": "test-channel",
    "guild_id": "test-guild"
  }'
```
**Expected:** HTTP 200/201, summary returned

2. **Test validation error:**
```bash
curl -X POST https://summarybot-ng.fly.dev/api/v1/summaries \
  -H "Content-Type: application/json" \
  -H "X-API-Key: test-api-key-12345" \
  -d '{"channel_id":"test","guild_id":"test","messages":[]}'
```
**Expected:** HTTP 400, INVALID_REQUEST error

3. **Test authentication error:**
```bash
curl -X POST https://summarybot-ng.fly.dev/api/v1/summaries \
  -H "Content-Type: application/json" \
  -d '{"messages":[],"channel_id":"test","guild_id":"test"}'
```
**Expected:** HTTP 401, authentication required

### Zapier Configuration Update
No changes needed to your Zapier webhook configuration. The API now returns proper status codes:
- **200/201** - Success
- **400** - Validation errors (bad request format, missing fields, invalid values)
- **401** - Authentication required
- **500** - Actual server errors

### Deployment
```bash
flyctl deploy --app summarybot-ng
```

### Monitoring
Check logs for proper error handling:
```bash
flyctl logs --app summarybot-ng
```

Look for:
- ✅ HTTP 400 responses for validation errors (not 500)
- ✅ Clean error messages in response JSON
- ✅ No unexpected exception traces for validation errors

### Prevention
**Best Practice for FastAPI Exception Handling:**
Always order exception handlers from **most specific to least specific**:

```python
try:
    # Your code
    pass
except SpecificCustomError as e:
    # Handle specific errors
    raise HTTPException(status_code=400, detail={...})
except HTTPException:
    # Always re-raise HTTPException without modification
    raise
except Exception as e:
    # Catch-all for truly unexpected errors
    raise HTTPException(status_code=500, detail={...})
```

### Related Issues
- Python exception handling order matters
- FastAPI HTTPException is itself an Exception
- Broad except clauses can mask intentional errors

### Summary
**Issue:** 500 errors returned for validation problems
**Cause:** Exception handler catching and re-wrapping HTTPExceptions
**Fix:** Added `except HTTPException: raise` before broad exception handler
**Result:** Proper HTTP status codes (400 for validation, 500 for server errors)
**Deployment:** Live at https://summarybot-ng.fly.dev
**Status:** ✅ Fixed and deployed
