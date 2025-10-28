"""API Gateway pour le cluster DispyCluster.

Ce service centralise l'accès à tous les services du cluster et fournit
une interface unifiée pour la gestion et le monitoring.
"""

import asyncio
import json
from datetime import datetime
from typing import Any, Dict, List, Optional

from fastapi import FastAPI, HTTPException, Request, Depends
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel, HttpUrl
import httpx
from aiohttp import ClientSession, ClientTimeout

# Configuration des services
SERVICES = {
    "cluster_controller": "http://localhost:8081",
    "monitoring": "http://localhost:8082", 
    "scheduler": "http://localhost:8083",
    "scraper": "http://localhost:8080"  # Service de scraping existant
}

app = FastAPI(
    title="DispyCluster API Gateway",
    description="Point d'entrée unifié pour le cluster de Raspberry Pi",
    version="1.0.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

class ClusterOverview(BaseModel):
    status: str
    services: Dict[str, str]
    cluster_stats: Dict[str, Any]
    recent_activity: List[Dict[str, Any]]
    alerts: List[str]

class ServiceStatus(BaseModel):
    name: str
    url: str
    status: str
    response_time: Optional[float]
    last_check: datetime
    error: Optional[str] = None

# Cache pour les statuts des services
service_status_cache: Dict[str, ServiceStatus] = {}

@app.get("/")
def root():
    """Point d'entrée principal de l'API Gateway."""
    return {
        "service": "DispyCluster API Gateway",
        "version": "1.0.0",
        "status": "running",
        "services": list(SERVICES.keys()),
        "endpoints": {
            "overview": "/overview",
            "services": "/services",
            "cluster": "/cluster",
            "monitoring": "/monitoring",
            "scheduler": "/scheduler",
            "scraper": "/scraper"
        }
    }

@app.get("/health")
async def health():
    """Vérification de l'état de tous les services."""
    services_health = {}
    
    for service_name, service_url in SERVICES.items():
        try:
            async with httpx.AsyncClient(timeout=5.0) as client:
                start_time = datetime.now()
                response = await client.get(f"{service_url}/health")
                response_time = (datetime.now() - start_time).total_seconds()
                
                services_health[service_name] = {
                    "status": "healthy",
                    "response_time": response_time,
                    "http_status": response.status_code
                }
        except Exception as e:
            services_health[service_name] = {
                "status": "unhealthy",
                "error": str(e)
            }
    
    overall_status = "healthy" if all(
        s["status"] == "healthy" for s in services_health.values()
    ) else "degraded"
    
    return {
        "overall_status": overall_status,
        "timestamp": datetime.now().isoformat(),
        "services": services_health
    }

@app.get("/overview", response_model=ClusterOverview)
async def get_cluster_overview():
    """Vue d'ensemble du cluster."""
    # Vérifier le statut des services
    services_status = {}
    for service_name, service_url in SERVICES.items():
        try:
            async with httpx.AsyncClient(timeout=5.0) as client:
                response = await client.get(f"{service_url}/health")
                services_status[service_name] = "online" if response.status_code == 200 else "offline"
        except:
            services_status[service_name] = "offline"
    
    # Récupérer les statistiques du cluster
    cluster_stats = {}
    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            response = await client.get(f"{SERVICES['cluster_controller']}/cluster")
            if response.status_code == 200:
                cluster_stats = response.json()
    except:
        cluster_stats = {"error": "Impossible de récupérer les statistiques"}
    
    # Récupérer l'activité récente
    recent_activity = []
    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            response = await client.get(f"{SERVICES['scheduler']}/history?limit=5")
            if response.status_code == 200:
                recent_activity = response.json()
    except:
        pass
    
    # Détecter les alertes
    alerts = []
    for service_name, status in services_status.items():
        if status == "offline":
            alerts.append(f"Service {service_name} hors ligne")
    
    # Vérifier les alertes de monitoring
    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            response = await client.get(f"{SERVICES['monitoring']}/alerts")
            if response.status_code == 200:
                monitoring_alerts = response.json()
                if monitoring_alerts.get("active_alerts"):
                    alerts.extend(monitoring_alerts["active_alerts"])
    except:
        pass
    
    return ClusterOverview(
        status="healthy" if not alerts else "warning",
        services=services_status,
        cluster_stats=cluster_stats,
        recent_activity=recent_activity,
        alerts=alerts
    )

@app.get("/services")
async def get_services_status():
    """Statut détaillé de tous les services."""
    services_status = []
    
    for service_name, service_url in SERVICES.items():
        try:
            async with httpx.AsyncClient(timeout=5.0) as client:
                start_time = datetime.now()
                response = await client.get(f"{service_url}/health")
                response_time = (datetime.now() - start_time).total_seconds()
                
                services_status.append(ServiceStatus(
                    name=service_name,
                    url=service_url,
                    status="online",
                    response_time=response_time,
                    last_check=datetime.now()
                ))
        except Exception as e:
            services_status.append(ServiceStatus(
                name=service_name,
                url=service_url,
                status="offline",
                response_time=None,
                last_check=datetime.now(),
                error=str(e)
            ))
    
    return services_status

# Proxy endpoints pour chaque service
@app.api_route("/cluster/{path:path}", methods=["GET", "POST", "PUT", "DELETE"])
async def proxy_cluster_controller(request: Request, path: str):
    """Proxy vers le service de contrôle du cluster."""
    return await proxy_request(request, SERVICES["cluster_controller"], path)

@app.api_route("/monitoring/{path:path}", methods=["GET", "POST", "PUT", "DELETE"])
async def proxy_monitoring(request: Request, path: str):
    """Proxy vers le service de monitoring."""
    return await proxy_request(request, SERVICES["monitoring"], path)

@app.api_route("/scheduler/{path:path}", methods=["GET", "POST", "PUT", "DELETE"])
async def proxy_scheduler(request: Request, path: str):
    """Proxy vers le service de planification."""
    return await proxy_request(request, SERVICES["scheduler"], path)

@app.api_route("/scraper/{path:path}", methods=["GET", "POST", "PUT", "DELETE"])
async def proxy_scraper(request: Request, path: str):
    """Proxy vers le service de scraping."""
    return await proxy_request(request, SERVICES["scraper"], path)

async def proxy_request(request: Request, service_url: str, path: str):
    """Proxifier une requête vers un service."""
    try:
        # Construire l'URL complète
        target_url = f"{service_url}/{path}"
        if request.query_params:
            target_url += f"?{request.query_params}"
        
        # Préparer les headers
        headers = dict(request.headers)
        headers.pop("host", None)  # Retirer le header host
        
        # Préparer le body si nécessaire
        body = None
        if request.method in ["POST", "PUT", "PATCH"]:
            body = await request.body()
        
        # Faire la requête
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.request(
                method=request.method,
                url=target_url,
                headers=headers,
                content=body
            )
            
            return JSONResponse(
                content=response.json() if response.headers.get("content-type", "").startswith("application/json") else response.text,
                status_code=response.status_code,
                headers=dict(response.headers)
            )
    
    except Exception as e:
        return JSONResponse(
            content={"error": f"Erreur de proxy: {str(e)}"},
            status_code=500
        )

# Endpoints de convenance pour les opérations courantes
@app.post("/scrape")
async def quick_scrape(
    start_url: HttpUrl,
    max_pages: int = 10,
    same_origin_only: bool = True,
    timeout_s: int = 30,
    priority: int = 1
):
    """Lancer un scraping rapide via l'API Gateway."""
    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            payload = {
                "start_url": str(start_url),
                "max_pages": max_pages,
                "same_origin_only": same_origin_only,
                "timeout_s": timeout_s,
                "priority": priority
            }
            
            response = await client.post(
                f"{SERVICES['cluster_controller']}/scrape",
                json=payload
            )
            
            return response.json()
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Erreur lors du scraping: {str(e)}")

@app.post("/scrape/batch")
async def quick_batch_scrape(
    urls: List[HttpUrl],
    max_pages: int = 10,
    same_origin_only: bool = True,
    timeout_s: int = 30,
    priority: int = 1
):
    """Lancer un scraping en lot via l'API Gateway."""
    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            payload = {
                "urls": [str(url) for url in urls],
                "max_pages": max_pages,
                "same_origin_only": same_origin_only,
                "timeout_s": timeout_s,
                "priority": priority
            }
            
            response = await client.post(
                f"{SERVICES['cluster_controller']}/scrape/batch",
                json=payload
            )
            
            return response.json()
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Erreur lors du scraping en lot: {str(e)}")

@app.get("/dashboard")
async def get_dashboard():
    """Données pour un tableau de bord unifié."""
    dashboard_data = {}
    
    # Statistiques du cluster
    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            response = await client.get(f"{SERVICES['cluster_controller']}/cluster")
            if response.status_code == 200:
                dashboard_data["cluster_stats"] = response.json()
    except:
        dashboard_data["cluster_stats"] = {"error": "Données indisponibles"}
    
    # Santé du cluster
    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            response = await client.get(f"{SERVICES['monitoring']}/cluster/health")
            if response.status_code == 200:
                dashboard_data["cluster_health"] = response.json()
    except:
        dashboard_data["cluster_health"] = {"error": "Données indisponibles"}
    
    # Statut des workers
    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            response = await client.get(f"{SERVICES['cluster_controller']}/workers")
            if response.status_code == 200:
                dashboard_data["workers"] = response.json()
    except:
        dashboard_data["workers"] = []
    
    # Jobs récents
    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            response = await client.get(f"{SERVICES['cluster_controller']}/jobs?limit=10")
            if response.status_code == 200:
                dashboard_data["recent_jobs"] = response.json()
    except:
        dashboard_data["recent_jobs"] = []
    
    # Tâches planifiées
    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            response = await client.get(f"{SERVICES['scheduler']}/tasks")
            if response.status_code == 200:
                dashboard_data["scheduled_tasks"] = response.json()
    except:
        dashboard_data["scheduled_tasks"] = []
    
    return {
        "timestamp": datetime.now().isoformat(),
        "data": dashboard_data
    }

@app.get("/metrics")
async def get_metrics():
    """Métriques agrégées de tous les services."""
    metrics = {}
    
    # Métriques du cluster
    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            response = await client.get(f"{SERVICES['monitoring']}/metrics")
            if response.status_code == 200:
                metrics["monitoring"] = response.json()
    except:
        pass
    
    # Performance du cluster
    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            response = await client.get(f"{SERVICES['monitoring']}/performance")
            if response.status_code == 200:
                metrics["performance"] = response.json()
    except:
        pass
    
    return {
        "timestamp": datetime.now().isoformat(),
        "metrics": metrics
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8084)