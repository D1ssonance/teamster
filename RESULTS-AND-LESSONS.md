# Обезличенные результаты и lessons learned

## Что подтвердилось

- Semantic role routing лучше прямого выбора модели по памяти.
- Приоритетные fallback chains полезны, если порядок и причины выбора зафиксированы.
- API smoke быстро отделяет route/auth/rate-limit/incompatibility от quality.
- Native role fixtures часто информативнее API/tool tests для agent work.
- Отдельные debugger/fixer fixtures выявляют nonlocal state и transaction defects, которые не видны в обычном chat smoke.
- Immutable reference + transient availability session layer безопаснее постоянной перезаписи production config.
- Fail-closed all-role generation предотвращает запуск роутера с тихо восстановленными defaults.
- Exact loader roundtrip нужен: неполная role map может воскресить нежелательные default models.
- Cache должен иметь TTL, atomic writes, lock ownership, corruption/future-time rejection и защищённые пути.
- Shared cooldown нельзя обходить флагом force; probe budget и admission quota — разные механизмы.
- Independent reviewer нужен после успешной реализации, но reviewer не заменяет native verification.
- Результат агента без receipt не является доказательством.
- Interrupted coordination нельзя автоматически трактовать как model failure.

## Что не следует обещать

- маленькая synthetic выборка не доказывает универсальный рейтинг;
- API tool incompatibility не доказывает native-agent inability;
- text probe не доказывает vision capability;
- одна роль не наследует автоматически качество другой роли;
- fallback chain не гарантирует reviewer independence;
- production activation не должна быть побочным эффектом успешных тестов;
- nested child inheritance environment нужно проверять отдельно;
- path preflight без OS primitives не устраняет все TOCTOU races.

## Надёжный порядок улучшений

1. Сначала документированный API и фактический loader contract.
2. Затем offline fake-gateway tests.
3. Затем bounded smoke.
4. Затем role-specific deterministic fixtures.
5. Затем независимый review.
6. Затем отдельный approval на reference update или activation.

## Операционный принцип

Разделяйте качество, доступность, скорость, безопасность и координацию. Не превращайте отсутствие ответа, rate limit или падение инфраструктуры в нулевую оценку модели.

## Historical aggregate evidence (not a ranking)

An anonymized development campaign covered 24 candidates: 99 text cases / 116
HTTP attempts, 54 tool cases / 92 attempts, and 54 native sessions across nine
candidates. Nine saved fixes passed their hidden tests; diagnosis tasks produced
seven passes, one timeout and one incorrect diagnosis. These are historical
small-sample observations, not current availability or cross-role qualification.

The local offline regression suite grew from 95 to 125 passing tests, including
30 session-generator tests. A separate reference validator had 19 passing tests;
14 documented adapter-contract tests passed. An older broader adapter suite had
known failures/errors, so these successes never established universal runtime health.
The portable package does NOT include that executable harness or its private data;
these counts describe prior verification, not tests shipped in this directory.

A missing/empty freeze manifest was found in a native campaign. Inputs were checked
against a prior baseline instead; the limitation remained explicit. Some grading
rubrics were ambiguous, and interpretations were kept separate from raw scores.
Reviewers twice understated safety findings. Root required fixes for state override,
cache collisions and directory aliases instead of accepting the approval label.
Repeated missing handoffs delayed delivery; bounded escalation to direct root work
is preferable to endless replacement delegation.


## Phase 2: Session Generation and Fallback Execution

### What Validated

- **Reference/Session separation is safer than mutable production config**
  - Reference router stays immutable
  - Session router regenerated from reference
  - Fail-closed generation prevents silent degradation
  - Clear rollback path (regenerate from reference)

- **Implicit fallback via array order simpler than explicit chains**
  - `models: [primary, secondary, tertiary]` order defines priority
  - No separate `fallback_chain` field needed
  - Filtering preserves order automatically
  - Obvious priority from JSON inspection

- **Error classification enables efficient retry**
  - Rate limit (429) → cooldown + try next model
  - Provider error (503/timeout) → try next immediately
  - Bad request (400) → fail fast, don't waste attempts
  - Unknown → cautiously try next
  - 4 categories with distinct strategies sufficient

- **Reusing existing logic reduces risk**
  - Existing `_select_model()` iterates through models array
  - Calling it multiple times traverses fallback chain automatically
  - Preserved cooldown tracking, quota enforcement
  - Minimal code change (+1.6 KB) reduces regression risk

- **Structured error messages improve debugging**
  - List tried models in exhaustion error
  - Include last error for diagnosis
  - Clear next action (wait? different role? change task?)
  - Much faster debugging vs generic "capacity error"

- **Fail-closed generation forces explicit degradation handling**
  - Zero models in any role → fail generation
  - Never emit partial session router
  - Operator alerted immediately
  - Prevents silent quality degradation

### What Required Tuning

