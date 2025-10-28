"""Vue intelligente pour la gestion du cluster.

Utilise les algorithmes du core pour fournir une interface unifiée.
"""

from typing import Dict, List, Any, Optional
from datetime import datetime
import asyncio
import json
import redis

from web.core.cluster_manager import ClusterManager
from web.core.worker_registry import WorkerRegistry, WorkerStatus
from web.core.task_queue import TaskQueue, Task, TaskPriority
from web.core.dispatcher import Dispatcher
from web.core.fault_tolerance import FaultToleranceManager
from web.config.metrics_config import REDIS_CONFIG
from web.config.logging_config import get_logger

# Configuration du logger
logger = get_logger(__name__)

class ClusterView:
    def __init__(self):
        self.cluster_manager = ClusterManager()
        self.worker_registry = WorkerRegistry()
        self.task_queue = TaskQueue()
        self.dispatcher = Dispatcher(self.worker_registry, self.task_queue)
        self.fault_tolerance = FaultToleranceManager()
        
        # Client Redis pour le cache des métriques
        self.redis_client = redis.Redis(**REDIS_CONFIG)
        
        # Initialiser les workers
        self._initialize_workers()

    def _initialize_workers(self):
        """Initialise les workers depuis la config nodes.yaml via ClusterManager."""
        if not self.cluster_manager.nodes:
            return
        default_capabilities = ["cpu", "scraping"]
        for node in self.cluster_manager.nodes:
            self.worker_registry.register(node, default_capabilities)
            self.worker_registry.set_metrics(node, {
                "cpu_usage": 45.2,
                "memory_usage": 67.8,
                "disk_usage": 23.1,
                "load_average": 1.2,
                "temperature": 42.5
            })

    def _get_cached_metrics(self) -> Optional[Dict[str, Any]]:
        """Récupère les métriques depuis le cache Redis."""
        try:
            cached_data = self.redis_client.get("cluster:metrics")
            if cached_data:
                data = json.loads(cached_data)
                # Les données Redis sont déjà dans le bon format
                return data
        except Exception as e:
            logger.error(f"Erreur lecture cache Redis: {e}")
        return None

    async def get_cluster_overview(self) -> Dict[str, Any]:
        """Vue d'ensemble intelligente du cluster avec cache Redis."""
        # Essayer d'abord le cache Redis
        cached_metrics = self._get_cached_metrics()
        if cached_metrics:
            # Calculer les vraies moyennes depuis les métriques individuelles
            total_cpu = 0.0
            total_memory = 0.0
            total_temperature = 0.0
            online_count = 0
            
            for node in self.cluster_manager.nodes:
                try:
                    node_metrics = self.redis_client.get(f"metrics:{node}")
                    if node_metrics:
                        metrics = json.loads(node_metrics)
                        cpu = metrics.get("cpu_usage", 0.0)
                        memory = metrics.get("memory_usage", 0.0)
                        temp = metrics.get("temperature", 0.0)
                        
                        if cpu > 0:  # Nœud actif
                            total_cpu += cpu
                            total_memory += memory
                            total_temperature += temp
                            online_count += 1
                except Exception as e:
                    logger.error(f"Erreur calcul moyenne {node}: {e}")
                    continue
            
            # Calculer les moyennes
            avg_cpu = total_cpu / online_count if online_count > 0 else 0.0
            avg_memory = total_memory / online_count if online_count > 0 else 0.0
            avg_temperature = total_temperature / online_count if online_count > 0 else 0.0
            
            # Construire la réponse avec les données calculées
            cluster_stats = {
                "total_nodes": len(self.cluster_manager.nodes),
                "ready_nodes": online_count,
                "down_nodes": len(self.cluster_manager.nodes) - online_count,
                "cpu_usage_avg": round(avg_cpu, 1),
                "memory_usage_avg": round(avg_memory, 1),
                "disk_usage_avg": 0.0,  # Pas calculé pour l'instant
                "last_check": datetime.now().isoformat()
            }
            
            # Déterminer le statut global
            if cluster_stats["down_nodes"] == 0:
                overall_status = "healthy"
            elif cluster_stats["down_nodes"] <= 2:
                overall_status = "warning"
            else:
                overall_status = "critical"
            
            return {
                "status": overall_status,
                "cluster_stats": cluster_stats,
                "worker_stats": {},
                "task_stats": {},
                "dispatch_stats": {},
                "health_status": {},
                "services_status": {
                    "cluster_controller": "online",
                    "monitoring": "online", 
                    "scheduler": "online",
                    "scraper": "online"
                },
                "timestamp": cached_metrics.get("timestamp", datetime.now().isoformat())
            }
        
        # Fallback vers la méthode classique si pas de cache
        # Vérifier la santé de tous les nœuds
        health_status = await self.cluster_manager.check_all_nodes()
        
        # Mettre à jour le registre des workers et les statuts du cluster
        for node, is_healthy in health_status.items():
            if is_healthy:
                self.worker_registry.set_status(node, WorkerStatus.READY)
                self.cluster_manager.mark_node_status(node, "ready")
            else:
                self.worker_registry.set_status(node, WorkerStatus.DOWN)
                self.cluster_manager.mark_node_status(node, "down")
        
        # Statistiques du cluster
        cluster_stats = self.cluster_manager.get_cluster_stats()
        worker_stats = self.worker_registry.get_stats()
        task_stats = self.task_queue.get_stats()
        dispatch_stats = self.dispatcher.get_dispatch_stats()
        
        # Déterminer le statut global
        if cluster_stats["down_nodes"] == 0:
            overall_status = "healthy"
        elif cluster_stats["down_nodes"] <= 2:
            overall_status = "warning"
        else:
            overall_status = "critical"
        
        # Services simulés
        services_status = {
            "cluster_controller": "online",
            "monitoring": "online", 
            "scheduler": "online",
            "scraper": "online"
        }
        
        return {
            "status": overall_status,
            "cluster_stats": cluster_stats,
            "worker_stats": worker_stats,
            "task_stats": task_stats,
            "dispatch_stats": dispatch_stats,
            "health_status": health_status,
            "services_status": services_status,
            "timestamp": datetime.now().isoformat()
        }

    async def get_nodes_status(self) -> List[Dict[str, Any]]:
        """Statut détaillé de tous les nœuds avec cache Redis."""
        # Essayer d'abord le cache Redis - récupérer les métriques individuelles
        nodes_data = []
        
        # Récupérer les métriques individuelles depuis Redis
        for node in self.cluster_manager.nodes:
            try:
                node_metrics = self.redis_client.get(f"metrics:{node}")
                if node_metrics:
                    metrics = json.loads(node_metrics)
                    
                    # Construire le format attendu par l'API
                    formatted_node = {
                        "node": node,
                        "status": "ready" if metrics.get("cpu_usage", 0) > 0 else "unknown",
                        "last_update": datetime.now().isoformat(),
                        "is_healthy": metrics.get("cpu_usage", 0) > 0,
                        "capabilities": ["cpu", "scraping"],
                        "performance_score": 0.6148,
                        "active_jobs": 0,
                        "total_jobs": 0,
                        "success_rate": 0,
                        # Métriques du cache
                        "cpu_usage": metrics.get("cpu_usage", 0.0),
                        "memory_usage": metrics.get("memory_usage", 0.0),
                        "disk_usage": metrics.get("disk_usage", 0.0),
                        "temperature": metrics.get("temperature", 0.0)
                    }
                    nodes_data.append(formatted_node)
                else:
                    # Nœud sans métriques
                    formatted_node = {
                        "node": node,
                        "status": "unknown",
                        "last_update": None,
                        "is_healthy": False,
                        "capabilities": ["cpu", "scraping"],
                        "performance_score": 0.6148,
                        "active_jobs": 0,
                        "total_jobs": 0,
                        "success_rate": 0,
                        "cpu_usage": 0.0,
                        "memory_usage": 0.0,
                        "disk_usage": 0.0,
                        "temperature": 0.0
                    }
                    nodes_data.append(formatted_node)
            except Exception as e:
                logger.error(f"Erreur métriques {node}: {e}")
                # Ajouter quand même le nœud sans métriques
                formatted_node = {
                    "node": node,
                    "status": "unknown",
                    "last_update": None,
                    "is_healthy": False,
                    "capabilities": ["cpu", "scraping"],
                    "performance_score": 0.6148,
                    "active_jobs": 0,
                    "total_jobs": 0,
                    "success_rate": 0,
                    "cpu_usage": 0.0,
                    "memory_usage": 0.0,
                    "disk_usage": 0.0,
                    "temperature": 0.0
                }
                nodes_data.append(formatted_node)
        
        if nodes_data:
            return nodes_data
        
        # Fallback vers la méthode classique
        nodes_data = []
        
        for node in self.cluster_manager.nodes:
            worker_info = self.worker_registry.get(node)
            health_info = self.cluster_manager.get_node_health(node)
            
            node_data = {
                "node": node,
                "status": health_info["status"],
                "last_update": health_info["last_update"].isoformat() if health_info["last_update"] else None,
                "is_healthy": health_info["status"] == "ready",
                "capabilities": worker_info.capabilities if worker_info else [],
                "performance_score": worker_info.performance_score if worker_info else 0,
                "active_jobs": worker_info.active_jobs if worker_info else 0,
                "total_jobs": worker_info.total_jobs if worker_info else 0,
                "success_rate": (worker_info.successful_jobs / worker_info.total_jobs * 100) if worker_info and worker_info.total_jobs > 0 else 0
            }
            
            # Ajouter les métriques si disponibles
            if health_info["metrics"]:
                node_data.update(health_info["metrics"])
            
            nodes_data.append(node_data)
        
        return nodes_data

    async def get_node_details(self, node_name: str) -> Dict[str, Any]:
        """Détails d'un nœud spécifique."""
        if node_name not in self.cluster_manager.nodes:
            return {"error": "Nœud non trouvé"}
        
        worker_info = self.worker_registry.get(node_name)
        health_info = self.cluster_manager.get_node_health(node_name)
        circuit_stats = self.fault_tolerance.circuit_breaker.get_stats(node_name)
        
        return {
            "node": node_name,
            "health": health_info,
            "worker_info": worker_info.to_dict() if worker_info else None,
            "circuit_breaker": circuit_stats,
            "recent_tasks": self._get_recent_tasks_for_node(node_name),
            "performance_history": self._get_performance_history(node_name)
        }

    def _get_recent_tasks_for_node(self, node_name: str) -> List[Dict[str, Any]]:
        """Récupère les tâches récentes pour un nœud."""
        recent_tasks = self.task_queue.get_recent_tasks(limit=20)
        node_tasks = [task for task in recent_tasks if task.assigned_node == node_name]
        return [task.to_dict() for task in node_tasks]

    def _get_performance_history(self, node_name: str) -> List[Dict[str, Any]]:
        """Récupère l'historique de performance d'un nœud."""
        # Simulation d'historique de performance
        # Dans une implémentation réelle, ceci viendrait d'une base de données
        return [
            {"timestamp": datetime.now().isoformat(), "cpu_usage": 45.2, "memory_usage": 67.8},
            {"timestamp": datetime.now().isoformat(), "cpu_usage": 52.1, "memory_usage": 71.2},
            {"timestamp": datetime.now().isoformat(), "cpu_usage": 38.9, "memory_usage": 63.4}
        ]

    async def submit_job(self, job_data: Dict[str, Any]) -> Dict[str, Any]:
        """Soumet un nouveau job au cluster via Dispy."""
        # Créer la tâche
        task = Task(
            payload=job_data,
            requires=job_data.get("requires", []),
            priority=TaskPriority(job_data.get("priority", 2))
        )
        
        # Ajouter à la file
        self.task_queue.push(task)
        
        # Déclencher le dispatch automatique avec Dispy
        dispatch_result = self.dispatcher.auto_dispatch(max_tasks=1)
        
        # Obtenir le statut Dispy
        dispy_status = self.dispatcher.get_dispy_status()
        
        return {
            "task_id": task.id,
            "status": "submitted",
            "dispatch_result": dispatch_result,
            "queue_position": len(self.task_queue),
            "dispy_status": dispy_status
        }

    async def get_jobs_status(self) -> Dict[str, Any]:
        """Statut des jobs avec intelligence."""
        stats = self.task_queue.get_stats()
        recent_tasks = self.task_queue.get_recent_tasks(limit=10)
        
        # Analyser les performances
        performance_analysis = self._analyze_job_performance()
        
        return {
            "stats": stats,
            "recent_tasks": [task.to_dict() for task in recent_tasks],
            "performance_analysis": performance_analysis,
            "recommendations": self._get_job_recommendations()
        }

    def _analyze_job_performance(self) -> Dict[str, Any]:
        """Analyse les performances des jobs."""
        worker_performance = self.dispatcher.get_worker_performance()
        
        # Calculer les métriques
        total_jobs = sum(w["total_jobs"] for w in worker_performance)
        successful_jobs = sum(w["successful_jobs"] for w in worker_performance)
        success_rate = (successful_jobs / total_jobs * 100) if total_jobs > 0 else 0
        
        # Identifier les workers les plus performants
        top_workers = sorted(worker_performance, key=lambda x: x["performance_score"], reverse=True)[:3]
        
        return {
            "overall_success_rate": success_rate,
            "total_jobs_processed": total_jobs,
            "top_performers": top_workers,
            "bottlenecks": self._identify_bottlenecks(worker_performance)
        }

    def _identify_bottlenecks(self, worker_performance: List[Dict[str, Any]]) -> List[str]:
        """Identifie les goulots d'étranglement."""
        bottlenecks = []
        
        for worker in worker_performance:
            if worker["cpu_usage"] > 90:
                bottlenecks.append(f"{worker['host']}: CPU usage élevé")
            if worker["memory_usage"] > 90:
                bottlenecks.append(f"{worker['host']}: Mémoire usage élevé")
            if worker["success_rate"] < 70:
                bottlenecks.append(f"{worker['host']}: Taux de succès faible")
        
        return bottlenecks

    def _get_job_recommendations(self) -> List[str]:
        """Génère des recommandations pour optimiser les jobs."""
        recommendations = []
        
        stats = self.dispatcher.get_dispatch_stats()
        
        if stats["success_rate"] < 80:
            recommendations.append("Considérer l'ajout de plus de workers")
        
        if stats["queue_size"] > 50:
            recommendations.append("La file de tâches est surchargée, optimiser le dispatch")
        
        if len(self.worker_registry.list_ready()) < 3:
            recommendations.append("Peu de workers disponibles, vérifier la santé du cluster")
        
        return recommendations

    async def optimize_cluster(self) -> Dict[str, Any]:
        """Optimise automatiquement le cluster avec Dispy."""
        # Nettoyer les anciennes tâches
        cleaned_tasks = self.task_queue.cleanup_old_tasks(days=7)
        
        # Nettoyer les jobs Dispy terminés
        cleaned_dispy_jobs = self.dispatcher.cleanup_dispy_jobs()
        
        # Optimiser la stratégie de dispatch
        optimal_strategy = self.dispatcher.optimize_dispatch_strategy()
        
        # Nettoyer les workers inactifs
        stale_workers = self.worker_registry.cleanup_stale_workers()
        
        # Dispatch automatique
        dispatch_result = self.dispatcher.auto_dispatch(max_tasks=5)
        
        # Obtenir le statut Dispy
        dispy_status = self.dispatcher.get_dispy_status()
        
        return {
            "cleaned_tasks": cleaned_tasks,
            "cleaned_dispy_jobs": cleaned_dispy_jobs,
            "optimal_strategy": optimal_strategy,
            "stale_workers_cleaned": len(stale_workers),
            "dispatch_result": dispatch_result,
            "dispy_status": dispy_status,
            "optimization_timestamp": datetime.now().isoformat()
        }