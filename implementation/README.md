# Phase 2 Implementation Documentation

This directory contains detailed documentation of Phase 2 implementation:
session router generation and automatic fallback execution logic.

## Documents

### [phase2-session-generation.md](./phase2-session-generation.md)
Complete guide to Phase 2.1: Session Router Generation
- Architecture: Reference → Smoke Test → Session Router
- API smoke test framework
- Fail-closed generation strategy
- State tracking and monitoring
- CLI interface and usage
- Validation checklist

### [phase2-fallback-execution.md](./phase2-fallback-execution.md)
Complete guide to Phase 2.2: Fallback Execution Logic
- Problem statement and solution
- 4-category error classification
- Retry strategy per error type
- Integration with cooldowns and quotas
- Monitoring metrics
- Operational considerations

### [phase2-lessons-learned.md](./phase2-lessons-learned.md)
Lessons and insights from implementation
- What worked well
- What needed iteration
- Design insights
- Architectural patterns validated
- Common pitfalls and how to avoid them
- Recommendations for others

### [fallback-execution-pseudocode.md](./fallback-execution-pseudocode.md)
Anonymized pseudocode examples
- Core fallback pattern
- Error classification logic
- State management
- Usage examples
- Error flow scenarios
- Configuration examples

## Quick Summary

**Phase 2.1 (Session Generation):**
- Transforms reference router into session-specific router
- Tests model availability via API smoke tests
- Filters unavailable models, preserves fallback order
- Fail-closed: never emit partial router
- Output: session-router.json + session-router-state.json

**Phase 2.2 (Fallback Execution):**
- Automatic retry through model fallback chain
- 4 error types with distinct strategies:
  - Rate limit (429) → cooldown + try next
  - Provider error (503/timeout) → try next immediately
  - Bad request (400) → fail fast
  - Unknown → cautiously try next
- Structured errors with tried models list
- Minimal code change (+1.6 KB)

## Architecture

```
┌──────────────────────┐
│  Reference Router    │  (immutable, desired state)
│  - All models        │
│  - All roles         │
└──────────┬───────────┘
           │
           ▼
┌──────────────────────┐
│  Session Generator   │
│  - API smoke tests   │
│  - Filter unavail.   │
│  - Fail-closed       │
└──────────┬───────────┘
           │
           ▼
┌──────────────────────┐
│  Session Router      │  (transient, runtime state)
│  - Available models  │
│  - Same structure    │
└──────────┬───────────┘
           │
           ▼
┌──────────────────────┐
│  Agent Spawn         │
│  - Select model      │
│  - Retry on error    │
│  - Fallback chain    │
└──────────────────────┘
```

## Key Principles

1. **Separation of concerns**
   - Reference = desired configuration (what should be used)
   - Session = runtime reality (what can be used now)
   - Spawn = execution with fallback (how to use it)

2. **Fail-closed at every level**
   - Generation: any role empty → fail
   - Spawn: bad request → fail fast
   - Quota: exhausted → fail before trying

3. **Priority preservation**
   - Array order = fallback priority
   - Filtering preserves order
   - Selection respects order + cooldowns

4. **Structured observability**
   - Generation state: what was tested, what failed
   - Spawn errors: what was tried, why failed
   - Metrics: fallback rate, success rate, latency

## Status

**Implementation:** Complete with mock smoke tests  
**Rating:** 4/5 (pending real API integration)  
**Next:** Replace mock with real provider API calls

## Validation Checklist

Before production:
- [ ] Replace mock smoke tests with real API
- [ ] Validate error patterns with actual providers
- [ ] Tune timeout values per provider
- [ ] Test cooldown integration under load
- [ ] Verify no secrets in logs/errors/state
- [ ] Test atomic write behavior
- [ ] Measure fallback impact (before/after)
- [ ] Monitor quality per model

## Success Metrics

**Phase 2.1:**
- Generation success rate >95%
- Generation time <60s for 24 models
- False positive/negative <5%

**Phase 2.2:**
- Fallback success rate >80%
- Manual intervention rate <5%
- Average models per spawn ~1.2
- P95 latency <10s (including fallback)

## Future Work (Phase 2.3)

- Auto-refresh mechanism (when to regenerate)
- Monitoring dashboard (availability visibility)
- Availability API (query current state)
- Webhook notifications (on availability change)
- Parallel smoke tests (faster generation)

---

See also: [../RESULTS-AND-LESSONS.md](../RESULTS-AND-LESSONS.md) for project-wide lessons
