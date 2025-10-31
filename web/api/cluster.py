"""API endpoints pour la gestion du cluster."""

from fastapi import APIRouter, HTTPException, Depends
from typing import List, Dict, Any, Optional
import httpx
import asyncio
import json
import redis
from datetime import datetime
from web.config.metrics_config import REDIS_CONFIG
from web.config.logging_config import get_logger

# Configuration du logger
logger = get_logger(__name__)

router = APIRouter(prefix="/api/cluster", tags=["cluster"])

# Client Redis pour le cache
redis_client = redis.Redis(**REDIS_CONFIG)

# Configuration des services
SERVICES = {
    "cluster_controller": "http://localhost:8081",
    "monitoring": "http://localhost:8082", 
    "scheduler": "http://localhost:8083"
}

@router.get("/overview")
async def get_cluster_overview():
    """Vue d'ensemble du cluster avec cache Redis."""
    try:
        from web.views.cluster_view import ClusterView
        
        cluster_view = ClusterView()
        overview = await cluster_view.get_cluster_overview()
        
        return overview
            
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Erreur lors de la récupération des données: {str(e)}")

@router.get("/nodes")
async def get_cluster_nodes():
    """Liste des nœuds du cluster avec cache Redis."""
    try:
        from web.views.cluster_view import ClusterView
        from web.app import websocket_manager
        from datetime import datetime
        
        cluster_view = ClusterView()
        nodes_data = await cluster_view.get_nodes_status()
        
        # Publier les données sur Redis pour les clients WebSocket
        try:
            await websocket_manager.publish_event("cluster:metrics", {
                "nodes": nodes_data,
                "timestamp": datetime.now().isoformat()
            })
        except Exception as e:
            logger.warning(f"Impossible de publier sur Redis: {e}")
        
        return nodes_data
    except Exception as e:
        return []

@router.get("/nodes/{node_name}")
async def get_node_details(node_name: str, hours: int = 24):
    """Détails d'un nœud spécifique."""
    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            response = await client.get(f"{SERVICES['monitoring']}/nodes/{node_name}?hours={hours}")
            if response.status_code == 200:
                return response.json()
            else:
                raise HTTPException(status_code=response.status_code, detail="Nœud non trouvé")
    except httpx.RequestError as e:
        raise HTTPException(status_code=503, detail=f"Service monitoring indisponible: {str(e)}")

@router.get("/health")
async def get_cluster_health():
    """Santé globale du cluster avec métriques cachées."""
    try:
        # Essayer d'abord le cache Redis
        cached_data = redis_client.get("cluster:metrics")
        if cached_data:
            cluster_metrics = json.loads(cached_data)
            
            online_nodes = cluster_metrics.get("online_nodes", 0)
            total_nodes = cluster_metrics.get("total_nodes", 0)
            down_nodes = total_nodes - online_nodes
            
            # Déterminer le statut global
            if down_nodes == 0 and total_nodes > 0:
                overall_status = "healthy"
            elif down_nodes <= total_nodes // 2:
                overall_status = "warning"
            else:
                overall_status = "critical"
            
            return {
                "overall_status": overall_status,
                "nodes_online": online_nodes,
                "nodes_total": total_nodes,
                "issues": [] if overall_status == "healthy" else [f"{down_nodes} nœuds hors ligne"]
            }
        
        # Fallback vers la méthode classique
        from web.views.cluster_view import ClusterView
        
        cluster_view = ClusterView()
        overview = await cluster_view.get_cluster_overview()
        
        cluster_stats = overview.get("cluster_stats", {})
        total_nodes = cluster_stats.get("total_nodes", 0)
        ready_nodes = cluster_stats.get("ready_nodes", 0)
        down_nodes = cluster_stats.get("down_nodes", 0)
        
        # Déterminer le statut global
        if down_nodes == 0 and total_nodes > 0:
            overall_status = "healthy"
        elif down_nodes <= total_nodes // 2:
            overall_status = "warning"
        else:
            overall_status = "critical"
        
        return {
            "overall_status": overall_status,
            "nodes_online": ready_nodes,
            "nodes_total": total_nodes,
            "issues": [] if overall_status == "healthy" else [f"{down_nodes} nœuds hors ligne"]
        }
    except Exception as e:
        return {
            "overall_status": "error",
            "nodes_online": 0,
            "nodes_total": 0,
            "issues": [f"Erreur de connexion: {str(e)}"]
        }

@router.post("/nodes/{node_name}/restart")
async def restart_node(node_name: str):
    """Redémarrer un nœud spécifique."""
    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(f"{SERVICES['cluster_controller']}/nodes/{node_name}/restart")
            if response.status_code == 200:
                return {"message": f"Nœud {node_name} redémarré avec succès"}
            else:
                raise HTTPException(status_code=response.status_code, detail="Erreur lors du redémarrage")
    except httpx.RequestError as e:
        raise HTTPException(status_code=503, detail=f"Service indisponible: {str(e)}")

