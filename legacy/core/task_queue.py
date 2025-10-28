"""File de tâches minimale pour le dispatcher.

Chaque `Task` contient un `payload` libre et une liste d'exigences de
capacités (ex: ["cpu"], ["image"], ["whisper"]).
"""

from typing import Any, Dict, List, Optional
from collections import deque


class Task:
    def __init__(self, payload: Dict[str, Any], requires: Optional[List[str]] = None) -> None:
        self.payload = payload
        self.requires = requires or []


class TaskQueue:
    def __init__(self) -> None:
        self._q: deque[Task] = deque()

    def push(self, task: Task) -> None:
        """Ajoute une tâche en fin de file."""
        self._q.append(task)

    def pop(self) -> Optional[Task]:
        """Retire et retourne la prochaine tâche, ou None si vide."""
        if not self._q:
            return None
        return self._q.popleft()

    def __len__(self) -> int:  # type: ignore[override]
        return len(self._q)

