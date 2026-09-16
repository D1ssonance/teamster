# First Run Instructions

## Prerequisites

1. **Check configuration files**:
   - `reference-router.json` - reference router with role definitions
   - `session-router-*.json` - generated session routers (if any exist)

2. **Verify model availability**:
   - All models in `reference-router.json` must be accessible through your gateway
   - Check authentication and endpoint configuration

## Quick Start

### Step 1: Inspect Reference Router

```bash
cat reference-router.json
```

Verify:
- Role definitions are correct
- Model identifiers match your gateway
- Quota groups are configured (if using quota management)
- Rate limits are reasonable for your environment

### Step 2: Generate Session Router

Run the session router generator:

```bash
python3 session_router_generator.py \
  --reference reference-router.json \
  --output session-router-$(date +%Y%m%d-%H%M%S).json
```

This will:
- Load the reference router
- Generate session-specific configuration
- Save to a timestamped session file
- Report generation status

### Step 3: Test Basic Functionality

#### Test 1: Verify session router is valid

```bash
python3 -c "import json; print(json.load(open('session-router.json'))['meta']['version'])"
```

Expected: Should print version number without errors

#### Test 2: Check model fallback chains

```bash
python3 -c "
import json
router = json.load(open('session-router.json'))
for role, config in router['roles'].items():
    print(f'{role}: {len(config["models"])} models')
"
```

Expected: Each role should show its fallback chain length

### Step 4: Integration Test (Pseudocode)

Use your agent framework to test role-based spawning:

```python
# Pseudocode - adapt to your framework
agent_runtime = YourAgentRuntime(router_path='session-router-*.json')

# Test spawning with each role
for role in ['scout', 'coder', 'reviewer']:
    try:
        child = await agent_runtime.spawn(
            role=role,
            objective='Test task',
            read_scope=['/workspace/test']
        )
        print(f'{role}: ✓ spawned successfully')
    except Exception as e:
        print(f'{role}: ✗ failed - {e}')
```

## Common Issues

### Issue 1: Model not found

**Symptom**: Error during spawn: "Model X not available"

**Fix**:
1. Check model identifier in reference router
2. Verify gateway access to that model
3. Update reference router if model was renamed/removed
4. Regenerate session router

### Issue 2: Quota exhausted immediately

**Symptom**: First spawn fails with quota error

**Fix**:
1. Check `maxStarts` in quota group config
2. Verify no leaked reservations from previous runs
3. Increase quota limits if needed
4. Implement cleanup of stale reservations

### Issue 3: Rate limit triggered unexpectedly

**Symptom**: Cooldown applied on first spawn

**Fix**:
1. Check cooldown state file for stale entries
2. Verify cooldown duration is reasonable
3. Clear state file if corrupted
4. Adjust `windowSeconds` in rate limit config

## Next Steps

1. Read `ARCHITECTURE.md` - understand the two-tier design
2. Read `implementation/fallback-execution-pseudocode.md` - see the retry logic
3. Check `ERRATA.md` - known issues and fixes
4. Review `methodology/` - testing and evaluation procedures

## Support

If issues persist:
1. Check logs for detailed error messages
2. Verify state files aren't corrupted
3. Review configuration against templates
4. Test with minimal single-role config first