- **Timeout values need provider-specific configuration**
  - One-size-fits-all (10s) may be too short/long
  - Different providers have different latencies
  - Per-provider timeout configuration needed
  - Balance: false negatives vs generation speed

- **Error patterns vary across providers**
  - Generic regex covers ~80% of cases
  - Provider-specific patterns needed for edge cases
  - Real provider validation required
  - May need per-provider error classifier

- **Mock smoke tests insufficient for validation**
  - Good for structure validation
  - Can't test real provider behavior
  - Can't validate timeout handling
  - Must replace with real API integration before production

- **Quota accounting must include all attempts**
  - Primary fail + secondary succeed = 2 quota
  - Prevents quota bypass via deliberate failures
  - Tracks true provider load
  - Alternative (count successes only) rejected

### What Not to Assume

- **Fallback does not guarantee quality**
  - Secondary model available ≠ secondary model good
  - Monitor quality metrics per model separately
  - Availability and quality are different dimensions
  - Success rate ≠ task quality

- **Transient vs persistent failures need different handling**
  - Fallback helps: rate limits, timeouts, provider outages
  - Fallback doesn't help: task incompatible with all models
  - Distinguish early to avoid wasting attempts
  - Bad request (400) = task issue, not provider issue

- **More fallback ≠ less cost**
  - Every fallback attempt consumes quota
  - Track cost per successful spawn (including retries)
  - Compare with manual retry cost (human time + delays)
  - Optimize primary model reliability, not just fallback coverage

- **Session router needs refresh mechanism**
  - Availability changes over time
  - Stale session router = missed opportunities or false expectations
  - Manual regeneration = operational burden
  - Auto-refresh (Phase 2.3) needed for production

### Design Insights

- **Separation of concerns reduces coupling**
  - Smoke test: availability check (can we reach?)
  - Role fit: quality check (is it good for this role?)
  - Runtime selection: priority + availability
  - Each mechanism evolves independently

- **Explicit loop bounds prevent runaway**
  - Even with "safe" logic, bound iterations
  - `max_attempts = len(models_array)`
  - Prevents infinite loops on classification errors
  - Clear worst-case latency

- **Error messages are user interface**
  - Invest in clarity, structure, actionability
  - List what was tried, what failed, why
  - Structured errors enable automation
  - Generic errors require human investigation

- **Immutable config + transient state = safety**
  - Reference router never corrupted by runtime
  - Session router ephemeral, regenerate anytime
  - No rollback needed (just regenerate)
  - Clear update flow: edit reference → regenerate session

### Operational Lessons

- **Fallback frequency indicates primary reliability**
  - Low fallback rate → primary reliable
  - High fallback rate → primary unreliable or quota too tight
  - Track per-role fallback rate
  - Adjust priority or quota based on evidence

- **Error distribution informs tuning**
  - Many 429s → quota too tight
  - Many timeouts → provider slow or timeout too short
  - Many 400s → task/model compatibility issue
  - Many unknowns → need better classification

- **Generation failures are operational signals**
  - Zero models available → provider outage
  - Specific role empty → targeted provider issue
  - Fail-closed prevents silent degradation
  - Alert operators immediately

### Validation Gaps

Before production deployment:

- [ ] Replace mock smoke tests with real provider API calls
- [ ] Validate error patterns match actual provider responses
- [ ] Tune timeout values per provider
- [ ] Test cooldown integration under concurrent load
- [ ] Verify no secrets in logs, errors, or state files
- [ ] Test atomic write behavior (concurrent generation, crashes)
- [ ] Measure fallback impact on success rate (before/after)
- [ ] Monitor quality degradation when using secondary models

### Metrics That Mattered

**Phase 2.1 (Session Generation):**
- Generation success rate (should be >95%)
- Generation time (should be <60s for 24 models)
- False positive rate (marked available but fails)
- False negative rate (marked unavailable but would work)

**Phase 2.2 (Fallback Execution):**
- Fallback success rate (% failures recovered)
- Models per spawn (avg, p95, p99)
- Manual intervention rate (should drop >60%)
- Time to success (including fallback attempts)

### Architectural Patterns Validated

1. **Two-tier configuration** (Reference → Generation → Session)
   - Applicable: Any system where config depends on runtime state
   - Benefits: Immutability, regeneration, fail-closed

2. **Priority via ordering** (Array order defines fallback)
   - Applicable: Small catalog (<10 items per role)
   - Benefits: Simplicity, obviousness, easy filtering

3. **Error classification strategy** (4 categories, distinct retry)
   - Applicable: Any retry mechanism with external dependencies
   - Benefits: Efficient quota use, fast fail on non-retryable

4. **Fail-closed transformation** (Incomplete output = failure)
   - Applicable: When partial functionality worse than none
   - Trade-off: Less automatic resilience, clearer failures

---

**Phase 2 Status:** Implemented with mock smoke tests  
**Phase 2 Rating:** 4/5 (pending real API integration)  
**Next:** Real provider validation, operational monitoring, Phase 2.3 (auto-refresh)
