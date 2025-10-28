"""Dispatcher de tâches.

Prend des tâches depuis la file et choisit un worker cible en combinant:
- un LoadBalancer (round-robin par défaut)
- un CircuitBreaker (évite d'insister sur un worker en échec)

La logique d'envoi réel vers le worker est laissée en placeholder pour
s'intégrer soit avec Dispy, soit avec une autre couche RPC.
"""

from typing import Optional, Dict

from .load_balancer import LoadBalancer
from .fault_tolerance import CircuitBreaker
from .task_queue import TaskQueue, Task
from .worker_registry import WorkerRegistry


class Dispatcher:
    def __init__(self, registry: WorkerRegistry, queue: TaskQueue) -> None:
        self.registry = registry
        self.queue = queue
        self.lb = LoadBalancer()
        self.cb = CircuitBreaker()

    def _pick_target(self, requires: Optional[list] = None) -> Optional[str]:
        ready = self.registry.list_ready(requires=requires)
        # filtrer les noeuds cassés par le circuit breaker
        ready = [n for n in ready if not self.cb.is_open(n)]
        return self.lb.pick_round_robin(ready)

    def dispatch_once(self) -> Optional[Dict[str, str]]:
        task: Optional[Task] = self.queue.pop()
        if not task:
            return None
        target = self._pick_target(task.requires)
        if not target:
            # pas de cible dispo, on réinsère en fin de file
            self.queue.push(task)
            return {"status": "queued"}

        # Placeholder d'envoi réel à un worker:
        # - avec Dispy: soumettre la fonction dédiée au dispyscheduler
        # - ou via SSH/RPC/HTTP vers le worker choisi
        success = True

        if success:
            self.cb.record_success(target)
            return {"status": "sent", "target": target}
        else:
            self.cb.record_failure(target)
            # réinsérer la tâche pour une tentative ultérieure
            self.queue.push(task)
            return {"status": "retry", "target": target}

