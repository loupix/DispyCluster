"""API endpoints pour le monitoring."""

from fastapi import APIRouter, HTTPException, BackgroundTasks
from typing import List, Dict, Any, Optional
from datetime import datetime, timedelta
import httpx
import asyncio
import json
import redis
from web.config.metrics_config import REDIS_CONFIG
from web.config.logging_config import get_logger

# Configuration du logger
logger = get_logger(__name__)

router = APIRouter(prefix="/api/monitoring", tags=["monitoring"])

# Client Redis pour le cache
redis_client = redis.Redis(**REDIS_CONFIG)

# Configuration
SERVICES = {
    "monitoring": "http://localhost:8082",
    "api_gateway": "http://localhost:8084"
}

@router.get("/health")
async def get_monitoring_health():
    """Santé du service de monitoring."""
    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            response = await client.get(f"{SERVICES['monitoring']}/health")
            if response.status_code == 200:
                return response.json()
            else:
                return {"status": "unhealthy", "error": f"HTTP {response.status_code}"}
    except Exception as e:
        return {"status": "unhealthy", "error": str(e)}

@router.get("/cluster/health")
async def get_cluster_health():
    """Santé globale du cluster."""
    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            response = await client.get(f"{SERVICES['monitoring']}/cluster/health")
            if response.status_code == 200:
                return response.json()
            else:
                return {
                    "overall_status": "unknown",
                    "nodes_online": 0,
                    "nodes_total": 0,
                    "issues": ["Service monitoring indisponible"]
                }
    except Exception as e:
        return {
            "overall_status": "error",
            "nodes_online": 0,
            "nodes_total": 0,
            "issues": [f"Erreur de connexion: {str(e)}"]
        }

@router.get("/nodes")
async def get_nodes_status():
    """Statut de tous les nœuds."""
    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            response = await client.get(f"{SERVICES['monitoring']}/nodes")
            if response.status_code == 200:
                return response.json()
            else:
                return {"error": f"Service monitoring indisponible (HTTP {response.status_code})", "nodes": []}
    except Exception as e:
        return {"error": str(e), "nodes": []}

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

@router.get("/metrics")
async def get_metrics():
    """Métriques du cluster."""
    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            response = await client.get(f"{SERVICES['monitoring']}/metrics")
            if response.status_code == 200:
                return response.json()
            else:
                return {"error": "Métriques indisponibles"}
    except Exception as e:
        return {"error": str(e)}

@router.get("/performance")
async def get_performance_report(hours: int = 24):
    """Rapport de performance du cluster."""
    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            response = await client.get(f"{SERVICES['monitoring']}/performance?hours={hours}")
            if response.status_code == 200:
                return response.json()
            else:
                return {"error": "Rapport de performance indisponible"}
    except Exception as e:
        return {"error": str(e)}

@router.get("/alerts")
async def get_alerts():
    """Alertes actives basées sur le cache Redis."""
    try:
        # Utiliser le cache Redis pour générer des alertes intelligentes
        cached_data = redis_client.get("cluster:metrics")
        if cached_data:
            cluster_metrics = json.loads(cached_data)
            
            alerts = []
            alert_count = 0
            
            # Vérifier les métriques du cluster
            cpu_avg = cluster_metrics.get("cpu_usage_avg", 0)
            memory_avg = cluster_metrics.get("memory_usage_avg", 0)
            online_nodes = cluster_metrics.get("online_nodes", 0)
            total_nodes = cluster_metrics.get("total_nodes", 0)
            
            # Alertes basées sur les métriques
            if cpu_avg > 90:
                alerts.append({
                    "id": "high_cpu",
                    "type": "warning",
                    "message": f"Utilisation CPU élevée: {cpu_avg:.1f}%",
                    "timestamp": datetime.now().isoformat()
                })
                alert_count += 1
            
            if memory_avg > 90:
                alerts.append({
                    "id": "high_memory",
                    "type": "warning", 
                    "message": f"Utilisation mémoire élevée: {memory_avg:.1f}%",
                    "timestamp": datetime.now().isoformat()
                })
                alert_count += 1
            
            if online_nodes < total_nodes:
                down_nodes = total_nodes - online_nodes
                alerts.append({
                    "id": "nodes_down",
                    "type": "critical" if down_nodes > total_nodes // 2 else "warning",
                    "message": f"{down_nodes} nœuds hors ligne ({online_nodes}/{total_nodes})",
                    "timestamp": datetime.now().isoformat()
                })
                alert_count += 1
            
            # Vérifier les nœuds individuels
            for node_data in cluster_metrics.get("nodes", []):
                node_name = node_data.get("node", "")
                cpu_usage = node_data.get("cpu_usage", 0)
                memory_usage = node_data.get("memory_usage", 0)
                temperature = node_data.get("temperature", 0)
                
                if cpu_usage > 95:
                    alerts.append({
                        "id": f"high_cpu_{node_name}",
                        "type": "warning",
                        "message": f"{node_name}: CPU très élevé ({cpu_usage:.1f}%)",
                        "timestamp": datetime.now().isoformat()
                    })
                    alert_count += 1
                
                if memory_usage > 95:
                    alerts.append({
                        "id": f"high_memory_{node_name}",
                        "type": "warning",
                        "message": f"{node_name}: Mémoire très élevée ({memory_usage:.1f}%)",
                        "timestamp": datetime.now().isoformat()
                    })
                    alert_count += 1
                
                if temperature > 80:
                    alerts.append({
                        "id": f"high_temp_{node_name}",
                        "type": "critical",
                        "message": f"{node_name}: Température élevée ({temperature:.1f}°C)",
                        "timestamp": datetime.now().isoformat()
                    })
                    alert_count += 1
            
            return {
                "active_alerts": alerts,
                "alert_count": alert_count,
                "timestamp": datetime.now().isoformat()
            }
            
    except Exception as e:
        return {"active_alerts": [], "alert_count": 0, "error": str(e)}

