"""Service de contrôle principal pour le cluster DispyCluster.

Ce service permet de gérer le cluster de Raspberry Pi et d'orchestrer
les tâches de scraping de manière centralisée.
"""

import asyncio
import json
import time
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional, Union
from enum import Enum

from fastapi import FastAPI, HTTPException, BackgroundTasks, Depends
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, HttpUrl, Field
import requests
from aiohttp import ClientSession, ClientTimeout

# Configuration du cluster
CLUSTER_NODES = [
    "node6.lan", "node7.lan", "node9.lan", 
    "node10.lan", "node11.lan", "node12.lan", "node14.lan"
]

# Ports des services
DISPY_SCHEDULER_PORT = 51347
SCRAPER_SERVICE_PORT = 8080
NODE_EXPORTER_PORT = 9100

app = FastAPI(
    title="DispyCluster Controller",
    description="Service de contrôle pour le cluster de Raspberry Pi",
    version="1.0.0"
)

# CORS pour permettre l'accès depuis l'extérieur
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Modèles de données
class JobStatus(str, Enum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"

class ScrapeJob(BaseModel):
    id: str
    start_url: HttpUrl
    max_pages: int = Field(10, ge=1, le=1000)
    same_origin_only: bool = True
    timeout_s: int = Field(30, ge=1, le=300)
    priority: int = Field(1, ge=1, le=10)
    created_at: datetime
    status: JobStatus = JobStatus.PENDING
    assigned_worker: Optional[str] = None
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    result: Optional[Dict[str, Any]] = None
    error: Optional[str] = None

class WorkerStatus(BaseModel):
    node: str
    status: str  # online, offline, busy
    last_seen: datetime
    active_jobs: int
    total_jobs_completed: int
    cpu_usage: Optional[float] = None
    memory_usage: Optional[float] = None

class ClusterStats(BaseModel):
    total_workers: int
    online_workers: int
    total_jobs: int
    pending_jobs: int
    running_jobs: int
    completed_jobs: int
    failed_jobs: int
    average_job_duration: Optional[float] = None

# Stockage en mémoire (dans un vrai projet, utiliser une base de données)
job_queue: List[ScrapeJob] = []
job_history: List[ScrapeJob] = []
worker_status: Dict[str, WorkerStatus] = {}

# Compteurs pour les statistiques
job_counter = 0

@app.get("/")
def root():
    """Point d'entrée principal."""
    return {
        "service": "DispyCluster Controller",
        "version": "1.0.0",
        "status": "running",
        "endpoints": {
            "health": "/health",
            "cluster": "/cluster",
            "workers": "/workers",
            "jobs": "/jobs",
            "scrape": "/scrape"
        }
    }

@app.get("/health")
def health():
    """Vérification de l'état du service."""
    return {
        "status": "healthy",
        "timestamp": datetime.now().isoformat(),
        "cluster_nodes": len(CLUSTER_NODES),
        "active_jobs": len([job for job in job_queue if job.status == JobStatus.RUNNING])
    }

@app.get("/cluster", response_model=ClusterStats)
def get_cluster_stats():
    """Statistiques globales du cluster."""
    online_workers = len([w for w in worker_status.values() if w.status == "online"])
    total_jobs = len(job_queue) + len(job_history)
    
    pending_jobs = len([job for job in job_queue if job.status == JobStatus.PENDING])
    running_jobs = len([job for job in job_queue if job.status == JobStatus.RUNNING])
    completed_jobs = len([job for job in job_history if job.status == JobStatus.COMPLETED])
    failed_jobs = len([job for job in job_history if job.status == JobStatus.FAILED])
    
    # Calcul de la durée moyenne des jobs complétés
    completed_jobs_with_duration = [
        job for job in job_history 
        if job.status == JobStatus.COMPLETED and job.started_at and job.completed_at
    ]
    avg_duration = None
    if completed_jobs_with_duration:
        durations = [
            (job.completed_at - job.started_at).total_seconds() 
            for job in completed_jobs_with_duration
        ]
        avg_duration = sum(durations) / len(durations)
    
    return ClusterStats(
        total_workers=len(CLUSTER_NODES),
        online_workers=online_workers,
        total_jobs=total_jobs,
        pending_jobs=pending_jobs,
        running_jobs=running_jobs,
        completed_jobs=completed_jobs,
        failed_jobs=failed_jobs,
        average_job_duration=avg_duration
    )

@app.get("/workers", response_model=List[WorkerStatus])
def get_workers():
    """Liste des workers et leur statut."""
    return list(worker_status.values())

@app.get("/workers/{node_name}")
def get_worker_details(node_name: str):
    """Détails d'un worker spécifique."""
    if node_name not in worker_status:
        raise HTTPException(status_code=404, detail="Worker non trouvé")
    
    worker = worker_status[node_name]
    
    # Récupérer les métriques système si le worker est en ligne
    metrics = {}
    if worker.status == "online":
        try:
            response = requests.get(f"http://{node_name}:{NODE_EXPORTER_PORT}/metrics", timeout=5)
            if response.status_code == 200:
                # Parser les métriques de base (simplifié)
                metrics_text = response.text
                # Ici on pourrait parser les métriques Prometheus
                metrics["raw_metrics"] = "disponibles"
        except:
            metrics["error"] = "Impossible de récupérer les métriques"
    
    return {
        "worker": worker,
        "metrics": metrics,
        "recent_jobs": [
            job for job in job_history 
            if job.assigned_worker == node_name
        ][-5:]  # 5 derniers jobs
    }

@app.post("/workers/{node_name}/ping")
def ping_worker(node_name: str):
    """Ping un worker spécifique."""
    if node_name not in CLUSTER_NODES:
        raise HTTPException(status_code=404, detail="Worker non trouvé dans le cluster")
    
    try:
        # Tenter de contacter le service de scraping du worker
        response = requests.get(f"http://{node_name}:{SCRAPER_SERVICE_PORT}/health", timeout=5)
        if response.status_code == 200:
            # Mettre à jour le statut du worker
            if node_name not in worker_status:
                worker_status[node_name] = WorkerStatus(
                    node=node_name,
                    status="online",
                    last_seen=datetime.now(),
                    active_jobs=0,
                    total_jobs_completed=0
                )
            else:
                worker_status[node_name].status = "online"
                worker_status[node_name].last_seen = datetime.now()
            
            return {"status": "online", "response_time": response.elapsed.total_seconds()}
        else:
            worker_status[node_name].status = "offline"
            return {"status": "offline", "error": f"HTTP {response.status_code}"}
    except Exception as e:
        if node_name in worker_status:
            worker_status[node_name].status = "offline"
        return {"status": "offline", "error": str(e)}

@app.get("/jobs")
def get_jobs(status: Optional[JobStatus] = None, limit: int = 50):
    """Liste des jobs avec filtrage optionnel."""
    all_jobs = job_queue + job_history
    
    if status:
        all_jobs = [job for job in all_jobs if job.status == status]
    
    # Trier par date de création (plus récents en premier)
    all_jobs.sort(key=lambda x: x.created_at, reverse=True)
    
    return all_jobs[:limit]

@app.get("/jobs/{job_id}")
def get_job_details(job_id: str):
    """Détails d'un job spécifique."""
    all_jobs = job_queue + job_history
    job = next((job for job in all_jobs if job.id == job_id), None)
    
    if not job:
        raise HTTPException(status_code=404, detail="Job non trouvé")
    
    return job

@app.post("/jobs/{job_id}/cancel")
def cancel_job(job_id: str):
    """Annuler un job."""
    job = next((job for job in job_queue if job.id == job_id), None)
    
    if not job:
        raise HTTPException(status_code=404, detail="Job non trouvé")
    
    if job.status not in [JobStatus.PENDING, JobStatus.RUNNING]:
        raise HTTPException(status_code=400, detail="Impossible d'annuler ce job")
    
    job.status = JobStatus.CANCELLED
    job.completed_at = datetime.now()
    
    # Déplacer vers l'historique
    job_queue.remove(job)
    job_history.append(job)
    
    return {"message": "Job annulé avec succès"}

@app.post("/scrape")
def create_scrape_job(
    start_url: HttpUrl,
    max_pages: int = Field(10, ge=1, le=1000),
    same_origin_only: bool = True,
    timeout_s: int = Field(30, ge=1, le=300),
    priority: int = Field(1, ge=1, le=10),
    background_tasks: BackgroundTasks = None
):
    """Créer un nouveau job de scraping."""
    global job_counter
    job_counter += 1
    
    job = ScrapeJob(
        id=f"job_{job_counter}_{int(time.time())}",
        start_url=start_url,
        max_pages=max_pages,
        same_origin_only=same_origin_only,
        timeout_s=timeout_s,
        priority=priority,
        created_at=datetime.now()
    )
    
    job_queue.append(job)
    
    # Trier la queue par priorité (plus haute priorité en premier)
    job_queue.sort(key=lambda x: x.priority, reverse=True)
    
    # Lancer le job en arrière-plan
    if background_tasks:
        background_tasks.add_task(execute_job, job.id)
    
    return {
        "message": "Job créé avec succès",
        "job_id": job.id,
        "status": job.status
    }

@app.post("/scrape/batch")
def create_batch_scrape_jobs(
    urls: List[HttpUrl],
    max_pages: int = Field(10, ge=1, le=1000),
    same_origin_only: bool = True,
    timeout_s: int = Field(30, ge=1, le=300),
    priority: int = Field(1, ge=1, le=10),
    background_tasks: BackgroundTasks = None
):
    """Créer plusieurs jobs de scraping en lot."""
    job_ids = []
    
    for url in urls:
        global job_counter
        job_counter += 1
        
        job = ScrapeJob(
            id=f"batch_{job_counter}_{int(time.time())}",
            start_url=url,
            max_pages=max_pages,
            same_origin_only=same_origin_only,
            timeout_s=timeout_s,
            priority=priority,
            created_at=datetime.now()
        )
        
        job_queue.append(job)
        job_ids.append(job.id)
    
    # Trier la queue par priorité
    job_queue.sort(key=lambda x: x.priority, reverse=True)
    
    # Lancer tous les jobs en arrière-plan
    if background_tasks:
        for job_id in job_ids:
            background_tasks.add_task(execute_job, job_id)
    
    return {
        "message": f"{len(urls)} jobs créés avec succès",
        "job_ids": job_ids
    }

async def execute_job(job_id: str):
    """Exécuter un job de scraping sur un worker disponible."""
    job = next((job for job in job_queue if job.id == job_id), None)
    if not job:
        return
    
    # Trouver un worker disponible
    available_workers = [
        node for node in CLUSTER_NODES 
        if worker_status.get(node, {}).status == "online"
    ]
    
    if not available_workers:
        job.status = JobStatus.FAILED
        job.error = "Aucun worker disponible"
        job.completed_at = datetime.now()
        job_queue.remove(job)
        job_history.append(job)
        return
    
    # Assigner au premier worker disponible
    assigned_worker = available_workers[0]
    job.assigned_worker = assigned_worker
    job.status = JobStatus.RUNNING
    job.started_at = datetime.now()
    
    try:
        # Appeler le service de scraping du worker
        async with ClientSession(timeout=ClientTimeout(total=job.timeout_s + 10)) as session:
            payload = {
                "start_url": str(job.start_url),
                "max_pages": job.max_pages,
                "same_origin_only": job.same_origin_only,
                "timeout_s": job.timeout_s
            }
            
            async with session.post(
                f"http://{assigned_worker}:{SCRAPER_SERVICE_PORT}/scrape",
                json=payload
            ) as response:
                if response.status == 200:
                    result = await response.json()
                    job.result = result
                    job.status = JobStatus.COMPLETED
                else:
                    job.status = JobStatus.FAILED
                    job.error = f"Erreur HTTP {response.status}"
    
    except Exception as e:
        job.status = JobStatus.FAILED
        job.error = str(e)
    
    finally:
        job.completed_at = datetime.now()
        
        # Mettre à jour les statistiques du worker
        if assigned_worker in worker_status:
            if job.status == JobStatus.COMPLETED:
                worker_status[assigned_worker].total_jobs_completed += 1
        
        # Déplacer vers l'historique
        job_queue.remove(job)
        job_history.append(job)

@app.get("/monitoring/dashboard")
def get_dashboard_data():
    """Données pour un tableau de bord de monitoring."""
    stats = get_cluster_stats()
    
    # Jobs récents
    recent_jobs = sorted(
        job_queue + job_history,
        key=lambda x: x.created_at,
        reverse=True
    )[:10]
    
    # Performance des workers
    worker_performance = []
    for node, worker in worker_status.items():
        if worker.total_jobs_completed > 0:
            worker_performance.append({
                "node": node,
                "jobs_completed": worker.total_jobs_completed,
                "status": worker.status,
                "last_seen": worker.last_seen
            })
    
    return {
        "cluster_stats": stats,
        "recent_jobs": recent_jobs,
        "worker_performance": worker_performance,
        "timestamp": datetime.now().isoformat()
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8081)