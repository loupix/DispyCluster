"""Composants de tolérance aux pannes.

Ici un circuit breaker très simple: après N échecs, on ouvre le circuit pour
un certain temps. Une fois le délai passé, on tente à nouveau (état demi-ouvert).
"""

from typing import Dict
import time

class CircuitBreaker:
    def __init__(self, failure_threshold: int = 3, reset_after_s: int = 30) -> None:
        self.failure_threshold = failure_threshold
        self.reset_after_s = reset_after_s
        self.failures: Dict[str, int] = {}
        self.tripped_at: Dict[str, float] = {}

    def record_success(self, node: str) -> None:
        """Réinitialise les compteurs d'échec pour `node`."""
        self.failures[node] = 0
        self.tripped_at.pop(node, None)

    def record_failure(self, node: str) -> None:
        """Incrémente les échecs et ouvre le circuit si seuil atteint."""
        count = self.failures.get(node, 0) + 1
        self.failures[node] = count
        if count >= self.failure_threshold:
            self.tripped_at[node] = time.time()

    def is_open(self, node: str) -> bool:
        """Retourne True si le circuit est ouvert pour `node`."""
        if node not in self.tripped_at:
            return False
        if time.time() - self.tripped_at[node] > self.reset_after_s:
            # demi-ouvert
            self.failures[node] = 0
            self.tripped_at.pop(node, None)
            return False
        return True

