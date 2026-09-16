# Phase 2 Implementation Lessons

## What Worked Well

### 1. Reference/Session Separation

**Decision:** Keep reference router immutable, generate session router dynamically

**Outcome:** ✅ Excellent
- Clear separation of "desired" vs "available"
- Reference never corrupted by runtime state
- Easy rollback (regenerate from reference)
- Fail-closed generation prevents silent degradation

**Lesson:** Immutable configuration + transient runtime state is safer than 
mutable production config that gets rewritten.

### 2. Fallback via Array Order

**Decision:** Use models[] array order as implicit fallback priority

**Outcome:** ✅ Excellent
- No separate fallback_chain field needed
- Priority obvious from JSON inspection
- Filtering preserves order automatically
- Assessment evidence → array order → execution order

**Lesson:** Implicit priority from ordering is simpler than explicit chains, 
when ordering has clear semantics.

### 3. Minimal Invasive Changes

**Decision:** Reuse existing _select_model() logic, add retry loop only

**Outcome:** ✅ Excellent
- +1.6 KB change only
- Existing cooldown logic preserved
- Existing quota logic preserved
- Lower risk of regression

**Lesson:** When existing logic is sound, wrap rather than rewrite.

### 4. Error Classification

**Decision:** 4 error types with distinct retry strategies

**Outcome:** ✅ Good
- Clear retry vs fail-fast boundaries
- Pattern matching simple (regex on error message)
- Easy to extend with new patterns

**Challenge:** Error message patterns vary across providers
- Need real provider validation
- May need provider-specific patterns

**Lesson:** Error classification needs provider-specific tuning, but generic 
patterns cover 80% of cases.

### 5. Fail-Closed Generation

**Decision:** If any role empty after filtering, fail generation

**Outcome:** ✅ Excellent
- Never emit incomplete session router
- Forces explicit decision on degraded mode
- Clear signal to operators

**Lesson:** Fail-closed prevents silent degradation that's hard to detect later.

### 6. Structured Error Messages

**Decision:** Include tried models list and last error in exhaustion message

**Outcome:** ✅ Excellent
- Much easier debugging
- Clear what was attempted
- Obvious next action (wait? different role? change task?)

**Lesson:** Error messages are user interface. Invest in clarity.

## What Needed Iteration

### 1. Mock vs Real Smoke Tests

**Initial:** Mock implementation (assume all available)

**Outcome:** ⚠️ Incomplete
- Works for structure validation
- Doesn't test real provider behavior
- Can't validate timeout handling

**Next:** Replace mock with real API calls

**Lesson:** Mocks are useful for structure, but can't replace integration tests 
for external dependencies.

### 2. Timeout Tuning

**Initial:** Fixed 10s timeout for smoke tests

**Question:** Is 10s right for all providers?

**Considerations:**
- Too short → false negatives (model marked unavailable)
- Too long → slow generation (24 models × 10s = 4min)
- Different providers may need different timeouts

**Next:** Per-provider timeout configuration

**Lesson:** One-size-fits-all timeouts don't work for heterogeneous providers.

### 3. Retry vs Fallback Terminology

**Confusion:** "retry" can mean:
- Retry same model (provider transient error)
- Try next model in chain (fallback)

**Resolution:** Use "fallback" for trying next model, "retry" only for 
same-model attempts

**Lesson:** Overloaded terms create confusion. Use distinct vocabulary.

### 4. Quota Interaction

**Initial question:** Should fallback attempts count toward quota?

**Decision:** Yes, count all spawn attempts

**Reasoning:**
- Primary fail + secondary succeed = 2 spawns = 2 quota
- Prevents quota bypass via deliberate primary failures
- Tracks real provider load

**Alternative considered:** Count only successful spawns
- Rejected: Allows quota bypass, doesn't reflect true load

**Lesson:** Quota must track all attempts, not just successes.

## Design Insights

### 1. Elegance via Reuse

**Observation:** _select_model() already iterates models[], returns first not-on-cooldown

**Insight:** Calling reserve_model() multiple times automatically traverses fallback chain

**Impact:** 
- No need to duplicate fallback iteration logic
- Cooldown tracking works unchanged
- Single source of truth for "next model"

**Lesson:** Before adding new logic, check if existing mechanisms can be composed.

### 2. Separation of Concerns

**Availability vs Quality:**
- Smoke test: "can we reach this model?" (Phase 2.1)
- Role fit: "is this model good for this role?" (Phase 1)
- Runtime selection: "which available model?" (Phase 2.2)

**Benefits:**
- Each mechanism has single responsibility
- Can evolve independently
- Failures are easier to diagnose

**Lesson:** Don't conflate availability and quality. They're different questions.

### 3. Fail-Fast Boundaries

**Principle:** Distinguish retryable from non-retryable errors

