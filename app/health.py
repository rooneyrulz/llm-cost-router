import time
from collections import defaultdict


class HealthChecker:
    """Simple circuit breaker: trips after N consecutive failures,
    resets after a cooldown period."""

    def __init__(self, failure_threshold: int = 3, cooldown_s: int = 30):
        self.failures: dict[str, int] = defaultdict(int)
        self.tripped_at: dict[str, float] = {}
        self.failure_threshold = failure_threshold
        self.cooldown_s = cooldown_s

    def record_success(self, model_name: str):
        self.failures[model_name] = 0
        self.tripped_at.pop(model_name, None)

    def record_failure(self, model_name: str):
        self.failures[model_name] += 1
        if self.failures[model_name] >= self.failure_threshold:
            self.tripped_at[model_name] = time.monotonic()

    def is_healthy(self, model_name: str) -> bool:
        if model_name not in self.tripped_at:
            return True
        if time.monotonic() - self.tripped_at[model_name] > self.cooldown_s:
            self.record_success(model_name)  # reset after cooldown
            return True
        return False
