<p align="center">
  <img src="assets/logo.png" alt="Teamster" width="480">
</p>

<p align="center">
  <strong>Role-based orchestration and workflow toolkit for AI agents</strong>
</p>

<p align="center">
  Skills · Role Router · Work Contracts · Verification · Multi-Agent Workflows
</p>

---

# Agent Router Workflow

Principles, patterns, and lessons learned from implementing a semantic-role 
based agent routing system with dynamic availability and automatic fallback.

## What This Is

A reference implementation and documentation of:
- Semantic role-based model selection
- Two-tier configuration (reference + session)
- API availability testing
- Automatic fallback through model chains
- Error classification and retry strategies
- Fail-closed generation and execution
- Privacy-safe monitoring and state management

## Quick Start

1. **[FIRST-RUN.md](./FIRST-RUN.md)** - Setup and initial validation
2. **[examples/](./examples/)** - Configuration templates
3. **[implementation/](./implementation/)** - Phase 2 implementation guide
4. **[RESULTS-AND-LESSONS.md](./RESULTS-AND-LESSONS.md)** - Key lessons

## Architecture

```
┌─────────────────────┐
│  Reference Router   │  Phase 1: Static configuration
│  (immutable)        │  - 10 semantic roles
└──────────┬──────────┘  - Priority-ordered models per role
           │             - Quota groups, cooldowns
           ▼
┌─────────────────────┐
│  Session Generator  │  Phase 2.1: Dynamic availability
│  (API smoke tests)  │  - Test each model
└──────────┬──────────┘  - Filter unavailable
           │             - Fail-closed generation
           ▼
┌─────────────────────┐
│  Session Router     │  Phase 2.2: Runtime execution
│  (available only)   │  - Automatic fallback
└──────────┬──────────┘  - Error classification
           │             - Structured errors
           ▼
┌─────────────────────┐
│  Agent Delegation   │
│  (spawn with role)  │
└─────────────────────┘
```

## Core Concepts

### Semantic Roles

Instead of selecting models by name, select by task semantics:

- **scout**: Repository search, evidence collection
- **coder**: Focused implementation
- **heavy-coder**: Complex multi-file refactoring
- **test-writer**: Test implementation
- **fixer**: Bug corrections
- **debugger**: Diagnosis and investigation
- **reviewer**: Independent review
- **requirements**: Requirements clarification
- **corporate-architect**: Architecture decisions
- **vision**: Image/diagram analysis

### Reference/Session Separation

**Reference Router (immutable):**
- Complete model catalog
- Desired configuration
- All roles, all models
- Source of truth

**Session Router (transient):**
- Currently available models only
- Generated from reference
- Filtered by availability
- Used at runtime

### Priority-Ordered Fallback

Models listed in priority order:
```json
{
  "models": ["primary", "secondary", "tertiary"]
}
```

- First model tried first
- Automatic fallback on retryable errors
- Order preserved through filtering

### Error Classification

Four categories with distinct retry strategies:

1. **Rate Limit (429)** → Cooldown + try next model
2. **Provider Error (503/timeout)** → Try next immediately  
3. **Bad Request (400)** → Fail fast, don't waste attempts
4. **Unknown** → Cautiously try next

## Implementation Phases

### Phase 1: Reference Router (Complete ✅)
- Semantic role definitions
- Model catalog per role
- Quota groups and rate limits
- Cooldown tracking
- Manual model selection

### Phase 2.1: Session Generation (Complete ✅)
- API smoke test framework
- Model availability detection
- Reference → Session transformation
- Fail-closed generation
- State tracking

### Phase 2.2: Fallback Execution (Complete ✅)
- Automatic retry loop
- Error classification
- Cooldown integration
- Structured error messages
- Minimal invasive changes

### Phase 2.3: Auto-Refresh (Future 🔄)
- Periodic regeneration
- Availability monitoring
- Webhook notifications
- Dashboard visualization

