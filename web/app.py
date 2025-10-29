"""Application web principale pour DispyCluster.

Interface web moderne et API unifiée pour gérer le cluster,
les workers, le monitoring et les jobs.
"""

import asyncio
import json
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional
from pathlib import Path

# Configuration du logging
from web.config.logging_config import setup_logging
setup_logging()

from fastapi import FastAPI, HTTPException, Request, BackgroundTasks, Depends
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi import Response
from pydantic import BaseModel, HttpUrl
import httpx
import sqlite3
import uvicorn
from typing import cast
from contextlib import asynccontextmanager

# Importer les routes API
from web.api.cluster import router as cluster_router
from web.api.jobs import router as jobs_router
from web.api.monitoring import router as monitoring_router
from web.api.tests import router as tests_router
from web.api.metrics_cache import router as metrics_cache_router
from web.api.graphs import router as graphs_router

# Importer les vues intelligentes
from web.views.cluster_view import ClusterView
from web.views.monitoring_view import MonitoringView

# Importer le gestionnaire WebSocket
from web.core.websocket_manager import WebSocketManager

# Configuration
DATABASE_PATH = "web/data/cluster.db"
STATIC_PATH = "web/static"
TEMPLATES_PATH = "web/templates"

# Services backend
SERVICES = {
    "cluster_controller": "http://localhost:8081",
    "monitoring": "http://localhost:8082", 
    "scheduler": "http://localhost:8083",
    "scraper": "http://localhost:8080",
    "api_gateway": "http://localhost:8084"
}

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Initialise l'appli au démarrage et gère le teardown proprement."""
    init_database()
    print("Base de données initialisée")
    try:
        await websocket_manager.start_redis_subscriber()
        print("WebSocket Manager démarré avec support Redis pub/sub")
    except Exception as e:
        print(f"Erreur lors du démarrage de WebSocket Manager: {e}")

    # Pas de snapshot Celery périodique

    yield

    try:
        if websocket_manager.pubsub is not None:
            websocket_manager.pubsub.close()
    except Exception:
        pass
    # Rien à arrêter côté Celery snapshot

app = FastAPI(
    title="DispyCluster Web Interface",
    description="Interface web unifiée pour le cluster de Raspberry Pi",
    version="2.0.0",
    lifespan=lifespan
)

# Middleware CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Templates et fichiers statiques
templates = Jinja2Templates(directory=TEMPLATES_PATH)
app.mount("/static", StaticFiles(directory=STATIC_PATH), name="static")

# Inclure les routes API
app.include_router(cluster_router)
app.include_router(jobs_router)
app.include_router(monitoring_router)
app.include_router(tests_router)
app.include_router(metrics_cache_router)
app.include_router(graphs_router)

# Initialiser les vues intelligentes
cluster_view = ClusterView()
monitoring_view = MonitoringView(cluster_view)

# Initialiser le gestionnaire WebSocket
websocket_manager = WebSocketManager()
websocket_manager.init_app(app)

# Modèles de données
class JobRequest(BaseModel):
    name: str
    job_type: str  # scraping, processing, etc.
    parameters: Dict[str, Any]
    priority: int = 1
    scheduled_at: Optional[datetime] = None

class ClusterNode(BaseModel):
    name: str
    status: str
    cpu_usage: float
    memory_usage: float
    disk_usage: float
    temperature: Optional[float]
    last_seen: datetime

class JobStatus(BaseModel):
    id: str
    name: str
    status: str  # pending, running, completed, failed
    node: Optional[str]
    progress: float
    created_at: datetime
    started_at: Optional[datetime]
    completed_at: Optional[datetime]
    result: Optional[Dict[str, Any]]
# Celery integration
try:
    from web.celery_app import celery_app
    from web.tasks.scraping import run_scrape as celery_run_scrape
    _celery_available = True
except Exception:
    celery_app = None
    celery_run_scrape = None
    _celery_available = False


