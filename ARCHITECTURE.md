# Architecture Overview

This document provides a visual overview of the agent router architecture
across all phases.

## System Components

```
┌─────────────────────────────────────────────────────────────────┐
│                     AGENT ROUTER SYSTEM                          │
└─────────────────────────────────────────────────────────────────┘

┌──────────────────────┐
│  Phase 1: Reference  │
│  Router              │
├──────────────────────┤
│ • 10 semantic roles  │
│ • Model catalog      │
│ • Quota groups       │
│ • Cooldown config    │
│ • Priority order     │
│                      │
│ Status: Immutable    │
│ Format: JSON         │
│ Location: Protected  │
└──────────┬───────────┘
           │
           │ reads
           ▼
┌──────────────────────┐
│  Phase 2.1: Session  │
│  Generator           │
├──────────────────────┤
│ • Read reference     │
│ • Extract models     │
│ • Smoke test each    │
│ • Filter unavailable │
│ • Generate session   │
│                      │
│ Trigger: Manual      │
│ Duration: ~30-60s    │
│ Output: 2 files      │
└──────────┬───────────┘
           │
           │ generates
           ▼
┌──────────────────────┐
│  Session Router      │
├──────────────────────┤
│ • Available models   │
│ • Same structure     │
│ • Filtered roles     │
│ • Metadata included  │
│                      │
│ Status: Transient    │
│ Lifetime: Until next │
│ Regeneration: Manual │
└──────────┬───────────┘
           │
           │ loaded by
           ▼
┌──────────────────────┐
│  Phase 2.2: Agent    │
│  Spawn with Fallback │
├──────────────────────┤
│ • Select role        │
│ • Try models in      │
│   priority order     │
│ • Classify errors    │
│ • Auto fallback      │
│ • Track cooldowns    │
│                      │
│ Trigger: Per spawn   │
│ Duration: ~2-20s     │
│ Output: Agent handle │
└──────────────────────┘
```

## Data Flow

### Session Generation Flow

```
Reference Router (JSON)
    │
    ├─→ Parse & validate schema
    │
    ├─→ Extract unique models
    │   [model-1, model-2, ..., model-N]
    │
    ├─→ For each model:
    │   ├─→ Smoke test API
    │   ├─→ 200 OK? → mark available
    │   └─→ Error?  → mark unavailable
    │
    ├─→ Filter each role.models[]
    │   └─→ Keep only available, preserve order
    │
    ├─→ Validate all roles non-empty
    │   ├─→ Any empty? → FAIL (fail-closed)
    │   └─→ All good?  → Continue
    │
    ├─→ Write session-router.json
    │   └─→ Atomic write (temp → rename)
    │
    └─→ Write session-router-state.json
        └─→ Availability + timestamps
```

### Agent Spawn Flow

```
spawn(role="coder", task="...")
    │
    ├─→ Load session router
    │
    ├─→ Get role.models[] (available only)
    │
    ├─→ Check quota group capacity
    │   ├─→ Full? → Error
    │   └─→ OK?   → Continue
    │
    └─→ Retry Loop (bounded by len(models)):
        │
        ├─→ Select next available model
        │   └─→ First not on cooldown
        │
        ├─→ Try spawn with model
        │   │
        │   ├─→ SUCCESS → Return result ✓
        │   │
        │   └─→ ERROR → Classify:
        │       │
        │       ├─→ RATE_LIMIT (429)
        │       │   ├─→ Mark cooldown
        │       │   └─→ Continue to next model
        │       │
        │       ├─→ PROVIDER_ERROR (503/timeout)
        │       │   └─→ Continue immediately
        │       │
        │       ├─→ BAD_REQUEST (400)
        │       │   └─→ FAIL FAST ✗
        │       │
        │       └─→ UNKNOWN
        │           └─→ Continue cautiously
        │
        └─→ All models tried?
            └─→ Structured error with tried list
```

## State Management

### Cooldown State

