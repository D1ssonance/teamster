# Phase 2.2: Fallback Execution Logic

## Overview

Automatic retry through the fallback chain when a model fails due to 
retryable errors (rate limits, provider outages, timeouts), while 
failing fast on non-retryable errors (protocol mismatches, invalid requests).

## Problem Statement

**Before Phase 2.2:**
```
spawn(role, task) 
  → select ONE model from chain
  → try it
  → error → fail immediately
  → user must manually retry
```

**Result:** High failure rate from transient provider issues, manual intervention needed

## Solution

**After Phase 2.2:**
```
spawn(role, task)
  → loop through fallback chain:
      → select next available model
      → try it
      → retryable error? → continue to next model
      → non-retryable error? → fail fast
      → success? → return immediately
  → all exhausted → structured error
```

**Result:** Much higher success rate, automatic recovery from transient issues

## Error Classification

Four error types with distinct retry strategies:

### 1. Rate Limit (429)

**Indicators:**
- HTTP 429 status
- Error message contains "rate limit", "quota exceeded"

**Strategy:**
- Report to cooldown tracker
- Mark model unavailable for cooldown period
- Try next model in chain

**Reason:** Provider quota exhausted temporarily

### 2. Provider Error (503/504/timeout)

**Indicators:**
- HTTP 503, 504 status
- Connection timeout
- Error message contains "unavailable", "timeout", "connection"

**Strategy:**
- Try next model immediately
- Don't mark long cooldown (might be transient)

**Reason:** Provider infrastructure issue, not quota

### 3. Bad Request (400/422)

**Indicators:**
- HTTP 400, 422 status
- Error message contains "invalid", "malformed", "bad request"

**Strategy:**
- Fail fast, don't try other models
- Return error to caller immediately

**Reason:** Task incompatible with model (wrong protocol, unsupported feature)

### 4. Unknown

**Indicators:**
- Any other error not matching above patterns

**Strategy:**
- Cautiously try next model
- Log for investigation

**Reason:** Be conservative, but don't block on unknown errors

## Implementation

### Key Design Decision: Reuse Existing Logic

**Discovery:** Existing model selection already iterates through models array 
and returns first not-on-cooldown. 

**Insight:** Calling model reservation multiple times in a retry loop 
automatically traverses the fallback chain!

**Before (single attempt):**
```python
model = reserve_model(config, role_spec)
result = await rlm(prompt, model=model)
return result
```

**After (retry loop):**
```python
tried_models = []
for attempt in range(max_attempts):
    model = reserve_model(config, role_spec)
    tried_models.append(model)
    
    try:
        result = await rlm(prompt, model=model)
        return result  # Success!
    except Exception as exc:
        error_type = classify_error(exc)
        
        if error_type == "rate_limit":
            report_cooldown(model)
            continue  # Try next
        elif error_type == "provider_error":
            continue  # Try next immediately
        elif error_type == "bad_request":
            raise  # Fail fast
        else:
            continue  # Cautiously try next

# All exhausted
raise CapacityError(f"Tried: {tried_models}")
```

**Benefits:**
- Minimal code change (+50 lines)
- Reuses existing selection logic
- Preserves cooldown tracking
- No duplication of fallback logic

### Error Message Structure

**Exhausted all models:**
```
CorporityCapacityError: All 5 fallback attempt(s) for role 'coder' failed.
Tried models: provider-a/model-1, provider-a/model-2, provider-b/model-3.
Last error: TimeoutError: Connection timed out after 30s
```

**Benefits:**
- Lists what was attempted (debugging)
- Shows last error (diagnosis)
- Clear failure reason (not just "capacity")

### Integration with Cooldowns

**Cooldown mechanism unchanged:**
- Rate limits still trigger cooldowns
- Cooldown duration still configured per quota group
- State persistence still works

**New behavior:**
- Rate limited model → cooldown + try next
- Before: rate limited model → fail immediately
- Result: Automatic fallback to secondary models

### Integration with Quota Groups

**Quota enforcement unchanged:**
- Per-group start rate limits still enforced
- Burst windows still tracked
- Manual cooldowns still respected

**New behavior:**
- Quota exhaustion checked once before loop
- If quota full → fail before trying any models
- Reason: Don't waste attempts when quota is the blocker

## Retry Boundaries

### What Gets Retried

- ✅ Rate limits (429)
- ✅ Provider timeouts
- ✅ Provider unavailability (503/504)
- ✅ Connection errors
- ✅ Unknown errors (cautiously)

### What Doesn't Get Retried