# Base de données
def init_database():
    """Initialiser la base de données SQLite."""
    Path("web/data").mkdir(parents=True, exist_ok=True)
    
    conn = sqlite3.connect(DATABASE_PATH)
    cursor = conn.cursor()
    
    # Table des jobs
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS jobs (
            id TEXT PRIMARY KEY,
            name TEXT NOT NULL,
            job_type TEXT NOT NULL,
            parameters TEXT NOT NULL,
            status TEXT NOT NULL,
            node TEXT,
            progress REAL DEFAULT 0,
            priority INTEGER DEFAULT 1,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            started_at TIMESTAMP,
            completed_at TIMESTAMP,
            result TEXT
        )
    """)

    # Ajouter la colonne task_id si elle n'existe pas
    cursor.execute("PRAGMA table_info(jobs)")
    cols = [row[1] for row in cursor.fetchall()]
    if "task_id" not in cols:
        cursor.execute("ALTER TABLE jobs ADD COLUMN task_id TEXT")
    
    # Table des nœuds
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS nodes (
            name TEXT PRIMARY KEY,
            status TEXT NOT NULL,
            cpu_usage REAL,
            memory_usage REAL,
            disk_usage REAL,
            temperature REAL,
            last_seen TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    
    # Table des métriques
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS metrics (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            node TEXT NOT NULL,
            metric_type TEXT NOT NULL,
            value REAL NOT NULL,
            timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    
    conn.commit()
    conn.close()

# Routes principales
@app.get("/", response_class=HTMLResponse)
async def dashboard(request: Request):
    """Page d'accueil du dashboard."""
    return templates.TemplateResponse("dashboard.html", {
        "request": request,
        "title": "DispyCluster Dashboard"
    })

@app.get("/favicon.ico")
async def favicon():
    # Répondre sans contenu pour éviter les 404 dans les navigateurs
    return Response(status_code=204)

@app.get("/api/health")
async def health():
    """État de santé de l'application web."""
    broker_ok = False
    if _celery_available:
        try:
            # ping renvoie une liste des workers répondants
            resp = celery_app.control.ping(timeout=1)
            broker_ok = isinstance(resp, list)
        except Exception:
            broker_ok = False
    return {
        "status": "healthy",
        "timestamp": datetime.now().isoformat(),
        "version": "2.0.0",
        "celery": {"available": _celery_available, "broker": broker_ok},
        "websocket": {"connected_clients": len(websocket_manager.connected_clients)}
    }

@app.get("/api/cluster/overview")
async def get_cluster_overview():
    """Vue d'ensemble intelligente du cluster."""
    try:
        return await cluster_view.get_cluster_overview()
    except Exception as e:
        return {
            "status": "error",
            "error": str(e),
            "timestamp": datetime.now().isoformat()
        }

@app.get("/api/cluster/nodes")
async def get_cluster_nodes():
    """Liste intelligente des nœuds du cluster."""
    try:
        nodes_data = await cluster_view.get_nodes_status()
        
        # Publier les données sur Redis pour les clients WebSocket
        await websocket_manager.publish_event("cluster:metrics", {
            "nodes": nodes_data,
            "timestamp": datetime.now().isoformat()
        })
        
        return nodes_data
    except Exception:
        # Retourner une liste vide en cas d'erreur pour ne pas casser le front
        return []

@app.get("/api/cluster/nodes/{node_name}")
async def get_node_details(node_name: str, hours: int = 24):
    """Détails intelligents d'un nœud spécifique."""
    try:
        return await cluster_view.get_node_details(node_name)
    except Exception as e:
        return {"error": str(e)}

# Gestion des jobs
@app.get("/api/jobs")
async def get_jobs(status: Optional[str] = None, limit: int = 50):
    """Liste des jobs."""
    conn = sqlite3.connect(DATABASE_PATH)
    cursor = conn.cursor()
    
    query = "SELECT * FROM jobs"
    params = []
    
    if status:
        query += " WHERE status = ?"
        params.append(status)
    
    query += " ORDER BY created_at DESC LIMIT ?"
    params.append(limit)
    
    cursor.execute(query, params)
    rows = cursor.fetchall()
    
    jobs = []
    for row in rows:
        jobs.append({
            "id": row[0],
            "name": row[1],
            "job_type": row[2],
            "parameters": json.loads(row[3]),
            "status": row[4],
            "node": row[5],
            "progress": row[6],
            "priority": row[7],
            "created_at": row[8],
            "started_at": row[9],
            "completed_at": row[10],
            "result": json.loads(row[11]) if row[11] else None
        })
    
    conn.close()
    return jobs

@app.post("/api/jobs")
async def create_job(job: JobRequest):
    """Créer un nouveau job avec intelligence."""
    try:
        job_data = {
            "name": job.name,
            "job_type": job.job_type,
            "parameters": job.parameters,
            "priority": job.priority,
            "requires": job.parameters.get("requires", [])
        }
        
        # Si Celery est dispo et type scraping, déclencher une task Celery et tracer dans SQLite
        if _celery_available and job.job_type == "scraping":
            # Enregistrer le job en base
            conn = sqlite3.connect(DATABASE_PATH)
            cursor = conn.cursor()
            job_id = f"job_{int(datetime.now().timestamp()*1000)}"
            cursor.execute(
                "INSERT INTO jobs (id, name, job_type, parameters, status, priority) VALUES (?, ?, ?, ?, ?, ?)",
                (job_id, job.name, job.job_type, json.dumps(job.parameters), "queued", job.priority),
            )
            conn.commit()

            # Lancer la task Celery
            task = celery_run_scrape.delay(job.parameters)

            # Sauvegarder le task_id pour suivi
            cursor.execute(
                "UPDATE jobs SET task_id = ? WHERE id = ?",
                (task.id, job_id),
            )
            conn.commit()
            conn.close()

            # Retourner l’identifiant Celery pour suivi
            return {"id": job_id, "task_id": task.id, "status": "queued"}

        # Sinon, fallback actuel
        result = await cluster_view.submit_job(job_data)
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Erreur lors de la création du job: {str(e)}")

