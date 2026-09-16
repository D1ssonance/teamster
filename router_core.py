#!/usr/bin/env python3
"""
Agent Router Core Implementation

Implements role-based agent routing with quota management,
cooldown tracking, and priority-preserving fallback chains.
"""

import json
import time
import fcntl
import os
from pathlib import Path
from typing import Dict, List, Any, Optional, Tuple
from dataclasses import dataclass
from enum import Enum


class ErrorCategory(Enum):
    """Error classification for fallback decisions."""
    AUTH = "AUTH"
    RATE_LIMIT = "RATE_LIMIT"
    PROVIDER_ERROR = "PROVIDER_ERROR"
    BAD_REQUEST = "BAD_REQUEST"
    UNKNOWN = "UNKNOWN"


class CapacityError(Exception):
    """Raised when quota group is exhausted."""
    def __init__(self, quota_group: str):
        self.quota_group = quota_group
        super().__init__(f"Quota group '{quota_group}' exhausted")


class AuthError(Exception):
    """Raised on authentication/authorization failures."""
    pass


@dataclass
class CooldownInfo:
    """Cooldown tracking information."""
    until: float
    reason: str


class RouterState:
    """Manages persistent router state with atomic updates."""
    
    def __init__(self, state_file: str = "~/.router-state.json"):
        """
        Initialize state manager.
        
        Args:
            state_file: Path to persistent state file
        """
        self.state_file = Path(state_file).expanduser()
        self.state_file.parent.mkdir(parents=True, exist_ok=True)
        self._lock_file = self.state_file.with_suffix('.lock')
        self._ensure_state_exists()
    
    def _ensure_state_exists(self):
        """Create initial state file if missing."""
        if not self.state_file.exists():
            initial_state = {
                "cooldowns": {},
                "starts": {}
            }
            self._write_state(initial_state)
    
    def _acquire_lock(self):
        """Acquire exclusive file lock."""
        self._lock_fd = open(self._lock_file, 'w')
        fcntl.flock(self._lock_fd.fileno(), fcntl.LOCK_EX)
    
    def _release_lock(self):
        """Release file lock."""
        fcntl.flock(self._lock_fd.fileno(), fcntl.LOCK_UN)
        self._lock_fd.close()
    
    def _read_state(self) -> Dict[str, Any]:
        """Read current state from disk."""
        with open(self.state_file, 'r') as f:
            return json.load(f)
    
    def _write_state(self, state: Dict[str, Any]):
        """Write state to disk atomically."""
        # Write to temporary file in same directory
        temp_file = self.state_file.with_suffix('.tmp')
        with open(temp_file, 'w') as f:
            json.dump(state, f, indent=2)
            f.flush()
            os.fsync(f.fileno())
        
        # Atomic rename
        temp_file.replace(self.state_file)
    
    def is_on_cooldown(self, model_id: str) -> bool:
        """
        Check if model is currently on cooldown.
        
        Args:
            model_id: Model identifier
            
        Returns:
            True if model is on cooldown
        """
        self._acquire_lock()
        try:
            state = self._read_state()
            cooldowns = state.get("cooldowns", {})
            
            if model_id not in cooldowns:
                return False
            
            cooldown = cooldowns[model_id]
            now = time.time()
            
            # Handle both formats: object with 'until' or plain timestamp
            if isinstance(cooldown, dict):
                until = cooldown.get("until", 0)
            else:
                until = cooldown
            
            if now >= until:
                # Cooldown expired, clean it up
                del cooldowns[model_id]
                state["cooldowns"] = cooldowns
                self._write_state(state)
                return False
            
            return True
        finally:
            self._release_lock()
    
    def report_rate_limit(self, model_id: str, reason: str, until: float):
        """
        Report rate limit and set cooldown.
        
        Args:
            model_id: Model identifier
            reason: Reason for cooldown
            until: Unix timestamp when cooldown expires
        """
        self._acquire_lock()
        try:
            state = self._read_state()
            cooldowns = state.get("cooldowns", {})
            
            cooldowns[model_id] = {
                "until": until,
                "reason": reason
            }
            
            state["cooldowns"] = cooldowns
            self._write_state(state)
        finally:
            self._release_lock()
    
    def check_quota(self, quota_group: str, window_seconds: int, max_starts: int) -> bool:
        """
        Check if quota group has capacity.
        
        Args:
            quota_group: Quota group name
            window_seconds: Window size in seconds
            max_starts: Maximum starts per window
            
        Returns:
            True if capacity available
        """
        self._acquire_lock()
        try:
            state = self._read_state()
            starts = state.get("starts", {})
            
            now = time.time()
            group_starts = starts.get(quota_group, [])
            
            # Filter to current window
            cutoff = now - window_seconds
            recent_starts = [ts for ts in group_starts if ts > cutoff]
            
            # Check capacity
            if len(recent_starts) >= max_starts:
                return False
            
            # Record this start
            recent_starts.append(now)
            starts[quota_group] = recent_starts
            state["starts"] = starts
            self._write_state(state)
            
            return True
        finally:
            self._release_lock()


