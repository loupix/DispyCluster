"""Composants de tolérance aux pannes intégrés dans l'interface web.

Algorithme adapté du core/fault_tolerance.py original avec des améliorations.
"""

from typing import Dict, List, Optional
import time
from datetime import datetime, timedelta
from enum import Enum

class CircuitState(Enum):
    CLOSED = "closed"
    OPEN = "open"
    HALF_OPEN = "half_open"

class CircuitBreaker:
    def __init__(self, failure_threshold: int = 3, reset_after_s: int = 30, 
                 success_threshold: int = 2, timeout_s: int = 5) -> None:
        self.failure_threshold = failure_threshold
        self.reset_after_s = reset_after_s
        self.success_threshold = success_threshold
        self.timeout_s = timeout_s
        
        self.failures: Dict[str, int] = {}
        self.successes: Dict[str, int] = {}
        self.tripped_at: Dict[str, float] = {}
        self.last_attempt: Dict[str, float] = {}
        self.circuit_state: Dict[str, CircuitState] = {}

    def record_success(self, node: str) -> None:
        """Réinitialise les compteurs d'échec pour `node`."""
        self.failures[node] = 0
        self.successes[node] = self.successes.get(node, 0) + 1
        self.tripped_at.pop(node, None)
        self.circuit_state[node] = CircuitState.CLOSED

    def record_failure(self, node: str) -> None:
        """Incrémente les échecs et ouvre le circuit si seuil atteint."""
        count = self.failures.get(node, 0) + 1
        self.failures[node] = count
        self.successes[node] = 0  # Reset success count on failure
        
        if count >= self.failure_threshold:
            self.tripped_at[node] = time.time()
            self.circuit_state[node] = CircuitState.OPEN

    def is_open(self, node: str) -> bool:
        """Retourne True si le circuit est ouvert pour `node`."""
        if node not in self.circuit_state:
            self.circuit_state[node] = CircuitState.CLOSED
            return False
        
        current_state = self.circuit_state[node]
        
        if current_state == CircuitState.CLOSED:
            return False
        elif current_state == CircuitState.OPEN:
            # Vérifier si on peut passer en demi-ouvert
            if node in self.tripped_at:
                if time.time() - self.tripped_at[node] > self.reset_after_s:
                    self.circuit_state[node] = CircuitState.HALF_OPEN
                    return False
            return True
        elif current_state == CircuitState.HALF_OPEN:
            # En demi-ouvert, on permet quelques tentatives
            return False
        
        return False

    def can_attempt(self, node: str) -> bool:
        """Vérifie si on peut tenter une opération sur le nœud."""
        if self.is_open(node):
            return False
        
        # Vérifier le timeout
        if node in self.last_attempt:
            if time.time() - self.last_attempt[node] < self.timeout_s:
                return False
        
        self.last_attempt[node] = time.time()
        return True

    def get_circuit_state(self, node: str) -> CircuitState:
        """Retourne l'état actuel du circuit pour un nœud."""
        return self.circuit_state.get(node, CircuitState.CLOSED)

    def get_stats(self, node: str) -> Dict[str, any]:
        """Retourne les statistiques du circuit breaker pour un nœud."""
        return {
            "node": node,
            "state": self.get_circuit_state(node).value,
            "failures": self.failures.get(node, 0),
            "successes": self.successes.get(node, 0),
            "tripped_at": self.tripped_at.get(node),
            "last_attempt": self.last_attempt.get(node),
            "is_open": self.is_open(node),
            "can_attempt": self.can_attempt(node)
        }

    def reset(self, node: str) -> None:
        """Force la réinitialisation du circuit pour un nœud."""
        self.failures[node] = 0
        self.successes[node] = 0
        self.tripped_at.pop(node, None)
        self.last_attempt.pop(node, None)
        self.circuit_state[node] = CircuitState.CLOSED

    def get_all_stats(self) -> Dict[str, Dict[str, any]]:
        """Retourne les statistiques pour tous les nœuds."""
        all_nodes = set()
        all_nodes.update(self.failures.keys())
        all_nodes.update(self.successes.keys())
        all_nodes.update(self.tripped_at.keys())
        all_nodes.update(self.circuit_state.keys())
        
        return {node: self.get_stats(node) for node in all_nodes}

