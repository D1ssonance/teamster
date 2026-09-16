# Role-Fit Evaluation Methodology

## Purpose

Determine whether a model is suitable for specific agent roles based on capability requirements, not just API availability.

## Scope

Test role-specific capabilities:
- **Scout**: Search, file inspection, pattern matching
- **Coder**: Code generation, stdlib usage, error handling
- **Reviewer**: Code analysis, issue detection, improvement suggestions
- **Test-writer**: Test generation, edge case coverage
- **Debugger**: Root cause analysis, hypothesis testing
- **Heavy-coder**: Multi-file refactoring, architecture changes

**Not tested**: Performance optimization, cost efficiency, latency

## Test Procedure

### Phase 1: Tool Protocol Test

Verify model supports required tool calling format:

```json
{
  "model": "provider/model-name",
  "messages": [...],
  "tools": [
    {
      "type": "function",
      "function": {
        "name": "read_file",
        "description": "Read file contents",
        "parameters": {"type": "object", "properties": {...}}
      }
    }
  ]
}
```

**Success**: Model returns valid `tool_calls` in response  
**Failure**: Model doesn't support tools or returns invalid structure

### Phase 2: Native Agent Test

Test model as agent in minimal task:

```python
# Pseudocode
agent = spawn_agent(
    model="provider/model-name",
    objective="Find all TODO comments in src/",
    read_scope=["/workspace/src"],
    tools=["read_file", "search_files"]
)

result = await agent.complete()
```

**Success**: Agent completes task and sends valid result  
**Failure**: Agent fails, loops, or produces invalid output

### Phase 3: Role-Specific Tests

Each role has specific test scenarios:

#### Scout Test

**Task**: "Find all implementations of interface X"

**Capabilities tested**:
- File search
- Content inspection
- Pattern matching
- Result summarization

**Pass criteria**:
- Found all implementations
- No false positives
- Concise summary provided

#### Coder Test

**Task**: "Add logging to function Y"

**Capabilities tested**:
- Code reading
- Modification in place
- Syntax correctness
- Style consistency

**Pass criteria**:
- Code compiles/runs
- Logging added correctly
- Original behavior preserved
- Style matches project

#### Reviewer Test

**Task**: "Review PR for security issues"

**Capabilities tested**:
- Multi-file analysis
- Issue detection
- Severity assessment
- Recommendation quality

**Pass criteria**:
- Found real issues
- No false positives (or minimal)
- Severity ratings reasonable
- Actionable recommendations

## Scoring

Each role receives:
- **PASS**: Meets all criteria
- **PARTIAL**: Meets some criteria, usable with supervision
- **FAIL**: Does not meet basic requirements

Example output:

```
Model: provider/model-name
├─ Tool Protocol: PASS
├─ Native Agent: PASS
└─ Role Fit:
   ├─ scout: PASS
   ├─ coder: PASS
   ├─ reviewer: PARTIAL (missed 1/3 issues)
   ├─ test-writer: PASS
   ├─ debugger: FAIL (no hypothesis testing)
   └─ heavy-coder: PASS
```

## Integration with Router

Role-fit results determine role-to-model mappings:

```json
{
  "roles": {
    "scout": {
      "models": ["model-a", "model-b"]  // Both passed scout test
    },
    "coder": {
      "models": ["model-a"]  // Only model-a passed coder test
    },
    "reviewer": {
      "models": ["model-a", "model-c"]  // model-a full pass, model-c partial
    }
  }
}
```

## Limitations

- Tests use synthetic tasks, not production workload
- Single test may not represent all scenarios
- Model behavior can vary with prompt phrasing
- Performance characteristics not measured
- Cost not considered in fit evaluation

**Use this for**: Role assignment decisions  
**Use monitoring for**: Production performance validation
