"""Integration tests for router_core implementation."""

import pytest
import json
import tempfile
import os
from pathlib import Path
import sys

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from router_core import (
    AgentRouter, RouterState, ErrorCategory,
    CapacityError, AuthError, CooldownInfo
)


@pytest.fixture
def temp_state_file(tmp_path):
    """Create temporary state file."""
    state_file = tmp_path / "test-state.json"
    return str(state_file)


@pytest.fixture
def test_config(tmp_path):
    """Create test router configuration."""
    config = {
        "version": "2.0",
        "provider": "test",
        "defaultQuotaGroup": "standard",
        "maxFallbackAttempts": 3,
        "quotaGroups": {
            "fast": {"windowSeconds": 60, "maxStarts": 3},
            "standard": {"windowSeconds": 60, "maxStarts": 2}
        },
        "roles": {
            "test-role": {
                "description": "Test role",
                "models": ["model-a", "model-b", "model-c"],
                "quotaGroup": "standard"
            }
        }
    }
    
    config_file = tmp_path / "test-config.json"
    with open(config_file, 'w') as f:
        json.dump(config, f)
    
    return str(config_file)


class TestRouterState:
    """Test RouterState persistence and locking."""
    
    def test_initial_state_creation(self, temp_state_file):
        """Test that initial state file is created."""
        state = RouterState(temp_state_file)
        assert Path(temp_state_file).exists()
        
        with open(temp_state_file) as f:
            data = json.load(f)
        
        assert data == {"cooldowns": {}, "starts": {}}
    
    def test_cooldown_tracking(self, temp_state_file):
        """Test cooldown set and check."""
        import time
        state = RouterState(temp_state_file)
        
        # Not on cooldown initially
        assert not state.is_on_cooldown("model-a")
        
        # Set cooldown
        until = time.time() + 30
        state.report_rate_limit("model-a", "Test cooldown", until)
        
        # Now on cooldown
        assert state.is_on_cooldown("model-a")
        
        # Other model not affected
        assert not state.is_on_cooldown("model-b")
    
    def test_expired_cooldown_cleanup(self, temp_state_file):
        """Test that expired cooldowns are cleaned up."""
        import time
        state = RouterState(temp_state_file)
        
        # Set cooldown in the past
        until = time.time() - 10
        state.report_rate_limit("model-a", "Past cooldown", until)
        
        # Should not be on cooldown (expired)
        assert not state.is_on_cooldown("model-a")
        
        # Should be removed from state
        with open(temp_state_file) as f:
            data = json.load(f)
        assert "model-a" not in data["cooldowns"]
    
    def test_quota_tracking(self, temp_state_file):
        """Test quota window tracking."""
        state = RouterState(temp_state_file)
        
        # First start should succeed
        assert state.check_quota("test-group", 60, 2)
        
        # Second start should succeed
        assert state.check_quota("test-group", 60, 2)
        
        # Third start should fail (max 2)
        assert not state.check_quota("test-group", 60, 2)


class TestAgentRouter:
    """Test AgentRouter fallback logic."""
    
    def test_router_initialization(self, test_config, temp_state_file):
        """Test router loads configuration."""
        router = AgentRouter(test_config, temp_state_file)
        assert router.provider == "test"
        assert "test-role" in router.config["roles"]
    
    def test_error_classification(self, test_config, temp_state_file):
        """Test error classification logic."""
        router = AgentRouter(test_config, temp_state_file)
        
        # AUTH errors
        auth_error = Exception("401 Unauthorized")
        assert router._classify_error(auth_error) == ErrorCategory.AUTH
        
        # RATE_LIMIT errors
        rate_error = Exception("429 Too Many Requests")
        assert router._classify_error(rate_error) == ErrorCategory.RATE_LIMIT
        
        # PROVIDER_ERROR
        provider_error = Exception("503 Service Unavailable")
        assert router._classify_error(provider_error) == ErrorCategory.PROVIDER_ERROR
        
        # BAD_REQUEST
        bad_req_error = Exception("400 Bad Request")
        assert router._classify_error(bad_req_error) == ErrorCategory.BAD_REQUEST
        
        # UNKNOWN
        unknown_error = Exception("Something weird happened")
        assert router._classify_error(unknown_error) == ErrorCategory.UNKNOWN
    
    @pytest.mark.asyncio
    async def test_quota_exhaustion_raises_capacity_error(self, test_config, temp_state_file):
        """Test that quota exhaustion raises CapacityError."""
        router = AgentRouter(test_config, temp_state_file)
        
        # Exhaust quota
        router.state.check_quota("standard", 60, 2)
        router.state.check_quota("standard", 60, 2)
        
        # Next spawn should raise CapacityError
        with pytest.raises(CapacityError) as exc_info:
            await router.spawn_agent("test-role", "Test task")
        
        assert "standard" in str(exc_info.value)


class TestSessionGenerator:
    """Test session router generator."""
    
    def test_generator_creates_session_config(self, tmp_path):
        """Test that generator produces valid session config."""
        from session_router_generator import SessionRouterGenerator
        
        # Create minimal reference config
        ref_config = {
            "version": "2.0",
            "provider": "test",
            "defaultQuotaGroup": "standard",
            "maxFallbackAttempts": 3,
            "quotaGroups": {"standard": {"windowSeconds": 60, "maxStarts": 2}},
            "roles": {
                "test-role": {
                    "description": "Test",
                    "models": ["model-a"],
                    "quotaGroup": "standard"
                }
            }
        }
        
        ref_path = tmp_path / "ref.json"
        with open(ref_path, 'w') as f:
            json.dump(ref_config, f)
        
        # Generate session config
        generator = SessionRouterGenerator(str(ref_path))
        output_path = tmp_path / "session.json"
        result = generator.generate(str(output_path), "test-session")
        
        # Verify output
        assert output_path.exists()
        assert result["sessionId"] == "test-session"
        assert "generatedAt" in result
        assert result["roles"]["test-role"]["models"] == ["model-a"]


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