```
{
  "cooldowns": {
    "provider-a/model-1": {
      "until": <unix_timestamp>,
      "reason": "rate_limit"
    }
  }
}
```

**Updated:**
- On rate limit (429) detection
- Persisted atomically to disk
- Read on every model selection

**Cleared:**
- Automatically when timestamp passes
- Manual clear (admin only)

### Quota State

```
{
  "starts": {
    "quota-group-name": [
      <timestamp_1>,
      <timestamp_2>,
      <timestamp_3>
    ]
  }
}
```

**Updated:**
- On every spawn attempt (success or fail)
- Sliding window pruned on read

**Enforced:**
- Before attempting model
- Sliding window calculation

### Session State

```
{
  "generatedAt": "<timestamp>",
  "referenceHash": "sha256:...",
  "testedModels": {
    "provider-a/model-1": {
      "available": true,
      "testedAt": "<timestamp>"
    },
    "provider-b/model-2": {
      "available": false,
      "testedAt": "<timestamp>",
      "error": "timeout after 10s"
    }
  }
}
```

**Updated:**
- On every session generation
- Includes test results
- Timestamped for staleness detection


## Concurrency & Thread Safety

### Thread Safety Model

**Single-Writer Assumption**: The router assumes a single writer per state file. Multiple concurrent router instances sharing the same `stateFile` require external coordination.

### State File Access Patterns

```
Read operations:
  • is_on_cooldown() - reads cooldown timestamps
  • check_quota() - reads start history within time window
  
Write operations:
  • set_cooldown() - writes new cooldown timestamp
  • record_start() - appends start timestamp to quota group
```

### Safe Concurrency Patterns

**Option 1: Single Router Instance (Recommended)**
- One router process serves all spawn requests
- State mutations are serialized within the process
- Simplest and safest approach

**Option 2: File Locking (Advanced)**
```python
import fcntl

def with_state_lock(state_file_path):
    """Advisory file lock for concurrent router instances"""
    with open(state_file_path, 'r+') as f:
        fcntl.flock(f.fileno(), fcntl.LOCK_EX)
        try:
            # Read, modify, write state
            yield f
        finally:
            fcntl.flock(f.fileno(), fcntl.LOCK_UN)
```

**Option 3: Separate State Files**
- Each router instance uses its own state file
- Quota enforcement becomes per-instance, not global
- Acceptable if quota limits are generous

### Race Conditions

**Quota Check Race**:
```
Time T0: Router A checks quota → 5/6 used, OK
Time T1: Router B checks quota → 5/6 used, OK
Time T2: Router A spawns → 6/6 used
Time T3: Router B spawns → 7/6 OVER LIMIT
```

**Mitigation**: File locking or atomic check-and-increment operations.

**Cooldown Race**:
```
Time T0: Router A sets cooldown for model X
Time T1: Router B reads stale state (no cooldown)
Time T2: Router B attempts model X → rate limit error
```

**Mitigation**: Cooldown buffer (`cooldownBufferSeconds`) provides safety margin.

### Crash Recovery

**State File Corruption**:
- Corrupted JSON → router cannot start
- Solution: Validate state on load, fall back to empty state
- Keep backup: `state.json.backup`

**Orphaned Cooldowns**:
- Process crash leaves cooldown active
- Manual intervention: delete cooldown or wait for expiry

**Stale Start Records**:
- Old timestamps outside window accumulate
- Solution: Prune timestamps older than max window on load

### Production Recommendations

1. **Use single router instance** when possible
2. **Implement file locking** if multiple instances required
3. **Monitor state file size** - prune old data periodically
4. **Validate state on load** - handle corruption gracefully
5. **Log all state mutations** for debugging race conditions

## Error Flow

### Generation Errors

```
Reference Router
    │
    ├─→ Not found
    │   └─→ FAIL: Cannot generate
    │
    ├─→ Invalid schema
    │   └─→ FAIL: Validate reference first
    │
    ├─→ Model smoke test timeout
    │   └─→ Mark unavailable, continue others
    │
    └─→ Role has zero available models
        └─→ FAIL: Fail-closed, don't emit partial
```