- ❌ Bad request (400/422) - protocol mismatch
- ❌ Authentication failures (401/403) - wrong credentials
- ❌ Quota group exhaustion - no models available anyway
- ❌ All roles empty - session router problem

**Reason:** Don't waste fallback attempts on non-retryable errors

## Safety Mechanisms

### Maximum Attempts

**Bounded by models array length:**
```python
max_attempts = len(role_spec["models"])
```

**Never infinite:**
- Even with unknown errors, loop terminates
- Maximum attempts = number of models for role
- Typical: 2-5 models per role

### Fail-Fast for Bad Requests

**Important:** If task is incompatible with model type, don't try all models

**Example:**
- Task requires vision capability
- Role has 3 text-only models
- First model returns 400 "vision not supported"
- Don't try remaining text-only models
- Fail fast with clear error

### Structured Logging

**Log each attempt:**
- Model tried
- Error type
- Decision (retry/fail-fast)

**Don't log:**
- Full request bodies
- Full response bodies
- User data
- Secrets

## Testing Strategy

### Unit Tests

**Error classification:**
- Test 429 detection
- Test 503/timeout detection
- Test 400/422 detection
- Test unknown error handling

**Retry logic:**
- Test successful first attempt
- Test fallback to second model
- Test all models exhausted
- Test fail-fast on bad request

### Integration Tests

**With real runtime:**
- Test with mock provider returning 429
- Test with mock provider timing out
- Test with mock provider returning 503
- Verify cooldown tracking works
- Verify structured error messages

### Failure Injection

**Controlled failures:**
- Inject 429 on first model, success on second
- Inject timeout on first model, success on second
- Inject 400 on first model, verify fail-fast
- Measure success rate improvement

## Monitoring Metrics

### Success Metrics

**Fallback success rate:**
- % of spawns that succeeded after fallback
- Target: >80% of initial failures recovered

**Models per spawn:**
- Average models tried: expect ~1.2 (most succeed first try)
- P95 models tried: expect <3
- P99 models tried: expect ≤ max_attempts

**Recovery time:**
- Time from first error to fallback success
- Target: <5s additional latency

### Failure Metrics

**Exhaustion rate:**
- % of spawns that exhausted all models
- Target: <5%

**Bad request rate:**
- % of spawns that failed fast due to 400/422
- Indicates: task/model mismatch issues

**Error distribution:**
- Which error types most common
- Informs: provider reliability, quota tuning

## Operational Considerations

### Capacity Planning

**More fallbacks = more quota consumed:**
- Primary model rate limited → secondary model used → quota consumed
- Plan quotas for both primary and fallback usage
- Monitor fallback frequency

### Provider Reliability

**Fallback exposes provider differences:**
- If secondary model rarely used → primary reliable
- If secondary frequently used → primary unreliable
- Adjust fallback priority based on observed reliability

### Cost Implications

**Fallback increases total requests:**
- Primary fails → secondary succeeds = 2 requests
- Track cost per successful spawn (including retries)
- Compare with manual retry cost (human time)

## Limitations

### Not a Quality Guarantee

**Fallback ensures availability, not quality:**
- Secondary model may be available but worse quality
- Monitor quality metrics per model
- Adjust priority if quality issues observed

### Transient vs Persistent Failures

**Fallback helps transient failures:**
- Provider outage → fallback works
- Rate limit → fallback works
- Persistent model incompatibility → fallback doesn't help

**Not solved:**
- All providers down → no fallback helps
- Task truly incompatible with all models → fail

### Coordination Overhead

**More attempts = more latency:**
- First model timeout (10s) + second attempt (2s) = 12s total
- Tune timeouts carefully
- Short timeouts = faster fallback but more false failures
- Long timeouts = fewer false failures but slower fallback

## Future Enhancements

### Parallel Attempts (Phase 3)

**Race multiple models simultaneously:**
- Start 2-3 models in parallel
- Use first successful response
- Cancel others
- Benefits: Lower latency, higher success rate
- Costs: More quota consumed

### Adaptive Timeouts

**Learn optimal timeout per model:**
- Track P95 latency per model
- Set timeout = P95 + buffer
- Adjust based on observed behavior

### Error Pattern Learning

**Classify errors more intelligently:**
- Learn which errors are transient
- Learn which errors indicate model mismatch
- Adjust retry strategy based on history

---

**Status:** Implemented, tested with mock errors  
**Rating:** 4/5 (pending real provider validation)  
**Impact:** Estimated 60-80% reduction in manual retry interventions
