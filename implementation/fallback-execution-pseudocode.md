# Fallback Execution - Pseudocode Example

This is anonymized pseudocode demonstrating the fallback execution pattern.
Actual implementation details vary by runtime and language.

## Core Pattern

```python
def spawn_agent(role: str, task: str, config: Config) -> AgentResult:
    """
    Spawn agent with automatic fallback through model chain.
    
    Args:
        role: Semantic role (e.g., "coder", "reviewer")
        task: Task description and work contract
        config: Router configuration with role definitions
    
    Returns:
        AgentResult on success
    
    Raises:
        CapacityError: All models exhausted
        ValidationError: Invalid request (fail-fast)
    """
    role_spec = config.roles[role]
    max_attempts = len(role_spec.models)
    tried_models = []
    last_error = None
    
    # Retry loop through fallback chain
    for attempt in range(max_attempts):
        try:
            # Select next available model (not on cooldown)
            model = select_next_available_model(config, role_spec)
            tried_models.append(model)
            
            # Check quota before attempting
            check_quota(config, role_spec)
            
            # Try to spawn with this model
            result = await runtime.spawn(
                prompt=task,
                model=model,
                name=f"{role}-{attempt}"
            )
            
            # Success!
            return result
            
        except Exception as exc:
            last_error = exc
            error_type = classify_error(exc)
            
            if error_type == ErrorType.RATE_LIMIT:
                # Mark model on cooldown, try next
                report_rate_limit(model, config)
                continue
                
            elif error_type == ErrorType.PROVIDER_ERROR:
                # Provider issue, try next immediately
                # (don't cooldown, might be transient)
                continue
                
            elif error_type == ErrorType.BAD_REQUEST:
                # Task incompatible, fail fast
                # (don't try other models, same issue)
                raise
                
            else:  # ErrorType.UNKNOWN
                # Cautiously try next model
                continue
    
    # All models exhausted
    raise CapacityError(
        f"All {max_attempts} fallback attempt(s) for role '{role}' failed. "
        f"Tried models: {', '.join(tried_models)}. "
        f"Last error: {type(last_error).__name__}: {str(last_error)[:100]}"
    )


def select_next_available_model(config: Config, role_spec: RoleSpec) -> str:
    """
    Select next model from role's model list that is not on cooldown.
    
    Models are tried in array order (priority order).
    Returns first model not on cooldown.
    
    Raises:
        CapacityError: All models on cooldown
    """
    now = time.time()
    
    for model_id in role_spec.models:
        # Check if on cooldown
        cooldown = config.state.cooldowns.get(model_id)
        if cooldown and cooldown.until > now:
            # Still on cooldown, skip
            continue
        
        # Available!
        return model_id
    
    # All on cooldown
    wait_times = [
        cooldown.until - now 
        for cooldown in config.state.cooldowns.values()
        if cooldown.until > now
    ]
    retry_after = min(wait_times) if wait_times else 60
    
    raise CapacityError(
        f"All models for role '{role_spec.name}' on cooldown. "
        f"Retry after {retry_after}s"
    )


class ErrorType(Enum):
    """Error classification for retry strategy."""
    RATE_LIMIT = "rate_limit"       # 429, quota exceeded
    PROVIDER_ERROR = "provider"     # 503, timeout, connection
    BAD_REQUEST = "bad_request"     # 400, 422, invalid
    UNKNOWN = "unknown"             # Other


def classify_error(exc: Exception) -> ErrorType:
    """
    Classify error for retry strategy.
    
    Uses pattern matching on error message and type.
    Adjust patterns based on actual provider responses.
    """
    message = str(exc).lower()
    
    # Rate limit patterns
    if any(pattern in message for pattern in [
        "429", "rate limit", "quota exceeded", "too many requests"
    ]):
        return ErrorType.RATE_LIMIT
    
    # Provider error patterns
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
    result = spawn_agent(
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
