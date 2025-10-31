# Intégration du Service Scraper avec API Gateway et Cluster Controller

## Architecture

Le service scraper est intégré dans `web/app.py` et peut être utilisé de deux façons :

1. **Directement** : via les endpoints `/api/scrapers/*`
2. **Via l'API Gateway** : via les endpoints `/scrapers/*` ou `/scrape` sur le port 8084

## Routes API Gateway

### Nouveau service scraper (recommandé)

- `POST /scrapers/submit` → route vers `/api/scrapers/submit`
- `GET /scrapers/jobs/{job_id}` → route vers `/api/scrapers/jobs/{job_id}`
- `GET /scrapers/jobs` → route vers `/api/scrapers/jobs`
- `GET /scrapers/history` → route vers `/api/scrapers/history`
- `GET /scrapers/jobs/{job_id}/results` → route vers `/api/scrapers/jobs/{job_id}/results`
- `DELETE /scrapers/jobs/{job_id}` → route vers `/api/scrapers/jobs/{job_id}`
- `GET /scrapers/stats` → route vers `/api/scrapers/stats`

### Endpoints de convenance

- `POST /scrape` : Route vers le service scraper
- `POST /scrape/batch` : Scraping en lot via le service scraper


## Utilisation

### Via API Gateway (port 8084)

```bash
# Soumettre un scraping
curl -X POST http://localhost:8084/scrapers/submit \
  -H "Content-Type: application/json" \
  -d '{
    "url": "https://example.com",
    "max_pages": 10,
    "timeout_s": 10,
    "same_origin_only": true,
    "priority": 1
  }'

# Ou via l'endpoint de convenance
curl -X POST http://localhost:8084/scrape \
  -H "Content-Type: application/json" \
  -d '{
    "start_url": "https://example.com",
    "max_pages": 10
  }'

# Consulter les stats
curl http://localhost:8084/scrapers/stats

# Lister les jobs
curl http://localhost:8084/scrapers/jobs
```

### Directement (port 8085)

```bash
# Soumettre un scraping
curl -X POST http://localhost:8085/api/scrapers/submit \
  -H "Content-Type: application/json" \
  -d '{
    "url": "https://example.com",
    "max_pages": 10
  }'
```

## Architecture

Le service scraper est maintenant le seul service de scraping disponible. Il est intégré dans `web/app.py` (port 8085) et accessible via l'API Gateway (port 8084).

## Service Integration Module

Le module `web/core/service_integration.py` fournit :

- `ServiceIntegration` : Gestionnaire d'intégration avec les services externes
  - `check_service_health()` : Vérifie la santé d'un service
  - `route_to_api_gateway()` : Route une requête via l'API Gateway
  - `submit_job_to_controller()` : Soumet un job au Cluster Controller
  - `get_cluster_stats_from_controller()` : Récupère les stats du cluster

- `ScraperServiceAdapter` : Adaptateur pour intégrer le service scraper avec l'API Gateway
  - `submit_via_gateway()` : Soumet un scraping via l'API Gateway avec fallback direct

## Configuration

Les URLs des services sont configurées dans :

- `legacy/services/api_gateway.py` : `SERVICES` dict
- `web/core/service_integration.py` : `SERVICE_URLS` dict

Par défaut :
- API Gateway : `http://localhost:8084`
- Cluster Controller : `http://localhost:8081`
- Nouveau service scraper : `http://localhost:8085` (web/app)

## Notes

- L'API Gateway route vers le service scraper intégré (port 8085)
- Les événements WebSocket/Redis fonctionnent en temps réel
- La base de données SQLite/Postgres stocke tous les jobs et résultats
- Le service est distribué sur le cluster Dispy automatiquement

