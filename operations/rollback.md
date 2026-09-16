# Router Rollback Procedures

## Overview

When router changes cause problems (failed spawns, wrong models, quota issues), follow these procedures to restore working state.

## Rollback Scenarios

### 1. Bad Configuration Change

**Symptom**: Router fails to spawn agents after config update

**Rollback**:

```bash
# Option A: Restore from version control
git checkout HEAD^ reference-router.json
# Restart router process if needed

# Option B: Restore from backup
cp reference-router.json.backup reference-router.json

# Verify syntax
python -m json.tool reference-router.json > /dev/null && echo "Valid JSON"
```

### 2. Disable Router Completely

**When**: Router causing more problems than it solves

**Procedure**: Set `enabled=false` in reference-router.json

**Effect**: All spawns use explicit model parameter or parent model, bypassing router.

### 3. Revert to Primary Models Only

**When**: Fallback models causing issues (wrong behavior, high cost)

**Procedure**: Remove fallback models from role configurations, keep only primary model.

### 4. Clear All Cooldowns

**When**: Models stuck on cooldown after rate limit errors

```bash
# Backup current state
cp state.json state.json.backup

# Clear cooldowns
jq '.cooldowns = {}' state.json > state.json.tmp && mv state.json.tmp state.json
```

### 5. Reset Quota State

**When**: Quota incorrectly exhausted, blocking all spawns

```bash
# Clear all quota tracking
jq '.starts = {}' state.json > state.json.tmp && mv state.json.tmp state.json
```

### 6. Rollback Model Catalog

**When**: Bad model added to router causing failures

```bash
# Remove model from all roles
jq '.roles |= map_values(.models |= map(select(. != "bad-provider/bad-model")))' reference-router.json > tmp.json
mv tmp.json reference-router.json
```

## Configuration Backup Strategy

### Before Any Change

```bash
# Timestamp backup
cp reference-router.json reference-router.json.$(date +%Y%m%d_%H%M%S)

# Or use git
git add reference-router.json
git commit -m "Save working router config before experiment"
```

## Validation Before Activation

### 1. JSON Syntax

```bash
python -m json.tool reference-router.json > /dev/null
echo $?  # Should be 0
```

### 2. Schema Validation

```bash
# Using jsonschema
jsonschema -i reference-router.json schemas/reference-router.schema.json
```

## Emergency Procedures

### Complete Router Reset

**Use only when**: All other procedures fail, router completely broken.

```bash
# 1. Disable router
jq '.enabled = false' reference-router.json > tmp.json && mv tmp.json reference-router.json

# 2. Clear state
echo '{"cooldowns": {}, "starts": {}}' > state.json

# 3. Verify manual spawns work with explicit model parameter

# 4. Re-enable carefully after investigation
```

### Revert to Session Router Only

**When**: Reference router problematic, but session generation works.

Disable reference router (`enabled=false`), session router generator continues to work independently.

## Monitoring During Rollback

Check these indicators after rollback:

1. **Config valid JSON** - Can be parsed without errors
2. **State file readable** - No corruption
3. **No orphaned cooldowns** - All cooldowns have reasonable timestamps
4. **Quota available** - Start history not exhausted

## Communication

When rolling back in production:

1. **Notify stakeholders**: "Router disabled due to issue X"
2. **Provide workaround**: "Use explicit model parameter"
3. **Set timeline**: "Investigating, expect fix in Y hours"
4. **Document root cause**: Add to ERRATA.md or incident log

## Prevention

### Staged Rollout

Test on single role first, monitor for 1 hour, then expand to other roles if successful.

### Canary Testing

Add new model as fallback only (not primary), so it's only used if primary fails.

### Feature Flags

```json
{
  "version": 2,
  "enabled": true,
  "workflow": {
    "fallbackEnabled": true,
    "sessionGeneration": true
  }
}
```

## See Also

- [state-recovery.md](state-recovery.md) - State file corruption recovery
- [troubleshooting.md](troubleshooting.md) - General troubleshooting
- [ARCHITECTURE.md](../ARCHITECTURE.md) - Router architecture
