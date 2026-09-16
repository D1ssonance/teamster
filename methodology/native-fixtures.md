# Native Fixtures Methodology

## Purpose

Test agent behavior with real tool execution in sandboxed environment, not just API responses.

## Scope

- Actual file operations
- Real shell command execution
- Tool call sequences
- State persistence across calls
- Error recovery

**Not tested**: Network access, external services, production data

## Test Environment

### Sandbox Requirements

1. **Isolated filesystem**: Temporary directory, cleaned after test
2. **Restricted shell**: No network, limited syscalls
3. **Timeout enforcement**: Tests fail if exceeded
4. **Resource limits**: Memory, CPU, disk usage bounded

### Fixture Structure

```
fixtures/
├── scout-find-todos/
│   ├── workspace/
│   │   ├── src/main.py         # Test files
│   │   └── src/utils.py
│   ├── expected.json           # Expected result
│   └── test.py                 # Test runner
├── coder-add-logging/
│   ├── workspace/
│   │   └── src/handler.py
│   ├── expected-diff.txt
│   └── test.py
└── reviewer-security/
    ├── workspace/
    │   └── src/api.py
    ├── expected-issues.json
    └── test.py
```

## Test Execution

### Setup Phase

1. Copy fixture workspace to temp directory
2. Initialize agent runtime with temp workspace
3. Configure tools (read_file, write_file, bash)
4. Set timeout (default: 60s)

### Execution Phase

```python
# Pseudocode
agent = spawn_agent(
    model="provider/model-name",
    role="scout",
    objective=fixture.objective,
    read_scope=[temp_workspace],
    tools=["read_file", "search_files"]
)

result = await agent.complete(timeout=60)
```

### Validation Phase

Compare actual result against expected:
- File contents match
- Commands executed correctly
- Output structure valid
- No unauthorized operations

## Example: Scout Fixture

**Fixture**: `scout-find-todos`

**Workspace**:
```
workspace/src/main.py:
  # TODO: add error handling
  def process(): pass

workspace/src/utils.py:
  # TODO: optimize this
  def helper(): pass
```

**Objective**: "Find all TODO comments with file and line number"

**Expected Result**:
```json
{
  "todos": [
    {"file": "src/main.py", "line": 1, "text": "add error handling"},
    {"file": "src/utils.py", "line": 1, "text": "optimize this"}
  ]
}
```

**Validation**:
- All TODOs found: ✓
- Correct file paths: ✓
- Correct line numbers: ✓
- No false positives: ✓

## Example: Coder Fixture

**Fixture**: `coder-add-logging`

**Workspace**:
```python
# workspace/src/handler.py
def handle_request(request):
    data = parse(request)
    return process(data)
```

**Objective**: "Add logging before and after process() call"

**Expected Diff**:
```python
def handle_request(request):
    data = parse(request)
+   logger.info("Processing request with data: %s", data)
    result = process(data)
+   logger.info("Process completed with result: %s", result)
-   return process(data)
+   return result
```

**Validation**:
- Logging added: ✓
- Syntax valid: ✓
- Original behavior preserved: ✓
- Style consistent: ✓

## Pass/Fail Criteria

### Pass
- All expected operations performed
- No unauthorized operations
- Output matches expected format
- Completed within timeout
- No tool errors

### Fail
- Missing expected operations
- Incorrect output format
- Timeout exceeded
- Tool call errors
- Unauthorized file access

## Integration with Role-Fit

Native fixtures run after basic role-fit tests:

```
Phase 1: API Smoke → PASS
Phase 2: Tool Protocol → PASS
Phase 3: Native Agent → PASS
Phase 4: Native Fixtures → scout:PASS, coder:PASS, reviewer:FAIL
```

## Limitations

- Fixtures are synthetic scenarios
- Sandbox may not match production environment
- Limited test coverage (one fixture per role)
- No multi-turn interaction testing
- No context window stress testing

**Use this for**: Validating actual tool execution  
**Use monitoring for**: Production behavior tracking
