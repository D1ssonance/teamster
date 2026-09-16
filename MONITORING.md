# Monitoring Setup Guide

## Overview

Monitor router health, quota usage, fallback rates, and error patterns to ensure reliable operation.

## Metrics to Track

### 1. Spawn Success Rate

**What**: Percentage of successful spawns vs failures

**Target**: >95%

**Collection**:
```python
spawn_attempts = 0
spawn_successes = 0

async def spawn_with_metrics(*args, **kwargs):
    global spawn_attempts, spawn_successes
    spawn_attempts += 1
    
    try:
        result = await corporate_agents.spawn(*args, **kwargs)
        spawn_successes += 1
        return result
    except Exception as e:
        logger.error(f"Spawn failed: {e}")
        raise

# Report
success_rate = spawn_successes / spawn_attempts if spawn_attempts > 0 else 0
print(f"Success rate: {success_rate:.1%}")
```

---

### 2. Fallback Rate

**What**: How often fallback models are used

**Target**: <30% (most spawns use primary model)

**Collection**:
```python
primary_used = 0
fallback_used = 0

def track_model_selection(selected_model, role_config):
    global primary_used, fallback_used
    
    if selected_model == role_config['models'][0]:
        primary_used += 1
    else:
        fallback_used += 1

# Report
fallback_rate = fallback_used / (primary_used + fallback_used)
print(f"Fallback rate: {fallback_rate:.1%}")
```

---

### 3. Cooldown Frequency

**What**: How often models hit rate limits and enter cooldown

**Target**: <10% of spawns trigger cooldown

**Collection**:
```python
cooldown_events = 0
total_spawns = 0

def track_cooldown_event():
    global cooldown_events
    cooldown_events += 1

# Report
cooldown_frequency = cooldown_events / total_spawns if total_spawns > 0 else 0
print(f"Cooldown frequency: {cooldown_frequency:.1%}")
```

---

### 4. Quota Utilization

**What**: How much of each quota group's capacity is used

**Target**: 40-80% (not idle, not maxed out)

**Collection**:
```python
import time
import json

def measure_quota_utilization(state_path, config):
    with open(state_path) as f:
        state = json.load(f)
    
    now = time.time()
    
    for group_name, group_config in config['quotaGroups'].items():
        starts = state.get('starts', {}).get(group_name, [])
        window = group_config['windowSeconds']
        
        # Count recent starts
        recent = [s for s in starts if s > now - window]
        max_starts = group_config['maxStarts']
        utilization = len(recent) / max_starts
        
        print(f"{group_name}: {utilization:.0%} ({len(recent)}/{max_starts})")
```

---

### 5. Spawn Latency

**What**: Time from spawn request to agent ready

**Target**: P95 <10s

**Collection**:
```python
import time

latencies = []

async def spawn_with_timing(*args, **kwargs):
    start = time.time()
    result = await corporate_agents.spawn(*args, **kwargs)
    latency = time.time() - start
    latencies.append(latency)
    return result

# Report
import statistics
if latencies:
    p50 = statistics.median(latencies)
    p95 = statistics.quantiles(latencies, n=20)[18]  # 95th percentile
    print(f"P50 latency: {p50:.2f}s")
    print(f"P95 latency: {p95:.2f}s")
```

---

### 6. Error Distribution

**What**: Breakdown of error types

**Target**: AUTH <1%, RATE_LIMIT <5%, UNKNOWN <10%

**Collection**:
```python
from collections import Counter

error_counts = Counter()

def track_error(error_type):
    error_counts[error_type.value] += 1

# Report
total_errors = sum(error_counts.values())
for error_type, count in error_counts.most_common():
    pct = count / total_errors if total_errors > 0 else 0
    print(f"{error_type}: {count} ({pct:.1%})")
```

---

## Monitoring Implementation

### Simple File-Based Logging

```python
import json
import time

def log_spawn_event(event_type, **data):
    """Append event to monitoring log"""
    event = {
        "timestamp": time.time(),
        "type": event_type,
        **data
    }
    
    with open("/var/log/router-metrics.jsonl", "a") as f:
        f.write(json.dumps(event) + "\n")

# Usage
log_spawn_event("spawn_success", role="coder", model="provider-a/model-x", latency=2.3)
log_spawn_event("spawn_failure", role="scout", error_type="RATE_LIMIT")
log_spawn_event("fallback_used", role="coder", primary="model-x", fallback="model-y")
```

### Daily Report Generation

```python
import json
from datetime import datetime, timedelta
from collections import Counter

def generate_daily_report(log_path):
    """Analyze last 24 hours of metrics"""
    cutoff = time.time() - 86400  # 24 hours ago
    
    successes = 0
    failures = 0
    fallbacks = 0
    error_types = Counter()
    latencies = []
    
    with open(log_path) as f:
        for line in f:
            event = json.loads(line)
            if event['timestamp'] < cutoff:
                continue
            
            if event['type'] == 'spawn_success':
                successes += 1
                if 'latency' in event:
                    latencies.append(event['latency'])
            elif event['type'] == 'spawn_failure':
                failures += 1
                error_types[event.get('error_type', 'UNKNOWN')] += 1
            elif event['type'] == 'fallback_used':
                fallbacks += 1
    
    total = successes + failures
    
    print("=== Router Daily Report ===")
    print(f"Date: {datetime.now().strftime('%Y-%m-%d')}")
    print(f"\nSpawn Statistics:")
    print(f"  Total: {total}")
    print(f"  Success: {successes} ({successes/total:.1%})")
    print(f"  Failed: {failures} ({failures/total:.1%})")
    print(f"  Fallback rate: {fallbacks/total:.1%}")
    
    if latencies:
        print(f"\nLatency:")
        print(f"  Median: {statistics.median(latencies):.2f}s")
        print(f"  P95: {statistics.quantiles(latencies, n=20)[18]:.2f}s")
    
    if error_types:
        print(f"\nError Types:")
        for error_type, count in error_types.most_common():
            print(f"  {error_type}: {count}")
```