async def trigger_scraping_job(job_id: str, parameters: Dict[str, Any]):
    """Déclencher un job de scraping."""
    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            payload = {
                "start_url": parameters.get("start_url"),
                "max_pages": parameters.get("max_pages", 10),
                "same_origin_only": parameters.get("same_origin_only", True),
                "timeout_s": parameters.get("timeout_s", 30),
                "priority": parameters.get("priority", 1)
            }
            
            response = await client.post(
                f"{SERVICES['api_gateway']}/scrape",
                json=payload
            )
            
            if response.status_code == 200:
                # Mettre à jour le statut du job
                conn = sqlite3.connect(DATABASE_PATH)
                cursor = conn.cursor()
                cursor.execute(
                    "UPDATE jobs SET status = ?, started_at = ? WHERE id = ?",
                    ("running", datetime.now().isoformat(), job_id)
                )
                conn.commit()
                conn.close()
                
    except Exception as e:
        # Marquer le job comme échoué
        conn = sqlite3.connect(DATABASE_PATH)
        cursor = conn.cursor()
        cursor.execute(
            "UPDATE jobs SET status = ?, result = ? WHERE id = ?",
            ("failed", json.dumps({"error": str(e)}), job_id)
        )
        conn.commit()
        conn.close()

@app.get("/api/jobs/{job_id}")
async def get_job(job_id: str):
    """Détails d'un job spécifique."""
    conn = sqlite3.connect(DATABASE_PATH)
    cursor = conn.cursor()
    
    cursor.execute("SELECT * FROM jobs WHERE id = ?", (job_id,))
    row = cursor.fetchone()
    
    if not row:
        raise HTTPException(status_code=404, detail="Job non trouvé")
    
    # Construire la réponse et inclure état Celery si task_id
    response = {
        "id": row[0],
        "name": row[1],
        "job_type": row[2],
        "parameters": json.loads(row[3]),
        "status": row[4],
        "node": row[5],
        "progress": row[6],
        "priority": row[7],
        "created_at": row[8],
        "started_at": row[9],
        "completed_at": row[10],
        "result": json.loads(row[11]) if row[11] else None
    }

    # Tenter de récupérer le task_id si la colonne existe
    try:
        # Requêter explicitement la colonne task_id
        cursor.execute("SELECT task_id FROM jobs WHERE id = ?", (job_id,))
        task_row = cursor.fetchone()
        if task_row:
            task_id = task_row[0]
        else:
            task_id = None
    except Exception:
        task_id = None

    conn.close()

    if _celery_available and task_id:
        async_result = celery_app.AsyncResult(task_id)
        response["task_id"] = task_id
        response["celery_state"] = async_result.state
        if async_result.ready():
            response["celery_result"] = async_result.result

    return response


@app.get("/api/scrape/{task_id}")
async def scrape_status(task_id: str):
    if not _celery_available:
        raise HTTPException(503, "Celery non disponible")
    async_result = celery_app.AsyncResult(task_id)
    return {
        "id": task_id,
        "state": async_result.state,
        "ready": async_result.ready(),
        "result": async_result.result if async_result.ready() else None,
    }

@app.post("/api/scrape")
async def api_scrape(payload: Dict[str, Any]):
    if not _celery_available:
        raise HTTPException(503, "Celery non disponible")
    task = celery_run_scrape.delay(payload)
    return {"task_id": task.id}

# Endpoint retiré: pas de snapshot Celery

@app.post("/api/scrape/{task_id}/abort")
async def abort_scrape(task_id: str):
    if not _celery_available:
        raise HTTPException(503, "Celery non disponible")
    try:
        celery_app.control.revoke(task_id, terminate=True, signal="SIGTERM")
        return {"task_id": task_id, "aborted": True}
    except Exception as e:
        raise HTTPException(500, f"Abort échec: {e}")

# Monitoring et métriques
@app.get("/api/metrics")
async def get_metrics():
    """Métriques intelligentes du cluster."""
    try:
        return await monitoring_view.get_real_time_metrics()
    except Exception as e:
        return {"error": str(e), "metrics": {}}

