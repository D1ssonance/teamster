"""
Executable tests for router fallback logic.

Run with: pytest tests/test_router.py -v
"""
import pytest
from enum import Enum
from typing import List, Optional
from dataclasses import dataclass


# Mock classes for testing
class ErrorType(Enum):
    RATE_LIMIT = "rate_limit"
    AUTH = "auth"
    AVAILABILITY = "availability"
    VALIDATION = "validation"
    UNKNOWN = "unknown"


@dataclass
class RoleSpec:
    models: List[str]
    quotaGroup: str


@dataclass
class Config:
    roles: dict
    cooldowns: dict = None
    quotaGroups: dict = None
    
    def __post_init__(self):
        if self.cooldowns is None:
            self.cooldowns = {}
        if self.quotaGroups is None:
            self.quotaGroups = {}


class MockRuntime:
    """Mock runtime for testing"""
    
    def __init__(self):
        self.spawn_count = 0
        self.failures = []
    
    async def spawn(self, prompt, model, name):
        """Simulate spawn - fail or succeed based on test setup"""
        self.spawn_count += 1
        
        for fail_model, error_type in self.failures:
            if model == fail_model:
                if error_type == ErrorType.RATE_LIMIT:
                    raise Exception("429: Rate limit exceeded")
                elif error_type == ErrorType.AUTH:
                    raise Exception("401: Unauthorized")
                elif error_type == ErrorType.AVAILABILITY:
                    raise Exception("503: Service unavailable")
                elif error_type == ErrorType.VALIDATION:
                    raise Exception("400: Bad request")
        
        return {"model": model, "name": name}


# Helper functions from pseudocode
def classify_error(error_message: str) -> ErrorType:
    """Classify error by pattern matching"""
    msg_lower = error_message.lower()
    
    if any(p in msg_lower for p in ["401", "403", "unauthorized", "forbidden"]):
        return ErrorType.AUTH
    
    if any(p in msg_lower for p in ["rate limit", "429", "too many"]):
        return ErrorType.RATE_LIMIT
    
    if any(p in msg_lower for p in ["503", "504", "unavailable", "timeout"]):
        return ErrorType.AVAILABILITY
    
    if any(p in msg_lower for p in ["400", "invalid request", "bad request"]):
        return ErrorType.VALIDATION
    
    return ErrorType.UNKNOWN


def is_on_cooldown(config: Config, model_id: str) -> bool:
    """Check if model is on cooldown"""
    import time
    cooldown_until = config.cooldowns.get(model_id, 0)
    return time.time() < cooldown_until


# Main spawn function from pseudocode
async def spawn_agent(role: str, task: str, config: Config, runtime: MockRuntime) -> dict:
    """Spawn agent with fallback (simplified for testing)"""
    role_spec = config.roles[role]
    tried_models = []
    
    for model in role_spec.models:
        if model in tried_models:
            continue
        
        if is_on_cooldown(config, model):
            continue
        
        tried_models.append(model)
        
        try:
            result = await runtime.spawn(
                prompt=task,
                model=model,
                name=f"{role}-{model}"
            )
            return result
        
        except Exception as exc:
            error_type = classify_error(str(exc))
            
            if error_type == ErrorType.AUTH:
                raise  # Fail fast
            
            if error_type == ErrorType.VALIDATION:
                raise  # Fail fast
            
            if error_type == ErrorType.RATE_LIMIT:
                import time
                config.cooldowns[model] = time.time() + 60
                continue
            
            # Try fallback for other errors
            continue
    
    raise Exception("All models exhausted")


# ===== TESTS =====

@pytest.mark.asyncio
async def test_primary_model_success():
    """Test successful spawn with primary model"""
    config = Config(roles={
        "coder": RoleSpec(
            models=["provider-a/model-x", "provider-a/model-y"],
            quotaGroup="fast"
        )
    })
    
    runtime = MockRuntime()
    result = await spawn_agent("coder", "Test task", config, runtime)
    
    assert result["model"] == "provider-a/model-x"
    assert runtime.spawn_count == 1


@pytest.mark.asyncio
async def test_fallback_on_rate_limit():
    """Test fallback when primary hits rate limit"""
    config = Config(roles={
        "coder": RoleSpec(
            models=["provider-a/model-x", "provider-a/model-y"],
            quotaGroup="fast"
        )
    })
    
    runtime = MockRuntime()
    runtime.failures = [("provider-a/model-x", ErrorType.RATE_LIMIT)]
    
    result = await spawn_agent("coder", "Test task", config, runtime)
    
    assert result["model"] == "provider-a/model-y"  # Used fallback
    assert runtime.spawn_count == 2
    assert "provider-a/model-x" in config.cooldowns  # Cooldown set


@pytest.mark.asyncio
async def test_auth_error_fails_fast():
    """Test that AUTH errors don't try fallback"""
    config = Config(roles={
        "coder": RoleSpec(
            models=["provider-a/model-x", "provider-a/model-y"],
            quotaGroup="fast"
        )
    })
    
    runtime = MockRuntime()
    runtime.failures = [("provider-a/model-x", ErrorType.AUTH)]
    
    with pytest.raises(Exception, match="401"):
        await spawn_agent("coder", "Test task", config, runtime)
    
    assert runtime.spawn_count == 1  # Only tried once


@pytest.mark.asyncio
async def test_skip_models_on_cooldown():
    """Test that models on cooldown are skipped"""
    import time
    
    config = Config(roles={
        "coder": RoleSpec(
            models=["provider-a/model-x", "provider-a/model-y"],
            quotaGroup="fast"
        )
    })
    
    # Set cooldown on primary
    config.cooldowns["provider-a/model-x"] = time.time() + 3600
    
    runtime = MockRuntime()
    result = await spawn_agent("coder", "Test task", config, runtime)
    
    assert result["model"] == "provider-a/model-y"  # Skipped model-x
    assert runtime.spawn_count == 1  # Only tried model-y


@pytest.mark.asyncio
async def test_all_models_exhausted():
    """Test error when all models fail"""
    config = Config(roles={
        "coder": RoleSpec(
            models=["provider-a/model-x", "provider-a/model-y"],
            quotaGroup="fast"
        )
    })
    
    runtime = MockRuntime()
    runtime.failures = [
        ("provider-a/model-x", ErrorType.RATE_LIMIT),
        ("provider-a/model-y", ErrorType.RATE_LIMIT)
    ]
    
    with pytest.raises(Exception, match="exhausted"):
        await spawn_agent("coder", "Test task", config, runtime)
    
    assert runtime.spawn_count == 2  # Tried both


def test_error_classification():
    """Test error classification logic"""
    assert classify_error("429: Rate limit") == ErrorType.RATE_LIMIT
    assert classify_error("401: Unauthorized") == ErrorType.AUTH
    assert classify_error("503: Unavailable") == ErrorType.AVAILABILITY
    assert classify_error("400: Bad request") == ErrorType.VALIDATION
    assert classify_error("Unknown error") == ErrorType.UNKNOWN


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
