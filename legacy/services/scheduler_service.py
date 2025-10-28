"""Service de planification des tâches pour le cluster DispyCluster.

Ce service permet de programmer des tâches de scraping récurrentes,
de gérer des workflows complexes, et d'optimiser l'utilisation des ressources.
"""

import asyncio
import json
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional, Union
from enum import Enum
from dataclasses import dataclass

from fastapi import FastAPI, HTTPException, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
import requests
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
from apscheduler.triggers.interval import IntervalTrigger
from apscheduler.triggers.date import DateTrigger

# Configuration
CLUSTER_CONTROLLER_URL = "http://localhost:8081"
MONITORING_SERVICE_URL = "http://localhost:8082"

app = FastAPI(
    title="DispyCluster Scheduler",
    description="Service de planification des tâches pour le cluster",
    version="1.0.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Scheduler APScheduler
scheduler = AsyncIOScheduler()

class ScheduleType(str, Enum):
    ONCE = "once"
    INTERVAL = "interval"
    CRON = "cron"

class TaskStatus(str, Enum):
    SCHEDULED = "scheduled"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"

class ScrapeTask(BaseModel):
    id: str
    name: str
    description: Optional[str] = None
    urls: List[str]
    max_pages: int = Field(10, ge=1, le=1000)
    same_origin_only: bool = True
    timeout_s: int = Field(30, ge=1, le=300)
    priority: int = Field(1, ge=1, le=10)
    schedule_type: ScheduleType
    schedule_config: Dict[str, Any]
    created_at: datetime
    last_run: Optional[datetime] = None
    next_run: Optional[datetime] = None
    status: TaskStatus = TaskStatus.SCHEDULED
    run_count: int = 0
    success_count: int = 0
    failure_count: int = 0
    enabled: bool = True

class WorkflowStep(BaseModel):
    step_id: str
    name: str
    action: str  # scrape, wait, condition, etc.
    config: Dict[str, Any]
    depends_on: List[str] = []

class Workflow(BaseModel):
    id: str
    name: str
    description: Optional[str] = None
    steps: List[WorkflowStep]
    schedule_type: ScheduleType
    schedule_config: Dict[str, Any]
    created_at: datetime
    status: TaskStatus = TaskStatus.SCHEDULED
    enabled: bool = True

# Stockage des tâches et workflows
scheduled_tasks: Dict[str, ScrapeTask] = {}
workflows: Dict[str, Workflow] = {}
task_history: List[Dict[str, Any]] = []

@app.get("/")
def root():
    """Point d'entrée du service de planification."""
    return {
        "service": "DispyCluster Scheduler",
        "version": "1.0.0",
        "status": "running",
        "scheduler_running": scheduler.running,
        "endpoints": {
            "health": "/health",
            "tasks": "/tasks",
            "workflows": "/workflows",
            "schedule": "/schedule"
        }
    }

@app.get("/health")
def health():
    """Vérification de l'état du service."""
    return {
        "status": "healthy",
        "timestamp": datetime.now().isoformat(),
        "scheduler_running": scheduler.running,
        "scheduled_tasks": len(scheduled_tasks),
        "active_workflows": len([w for w in workflows.values() if w.enabled])
    }

@app.post("/tasks")
def create_scheduled_task(
    name: str,
    urls: List[str],
    max_pages: int = Field(10, ge=1, le=1000),
    same_origin_only: bool = True,
    timeout_s: int = Field(30, ge=1, le=300),
    priority: int = Field(1, ge=1, le=10),
    schedule_type: ScheduleType = ScheduleType.ONCE,
    schedule_config: Dict[str, Any] = {},
    description: Optional[str] = None
):
    """Créer une tâche planifiée."""
    task_id = f"task_{int(datetime.now().timestamp())}"
    
    # Calculer la prochaine exécution
    next_run = calculate_next_run(schedule_type, schedule_config)
    
    task = ScrapeTask(
        id=task_id,
        name=name,
        description=description,
        urls=urls,
        max_pages=max_pages,
        same_origin_only=same_origin_only,
        timeout_s=timeout_s,
        priority=priority,
        schedule_type=schedule_type,
        schedule_config=schedule_config,
        created_at=datetime.now(),
        next_run=next_run
    )
    
    scheduled_tasks[task_id] = task
    
    # Programmer la tâche
    if schedule_type == ScheduleType.ONCE:
        if next_run:
            scheduler.add_job(
                execute_task,
                DateTrigger(run_date=next_run),
                args=[task_id],
                id=task_id
            )
    elif schedule_type == ScheduleType.INTERVAL:
        interval_seconds = schedule_config.get("seconds", 3600)
        scheduler.add_job(
            execute_task,
            IntervalTrigger(seconds=interval_seconds),
            args=[task_id],
            id=task_id
        )
    elif schedule_type == ScheduleType.CRON:
        cron_expression = schedule_config.get("cron", "0 * * * *")
        scheduler.add_job(
            execute_task,
            CronTrigger.from_crontab(cron_expression),
            args=[task_id],
            id=task_id
        )
    
    return {
        "message": "Tâche créée avec succès",
        "task_id": task_id,
        "next_run": next_run.isoformat() if next_run else None
    }

@app.get("/tasks")
def get_tasks():
    """Liste toutes les tâches planifiées."""
    return list(scheduled_tasks.values())

@app.get("/tasks/{task_id}")
def get_task_details(task_id: str):
    """Détails d'une tâche spécifique."""
    if task_id not in scheduled_tasks:
        raise HTTPException(status_code=404, detail="Tâche non trouvée")
    
    return scheduled_tasks[task_id]

@app.post("/tasks/{task_id}/enable")
def enable_task(task_id: str):
    """Activer une tâche."""
    if task_id not in scheduled_tasks:
        raise HTTPException(status_code=404, detail="Tâche non trouvée")
    
    task = scheduled_tasks[task_id]
    task.enabled = True
    
    # Reprogrammer la tâche
    if task.schedule_type == ScheduleType.ONCE:
        if task.next_run:
            scheduler.add_job(
                execute_task,
                DateTrigger(run_date=task.next_run),
                args=[task_id],
                id=task_id
            )
    elif task.schedule_type == ScheduleType.INTERVAL:
        interval_seconds = task.schedule_config.get("seconds", 3600)
        scheduler.add_job(
            execute_task,
            IntervalTrigger(seconds=interval_seconds),
            args=[task_id],
            id=task_id
        )
    elif task.schedule_type == ScheduleType.CRON:
        cron_expression = task.schedule_config.get("cron", "0 * * * *")
        scheduler.add_job(
            execute_task,
            CronTrigger.from_crontab(cron_expression),
            args=[task_id],
            id=task_id
        )
    
    return {"message": "Tâche activée"}

@app.post("/tasks/{task_id}/disable")
def disable_task(task_id: str):
    """Désactiver une tâche."""
    if task_id not in scheduled_tasks:
        raise HTTPException(status_code=404, detail="Tâche non trouvée")
    
    task = scheduled_tasks[task_id]
    task.enabled = False
    
    # Supprimer la tâche du scheduler
    try:
        scheduler.remove_job(task_id)
    except:
        pass
    
    return {"message": "Tâche désactivée"}

@app.delete("/tasks/{task_id}")
def delete_task(task_id: str):
    """Supprimer une tâche."""
    if task_id not in scheduled_tasks:
        raise HTTPException(status_code=404, detail="Tâche non trouvée")
    
    # Supprimer du scheduler
    try:
        scheduler.remove_job(task_id)
    except:
        pass
    
    # Supprimer de la liste
    del scheduled_tasks[task_id]
    
    return {"message": "Tâche supprimée"}

@app.post("/tasks/{task_id}/run")
def run_task_now(task_id: str, background_tasks: BackgroundTasks):
    """Exécuter une tâche immédiatement."""
    if task_id not in scheduled_tasks:
        raise HTTPException(status_code=404, detail="Tâche non trouvée")
    
    background_tasks.add_task(execute_task, task_id)
    
    return {"message": "Tâche lancée immédiatement"}

@app.post("/workflows")
def create_workflow(
    name: str,
    steps: List[WorkflowStep],
    schedule_type: ScheduleType = ScheduleType.ONCE,
    schedule_config: Dict[str, Any] = {},
    description: Optional[str] = None
):
    """Créer un workflow complexe."""
    workflow_id = f"workflow_{int(datetime.now().timestamp())}"
    
    workflow = Workflow(
        id=workflow_id,
        name=name,
        description=description,
        steps=steps,
        schedule_type=schedule_type,
        schedule_config=schedule_config,
        created_at=datetime.now()
    )
    
    workflows[workflow_id] = workflow
    
    # Programmer le workflow
    if schedule_type == ScheduleType.ONCE:
        next_run = calculate_next_run(schedule_type, schedule_config)
        if next_run:
            scheduler.add_job(
                execute_workflow,
                DateTrigger(run_date=next_run),
                args=[workflow_id],
                id=workflow_id
            )
    elif schedule_type == ScheduleType.INTERVAL:
        interval_seconds = schedule_config.get("seconds", 3600)
        scheduler.add_job(
            execute_workflow,
            IntervalTrigger(seconds=interval_seconds),
            args=[workflow_id],
            id=workflow_id
        )
    elif schedule_type == ScheduleType.CRON:
        cron_expression = schedule_config.get("cron", "0 * * * *")
        scheduler.add_job(
            execute_workflow,
            CronTrigger.from_crontab(cron_expression),
            args=[workflow_id],
            id=workflow_id
        )
    
    return {
        "message": "Workflow créé avec succès",
        "workflow_id": workflow_id
    }

@app.get("/workflows")
def get_workflows():
    """Liste tous les workflows."""
    return list(workflows.values())

@app.get("/workflows/{workflow_id}")
def get_workflow_details(workflow_id: str):
    """Détails d'un workflow spécifique."""
    if workflow_id not in workflows:
        raise HTTPException(status_code=404, detail="Workflow non trouvé")
    
    return workflows[workflow_id]

@app.post("/workflows/{workflow_id}/run")
def run_workflow_now(workflow_id: str, background_tasks: BackgroundTasks):
    """Exécuter un workflow immédiatement."""
    if workflow_id not in workflows:
        raise HTTPException(status_code=404, detail="Workflow non trouvé")
    
    background_tasks.add_task(execute_workflow, workflow_id)
    
    return {"message": "Workflow lancé immédiatement"}

@app.get("/schedule")
def get_schedule():
    """Aperçu du planning des tâches."""
    jobs = []
    
    for job in scheduler.get_jobs():
        jobs.append({
            "id": job.id,
            "name": job.name or "Sans nom",
            "next_run": job.next_run_time.isoformat() if job.next_run_time else None,
            "trigger": str(job.trigger)
        })
    
    return {
        "scheduler_running": scheduler.running,
        "total_jobs": len(jobs),
        "jobs": jobs
    }

@app.get("/history")
def get_task_history(limit: int = 50):
    """Historique des exécutions de tâches."""
    return task_history[-limit:]

def calculate_next_run(schedule_type: ScheduleType, schedule_config: Dict[str, Any]) -> Optional[datetime]:
    """Calculer la prochaine exécution d'une tâche."""
    now = datetime.now()
    
    if schedule_type == ScheduleType.ONCE:
        if "datetime" in schedule_config:
            return datetime.fromisoformat(schedule_config["datetime"])
        return now + timedelta(minutes=1)
    
    elif schedule_type == ScheduleType.INTERVAL:
        seconds = schedule_config.get("seconds", 3600)
        return now + timedelta(seconds=seconds)
    
    elif schedule_type == ScheduleType.CRON:
        # Pour les tâches cron, on ne peut pas calculer facilement la prochaine exécution
        # Le scheduler APScheduler s'en chargera
        return None
    
    return None

async def execute_task(task_id: str):
    """Exécuter une tâche planifiée."""
    if task_id not in scheduled_tasks:
        return
    
    task = scheduled_tasks[task_id]
    
    if not task.enabled:
        return
    
    task.status = TaskStatus.RUNNING
    task.last_run = datetime.now()
    task.run_count += 1
    
    try:
        # Appeler le service de contrôle du cluster
        payload = {
            "urls": task.urls,
            "max_pages": task.max_pages,
            "same_origin_only": task.same_origin_only,
            "timeout_s": task.timeout_s,
            "priority": task.priority
        }
        
        response = requests.post(
            f"{CLUSTER_CONTROLLER_URL}/scrape/batch",
            json=payload,
            timeout=30
        )
        
        if response.status_code == 200:
            task.status = TaskStatus.COMPLETED
            task.success_count += 1
        else:
            task.status = TaskStatus.FAILED
            task.failure_count += 1
        
    except Exception as e:
        task.status = TaskStatus.FAILED
        task.failure_count += 1
        print(f"Erreur lors de l'exécution de la tâche {task_id}: {e}")
    
    # Enregistrer dans l'historique
    task_history.append({
        "task_id": task_id,
        "task_name": task.name,
        "executed_at": task.last_run.isoformat(),
        "status": task.status,
        "run_count": task.run_count
    })
    
    # Calculer la prochaine exécution pour les tâches récurrentes
    if task.schedule_type != ScheduleType.ONCE:
        task.next_run = calculate_next_run(task.schedule_type, task.schedule_config)

async def execute_workflow(workflow_id: str):
    """Exécuter un workflow complexe."""
    if workflow_id not in workflows:
        return
    
    workflow = workflows[workflow_id]
    
    if not workflow.enabled:
        return
    
    workflow.status = TaskStatus.RUNNING
    
    try:
        # Exécuter les étapes du workflow dans l'ordre
        for step in workflow.steps:
            await execute_workflow_step(workflow_id, step)
        
        workflow.status = TaskStatus.COMPLETED
        
    except Exception as e:
        workflow.status = TaskStatus.FAILED
        print(f"Erreur lors de l'exécution du workflow {workflow_id}: {e}")
    
    # Enregistrer dans l'historique
    task_history.append({
        "workflow_id": workflow_id,
        "workflow_name": workflow.name,
        "executed_at": datetime.now().isoformat(),
        "status": workflow.status
    })

async def execute_workflow_step(workflow_id: str, step: WorkflowStep):
    """Exécuter une étape d'un workflow."""
    if step.action == "scrape":
        # Exécuter un scraping
        urls = step.config.get("urls", [])
        max_pages = step.config.get("max_pages", 10)
        
        payload = {
            "urls": urls,
            "max_pages": max_pages,
            "same_origin_only": step.config.get("same_origin_only", True),
            "timeout_s": step.config.get("timeout_s", 30),
            "priority": step.config.get("priority", 1)
        }
        
        response = requests.post(
            f"{CLUSTER_CONTROLLER_URL}/scrape/batch",
            json=payload,
            timeout=30
        )
        
        if response.status_code != 200:
            raise Exception(f"Erreur lors du scraping: {response.status_code}")
    
    elif step.action == "wait":
        # Attendre un certain temps
        seconds = step.config.get("seconds", 60)
        await asyncio.sleep(seconds)
    
    elif step.action == "condition":
        # Vérifier une condition
        condition = step.config.get("condition")
        if not condition:
            raise Exception("Condition non spécifiée")
        
        # Ici on pourrait implémenter des conditions plus complexes
        # Pour l'instant, on simule
        if not eval(condition):
            raise Exception(f"Condition non remplie: {condition}")

@app.on_event("startup")
async def startup_event():
    """Démarrer le scheduler au démarrage."""
    if not scheduler.running:
        scheduler.start()

@app.on_event("shutdown")
async def shutdown_event():
    """Arrêter le scheduler à l'arrêt."""
    if scheduler.running:
        scheduler.shutdown()

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8083)