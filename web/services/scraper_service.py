"""Service de scraping distribué sur cluster Dispy.

Utilise les workers scraping existants et permet de scraper des sites
en distribuant le travail sur plusieurs nœuds du cluster.
"""

from typing import Dict, List, Any, Optional
from datetime import datetime
import json

from web.core.base_service import BaseService
from web.core.database import DatabaseManager
from web.core.dispatcher import Dispatcher
from web.core.task_queue import TaskQueue
from web.config.logging_config import get_logger

logger = get_logger(__name__)


class ScraperService(BaseService):
    """Service de scraping distribué."""
    
    def __init__(
        self,
        dispatcher: Dispatcher,
        task_queue: TaskQueue,
        database: Optional[DatabaseManager] = None
    ):
        """Initialise le service scraper.
        
        Args:
            dispatcher: Dispatcher pour soumettre les jobs Dispy
            task_queue: File de tâches
            database: Gestionnaire de base de données (optionnel)
        """
        super().__init__(
            service_name="scraper",
            dispatcher=dispatcher,
            task_queue=task_queue
        )
        
        self.database = database or DatabaseManager(db_type="sqlite", db_path="web/data/cluster.db")
    
    def validate_job_data(self, job_data: Dict[str, Any]) -> tuple[bool, Optional[str]]:
        """Valide les données d'un job de scraping.
        
        Args:
            job_data: Données du job
            
        Returns:
            Tuple (is_valid, error_message)
        """
        # URL obligatoire
        if "url" not in job_data or not job_data["url"]:
            return False, "URL requise"
        
        url = job_data["url"]
        if not isinstance(url, str) or not url.startswith(("http://", "https://")):
            return False, "URL invalide (doit commencer par http:// ou https://)"
        
        # max_pages optionnel mais doit être positif
        max_pages = job_data.get("max_pages", 10)
        if not isinstance(max_pages, int) or max_pages < 1:
            return False, "max_pages doit être un entier positif"
        
        if max_pages > 1000:
            return False, "max_pages ne peut pas dépasser 1000"
        
        # timeout optionnel
        timeout = job_data.get("timeout_s", 10)
        if not isinstance(timeout, (int, float)) or timeout < 1:
            return False, "timeout_s doit être >= 1"
        
        return True, None
    
    async def process_job(self, job_data: Dict[str, Any]) -> Dict[str, Any]:
        """Traitement d'un job de scraping (appelé par le worker Dispy).
        
        Args:
            job_data: Données du job
            
        Returns:
            Résultat du scraping
        """
        job_id = job_data.get("job_id")
        url = job_data.get("url")
        max_pages = job_data.get("max_pages", 10)
        timeout_s = job_data.get("timeout_s", 10)
        same_origin_only = job_data.get("same_origin_only", True)
        
        logger.info(f"Traitement du job scraping {job_id} pour {url}")
        
        try:
            # Importer la fonction de scraping du worker
            # Le worker scraping sera exécuté sur un nœud du cluster
            from workers.scraper_worker import scrape_site
            
            # Exécuter le scraping
            result = scrape_site(
                start_url=url,
                max_pages=max_pages,
                same_origin_only=same_origin_only,
                timeout_s=timeout_s
            )
            
            # Enregistrer dans la base de données
            if self.database and job_id:
                await self._save_results(job_id, result)
            
            # Émettre un événement de progression
            await self._publish_job_event("job_progress", {
                "job_id": job_id,
                "progress": 100,
                "urls_crawled": len(result.get("crawled", [])),
                "status": "completed"
            })
            
            self.record_job_result(success=True)
            
            return {
                "success": True,
                "job_id": job_id,
                "result": result,
                "timestamp": datetime.now().isoformat()
            }
            
        except Exception as e:
            logger.error(f"Erreur lors du scraping {job_id}: {e}")
            
            # Émettre un événement d'erreur
            await self._publish_job_event("job_failed", {
                "job_id": job_id,
                "error": str(e),
                "status": "failed"
            })
            
            self.record_job_result(success=False)
            
            return {
                "success": False,
                "job_id": job_id,
                "error": str(e),
                "timestamp": datetime.now().isoformat()
            }
    
    async def submit_scrape_job(
        self,
        url: str,
        max_pages: int = 10,
        timeout_s: int = 10,
        same_origin_only: bool = True,
        priority: int = 1
    ) -> Dict[str, Any]:
        """Soumet un job de scraping.
        
        Args:
            url: URL à scraper
            max_pages: Nombre maximum de pages
            timeout_s: Timeout par requête
            same_origin_only: Limiter au même domaine
            priority: Priorité du job (1-10)
            
        Returns:
            Résultat de la soumission
        """
        job_data = {
            "url": url,
            "max_pages": max_pages,
            "timeout_s": timeout_s,
            "same_origin_only": same_origin_only
        }
        
        # Soumettre via la méthode de base
        result = await self.submit_job(
            job_data=job_data,
            priority=priority,
            requires=["scraping"]  # Capacité requise
        )
        
        # Enregistrer dans la DB
        if result.get("success") and self.database:
            await self._save_job_to_db(result["job_id"], job_data)
        
        return result
    
    async def _save_job_to_db(self, job_id: str, job_data: Dict[str, Any]) -> None:
        """Enregistre un job dans la base de données.
        
        Args:
            job_id: ID du job
            job_data: Données du job
        """
        try:
            self.database.execute("""
                INSERT OR REPLACE INTO scraper_jobs 
                (id, job_id, url, max_pages, status, created_at)
                VALUES (?, ?, ?, ?, ?, ?)
            """, (
                job_id,
                job_id,
                job_data["url"],
                job_data.get("max_pages", 10),
                "pending",
                datetime.now().isoformat()
            ))
        except Exception as e:
            logger.warning(f"Impossible d'enregistrer le job {job_id} en DB: {e}")
    
    async def _save_results(self, job_id: str, result: Dict[str, Any]) -> None:
        """Enregistre les résultats d'un scraping dans la DB.
        
        Args:
            job_id: ID du job
            result: Résultats du scraping
        """
        try:
            crawled = result.get("crawled", [])
            pii_by_url = result.get("pii_by_url", {})
            errors = result.get("errors", {})
            
            # Mettre à jour le statut du job
            self.database.execute("""
                UPDATE scraper_jobs 
                SET status = ?, completed_at = ?, result = ?
                WHERE job_id = ?
            """, (
                "completed",
                datetime.now().isoformat(),
                json.dumps(result),
                job_id
            ))
            
            # Enregistrer les résultats par URL
            for url in crawled:
                pii = pii_by_url.get(url, {})
                emails = json.dumps(pii.get("emails", []))
                phones = json.dumps(pii.get("phones", []))
                
                self.database.execute("""
                    INSERT INTO scraper_results 
                    (job_id, url, emails, phones, links_count, crawled_at)
                    VALUES (?, ?, ?, ?, ?, ?)
                """, (
                    job_id,
                    url,
                    emails,
                    phones,
                    0,  # TODO: compter les liens
                    datetime.now().isoformat()
                ))
            
            # Enregistrer les erreurs
            for url, error_msg in errors.items():
                self.database.execute("""
                    INSERT INTO scraper_results 
                    (job_id, url, error, crawled_at)
                    VALUES (?, ?, ?, ?)
                """, (
                    job_id,
                    url,
                    error_msg,
                    datetime.now().isoformat()
                ))
                
        except Exception as e:
            logger.warning(f"Impossible d'enregistrer les résultats {job_id}: {e}")
    
    async def get_scrape_history(
        self,
        limit: int = 50,
        status: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """Récupère l'historique des scrapings.
        
        Args:
            limit: Nombre maximum de résultats
            status: Filtrer par statut
            
        Returns:
            Liste des jobs
        """
        try:
            if status:
                jobs = self.database.fetch_all("""
                    SELECT * FROM scraper_jobs 
                    WHERE status = ?
                    ORDER BY created_at DESC
                    LIMIT ?
                """, (status, limit))
            else:
                jobs = self.database.fetch_all("""
                    SELECT * FROM scraper_jobs 
                    ORDER BY created_at DESC
                    LIMIT ?
                """, (limit,))
            
            # Formater les résultats
            formatted = []
            for job in jobs:
                result_data = None
                if job.get("result"):
                    try:
                        result_data = json.loads(job["result"])
                    except:
                        pass
                
                formatted.append({
                    "job_id": job["job_id"],
                    "url": job["url"],
                    "max_pages": job["max_pages"],
                    "status": job["status"],
                    "progress": job.get("progress", 0),
                    "assigned_node": job.get("assigned_node"),
                    "created_at": job["created_at"],
                    "started_at": job.get("started_at"),
                    "completed_at": job.get("completed_at"),
                    "result": result_data,
                    "error": job.get("error")
                })
            
            return formatted
            
        except Exception as e:
            logger.error(f"Erreur lors de la récupération de l'historique: {e}")
            return []
    
    async def get_scrape_results(self, job_id: str) -> Dict[str, Any]:
        """Récupère les résultats détaillés d'un scraping.
        
        Args:
            job_id: ID du job
            
        Returns:
            Résultats détaillés
        """
        try:
            # Job principal
            job = self.database.fetch_one("""
                SELECT * FROM scraper_jobs WHERE job_id = ?
            """, (job_id,))
            
            if not job:
                return {"error": "Job non trouvé"}
            
            # Résultats par URL
            results = self.database.fetch_all("""
                SELECT * FROM scraper_results 
                WHERE job_id = ?
                ORDER BY crawled_at DESC
            """, (job_id,))
            
            formatted_results = []
            for r in results:
                emails = []
                phones = []
                
                if r.get("emails"):
                    try:
                        emails = json.loads(r["emails"])
                    except:
                        pass
                
                if r.get("phones"):
                    try:
                        phones = json.loads(r["phones"])
                    except:
                        pass
                
                formatted_results.append({
                    "url": r["url"],
                    "emails": emails,
                    "phones": phones,
                    "links_count": r.get("links_count", 0),
                    "error": r.get("error"),
                    "crawled_at": r["crawled_at"]
                })
            
            result_data = None
            if job.get("result"):
                try:
                    result_data = json.loads(job["result"])
                except:
                    pass
            
            return {
                "job_id": job_id,
                "url": job["url"],
                "status": job["status"],
                "max_pages": job["max_pages"],
                "progress": job.get("progress", 0),
                "created_at": job["created_at"],
                "started_at": job.get("started_at"),
                "completed_at": job.get("completed_at"),
                "result": result_data,
                "results_by_url": formatted_results,
                "total_urls_crawled": len(formatted_results)
            }
            
        except Exception as e:
            logger.error(f"Erreur lors de la récupération des résultats {job_id}: {e}")
            return {"error": str(e)}