class RetryPolicy:
    def __init__(self, max_retries: int = 3, base_delay: float = 1.0, 
                 max_delay: float = 60.0, backoff_factor: float = 2.0) -> None:
        self.max_retries = max_retries
        self.base_delay = base_delay
        self.max_delay = max_delay
        self.backoff_factor = backoff_factor

    def get_delay(self, attempt: int) -> float:
        """Calcule le délai d'attente pour un essai donné."""
        delay = self.base_delay * (self.backoff_factor ** attempt)
        return min(delay, self.max_delay)

    def should_retry(self, attempt: int, error: Exception) -> bool:
        """Détermine si on doit réessayer basé sur l'essai et l'erreur."""
        if attempt >= self.max_retries:
            return False
        
        # Types d'erreurs qui justifient un retry
        retryable_errors = (
            ConnectionError,
            TimeoutError,
            OSError,
            # Ajouter d'autres types d'erreurs selon les besoins
        )
        
        return isinstance(error, retryable_errors)

class HealthChecker:
    def __init__(self, timeout_s: int = 5, check_interval_s: int = 30) -> None:
        self.timeout_s = timeout_s
        self.check_interval_s = check_interval_s
        self.last_check: Dict[str, float] = {}
        self.health_status: Dict[str, bool] = {}

    def is_healthy(self, node: str) -> bool:
        """Vérifie si un nœud est en bonne santé."""
        return self.health_status.get(node, False)

    def should_check(self, node: str) -> bool:
        """Détermine si on doit vérifier la santé d'un nœud."""
        if node not in self.last_check:
            return True
        
        return time.time() - self.last_check[node] > self.check_interval_s

    def update_health(self, node: str, is_healthy: bool) -> None:
        """Met à jour le statut de santé d'un nœud."""
        self.health_status[node] = is_healthy
        self.last_check[node] = time.time()

    def get_health_stats(self) -> Dict[str, any]:
        """Retourne les statistiques de santé."""
        total_nodes = len(self.health_status)
        healthy_nodes = sum(1 for healthy in self.health_status.values() if healthy)
        
        return {
            "total_nodes": total_nodes,
            "healthy_nodes": healthy_nodes,
            "unhealthy_nodes": total_nodes - healthy_nodes,
            "health_rate": healthy_nodes / total_nodes if total_nodes > 0 else 0,
            "last_checks": {node: datetime.fromtimestamp(timestamp).isoformat() 
                           for node, timestamp in self.last_check.items()}
        }

class FaultToleranceManager:
    def __init__(self) -> None:
        self.circuit_breaker = CircuitBreaker()
        self.retry_policy = RetryPolicy()
        self.health_checker = HealthChecker()

    def execute_with_fault_tolerance(self, node: str, operation, *args, **kwargs):
        """Exécute une opération avec tolérance aux pannes."""
        if not self.circuit_breaker.can_attempt(node):
            raise Exception(f"Circuit breaker ouvert pour {node}")
        
        if not self.health_checker.is_healthy(node):
            raise Exception(f"Nœud {node} en mauvaise santé")
        
        attempt = 0
        last_error = None
        
        while attempt <= self.retry_policy.max_retries:
            try:
                result = operation(*args, **kwargs)
                self.circuit_breaker.record_success(node)
                return result
            except Exception as e:
                last_error = e
                attempt += 1
                
                if not self.retry_policy.should_retry(attempt, e):
                    break
                
                if attempt <= self.retry_policy.max_retries:
                    delay = self.retry_policy.get_delay(attempt - 1)
                    time.sleep(delay)
        
        self.circuit_breaker.record_failure(node)
        raise last_error

    def get_comprehensive_stats(self) -> Dict[str, any]:
        """Retourne des statistiques complètes de tolérance aux pannes."""
        return {
            "circuit_breaker": self.circuit_breaker.get_all_stats(),
            "health_checker": self.health_checker.get_health_stats(),
            "retry_policy": {
                "max_retries": self.retry_policy.max_retries,
                "base_delay": self.retry_policy.base_delay,
                "max_delay": self.retry_policy.max_delay,
                "backoff_factor": self.retry_policy.backoff_factor
            }
        }