@app.get("/api/alerts")
async def get_alerts():
    """Alertes intelligentes."""
    try:
        return await monitoring_view.get_alerts()
    except Exception as e:
        return {"error": str(e), "alerts": []}

# Endpoints intelligents supplémentaires
@app.get("/api/cluster/optimize")
async def optimize_cluster():
    """Optimise automatiquement le cluster."""
    try:
        return await cluster_view.optimize_cluster()
    except Exception as e:
        return {"error": str(e)}

@app.get("/api/jobs/status")
async def get_jobs_status():
    """Statut intelligent des jobs."""
    try:
        return await cluster_view.get_jobs_status()
    except Exception as e:
        return {"error": str(e)}

@app.get("/api/monitoring/export")
async def export_metrics(format: str = "json"):
    """Exporte les métriques."""
    try:
        return await monitoring_view.export_metrics(format)
    except Exception as e:
        return {"error": str(e)}

@app.get("/api/monitoring/history")
async def get_metrics_history(hours: int = 24):
    """Historique des métriques."""
    try:
        return monitoring_view.get_metrics_history(hours)
    except Exception as e:
        return {"error": str(e)}

# Endpoints Dispy
@app.get("/api/dispy/status")
async def get_dispy_status():
    """Statut du cluster Dispy."""
    try:
        return cluster_view.dispatcher.get_dispy_status()
    except Exception as e:
        return {"error": str(e)}

@app.get("/api/dispy/jobs")
async def get_dispy_jobs():
    """Liste des jobs Dispy actifs."""
    try:
        dispatcher = cluster_view.dispatcher
        if not dispatcher.dispy_cluster:
            return {"dispy_active": False, "jobs": []}
        
        jobs_info = []
        for job in dispatcher.dispy_jobs:
            try:
                finished = job.finished()
                result = None
                if finished:
                    result = job.result
                
                jobs_info.append({
                    "id": str(id(job)),  # Identifiant unique
                    "finished": finished,
                    "status": "completed" if finished else "running",
                    "result": result if finished else None
                })
            except Exception as e:
                jobs_info.append({
                    "id": str(id(job)),
                    "finished": False,
                    "status": "error",
                    "error": str(e)
                })
        
        return {
            "dispy_active": True,
            "total_jobs": len(jobs_info),
            "active_jobs": len([j for j in jobs_info if j["status"] == "running"]),
            "completed_jobs": len([j for j in jobs_info if j["status"] == "completed"]),
            "jobs": jobs_info
        }
    except Exception as e:
        return {"dispy_active": False, "jobs": [], "error": str(e)}

@app.post("/api/dispy/cleanup")
async def cleanup_dispy_jobs():
    """Nettoie les jobs Dispy terminés."""
    try:
        cleaned = cluster_view.dispatcher.cleanup_dispy_jobs()
        return {"cleaned_jobs": cleaned, "message": "Jobs Dispy nettoyés"}
    except Exception as e:
        return {"error": str(e)}

# Pages web
@app.get("/jobs", response_class=HTMLResponse)
async def jobs_page(request: Request):
    """Page de gestion des jobs."""
    return templates.TemplateResponse("jobs.html", {
        "request": request,
        "title": "Gestion des Jobs"
    })

@app.get("/monitoring", response_class=HTMLResponse)
async def monitoring_page(request: Request):
    """Page de monitoring."""
    return templates.TemplateResponse("monitoring.html", {
        "request": request,
        "title": "Monitoring du Cluster"
    })

@app.get("/nodes", response_class=HTMLResponse)
async def nodes_page(request: Request):
    """Page des nœuds."""
    return templates.TemplateResponse("nodes.html", {
        "request": request,
        "title": "Nœuds du Cluster"
    })

@app.get("/tests", response_class=HTMLResponse)
async def tests_page(request: Request):
    """Page de tests en temps réel."""
    return templates.TemplateResponse("tests.html", {
        "request": request,
        "title": "Tests en Temps Réel"
    })

@app.get("/websocket-test", response_class=HTMLResponse)
async def websocket_test_page(request: Request):
    """Page de test WebSocket."""
    with open("web/static/websocket_test.html", "r", encoding="utf-8") as f:
        content = f.read()
    return HTMLResponse(content=content)

# Événements supprimés (remplacés par lifespan)

# Modèle d'application pour le running direct
def create_socketio_app():
    """Créer l'application combinée SocketIO + FastAPI."""
    return websocket_manager.app if websocket_manager.app else app

if __name__ == "__main__":
    # Utiliser l'app WebSocket au lieu de l'app FastAPI directement
    socketio_app = create_socketio_app()
    uvicorn.run(socketio_app, host="0.0.0.0", port=8085)