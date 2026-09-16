# Router Tests

## Overview

Executable tests for router fallback logic and error classification.

## Running Tests

### Install Dependencies

```bash
pip install pytest pytest-asyncio
```

### Run All Tests

```bash
pytest tests/ -v
```

### Run Specific Test

```bash
pytest tests/test_router.py::test_fallback_on_rate_limit -v
```

### Run with Coverage

```bash
pip install pytest-cov
pytest tests/ --cov=router --cov-report=html
```

## Test Files

- **test_router.py** - Core fallback and error handling tests
  - Primary model success
  - Fallback on rate limit
  - AUTH error fail-fast
  - Cooldown model skipping
  - Error classification

## Test Structure

Tests use mock runtime and configuration to verify:

1. **Fallback logic** - Tries secondary models when primary fails
2. **Error classification** - Correctly identifies error types
3. **Cooldown behavior** - Skips models on cooldown
4. **Fail-fast errors** - AUTH and VALIDATION don't retry

## Adding New Tests

```python
@pytest.mark.asyncio
async def test_your_scenario():
    """Test description"""
    config = Config(roles={
        "coder": RoleSpec(
            models=["provider/model-1", "provider/model-2"],
            quotaGroup="fast"
        )
    })
    
    runtime = MockRuntime()
    # Configure failures if needed
    runtime.failures = [("provider/model-1", ErrorType.RATE_LIMIT)]
    
    result = await spawn_agent("coder", "task", config, runtime)
    
    assert result["model"] == "provider/model-2"
```

## See Also

- [../implementation/fallback-execution-pseudocode.md](../implementation/fallback-execution-pseudocode.md) - Logic reference
- [../operations/troubleshooting.md](../operations/troubleshooting.md) - Common issues

### Integration Tests

`test_integration.py` - Tests for the complete router implementation:
- RouterState persistence and locking
- AgentRouter fallback logic
- Error classification
- Quota tracking
- Session generator

Run integration tests:
```bash
pytest tests/test_integration.py -v
```
