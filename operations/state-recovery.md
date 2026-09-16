# State File Recovery Procedures

## Overview

The router state file (`state.json`) tracks cooldowns and quota usage. Corruption or inconsistency can block spawns or cause quota violations.

## State File Structure

```json
{
  "cooldowns": {
    "provider-a/model-x": 1735000000.123,
    "provider-b/model-y": 1735001000.456
  },
  "starts": {
    "fast": [1735000000, 1735000005, 1735000010]
  }
}
```

## Detection

### Symptoms of Corrupted State

1. **Router fails to start**
   - Error: `JSONDecodeError` or `FileNotFoundError`
   - Cause: Corrupted or missing state file

2. **All models on cooldown**
   - Error: "No available models"
   - Cause: Stale cooldown timestamps from crashed process

3. **Quota always exhausted**
   - Error: "Quota group exhausted"
   - Cause: Start records not pruned, accumulated indefinitely

4. **Router ignores cooldowns**
   - Symptom: Rate limit errors despite cooldown
   - Cause: State file not being read or written

## Recovery Procedures

### 1. Validate State File

```python
import json

def validate_state(state_path):
    """Check state file for corruption"""
    try:
        with open(state_path, 'r') as f:
            state = json.load(f)
        
        # Check required keys
        assert 'cooldowns' in state
        assert 'starts' in state
        
        # Check types
        assert isinstance(state['cooldowns'], dict)
        assert isinstance(state['starts'], dict)
        
        # Check cooldown timestamps are numbers
        for model, timestamp in state['cooldowns'].items():
            assert isinstance(timestamp, (int, float))
        
        # Check start arrays contain numbers
        for group, starts in state['starts'].items():
            assert isinstance(starts, list)
            assert all(isinstance(t, (int, float)) for t in starts)
        
        print(f"✓ State file valid: {len(state['cooldowns'])} cooldowns, {sum(len(s) for s in state['starts'].values())} starts")
        return True
        
    except FileNotFoundError:
        print("✗ State file not found")
        return False
    except json.JSONDecodeError as e:
        print(f"✗ Invalid JSON: {e}")
        return False
    except AssertionError as e:
        print(f"✗ Invalid structure: {e}")
        return False
```

### 2. Reset State File

**When**: Corrupted JSON, invalid structure, or unrecoverable state.

```bash
# Backup existing state
cp state.json state.json.corrupt.$(date +%s)

# Reset to empty state
echo '{"cooldowns": {}, "starts": {}}' > state.json

# Verify
cat state.json | python -m json.tool
```

### 3. Prune Stale Data

**When**: Quota always exhausted, state file growing indefinitely.

```python
import time
import json

def prune_state(state_path, max_window_seconds=60):
    """Remove old timestamps outside quota windows"""
    with open(state_path, 'r') as f:
        state = json.load(f)
    
    now = time.time()
    cutoff = now - max_window_seconds
    
    # Prune old start timestamps
    for group in state['starts']:
        old_count = len(state['starts'][group])
        state['starts'][group] = [t for t in state['starts'][group] if t >= cutoff]
        new_count = len(state['starts'][group])
        print(f"{group}: removed {old_count - new_count} old timestamps")
    
    # Remove expired cooldowns
    expired = [model for model, ts in state['cooldowns'].items() if ts < now]
    for model in expired:
        del state['cooldowns'][model]
    print(f"Removed {len(expired)} expired cooldowns")
    
    # Write back
    with open(state_path, 'w') as f:
        json.dump(state, f, indent=2)
```

### 4. Clear Stuck Cooldowns

**When**: Process crashed, cooldowns preventing all spawns.

```bash
# View current cooldowns
jq '.cooldowns' state.json

# Remove specific model cooldown
jq '.cooldowns |= del(.["provider-a/model-x"])' state.json > state.json.tmp
mv state.json.tmp state.json

# Clear ALL cooldowns (emergency)
jq '.cooldowns = {}' state.json > state.json.tmp
mv state.json.tmp state.json
```

### 5. Manual Quota Reset

**When**: Quota group stuck, all spawns failing.

```bash
# Clear start history for quota group
jq '.starts.fast = []' state.json > state.json.tmp
mv state.json.tmp state.json

# Clear ALL quota groups
jq '.starts = {}' state.json > state.json.tmp
mv state.json.tmp state.json
```

## Prevention

### Atomic Writes

Always write state atomically:

```python
import json
import tempfile
import os

def save_state(state, state_path):
    """Atomic state write with backup"""
    # Backup existing
    if os.path.exists(state_path):
        backup = f"{state_path}.backup"
        os.replace(state_path, backup)
    
    # Write to temp file
    with tempfile.NamedTemporaryFile('w', delete=False) as f:
        json.dump(state, f, indent=2)
        temp_path = f.name
    
    # Atomic rename
    os.replace(temp_path, state_path)
```

### State Validation on Load

```python
def load_state(state_path):
    """Load state with validation and auto-recovery"""
    try:
        with open(state_path, 'r') as f:
            state = json.load(f)
        
        # Validate structure
        if not isinstance(state.get('cooldowns'), dict):
            raise ValueError("Invalid cooldowns")
        if not isinstance(state.get('starts'), dict):
            raise ValueError("Invalid starts")
        
        return state
        
    except (FileNotFoundError, json.JSONDecodeError, ValueError) as e:
        print(f"Warning: State file issue ({e}), starting fresh")
        return {"cooldowns": {}, "starts": {}}
```

### Periodic Maintenance

```bash
# Daily cron job to prune old data
0 2 * * * /path/to/prune_state.py --state /path/to/state.json --max-age 3600
```

## Monitoring

### Health Checks

```python
def check_state_health(state_path, config):
    """Health check for state file"""
    issues = []
    
    with open(state_path, 'r') as f:
        state = json.load(f)
    
    # Check cooldown count
    cooldown_count = len(state['cooldowns'])
    if cooldown_count > 10:
        issues.append(f"High cooldown count: {cooldown_count}")
    
    # Check start history size
    for group, starts in state['starts'].items():
        if len(starts) > 100:
            issues.append(f"Large start history for {group}: {len(starts)}")
    
    # Check file size
    file_size = os.path.getsize(state_path)
    if file_size > 1_000_000:  # 1 MB
        issues.append(f"Large state file: {file_size} bytes")
    
    return issues
```

## Emergency Contacts

When state corruption blocks critical work:

1. **Quick fix**: Reset state file (loses cooldown protection)
2. **Investigation**: Check logs for write errors, concurrent access
3. **Prevention**: Implement file locking if multiple router instances

## See Also

- [ARCHITECTURE.md](../ARCHITECTURE.md) - Concurrency & Thread Safety section
- [troubleshooting.md](troubleshooting.md) - General troubleshooting guide
