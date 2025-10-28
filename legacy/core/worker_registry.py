"""Registre central des workers.

Permet d'enregistrer les workers, leurs capacités (tags) et leur statut.
Fournit aussi une liste filtrée des workers "ready" qui satisfont des
contraintes de capacités.
"""

from typing import Dict, Optional, List
import time


class WorkerInfo:
    def __init__(self, host: str, capabilities: Optional[List[str]] = None) -> None:
        self.host = host
        self.capabilities = capabilities or []
        self.last_heartbeat_s: float = 0.0
        self.status: str = "unknown"  # unknown|ready|busy|down

    def heartbeat(self) -> None:
        self.last_heartbeat_s = time.time()
        if self.status == "unknown":
            self.status = "ready"


class WorkerRegistry:
    def __init__(self) -> None:
        self._workers: Dict[str, WorkerInfo] = {}

    def register(self, host: str, capabilities: Optional[List[str]] = None) -> WorkerInfo:
        """Enregistre ou met à jour un worker et marque un heartbeat."""
        info = self._workers.get(host)
        if not info:
            info = WorkerInfo(host, capabilities)
            self._workers[host] = info
        else:
            if capabilities:
                info.capabilities = capabilities
        info.heartbeat()
        return info

    def heartbeat(self, host: str) -> None:
        """Met à jour l'horodatage de vie pour `host` (s'il existe)."""
        if host in self._workers:
            self._workers[host].heartbeat()

    def set_status(self, host: str, status: str) -> None:
        """Change l'état logique d'un worker (ready, busy, down...)."""
        if host in self._workers:
            self._workers[host].status = status

    def get(self, host: str) -> Optional[WorkerInfo]:
        return self._workers.get(host)

    def list_ready(self, requires: Optional[List[str]] = None) -> List[str]:
        """Retourne les hôtes prêts qui possèdent toutes les `requires`."""
        requires = requires or []
        hosts: List[str] = []
        for host, info in self._workers.items():
            if info.status == "ready" and all(cap in info.capabilities for cap in requires):
                hosts.append(host)
        return hosts

    def all_hosts(self) -> List[str]:
        return list(self._workers.keys())

