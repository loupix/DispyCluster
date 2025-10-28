"""File de tâches intégrée dans l'interface web.

Algorithme adapté du core/task_queue.py original avec des améliorations.
"""

from typing import Any, Dict, List, Optional
from collections import deque
from datetime import datetime
from enum import Enum
import uuid
import json

class TaskPriority(Enum):
    LOW = 1
    NORMAL = 2
    HIGH = 3
    URGENT = 4

class TaskStatus(Enum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"

class Task:
    def __init__(self, payload: Dict[str, Any], requires: Optional[List[str]] = None, 
                 priority: TaskPriority = TaskPriority.NORMAL, 
                 task_id: Optional[str] = None) -> None:
        self.id = task_id or f"task_{uuid.uuid4().hex[:8]}"
        self.payload = payload
        self.requires = requires or []
        self.priority = priority
        self.status = TaskStatus.PENDING
        self.created_at = datetime.now()
        self.started_at: Optional[datetime] = None
        self.completed_at: Optional[datetime] = None
        self.assigned_node: Optional[str] = None
        self.retry_count = 0
        self.max_retries = 3
        self.result: Optional[Dict[str, Any]] = None
        self.error: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        """Convertit la tâche en dictionnaire pour la sérialisation."""
        return {
            "id": self.id,
            "payload": self.payload,
            "requires": self.requires,
            "priority": self.priority.value,
            "status": self.status.value,
            "created_at": self.created_at.isoformat(),
            "started_at": self.started_at.isoformat() if self.started_at else None,
            "completed_at": self.completed_at.isoformat() if self.completed_at else None,
            "assigned_node": self.assigned_node,
            "retry_count": self.retry_count,
            "max_retries": self.max_retries,
            "result": self.result,
            "error": self.error
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'Task':
        """Crée une tâche à partir d'un dictionnaire."""
        task = cls(
            payload=data["payload"],
            requires=data.get("requires"),
            priority=TaskPriority(data.get("priority", 2)),
            task_id=data["id"]
        )
        task.status = TaskStatus(data.get("status", "pending"))
        task.created_at = datetime.fromisoformat(data["created_at"])
        if data.get("started_at"):
            task.started_at = datetime.fromisoformat(data["started_at"])
        if data.get("completed_at"):
            task.completed_at = datetime.fromisoformat(data["completed_at"])
        task.assigned_node = data.get("assigned_node")
        task.retry_count = data.get("retry_count", 0)
        task.max_retries = data.get("max_retries", 3)
        task.result = data.get("result")
        task.error = data.get("error")
        return task

class TaskQueue:
    def __init__(self) -> None:
        self._q: deque[Task] = deque()
        self._running_tasks: Dict[str, Task] = {}
        self._completed_tasks: List[Task] = []
        self._failed_tasks: List[Task] = []

    def push(self, task: Task) -> None:
        """Ajoute une tâche en fin de file avec tri par priorité."""
        self._q.append(task)
        # Trier par priorité (plus haute priorité en premier)
        self._q = deque(sorted(self._q, key=lambda t: t.priority.value, reverse=True))

    def pop(self) -> Optional[Task]:
        """Retire et retourne la prochaine tâche, ou None si vide."""
        if not self._q:
            return None
        return self._q.popleft()

    def peek(self) -> Optional[Task]:
        """Retourne la prochaine tâche sans la retirer."""
        if not self._q:
            return None
        return self._q[0]

    def mark_running(self, task: Task, node: str) -> None:
        """Marque une tâche comme en cours d'exécution."""
        task.status = TaskStatus.RUNNING
        task.started_at = datetime.now()
        task.assigned_node = node
        self._running_tasks[task.id] = task

    def mark_completed(self, task_id: str, result: Optional[Dict[str, Any]] = None) -> None:
        """Marque une tâche comme terminée."""
        if task_id in self._running_tasks:
            task = self._running_tasks.pop(task_id)
            task.status = TaskStatus.COMPLETED
            task.completed_at = datetime.now()
            task.result = result
            self._completed_tasks.append(task)

    def mark_failed(self, task_id: str, error: str) -> None:
        """Marque une tâche comme échouée."""
        if task_id in self._running_tasks:
            task = self._running_tasks.pop(task_id)
            task.error = error
            task.retry_count += 1
            
            if task.retry_count < task.max_retries:
                # Réinsérer pour retry
                task.status = TaskStatus.PENDING
                task.assigned_node = None
                task.started_at = None
                self.push(task)
            else:
                # Définitivement échouée
                task.status = TaskStatus.FAILED
                task.completed_at = datetime.now()
                self._failed_tasks.append(task)

    def cancel_task(self, task_id: str) -> bool:
        """Annule une tâche."""
        # Chercher dans la file
        for i, task in enumerate(self._q):
            if task.id == task_id:
                task = self._q[i]
                task.status = TaskStatus.CANCELLED
                task.completed_at = datetime.now()
                del self._q[i]
                return True
        
        # Chercher dans les tâches en cours
        if task_id in self._running_tasks:
            task = self._running_tasks.pop(task_id)
            task.status = TaskStatus.CANCELLED
            task.completed_at = datetime.now()
            return True
        
        return False

    def get_task(self, task_id: str) -> Optional[Task]:
        """Récupère une tâche par son ID."""
        # Chercher dans la file
        for task in self._q:
            if task.id == task_id:
                return task
        
        # Chercher dans les tâches en cours
        if task_id in self._running_tasks:
            return self._running_tasks[task_id]
        
        # Chercher dans les tâches terminées
        for task in self._completed_tasks:
            if task.id == task_id:
                return task
        
        # Chercher dans les tâches échouées
        for task in self._failed_tasks:
            if task.id == task_id:
                return task
        
        return None

    def get_stats(self) -> Dict[str, Any]:
        """Retourne les statistiques de la file."""
        return {
            "pending": len(self._q),
            "running": len(self._running_tasks),
            "completed": len(self._completed_tasks),
            "failed": len(self._failed_tasks),
            "total": len(self._q) + len(self._running_tasks) + len(self._completed_tasks) + len(self._failed_tasks)
        }

    def get_recent_tasks(self, limit: int = 10) -> List[Task]:
        """Retourne les tâches récentes."""
        all_tasks = []
        all_tasks.extend(self._q)
        all_tasks.extend(self._running_tasks.values())
        all_tasks.extend(self._completed_tasks[-limit:])
        all_tasks.extend(self._failed_tasks[-limit:])
        
        # Trier par date de création
        all_tasks.sort(key=lambda t: t.created_at, reverse=True)
        return all_tasks[:limit]

    def cleanup_old_tasks(self, days: int = 7) -> int:
        """Nettoie les anciennes tâches terminées."""
        cutoff = datetime.now().timestamp() - (days * 24 * 3600)
        cleaned = 0
        
        # Nettoyer les tâches terminées
        self._completed_tasks = [
            task for task in self._completed_tasks 
            if task.completed_at and task.completed_at.timestamp() > cutoff
        ]
        
        # Nettoyer les tâches échouées
        self._failed_tasks = [
            task for task in self._failed_tasks 
            if task.completed_at and task.completed_at.timestamp() > cutoff
        ]
        
        return cleaned

    def __len__(self) -> int:
        return len(self._q)