### Spawn Errors

```
Spawn Attempt
    │
    ├─→ Quota exhausted
    │   └─→ FAIL: Wait for quota window
    │
    ├─→ All models on cooldown
    │   └─→ FAIL: Wait for cooldown expiry
    │
    ├─→ Model error (429/503/400/unknown)
    │   ├─→ Retryable? → Try next model
    │   └─→ Non-retryable? → FAIL FAST
    │
    └─→ All models exhausted
        └─→ FAIL: Structured error with tried list
```

## Configuration Hierarchy

```
Reference Router (source of truth)
  │
  ├─→ roles {}
  │   └─→ [role-name]
  │       ├─→ models: [...]        # Priority order
  │       ├─→ quotaGroup: "..."
  │       └─→ metadata: {}
  │
  ├─→ quotaGroups {}
  │   └─→ [group-name]
  │       ├─→ maxStarts: N
  │       ├─→ windowSeconds: N
  │       └─→ cooldownSeconds: N
  │
  ├─→ maxConcurrentPerProvider {}
  │   └─→ [provider]: N
  │
  └─→ workflow {}
      ├─→ reviewerIndependence: "..."
      └─→ activation: "..."

Session Router (runtime filtered copy)
  │
  └─→ Same structure, but:
      ├─→ models[] filtered to available only
      ├─→ metadata includes generation info
      └─→ rest preserved from reference
```

## Timing Diagram

```
T=0s    Reference Router created manually
        │
        └─→ Validated offline
            │
            └─→ Committed to protected location

T=startup  Session Generation triggered
        │
        ├─→ T+0s:   Read reference router
        ├─→ T+1s:   Start smoke tests (parallel possible)
        ├─→ T+30s:  All tests complete
        ├─→ T+31s:  Filter models
        ├─→ T+32s:  Validate non-empty
        └─→ T+33s:  Write session router + state

T=spawn    Agent spawn requested
        │
        ├─→ T+0s:   Check quota
        ├─→ T+0.1s: Select model
        ├─→ T+0.2s: Attempt spawn
        │   │
        │   ├─→ SUCCESS → T+2s (typical)
        │   │
        │   └─→ ERROR → classify
        │       ├─→ T+1s:   Try model 2
        │       └─→ T+3s:   Success or fail

T=cooldown Automatic cooldown expiry
        │
        └─→ Model becomes available again
            (no action needed, automatic)
```

## Security Boundaries

```
┌─────────────────────────────────────┐
│  Protected Zone                     │
│  • Reference router                 │
│  • Provider credentials             │
│  • State files (cooldown, quota)    │
│  • Session generation logs          │
│                                     │
│  Access: Admin only                 │
│  Network: Internal only             │
└─────────────────────────────────────┘
        │
        │ reads (no write)
        ▼
┌─────────────────────────────────────┐
│  Runtime Zone                       │
│  • Session router (filtered copy)   │
│  • Agent spawn logic                │
│  • Error classification             │
│                                     │
│  Access: Agent runtime              │
│  Network: Both internal/external    │
└─────────────────────────────────────┘
        │
        │ uses (opaque IDs only)
        ▼
┌─────────────────────────────────────┐
│  External Zone                      │
│  • Model providers                  │
│  • API gateways                     │
│                                     │
│  Access: Via credentials            │
│  Network: External                  │
└─────────────────────────────────────┘
```

## Key Principles

1. **Immutability**: Reference router never modified at runtime
2. **Fail-closed**: Incomplete state causes failure, not degradation
3. **Priority preservation**: Array order maintained through all transforms
4. **Bounded retry**: Loop terminates at models.length iterations
5. **Structured errors**: Always include context (tried models, reason)
6. **State persistence**: Atomic writes, corruption detection
7. **Privacy**: No secrets in session router or logs

---

See [README.md](./README.md) for full documentation.
