"""API endpoints pour la gestion des jobs."""

from fastapi import APIRouter, HTTPException, Depends, BackgroundTasks
from typing import List, Dict, Any, Optional
from pydantic import BaseModel
from datetime import datetime
import json
import sqlite3
import uuid
import httpx
import asyncio

router = APIRouter(prefix="/api/jobs", tags=["jobs"])

# Configuration
DATABASE_PATH = "web/data/cluster.db"
SERVICES = {
    "api_gateway": "http://localhost:8084",
    "cluster_controller": "http://localhost:8081"
}

# Modèles
class JobRequest(BaseModel):
    name: str
    job_type: str
    parameters: Dict[str, Any]
    priority: int = 1
    scheduled_at: Optional[datetime] = None

class JobUpdate(BaseModel):
    status: Optional[str] = None
    progress: Optional[float] = None
    node: Optional[str] = None
    result: Optional[Dict[str, Any]] = None

class JobResponse(BaseModel):
    id: str
    name: str
    job_type: str
    parameters: Dict[str, Any]
    status: str
    node: Optional[str]
    progress: float
    priority: int
    created_at: datetime
    started_at: Optional[datetime]
    completed_at: Optional[datetime]
    result: Optional[Dict[str, Any]]

@router.get("/", response_model=List[JobResponse])
async def get_jobs(
    status: Optional[str] = None,
    job_type: Optional[str] = None,
    limit: int = 50,
    offset: int = 0
):
    """Liste des jobs avec filtres."""
    conn = sqlite3.connect(DATABASE_PATH)
    cursor = conn.cursor()
    
    # Construire la requête
    query = "SELECT * FROM jobs WHERE 1=1"
    params = []
    
    if status:
        query += " AND status = ?"
        params.append(status)
    
    if job_type:
        query += " AND job_type = ?"
        params.append(job_type)
    
    query += " ORDER BY created_at DESC LIMIT ? OFFSET ?"
    params.extend([limit, offset])
    
    cursor.execute(query, params)
    rows = cursor.fetchall()
    
    jobs = []
    for row in rows:
        jobs.append(JobResponse(
            id=row[0],
            name=row[1],
            job_type=row[2],
            parameters=json.loads(row[3]),
            status=row[4],
            node=row[5],
            progress=row[6],
            priority=row[7],
            created_at=datetime.fromisoformat(row[8]),
            started_at=datetime.fromisoformat(row[9]) if row[9] else None,
            completed_at=datetime.fromisoformat(row[10]) if row[10] else None,
            result=json.loads(row[11]) if row[11] else None
        ))
    
    conn.close()
    return jobs

@router.get("/{job_id}", response_model=JobResponse)
async def get_job(job_id: str):
    """Détails d'un job spécifique."""
    conn = sqlite3.connect(DATABASE_PATH)
    cursor = conn.cursor()
    
    cursor.execute("SELECT * FROM jobs WHERE id = ?", (job_id,))
    row = cursor.fetchone()
    
    if not row:
        raise HTTPException(status_code=404, detail="Job non trouvé")
    
    conn.close()
    
    return JobResponse(
        id=row[0],
        name=row[1],
        job_type=row[2],
        parameters=json.loads(row[3]),
        status=row[4],
        node=row[5],
        progress=row[6],
        priority=row[7],
        created_at=datetime.fromisoformat(row[8]),
        started_at=datetime.fromisoformat(row[9]) if row[9] else None,
        completed_at=datetime.fromisoformat(row[10]) if row[10] else None,
        result=json.loads(row[11]) if row[11] else None
    )

@router.post("/", response_model=Dict[str, str])
async def create_job(job: JobRequest, background_tasks: BackgroundTasks):
    """Créer un nouveau job."""
    job_id = f"job_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{uuid.uuid4().hex[:8]}"
    
    conn = sqlite3.connect(DATABASE_PATH)
    cursor = conn.cursor()
    
    cursor.execute("""
        INSERT INTO jobs (id, name, job_type, parameters, status, priority, created_at)
        VALUES (?, ?, ?, ?, ?, ?, ?)
    """, (
        job_id,
        job.name,
        job.job_type,
        json.dumps(job.parameters),
        "pending",
        job.priority,
        datetime.now().isoformat()
    ))
    
    conn.commit()
    conn.close()
    
    # Déclencher le job en arrière-plan
    background_tasks.add_task(process_job, job_id, job)
    
    return {"id": job_id, "status": "created"}

@router.put("/{job_id}")
async def update_job(job_id: str, update: JobUpdate):
    """Mettre à jour un job."""
    conn = sqlite3.connect(DATABASE_PATH)
    cursor = conn.cursor()
    
    # Vérifier que le job existe
    cursor.execute("SELECT id FROM jobs WHERE id = ?", (job_id,))
    if not cursor.fetchone():
        conn.close()
        raise HTTPException(status_code=404, detail="Job non trouvé")
    
    # Construire la requête de mise à jour
    updates = []
    params = []
    
    if update.status is not None:
        updates.append("status = ?")
        params.append(update.status)
        
        # Mettre à jour les timestamps selon le statut
        if update.status == "running":
            updates.append("started_at = ?")
            params.append(datetime.now().isoformat())
        elif update.status in ["completed", "failed"]:
            updates.append("completed_at = ?")
            params.append(datetime.now().isoformat())
    
    if update.progress is not None:
        updates.append("progress = ?")
        params.append(update.progress)
    
    if update.node is not None:
        updates.append("node = ?")
        params.append(update.node)
    
    if update.result is not None:
        updates.append("result = ?")
        params.append(json.dumps(update.result))
    
    if updates:
        params.append(job_id)
        query = f"UPDATE jobs SET {', '.join(updates)} WHERE id = ?"
        cursor.execute(query, params)
        conn.commit()
    
    conn.close()
    return {"message": "Job mis à jour avec succès"}

