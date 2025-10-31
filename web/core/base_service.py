"""Classe de base abstraite pour tous les services DispyCluster.

Permet de créer facilement de nouveaux services (scraper, image processing, NLP, etc.)
avec une architecture cohérente et réutilisable.
"""

from abc import ABC, abstractmethod
from typing import Dict, List, Any, Optional
from datetime import datetime
import uuid
import json
import redis
from web.config.metrics_config import REDIS_CONFIG
from web.config.logging_config import get_logger
from web.core.dispatcher import Dispatcher
from web.core.task_queue import TaskQueue, Task, TaskPriority

logger = get_logger(__name__)


class BaseService(ABC):
    """Classe de base pour tous les services distribués sur Dispy cluster."""
    
    def __init__(
        self,
        service_name: str,
        dispatcher: Dispatcher,
        task_queue: TaskQueue,
        redis_client: Optional[redis.Redis] = None
    ):
        """Initialise un service de base.
        
        Args:
            service_name: Nom unique du service (ex: 'scraper', 'image_processor')
            dispatcher: Instance du Dispatcher pour soumettre des jobs à Dispy
            task_queue: File de tâches partagée
            redis_client: Client Redis pour pub/sub et cache (optionnel)
        """
        self.service_name = service_name
        self.dispatcher = dispatcher
        self.task_queue = task_queue
        self.redis_client = redis_client or redis.Redis(**REDIS_CONFIG)
        
        # Statistiques du service
        self.stats = {
            "total_jobs": 0,
            "successful_jobs": 0,
            "failed_jobs": 0,
            "active_jobs": 0,
            "created_at": datetime.now().isoformat()
        }
    
    @abstractmethod
    async def process_job(self, job_data: Dict[str, Any]) -> Dict[str, Any]:
        """Traitement spécifique d'un job (à implémenter par chaque service).
        
        Args:
            job_data: Données du job à traiter
            
        Returns:
            Résultat du traitement
        """
        pass
    
    @abstractmethod
    def validate_job_data(self, job_data: Dict[str, Any]) -> tuple[bool, Optional[str]]:
        """Valide les données d'un job avant soumission.
        
        Args:
            job_data: Données à valider
            
        Returns:
            Tuple (is_valid, error_message)
        """
        pass
    
    async def submit_job(
        self,
        job_data: Dict[str, Any],
        priority: int = 1,
        requires: Optional[List[str]] = None
    ) -> Dict[str, Any]:
        """Soumet un job au cluster via Dispy.
        
        Args:
            job_data: Données du job
            priority: Priorité (1-10, plus élevé = plus prioritaire)
            requires: Capacités requises (ex: ['gpu', 'scraping'])
            
        Returns:
            Informations sur le job soumis
        """
        # Valider les données
        is_valid, error = self.validate_job_data(job_data)
        if not is_valid:
            return {
                "success": False,
                "error": error,
                "job_id": None
            }
        
        # Créer l'ID unique du job
        job_id = str(uuid.uuid4())
        job_data["job_id"] = job_id
        job_data["service_name"] = self.service_name
        job_data["job_type"] = self.service_name
        job_data["created_at"] = datetime.now().isoformat()
        
        # Créer la tâche
        task = Task(
            payload=job_data,
            requires=requires or [],
            priority=TaskPriority(min(max(priority, 1), 10))
        )
        
        # Ajouter à la file
        self.task_queue.push(task)
        self.stats["total_jobs"] += 1
        self.stats["active_jobs"] += 1
        
        # Émettre un événement Redis pour le WebSocket
        await self._publish_job_event("job_submitted", {
            "job_id": job_id,
            "service_name": self.service_name,
            "status": "submitted",
            "priority": priority
        })
        
        # Déclencher le dispatch automatique
        dispatch_result = self.dispatcher.auto_dispatch(max_tasks=1)
        
        return {
            "success": True,
            "job_id": job_id,
            "task_id": task.id,
            "status": "submitted",
            "dispatch_result": dispatch_result,
            "queue_position": len(self.task_queue)
        }
    
    async def get_job_status(self, job_id: str) -> Dict[str, Any]:
        """Récupère le statut d'un job.
        
        Args:
            job_id: ID du job
            
        Returns:
            Statut du job
        """
        # Chercher dans la file de tâches
        task = self.task_queue.get_by_id(job_id)
        
        if task:
            return {
                "job_id": job_id,
                "status": task.status.value,
                "assigned_node": task.assigned_node,
                "progress": task.progress,
                "created_at": task.created_at.isoformat() if task.created_at else None,
                "started_at": task.started_at.isoformat() if task.started_at else None,
                "result": task.result
            }
        
        # Si pas trouvé, vérifier dans le cache Redis
        cached = self.redis_client.get(f"job:{job_id}")
        if cached:
            return json.loads(cached)
        
        return {
            "job_id": job_id,
            "status": "not_found",
            "error": "Job non trouvé"
        }
    
    async def get_service_stats(self) -> Dict[str, Any]:
        """Retourne les statistiques du service.
        
        Returns:
            Statistiques complètes
        """
        success_rate = (
            self.stats["successful_jobs"] / self.stats["total_jobs"] * 100
            if self.stats["total_jobs"] > 0
            else 0
        )
        
        # Stats du dispatcher pour ce service
        dispatch_stats = self.dispatcher.get_dispatch_stats()
        dispy_status = self.dispatcher.get_dispy_status()
        
        return {
            "service_name": self.service_name,
            "stats": {
                **self.stats,
                "success_rate": round(success_rate, 2),
                "failure_rate": round(100 - success_rate, 2)
            },
            "dispatcher": dispatch_stats,
            "dispy_cluster": dispy_status,
            "queue_size": len(self.task_queue),
            "timestamp": datetime.now().isoformat()
        }
    
    async def list_jobs(
        self,
        status: Optional[str] = None,
        limit: int = 50
    ) -> List[Dict[str, Any]]:
        """Liste les jobs du service.
        
        Args:
            status: Filtrer par statut (optionnel)
            limit: Nombre maximum de jobs à retourner
            
        Returns:
            Liste des jobs
        """
        all_tasks = self.task_queue.get_recent_tasks(limit=limit * 2)
        
        # Filtrer par service
        service_tasks = [
            task for task in all_tasks
            if task.payload.get("service_name") == self.service_name
        ]
        
        # Filtrer par statut si demandé
        if status:
            service_tasks = [
                task for task in service_tasks
                if task.status.value == status
            ]
        
        # Limiter et convertir
        return [task.to_dict() for task in service_tasks[:limit]]
    
    async def cancel_job(self, job_id: str) -> Dict[str, Any]:
        """Annule un job en cours.
        
        Args:
            job_id: ID du job à annuler
            
        Returns:
            Résultat de l'annulation
        """
        task = self.task_queue.get_by_id(job_id)
        
        if not task:
            return {
                "success": False,
                "error": "Job non trouvé"
            }
        
        if task.status.value in ["completed", "failed"]:
            return {
                "success": False,
                "error": f"Impossible d'annuler un job {task.status.value}"
            }
        
        # Marquer comme annulé
        self.task_queue.mark_failed(job_id, "Annulé par l'utilisateur")
        self.stats["active_jobs"] = max(0, self.stats["active_jobs"] - 1)
        
        # Émettre un événement
        await self._publish_job_event("job_cancelled", {
            "job_id": job_id,
            "service_name": self.service_name
        })
        
        return {
            "success": True,
            "job_id": job_id,
            "message": "Job annulé"
        }
    
    async def _publish_job_event(self, event_type: str, data: Dict[str, Any]) -> None:
        """Publie un événement Redis pour le WebSocket.
        
        Args:
            event_type: Type d'événement (ex: 'job_submitted', 'job_completed')
            data: Données de l'événement
        """
        try:
            event_data = {
                "service_name": self.service_name,
                "event_type": event_type,
                "data": data,
                "timestamp": datetime.now().isoformat()
            }
            
            # Canal Redis pour ce service
            channel = f"{self.service_name}:events"
            self.redis_client.publish(channel, json.dumps(event_data))
            
            # Canal global aussi
            global_channel = "cluster:events"
            self.redis_client.publish(global_channel, json.dumps(event_data))
            
        except Exception as e:
            logger.warning(f"Impossible de publier l'événement {event_type}: {e}")
    
    def record_job_result(self, success: bool) -> None:
        """Enregistre le résultat d'un job pour les stats.
        
        Args:
            success: True si le job a réussi
        """
        if success:
            self.stats["successful_jobs"] += 1
        else:
            self.stats["failed_jobs"] += 1
        
        self.stats["active_jobs"] = max(0, self.stats["active_jobs"] - 1)

