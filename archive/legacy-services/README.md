# Services Legacy - Archivés

Ces services ont été remplacés par une architecture modulaire intégrée dans `web/app.py`.

## Date d'archivage

Tag git : `archive/legacy-services-before-removal`
Date : 2024

## Services archivés

- `cluster_controller.py` : Remplacé par `web/core/cluster_manager.py` et `web/core/dispatcher.py`
- `monitoring_service.py` : Remplacé par `web/api/monitoring.py` et `web/views/monitoring_view.py`
- `scheduler_service.py` : Intégration prévue dans `web/services/` (architecture modulaire)
- `scraper_service.py` : Remplacé par `web/services/scraper_service.py` (BaseService)

## Migration

L'API Gateway (`legacy/services/api_gateway.py`) a été conservé et mis à jour pour router vers les nouveaux services intégrés.

## Architecture actuelle

Les nouveaux services héritent de `BaseService` (`web/core/base_service.py`) et sont intégrés directement dans `web/app.py` :

- Service scraper : `web/services/scraper_service.py`
- Architecture modulaire : `web/core/base_service.py`
- Abstraction DB : `web/core/database.py`

## Récupération

Pour restaurer ces services :

```bash
git checkout archive/legacy-services-before-removal
```

Ou copier les fichiers depuis ce dossier d'archive.