## Directory Structure

```
agent-router-workflow/
├── README.md                       # This file
├── FIRST-RUN.md                    # Setup guide
├── RESULTS-AND-LESSONS.md          # Key lessons learned
│
├── examples/                       # Configuration templates
│   ├── README.md
│   ├── reference-router.template.json
│   └── session-router-report.template.json
│
├── implementation/                 # Phase 2 documentation
│   ├── README.md
│   ├── phase2-session-generation.md
│   ├── phase2-fallback-execution.md
│   ├── phase2-lessons-learned.md
│   └── fallback-execution-pseudocode.md
│
├── methodology/                    # Evaluation methods
│   ├── api-smoke.md
│   ├── role-fit.md
│   ├── native-fixtures.md
│   └── tooling-pilots.md
│
├── policies/                       # Safety and operational policies
│   ├── evidence-and-privacy.md
│   ├── production-safety.md
│   └── orchestration.md
│
├── skills/                         # Skill documentation
│   ├── model-api-smoke-test/
│   └── router-role-fit-evaluation/
│
└── templates/
    └── work-contract.md            # Agent work contract template
```

## Key Lessons

### Design Decisions That Worked

✅ **Immutable reference + transient session**
- Clear separation of desired vs available
- Safe rollback (regenerate from reference)
- No config corruption

✅ **Fallback via array order**
- No explicit chain configuration
- Priority obvious from structure
- Easy to filter and preserve order

✅ **Minimal invasive changes**
- Wrapped existing logic instead of rewriting
- Preserved cooldown and quota mechanisms
- Lower regression risk

✅ **Fail-closed at every level**
- Incomplete session → fail generation
- Bad request → fail fast
- Prevents silent degradation

### What Required Iteration

⚠️ **Mock vs real smoke tests**
- Mock good for structure
- Can't validate real behavior
- Must replace with real API

⚠️ **Timeout tuning**
- One-size-fits-all doesn't work
- Per-provider configuration needed
- Balance speed vs false negatives

⚠️ **Error pattern matching**
- Generic patterns cover ~80%
- Provider-specific patterns needed
- Continuous tuning required

## Privacy and Safety

**All configuration is anonymized:**
- No actual model names
- No provider credentials
- No project-specific data
- Generic examples only

**State management:**
- No secrets in JSON
- Atomic writes
- Corruption detection
- TTL for cached data

**Logging:**
- No request/response bodies
- Model IDs and status codes only
- No user data
- Protected state directory

## Metrics

### Phase 2.1 (Session Generation)
- Generation success rate >95%
- Generation time <60s for 24 models
- False positive/negative <5%

### Phase 2.2 (Fallback Execution)
- Fallback success rate >80%
- Manual intervention <5%
- Avg models per spawn ~1.2
- P95 latency <10s

## Usage Pattern

```python
# Load session router (generated from reference)
config = load_router_config("/path/to/session-router.json")

# Spawn with automatic fallback
result = spawn_agent(
    role="coder",              # Semantic role
    task="Implement feature",  # Task description
    config=config              # Session router
)

# On error, automatically tries fallback models
# Structured error on exhaustion with tried models list
```

## When to Use This

**Good fit:**
- Multiple LLM providers/models
- Semantic task categorization
- Need automatic failover
- Rate limits and quotas
- Heterogeneous model capabilities

**Not a fit:**
- Single model/provider
- All tasks same quality requirements
- No rate limit issues
- Direct model selection preferred

## Contributing

This is documentation and lessons learned from a real implementation.
Adapt patterns to your context. All examples are anonymized.

**Share your own lessons:**
- What worked in your environment?
- What needed different approaches?
- What patterns emerged?

## License

This documentation is provided as-is for reference and learning.
No warranty, no guarantees. Use at your own risk.

---

**Status:** Phase 2.1+2.2 complete, Phase 2.3 planned  
**Rating:** 4/5 (pending real API integration)
