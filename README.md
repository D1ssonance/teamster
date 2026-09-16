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
agent-router-workflow/
├── README.md
├── ARCHITECTURE.md
├── INSTALLATION.md
├── FIRST-RUN.md
├── MONITORING.md
├── MIGRATION.md
├── REPRODUCIBILITY.md
├── CHANGES.md
├── FIX-SUMMARY.md
├── reference-router.json
├── reference-router.template.json
├── session-router-report.template.json
├── session_router_generator.py
├── router_core.py
├── examples/
│   ├── README.md
│   └── work-contract.md
├── implementation/
│   ├── README.md
│   ├── fallback-execution-pseudocode.md
│   └── ERRATA.md
├── operations/
│   ├── README.md
│   ├── troubleshooting.md
│   ├── state-recovery.md
│   ├── rollback.md
│   ├── quota-configuration.md
│   └── error-classification.md
├── phase2/
│   ├── README.md
│   ├── phase2-session-generation.md
│   ├── phase2-fallback-execution.md
│   └── RESULTS-AND-LESSONS.md
├── policies/
│   ├── README.md
│   ├── production-safety.md
│   └── privacy-guidelines.md
├── schemas/
│   ├── README.md
│   └── reference-router.schema.json
└── tests/
    ├── README.md
    └── test_router.py
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
├── README.md                           # Quick start and overview
├── ARCHITECTURE.md                     # System design and components
├── FIRST-RUN.md                        # Initial setup guide
├── INSTALLATION.md                     # Installation steps
├── MIGRATION.md                        # Migration scenarios
├── MONITORING.md                       # Metrics and alerting
├── REPRODUCIBILITY.md                  # Implementation estimate
├── RESULTS-AND-LESSONS.md              # Evaluation results
├── REVIEW.md                           # Code review findings
├── SHARING.md                          # Distribution guide
├── CHANGES.md                          # Change log
├── ERRATA.md                           # Known bugs and fixes
│
├── implementation/                     # Phase 2 documentation
│   ├── README.md
│   ├── fallback-execution-pseudocode.md    # Canonical logic
│   ├── phase2-session-generation.md        # Phase 2.1
│   ├── phase2-fallback-execution.md        # Phase 2.2
│   └── phase2-lessons-learned.md
│
├── methodology/                        # Evaluation methods
│   ├── api-smoke.md                    # API testing approach
│   ├── role-fit.md                     # Role evaluation
│   ├── native-fixtures.md              # Test fixtures
│   └── tooling-pilots.md               # Tool integration
│
├── operations/                         # Operational procedures
│   ├── README.md
│   ├── troubleshooting.md              # Common issues and solutions
│   ├── state-recovery.md               # State file recovery
│   ├── rollback.md                     # Configuration rollback
│   ├── quota-configuration.md          # Quota tuning guide
│   └── error-classification.md         # Error handling patterns
│
├── policies/                           # Safety and workflow policies
│   ├── orchestration.md                # Workflow and delegation
│   ├── production-safety.md            # Safety guidelines
│   └── evidence-and-privacy.md         # Privacy rules
│
├── schemas/                            # JSON Schema definitions
│   ├── README.md
│   └── reference-router.schema.json    # Router config schema
│
├── templates/                          # Configuration templates
│   ├── work-contract.md                # Work contract template
│   ├── reference-router.template.json  # Router config template
│   └── session-router-report.template.json
│
├── examples/                           # Usage examples
│   └── README.md
│
└── skills/                             # Skill documentation
    ├── model-api-smoke-test/
    │   ├── SKILL.md
    │   └── references/protocol.md
    └── router-role-fit-evaluation/
        ├── SKILL.md
        └── references/protocol.md
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
- Generation time <60s (tested with 10 roles, 2-3 models each)
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
result = await spawn_agent(
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
**Errata:** Pseudocode fallback logic fixed 2025-01-15 (see [ERRATA.md](./ERRATA.md))  
**Rating:** 4/5 (pending real API integration)  
**Last Updated:** 2025-01-15
