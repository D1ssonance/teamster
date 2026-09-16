# Quota Groups Configuration Guide

## Overview

Quota groups limit the rate of agent spawns across roles to prevent overwhelming model providers and ensure fair resource distribution.

## Basic Concepts

**Quota Group**: Named rate limit applying to one or more roles

**Key Parameters**:
- `maxStarts`: Maximum spawns allowed in the time window
- `windowSeconds`: Time window for counting spawns
- `cooldownSeconds`: Cooldown period after hitting the limit

## Configuration Examples

### Example 1: Single Quota Group (Simple)

**Scenario**: All roles share one quota pool

```json
{
  "quotaGroups": {
    "default": {
      "maxStarts": 10,
      "windowSeconds": 60,
      "cooldownSeconds": 60
    }
  },
  "roles": {
    "scout": {
      "models": ["provider-a/model-x"],
      "quotaGroup": "default"
    },
    "coder": {
      "models": ["provider-a/model-y"],
      "quotaGroup": "default"
    }
  }
}
```

**Effect**: Max 10 spawns across all roles per minute

---

### Example 2: Multiple Quota Groups (Role Separation)

**Scenario**: High-priority roles get dedicated quota

```json
{
  "quotaGroups": {
    "critical": {
      "maxStarts": 6,
      "windowSeconds": 30,
      "cooldownSeconds": 30
    },
    "standard": {
      "maxStarts": 10,
      "windowSeconds": 60,
      "cooldownSeconds": 60
    },
    "bulk": {
      "maxStarts": 20,
      "windowSeconds": 120,
      "cooldownSeconds": 120
    }
  },
  "roles": {
    "debugger": {
      "models": ["provider-a/expert"],
      "quotaGroup": "critical"
    },
    "coder": {
      "models": ["provider-a/standard"],
      "quotaGroup": "standard"
    },
    "scout": {
      "models": ["provider-b/fast"],
      "quotaGroup": "bulk"
    }
  }
}
```

**Effect**: Critical roles isolated from bulk workload

---

### Example 3: Provider-Based Quotas

**Scenario**: Different quotas per provider

```json
{
  "quotaGroups": {
    "provider-a-quota": {
      "maxStarts": 8,
      "windowSeconds": 60,
      "cooldownSeconds": 90
    },
    "provider-b-quota": {
      "maxStarts": 15,
      "windowSeconds": 60,
      "cooldownSeconds": 45
    }
  },
  "roles": {
    "coder": {
      "models": ["provider-a/model-x"],
      "quotaGroup": "provider-a-quota"
    },
    "scout": {
      "models": ["provider-b/model-y"],
      "quotaGroup": "provider-b-quota"
    }
  }
}
```

**Effect**: Respects different provider rate limits independently

---

### Example 4: Time-of-Day Quotas (Manual Switch)

**Scenario**: Higher limits during off-peak hours

```json
// peak-hours-config.json
{
  "quotaGroups": {
    "fast": {
      "maxStarts": 6,
      "windowSeconds": 60,
      "cooldownSeconds": 60
    }
  }
}

// off-peak-config.json
{
  "quotaGroups": {
    "fast": {
      "maxStarts": 20,
      "windowSeconds": 60,
      "cooldownSeconds": 30
    }
  }
}
```

**Effect**: Higher capacity when system less busy

---

### Example 5: Progressive Cooldown

**Scenario**: Longer cooldown discourages repeated rate limit hits

```json
{
  "quotaGroups": {
    "adaptive": {
      "maxStarts": 10,
      "windowSeconds": 60,
      "cooldownSeconds": 120
    }
  }
}
```

**Effect**: 2-minute cooldown prevents rapid retry bursts

---

## Quota Design Patterns

### Pattern 1: Conservative (Safety First)

```json
{
  "maxStarts": 5,
  "windowSeconds": 60,
  "cooldownSeconds": 120
}
```

**Use when**: Testing new provider, unknown rate limits, production safety

---

