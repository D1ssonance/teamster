# Migration Guide

## Overview

This guide covers migrating from manual model selection to the corporate router, and upgrading between router versions.

## Migration Scenarios

### 1. From Manual Model Selection

**Before** (manual):
```python
# Explicit model in every spawn
result = await rlm(
    task="Implement feature X",
    model="provider-a/specific-model"
)
```

**After** (router):
```python
# Router selects model based on role
result = await corporate_agents.spawn(
    task="Implement feature X",
    role="coder",  # Router picks best model for role
    read=["/workspace"],
    write=["/workspace/src"]
)
```

**Migration steps**:

1. **Audit existing spawns**:
   ```bash
   # Find all manual model spawns
   grep -r "model=" . --include="*.py" | grep "await rlm"
   ```

2. **Map models to roles**:
   ```python
   # Document which models are used for what
   model_usage = {
       "provider-a/fast-model": ["scout", "reviewer"],
       "provider-a/smart-model": ["coder", "debugger"],
       "provider-b/vision-model": ["vision"]
   }
   ```

3. **Configure router**:
   ```json
   {
     "roles": {
       "scout": {
         "models": ["provider-a/fast-model"]
       },
       "coder": {
         "models": ["provider-a/smart-model"]
       }
     }
   }
   ```

4. **Gradual rollout**:
   - Enable router: `"enabled": true`
   - Test on one role first
   - Monitor for 1 week
   - Expand to all roles

5. **Remove manual model parameters**:
   ```python
   # Old
   await rlm(task, model="provider-a/model-x")
   
   # New
   await corporate_agents.spawn(task, role="coder")
   ```

---

### 2. Router v1 → v2 Migration

**Changes in v2**:
- Added `quotaGroup` field to roles
- Added `maxFallbackAttempts` global setting
- Added `cooldownBufferSeconds`
- Added JSON Schema support

**Migration steps**:

1. **Backup v1 config**:
   ```bash
   cp reference-router.json reference-router.v1.backup
   ```

2. **Update version field**:
   ```json
   {
     "version": 2,  // Changed from 1
     ...
   }
   ```

3. **Add quota groups to roles**:
   ```json
   {
     "roles": {
       "coder": {
         "models": [...],
         "quotaGroup": "fast"  // NEW: Required in v2
       }
     }
   }
   ```

4. **Add new global fields**:
   ```json
   {
     "maxFallbackAttempts": 2,      // NEW
     "cooldownBufferSeconds": 5,    // NEW
     ...
   }
   ```

5. **Validate against schema**:
   ```bash
   jsonschema -i reference-router.json schemas/reference-router.schema.json
   ```

6. **Test before production**:
   ```python
   # Load and verify config
   with open('reference-router.json') as f:
       config = json.load(f)
   
   assert config['version'] == 2
   for role in config['roles'].values():
       assert 'quotaGroup' in role
   ```

---

### 3. Single Provider → Multi-Provider

**Before**:
```json
{
  "allowedProviders": ["provider-a"],
  "roles": {
    "coder": {
      "models": ["provider-a/model-x"]
    }
  }
}
```

**After**:
```json
{
  "allowedProviders": ["provider-a", "provider-b"],
  "roles": {
    "coder": {
      "models": [
        "provider-a/model-x",     // Primary
        "provider-b/model-y"      // Fallback from different provider
      ],
      "quotaGroup": "fast"
    }
  }
}
```

**Benefits**:
- Resilience: Provider A outage → automatically use Provider B
- Load balancing: Distribute across providers
- Cost optimization: Use cheaper provider as fallback

**Migration steps**:

1. **Add provider credentials**:
   - Obtain API keys for new provider
   - Configure in corporate gateway
   - Test manual spawn with new provider

2. **Add to allowedProviders**:
   ```json
   "allowedProviders": ["provider-a", "provider-b"]
   ```

3. **Add fallback models**:
   ```json
   "models": [
     "provider-a/primary",
     "provider-b/fallback"
   ]
   ```

4. **Test fallback**:
   - Trigger rate limit on provider-a
   - Verify provider-b used automatically
   - Check logs for model selection

5. **Monitor cross-provider usage**:
   - Track which provider used per spawn
   - Adjust if one provider overwhelmed

---

### 4. No Quotas → Quota Groups

**Before**:
```json
{
  // No quota limits, relied on provider rate limits
  "roles": {
    "coder": {
      "models": ["provider-a/model-x"]
    }
  }
}
```

