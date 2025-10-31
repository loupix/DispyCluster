# Architecture des Services DispyCluster

Cette architecture modulaire permet de créer facilement de nouveaux services distribués sur le cluster Dispy.

## Structure

```
web/
├── core/
│   ├── base_service.py      # Classe abstraite de base
│   ├── database.py          # Abstraction DB (SQLite/Postgres)
│   ├── dispatcher.py        # Intégration Dispy
│   └── websocket_manager.py # Événements temps réel
├── services/
│   ├── scraper_service.py   # Service de scraping (exemple)
│   └── README.md           # Ce fichier
└── api/
    └── scrapers.py          # Endpoints API pour le front
```

## BaseService

Tous les services héritent de `BaseService` qui fournit:

- **Soumission de jobs** via Dispy cluster
- **Validation** des données de job
- **Statistiques** automatiques (succès/échecs)
- **Événements Redis/WebSocket** pour le temps réel
- **Gestion de la file** de tâches
- **Annulation** de jobs

### Exemple d'utilisation

```python
from web.services.scraper_service import ScraperService
from web.core.dispatcher import Dispatcher
from web.core.task_queue import TaskQueue

# Initialiser le service
service = ScraperService(
    dispatcher=dispatcher,
    task_queue=task_queue
)

# Soumettre un job
result = await service.submit_scrape_job(
    url="https://example.com",
    max_pages=10
)

# Consulter le statut
status = await service.get_job_status(result["job_id"])
```

## Base de données

Abstraction multi-adaptateurs:

- **SQLite** pour le développement local (défaut)
- **PostgreSQL** pour la production (à implémenter)

Le `DatabaseManager` permet de basculer entre les deux sans changer le code métier.

### Schéma actuel

**scraper_jobs**: Jobs de scraping
- `id`, `job_id`, `url`, `max_pages`, `status`, `result`, etc.

**scraper_results**: Résultats par URL
- `job_id`, `url`, `emails`, `phones`, `links_count`, `error`

## Intégration Dispy

Les jobs sont distribués automatiquement sur le cluster via:

1. **TaskQueue**: File de tâches partagée
2. **Dispatcher**: Sélectionne le meilleur nœud
3. **Dispy JobCluster**: Exécute sur les workers

Les workers doivent être disponibles dans `workers/scraper_worker.py` ou similaires.

## WebSocket / Redis Events

Les événements sont diffusés en temps réel via Redis pub/sub:

- `scraper:events`: Événements spécifiques au scraper
- `cluster:events`: Événements globaux

Le front reçoit automatiquement:
- `service_job_submitted`
- `service_job_progress`
- `service_job_completed`
- `service_job_failed`
- `scraper_job_*` (compatibilité)

## API Endpoints

### POST /api/scrapers/submit
Soumet un nouveau job de scraping.

**Body:**
```json
{
  "url": "https://example.com",
  "max_pages": 10,
  "timeout_s": 10,
  "same_origin_only": true,
  "priority": 1
}
```

### GET /api/scrapers/jobs/{job_id}
Récupère le statut d'un job.

### GET /api/scrapers/jobs
Liste tous les jobs (filtrable par statut).

### GET /api/scrapers/history
Historique depuis la DB.

### GET /api/scrapers/jobs/{job_id}/results
Résultats détaillés d'un scraping.

### DELETE /api/scrapers/jobs/{job_id}
Annule un job en cours.

### GET /api/scrapers/stats
Statistiques du service.

## Créer un nouveau service

1. Créer `web/services/mon_service.py`:

```python
from web.core.base_service import BaseService

class MonService(BaseService):
    def __init__(self, dispatcher, task_queue):
        super().__init__("mon_service", dispatcher, task_queue)
    
    def validate_job_data(self, job_data):
        # Validation spécifique
        return True, None
    
    async def process_job(self, job_data):
        # Traitement spécifique
        return {"success": True}
```

2. Créer `web/api/mon_service.py` avec les endpoints

3. Intégrer dans `web/app.py`:

```python
from web.services.mon_service import MonService

mon_service = MonService(
    dispatcher=cluster_view.dispatcher,
    task_queue=cluster_view.task_queue
)

app.include_router(mon_service_router)
```

4. Ajouter les événements Redis dans le WebSocket manager si besoin

## Notes

- Les services utilisent la même file de tâches et dispatcher
- La DB est partagée mais chaque service peut avoir ses propres tables
- Les événements Redis sont isolés par canal (`service_name:events`)
- L'intégration Dispy est automatique via le dispatcher existant

