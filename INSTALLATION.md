# Router Installation Guide

## Prerequisites

- Python 3.8+
- Access to model provider APIs (credentials/tokens)
- Write permissions for state file directory

## Installation Steps

### 1. Install Dependencies

```bash
# Core dependencies
pip install pyyaml  # For YAML config parsing (optional)

# No additional dependencies required for basic router
# JSON parsing uses stdlib
```

### 2. Create Directory Structure

```bash
# Create router configuration directory
mkdir -p ~/.prime/agent/router-reference

# Create state file directory (writable)
mkdir -p ~/.prime/agent/router-state

# Set permissions
chmod 755 ~/.prime/agent/router-reference
chmod 755 ~/.prime/agent/router-state
```

### 3. Copy Router Files

```bash
# Copy reference router configuration
cp reference-router.json ~/.prime/agent/router-reference/

# Copy session router generator
cp session_router_generator.py ~/.prime/agent/router-reference/

# Create empty state file
echo '{"cooldowns": {}, "starts": {}}' > ~/.prime/agent/router-state/state.json
```

### 4. Configure Router

Edit `~/.prime/agent/router-reference/reference-router.json`:

```json
{
  "version": 2,
  "enabled": true,
  "allowedProviders": ["your-provider-name"],
  "stateFile": "/home/user/.prime/agent/router-state/state.json",
  "cooldownBufferSeconds": 5,
  "maxFallbackAttempts": 2,
  "quotaGroups": {
    "fast": {
      "maxStarts": 6,
      "windowSeconds": 15,
      "cooldownSeconds": 45
    }
  },
  "maxConcurrentPerProvider": {
    "your-provider-name": 3
  },
  "roles": {
    "coder": {
      "models": [
        "your-provider-name/your-model-name"
      ],
      "quotaGroup": "fast"
    }
  }
}
```

**Required changes**:
- Replace `your-provider-name` with actual provider
- Replace `your-model-name` with actual model identifier
- Update `stateFile` path to absolute path
- Configure all roles you need

### 5. Validate Configuration

```bash
# Check JSON syntax
python -m json.tool ~/.prime/agent/router-reference/reference-router.json

# Validate against schema (optional)
pip install jsonschema
jsonschema -i ~/.prime/agent/router-reference/reference-router.json            -s schemas/reference-router.schema.json
```

### 6. Test Router

```python
# Test configuration loads
import json

with open('/home/user/.prime/agent/router-reference/reference-router.json') as f:
    config = json.load(f)

print(f"Router enabled: {config['enabled']}")
print(f"Roles configured: {list(config['roles'].keys())}")
print(f"Quota groups: {list(config['quotaGroups'].keys())}")
```

### 7. Integrate with Corporate Agents

Edit `~/.prime/agent/skills/corporate-agents/src/corporate_agents/__init__.py`:

```python
# Point to router configuration
ROUTER_CONFIG_PATH = "/home/user/.prime/agent/router-reference/reference-router.json"

# Verify in spawn function
def spawn(...):
    router = load_router(ROUTER_CONFIG_PATH)
    # ... rest of spawn logic
```

### 8. First Spawn Test

```python
from corporate_agents import spawn

# Test spawn with router
result = await spawn(
    task="Test spawn",
    role="coder",
    read=["/workspace"],
    write=[]
)

print(f"Spawned with model: {result.model}")
```

---

## Verification Checklist

- [ ] Configuration file is valid JSON
- [ ] State file created and writable
- [ ] All provider names match corporate gateway
- [ ] All model identifiers exist in provider catalog
- [ ] Quota limits are reasonable (not too aggressive)
- [ ] At least one role configured
- [ ] Test spawn succeeds

---

## Common Installation Issues

### Issue: JSON Parse Error

**Symptom**: `json.JSONDecodeError` when loading config

**Fix**:
```bash
# Validate JSON
python -m json.tool reference-router.json

# Common issues: trailing commas, missing quotes
```

### Issue: State File Permission Denied

**Symptom**: Cannot write to state.json

**Fix**:
```bash
# Check permissions
ls -l state.json

# Fix permissions
chmod 644 state.json
chmod 755 $(dirname state.json)
```

### Issue: Router Not Active

**Symptom**: Spawns bypass router

**Fix**:
```json
{
  "enabled": true  // Make sure this is true, not false
}
```

### Issue: Model Not Found

**Symptom**: "Model X not found in catalog"

**Fix**:
- Verify model name exactly matches provider format
- Check model exists in provider's available models
- Regenerate session router after config change

---

## Directory Structure After Installation

```
~/.prime/agent/
├── router-reference/
│   ├── reference-router.json       # Main configuration
│   └── session_router_generator.py # Generator script
├── router-state/
│   └── state.json                  # Runtime state
└── skills/
    └── corporate-agents/
        └── src/corporate_agents/
            └── __init__.py         # Integration point
```

---

## Environment Variables (Optional)

```bash
# Override config path
export ROUTER_CONFIG=/custom/path/reference-router.json

# Override state file path
export ROUTER_STATE=/custom/path/state.json

# Enable debug logging
export ROUTER_DEBUG=1
```

---

## Uninstallation

```bash
# Remove router files
rm -rf ~/.prime/agent/router-reference
rm -rf ~/.prime/agent/router-state

# Disable in corporate agents
# Set enabled=false or remove router integration
```

---

## Next Steps

After successful installation:

1. **Configure monitoring** - See [MONITORING.md](MONITORING.md)
2. **Tune quotas** - See [operations/quota-configuration.md](operations/quota-configuration.md)
3. **Test fallback** - Trigger rate limit to verify fallback works
4. **Read troubleshooting** - Familiarize with [operations/troubleshooting.md](operations/troubleshooting.md)

---

## Getting Help

If installation fails:

1. Check [FIRST-RUN.md](FIRST-RUN.md) for initial setup guide
2. See [operations/troubleshooting.md](operations/troubleshooting.md)
3. Verify prerequisites met (Python version, file permissions)
4. Test configuration syntax separately before integration
