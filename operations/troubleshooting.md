# Router Troubleshooting Guide

## Quick Diagnosis

Use this decision tree to identify the problem:

```
Spawn fails?
├─→ YES: See "Spawn Failures" section
└─→ NO: Working but slow/wrong model?
    ├─→ Wrong model selected: See "Model Selection Issues"
    ├─→ Too slow: See "Performance Issues"
    └─→ Quota exhausted: See "Quota Issues"
```

## Common Issues

### 1. Router Not Active

**Symptom**: Spawns ignore router, use parent model or fail with "no model specified"

**Diagnosis**:
```bash
# Check if router is enabled
jq '.enabled' reference-router.json
# Should show: true
```

**Solutions**:
- Set `enabled: true` in reference-router.json
- Verify router file path is correct in corporate_agents configuration
- Check router file has valid JSON syntax

---

### 2. All Models On Cooldown

**Symptom**: "No available models" error, all spawns fail

**Diagnosis**:
```bash
# Check current cooldowns
jq '.cooldowns' state.json

# Check if cooldowns are recent
jq '.cooldowns | to_entries[] | select(.value > now)' state.json
```

**Solutions**:

**Option A: Wait** - Cooldowns expire automatically (check `cooldownSeconds` in quota config)

**Option B: Clear cooldowns** (if stuck after crash):
```bash
cp state.json state.json.backup
jq '.cooldowns = {}' state.json > tmp.json && mv tmp.json state.json
```

**Option C: Add more models** - Expand fallback chain in role configuration

---

### 3. Quota Always Exhausted

**Symptom**: "Quota group exhausted" error immediately after reset

**Diagnosis**:
```bash
# Check start history size
jq '.starts | to_entries[] | .key + ": " + (.value | length | tostring)' state.json

# Check quota limits
jq '.quotaGroups' reference-router.json
```

**Solutions**:

**Immediate fix**:
```bash
# Clear start history
jq '.starts = {}' state.json > tmp.json && mv tmp.json state.json
```

**Root cause fixes**:
- Increase `maxStarts` in quota group configuration
- Increase `windowSeconds` to allow more capacity over time
- Implement proper state pruning (remove old timestamps)
- Split roles across multiple quota groups

---

### 4. Wrong Model Selected

**Symptom**: Router selects unexpected model (fallback instead of primary)

**Diagnosis**:
```bash
# Check role configuration
jq '.roles.coder.models' reference-router.json

# Check if primary on cooldown
jq '.cooldowns["provider-a/model-primary"]' state.json

# Check provider allowed
jq '.allowedProviders' reference-router.json
```

**Solutions**:
- Verify primary model is first in `models` array
- Check primary model not on cooldown (clear if stuck)
- Verify provider in `allowedProviders` list
- Check model name matches exactly (provider/model format)

---

### 5. Fallback Not Working

**Symptom**: Spawn fails instead of trying fallback model

**Diagnosis**:
```bash
# Check maxFallbackAttempts
jq '.maxFallbackAttempts' reference-router.json

# Check if fallback models configured
jq '.roles.coder.models | length' reference-router.json
```

**Solutions**:
- Set `maxFallbackAttempts > 0` (default: 2)
- Add fallback models to role: `models: ["primary", "fallback1", "fallback2"]`
- Check fallback models not all on cooldown
- Verify error classification working (AUTH errors should fail-fast, not fallback)

---

### 6. State File Corruption

**Symptom**: Router fails to start, JSON parse errors

**Diagnosis**:
```bash
# Test JSON validity
python -m json.tool state.json
echo $?  # Non-zero = corrupted

# Check file size (should be small)
ls -lh state.json
```

**Solutions**:
See [state-recovery.md](state-recovery.md) for complete procedures.

**Quick fix**:
```bash
# Reset to empty state
echo '{"cooldowns": {}, "starts": {}}' > state.json
```

---

### 7. Rate Limit Errors Despite Cooldown

**Symptom**: Model hit with rate limit even though cooldown active

**Root causes**:
- Multiple router instances sharing state file (race condition)
- Cooldown buffer too small
- Provider rate limit changed

**Solutions**:
- Use single router instance (see [ARCHITECTURE.md](../ARCHITECTURE.md) concurrency section)
- Increase `cooldownBufferSeconds` (default: 5)
- Update `cooldownSeconds` in quota group to match provider limits
- Implement file locking for concurrent access

---

### 8. Session Router Generation Fails

**Symptom**: Session router file not created or invalid

**Diagnosis**:
```bash
# Check generator script exists
ls -l session_router_generator.py

# Test generation manually
python session_router_generator.py reference-router.json model-catalog.json
```