class AgentRouter:
    """Role-based agent router with fallback chains."""
    
    def __init__(self, config_path: str, state_file: str = "~/.router-state.json"):
        """
        Initialize router.
        
        Args:
            config_path: Path to session router configuration
            state_file: Path to persistent state file
        """
        with open(config_path) as f:
            self.config = json.load(f)
        
        self.state = RouterState(state_file)
        self.provider = self.config.get("provider", "unknown")
    
    async def spawn_agent(self, role: str, task: str, **kwargs) -> Dict[str, Any]:
        """
        Spawn agent for role with fallback chain.
        
        Args:
            role: Semantic role name
            task: Task description
            **kwargs: Additional spawn parameters
            
        Returns:
            Spawn result with model used
            
        Raises:
            CapacityError: If quota exhausted
            AuthError: If all models fail with AUTH
            Exception: If all models exhausted
        """
        if role not in self.config["roles"]:
            raise ValueError(f"Unknown role: {role}")
        
        role_config = self.config["roles"][role]
        models = role_config["models"]
        quota_group = role_config["quotaGroup"]
        quota_config = self.config["quotaGroups"][quota_group]
        
        # Determine max attempts
        max_attempts = role_config.get(
            "maxFallbackAttempts",
            self.config.get("maxFallbackAttempts", 3)
        )
        
        # Track tried models by index (not by model_id for duplicates)
        tried_models = set()
        
        for attempt in range(max_attempts):
            # Check quota before each attempt
            if not self.state.check_quota(
                quota_group,
                quota_config["windowSeconds"],
                quota_config["maxStarts"]
            ):
                raise CapacityError(quota_group)
            # Find next available model
            selected_index = None
            selected_model = None
            
            for idx, model_id in enumerate(models):
                # Skip already tried
                if idx in tried_models:
                    continue
                
                # Skip models on cooldown
                if self.state.is_on_cooldown(model_id):
                    continue
                
                # Found candidate
                selected_index = idx
                selected_model = model_id
                break
            
            if selected_model is None:
                # All models tried or on cooldown
                raise Exception(f"All models exhausted for role '{role}'")
            
            # Mark this index as tried
            tried_models.add(selected_index)
            
            # Attempt spawn
            try:
                result = await self._spawn_with_provider(
                    selected_model,
                    role,
                    task,
                    **kwargs
                )
                return result
                
            except Exception as e:
                category = self._classify_error(e)
                
                # AUTH = fail fast, no fallback
                if category == ErrorCategory.AUTH:
                    raise AuthError(f"Authentication failed for role '{role}'") from e
                
                # RATE_LIMIT = cooldown + retry
                if category == ErrorCategory.RATE_LIMIT:
                    until = time.time() + self.config.get('cooldownSeconds', 60)  # Configurable cooldown
                    self.state.report_rate_limit(
                        selected_model,
                        "Rate limit exceeded",
                        until
                    )
                    continue
                
                # BAD_REQUEST = fail-fast, no retry
                if category == ErrorCategory.BAD_REQUEST:
                    raise
                
                # PROVIDER_ERROR, UNKNOWN = retry next model
                continue
        
        # Exhausted all attempts
        raise Exception(f"All fallback attempts exhausted for role '{role}'")
    
    async def _spawn_with_provider(
        self,
        model: str,
        role: str,
        task: str,
        **kwargs
    ) -> Dict[str, Any]:
        """
        Spawn agent through provider.
        
        This is a stub that would integrate with actual provider API.
        
        Args:
            model: Model identifier
            role: Semantic role
            task: Task description
            **kwargs: Additional parameters
            
        Returns:
            Spawn result
        """
        # Stub implementation - real version would call provider API
        return {
            "model": model,
            "role": role,
            "task": task,
            "status": "spawned"
        }
    
    def _classify_error(self, error: Exception) -> ErrorCategory:
        """
        Classify error for fallback decisions.
        
        Args:
            error: Exception to classify
            
        Returns:
            Error category
        """
        error_msg = str(error).lower()
        
        # AUTH patterns
        auth_patterns = [
            "unauthorized", "forbidden", "authentication",
            "401", "403", "invalid token", "access denied"
        ]
        if any(pattern in error_msg for pattern in auth_patterns):
            return ErrorCategory.AUTH
        
        # RATE_LIMIT patterns
        rate_patterns = [
            "rate limit", "too many requests", "429",
            "quota exceeded", "throttled"
        ]
        if any(pattern in error_msg for pattern in rate_patterns):
            return ErrorCategory.RATE_LIMIT
        
        # PROVIDER_ERROR patterns
        provider_patterns = [
            "500", "502", "503", "504",
            "internal error", "service unavailable",
            "gateway timeout"
        ]
        if any(pattern in error_msg for pattern in provider_patterns):
            return ErrorCategory.PROVIDER_ERROR
        
        # BAD_REQUEST patterns
        bad_request_patterns = [
            "400", "invalid", "malformed",
            "bad request", "validation error"
        ]
        if any(pattern in error_msg for pattern in bad_request_patterns):
            return ErrorCategory.BAD_REQUEST
        
        return ErrorCategory.UNKNOWN


def main():
    """Example usage."""
    import asyncio
    
    async def example():
        router = AgentRouter("session-router.json")
        
        try:
            result = await router.spawn_agent(
                role="scout",
                task="Find all API endpoints"
            )
            print(f"Spawned: {result}")
        except Exception as e:
            print(f"Failed: {e}")
    
    asyncio.run(example())


if __name__ == "__main__":
    main()
