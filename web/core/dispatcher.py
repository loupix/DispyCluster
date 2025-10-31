"""Dispatcher de tâches intégré dans l'interface web avec Dispy 4.15.

Algorithme adapté du core/dispatcher.py original avec des améliorations.
"""

from typing import Optional, Dict, List, Any
import asyncio
import time
from datetime import datetime
import os
import dispy
import dispy.httpd

from .load_balancer import LoadBalancer
from .fault_tolerance import FaultToleranceManager
from .task_queue import TaskQueue, Task, TaskStatus
from .worker_registry import WorkerRegistry, WorkerStatus

class Dispatcher:
    def __init__(self, registry: WorkerRegistry, queue: TaskQueue) -> None:
        self.registry = registry
        self.queue = queue
        self.load_balancer = LoadBalancer()
        self.fault_tolerance = FaultToleranceManager()
        self.dispatch_stats = {
            "total_dispatched": 0,
            "successful_dispatches": 0,
            "failed_dispatches": 0,
            "last_dispatch": None
        }
        
        # Initialiser Dispy cluster (désactivable via env WEB_INIT_DISPY=1)
        self.dispy_cluster = None
        self.dispy_jobs = []
        if os.getenv("WEB_INIT_DISPY", "0") in ("1", "true", "True"):
            self._init_dispy_cluster()

    def _init_dispy_cluster(self):
        """Initialise le cluster Dispy."""
        try:
            # Essayer de créer un cluster Dispy local
            print("Tentative de connexion au cluster Dispy local...")
            
            # Ajouter le répertoire parent au path pour importer les modules
            import sys
            from pathlib import Path
            import os
            parent_dir = Path(__file__).parent.parent.parent
            if str(parent_dir) not in sys.path:
                sys.path.insert(0, str(parent_dir))
            
            # Importer les fonctions de computation
            from scripts.dispy_functions import cpu_computation, scraping_computation
            
            # Configurer le répertoire de cache Dispy
            cache_dir = os.environ.get("DISPY_CACHE_DIR")
            if not cache_dir:
                cache_dir = str(Path(__file__).parent.parent / "temp" / "dispy")
            try:
                os.makedirs(cache_dir, exist_ok=True)
            except Exception as _:
                pass

            # Changer temporairement de répertoire pour que _dispy_* se créent au bon endroit
            cwd_before = os.getcwd()
            try:
                os.chdir(cache_dir)
                # Créer le cluster avec la fonction de scraping (plus polyvalente)
                # Note: Dispy peut utiliser plusieurs fonctions, on démarre avec scraping
                self.dispy_cluster = dispy.JobCluster(scraping_computation)
            finally:
                os.chdir(cwd_before)
            print(f"✓ Cluster Dispy connecté avec succès")
            
            # Tester le cluster avec un job simple (scraping)
            test_job = self.dispy_cluster.submit({
                'url': 'https://example.com',
                'max_pages': 1,
                'timeout_s': 5
            })
            test_result = test_job()
            if test_result and test_result.get('success'):
                print(f"✓ Test cluster réussi: {len(test_result.get('crawled', []))} pages scrapées")
            else:
                print(f"⚠️ Test cluster avec avertissement: {test_result.get('error', 'Unknown')}")
            
        except Exception as e:
            print(f"⚠️ Impossible de se connecter au cluster Dispy: {e}")
            print("Mode simulation activé")
            self.dispy_cluster = None

    def _dispach_function(self, task_data):
        """Fonction de dispatch pour Dispy."""
        try:
            # Simuler l'exécution de la tâche
            import time
            time.sleep(0.1)  # Simulation
            
            return {
                "success": True,
                "result": f"Task {task_data.get('id', 'unknown')} completed",
                "timestamp": datetime.now().isoformat()
            }
        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "timestamp": datetime.now().isoformat()
            }

    def _pick_target(self, requires: Optional[List[str]] = None, 
                    strategy: str = "round_robin") -> Optional[str]:
        """Sélectionne un nœud cible pour une tâche."""
        ready_nodes = self.registry.list_ready(requires=requires)
        
        if not ready_nodes:
            return None
        
        # Filtrer les nœuds avec circuit breaker ouvert
        available_nodes = []
        for node in ready_nodes:
            if (not self.fault_tolerance.circuit_breaker.is_open(node) and
                self.fault_tolerance.health_checker.is_healthy(node)):
                available_nodes.append(node)
        
        if not available_nodes:
            return None
        
        # Obtenir les métriques de performance
        performance_metrics = {}
        connection_counts = {}
        weights = {}
        
        for node in available_nodes:
            worker_info = self.registry.get(node)
            if worker_info:
                performance_metrics[node] = {
                    "cpu_usage": worker_info.cpu_usage,
                    "memory_usage": worker_info.memory_usage,
                    "response_time": 1.0 / worker_info.performance_score if worker_info.performance_score > 0 else 1.0
                }
                connection_counts[node] = worker_info.active_jobs
                weights[node] = worker_info.performance_score
        
        # Sélectionner le nœud selon la stratégie
        return self.load_balancer.get_balanced_selection(
            available_nodes,
            strategy=strategy,
            weights=weights,
            connection_counts=connection_counts,
            performance_metrics=performance_metrics
        )

    async def dispatch_once(self) -> Optional[Dict[str, Any]]:
        """Traite une tâche de la file."""
        task: Optional[Task] = self.queue.pop()
        if not task:
            return None
        
        target = self._pick_target(task.requires)
        if not target:
            # Pas de cible disponible, réinsérer en fin de file
            self.queue.push(task)
            return {"status": "queued", "reason": "no_available_nodes"}
        
        # Marquer la tâche comme en cours
        self.queue.mark_running(task, target)
        self.registry.set_status(target, WorkerStatus.BUSY)
        
        try:
            # Exécuter la tâche avec tolérance aux pannes
            result = await self._execute_task_with_fault_tolerance(task, target)
            
            if result["success"]:
                self.queue.mark_completed(task.id, result.get("data"))
                self.registry.set_status(target, WorkerStatus.READY)
                self.registry.record_job_result(target, True)
                self.load_balancer.update_node_performance(target, result.get("response_time", 0), True)
                
                self.dispatch_stats["successful_dispatches"] += 1
                return {"status": "completed", "target": target, "result": result}
            else:
                self.queue.mark_failed(task.id, result.get("error", "Unknown error"))
                self.registry.set_status(target, WorkerStatus.READY)
                self.registry.record_job_result(target, False)
                self.load_balancer.update_node_performance(target, result.get("response_time", 0), False)
                
                self.dispatch_stats["failed_dispatches"] += 1
                return {"status": "failed", "target": target, "error": result.get("error")}
                
        except Exception as e:
            self.queue.mark_failed(task.id, str(e))
            self.registry.set_status(target, WorkerStatus.READY)
            self.registry.record_job_result(target, False)
            
            self.dispatch_stats["failed_dispatches"] += 1
            return {"status": "error", "target": target, "error": str(e)}
        
        finally:
            self.dispatch_stats["total_dispatched"] += 1
            self.dispatch_stats["last_dispatch"] = datetime.now().isoformat()

    async def _execute_task_with_fault_tolerance(self, task: Task, target: str) -> Dict[str, Any]:
        """Exécute une tâche avec tolérance aux pannes via Dispy."""
        start_time = time.time()
        
        try:
            if self.dispy_cluster:
                # Utiliser Dispy pour exécuter la tâche
                result = await self._send_task_via_dispy(task, target)
            else:
                # Fallback vers simulation
                result = await self._send_task_to_worker(task, target)
            
            response_time = time.time() - start_time
            
            return {
                "success": True,
                "data": result,
                "response_time": response_time
            }
            
        except Exception as e:
            response_time = time.time() - start_time
            
            return {
                "success": False,
                "error": str(e),
                "response_time": response_time
            }

    async def _send_task_via_dispy(self, task: Task, target: str) -> Dict[str, Any]:
        """Envoie une tâche via Dispy."""
        try:
            # Préparer les données de la tâche selon le type
            task_type = task.payload.get("job_type", "scraper")
            service_name = task.payload.get("service_name", "scraper")
            
            # Si c'est un scraper ou scraping
            if task_type in ["scraper", "scraping"] or service_name == "scraper":
                task_data = {
                    "url": task.payload.get("url", ""),
                    "max_pages": task.payload.get("max_pages", 10),
                    "timeout_s": task.payload.get("timeout_s", 10),
                    "same_origin_only": task.payload.get("same_origin_only", True),
                    "job_id": task.payload.get("job_id", task.id)
                }
            else:  # CPU par défaut
                task_data = {
                    "iterations": task.payload.get("iterations", 10000)
                }
            
            # Soumettre le job à Dispy
            job = self.dispy_cluster.submit(task_data)
            self.dispy_jobs.append(job)
            
            # Attendre le résultat
            result = job()
            
            if result and result.get("success"):
                return result
            else:
                raise Exception(result.get("error", "Task failed"))
                
        except Exception as e:
            raise Exception(f"Dispy execution failed: {str(e)}")

    async def _send_task_to_worker(self, task: Task, target: str) -> Dict[str, Any]:
        """Envoie une tâche à un worker (fallback simulation)."""
        # Simulation d'un délai d'exécution
        await asyncio.sleep(0.1)
        
        # Simulation d'un taux de succès de 90%
        import random
        if random.random() < 0.9:
            return {
                "task_id": task.id,
                "result": f"Task {task.id} completed on {target}",
                "timestamp": datetime.now().isoformat()
            }
        else:
            raise Exception("Simulated task failure")

    def dispatch_all_pending(self) -> List[Dict[str, Any]]:
        """Traite toutes les tâches en attente."""
        results = []
        
        while True:
            result = asyncio.run(self.dispatch_once())
            if result is None:
                break
            results.append(result)
        
        return results

    def get_dispatch_stats(self) -> Dict[str, Any]:
        """Retourne les statistiques de dispatch."""
        total = self.dispatch_stats["total_dispatched"]
        success_rate = (self.dispatch_stats["successful_dispatches"] / total * 100) if total > 0 else 0
        
        return {
            **self.dispatch_stats,
            "success_rate": success_rate,
            "failure_rate": 100 - success_rate,
            "queue_size": len(self.queue),
            "available_workers": len(self.registry.list_ready()),
            "total_workers": len(self.registry.all_hosts())
        }

    def get_worker_performance(self) -> List[Dict[str, Any]]:
        """Retourne les performances des workers."""
        performance = []
        
        for host in self.registry.all_hosts():
            worker_info = self.registry.get(host)
            if worker_info:
                performance.append({
                    "host": host,
                    "performance_score": worker_info.performance_score,
                    "success_rate": worker_info.successful_jobs / worker_info.total_jobs if worker_info.total_jobs > 0 else 0,
                    "active_jobs": worker_info.active_jobs,
                    "cpu_usage": worker_info.cpu_usage,
                    "memory_usage": worker_info.memory_usage,
                    "status": worker_info.status.value
                })
        
        # Trier par score de performance
        performance.sort(key=lambda x: x["performance_score"], reverse=True)
        return performance

    def optimize_dispatch_strategy(self) -> str:
        """Détermine la meilleure stratégie de dispatch basée sur les performances."""
        stats = self.get_dispatch_stats()
        
        if stats["success_rate"] > 90:
            return "round_robin"  # Stratégie stable
        elif stats["success_rate"] > 70:
            return "best_performance"  # Optimiser les performances
        else:
            return "least_connections"  # Réduire la charge

    def auto_dispatch(self, max_tasks: int = 10) -> Dict[str, Any]:
        """Dispatch automatique avec optimisation."""
        strategy = self.optimize_dispatch_strategy()
        results = []
        
        for _ in range(max_tasks):
            result = asyncio.run(self.dispatch_once())
            if result is None:
                break
            results.append(result)
        
        return {
            "strategy_used": strategy,
            "tasks_processed": len(results),
            "results": results,
            "stats": self.get_dispatch_stats()
        }

    def get_dispy_status(self) -> Dict[str, Any]:
        """Retourne le statut du cluster Dispy."""
        if not self.dispy_cluster:
            return {"status": "not_initialized", "nodes": 0, "jobs": 0}
        
        try:
            # Obtenir les statistiques du cluster
            cluster_status = self.dispy_cluster.status()
            active_jobs = len([job for job in self.dispy_jobs if not job.finished()])
            
            return {
                "status": "active",
                "nodes": len(self.dispy_cluster.status()),
                "active_jobs": active_jobs,
                "total_jobs": len(self.dispy_jobs),
                "cluster_info": cluster_status
            }
        except Exception as e:
            return {"status": "error", "error": str(e)}

    def cleanup_dispy_jobs(self):
        """Nettoie les jobs Dispy terminés."""
        if not self.dispy_jobs:
            return 0
        
        cleaned = 0
        active_jobs = []
        
        for job in self.dispy_jobs:
            if job.finished():
                cleaned += 1
            else:
                active_jobs.append(job)
        
        self.dispy_jobs = active_jobs
        return cleaned

    def shutdown_dispy_cluster(self):
        """Arrête le cluster Dispy proprement."""
        if self.dispy_cluster:
            try:
                self.dispy_cluster.close()
                print("Cluster Dispy arrêté proprement")
            except Exception as e:
                print(f"Erreur lors de l'arrêt du cluster Dispy: {e}")
            finally:
                self.dispy_cluster = None