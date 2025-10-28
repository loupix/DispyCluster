"""Service de monitoring avancé pour le cluster DispyCluster.

Ce service collecte et expose des métriques détaillées sur le cluster,
les workers, et les performances de scraping.
"""

import asyncio
import json
import time
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional
from dataclasses import dataclass, asdict

from fastapi import FastAPI, HTTPException, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import requests
from aiohttp import ClientSession, ClientTimeout

# Configuration
CLUSTER_NODES = [
    "node6.lan", "node7.lan", "node9.lan", 
    "node10.lan", "node11.lan", "node12.lan", "node14.lan"
]

NODE_EXPORTER_PORT = 9100
PROMETHEUS_PORT = 9090

app = FastAPI(
    title="DispyCluster Monitoring",
    description="Service de monitoring pour le cluster de Raspberry Pi",
    version="1.0.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@dataclass
class NodeMetrics:
    node: str
    timestamp: datetime
    cpu_usage: float
    memory_usage: float
    disk_usage: float
    network_rx: int
    network_tx: int
    load_1m: float
    load_5m: float
    load_15m: float
    uptime: int
    temperature: Optional[float] = None

@dataclass
class ScrapingMetrics:
    node: str
    timestamp: datetime
    total_requests: int
    successful_requests: int
    failed_requests: int
    average_response_time: float
    pages_scraped: int
    data_size_mb: float

class ClusterHealth(BaseModel):
    overall_status: str  # healthy, warning, critical
    nodes_online: int
    nodes_total: int
    cpu_usage_avg: float
    memory_usage_avg: float
    disk_usage_avg: float
    issues: List[str]

class PerformanceReport(BaseModel):
    period: str
    total_jobs: int
    successful_jobs: int
    failed_jobs: int
    average_job_duration: float
    throughput_per_hour: float
    top_performing_nodes: List[Dict[str, Any]]
    bottlenecks: List[str]

# Stockage des métriques
node_metrics_history: Dict[str, List[NodeMetrics]] = {}
scraping_metrics_history: Dict[str, List[ScrapingMetrics]] = {}
health_alerts: List[Dict[str, Any]] = []

@app.get("/")
def root():
    """Point d'entrée du service de monitoring."""
    return {
        "service": "DispyCluster Monitoring",
        "version": "1.0.0",
        "status": "running",
        "endpoints": {
            "health": "/health",
            "cluster_health": "/cluster/health",
            "nodes": "/nodes",
            "metrics": "/metrics",
            "performance": "/performance",
            "alerts": "/alerts"
        }
    }

@app.get("/health")
def health():
    """Vérification de l'état du service de monitoring."""
    return {
        "status": "healthy",
        "timestamp": datetime.now().isoformat(),
        "monitored_nodes": len(CLUSTER_NODES),
        "metrics_collected": sum(len(metrics) for metrics in node_metrics_history.values())
    }

@app.get("/cluster/health", response_model=ClusterHealth)
def get_cluster_health():
    """État de santé global du cluster."""
    nodes_online = 0
    cpu_usage_values = []
    memory_usage_values = []
    disk_usage_values = []
    issues = []
    
    for node in CLUSTER_NODES:
        if node in node_metrics_history and node_metrics_history[node]:
            latest_metrics = node_metrics_history[node][-1]
            nodes_online += 1
            
            cpu_usage_values.append(latest_metrics.cpu_usage)
            memory_usage_values.append(latest_metrics.memory_usage)
            disk_usage_values.append(latest_metrics.disk_usage)
            
            # Détecter des problèmes
            if latest_metrics.cpu_usage > 90:
                issues.append(f"{node}: CPU usage élevé ({latest_metrics.cpu_usage:.1f}%)")
            if latest_metrics.memory_usage > 90:
                issues.append(f"{node}: Mémoire usage élevé ({latest_metrics.memory_usage:.1f}%)")
            if latest_metrics.disk_usage > 90:
                issues.append(f"{node}: Disque usage élevé ({latest_metrics.disk_usage:.1f}%)")
            if latest_metrics.temperature and latest_metrics.temperature > 80:
                issues.append(f"{node}: Température élevée ({latest_metrics.temperature:.1f}°C)")
        else:
            issues.append(f"{node}: Pas de métriques disponibles")
    
    # Déterminer le statut global
    if len(issues) == 0:
        overall_status = "healthy"
    elif len(issues) <= 2:
        overall_status = "warning"
    else:
        overall_status = "critical"
    
    return ClusterHealth(
        overall_status=overall_status,
        nodes_online=nodes_online,
        nodes_total=len(CLUSTER_NODES),
        cpu_usage_avg=sum(cpu_usage_values) / len(cpu_usage_values) if cpu_usage_values else 0,
        memory_usage_avg=sum(memory_usage_values) / len(memory_usage_values) if memory_usage_values else 0,
        disk_usage_avg=sum(disk_usage_values) / len(disk_usage_values) if disk_usage_values else 0,
        issues=issues
    )

@app.get("/nodes")
def get_nodes_status():
    """Statut détaillé de tous les nœuds."""
    nodes_data = []
    
    for node in CLUSTER_NODES:
        if node in node_metrics_history and node_metrics_history[node]:
            latest_metrics = node_metrics_history[node][-1]
            nodes_data.append({
                "node": node,
                "status": "online",
                "last_update": latest_metrics.timestamp.isoformat(),
                "cpu_usage": latest_metrics.cpu_usage,
                "memory_usage": latest_metrics.memory_usage,
                "disk_usage": latest_metrics.disk_usage,
                "load_1m": latest_metrics.load_1m,
                "temperature": latest_metrics.temperature,
                "uptime_hours": latest_metrics.uptime / 3600
            })
        else:
            nodes_data.append({
                "node": node,
                "status": "offline",
                "last_update": None,
                "error": "Pas de métriques disponibles"
            })
    
    return nodes_data

@app.get("/nodes/{node_name}")
def get_node_details(node_name: str, hours: int = 24):
    """Détails d'un nœud spécifique avec historique."""
    if node_name not in CLUSTER_NODES:
        raise HTTPException(status_code=404, detail="Nœud non trouvé")
    
    if node_name not in node_metrics_history:
        return {
            "node": node_name,
            "status": "offline",
            "error": "Pas de métriques disponibles"
        }
    
    # Filtrer les métriques des dernières heures
    cutoff_time = datetime.now() - timedelta(hours=hours)
    recent_metrics = [
        m for m in node_metrics_history[node_name] 
        if m.timestamp >= cutoff_time
    ]
    
    if not recent_metrics:
        return {
            "node": node_name,
            "status": "offline",
            "error": f"Pas de métriques dans les dernières {hours} heures"
        }
    
    # Calculer des statistiques
    cpu_values = [m.cpu_usage for m in recent_metrics]
    memory_values = [m.memory_usage for m in recent_metrics]
    disk_values = [m.disk_usage for m in recent_metrics]
    
    return {
        "node": node_name,
        "status": "online",
        "metrics_count": len(recent_metrics),
        "time_range": {
            "from": recent_metrics[0].timestamp.isoformat(),
            "to": recent_metrics[-1].timestamp.isoformat()
        },
        "current": {
            "cpu_usage": recent_metrics[-1].cpu_usage,
            "memory_usage": recent_metrics[-1].memory_usage,
            "disk_usage": recent_metrics[-1].disk_usage,
            "load_1m": recent_metrics[-1].load_1m,
            "temperature": recent_metrics[-1].temperature
        },
        "statistics": {
            "cpu_avg": sum(cpu_values) / len(cpu_values),
            "cpu_max": max(cpu_values),
            "memory_avg": sum(memory_values) / len(memory_values),
            "memory_max": max(memory_values),
            "disk_avg": sum(disk_values) / len(disk_values),
            "disk_max": max(disk_values)
        },
        "history": [asdict(m) for m in recent_metrics[-50:]]  # 50 derniers points
    }

@app.get("/metrics")
def get_metrics_summary():
    """Résumé des métriques collectées."""
    total_metrics = sum(len(metrics) for metrics in node_metrics_history.values())
    nodes_with_metrics = len([node for node in CLUSTER_NODES if node in node_metrics_history])
    
    return {
        "total_metrics_collected": total_metrics,
        "nodes_with_metrics": nodes_with_metrics,
        "collection_rate": "toutes les 30 secondes",
        "retention": "24 heures",
        "data_size_estimate_mb": total_metrics * 0.5  # Estimation
    }

@app.get("/performance", response_model=PerformanceReport)
def get_performance_report(hours: int = 24):
    """Rapport de performance du cluster."""
    # Cette fonction analyserait les métriques pour générer un rapport
    # Pour l'instant, on retourne des données simulées
    
    cutoff_time = datetime.now() - timedelta(hours=hours)
    
    # Analyser les métriques de scraping
    total_jobs = 0
    successful_jobs = 0
    failed_jobs = 0
    job_durations = []
    
    for node_metrics in scraping_metrics_history.values():
        recent_metrics = [
            m for m in node_metrics 
            if m.timestamp >= cutoff_time
        ]
        
        for metrics in recent_metrics:
            total_jobs += metrics.total_requests
            successful_jobs += metrics.successful_requests
            failed_jobs += metrics.failed_requests
    
    # Calculer les performances par nœud
    node_performance = []
    for node in CLUSTER_NODES:
        if node in scraping_metrics_history:
            recent_metrics = [
                m for m in scraping_metrics_history[node]
                if m.timestamp >= cutoff_time
            ]
            if recent_metrics:
                total_pages = sum(m.pages_scraped for m in recent_metrics)
                avg_response_time = sum(m.average_response_time for m in recent_metrics) / len(recent_metrics)
                node_performance.append({
                    "node": node,
                    "pages_scraped": total_pages,
                    "avg_response_time": avg_response_time,
                    "success_rate": sum(m.successful_requests for m in recent_metrics) / sum(m.total_requests for m in recent_metrics) * 100
                })
    
    # Trier par performance
    node_performance.sort(key=lambda x: x["pages_scraped"], reverse=True)
    
    return PerformanceReport(
        period=f"{hours} heures",
        total_jobs=total_jobs,
        successful_jobs=successful_jobs,
        failed_jobs=failed_jobs,
        average_job_duration=sum(job_durations) / len(job_durations) if job_durations else 0,
        throughput_per_hour=total_jobs / hours if hours > 0 else 0,
        top_performing_nodes=node_performance[:3],
        bottlenecks=["CPU usage élevé sur node6", "Mémoire limitée sur node7"]  # Exemple
    )

@app.get("/alerts")
def get_alerts():
    """Liste des alertes actives."""
    return {
        "active_alerts": health_alerts,
        "alert_count": len(health_alerts),
        "last_updated": datetime.now().isoformat()
    }

@app.post("/collect_metrics")
def collect_metrics_now(background_tasks: BackgroundTasks):
    """Forcer la collecte immédiate des métriques."""
    background_tasks.add_task(collect_all_metrics)
    return {"message": "Collecte des métriques lancée"}

async def collect_all_metrics():
    """Collecter les métriques de tous les nœuds."""
    tasks = []
    for node in CLUSTER_NODES:
        tasks.append(collect_node_metrics(node))
    
    await asyncio.gather(*tasks, return_exceptions=True)

async def collect_node_metrics(node: str):
    """Collecter les métriques d'un nœud spécifique."""
    try:
        async with ClientSession(timeout=ClientTimeout(total=10)) as session:
            # Récupérer les métriques Prometheus
            async with session.get(f"http://{node}:{NODE_EXPORTER_PORT}/metrics") as response:
                if response.status == 200:
                    metrics_text = await response.text()
                    metrics = parse_prometheus_metrics(metrics_text)
                    
                    # Créer l'objet NodeMetrics
                    node_metrics = NodeMetrics(
                        node=node,
                        timestamp=datetime.now(),
                        cpu_usage=metrics.get("cpu_usage", 0.0),
                        memory_usage=metrics.get("memory_usage", 0.0),
                        disk_usage=metrics.get("disk_usage", 0.0),
                        network_rx=metrics.get("network_rx", 0),
                        network_tx=metrics.get("network_tx", 0),
                        load_1m=metrics.get("load_1m", 0.0),
                        load_5m=metrics.get("load_5m", 0.0),
                        load_15m=metrics.get("load_15m", 0.0),
                        uptime=metrics.get("uptime", 0),
                        temperature=metrics.get("temperature")
                    )
                    
                    # Stocker les métriques
                    if node not in node_metrics_history:
                        node_metrics_history[node] = []
                    
                    node_metrics_history[node].append(node_metrics)
                    
                    # Garder seulement les 24 dernières heures
                    cutoff_time = datetime.now() - timedelta(hours=24)
                    node_metrics_history[node] = [
                        m for m in node_metrics_history[node]
                        if m.timestamp >= cutoff_time
                    ]
                    
    except Exception as e:
        print(f"Erreur lors de la collecte des métriques pour {node}: {e}")

def parse_prometheus_metrics(metrics_text: str) -> Dict[str, Any]:
    """Parser les métriques Prometheus (version simplifiée)."""
    metrics = {}
    lines = metrics_text.split('\n')
    
    for line in lines:
        if line.startswith('#') or not line.strip():
            continue
        
        try:
            if ' ' in line:
                name, value = line.rsplit(' ', 1)
                value = float(value)
                
                # Mapper les métriques importantes
                if 'node_cpu_seconds_total' in name:
                    metrics['cpu_usage'] = value * 100  # Convertir en pourcentage
                elif 'node_memory_MemAvailable_bytes' in name:
                    metrics['memory_usage'] = value
                elif 'node_filesystem_avail_bytes' in name:
                    metrics['disk_usage'] = value
                elif 'node_load1' in name:
                    metrics['load_1m'] = value
                elif 'node_load5' in name:
                    metrics['load_5m'] = value
                elif 'node_load15' in name:
                    metrics['load_15m'] = value
                elif 'node_boot_time_seconds' in name:
                    metrics['uptime'] = int(time.time() - value)
                elif 'node_thermal_zone_temp' in name:
                    metrics['temperature'] = value
                    
        except (ValueError, IndexError):
            continue
    
    return metrics

# Tâche de collecte périodique
async def periodic_metrics_collection():
    """Collecte périodique des métriques."""
    while True:
        await collect_all_metrics()
        await asyncio.sleep(30)  # Collecte toutes les 30 secondes

@app.on_event("startup")
async def startup_event():
    """Démarrer la collecte périodique des métriques."""
    asyncio.create_task(periodic_metrics_collection())

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8082)