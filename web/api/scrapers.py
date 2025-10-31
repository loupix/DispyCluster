"""API endpoints pour le service de scraping.

Endpoints XHR pour lancer, arrêter et consulter les scrapings.
"""

from fastapi import APIRouter, HTTPException, Depends
from typing import List, Dict, Any, Optional
from pydantic import BaseModel, HttpUrl
from datetime import datetime

from web.config.logging_config import get_logger

logger = get_logger(__name__)

router = APIRouter(prefix="/api/scrapers", tags=["scrapers"])


# Modèles de requête
class ScrapeRequest(BaseModel):
    """Requête pour lancer un scraping."""
    url: str
    max_pages: int = 10
    timeout_s: int = 10
    same_origin_only: bool = True
    priority: int = 1


class ScrapeResponse(BaseModel):
    """Réponse d'une soumission de scraping."""
    success: bool
    job_id: Optional[str] = None
    task_id: Optional[str] = None
    status: str
    error: Optional[str] = None


# Dépendance pour obtenir le service scraper
def get_scraper_service():
    """Récupère l'instance du service scraper depuis l'app."""
    from web.app import scraper_service
    return scraper_service


@router.post("/submit", response_model=ScrapeResponse)
async def submit_scrape(
    request: ScrapeRequest,
    service = Depends(get_scraper_service)
):
    """Soumet un job de scraping au cluster.
    
    Args:
        request: Paramètres du scraping
        
    Returns:
        Informations sur le job soumis
    """
    try:
        result = await service.submit_scrape_job(
            url=request.url,
            max_pages=request.max_pages,
            timeout_s=request.timeout_s,
            same_origin_only=request.same_origin_only,
            priority=request.priority
        )
        
        if result.get("success"):
            return ScrapeResponse(
                success=True,
                job_id=result.get("job_id"),
                task_id=result.get("task_id"),
                status=result.get("status", "submitted")
            )
        else:
            return ScrapeResponse(
                success=False,
                error=result.get("error", "Erreur inconnue")
            )
            
    except Exception as e:
        logger.error(f"Erreur lors de la soumission du scraping: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/jobs/{job_id}")
async def get_job_status(
    job_id: str,
    service = Depends(get_scraper_service)
):
    """Récupère le statut d'un job de scraping.
    
    Args:
        job_id: ID du job
        
    Returns:
        Statut du job
    """
    try:
        status = await service.get_job_status(job_id)
        return status
    except Exception as e:
        logger.error(f"Erreur lors de la récupération du statut {job_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/jobs")
async def list_jobs(
    status: Optional[str] = None,
    limit: int = 50,
    service = Depends(get_scraper_service)
):
    """Liste les jobs de scraping.
    
    Args:
        status: Filtrer par statut (optionnel)
        limit: Nombre maximum de jobs
        
    Returns:
        Liste des jobs
    """
    try:
        jobs = await service.list_jobs(status=status, limit=limit)
        return {
            "jobs": jobs,
            "total": len(jobs),
            "timestamp": datetime.now().isoformat()
        }
    except Exception as e:
        logger.error(f"Erreur lors de la liste des jobs: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/history")
async def get_scrape_history(
    limit: int = 50,
    status: Optional[str] = None,
    service = Depends(get_scraper_service)
):
    """Récupère l'historique des scrapings depuis la DB.
    
    Args:
        limit: Nombre maximum de résultats
        status: Filtrer par statut
        
    Returns:
        Historique des scrapings
    """
    try:
        history = await service.get_scrape_history(limit=limit, status=status)
        return {
            "history": history,
            "total": len(history),
            "timestamp": datetime.now().isoformat()
        }
    except Exception as e:
        logger.error(f"Erreur lors de la récupération de l'historique: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/jobs/{job_id}/results")
async def get_scrape_results(
    job_id: str,
    service = Depends(get_scraper_service)
):
    """Récupère les résultats détaillés d'un scraping.
    
    Args:
        job_id: ID du job
        
    Returns:
        Résultats détaillés
    """
    try:
        results = await service.get_scrape_results(job_id)
        return results
    except Exception as e:
        logger.error(f"Erreur lors de la récupération des résultats {job_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/jobs/{job_id}")
async def cancel_job(
    job_id: str,
    service = Depends(get_scraper_service)
):
    """Annule un job de scraping en cours.
    
    Args:
        job_id: ID du job
        
    Returns:
        Résultat de l'annulation
    """
    try:
        result = await service.cancel_job(job_id)
        return result
    except Exception as e:
        logger.error(f"Erreur lors de l'annulation du job {job_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/stats")
async def get_service_stats(
    service = Depends(get_scraper_service)
):
    """Récupère les statistiques du service scraper.
    
    Returns:
        Statistiques complètes
    """
    try:
        stats = await service.get_service_stats()
        return stats
    except Exception as e:
        logger.error(f"Erreur lors de la récupération des stats: {e}")
        raise HTTPException(status_code=500, detail=str(e))

