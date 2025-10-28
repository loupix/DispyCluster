"""API optimisée pour les métriques avec cache Redis."""

from fastapi import APIRouter, HTTPException
from typing import Dict, List, Any, Optional
from datetime import datetime, timedelta
import json
import redis
from web.tasks.monitoring import get_cached_metrics
from web.config.metrics_config import NODES, REDIS_CONFIG

router = APIRouter(prefix="/api/metrics", tags=["metrics-cache"])

# Client Redis configuré
redis_client = redis.Redis(**REDIS_CONFIG)

@router.get("/cluster")
async def get_cluster_metrics():
    """Métriques du cluster depuis le cache Redis."""
    try:
        # Utiliser la tâche Celery pour récupérer les métriques
        result = get_cached_metrics.delay()
        metrics = result.get(timeout=5)
        
        if "error" in metrics:
            raise HTTPException(status_code=500, detail=metrics["error"])
        
        return {
            "status": "success",
            "timestamp": datetime.utcnow().isoformat(),
            "data": metrics
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Erreur récupération métriques: {str(e)}")

@router.get("/nodes")
async def get_nodes_metrics():
    """Métriques des nœuds depuis le cache."""
    try:
        # Récupérer directement depuis Redis en utilisant la liste des nœuds
        all_metrics = []
        for node in NODES:
            cache_key = f"metrics:{node}"
            cached_data = redis_client.get(cache_key)
            if cached_data:
                all_metrics.append(json.loads(cached_data))
        
        return {
            "status": "success",
            "timestamp": datetime.utcnow().isoformat(),
            "nodes": all_metrics,
            "total_nodes": len(all_metrics)
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Erreur récupération nœuds: {str(e)}")

@router.get("/node/{node_name}")
async def get_node_metrics(node_name: str):
    """Métriques d'un nœud spécifique depuis le cache."""
    try:
        cache_key = f"metrics:{node_name}"
        cached_data = redis_client.get(cache_key)
        
        if not cached_data:
            raise HTTPException(status_code=404, detail=f"Nœud {node_name} non trouvé dans le cache")
        
        metrics = json.loads(cached_data)
        
        return {
            "status": "success",
            "timestamp": datetime.utcnow().isoformat(),
            "node": metrics
        }
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Erreur récupération nœud: {str(e)}")

@router.get("/overview")
async def get_metrics_overview():
    """Vue d'ensemble des métriques avec cache."""
    try:
        # Récupérer les métriques agrégées
        aggregated_data = redis_client.get("cluster:metrics")
        
        if aggregated_data:
            return json.loads(aggregated_data)
        
        # Fallback: calculer à la volée en utilisant la liste des nœuds
        all_metrics = []
        for node in NODES:
            cache_key = f"metrics:{node}"
            cached_data = redis_client.get(cache_key)
            if cached_data:
                all_metrics.append(json.loads(cached_data))
        
        if not all_metrics:
            return {
                "timestamp": datetime.utcnow().isoformat(),
                "total_nodes": len(NODES),
                "online_nodes": 0,
                "cpu_usage_avg": 0.0,
                "memory_usage_avg": 0.0,
                "disk_usage_avg": 0.0,
                "nodes": []
            }
        
        # Calculer les moyennes
        cpu_values = [m.get('cpu_usage', 0) for m in all_metrics if m.get('cpu_usage') is not None]
        memory_values = [m.get('memory_usage', 0) for m in all_metrics if m.get('memory_usage') is not None]
        disk_values = [m.get('disk_usage', 0) for m in all_metrics if m.get('disk_usage') is not None]
        
        return {
            "timestamp": datetime.utcnow().isoformat(),
            "total_nodes": len(NODES),
            "online_nodes": len(all_metrics),
            "cpu_usage_avg": sum(cpu_values) / len(cpu_values) if cpu_values else 0.0,
            "memory_usage_avg": sum(memory_values) / len(memory_values) if memory_values else 0.0,
            "disk_usage_avg": sum(disk_values) / len(disk_values) if disk_values else 0.0,
            "nodes": all_metrics
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Erreur vue d'ensemble: {str(e)}")

@router.get("/health")
async def get_cache_health():
    """Santé du cache Redis."""
    try:
        # Test de connexion Redis
        redis_client.ping()
        
        # Vérifier les clés de cache
        cache_keys = redis_client.keys("metrics:*")
        cluster_key = redis_client.get("cluster:metrics")
        
        return {
            "status": "healthy",
            "timestamp": datetime.utcnow().isoformat(),
            "redis_connected": True,
            "cached_nodes": len(cache_keys),
            "aggregated_metrics_available": cluster_key is not None,
            "cache_keys": cache_keys[:10]  # Limiter l'affichage
        }
        
    except Exception as e:
        return {
            "status": "unhealthy",
            "timestamp": datetime.utcnow().isoformat(),
            "redis_connected": False,
            "error": str(e)
        }

@router.post("/refresh")
async def refresh_metrics_cache():
    """Force le rafraîchissement du cache des métriques."""
    try:
        from web.tasks.monitoring import collect_metrics
        
        # Lancer la tâche de collecte
        task = collect_metrics.delay()
        result = task.get(timeout=30)
        
        return {
            "status": "success",
            "timestamp": datetime.utcnow().isoformat(),
            "message": "Cache rafraîchi",
            "task_result": result
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Erreur rafraîchissement: {str(e)}")

@router.get("/stats")
async def get_cache_stats():
    """Statistiques du cache."""
    try:
        # Informations Redis
        info = redis_client.info()
        
        # Clés de cache
        cache_keys = redis_client.keys("metrics:*")
        cluster_key = redis_client.get("cluster:metrics")
        
        # TTL des clés
        ttl_info = {}
        for key in cache_keys[:5]:  # Limiter aux 5 premières
            ttl = redis_client.ttl(key)
            ttl_info[key] = ttl
        
        return {
            "timestamp": datetime.utcnow().isoformat(),
            "redis_info": {
                "used_memory": info.get("used_memory_human", "N/A"),
                "connected_clients": info.get("connected_clients", 0),
                "total_commands_processed": info.get("total_commands_processed", 0)
            },
            "cache_stats": {
                "total_cached_nodes": len(cache_keys),
                "aggregated_metrics_available": cluster_key is not None,
                "sample_ttl": ttl_info
            }
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Erreur statistiques: {str(e)}")
