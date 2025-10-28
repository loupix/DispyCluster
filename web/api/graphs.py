"""API endpoints pour les graphiques et données historiques."""

from fastapi import APIRouter, HTTPException, Query
from typing import List, Dict, Any, Optional
from datetime import datetime, timedelta
from web.core.metrics_history import history_manager
from web.config.logging_config import get_logger

logger = get_logger(__name__)

router = APIRouter(prefix="/api/graphs", tags=["graphs"])

@router.get("/cpu-history")
async def get_cpu_history(
    hours: int = Query(24, description="Nombre d'heures d'historique"),
    node: Optional[str] = Query(None, description="Nœud spécifique (optionnel)"),
    interval_minutes: int = Query(5, description="Intervalle d'agrégation en minutes")
):
    """Historique de l'utilisation CPU pour les graphiques."""
    try:
        if node:
            # Historique d'un nœud spécifique
            history = history_manager.get_node_history(node, hours)
            cpu_data = []
            for point in history:
                cpu_data.append({
                    "timestamp": point["timestamp"],
                    "node": point["node"],
                    "cpu_usage": point["metrics"].get("cpu_usage", 0)
                })
        else:
            # Historique agrégé du cluster
            history = history_manager.get_aggregated_history(hours, interval_minutes)
            cpu_data = []
            for point in history:
                cpu_data.append({
                    "timestamp": point["timestamp"],
                    "avg_cpu": point["cluster_stats"]["avg_cpu"],
                    "online_nodes": point["cluster_stats"]["online_nodes"]
                })
        
        return {
            "metric_type": "cpu",
            "hours": hours,
            "interval_minutes": interval_minutes,
            "data_points": len(cpu_data),
            "data": cpu_data
        }
        
    except Exception as e:
        logger.error(f"Erreur récupération historique CPU: {e}")
        raise HTTPException(status_code=500, detail=f"Erreur: {str(e)}")

@router.get("/memory-history")
async def get_memory_history(
    hours: int = Query(24, description="Nombre d'heures d'historique"),
    node: Optional[str] = Query(None, description="Nœud spécifique (optionnel)"),
    interval_minutes: int = Query(5, description="Intervalle d'agrégation en minutes")
):
    """Historique de l'utilisation mémoire pour les graphiques."""
    try:
        if node:
            # Historique d'un nœud spécifique
            history = history_manager.get_node_history(node, hours)
            memory_data = []
            for point in history:
                memory_data.append({
                    "timestamp": point["timestamp"],
                    "node": point["node"],
                    "memory_usage": point["metrics"].get("memory_usage", 0)
                })
        else:
            # Historique agrégé du cluster
            history = history_manager.get_aggregated_history(hours, interval_minutes)
            memory_data = []
            for point in history:
                memory_data.append({
                    "timestamp": point["timestamp"],
                    "avg_memory": point["cluster_stats"]["avg_memory"],
                    "online_nodes": point["cluster_stats"]["online_nodes"]
                })
        
        return {
            "metric_type": "memory",
            "hours": hours,
            "interval_minutes": interval_minutes,
            "data_points": len(memory_data),
            "data": memory_data
        }
        
    except Exception as e:
        logger.error(f"Erreur récupération historique mémoire: {e}")
        raise HTTPException(status_code=500, detail=f"Erreur: {str(e)}")

@router.get("/disk-history")
async def get_disk_history(
    hours: int = Query(24, description="Nombre d'heures d'historique"),
    node: Optional[str] = Query(None, description="Nœud spécifique (optionnel)"),
    interval_minutes: int = Query(5, description="Intervalle d'agrégation en minutes")
):
    """Historique de l'utilisation disque pour les graphiques."""
    try:
        if node:
            # Historique d'un nœud spécifique
            history = history_manager.get_node_history(node, hours)
            disk_data = []
            for point in history:
                disk_data.append({
                    "timestamp": point["timestamp"],
                    "node": point["node"],
                    "disk_usage": point["metrics"].get("disk_usage", 0)
                })
        else:
            # Historique agrégé du cluster
            history = history_manager.get_aggregated_history(hours, interval_minutes)
            disk_data = []
            for point in history:
                disk_data.append({
                    "timestamp": point["timestamp"],
                    "avg_disk": point["cluster_stats"]["avg_disk"],
                    "online_nodes": point["cluster_stats"]["online_nodes"]
                })
        
        return {
            "metric_type": "disk",
            "hours": hours,
            "interval_minutes": interval_minutes,
            "data_points": len(disk_data),
            "data": disk_data
        }
        
    except Exception as e:
        logger.error(f"Erreur récupération historique disque: {e}")
        raise HTTPException(status_code=500, detail=f"Erreur: {str(e)}")

