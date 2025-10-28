# DispyCluster

Cluster de calcul distribué basé sur Dispy pour Raspberry Pi avec services avancés de scraping et monitoring.

## Vue d'ensemble

DispyCluster est un système complet pour orchestrer des tâches de scraping sur un cluster de Raspberry Pi. Il combine la puissance de Dispy avec des services modernes de contrôle, monitoring et planification.

### Fonctionnalités principales

- **Cluster distribué** : Orchestration de tâches sur plusieurs Raspberry Pi
- **Scraping intelligent** : Distribution automatique des tâches de scraping
- **Monitoring en temps réel** : Surveillance des performances et santé du cluster
- **Planification avancée** : Tâches récurrentes et workflows complexes
- **API unifiée** : Interface REST pour tous les services
- **Tableau de bord** : Visualisation des métriques et statuts

## Architecture

```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   API Gateway   │    │ Cluster Control │    │   Monitoring   │
│   (Port 8084)   │◄──►│   (Port 8081)   │◄──►│   (Port 8082)   │
└─────────────────┘    └─────────────────┘    └─────────────────┘
         │                       │                       │
         │                       │                       │
         ▼                       ▼                       ▼
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   Scheduler     │    │   Dispy Master  │    │   Prometheus    │
│   (Port 8083)   │    │   (Port 51347)  │    │   (Port 9090)   │
└─────────────────┘    └─────────────────┘    └─────────────────┘
         │                       │                       │
         │                       │                       │
         ▼                       ▼                       ▼
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   Workers       │    │   Workers       │    │     Grafana     │
│  (node6-14.lan) │    │  (node6-14.lan) │    │   (Port 3000)   │
└─────────────────┘    └─────────────────┘    └─────────────────┘
```

## Installation rapide

### Prérequis

- Raspberry Pi OS récent sur chaque nœud
- Accès SSH depuis le maître vers chaque worker
- Docker et Docker Compose sur le maître

### Installation du cluster de base

1. **Configurer l'inventaire** :
```bash
# Éditer la liste des nœuds
nano inventory/nodes.yaml
```

2. **Installer les workers** :
```bash
# Sur chaque Raspberry Pi worker
sudo bash scripts/install_node.sh
```

3. **Installer le maître** :
```bash
# Sur le nœud maître
sudo bash scripts/install_master.sh
```

4. **Installer les services avancés** :
```bash
# Sur le nœud maître
sudo bash scripts/install_services.sh
```

5. **Démarrer le monitoring** :
```bash
cd monitoring
docker compose up -d
```

## Services

### API Gateway (Port 8084)
Point d'entrée unifié pour tous les services.

**Endpoints principaux :**
- `GET /` - Informations sur l'API
- `GET /health` - Santé de tous les services
- `GET /overview` - Vue d'ensemble du cluster
- `GET /dashboard` - Données pour tableau de bord
- `POST /scrape` - Scraping rapide
- `POST /scrape/batch` - Scraping en lot

### Cluster Controller (Port 8081)
Gestion centralisée du cluster et des jobs.

**Fonctionnalités :**
- Gestion des workers
- File de jobs avec priorités
- Distribution automatique des tâches
- Surveillance des performances

### Monitoring Service (Port 8082)
Surveillance en temps réel du cluster.

**Fonctionnalités :**
- Collecte automatique des métriques
- Surveillance de la santé des nœuds
- Détection d'alertes
- Rapports de performance

### Scheduler Service (Port 8083)
Planification et automatisation des tâches.

**Fonctionnalités :**
- Tâches planifiées (cron, intervalle, ponctuel)
- Workflows complexes
- Gestion des dépendances
- Historique des exécutions

## Utilisation

### Scraping simple

```bash
# Scraping d'un site
curl -X POST http://localhost:8084/scrape \
  -H "Content-Type: application/json" \
  -d '{"start_url": "https://example.com", "max_pages": 10}'
```

### Scraping en lot

```bash
# Scraping de plusieurs sites
curl -X POST http://localhost:8084/scrape/batch \
  -H "Content-Type: application/json" \
  -d '{
    "urls": ["https://site1.com", "https://site2.com"],
    "max_pages": 5,
    "priority": 3
  }'
```

### Tâche planifiée

```bash
# Tâche quotidienne à 6h du matin
curl -X POST http://localhost:8083/tasks \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Scraping quotidien",
    "urls": ["https://news.com"],
    "schedule_type": "cron",
    "schedule_config": {"cron": "0 6 * * *"}
  }'
```

### Workflow complexe

