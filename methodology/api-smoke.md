# API Smoke Test Methodology

## Purpose

Quick validation that a model is reachable through the gateway and responds to basic requests. This is the first gate before role-fit evaluation.

## Scope

- Gateway connectivity
- Authentication
- Basic chat completion
- Response structure validity
- Latency threshold check

**Not tested**: Tool calling, reasoning quality, role-specific capabilities

## Test Procedure

### Input

- Model identifier (e.g., `provider/model-name`)
- Gateway endpoint
- Authentication credentials
- Timeout threshold (default: 30s)

### Test Case

Send minimal chat completion request:

```json
{
  "model": "provider/model-name",
  "messages": [
    {"role": "user", "content": "Reply with: OK"}
  ],
  "max_tokens": 10,
  "temperature": 0
}
```

### Success Criteria

1. **HTTP 200**: Request completed successfully
2. **Valid structure**: Response contains `choices[0].message.content`
3. **Non-empty response**: Content is not empty or whitespace
4. **Latency acceptable**: Response within timeout threshold
5. **No auth errors**: No 401/403 status codes

### Failure Classification

- **AUTH_FAILURE**: 401/403 status code
- **NOT_FOUND**: 404 status code (model not available)
- **TIMEOUT**: Request exceeded timeout threshold
- **INVALID_RESPONSE**: Missing expected fields in response
- **GATEWAY_ERROR**: 500/502/503 gateway errors
- **UNKNOWN**: Other errors

## Expected Output

### Success

```
✓ Model: provider/model-name
  Status: AVAILABLE
  Latency: 450ms
  Response: OK
```

### Failure

```
✗ Model: provider/model-name
  Status: AUTH_FAILURE
  Error: 401 Unauthorized
  Message: Invalid API key
```

## Usage in Router Evaluation

API smoke test runs before role-fit evaluation:

```
Phase 1: API Smoke Test
├─ provider/model-a → ✓ AVAILABLE (380ms)
├─ provider/model-b → ✗ AUTH_FAILURE
└─ provider/model-c → ✓ AVAILABLE (520ms)

Phase 2: Role Fit (only for available models)
├─ provider/model-a → scout:PASS, coder:PASS, reviewer:PASS
└─ provider/model-c → scout:PASS, coder:FAIL, reviewer:PASS
```

## Limitations

- Does not test role-specific capabilities
- Does not verify tool calling support
- Does not test reasoning quality
- Does not validate context window size
- Simple prompt may not trigger rate limits

**Use this for**: Gateway availability check  
**Use role-fit for**: Capability validation
