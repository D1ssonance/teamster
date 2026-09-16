# Phase 2.2: Fallback Execution Logic

## Overview

This document describes Phase 2.2 implementation: automatic fallback through model chains when spawn attempts fail.

**Status**: ✅ Implemented with critical bug fix

**Canonical Implementation**: See `fallback-execution-pseudocode.md` for the corrected pseudocode with full test scenarios.

## Architecture Integration

Phase 2.2 adds retry logic around the existing spawn mechanism:

```
User Request
    ↓
Role Selection (from session router)
    ↓
Model Chain Loaded (e.g., [model-a, model-b, model-c])
    ↓
╔════════════════════════════════════════════════════╗
║  FALLBACK EXECUTION LOOP (Phase 2.2)              ║
║                                                    ║
║  for model_index in models:                       ║
║    ↓                                               ║
║    Check Cooldown (rate limit state)              ║
║    ↓                                               ║
║    Check Quota (available starts)                 ║
║    ↓                                               ║
║    Try Spawn (existing _rlm mechanism)            ║
║    ↓                                               ║
║    Success? → Return child handle                 ║
║    ↓                                               ║
║    Classify Error:                                ║
║    • AUTH → Fail immediately                      ║
║    • CAPACITY → Try next model                    ║
║    • RATE_LIMIT → Mark cooldown, try next        ║
║    • PROVIDER → Try next model                    ║
║    • UNKNOWN → Try next model                     ║
║    ↓                                               ║
║  All models exhausted? → Raise final error        ║
╚════════════════════════════════════════════════════╝
```

## Design Decisions

### 1. Minimal Changes Approach

**Decision**: Add retry loop around existing `_rlm()` call, preserve `_select_model()` and `_reserve_model()` logic.

**Rationale**: Reduce integration risk by keeping existing quota and cooldown mechanisms unchanged.

**Trade-off**: Required careful validation of interaction between new loop and existing selection logic.

### 2. Explicit Model Index Tracking

**Decision**: Track tried model indices in a set to prevent repeated attempts on the same model.

**Rationale**: Critical bug fix - without tracking, loop could select the same available model repeatedly on PROVIDER/UNKNOWN errors.

**Corrected Pattern** (simplified):
```python
tried_models = []  # Track by index, not set
for model_index in range(len(role_spec.models)):
    model = role_spec.models[model_index]
    
    # Skip already tried models
    if model_index in tried_models:
        continue
    
    # Check availability (cooldown, quota)
    if not is_available(model):
        tried_models.append(model_index)
        continue
    
    # Try spawn
    tried_models.append(model_index)
    try:
        result = spawn_with_model(model, task)
        return result  # Success!
    except Error as e:
        error_type = classify_error(e)
        # Handle by error type, continue to next model
        continue

# All models exhausted
raise CapacityError("No available models")
```

**See**: `ERRATA.md` for detailed bug description and fix validation, `fallback-execution-pseudocode.md` for complete implementation with error handling.

### 3. Error Classification

**Decision**: Classify errors into five categories to determine retry behavior.

**Categories**:
- **AUTH** (401/403): Don't retry, fail immediately
- **CAPACITY** (quota): Try next model
- **RATE_LIMIT** (429): Mark cooldown, try next model
- **PROVIDER** (50x, connection): Try next model
- **UNKNOWN**: Try next model (configurable policy)

**See**: `fallback-execution-pseudocode.md` for classification logic and error handling details.

### 4. Fail-Fast on Auth Errors

**Decision**: Authentication and authorization errors abort the entire fallback chain.

**Rationale**: Auth errors indicate misconfiguration, not transient failure. Retrying wastes time and quota.

**Implementation**: `classify_error()` detects 401/403 and returns AUTH category, loop breaks immediately.

### 5. State Persistence for Cooldowns

**Decision**: Cooldown state persists to filesystem, survives process restart.

**Rationale**: Rate limits apply across process lifetime; in-memory state would reset on restart and trigger repeated rate limiting.

**Format**: JSON file with `{model: {role: {expires_at: timestamp}}}`