@router.post("/collect_metrics")
async def collect_metrics_now(background_tasks: BackgroundTasks):
    """Forcer la collecte immédiate des métriques."""
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.post(f"{SERVICES['monitoring']}/collect_metrics")
            if response.status_code == 200:
                return {"message": "Collecte des métriques lancée", "status": "success"}
            else:
                return {"message": "Erreur lors de la collecte", "status": "error"}
    except Exception as e:
        return {"message": f"Erreur: {str(e)}", "status": "error"}

@router.get("/dashboard")
async def get_dashboard_data():
    """Données pour le dashboard de monitoring."""
    try:
        # Récupérer toutes les données en parallèle
        tasks = [
            get_cluster_health(),
            get_nodes_status(),
            get_metrics(),
            get_alerts(),
            get_performance_report(24)
        ]
        
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        return {
            "timestamp": datetime.now().isoformat(),
            "cluster_health": results[0] if not isinstance(results[0], Exception) else {"error": str(results[0])},
            "nodes": results[1] if not isinstance(results[1], Exception) else {"error": str(results[1])},
            "metrics": results[2] if not isinstance(results[2], Exception) else {"error": str(results[2])},
            "alerts": results[3] if not isinstance(results[3], Exception) else {"error": str(results[3])},
            "performance": results[4] if not isinstance(results[4], Exception) else {"error": str(results[4])}
        }
        
    except Exception as e:
        return {
            "timestamp": datetime.now().isoformat(),
            "error": str(e),
            "cluster_health": {"error": "Données indisponibles"},
            "nodes": {"error": "Données indisponibles"},
            "metrics": {"error": "Données indisponibles"},
            "alerts": {"error": "Données indisponibles"},
            "performance": {"error": "Données indisponibles"}
        }

@router.get("/export")
async def export_metrics(format: str = "json", hours: int = 24):
    """Exporter les métriques."""
    try:
        # Récupérer les données
        dashboard_data = await get_dashboard_data()
        
        if format == "json":
            return {
                "format": "json",
                "data": dashboard_data,
                "exported_at": datetime.now().isoformat()
            }
        elif format == "csv":
            # Convertir en CSV (simplifié)
            csv_data = convert_to_csv(dashboard_data)
            return {
                "format": "csv",
                "data": csv_data,
                "exported_at": datetime.now().isoformat()
            }
        else:
            raise HTTPException(status_code=400, detail="Format non supporté")
            
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Erreur lors de l'export: {str(e)}")

def convert_to_csv(data: Dict[str, Any]) -> str:
    """Convertir les données en format CSV (simplifié)."""
    import csv
    import io
    
    output = io.StringIO()
    writer = csv.writer(output)
    
    # En-têtes
    writer.writerow(["timestamp", "metric_type", "value"])
    
    # Données des nœuds
    if "nodes" in data and isinstance(data["nodes"], list):
        for node in data["nodes"]:
            writer.writerow([data["timestamp"], f"node_{node.get('node', 'unknown')}_cpu", node.get("cpu_usage", 0)])
            writer.writerow([data["timestamp"], f"node_{node.get('node', 'unknown')}_memory", node.get("memory_usage", 0)])
            writer.writerow([data["timestamp"], f"node_{node.get('node', 'unknown')}_disk", node.get("disk_usage", 0)])
    
    return output.getvalue()

@router.get("/history")
async def get_metrics_history(hours: int = 24, metric_type: str = "all"):
    """Historique des métriques."""
    try:
        # Pour l'instant, retourner des données simulées
        # Dans une implémentation complète, on récupérerait l'historique depuis la base de données
        
        history = []
        now = datetime.now()
        
        for i in range(hours * 4):  # 4 points par heure (toutes les 15 minutes)
            timestamp = now - timedelta(minutes=i * 15)
            history.append({
                "timestamp": timestamp.isoformat(),
                "cpu_usage": 20 + (i % 20),  # Simulation
                "memory_usage": 30 + (i % 15),
                "disk_usage": 40 + (i % 10),
                "network_rx": 100 + (i % 50),
                "network_tx": 80 + (i % 30)
            })
        
        return {
            "metric_type": metric_type,
            "hours": hours,
            "data_points": len(history),
            "history": history
        }
        
    except Exception as e:
        return {"error": str(e), "history": []}