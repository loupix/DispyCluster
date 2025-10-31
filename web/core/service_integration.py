"""Module d'intégration pour connecter les services avec l'API Gateway et le Cluster Controller.

Permet au service scraper de fonctionner avec l'architecture existante.
"""

from typing import Dict, List, Any, Optional
import httpx
import asyncio
from web.config.logging_config import get_logger

logger = get_logger(__name__)

# Configuration des services
SERVICE_URLS = {
    "api_gateway": "http://localhost:8084",
    "cluster_controller": "http://localhost:8081",
    "monitoring": "http://localhost:8082",
    "scheduler": "http://localhost:8083"
}


class ServiceIntegration:
    """Gestionnaire d'intégration avec les services externes."""
    
    def __init__(self):
        self.service_urls = SERVICE_URLS
    
    async def check_service_health(self, service_name: str) -> Dict[str, Any]:
        """Vérifie la santé d'un service.
        
        Args:
            service_name: Nom du service
            
        Returns:
            Statut du service
        """
        url = self.service_urls.get(service_name)
        if not url:
            return {"status": "unknown", "error": f"Service {service_name} non configuré"}
        
        try:
            async with httpx.AsyncClient(timeout=5.0) as client:
                response = await client.get(f"{url}/health")
                if response.status_code == 200:
                    return {"status": "online", "data": response.json()}
                else:
                    return {"status": "offline", "error": f"HTTP {response.status_code}"}
        except Exception as e:
            logger.warning(f"Service {service_name} indisponible: {e}")
            return {"status": "offline", "error": str(e)}
    
    async def route_to_api_gateway(
        self,
        path: str,
        method: str = "GET",
        data: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """Route une requête via l'API Gateway.
        
        Args:
            path: Chemin de l'endpoint
            method: Méthode HTTP
            data: Données à envoyer (pour POST/PUT)
            
        Returns:
            Réponse du service
        """
        gateway_url = self.service_urls.get("api_gateway")
        if not gateway_url:
            raise ValueError("API Gateway non configuré")
        
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                url = f"{gateway_url}/{path.lstrip('/')}"
                
                if method == "GET":
                    response = await client.get(url)
                elif method == "POST":
                    response = await client.post(url, json=data)
                elif method == "PUT":
                    response = await client.put(url, json=data)
                elif method == "DELETE":
                    response = await client.delete(url)
                else:
                    raise ValueError(f"Méthode {method} non supportée")
                
                if response.status_code >= 400:
                    return {
                        "success": False,
                        "error": response.text,
                        "status_code": response.status_code
                    }
                
                return {
                    "success": True,
                    "data": response.json() if response.headers.get("content-type", "").startswith("application/json") else response.text
                }
                
        except Exception as e:
            logger.error(f"Erreur routage API Gateway: {e}")
            return {
                "success": False,
                "error": str(e)
            }
    
    async def submit_job_to_controller(
        self,
        job_data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Soumet un job au Cluster Controller.
        
        Args:
            job_data: Données du job
            
        Returns:
            Résultat de la soumission
        """
        controller_url = self.service_urls.get("cluster_controller")
        if not controller_url:
            raise ValueError("Cluster Controller non configuré")
        
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                # Adapter le format pour le Cluster Controller
                controller_payload = {
                    "start_url": job_data.get("url"),
                    "max_pages": job_data.get("max_pages", 10),
                    "same_origin_only": job_data.get("same_origin_only", True),
                    "timeout_s": job_data.get("timeout_s", 10),
                    "priority": job_data.get("priority", 1)
                }
                
                response = await client.post(
                    f"{controller_url}/scrape",
                    json=controller_payload
                )
                
                if response.status_code >= 400:
                    return {
                        "success": False,
                        "error": response.text,
                        "status_code": response.status_code
                    }
                
                return {
                    "success": True,
                    "data": response.json()
                }
                
        except Exception as e:
            logger.error(f"Erreur soumission Cluster Controller: {e}")
            return {
                "success": False,
                "error": str(e)
            }
    
    async def get_cluster_stats_from_controller(self) -> Dict[str, Any]:
        """Récupère les stats du cluster depuis le Controller.
        
        Returns:
            Statistiques du cluster
        """
        try:
            result = await self.route_to_api_gateway("cluster", method="GET")
            if result.get("success"):
                return result.get("data", {})
            else:
                return {"error": result.get("error", "Erreur inconnue")}
        except Exception as e:
            logger.error(f"Erreur récupération stats cluster: {e}")
            return {"error": str(e)}


class ScraperServiceAdapter:
    """Adaptateur pour intégrer le service scraper avec l'API Gateway."""
    
    def __init__(self, scraper_service):
        """Initialise l'adaptateur.
        
        Args:
            scraper_service: Instance du ScraperService
        """
        self.scraper_service = scraper_service
        self.integration = ServiceIntegration()
    
    async def submit_via_gateway(
        self,
        url: str,
        max_pages: int = 10,
        timeout_s: int = 10,
        same_origin_only: bool = True,
        priority: int = 1
    ) -> Dict[str, Any]:
        """Soumet un scraping via l'API Gateway (qui route vers notre service).
        
        Args:
            url: URL à scraper
            max_pages: Nombre maximum de pages
            timeout_s: Timeout
            same_origin_only: Limiter au même domaine
            priority: Priorité
            
        Returns:
            Résultat avec indication si c'est via Gateway ou direct
        """
        # Vérifier si l'API Gateway est disponible
        gateway_health = await self.integration.check_service_health("api_gateway")
        
        if gateway_health.get("status") == "online":
            # Router via l'API Gateway
            try:
                result = await self.integration.route_to_api_gateway(
                    "scrapers/submit",
                    method="POST",
                    data={
                        "url": url,
                        "max_pages": max_pages,
                        "timeout_s": timeout_s,
                        "same_origin_only": same_origin_only,
                        "priority": priority
                    }
                )
                
                if result.get("success"):
                    return {
                        **result.get("data", {}),
                        "via_gateway": True
                    }
            except Exception as e:
                logger.warning(f"Erreur via Gateway, fallback direct: {e}")
        
        # Fallback: soumission directe
        result = await self.scraper_service.submit_scrape_job(
            url=url,
            max_pages=max_pages,
            timeout_s=timeout_s,
            same_origin_only=same_origin_only,
            priority=priority
        )
        
        return {
            **result,
            "via_gateway": False
        }

