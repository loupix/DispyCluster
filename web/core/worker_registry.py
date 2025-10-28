"""Registre central des workers intégré dans l'interface web.

Algorithme adapté du core/worker_registry.py original avec des améliorations.
"""

from typing import Dict, Optional, List
import time
from datetime import datetime, timedelta
from enum import Enum

class WorkerStatus(Enum):
    UNKNOWN = "unknown"
    READY = "ready"
    BUSY = "busy"
    DOWN = "down"
    MAINTENANCE = "maintenance"

class WorkerInfo:
    def __init__(self, host: str, capabilities: Optional[List[str]] = None) -> None:
        self.host = host
        self.capabilities = capabilities or []
        self.last_heartbeat_s: float = 0.0
        self.status: WorkerStatus = WorkerStatus.UNKNOWN
        self.cpu_usage: float = 0.0
        self.memory_usage: float = 0.0
        self.disk_usage: float = 0.0
        self.temperature: Optional[float] = None
        self.active_jobs: int = 0
        self.total_jobs: int = 0
        self.successful_jobs: int = 0
        self.failed_jobs: int = 0
        self.last_job_time: Optional[datetime] = None
        self.performance_score: float = 1.0

    def heartbeat(self) -> None:
        """Met à jour le heartbeat et le statut."""
        self.last_heartbeat_s = time.time()
        if self.status == WorkerStatus.UNKNOWN:
            self.status = WorkerStatus.READY

    def is_healthy(self, timeout_s: int = 30) -> bool:
        """Vérifie si le worker est en bonne santé."""
        return (time.time() - self.last_heartbeat_s) < timeout_s

    def update_metrics(self, cpu_usage: float, memory_usage: float, 
                      disk_usage: float, temperature: Optional[float] = None) -> None:
        """Met à jour les métriques du worker."""
        self.cpu_usage = cpu_usage
        self.memory_usage = memory_usage
        self.disk_usage = disk_usage
        self.temperature = temperature
        
        # Calculer le score de performance
        self.performance_score = self._calculate_performance_score()

    def _calculate_performance_score(self) -> float:
        """Calcule un score de performance basé sur les métriques."""
        # Score basé sur l'utilisation des ressources (plus bas = mieux)
        cpu_score = 1.0 - (self.cpu_usage / 100.0)
        memory_score = 1.0 - (self.memory_usage / 100.0)
        disk_score = 1.0 - (self.disk_usage / 100.0)
        
        # Score basé sur le taux de succès
        success_rate = 1.0
        if self.total_jobs > 0:
            success_rate = self.successful_jobs / self.total_jobs
        
        # Score composite
        return (cpu_score * 0.3 + memory_score * 0.3 + disk_score * 0.2 + success_rate * 0.2)

    def record_job_result(self, success: bool) -> None:
        """Enregistre le résultat d'un job."""
        self.total_jobs += 1
        if success:
            self.successful_jobs += 1
        else:
            self.failed_jobs += 1
        self.last_job_time = datetime.now()
        
        # Recalculer le score de performance
        self.performance_score = self._calculate_performance_score()

    def to_dict(self) -> Dict[str, any]:
        """Convertit les informations du worker en dictionnaire."""
        return {
            "host": self.host,
            "capabilities": self.capabilities,
            "status": self.status.value,
            "last_heartbeat": datetime.fromtimestamp(self.last_heartbeat_s).isoformat(),
            "cpu_usage": self.cpu_usage,
            "memory_usage": self.memory_usage,
            "disk_usage": self.disk_usage,
            "temperature": self.temperature,
            "active_jobs": self.active_jobs,
            "total_jobs": self.total_jobs,
            "successful_jobs": self.successful_jobs,
            "failed_jobs": self.failed_jobs,
            "success_rate": self.successful_jobs / self.total_jobs if self.total_jobs > 0 else 0,
            "performance_score": self.performance_score,
            "is_healthy": self.is_healthy()
        }

