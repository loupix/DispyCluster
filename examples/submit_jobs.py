"""Exemple minimal de soumission de tâches.

Enregistre trois workers fictifs avec des capacités, pousse quelques tâches
dans la file puis appelle le dispatcher plusieurs fois.
"""

from core.worker_registry import WorkerRegistry
from core.task_queue import TaskQueue, Task
from core.dispatcher import Dispatcher


def main() -> None:
    """Point d'entrée de l'exemple."""
    registry = WorkerRegistry()
    # Enregistrement de quelques workers avec capacités
    for h in ["node6.lan", "node7.lan", "node9.lan"]:
        registry.register(h, capabilities=["cpu", "image"])  # exemple
        registry.set_status(h, "ready")

    queue = TaskQueue()
    # 3 tâches CPU, 2 images, 1 Whisper
    queue.push(Task({"type": "cpu", "iterations": 50000}, requires=["cpu"]))
    queue.push(Task({"type": "cpu", "iterations": 80000}, requires=["cpu"]))
    queue.push(Task({"type": "image", "path": "test.jpg", "w": 320, "h": 240}, requires=["image"]))
    queue.push(Task({"type": "whisper", "path": "sample.wav"}, requires=["whisper"]))

    dispatcher = Dispatcher(registry, queue)

    # Dispatcher simple: traite quelques tours
    for _ in range(10):
        result = dispatcher.dispatch_once()
        if result:
            print(result)


if __name__ == "__main__":
    main()