**After**:
```json
{
  "quotaGroups": {
    "fast": {
      "maxStarts": 6,
      "windowSeconds": 15,
      "cooldownSeconds": 45
    }
  },
  "roles": {
    "coder": {
      "models": ["provider-a/model-x"],
      "quotaGroup": "fast"
    }
  }
}
```

**Why**:
- Prevents overwhelming providers
- Ensures fair resource distribution
- Enables proactive cooldowns (avoid rate limit errors)

**Migration steps**:

1. **Analyze current usage**:
   ```python
   # Count spawns per hour over last week
   spawns_per_hour = analyze_logs()
   peak_rate = max(spawns_per_hour)
   print(f"Peak: {peak_rate} spawns/hour")
   ```

2. **Design conservative quota**:
   ```python
   # Start with 2x peak rate
   max_starts = peak_rate * 2 / 60  # Per minute
   
   quota = {
       "maxStarts": int(max_starts),
       "windowSeconds": 60,
       "cooldownSeconds": 60
   }
   ```

3. **Add quota group**:
   ```json
   "quotaGroups": {
     "standard": {
       "maxStarts": 10,
       "windowSeconds": 60,
       "cooldownSeconds": 60
     }
   }
   ```

4. **Assign roles to quota group**:
   ```json
   "roles": {
     "coder": { "quotaGroup": "standard" },
     "scout": { "quotaGroup": "standard" }
   }
   ```

5. **Monitor and tune**:
   - Track quota utilization
   - Increase if frequently exhausted
   - Decrease if never approaching limit

---

## Data Migration

### State File Format Changes

**v1 state** (hypothetical):
```json
{
  "cooldowns": {
    "provider/model": 1735000000
  }
}
```

**v2 state**:
```json
{
  "cooldowns": {
    "provider/model": 1735000000
  },
  "starts": {
    "fast": [1735000000, 1735000005]
  }
}
```

**Migration**:
```python
def migrate_state_v1_to_v2(state_v1):
    """Add quota tracking to v1 state"""
    state_v2 = state_v1.copy()
    state_v2['starts'] = {}  # Initialize quota tracking
    return state_v2
```

---

## Rollback Plan

If migration fails:

1. **Disable router**:
   ```json
   {"enabled": false}
   ```

2. **Revert to backup**:
   ```bash
   cp reference-router.v1.backup reference-router.json
   ```

3. **Use explicit models temporarily**:
   ```python
   # Bypass router during incident
   await rlm(task, model="provider-a/known-good-model")
   ```

4. **Investigate issue**:
   - Check logs for errors
   - Validate configuration syntax
   - Test with dry run

5. **Fix and re-enable**:
   ```json
   {"enabled": true}
   ```

---

## Testing Migration

### Pre-Migration Tests

```python
def test_pre_migration():
    """Verify current system works"""
    # Test manual spawn
    result = await rlm(task, model="provider-a/model-x")
    assert result is not None
    
    # Measure baseline latency
    latency = measure_spawn_latency()
    assert latency < 5.0
```

### Post-Migration Tests

```python
def test_post_migration():
    """Verify router works"""
    # Test router spawn
    result = await corporate_agents.spawn(task, role="coder")
    assert result is not None
    
    # Verify router active
    config = load_router_config()
    assert config['enabled'] == True
    
    # Test fallback
    trigger_rate_limit()
    result = await corporate_agents.spawn(task, role="coder")
    assert result.model != primary_model  # Used fallback
```

---

## Migration Checklist

- [ ] Backup current configuration
- [ ] Backup current state file
- [ ] Test router in staging environment
- [ ] Update configuration to new format
- [ ] Validate configuration syntax
- [ ] Enable router with `"enabled": true`
- [ ] Test single role first
- [ ] Monitor for 24 hours
- [ ] Expand to all roles
- [ ] Update documentation/runbooks
- [ ] Remove old manual model parameters
- [ ] Archive old configuration

---

## Timeline Recommendations

### Small Installation (<10 roles, single provider)
- Planning: 1 day
- Implementation: 2 hours
- Testing: 1 day
- Rollout: 1 day
- **Total: 3 days**

### Medium Installation (10-20 roles, 2-3 providers)
- Planning: 2 days
- Implementation: 4 hours
- Testing: 3 days
- Rollout: 1 week
- **Total: 2 weeks**

### Large Installation (>20 roles, multiple providers)
- Planning: 1 week
- Implementation: 1 day
- Testing: 1 week
- Rollout: 2 weeks
- **Total: 1 month**

---

## See Also

- [INSTALLATION.md](INSTALLATION.md) - Fresh installation guide
- [operations/rollback.md](operations/rollback.md) - Rollback procedures
- [operations/troubleshooting.md](operations/troubleshooting.md) - Common issues