@router.delete("/{job_id}")
async def cancel_job(job_id: str):
    """Annuler un job."""
    conn = sqlite3.connect(DATABASE_PATH)
    cursor = conn.cursor()
    
    # Vérifier que le job existe et n'est pas terminé
    cursor.execute("SELECT status FROM jobs WHERE id = ?", (job_id,))
    result = cursor.fetchone()
    
    if not result:
        conn.close()
        raise HTTPException(status_code=404, detail="Job non trouvé")
    
    if result[0] in ["completed", "failed", "cancelled"]:
        conn.close()
        raise HTTPException(status_code=400, detail="Impossible d'annuler un job terminé")
    
    # Marquer comme annulé
    cursor.execute(
        "UPDATE jobs SET status = ?, completed_at = ? WHERE id = ?",
        ("cancelled", datetime.now().isoformat(), job_id)
    )
    
    conn.commit()
    conn.close()
    
    return {"message": "Job annulé avec succès"}

@router.get("/{job_id}/logs")
async def get_job_logs(job_id: str):
    """Récupérer les logs d'un job."""
    # Pour l'instant, retourner des logs simulés
    # Dans une implémentation complète, on récupérerait les vrais logs
    return {
        "job_id": job_id,
        "logs": [
            {"timestamp": datetime.now().isoformat(), "level": "INFO", "message": "Job démarré"},
            {"timestamp": datetime.now().isoformat(), "level": "INFO", "message": "Traitement en cours..."}
        ]
    }

@router.post("/{job_id}/retry")
async def retry_job(job_id: str):
    """Relancer un job échoué."""
    conn = sqlite3.connect(DATABASE_PATH)
    cursor = conn.cursor()
    
    # Vérifier que le job existe et a échoué
    cursor.execute("SELECT status FROM jobs WHERE id = ?", (job_id,))
    result = cursor.fetchone()
    
    if not result:
        conn.close()
        raise HTTPException(status_code=404, detail="Job non trouvé")
    
    if result[0] != "failed":
        conn.close()
        raise HTTPException(status_code=400, detail="Seuls les jobs échoués peuvent être relancés")
    
    # Créer un nouveau job avec les mêmes paramètres
    cursor.execute("SELECT name, job_type, parameters, priority FROM jobs WHERE id = ?", (job_id,))
    job_data = cursor.fetchone()
    
    new_job_id = f"job_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{uuid.uuid4().hex[:8]}"
    
    cursor.execute("""
        INSERT INTO jobs (id, name, job_type, parameters, status, priority, created_at)
        VALUES (?, ?, ?, ?, ?, ?, ?)
    """, (
        new_job_id,
        f"{job_data[0]} (retry)",
        job_data[1],
        job_data[2],
        "pending",
        job_data[3],
        datetime.now().isoformat()
    ))
    
    conn.commit()
    conn.close()
    
    return {"id": new_job_id, "message": "Job relancé avec succès"}

async def process_job(job_id: str, job_request: JobRequest):
    """Traiter un job en arrière-plan."""
    try:
        # Mettre à jour le statut
        await update_job_status(job_id, "running", 0)
        
        # Traiter selon le type de job
        if job_request.job_type == "scraping":
            await process_scraping_job(job_id, job_request.parameters)
        elif job_request.job_type == "processing":
            await process_data_job(job_id, job_request.parameters)
        else:
            await process_generic_job(job_id, job_request.parameters)
            
    except Exception as e:
        # Marquer le job comme échoué
        await update_job_status(job_id, "failed", 100, result={"error": str(e)})

async def process_scraping_job(job_id: str, parameters: Dict[str, Any]):
    """Traiter un job de scraping."""
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
                result = response.json()
                await update_job_status(job_id, "completed", 100, result=result)
            else:
                await update_job_status(job_id, "failed", 100, result={"error": f"HTTP {response.status_code}"})
                
    except Exception as e:
        await update_job_status(job_id, "failed", 100, result={"error": str(e)})

async def process_data_job(job_id: str, parameters: Dict[str, Any]):
    """Traiter un job de traitement de données."""
    # Simulation d'un traitement
    import time
    time.sleep(2)  # Simulation du traitement
    
    await update_job_status(job_id, "completed", 100, result={"processed": True})

async def process_generic_job(job_id: str, parameters: Dict[str, Any]):
    """Traiter un job générique."""
    # Simulation d'un traitement
    import time
    time.sleep(1)  # Simulation du traitement
    
    await update_job_status(job_id, "completed", 100, result={"completed": True})

async def update_job_status(job_id: str, status: str, progress: float, node: str = None, result: Dict[str, Any] = None):
    """Mettre à jour le statut d'un job."""
    conn = sqlite3.connect(DATABASE_PATH)
    cursor = conn.cursor()
    
    updates = ["status = ?", "progress = ?"]
    params = [status, progress]
    
    if node:
        updates.append("node = ?")
        params.append(node)
    
    if result:
        updates.append("result = ?")
        params.append(json.dumps(result))
    
    if status == "running":
        updates.append("started_at = ?")
        params.append(datetime.now().isoformat())
    elif status in ["completed", "failed"]:
        updates.append("completed_at = ?")
        params.append(datetime.now().isoformat())
    
    params.append(job_id)
    query = f"UPDATE jobs SET {', '.join(updates)} WHERE id = ?"
    cursor.execute(query, params)
    
    conn.commit()
    conn.close()