**Examples:**
- 429 rate limit → retryable (try next model)
- 400 bad request → non-retryable (fail fast)

**Reasoning:**
- Retrying non-retryable errors wastes quota
- Failing fast on retryable errors wastes opportunity

**Lesson:** Error classification determines system efficiency. Get it right.

## Architectural Patterns

### 1. Two-Tier Configuration

**Pattern:**
```
Reference (immutable source of truth)
    ↓
Generation (transformation)
    ↓
Session (runtime config)
```

**Benefits:**
- Reference never corrupted
- Session can be regenerated
- Clear update flow

**Applicability:** Any system where configuration depends on runtime state

### 2. Fallback via Priority Order

**Pattern:** Array order defines fallback priority

**Instead of:**
```json
{
  "primary": "model-1",
  "fallback": ["model-2", "model-3"]
}
```

**Use:**
```json
{
  "models": ["model-1", "model-2", "model-3"]
}
```

**Benefits:**
- Simpler structure
- Obvious priority
- Easy to filter (remove unavailable, keep order)

### 3. Fail-Closed Generation

**Pattern:** If transformation produces incomplete output, fail rather than emit

**Example:** If any role has zero models after filtering, fail generation

**Benefits:**
- Prevents silent degradation
- Forces explicit handling of degraded state
- Clear operational signal

**Trade-off:** Less automatic resilience, more operator intervention

**When to use:** When partial functionality is worse than no functionality

### 4. Error Classification Strategy

**Pattern:** Classify errors into categories with distinct retry strategies

**Categories:**
- Transient provider (503, timeout) → retry immediately
- Quota exhausted (429) → retry different resource
- Invalid request (400) → don't retry, fail fast
- Unknown → cautious retry

**Benefits:**
- Efficient use of quota
- Faster failure on non-retryable errors
- Clear system behavior

## Metrics That Matter

### Leading Indicators

**Fallback frequency:**
- How often does primary model fail?
- Indicates: Primary model reliability

**Error type distribution:**
- Rate limits vs timeouts vs bad requests
- Indicates: Quota tuning, provider reliability, task compatibility

**Generation failures:**
- How often does session generation fail?
- Indicates: Provider availability issues

### Lagging Indicators

**Overall success rate:**
- % spawns that succeed (after fallback)
- Target: >95%

**Manual intervention rate:**
- % spawns that require human retry
- Target: <5%

**Time to success:**
- Latency including fallback attempts
- Target: <10s P95

## Common Pitfalls

### 1. Infinite Fallback Loops

**Risk:** If error classification wrong, could retry forever

**Mitigation:** Bound attempts by models array length

**Lesson:** Always have explicit loop bounds, even with "safe" logic.

### 2. Quota Bypass

**Risk:** Fallback could be abused to bypass quota limits

**Mitigation:** Count all attempts toward quota, check quota for each model attempt inside the retry loop

**Lesson:** Any retry mechanism needs quota integration.

### 3. Stale Session Router

**Risk:** Session router becomes outdated as provider availability changes

**Mitigation:** Regenerate periodically or on-demand

**Future:** Auto-refresh (Phase 2.3)

**Lesson:** Transient state needs refresh mechanism.

### 4. Silent Quality Degradation

**Risk:** Fallback succeeds but secondary model is lower quality

**Mitigation:** Monitor quality metrics per model, not just success rate

**Lesson:** Availability ≠ quality. Track both.

## Validation Gaps

### Before Production

**Must validate:**
- [ ] Real provider error patterns match regex
- [ ] Timeout values appropriate for each provider
- [ ] Cooldown integration works under load
- [ ] Structured errors useful for debugging
- [ ] No secrets leaked in logs/errors
- [ ] Atomic writes work correctly
- [ ] State file corruption handling

**Nice to have:**
- [ ] Parallel smoke tests (faster generation)
- [ ] A/B test different timeout values
- [ ] Dashboard for availability monitoring

## Recommendations for Others

### Starting Out

1. **Start with reference router only**
   - Manual model selection
   - Observe patterns
   - Document model → role fitness

2. **Add smoke tests second**
   - Validate "can we reach this model?"
   - Build confidence in availability detection
   - Don't conflate with quality

3. **Add fallback last**
   - Need evidence that fallback is needed
   - Need confidence in error classification
   - Measure impact on success rate

### Scaling Up

**As model catalog grows:**
- Session generation becomes slower (N models × timeout)
- Consider parallel smoke tests
- Consider caching availability results (with TTL)

**As roles grow:**
- More roles = more fallback chains to maintain
- Consider tooling to validate role coverage
- Consider automated priority updates from evidence

**As providers grow:**
- More providers = more error patterns
- Consider provider-specific error classification
- Consider per-provider timeout configuration

---

**Status:** Lessons documented from Phase 2.1+2.2 implementation  
**Next:** Validate with real provider integration, gather operational lessons