@router.get("/metrics")
async def get_cluster_metrics():
    """Métriques du cluster avec cache Redis."""
    try:
        # Essayer d'abord le cache Redis
        cached_data = redis_client.get("cluster:metrics")
        if cached_data:
            cluster_metrics = json.loads(cached_data)
            
            return {
                "cluster_stats": {
                    "total_nodes": cluster_metrics.get("total_nodes", 0),
                    "online_nodes": cluster_metrics.get("online_nodes", 0),
                    "cpu_usage_avg": cluster_metrics.get("cpu_usage_avg", 0.0),
                    "memory_usage_avg": cluster_metrics.get("memory_usage_avg", 0.0),
                    "disk_usage_avg": cluster_metrics.get("disk_usage_avg", 0.0)
                },
                "worker_stats": {},
                "timestamp": cluster_metrics.get("timestamp", datetime.now().isoformat())
            }
        
        # Fallback vers la méthode classique
        from web.views.cluster_view import ClusterView
        
        cluster_view = ClusterView()
        overview = await cluster_view.get_cluster_overview()
        
        cluster_stats = overview.get("cluster_stats", {})
        worker_stats = overview.get("worker_stats", {})
        
        return {
            "cluster_stats": cluster_stats,
            "worker_stats": worker_stats,
            "timestamp": datetime.now().isoformat()
        }
    except Exception as e:
        return {"error": str(e)}

async def check_service_health(service_name: str, service_url: str) -> Dict[str, Any]:
    """Vérifier la santé d'un service."""
    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            start_time = datetime.now()
            response = await client.get(f"{service_url}/health")
            response_time = (datetime.now() - start_time).total_seconds()
            
            return {
                "name": service_name,
                "url": service_url,
                "status": "online" if response.status_code == 200 else "offline",
                "response_time": response_time,
                "http_status": response.status_code
            }
    except Exception as e:
        return {
            "name": service_name,
            "url": service_url,
            "status": "offline",
            "error": str(e)
        }

async def get_cluster_stats() -> Dict[str, Any]:
    """Récupérer les statistiques du cluster."""
    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            response = await client.get(f"{SERVICES['cluster_controller']}/cluster")
            if response.status_code == 200:
                return response.json()
    except Exception:
        pass
    
    return {"error": "Statistiques indisponibles"}

async def get_recent_activity() -> List[Dict[str, Any]]:
    """Récupérer l'activité récente."""
    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            response = await client.get(f"{SERVICES['scheduler']}/history?limit=5")
            if response.status_code == 200:
                return response.json()
    except Exception:
        pass
    
    return []

async def get_alerts() -> Dict[str, Any]:
    """Récupérer les alertes."""
    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            response = await client.get(f"{SERVICES['monitoring']}/alerts")
            if response.status_code == 200:
                return response.json()
    except Exception:
        pass
    
    return {"active_alerts": []}


@router.get("/infra/health")
async def get_infra_health():
    """Etat infra avec métriques cachées."""
    try:
        # Essayer d'abord le cache Redis
        cached_data = redis_client.get("cluster:metrics")
        if cached_data:
            cluster_metrics = json.loads(cached_data)
            
            # Construire l'état détaillé des nœuds depuis le cache
            nodes_detail = []
            for node_data in cluster_metrics.get("nodes", []):
                nodes_detail.append({
                    "node": node_data.get("node", ""),
                    "status": "ready" if node_data.get("cpu_usage", 0) > 0 else "unknown",
                    "cpu_usage": node_data.get("cpu_usage", 0.0),
                    "memory_usage": node_data.get("memory_usage", 0.0),
                    "disk_usage": node_data.get("disk_usage", 0.0),
                    "last_update": node_data.get("timestamp"),
                    "healthy": node_data.get("cpu_usage", 0) > 0
                })
            
            return {
                "timestamp": cluster_metrics.get("timestamp", datetime.now().isoformat()),
                "master": "localhost",
                "infra": {"dispy": "online", "scheduler": "online"},
                "nodes": nodes_detail
            }
        
        # Fallback vers la méthode classique
        from web.views.cluster_view import ClusterView

        cluster_view = ClusterView()
        manager = cluster_view.cluster_manager

        # Vérifier les nœuds et mettre à jour les métriques internes
        nodes_health = await manager.check_all_nodes()

        # Vérifier l'infrastructure master
        infra = await manager.check_infrastructure()

        # Construire l'état détaillé des nœuds
        nodes_detail = []
        for node in manager.nodes:
            metrics = manager.node_metrics.get(node, {})
            nodes_detail.append({
                "node": node,
                "status": manager.node_status.get(node, "unknown"),
                "cpu_usage": metrics.get("cpu_usage", 0.0),
                "memory_usage": metrics.get("memory_usage", 0.0),
                "disk_usage": metrics.get("disk_usage", 0.0),
                "last_update": manager.last_update.get(node).isoformat() if manager.last_update.get(node) else None,
                "healthy": bool(nodes_health.get(node, False))
            })

        return {
            "timestamp": datetime.now().isoformat(),
            "master": manager.master,
            "infra": infra,
            "nodes": nodes_detail
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Erreur health infra: {str(e)}")