**See**: `fallback-execution-pseudocode.md` for state file operations.

## Implementation Size

- **New code**: ~43 lines (retry loop + error classification)
- **Preserved**: ~90% of existing spawn logic
- **Modified**: Error handling in `_run()` method

**Alternative considered**: Full rewrite of spawn logic (~150 lines) - rejected due to higher integration risk.

## Validation

### Critical Bug Fix

**Bug**: Original pseudocode could retry the same model repeatedly.

**Fix**: Added explicit `tried_models` tracking.

**Verification**: Regression tests in `ERRATA.md` demonstrate the fix prevents repeated same-model attempts.

### Test Scenarios

Five test scenarios validate fallback behavior:

1. **All models succeed**: First model used, no fallback
2. **First fails capacity**: Falls back to second model
3. **Rate limit mid-chain**: Skips rate-limited model, uses next
4. **Provider errors**: Tries all models in chain
5. **Auth error**: Stops immediately, no fallback

**See**: `fallback-execution-pseudocode.md` for complete test scenario descriptions.

## Configuration Integration

### Role Configuration

Each role specifies its model chain:

```json
{
  "roles": {
    "coder": {
      "models": ["primary-model", "fallback-model-1", "fallback-model-2"],
      "quotaGroup": "devx",
      "maxFallbackAttempts": 3
    }
  }
}
```

**Note**: `maxFallbackAttempts` field exists in template but is not yet enforced in pseudocode (uses `len(models)` instead). See Issue #6 in review findings.

### State Files

Fallback execution uses two state files:

1. **Cooldown state**: `~/.router-state/cooldowns.json`
2. **Quota state**: `~/.router-state/quota.json`

**Location configurable** via environment or config file.

## Error Reporting

When all models in chain fail, final error includes:

- Original objective
- Role requested
- All models attempted
- Error for each attempt
- Cooldown states
- Quota states

**Example**:

```
Failed to spawn agent for role 'coder' after trying 3 models:
  • primary-model: RATE_LIMIT (on cooldown until 2025-01-15 23:45:00)
  • fallback-model-1: PROVIDER (connection timeout)
  • fallback-model-2: CAPACITY (quota exhausted)

Quota state: devx group 0/3 available
Cooldown state: primary-model cooling until 23:45:00
```

## Known Limitations

### 1. Quota Check Placement

**Issue**: Quota check in pseudocode happens on every attempt and reserves a start slot.

**Impact**: Failed reservations are not released in pseudocode; unclear if quota accounts for all attempts or just successful ones.

**Status**: Documented as gap, needs clarification in next iteration.

**See**: Issue #3 in review findings.

### 2. Concurrency Not Specified

**Issue**: Concurrent access to cooldown/quota state files not addressed.

**Impact**: Race conditions possible with multiple router instances.

**Status**: Documented as gap, needs locking or atomic operations.

**See**: Issue #7 in review findings.

### 3. Error Classification Simplistic

**Issue**: Uses string matching for error detection, no structured exception types.

**Impact**: Can misclassify errors if message contains misleading substrings.

**Status**: Works for pilot, needs typed classification for production.

**See**: Issue #5 in review findings.

## Next Steps

### Immediate (Pre-Production)

1. Enforce `maxFallbackAttempts` in pseudocode loop
2. Clarify quota reservation semantics (per-attempt vs atomic)
3. Add structured error classification with HTTP status codes
4. Add 401/403 explicit handling in classifier

### Future (Production Hardening)

5. Add concurrency/locking for state files
6. Add Retry-After header parsing for 429
7. Add cancellation/deadline support
8. Add observability fields for monitoring

## References

- **Canonical Implementation**: `fallback-execution-pseudocode.md` (corrected version with tests)
- **Bug Fix Documentation**: `ERRATA.md` (critical bug and regression tests)
- **Architecture**: `ARCHITECTURE.md` (reference/session two-tier design)
- **Configuration**: `reference-router.template.json` (role and quota configuration)
- **Results**: `RESULTS-AND-LESSONS.md` (implementation lessons and metrics)