**Solutions**:
- Verify reference router has valid JSON
- Check model catalog contains referenced models
- Ensure all role models exist in catalog
- Check file permissions for output directory

---

### 9. Model Not Found in Catalog

**Symptom**: "Model X not found" despite being in reference router

**Diagnosis**:
```bash
# Check if model in catalog
jq '.models[] | select(.identifier == "provider-a/model-x")' model-catalog.json

# Check if model in role config
jq '.roles.coder.models[]' reference-router.json
```

**Solutions**:
- Add model to catalog with correct identifier format
- Fix model name typo in reference router
- Verify provider name matches exactly (case-sensitive)
- Regenerate session router after catalog update

---

## Performance Issues

### Slow Spawn Times

**Symptoms**: Spawns take >10 seconds

**Diagnosis steps**:
1. Check if many models on cooldown (forces retries)
2. Check if quota exhausted frequently (causes retry delays)
3. Check if availability test slow (network latency)
4. Monitor number of fallback attempts per spawn

**Solutions**:
- Add more models to reduce cooldown pressure
- Increase quota limits
- Cache availability test results (short TTL)
- Use faster models as primary

### High Fallback Rate

**Symptom**: Avg models per spawn >1.5 (should be ~1.2)

**Root causes**:
- Primary models frequently unavailable
- Provider rate limits too strict
- Cooldown settings too aggressive

**Solutions**:
- Add more capacity to primary models
- Negotiate higher rate limits with providers
- Reduce `cooldownSeconds` after testing
- Use multiple providers for resilience

---

## Debugging Tools

### State Inspector

```python
import json
import time

def inspect_state(state_path):
    with open(state_path) as f:
        state = json.load(f)
    
    now = time.time()
    
    print("=== Cooldowns ===")
    for model, ts in state.get('cooldowns', {}).items():
        remaining = max(0, ts - now)
        print(f"{model}: {remaining:.0f}s remaining")
    
    print("\n=== Quota Usage ===")
    for group, starts in state.get('starts', {}).items():
        print(f"{group}: {len(starts)} recent starts")
        if starts:
            oldest = min(starts)
            age = now - oldest
            print(f"  Oldest: {age:.0f}s ago")
```

### Config Validator

```python
def validate_config(config_path):
    with open(config_path) as f:
        config = json.load(f)
    
    issues = []
    
    # Check required fields
    if 'version' not in config:
        issues.append("Missing version field")
    if 'roles' not in config:
        issues.append("Missing roles field")
    
    # Check each role
    for role_name, role_config in config.get('roles', {}).items():
        if 'models' not in role_config:
            issues.append(f"Role {role_name} missing models array")
        elif len(role_config['models']) == 0:
            issues.append(f"Role {role_name} has empty models array")
        
        if 'quotaGroup' in role_config:
            quota_group = role_config['quotaGroup']
            if quota_group not in config.get('quotaGroups', {}):
                issues.append(f"Role {role_name} references undefined quota group: {quota_group}")
    
    return issues
```

### Test Spawn

```python
async def test_router_spawn(role, task="test"):
    """Test spawn with detailed diagnostics"""
    print(f"Testing spawn for role: {role}")
    
    try:
        result = await corporate_agents.spawn(
            task=task,
            role=role,
            dry_run=False
        )
        print(f"✓ Success! Model: {result.get('model')}")
        return True
    except Exception as e:
        print(f"✗ Failed: {e}")
        print(f"Error type: {type(e).__name__}")
        return False
```

---

## Monitoring Checklist

Regular checks to prevent issues:

- [ ] State file size <1MB (prune if larger)
- [ ] No cooldowns >24h old (indicates stuck state)
- [ ] Quota start history <100 entries per group
- [ ] Fallback rate <30% (should be mostly primary)
- [ ] P95 spawn latency <10s
- [ ] No AUTH errors (indicates config/credential issues)

---

## Getting Help

If troubleshooting fails:

1. **Collect diagnostic info**:
   - Reference router config (sanitized, no credentials)
   - State file snapshot
   - Error messages from logs
   - Recent spawn attempts and outcomes

2. **Check documentation**:
   - [ARCHITECTURE.md](../ARCHITECTURE.md) - System design
   - [state-recovery.md](state-recovery.md) - State corruption fixes
   - [rollback.md](rollback.md) - Configuration rollback

3. **Reproduce minimal example**:
   - Simplest config that shows the issue
   - Exact steps to trigger problem
   - Expected vs actual behavior

4. **Emergency fallback**:
   - Disable router: `{"enabled": false}`
   - Use explicit model parameters
   - Manual spawn with known-good model
