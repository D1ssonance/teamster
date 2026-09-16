# Fallback Execution - Pseudocode Example

This is anonymized pseudocode demonstrating the fallback execution pattern.
Actual implementation details vary by runtime and language.

## Exception Types

```python
class AuthenticationError(Exception):
    """Authentication or authorization failure (401/403)."""
    pass

class CapacityError(Exception):
    """All models exhausted or unavailable."""
    pass

class ValidationError(Exception):
    """Invalid request that won't succeed on retry."""
    pass
```



## Core Pattern

```python
async def spawn_agent(role: str, task: str, config: Config) -> AgentResult:
    """
    Spawn agent with automatic fallback through model chain.
    
    Args:
        role: Semantic role (e.g., "coder", "reviewer")
        task: Task description and work contract
        config: Router configuration with role definitions
    
    Returns:
        AgentResult on success
    
    Raises:
        AuthenticationError: Authentication/authorization failure (401/403)
        CapacityError: All models exhausted or unavailable
        ValidationError: Invalid request (fail-fast)
    """
    role_spec = config.roles[role]
    tried_models = []  # Track for logging/debugging
    last_error = None
    
    # Iterate through fallback chain by index (each index visited once)
    # Note: models[] may contain duplicates; each occurrence tried separately
    for model_index in range(len(role_spec.models)):
        model = role_spec.models[model_index]
        
        # Check cooldown first (fast fail, no side effects)
        # Then quota (may reserve slot, has side effects)
        if is_on_cooldown(config, model):
            continue
        
        tried_models.append(model)
        
        try:
            # Check quota before attempting spawn
            check_quota(config, role_spec)
            
            # Try to spawn with this model
            result = await runtime.spawn(
                prompt=task,
                model=model,
                name=f"{role}-{model_index}"
            )
            
            # Success!
            return result
            
        except Exception as exc:
            last_error = exc
            error_type = classify_error(exc)
            
            # AUTH errors: configuration issue, abort immediately
            if error_type == ErrorType.AUTH:
                raise AuthenticationError(
                    f"Authentication failed for model '{model}' in role '{role}'. "
                    f"Check API keys and permissions. Error: {str(exc)[:200]}"
                )
            
            # RATE_LIMIT: mark cooldown, try next model
            elif error_type == ErrorType.RATE_LIMIT:
                report_rate_limit(model, config)
                continue
                
            # PROVIDER_ERROR: transient issue, try next model
            elif error_type == ErrorType.PROVIDER_ERROR:
                # Don't cooldown - might be transient
                # Model already in tried_models, won't retry
                continue
                
            # BAD_REQUEST: task incompatible, fail fast
            elif error_type == ErrorType.BAD_REQUEST:
                # Don't try other models - same issue will occur
                raise
                
            # UNKNOWN: cautiously try next model
            else:  # ErrorType.UNKNOWN
                # Model already in tried_models, won't retry
                continue
    
    # All models exhausted or skipped
    if not tried_models:
        raise CapacityError(
            f"No available models for role '{role}'. "
            f"All models on cooldown or quota exhausted."
        )
    
    raise CapacityError(
        f"All {len(tried_models)} fallback attempt(s) for role '{role}' failed. "
        f"Tried models: {', '.join(tried_models)}. "
        f"Last error: {type(last_error).__name__}: {str(last_error)[:100]}"
    )


def is_on_cooldown(config: Config, model_id: str) -> bool:
    """
    Check if a specific model is currently on cooldown.
    
    Args:
        config: Router configuration with state
        model_id: Model to check
    
    Returns:
        True if model is on cooldown, False if available
    """
    now = time.time()
    cooldown = config.state.cooldowns.get(model_id)
    
    if cooldown and cooldown.until > now:
        return True
    
    return False


class ErrorType(Enum):
    AUTH = "auth"  # Authentication/authorization failure (401/403)
    """Error classification for retry strategy."""
    RATE_LIMIT = "rate_limit"       # 429, quota exceeded
    PROVIDER_ERROR = "provider"     # 503, timeout, connection
    BAD_REQUEST = "bad_request"     # 400, 422, invalid
    UNKNOWN = "unknown"             # Other


def classify_error(exc: Exception) -> ErrorType:
    """
    Classify error for retry strategy.
    
    Uses pattern matching on error message and type.
    For production: use structured HTTP status codes and typed exceptions.
    
    Returns:
        AUTH: Authentication/authorization failure (401/403) - DO NOT RETRY
        RATE_LIMIT: Rate limit hit (429) - mark cooldown, try next model
        PROVIDER_ERROR: Provider/gateway error (50x, timeout) - try next model
        BAD_REQUEST: Invalid request (400, 422) - likely won't succeed on retry
        UNKNOWN: Unclassified error - try next model (policy: fail-slow)
    """
    message = str(exc).lower()
    
    # Authentication/Authorization errors - DO NOT RETRY
    # These indicate configuration issues, not transient failures
    if any(pattern in message for pattern in [
        "401", "403", "unauthorized", "forbidden",
        "invalid api key", "authentication failed",
        "permission denied", "access denied"
    ]):
        return ErrorType.AUTH
    
    # Rate limit patterns (429)
    if any(pattern in message for pattern in [
        "429", "rate limit", "quota exceeded", "too many requests"
    ]):
        return ErrorType.RATE_LIMIT
    
    # Provider error patterns (50x, connectivity)
    if any(pattern in message for pattern in [
        "503", "504", "timeout", "timed out", 
        "unavailable", "connection", "gateway"
    ]):
        return ErrorType.PROVIDER_ERROR
    
    # Bad request patterns
    if any(pattern in message for pattern in [
        "400", "422", "bad request", "invalid", 
        "malformed", "unsupported"
    ]):
        return ErrorType.BAD_REQUEST
    
    # Unknown
    return ErrorType.UNKNOWN


def report_rate_limit(model_id: str, config: Config):
    """
    Report rate limit and put model on cooldown.
    
    Cooldown duration from config.quotaGroups[role.quotaGroup].cooldownSeconds
    """
    role_spec = find_role_for_model(model_id, config)
    quota_group = config.quota_groups[role_spec.quota_group]
    cooldown_seconds = quota_group.cooldown_seconds
    
    # Mark on cooldown
    config.state.cooldowns[model_id] = Cooldown(
        until=time.time() + cooldown_seconds,
        reason="rate_limit"
    )
    
    # Persist state (atomic write)
    save_state(config.state)


def check_quota(config: Config, role_spec: RoleSpec):
    """
    Check if quota group has capacity for new spawn.
    
    Raises:
        CapacityError: Quota exhausted
    """
    quota_group = config.quota_groups[role_spec.quota_group]
    window_seconds = quota_group.window_seconds
    max_starts = quota_group.max_starts
    now = time.time()
    
    # Count recent starts in sliding window
    recent_starts = [
        start_time 
        for start_time in config.state.starts.get(role_spec.quota_group, [])
        if now - start_time < window_seconds
    ]
    
    if len(recent_starts) >= max_starts:
        # Quota exhausted
        oldest_start = min(recent_starts)
        retry_after = math.ceil(oldest_start + window_seconds - now)
        raise CapacityError(
            f"Quota group '{role_spec.quota_group}' exhausted. "
            f"Max {max_starts} starts per {window_seconds}s. "
            f"Retry after {retry_after}s"
        )
    
    # Reserve slot
    config.state.starts[role_spec.quota_group] = recent_starts + [now]
    save_state(config.state)
```

