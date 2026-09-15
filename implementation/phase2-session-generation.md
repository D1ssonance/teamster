# Phase 2.1: Session Router Generation

## Overview

Session router generation transforms a reference router (complete model catalog) 
into a session-specific router containing only currently available models, 
preserving fallback priority order.

## Architecture

```
Reference Router (immutable)
  ↓
API Smoke Tests (availability check)
  ↓
Session Router (filtered, transient)
  ↓
Agent Delegation (uses session router)
```

**Key Principle:** Separation of concerns
- Reference router = desired configuration (what should be used)
- Session router = runtime reality (what can be used now)

## Implementation Components

### 1. Session Generator Script

**Responsibilities:**
- Read reference router JSON
- Extract unique model IDs across all roles
- Test each model for availability
- Filter unavailable models from each role
- Preserve fallback order (priority)
- Generate session-specific router JSON
- Save availability state for monitoring

**Key Design Decisions:**

1. **Fail-closed generation**
   - If any role has zero available models → fail generation
   - Never emit a partial session router
   - Prevents silent degradation to defaults

2. **Priority preservation**
   - Models array order defines fallback priority
   - Filtering removes unavailable but keeps order
   - Primary model is always models[0]

3. **State tracking**
   - Save which models passed/failed availability test
   - Timestamp of last generation
   - Reference router hash for consistency check

### 2. API Smoke Test Framework

**Purpose:** Fast, bounded availability check (not quality evaluation)

**Test per model:**
- Send minimal deterministic request
- Expected: any valid completion (not checking quality)
- Timeout: short (e.g., 10s)
- Retry: none (availability test, not production request)

**Error classification:**
- 200/success → available
- 401/403 → auth issue → unavailable
- 429 → rate limited → unavailable (temporary)
- 503/504/timeout → provider down → unavailable
- 400/422 → protocol mismatch → unavailable
- Other → unavailable (fail-closed)

**Important:** Smoke test ≠ quality validation
- Smoke test: "can we reach this model?"
- Role fit: "is this model good for this role?"

### 3. Session Router Format

Same structure as reference router, but:
- Only contains available models
- Metadata includes generation timestamp
- State file tracks what was filtered
- No secrets or endpoints in exported JSON

## CLI Interface

```bash
# Dry-run (don't write session router)
python3 session_generator.py --dry-run

# Generate with custom output path
python3 session_generator.py --output /path/to/session-router.json

# Default (writes to configured session path)
python3 session_generator.py
```

## State File Format

```json
{
  "generatedAt": "2026-09-15T10:30:00Z",
  "referenceHash": "sha256:abc123...",
  "testedModels": {
    "provider-a/model-1": {
      "available": true,
      "testedAt": "2026-09-15T10:29:55Z"
    },
    "provider-b/model-2": {
      "available": false,
      "testedAt": "2026-09-15T10:29:58Z",
      "error": "timeout after 10s"
    }
  }
}
```

## Error Handling

### Generation Failures

**Any role empty after filtering:**
- Error: "Role 'coder' has zero available models"
- Action: Fail generation, keep previous session router
- Reason: Fail-closed prevents silent degradation

**Reference router not found:**
- Error: "Reference router not found at path"
- Action: Fail immediately
- Reason: Cannot generate without source

**Smoke test timeout:**
- Per-model timeout (e.g., 10s)
- Global timeout for all tests (e.g., 2min)
- Action: Mark timeouts as unavailable, continue testing others

### Retry Policy

**No automatic retry during smoke test**
- Smoke test is availability check, not production request
- Single attempt per model
- Reason: Fast feedback, avoid wasting quota

**Manual regeneration:**
- User triggers regeneration when availability changes
- Or scheduled refresh (see Phase 2.3)

## Privacy and Safety

**No secrets in session router:**
- Model IDs only, no credentials
- No endpoints, no tokens
- Use runtime credential references

**No sensitive logs:**
- Don't log full request/response bodies
- Log model IDs and status codes only
- State file stays in protected directory

**Atomic writes:**
- Write to temporary file first
- Atomic rename on success
- Previous session router preserved on failure

## Integration Points

**With reference router:**
- Read-only access to reference
- Validate schema before processing
- Hash reference for change detection

**With agent runtime:**
- Session router path configured in adapter
- Adapter loads session router at startup
- Manual reload or restart needed after regeneration

**With cooldown state:**
- Session generation is independent of cooldowns
- Availability ≠ not-on-cooldown
- Both mechanisms coexist

## Validation Checklist

Before using generated session router:

- [ ] All 10 roles have at least one model
- [ ] Models array order preserved (priority)
- [ ] No secrets or endpoints in JSON
- [ ] Quota groups preserved from reference
- [ ] Workflow settings preserved
- [ ] State file written successfully
- [ ] Reference hash matches current reference

## Limitations

**Mock Implementation:**
- Current implementation uses mock smoke tests
- Assumes all models available
- Placeholder for real API integration

**Before Production:**
- Replace mock with real API calls
- Configure actual provider endpoints
- Establish smoke test timeout values
- Define retry policy for generation failures

## Success Metrics

Track after real API integration:

**Availability accuracy:**
- False positives: model marked available but fails on use
- False negatives: model marked unavailable but would succeed
- Target: <5% error rate

**Generation speed:**
- Total time to test all models
- Target: <60s for 24 models

**Failure recovery:**
- Time to detect model outage
- Time to regenerate and reload
- Target: <5min manual, <15min automated (Phase 2.3)

## Future Enhancements (Phase 2.3)

- Auto-refresh mechanism (when to regenerate)
- Monitoring dashboard (real-time availability)
- Availability API (query current status)
- Webhook notifications (on availability change)
- A/B testing (multiple session variants)

---

**Status:** Implemented with mock smoke tests  
**Rating:** 4/5 (pending real API integration)  
**Next:** Replace mock with real provider API calls
