DispyCluster
============

Projet pour orchestrer un mini cluster Dispy sur des Raspberry Pi (Raspberry Pi 3B+) nommés de `node6.lan` à `node14.lan`, avec un noeud maître qui héberge Prometheus et Grafana pour le monitoring.

Contenu
-------
- `inventory/nodes.yaml` liste des noeuds RPi
- `scripts/` scripts d'installation et utilitaires
- `systemd/` services pour lancer Dispy en maître et en worker
- `monitoring/` Prometheus + Grafana (docker-compose) et config
- `core/` coeur du cluster (discovery, load balancing, tolérance aux pannes, registry, dispatcher)
- `workers/` workers d'exemple (whisper, image, cpu, gpu)
- `config/` templates de configuration
- `examples/` client d'exemple `submit_jobs.py`

Prérequis
---------
- Un Raspberry Pi OS récent (Lite recommandé) sur chaque RPi
- Accès SSH depuis le maître vers chaque noeud
- Le maître doit avoir Docker et Docker Compose (installé par `scripts/install_master.sh`)

Déploiement rapide
------------------
1. Éditer `inventory/nodes.yaml` pour confirmer la liste des hôtes
2. Sur chaque RPi worker: copier et exécuter `scripts/install_node.sh`
3. Sur le maître: exécuter `scripts/install_master.sh`
4. Démarrer les services systemd côté maître et workers
5. Lancer le monitoring: se placer dans `monitoring/` puis `docker compose up -d`

Architecture avancée (optionnel)
--------------------------------
- Registre: `core/worker_registry.py`
- File de tâches: `core/task_queue.py`
- Dispatcher: `core/dispatcher.py` (utilise `load_balancer` + `fault_tolerance`)
- Workers d'exemples: `workers/*.py`
- Client: `examples/submit_jobs.py`

Monitoring
----------
- Prometheus: `http://<ip_maitre>:9090`
- Grafana: `http://<ip_maitre>:3000` (admin / admin au premier démarrage)

Healthcheck
-----------
`scripts/healthcheck.sh` permet de vérifier rapidement la disponibilité SSH et le port node_exporter des noeuds.

Notes
-----
- Les services s'appuient sur les binaires `dispyscheduler` et `dispynode` installés via pip. Ils se trouvent généralement dans `/usr/local/bin/`.
- Adaptez les interfaces réseau et ports selon votre LAN si nécessaire.

Service web de scraping (optionnel)
-----------------------------------
Un petit service FastAPI est fourni pour déclencher un crawl depuis un worker:

- Fichier: `services/scraper_service.py`
- Endpoints:
  - `GET /health`
  - `POST /scrape` avec corps JSON:
    ```json
    {
      "start_url": "https://example.com",
      "max_pages": 10,
      "same_origin_only": true,
      "timeout_s": 10
    }
    ```

Prérequis Python pour le service:

```bash
pip install fastapi uvicorn requests pydantic
```

Démarrage local du service:

```bash
cd DispyCluster
python -m uvicorn services.scraper_service:app --host 0.0.0.0 --port 8080
```

Test rapide:

```bash
curl -X POST http://localhost:8080/scrape \
  -H "Content-Type: application/json" \
  -d '{"start_url": "https://example.com", "max_pages": 5}'
```

Pour un déploiement persistant sur un RPi, créez un service systemd ou utilisez tmux/screen pour garder le process actif.

