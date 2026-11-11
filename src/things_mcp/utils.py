"""Small helpers shared by the Things MCP tools."""

import logging
import time
from typing import Optional

logger = logging.getLogger(__name__)


def _normalize_id(val: Optional[str]) -> Optional[str]:
    """Normalize null-like values to None.

    Handles:
    - Python None (null in JSON, stripped by middleware)
    - String "null" (malformed from some MCP clients)
    - String "None" (Python repr edge case)
    - Empty string
    """
    if val is None:
        return None
    if isinstance(val, str) and val.lower() in ("null", "none", ""):
        return None
    return val


class CircuitBreaker:
    """Circuit breaker to prevent repeated failed attempts"""

    # Circuit states
    CLOSED = "closed"  # Normal operation
    OPEN = "open"  # Not allowing operations
    HALF_OPEN = "half-open"  # Testing if system has recovered

    def __init__(self, failure_threshold=5, recovery_timeout=60):
        self.state = self.CLOSED
        self.failure_count = 0
        self.failure_threshold = failure_threshold
        self.recovery_timeout = recovery_timeout
        self.last_failure_time = 0

    def record_failure(self):
        """Record a failure and potentially open the circuit"""
        self.failure_count += 1
        self.last_failure_time = time.time()

        if self.failure_count >= self.failure_threshold:
            self.state = self.OPEN
            logger.warning(
                f"Circuit breaker opened after {self.failure_count} failures"
            )

    def record_success(self):
        """Record a success and reset the circuit if in half-open state"""
        if self.state == self.HALF_OPEN:
            self.state = self.CLOSED
            self.failure_count = 0
            logger.info("Circuit breaker closed after successful operation")
        elif self.state == self.CLOSED:
            self.failure_count = 0

    def allow_operation(self):
        """Check if operation should be allowed"""
        if self.state == self.CLOSED:
            return True

        if self.state == self.OPEN:
            # Check if recovery timeout has elapsed
            if time.time() - self.last_failure_time > self.recovery_timeout:
                self.state = self.HALF_OPEN
                logger.info("Circuit breaker half-open, testing system recovery")
                return True
            return False

        # Half-open state allows a single test operation
        return True


class RateLimiter:
    """Intelligent rate limiter for Things operations"""

    def __init__(self, operations_per_minute=30):
        self.operations_per_minute = operations_per_minute
        self.operation_interval = 60 / operations_per_minute
        self.last_operation_time = 0

    def wait_if_needed(self):
        """Wait if necessary to maintain rate limit"""
        current_time = time.time()
        time_since_last = current_time - self.last_operation_time

        if time_since_last < self.operation_interval:
            # Need to wait
            wait_time = self.operation_interval - time_since_last
            time.sleep(wait_time)

        self.last_operation_time = time.time()

    def __call__(self, func):
        """Decorator to rate limit a function"""

        def wrapper(*args, **kwargs):
            self.wait_if_needed()
            return func(*args, **kwargs)

        return wrapper


circuit_breaker = CircuitBreaker()
rate_limiter = RateLimiter()