class WorkerRegistry:
    def __init__(self) -> None:
        self._workers: Dict[str, WorkerInfo] = {}
        self._heartbeat_timeout = 30  # secondes

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

    def set_status(self, host: str, status: WorkerStatus) -> None:
        """Change l'état logique d'un worker."""
        if host in self._workers:
            self._workers[host].status = status

    def update_metrics(self, host: str, cpu_usage: float, memory_usage: float, 
                      disk_usage: float, temperature: Optional[float] = None) -> None:
        """Met à jour les métriques d'un worker."""
        if host in self._workers:
            self._workers[host].update_metrics(cpu_usage, memory_usage, disk_usage, temperature)

    def set_metrics(self, host: str, metrics: Dict[str, any]) -> None:
        """Met à jour les métriques d'un worker avec un dictionnaire."""
        if host in self._workers:
            cpu_usage = metrics.get("cpu_usage", 0.0)
            memory_usage = metrics.get("memory_usage", 0.0)
            disk_usage = metrics.get("disk_usage", 0.0)
            temperature = metrics.get("temperature")
            self._workers[host].update_metrics(cpu_usage, memory_usage, disk_usage, temperature)

    def record_job_result(self, host: str, success: bool) -> None:
        """Enregistre le résultat d'un job pour un worker."""
        if host in self._workers:
            self._workers[host].record_job_result(success)

    def get(self, host: str) -> Optional[WorkerInfo]:
        """Récupère les informations d'un worker."""
        return self._workers.get(host)

    def list_ready(self, requires: Optional[List[str]] = None) -> List[str]:
        """Retourne les hôtes prêts qui possèdent toutes les `requires`."""
        requires = requires or []
        hosts: List[str] = []
        
        for host, info in self._workers.items():
            if (info.status == WorkerStatus.READY and 
                info.is_healthy() and 
                all(cap in info.capabilities for cap in requires)):
                hosts.append(host)
        
        return hosts

    def list_healthy(self) -> List[str]:
        """Retourne tous les workers en bonne santé."""
        return [host for host, info in self._workers.items() if info.is_healthy()]

    def list_by_performance(self, limit: Optional[int] = None) -> List[str]:
        """Retourne les workers triés par performance."""
        healthy_workers = [(host, info) for host, info in self._workers.items() 
                          if info.is_healthy()]
        
        # Trier par score de performance (plus haut = mieux)
        healthy_workers.sort(key=lambda x: x[1].performance_score, reverse=True)
        
        hosts = [host for host, _ in healthy_workers]
        return hosts[:limit] if limit else hosts

    def all_hosts(self) -> List[str]:
        """Retourne tous les hôtes enregistrés."""
        return list(self._workers.keys())

    def get_stats(self) -> Dict[str, any]:
        """Retourne les statistiques globales des workers."""
        total_workers = len(self._workers)
        healthy_workers = len(self.list_healthy())
        ready_workers = len(self.list_ready())
        busy_workers = len([w for w in self._workers.values() if w.status == WorkerStatus.BUSY])
        down_workers = total_workers - healthy_workers
        
        total_jobs = sum(w.total_jobs for w in self._workers.values())
        successful_jobs = sum(w.successful_jobs for w in self._workers.values())
        failed_jobs = sum(w.failed_jobs for w in self._workers.values())
        
        return {
            "total_workers": total_workers,
            "healthy_workers": healthy_workers,
            "ready_workers": ready_workers,
            "busy_workers": busy_workers,
            "down_workers": down_workers,
            "total_jobs": total_jobs,
            "successful_jobs": successful_jobs,
            "failed_jobs": failed_jobs,
            "success_rate": successful_jobs / total_jobs if total_jobs > 0 else 0,
            "average_performance": sum(w.performance_score for w in self._workers.values()) / total_workers if total_workers > 0 else 0
        }

    def cleanup_stale_workers(self, timeout_s: int = 300) -> List[str]:
        """Nettoie les workers qui n'ont pas envoyé de heartbeat depuis longtemps."""
        stale_workers = []
        current_time = time.time()
        
        for host, info in self._workers.items():
            if (current_time - info.last_heartbeat_s) > timeout_s:
                info.status = WorkerStatus.DOWN
                stale_workers.append(host)
        
        return stale_workers

    def get_worker_details(self, host: str) -> Optional[Dict[str, any]]:
        """Retourne les détails complets d'un worker."""
        worker = self._workers.get(host)
        if worker:
            return worker.to_dict()
        return None