@router.get("/temperature-history")
async def get_temperature_history(
    hours: int = Query(24, description="Nombre d'heures d'historique"),
    node: Optional[str] = Query(None, description="Nœud spécifique (optionnel)"),
    interval_minutes: int = Query(5, description="Intervalle d'agrégation en minutes")
):
    """Historique de la température pour les graphiques."""
    try:
        if node:
            # Historique d'un nœud spécifique
            history = history_manager.get_node_history(node, hours)
            temp_data = []
            for point in history:
                temp_data.append({
                    "timestamp": point["timestamp"],
                    "node": point["node"],
                    "temperature": point["metrics"].get("temperature", 0)
                })
        else:
            # Historique agrégé du cluster
            history = history_manager.get_aggregated_history(hours, interval_minutes)
            temp_data = []
            for point in history:
                temp_data.append({
                    "timestamp": point["timestamp"],
                    "avg_temperature": point["cluster_stats"]["avg_temperature"],
                    "online_nodes": point["cluster_stats"]["online_nodes"]
                })
        
        return {
            "metric_type": "temperature",
            "hours": hours,
            "interval_minutes": interval_minutes,
            "data_points": len(temp_data),
            "data": temp_data
        }
        
    except Exception as e:
        logger.error(f"Erreur récupération historique température: {e}")
        raise HTTPException(status_code=500, detail=f"Erreur: {str(e)}")

@router.get("/combined-history")
async def get_combined_history(
    hours: int = Query(24, description="Nombre d'heures d'historique"),
    node: Optional[str] = Query(None, description="Nœud spécifique (optionnel)"),
    interval_minutes: int = Query(5, description="Intervalle d'agrégation en minutes")
):
    """Historique combiné de toutes les métriques pour les graphiques."""
    try:
        if node:
            # Historique d'un nœud spécifique
            history = history_manager.get_node_history(node, hours)
            combined_data = []
            for point in history:
                combined_data.append({
                    "timestamp": point["timestamp"],
                    "node": point["node"],
                    "cpu_usage": point["metrics"].get("cpu_usage", 0),
                    "memory_usage": point["metrics"].get("memory_usage", 0),
                    "disk_usage": point["metrics"].get("disk_usage", 0),
                    "temperature": point["metrics"].get("temperature", 0)
                })
        else:
            # Historique agrégé du cluster
            history = history_manager.get_aggregated_history(hours, interval_minutes)
            combined_data = []
            for point in history:
                combined_data.append({
                    "timestamp": point["timestamp"],
                    "avg_cpu": point["cluster_stats"]["avg_cpu"],
                    "avg_memory": point["cluster_stats"]["avg_memory"],
                    "avg_disk": point["cluster_stats"]["avg_disk"],
                    "avg_temperature": point["cluster_stats"]["avg_temperature"],
                    "online_nodes": point["cluster_stats"]["online_nodes"]
                })
        
        return {
            "metric_type": "combined",
            "hours": hours,
            "interval_minutes": interval_minutes,
            "data_points": len(combined_data),
            "data": combined_data
        }
        
    except Exception as e:
        logger.error(f"Erreur récupération historique combiné: {e}")
        raise HTTPException(status_code=500, detail=f"Erreur: {str(e)}")

@router.get("/nodes-list")
async def get_nodes_list():
    """Liste des nœuds disponibles pour les graphiques."""
    try:
        # Récupérer la liste des nœuds depuis les clés Redis
        import redis
        from web.config.metrics_config import REDIS_CONFIG
        
        redis_client = redis.Redis(**REDIS_CONFIG)
        pattern = "history:*"
        history_keys = redis_client.keys(pattern)
        
        nodes = []
        for key in history_keys:
            node = key.decode().replace("history:", "")
            nodes.append({
                "name": node,
                "has_history": True
            })
        
        return {
            "nodes": nodes,
            "total_nodes": len(nodes)
        }
        
    except Exception as e:
        logger.error(f"Erreur récupération liste nœuds: {e}")
        return {"nodes": [], "total_nodes": 0, "error": str(e)}

@router.get("/realtime-data")
async def get_realtime_data():
    """Données en temps réel pour les graphiques (dernières valeurs)."""
    try:
        import redis
        import json
        from web.config.metrics_config import REDIS_CONFIG, NODES
        
        redis_client = redis.Redis(**REDIS_CONFIG)
        
        realtime_data = {
            "timestamp": datetime.utcnow().isoformat(),
            "nodes": {}
        }
        
        for node in NODES:
            node_data = redis_client.get(f"metrics:{node}")
            if node_data:
                metrics = json.loads(node_data)
                realtime_data["nodes"][node] = {
                    "cpu_usage": metrics.get("cpu_usage", 0),
                    "memory_usage": metrics.get("memory_usage", 0),
                    "disk_usage": metrics.get("disk_usage", 0),
                    "temperature": metrics.get("temperature", 0)
                }
        
        return realtime_data
        
    except Exception as e:
        logger.error(f"Erreur récupération données temps réel: {e}")
        raise HTTPException(status_code=500, detail=f"Erreur: {str(e)}")