```python
import requests

# Créer un workflow avec étapes séquentielles
workflow_steps = [
    {
        "step_id": "step1",
        "name": "Scraping initial",
        "action": "scrape",
        "config": {"urls": ["https://site1.com"], "max_pages": 5}
    },
    {
        "step_id": "step2",
        "name": "Attente",
        "action": "wait",
        "config": {"seconds": 60},
        "depends_on": ["step1"]
    },
    {
        "step_id": "step3",
        "name": "Scraping final",
        "action": "scrape",
        "config": {"urls": ["https://site2.com"], "max_pages": 10},
        "depends_on": ["step2"]
    }
]

response = requests.post("http://localhost:8083/workflows", json={
    "name": "Workflow complexe",
    "steps": workflow_steps,
    "schedule_type": "interval",
    "schedule_config": {"seconds": 3600}
})
```

## Monitoring

### Tableau de bord

Accédez au tableau de bord via l'API Gateway :
```bash
curl http://localhost:8084/dashboard | jq
```

### Métriques Prometheus

- Prometheus : `http://<ip_maitre>:9090`
- Grafana : `http://<ip_maitre>:3000` (admin/admin)

### Surveillance des performances

```bash
# Rapport de performance sur 24h
curl http://localhost:8082/performance?hours=24

# Alertes actives
curl http://localhost:8082/alerts

# Santé du cluster
curl http://localhost:8082/cluster/health
```

## Gestion des services

### Démarrage/arrêt

```bash
# Démarrer tous les services
sudo /opt/dispycluster/start_services.sh

# Arrêter tous les services
sudo /opt/dispycluster/stop_services.sh

# Vérifier le statut
sudo /opt/dispycluster/check_services.sh
```

### Logs

```bash
# Logs du contrôleur
journalctl -u dispycluster-controller -f

# Logs du monitoring
journalctl -u dispycluster-monitoring -f

# Logs du planificateur
journalctl -u dispycluster-scheduler -f

# Logs de l'API Gateway
journalctl -u dispycluster-gateway -f
```

### Tests

```bash
# Test complet des services
sudo bash scripts/test_services.sh

# Exemples d'utilisation
python3 examples/cluster_usage_examples.py
```

## Configuration

### Fichiers de configuration

- `config/services_config.py` - Configuration centralisée
- `inventory/nodes.yaml` - Liste des nœuds du cluster
- `monitoring/docker-compose.yml` - Configuration Prometheus/Grafana

### Variables d'environnement

```bash
# Environnement (development, staging, production)
export DISPYCLUSTER_ENV=development

# Configuration personnalisée
export DISPYCLUSTER_LOG_LEVEL=INFO
export DISPYCLUSTER_MAX_WORKERS=10
```

## Structure du projet

```
DispyCluster/
├── docs/                          # Documentation
│   ├── README_ORIGINAL.md        # README original
│   ├── SERVICES_README.md         # Documentation des services
│   └── ARCHITECTURE.md            # Architecture du système
├── services/                      # Services avancés
│   ├── cluster_controller.py      # Contrôleur du cluster
│   ├── monitoring_service.py     # Service de monitoring
│   ├── scheduler_service.py      # Planificateur
│   ├── api_gateway.py            # API Gateway
│   └── scraper_service.py        # Service de scraping
├── config/                        # Configuration
│   └── services_config.py         # Configuration centralisée
├── scripts/                       # Scripts d'installation
│   ├── install_services.sh        # Installation des services
│   └── test_services.sh           # Tests des services
├── examples/                      # Exemples d'utilisation
│   └── cluster_usage_examples.py  # Exemples complets
├── core/                          # Cœur du cluster Dispy
├── workers/                       # Workers d'exemple
├── monitoring/                    # Configuration Prometheus/Grafana
└── inventory/                     # Inventaire des nœuds
```

## Dépannage

### Services non accessibles

1. Vérifier que les services sont démarrés :
```bash
sudo systemctl status dispycluster-*
```

2. Vérifier les ports :
```bash
sudo netstat -tlnp | grep -E "808[0-4]"
```

3. Vérifier les logs :
```bash
journalctl -u dispycluster-controller --since "1 hour ago"
```

### Workers non détectés

1. Vérifier la connectivité réseau :
```bash
ping node6.lan
```

2. Vérifier les services sur les workers :
```bash
curl http://node6.lan:8080/health
```

3. Ping via l'API :
```bash
curl -X POST http://localhost:8081/workers/node6.lan/ping
```

## Documentation

Toute la documentation a été regroupée dans `docs/`. Commence ici:

- `docs/README.md` - Sommaire et liens rapides
- `docs/QUICK_START.md` - Démarrage rapide
- `docs/TROUBLESHOOTING.md` - Dépannage
- `docs/ARCHITECTURE.md` - Architecture
- `docs/SERVICES_README.md` - Services
- `docs/README_ORIGINAL.md` - README original

## Support

Pour signaler des problèmes ou proposer des améliorations, consultez les logs des services et utilisez les outils de diagnostic fournis.

Les services sont conçus pour être modulaires et extensibles. Chaque service peut être modifié indépendamment sans affecter les autres.