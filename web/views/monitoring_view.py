"""Vue intelligente pour le monitoring du cluster.

Utilise les algorithmes du core pour fournir un monitoring avancé.
"""

from typing import Dict, List, Any, Optional
from datetime import datetime, timedelta
import asyncio
import json

from web.core.cluster_manager import ClusterManager
from web.core.worker_registry import WorkerRegistry, WorkerStatus
from web.core.task_queue import TaskQueue
from web.core.dispatcher import Dispatcher
from web.core.fault_tolerance import FaultToleranceManager

class MonitoringView:
    def __init__(self, cluster_view):
        self.cluster_view = cluster_view
        self.cluster_manager = cluster_view.cluster_manager
        self.worker_registry = cluster_view.worker_registry
        self.task_queue = cluster_view.task_queue
        self.dispatcher = cluster_view.dispatcher
        self.fault_tolerance = cluster_view.fault_tolerance
        
        # Historique des métriques
        self.metrics_history = []
        self.alerts_history = []

    async def get_comprehensive_metrics(self) -> Dict[str, Any]:
        """Métriques complètes du cluster."""
        # Métriques de base
        cluster_overview = await self.cluster_view.get_cluster_overview()
        nodes_status = await self.cluster_view.get_nodes_status()
        jobs_status = await self.cluster_view.get_jobs_status()
        
        # Métriques avancées
        performance_metrics = self._calculate_performance_metrics()
        health_metrics = self._calculate_health_metrics()
        efficiency_metrics = self._calculate_efficiency_metrics()
        
        # Détecter les anomalies
        anomalies = self._detect_anomalies()
        
        return {
            "timestamp": datetime.now().isoformat(),
            "cluster_overview": cluster_overview,
            "nodes_status": nodes_status,
            "jobs_status": jobs_status,
            "performance_metrics": performance_metrics,
            "health_metrics": health_metrics,
            "efficiency_metrics": efficiency_metrics,
            "anomalies": anomalies,
            "recommendations": self._generate_recommendations()
        }

    def _calculate_performance_metrics(self) -> Dict[str, Any]:
        """Calcule les métriques de performance."""
        worker_performance = self.dispatcher.get_worker_performance()
        dispatch_stats = self.dispatcher.get_dispatch_stats()
        
        # Métriques de performance
        avg_performance = sum(w["performance_score"] for w in worker_performance) / len(worker_performance) if worker_performance else 0
        avg_success_rate = sum(w["success_rate"] for w in worker_performance) / len(worker_performance) if worker_performance else 0
        
        # Throughput
        total_jobs = sum(w["total_jobs"] for w in worker_performance)
        successful_jobs = sum(w["successful_jobs"] for w in worker_performance)
        throughput = total_jobs / 24 if total_jobs > 0 else 0  # Jobs par heure
        
        return {
            "average_performance_score": avg_performance,
            "average_success_rate": avg_success_rate,
            "total_jobs_processed": total_jobs,
            "successful_jobs": successful_jobs,
            "throughput_per_hour": throughput,
            "top_performers": sorted(worker_performance, key=lambda x: x["performance_score"], reverse=True)[:3],
            "dispatch_success_rate": dispatch_stats.get("success_rate", 0)
        }

    def _calculate_health_metrics(self) -> Dict[str, Any]:
        """Calcule les métriques de santé."""
        all_nodes = self.worker_registry.all_hosts()
        healthy_nodes = self.worker_registry.list_healthy()
        ready_nodes = self.worker_registry.list_ready()
        
        # Santé du cluster
        health_rate = len(healthy_nodes) / len(all_nodes) if all_nodes else 0
        availability_rate = len(ready_nodes) / len(all_nodes) if all_nodes else 0
        
        # Circuit breaker stats
        circuit_stats = self.fault_tolerance.circuit_breaker.get_all_stats()
        open_circuits = sum(1 for stats in circuit_stats.values() if stats["is_open"])
        
        # Health checker stats
        health_stats = self.fault_tolerance.health_checker.get_health_stats()
        
        return {
            "health_rate": health_rate,
            "availability_rate": availability_rate,
            "healthy_nodes": len(healthy_nodes),
            "total_nodes": len(all_nodes),
            "open_circuits": open_circuits,
            "health_checker_stats": health_stats,
            "circuit_breaker_stats": circuit_stats
        }

    def _calculate_efficiency_metrics(self) -> Dict[str, Any]:
        """Calcule les métriques d'efficacité."""
        task_stats = self.task_queue.get_stats()
        dispatch_stats = self.dispatcher.get_dispatch_stats()
        
        # Efficacité de la file
        queue_efficiency = 1.0 - (task_stats["pending"] / max(task_stats["total"], 1))
        
        # Efficacité du dispatch
        dispatch_efficiency = dispatch_stats.get("success_rate", 0) / 100
        
        # Utilisation des ressources
        worker_performance = self.dispatcher.get_worker_performance()
        avg_cpu = sum(w["cpu_usage"] for w in worker_performance) / len(worker_performance) if worker_performance else 0
        avg_memory = sum(w["memory_usage"] for w in worker_performance) / len(worker_performance) if worker_performance else 0
        
        return {
            "queue_efficiency": queue_efficiency,
            "dispatch_efficiency": dispatch_efficiency,
            "resource_utilization": {
                "avg_cpu_usage": avg_cpu,
                "avg_memory_usage": avg_memory,
                "utilization_score": (avg_cpu + avg_memory) / 2
            },
            "task_processing_rate": dispatch_stats.get("total_dispatched", 0),
            "efficiency_score": (queue_efficiency + dispatch_efficiency) / 2
        }

    def _detect_anomalies(self) -> List[Dict[str, Any]]:
        """Détecte les anomalies dans le cluster."""
        anomalies = []
        
        # Vérifier les workers
        for host in self.worker_registry.all_hosts():
            worker_info = self.worker_registry.get(host)
            if worker_info:
                # CPU élevé
                if worker_info.cpu_usage > 90:
                    anomalies.append({
                        "type": "high_cpu_usage",
                        "node": host,
                        "severity": "warning",
                        "message": f"CPU usage élevé: {worker_info.cpu_usage:.1f}%"
                    })
                
                # Mémoire élevée
                if worker_info.memory_usage > 90:
                    anomalies.append({
                        "type": "high_memory_usage",
                        "node": host,
                        "severity": "warning",
                        "message": f"Mémoire usage élevé: {worker_info.memory_usage:.1f}%"
                    })
                
                # Taux de succès faible
                if worker_info.total_jobs > 10 and worker_info.successful_jobs / worker_info.total_jobs < 0.7:
                    anomalies.append({
                        "type": "low_success_rate",
                        "node": host,
                        "severity": "error",
                        "message": f"Taux de succès faible: {worker_info.successful_jobs / worker_info.total_jobs * 100:.1f}%"
                    })
        
        # Vérifier les circuits ouverts
        circuit_stats = self.fault_tolerance.circuit_breaker.get_all_stats()
        for node, stats in circuit_stats.items():
            if stats["is_open"]:
                anomalies.append({
                    "type": "circuit_breaker_open",
                    "node": node,
                    "severity": "error",
                    "message": f"Circuit breaker ouvert pour {node}"
                })
        
        # Vérifier la file de tâches
        task_stats = self.task_queue.get_stats()
        if task_stats["pending"] > 100:
            anomalies.append({
                "type": "queue_overload",
                "node": "system",
                "severity": "warning",
                "message": f"File de tâches surchargée: {task_stats['pending']} tâches en attente"
            })
        
        return anomalies

    def _generate_recommendations(self) -> List[Dict[str, Any]]:
        """Génère des recommandations d'optimisation."""
        recommendations = []
        
        # Analyser les performances
        performance_metrics = self._calculate_performance_metrics()
        health_metrics = self._calculate_health_metrics()
        efficiency_metrics = self._calculate_efficiency_metrics()
        
        # Recommandations basées sur les métriques
        if performance_metrics["average_success_rate"] < 80:
            recommendations.append({
                "type": "performance",
                "priority": "high",
                "message": "Taux de succès global faible, vérifier la configuration des workers",
                "action": "Optimiser les paramètres des workers et vérifier la connectivité"
            })
        
        if health_metrics["health_rate"] < 0.8:
            recommendations.append({
                "type": "health",
                "priority": "high",
                "message": "Taux de santé du cluster faible",
                "action": "Vérifier l'état des nœuds et redémarrer si nécessaire"
            })
        
        if efficiency_metrics["queue_efficiency"] < 0.5:
            recommendations.append({
                "type": "efficiency",
                "priority": "medium",
                "message": "Efficacité de la file de tâches faible",
                "action": "Optimiser la stratégie de dispatch et augmenter la capacité"
            })
        
        if efficiency_metrics["resource_utilization"]["utilization_score"] > 80:
            recommendations.append({
                "type": "resources",
                "priority": "medium",
                "message": "Utilisation des ressources élevée",
                "action": "Considérer l'ajout de nouveaux workers ou l'optimisation des tâches"
            })
        
        return recommendations

    async def get_real_time_metrics(self) -> Dict[str, Any]:
        """Métriques en temps réel."""
        # Mettre à jour les métriques
        await self.cluster_manager.check_all_nodes()
        
        # Récupérer les métriques actuelles
        current_metrics = await self.get_comprehensive_metrics()
        
        # Ajouter à l'historique
        self.metrics_history.append({
            "timestamp": datetime.now().isoformat(),
            "metrics": current_metrics
        })
        
        # Garder seulement les 100 dernières entrées
        if len(self.metrics_history) > 100:
            self.metrics_history = self.metrics_history[-100:]
        
        return current_metrics

    def get_metrics_history(self, hours: int = 24) -> List[Dict[str, Any]]:
        """Récupère l'historique des métriques."""
        cutoff_time = datetime.now() - timedelta(hours=hours)
        
        filtered_history = []
        for entry in self.metrics_history:
            entry_time = datetime.fromisoformat(entry["timestamp"])
            if entry_time >= cutoff_time:
                filtered_history.append(entry)
        
        return filtered_history

    async def get_alerts(self) -> Dict[str, Any]:
        """Récupère les alertes actives."""
        current_metrics = await self.get_real_time_metrics()
        anomalies = current_metrics.get("anomalies", [])
        
        # Catégoriser les alertes
        alerts_by_severity = {
            "error": [],
            "warning": [],
            "info": []
        }
        
        for anomaly in anomalies:
            severity = anomaly.get("severity", "info")
            alerts_by_severity[severity].append(anomaly)
        
        return {
            "active_alerts": anomalies,
            "alerts_by_severity": alerts_by_severity,
            "total_alerts": len(anomalies),
            "critical_alerts": len(alerts_by_severity["error"]),
            "warning_alerts": len(alerts_by_severity["warning"]),
            "timestamp": datetime.now().isoformat()
        }

    async def export_metrics(self, format: str = "json") -> Dict[str, Any]:
        """Exporte les métriques dans différents formats."""
        metrics = await self.get_comprehensive_metrics()
        
        if format == "json":
            return {
                "format": "json",
                "data": metrics,
                "exported_at": datetime.now().isoformat()
            }
        elif format == "csv":
            # Convertir en CSV (simplifié)
            csv_data = self._convert_to_csv(metrics)
            return {
                "format": "csv",
                "data": csv_data,
                "exported_at": datetime.now().isoformat()
            }
        else:
            return {"error": "Format non supporté"}

    def _convert_to_csv(self, metrics: Dict[str, Any]) -> str:
        """Convertit les métriques en format CSV."""
        import csv
        import io
        
        output = io.StringIO()
        writer = csv.writer(output)
        
        # En-têtes
        writer.writerow(["timestamp", "metric_type", "value", "node"])
        
        # Données des nœuds
        nodes_status = metrics.get("nodes_status", [])
        for node in nodes_status:
            writer.writerow([metrics["timestamp"], "node_cpu", node.get("cpu_usage", 0), node["node"]])
            writer.writerow([metrics["timestamp"], "node_memory", node.get("memory_usage", 0), node["node"]])
            writer.writerow([metrics["timestamp"], "node_disk", node.get("disk_usage", 0), node["node"]])
        
        return output.getvalue()