### Pattern 2: Aggressive (High Throughput)

```json
{
  "maxStarts": 20,
  "windowSeconds": 30,
  "cooldownSeconds": 30
}
```

**Use when**: Known stable provider, high capacity, dev environment

---

### Pattern 3: Burst-Tolerant

```json
{
  "maxStarts": 10,
  "windowSeconds": 10,
  "cooldownSeconds": 60
}
```

**Use when**: Need to handle sudden workload spikes

---

### Pattern 4: Steady-State

```json
{
  "maxStarts": 30,
  "windowSeconds": 300,
  "cooldownSeconds": 300
}
```

**Use when**: Predictable load, long-running tasks

---

## Tuning Guide

### Step 1: Start Conservative

```json
{
  "maxStarts": 5,
  "windowSeconds": 60,
  "cooldownSeconds": 90
}
```

### Step 2: Monitor for 1 Week

Track:
- Cooldown frequency (should be <10% of spawns)
- Rate limit errors (should be near zero)
- Queue delays (should be minimal)

### Step 3: Adjust

**If frequent cooldowns**: Increase `maxStarts` or `windowSeconds`

**If rate limit errors**: Decrease `maxStarts` or increase `cooldownSeconds`

**If queue delays**: Add more models or quota groups

### Step 4: Optimize

```json
{
  "maxStarts": 8,           // Increased from 5
  "windowSeconds": 60,      // Kept same
  "cooldownSeconds": 60     // Reduced from 90
}
```

---

## Common Mistakes

### ❌ Too Aggressive

```json
{
  "maxStarts": 100,
  "windowSeconds": 10,
  "cooldownSeconds": 5
}
```

**Problem**: Will hit provider rate limits, causes cascading failures

---

### ❌ All Roles Share One Group

```json
{
  "quotaGroups": {
    "everything": { ... }
  }
}
```

**Problem**: Bulk work blocks critical roles

**Fix**: Separate critical roles into dedicated quota group

---

### ❌ Cooldown Too Short

```json
{
  "cooldownSeconds": 5
}
```

**Problem**: Rapid retry after rate limit hit, compounds problem

**Fix**: Use at least 60s cooldown for provider rate limits

---

### ❌ Window Too Large

```json
{
  "windowSeconds": 3600  // 1 hour
}
```

**Problem**: Old spawns counted forever, capacity never recovers

**Fix**: Use 60-300s windows for responsive quota management

---

## Monitoring Metrics

Track these per quota group:

```python
def analyze_quota_usage(state_path, quota_config):
    with open(state_path) as f:
        state = json.load(f)
    
    for group_name, group_config in quota_config.items():
        starts = state.get('starts', ).get(group_name, [])
        now = time.time()
        window = group_config['windowSeconds']
        
        # Count recent starts
        recent = [s for s in starts if s > now - window]
        utilization = len(recent) / group_config['maxStarts']
        
        print(f"{group_name}:")
        print(f"  Utilization: {utilization:.0%}")
        print(f"  Recent starts: {len(recent)}/{group_config['maxStarts']}")
```

**Healthy metrics**:
- Utilization 40-80% (not too idle, not maxed out)
- Cooldown frequency <10%
- Rate limit errors near zero

---

## Advanced: Dynamic Quota Adjustment

**Future enhancement** (not implemented in Phase 2):

```python
def adjust_quota_dynamically(group_name, error_rate):
    if error_rate > 0.05:  # >5% rate limit errors
        # Reduce capacity
        config['quotaGroups'][group_name]['maxStarts'] *= 0.8
    elif error_rate == 0 and utilization < 0.5:
        # Increase capacity
        config['quotaGroups'][group_name]['maxStarts'] *= 1.2
```

---

## See Also

- [../ARCHITECTURE.md](../ARCHITECTURE.md) - Quota management design
- [troubleshooting.md](../operations/troubleshooting.md) - Quota exhaustion fixes
- [state-recovery.md](../operations/state-recovery.md) - Manual quota reset