## Usage Example

```python
# Initialize config
config = load_router_config("/path/to/session-router.json")

# Spawn with automatic fallback
try:
    result = await spawn_agent(
        role="coder",
        task="Implement user authentication flow",
        config=config
    )
    print(f"Success! Agent ID: {result.agent_id}")
    
except CapacityError as e:
    # All models exhausted
    print(f"Failed: {e}")
    print(f"Retry after {e.retry_after}s")
    
except ValidationError as e:
    # Bad request, don't retry
    print(f"Invalid task: {e}")
```

## Error Flow Examples

### Scenario 1: Rate Limit on Primary, Success on Secondary

```
Attempt 1: provider-a/model-1
  ↓
429 Rate Limit Error
  ↓
Classify: RATE_LIMIT
  ↓
report_rate_limit(model-1) → cooldown 45s
  ↓
Continue to next model

Attempt 2: provider-a/model-2
  ↓
200 Success
  ↓
Return result

Total attempts: 2
Total time: ~5s (1s fail + 4s success)
```

### Scenario 2: Provider Timeout, Fallback to Different Provider

```
Attempt 1: provider-a/model-1
  ↓
Timeout after 10s
  ↓
Classify: PROVIDER_ERROR
  ↓
Continue immediately (no cooldown)

Attempt 2: provider-b/model-1
  ↓
200 Success
  ↓
Return result

Total attempts: 2
Total time: ~12s (10s timeout + 2s success)
```

### Scenario 3: Bad Request, Fail Fast

```
Attempt 1: provider-a/model-1
  ↓
400 Bad Request: "vision capability required"
  ↓
Classify: BAD_REQUEST
  ↓
Raise immediately (don't try other models)

Total attempts: 1
Total time: ~1s
Reason: Task incompatible, other models won't help
```

