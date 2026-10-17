"""
R5 Operational Intelligence Platform - Circuit Breaker
Protects services and AI provider calls against cascading failures and hangs.
Automatically trips to OPEN upon consecutive failures and fast-fails or falls back to
deterministic baselines until recovery timeout expires.
"""

import time
import threading
from enum import Enum
from typing import Optional
from backend.app.core.logger import logger


class CircuitState(str, Enum):
    CLOSED = "CLOSED"         # Normal operation
    OPEN = "OPEN"             # Tripped; fail fast / fallback
    HALF_OPEN = "HALF_OPEN"   # Canary request testing provider recovery


class CircuitBreaker:
    def __init__(
        self,
        name: str,
        failure_threshold: int = 3,
        recovery_timeout_seconds: float = 15.0,
        half_open_success_threshold: int = 1
    ):
        self.name = name
        self.failure_threshold = failure_threshold
        self.recovery_timeout_seconds = recovery_timeout_seconds
        self.half_open_success_threshold = half_open_success_threshold

        self._state: CircuitState = CircuitState.CLOSED
        self._consecutive_failures: int = 0
        self._consecutive_successes: int = 0
        self._last_state_change: float = time.time()
        self._last_failure_time: Optional[float] = None
        self._last_error_message: Optional[str] = None
        self._lock = threading.RLock()

    @property
    def state(self) -> CircuitState:
        with self._lock:
            # Check if an OPEN circuit has waited long enough to test recovery
            if self._state == CircuitState.OPEN:
                now = time.time()
                if (now - self._last_state_change) >= self.recovery_timeout_seconds:
                    self._state = CircuitState.HALF_OPEN
                    self._consecutive_successes = 0
                    self._last_state_change = now
                    logger.info(f"Circuit breaker '{self.name}' moved to HALF_OPEN (probing recovery).")
            return self._state

    def can_execute(self) -> bool:
        """Returns True if the provider can be called directly, False if circuit is OPEN."""
        return self.state in (CircuitState.CLOSED, CircuitState.HALF_OPEN)

    def record_success(self) -> None:
        with self._lock:
            if self._state == CircuitState.HALF_OPEN:
                self._consecutive_successes += 1
                if self._consecutive_successes >= self.half_open_success_threshold:
                    self._state = CircuitState.CLOSED
                    self._consecutive_failures = 0
                    self._last_state_change = time.time()
                    logger.info(f"Circuit breaker '{self.name}' recovered: State reset to CLOSED.")
            elif self._state == CircuitState.CLOSED:
                self._consecutive_failures = 0

    def record_failure(self, error: Optional[Exception] = None) -> None:
        with self._lock:
            now = time.time()
            self._last_failure_time = now
            self._last_error_message = str(error) if error else "Unknown error"
            self._consecutive_failures += 1

            if self._state in (CircuitState.CLOSED, CircuitState.HALF_OPEN):
                if self._consecutive_failures >= self.failure_threshold or self._state == CircuitState.HALF_OPEN:
                    self._state = CircuitState.OPEN
                    self._last_state_change = now
                    logger.warning(
                        f"Circuit breaker '{self.name}' tripped to OPEN after "
                        f"{self._consecutive_failures} failure(s). Recovery timeout: {self.recovery_timeout_seconds}s. "
                        f"Last error: {self._last_error_message}"
                    )

    def reset(self) -> None:
        with self._lock:
            self._state = CircuitState.CLOSED
            self._consecutive_failures = 0
            self._consecutive_successes = 0
            self._last_state_change = time.time()
            self._last_failure_time = None
            self._last_error_message = None

    def get_status(self) -> dict:
        with self._lock:
            return {
                "name": self.name,
                "state": self.state.value,
                "consecutiveFailures": self._consecutive_failures,
                "failureThreshold": self.failure_threshold,
                "recoveryTimeoutSeconds": self.recovery_timeout_seconds,
                "lastFailureTime": self._last_failure_time,
                "lastErrorMessage": self._last_error_message
            }
