import json
import os
import time
import logging
from typing import Any, Callable, Dict, Optional
import redis

logger = logging.getLogger("aegis.orchestrator.state")


class SharedStateManager:
    """Persists agent handoff checkpoints in Redis with automatic in-memory fallback."""

    def __init__(self, ttl_seconds: int = 3600):
        self.ttl = ttl_seconds
        self._memory_store: Dict[str, str] = {}
        redis_host = os.getenv("REDIS_HOST", "localhost")
        redis_port = int(os.getenv("REDIS_PORT", "6379"))
        try:
            self._redis = redis.Redis(
                host=redis_host, port=redis_port, decode_responses=True, socket_connect_timeout=1
            )
            self._redis.ping()
        except Exception:
            logger.warning("Redis unavailable; using in-memory state recovery store.")
            self._redis = None

    def save_checkpoint(self, request_id: str, state: Dict[str, Any]) -> None:
        payload = json.dumps(state, default=str)
        if self._redis:
            self._redis.setex(f"aegis:agent_state:{request_id}", self.ttl, payload)
        else:
            self._memory_store[request_id] = payload

    def load_checkpoint(self, request_id: str) -> Optional[Dict[str, Any]]:
        raw = (
            self._redis.get(f"aegis:agent_state:{request_id}")
            if self._redis
            else self._memory_store.get(request_id)
        )
        return json.loads(raw) if raw else None


def execute_with_recovery(
    fn: Callable[[], str],
    fallback_msg: str,
    max_retries: int = 2,
) -> str:
    """Executes an LLM/agent step with exponential backoff and deterministic fallback."""
    backoff = 0.5
    for attempt in range(1, max_retries + 1):
        try:
            return fn()
        except Exception as exc:
            logger.warning("Agent step failed (attempt %d/%d): %s", attempt, max_retries, exc)
            if attempt == max_retries:
                return f"{fallback_msg} (recovered from: {exc})"
            time.sleep(backoff)
            backoff *= 2
    return fallback_msg