### Scenario 4: All Models Exhausted

```
Attempt 1: provider-a/model-1
  ↓
503 Service Unavailable

Attempt 2: provider-a/model-2
  ↓
Timeout after 10s

Attempt 3: provider-b/model-1
  ↓
429 Rate Limited

All models tried, all failed
  ↓
Raise CapacityError with tried_models list

Total attempts: 3
Total time: ~21s
```

## Configuration Example

```json
{
  "roles": {
    "coder": {
      "models": [
        "provider-a/model-fast",
        "provider-a/model-capable", 
        "provider-b/model-alternative"
      ],
      "quotaGroup": "coding",
      "metadata": {
        "validation": "validated",
        "lastAssessment": "2025-01-15"
      }
    }
  },
  "quotaGroups": {
    "coding": {
      "maxStarts": 3,
      "windowSeconds": 15,
      "cooldownSeconds": 45
    }
  }
}
```

## State File Example

```json
{
  "cooldowns": {
    "provider-a/model-1": {
      "until": 1726401234.567,
      "reason": "rate_limit"
    }
  },
  "starts": {
    "coding": [
      1726401200.123,
      1726401205.456
    ]
  }
}
```

## Key Points

1. **Bounded attempts**: Loop terminates at len(models) iterations
2. **Fail-fast on bad requests**: Don't waste quota on incompatible tasks
3. **Immediate retry on provider errors**: Don't cooldown for transient issues
4. **Cooldown on rate limits**: Prevent repeated 429s
5. **Structured errors**: Include tried models for debugging
6. **Quota enforcement**: Check before loop, track all attempts
7. **State persistence**: Atomic writes, survive restarts

---

**Note:** This is anonymized pseudocode. Actual implementation varies by:
- Runtime language (Python, TypeScript, Go, etc.)
- Agent framework (native, MCP, API-based)
- Provider error formats
- Authentication mechanisms
- Concurrency requirements

## Validation Test Cases

### Test 1: Fallback on Provider Timeout

Validates that timeout/503 errors advance through the fallback chain:

```python
def test_fallback_on_provider_timeout():
    """
    Verify that provider timeout triggers fallback to next model.
    This test validates the fix for the original pseudocode bug.
    """
    # Setup: Two models in priority order
    config = RouterConfig(
        roles={
            "coder": RoleSpec(
                name="coder",
                models=["provider-a/model-1", "provider-b/model-2"],
                quotaGroup="standard"
            )
        }
    )
    
    # Mock provider behavior
    mock_runtime.set_behavior(
        "provider-a/model-1",
        error=ProviderTimeout("Connection timeout after 10s")
    )
    mock_runtime.set_behavior(
        "provider-b/model-2",
        success=AgentResult(model="provider-b/model-2", handle="agent-123")
    )
    
    # Execute spawn
    result = await spawn_agent(
        role="coder",
        task="Implement feature X",
        config=config
    )
    
    # Assertions
    assert result.model == "provider-b/model-2", "Should fallback to model-2"
    
    # Verify call sequence
    calls = mock_runtime.get_call_log()
    assert len(calls) == 2, "Should try exactly 2 models"
    assert calls[0].model == "provider-a/model-1", "First attempt: model-1"
    assert calls[1].model == "provider-b/model-2", "Second attempt: model-2"
    
    # Verify model-1 NOT on cooldown (timeout doesn't trigger cooldown)
    assert not is_on_cooldown(config, "provider-a/model-1")
    
    print("✅ Fallback on timeout works correctly")


def test_no_infinite_retry_on_same_model():
    """
    Regression test: Ensure we don't retry the same model multiple times
    when it returns non-cooldown errors.
    
    This validates the fix for the original bug where provider_error
    would cause infinite retry on the same model.
    """
    config = RouterConfig(
        roles={
            "coder": RoleSpec(
                name="coder",
                models=["model-1", "model-2", "model-3"],
                quotaGroup="standard"
            )
        }
    )
    
    # All models fail with provider errors
    for model in ["model-1", "model-2", "model-3"]:
        mock_runtime.set_behavior(
            model,
            error=ProviderError("Service unavailable")
        )
    
    # Should exhaust all models exactly once
    with pytest.raises(CapacityError) as exc_info:
        await spawn_agent(role="coder", task="test", config=config)
    
    # Verify error message
    error_msg = str(exc_info.value)
    assert "3 fallback attempt(s)" in error_msg
    assert "model-1" in error_msg
    assert "model-2" in error_msg
    assert "model-3" in error_msg
    
    # Critical: Verify each model tried EXACTLY ONCE
    calls = mock_runtime.get_call_log()
    assert len(calls) == 3, "Should try each model exactly once"
    assert calls[0].model == "model-1"
    assert calls[1].model == "model-2"
    assert calls[2].model == "model-3"
    
    # Verify NO model called more than once
    call_counts = {}
    for call in calls:
        call_counts[call.model] = call_counts.get(call.model, 0) + 1
    
    for model, count in call_counts.items():
        assert count == 1, f"{model} should be called exactly once, got {count}"
    
    print("✅ No infinite retry - each model tried exactly once")


def test_rate_limit_triggers_cooldown_and_fallback():
    """
    Verify rate limit behavior: cooldown + fallback to next model.
    """
    config = RouterConfig(
        roles={
            "coder": RoleSpec(
                name="coder", 
                models=["model-1", "model-2"],
                quotaGroup="standard"
            )
        },
        quotaGroups={
            "standard": QuotaGroup(
                maxStarts=10,
                windowSeconds=60,
                cooldownSeconds=300
            )
        }
    )
    
    # model-1 hits rate limit, model-2 succeeds
    mock_runtime.set_behavior(
        "model-1",
        error=RateLimitError("Rate limit exceeded", retry_after=300)
    )
    mock_runtime.set_behavior(
        "model-2",
        success=AgentResult(model="model-2", handle="agent-456")
    )
    
    result = await spawn_agent(role="coder", task="test", config=config)
    
    # Verify success with model-2
    assert result.model == "model-2"
    
    # Verify model-1 IS on cooldown
    assert is_on_cooldown(config, "model-1")
    
    # Verify cooldown duration ~= 300s
    cooldown = config.state.cooldowns["model-1"]
    assert 295 <= (cooldown.until - time.time()) <= 305
    
    print("✅ Rate limit triggers cooldown and fallback")
```