---

## Alerting Rules

### Critical Alerts (Immediate Action)

```python
def check_critical_alerts(metrics):
    alerts = []
    
    # Success rate too low
    if metrics['success_rate'] < 0.80:  # <80%
        alerts.append(f"CRITICAL: Success rate {metrics['success_rate']:.1%} < 80%")
    
    # All models on cooldown
    if metrics['available_models'] == 0:
        alerts.append("CRITICAL: No models available (all on cooldown)")
    
    # AUTH errors present
    if metrics['auth_errors'] > 0:
        alerts.append(f"CRITICAL: {metrics['auth_errors']} AUTH errors (check credentials)")
    
    return alerts
```

### Warning Alerts (Investigate Soon)

```python
def check_warning_alerts(metrics):
    alerts = []
    
    # High fallback rate
    if metrics['fallback_rate'] > 0.50:  # >50%
        alerts.append(f"WARNING: High fallback rate {metrics['fallback_rate']:.1%}")
    
    # High quota utilization
    for group, util in metrics['quota_utilization'].items():
        if util > 0.90:  # >90%
            alerts.append(f"WARNING: Quota group {group} at {util:.0%}")
    
    # Slow spawns
    if metrics['p95_latency'] > 15:  # >15s
        alerts.append(f"WARNING: P95 latency {metrics['p95_latency']:.1f}s > 15s")
    
    return alerts
```

---

## Dashboard Visualization

### Terminal Dashboard (Simple)

```python
def print_dashboard(metrics):
    print("\n" + "="*60)
    print("Router Health Dashboard")
    print("="*60)
    
    # Traffic light indicators
    def indicator(value, green_threshold, yellow_threshold):
        if value >= green_threshold:
            return "🟢"
        elif value >= yellow_threshold:
            return "🟡"
        else:
            return "🔴"
    
    success_rate = metrics['success_rate']
    print(f"\n{indicator(success_rate, 0.95, 0.80)} Success Rate: {success_rate:.1%}")
    
    fallback_rate = metrics['fallback_rate']
    print(f"{indicator(1-fallback_rate, 0.70, 0.50)} Fallback Rate: {fallback_rate:.1%}")
    
    print(f"\nQuota Utilization:")
    for group, util in metrics['quota_utilization'].items():
        bar = "█" * int(util * 20)
        print(f"  {group:12s} [{bar:20s}] {util:.0%}")
    
    print(f"\nLatency:")
    print(f"  P50: {metrics['p50_latency']:.2f}s")
    print(f"  P95: {metrics['p95_latency']:.2f}s")
    
    print("="*60 + "\n")
```

---

## Cron Jobs

### Hourly State Pruning

```bash
# /etc/cron.hourly/router-state-prune
#!/bin/bash
python3 /path/to/prune_state.py --state ~/.prime/agent/router-state/state.json --max-age 3600
```

### Daily Report

```bash
# /etc/cron.daily/router-daily-report
#!/bin/bash
python3 /path/to/generate_report.py --log /var/log/router-metrics.jsonl --email team@example.com
```

### Weekly Quota Tuning Review

```bash
# /etc/cron.weekly/router-quota-review
#!/bin/bash
python3 /path/to/analyze_quota.py --config ~/.prime/agent/router-reference/reference-router.json
```

---

## Integration with Existing Monitoring

### Prometheus Metrics

```python
from prometheus_client import Counter, Histogram, Gauge

# Define metrics
spawn_requests = Counter('router_spawn_requests_total', 'Total spawn requests', ['role', 'outcome'])
spawn_latency = Histogram('router_spawn_latency_seconds', 'Spawn latency', ['role'])
quota_utilization = Gauge('router_quota_utilization', 'Quota group utilization', ['group'])

# Track events
spawn_requests.labels(role='coder', outcome='success').inc()
spawn_latency.labels(role='coder').observe(2.3)
quota_utilization.labels(group='fast').set(0.65)
```

### StatsD

```python
import statsd

stats = statsd.StatsClient('localhost', 8125)

# Track events
stats.incr('router.spawn.success')
stats.timing('router.spawn.latency', 2300)  # milliseconds
stats.gauge('router.quota.fast.utilization', 65)  # percentage
```

---

## See Also

- [operations/troubleshooting.md](operations/troubleshooting.md) - Interpreting metrics
- [operations/quota-configuration.md](operations/quota-configuration.md) - Tuning based on metrics
- [ARCHITECTURE.md](ARCHITECTURE.md) - Metrics collection points