### Test 2: Bad Request Fails Fast

```python
def test_bad_request_fails_fast():
    """
    Verify that bad request (400) doesn't waste attempts on other models.
    """
    config = RouterConfig(
        roles={
            "coder": RoleSpec(
                name="coder",
                models=["model-1", "model-2", "model-3"],
                quotaGroup="standard"
            )
        }
    )
    
    # First model returns bad request
    mock_runtime.set_behavior(
        "model-1",
        error=ValidationError("Invalid prompt format")
    )
    
    # Other models would succeed (but shouldn't be tried)
    mock_runtime.set_behavior("model-2", success=True)
    mock_runtime.set_behavior("model-3", success=True)
    
    # Should fail immediately with ValidationError
    with pytest.raises(ValidationError):
        await spawn_agent(role="coder", task="malformed", config=config)
    
    # Critical: Only model-1 should be tried
    calls = mock_runtime.get_call_log()
    assert len(calls) == 1, "Should try only first model"
    assert calls[0].model == "model-1"
    
    print("✅ Bad request fails fast without trying other models")
```

### Test 3: Skip Models on Cooldown

```python
def test_skip_models_on_cooldown():
    """
    Verify that models on cooldown are skipped during iteration.
    """
    config = RouterConfig(
        roles={
            "coder": RoleSpec(
                name="coder",
                models=["model-1", "model-2", "model-3"],
                quotaGroup="standard"
            )
        }
    )
    
    # Put model-1 on cooldown manually
    config.state.cooldowns["model-1"] = CooldownEntry(
        until=time.time() + 300,
        reason="rate_limit"
    )
    
    # model-2 succeeds
    mock_runtime.set_behavior(
        "model-2",
        success=AgentResult(model="model-2", handle="agent-789")
    )
    
    result = await spawn_agent(role="coder", task="test", config=config)
    
    # Should skip model-1, use model-2
    assert result.model == "model-2"
    
    calls = mock_runtime.get_call_log()
    assert len(calls) == 1
    assert calls[0].model == "model-2"
    
    print("✅ Models on cooldown correctly skipped")
```

## Key Takeaways from Tests

1. **Index-based iteration ensures forward progress**
   - Each loop iteration advances to next model in array
   - `tried_models` prevents accidental retries
   - Works for ALL error types (timeout, 503, unknown)

2. **Cooldown is selective**
   - Only `rate_limit` triggers cooldown
   - `provider_error`/`timeout` don't cooldown (might be transient)
   - Cooldown models automatically skipped in next spawn

3. **Fail-fast prevents waste**
   - `bad_request` stops immediately
   - Don't try other models for validation errors
   - User gets immediate feedback

4. **Structured errors provide context**
   - List of tried models
   - Last error details
   - Clear capacity vs validation failure

---
