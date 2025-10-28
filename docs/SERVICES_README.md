# Services DispyCluster

Ce document décrit les nouveaux services créés pour améliorer la gestion et le contrôle du cluster de Raspberry Pi.

## Vue d'ensemble

Le système DispyCluster a été étendu avec plusieurs services spécialisés qui travaillent ensemble pour fournir une solution complète de scraping distribué :

- **API Gateway** (port 8084) : Point d'entrée unifié
- **Cluster Controller** (port 8081) : Gestion du cluster et des jobs
- **Monitoring Service** (port 8082) : Surveillance et métriques
- **Scheduler Service** (port 8083) : Planification des tâches
- **Scraper Service** (port 8080) : Service de scraping existant

## Installation

### Prérequis

- DispyCluster installé et fonctionnel
- Python 3.7+
- Dépendances Python installées

### Installation automatique

```bash
# Sur le nœud maître
sudo bash scripts/install_services.sh
```

### Installation manuelle

1. Installer les dépendances :
```bash
pip3 install fastapi uvicorn aiohttp httpx apscheduler requests pydantic
```

2. Copier les services :
```bash
sudo cp services/*.py /opt/dispycluster/services/
```

3. Créer les services systemd (voir `scripts/install_services.sh`)

4. Démarrer les services :
```bash
sudo systemctl start dispycluster-controller dispycluster-monitoring dispycluster-scheduler dispycluster-gateway
```

## Services détaillés

### 1. API Gateway (Port 8084)

Point d'entrée unifié pour tous les services.

**Endpoints principaux :**
- `GET /` : Informations sur l'API Gateway
- `GET /health` : Santé de tous les services
- `GET /overview` : Vue d'ensemble du cluster
- `GET /dashboard` : Données pour tableau de bord
- `POST /scrape` : Scraping rapide
- `POST /scrape/batch` : Scraping en lot

**Exemple d'utilisation :**
```bash
# Vérifier la santé
curl http://localhost:8084/health

# Scraping rapide
curl -X POST http://localhost:8084/scrape \
  -H "Content-Type: application/json" \
  -d '{"start_url": "https://example.com", "max_pages": 10}'
```

### 2. Cluster Controller (Port 8081)

Gestion centralisée du cluster et des jobs de scraping.

**Fonctionnalités :**
- Gestion des workers
- File de jobs avec priorités
- Distribution automatique des tâches
- Surveillance des performances

**Endpoints principaux :**
- `GET /cluster` : Statistiques du cluster
- `GET /workers` : Liste des workers
- `POST /workers/{node}/ping` : Ping d'un worker
- `GET /jobs` : Liste des jobs
- `POST /scrape` : Créer un job de scraping
- `POST /scrape/batch` : Créer plusieurs jobs

**Exemple d'utilisation :**
```bash
# Statistiques du cluster
curl http://localhost:8081/cluster

# Ping d'un worker
curl -X POST http://localhost:8081/workers/node6.lan/ping

# Scraping en lot
curl -X POST http://localhost:8081/scrape/batch \
  -H "Content-Type: application/json" \
  -d '{"urls": ["https://site1.com", "https://site2.com"], "max_pages": 5}'
```

### 3. Monitoring Service (Port 8082)

Surveillance en temps réel du cluster et collecte de métriques.

**Fonctionnalités :**
- Collecte automatique des métriques
- Surveillance de la santé des nœuds
- Détection d'alertes
- Rapports de performance

**Endpoints principaux :**
- `GET /cluster/health` : Santé du cluster
- `GET /nodes` : Statut des nœuds
- `GET /nodes/{node}` : Détails d'un nœud
- `GET /performance` : Rapport de performance
- `GET /alerts` : Alertes actives

**Exemple d'utilisation :**
```bash
# Santé du cluster
curl http://localhost:8082/cluster/health

# Détails d'un nœud
curl http://localhost:8082/nodes/node6.lan

# Rapport de performance
curl http://localhost:8082/performance?hours=24
```

### 4. Scheduler Service (Port 8083)

Planification et automatisation des tâches de scraping.

**Fonctionnalités :**
- Tâches planifiées (cron, intervalle, ponctuel)
- Workflows complexes
- Gestion des dépendances
- Historique des exécutions

**Endpoints principaux :**
- `POST /tasks` : Créer une tâche planifiée
- `GET /tasks` : Liste des tâches
- `POST /tasks/{id}/run` : Exécuter une tâche
- `POST /workflows` : Créer un workflow
- `GET /schedule` : Planning des tâches

**Exemple d'utilisation :**
```bash
# Créer une tâche quotidienne
curl -X POST http://localhost:8083/tasks \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Scraping quotidien",
    "urls": ["https://news.com"],
    "schedule_type": "cron",
    "schedule_config": {"cron": "0 6 * * *"}
  }'

# Exécuter une tâche immédiatement
curl -X POST http://localhost:8083/tasks/task_123/run
```

## Configuration

### Fichier de configuration

Le fichier `config/services_config.py` contient toute la configuration :

```python
# Nœuds du cluster
CLUSTER_NODES = ["node6.lan", "node7.lan", ...]

# Ports des services
SERVICE_PORTS = {
    "cluster_controller": 8081,
    "monitoring": 8082,
    "scheduler": 8083,
    "api_gateway": 8084
}

# Limites
LIMITS = {
    "max_pages_per_job": 1000,
    "max_urls_per_batch": 50,
    "max_timeout_seconds": 300
}
```

### Variables d'environnement

```bash
# Environnement (development, staging, production)
export DISPYCLUSTER_ENV=development

# Configuration personnalisée
export DISPYCLUSTER_LOG_LEVEL=INFO
export DISPYCLUSTER_MAX_WORKERS=10
```

## Utilisation avancée

### Scraping en lot avec priorités

```python
import requests

# Scraping en lot avec priorités
urls = [
    "https://site1.com",
    "https://site2.com", 
    "https://site3.com"
]

response = requests.post("http://localhost:8084/scrape/batch", json={
    "urls": urls,
    "max_pages": 10,
    "priority": 5,  # Priorité élevée
    "timeout_s": 30
})

print(f"Jobs créés: {response.json()['job_ids']}")
```

### Tâches planifiées

```python
# Tâche quotidienne à 6h du matin
response = requests.post("http://localhost:8083/tasks", json={
    "name": "Scraping quotidien",
    "urls": ["https://news.com"],
    "max_pages": 50,
    "schedule_type": "cron",
    "schedule_config": {"cron": "0 6 * * *"},
    "priority": 3
})
```

### Workflow complexe

```python
# Workflow avec étapes séquentielles
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
    "schedule_config": {"seconds": 3600}  # Toutes les heures
})
```

## Monitoring et alertes

### Tableau de bord

Accédez au tableau de bord via l'API Gateway :

```bash
curl http://localhost:8084/dashboard | jq
```

### Surveillance des performances

```bash
# Rapport de performance sur 24h
curl http://localhost:8082/performance?hours=24

# Alertes actives
curl http://localhost:8082/alerts
```

### Métriques Prometheus

Les métriques sont exposées sur le port 9090 (Prometheus existant) et peuvent être visualisées dans Grafana.

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

### Redémarrage

```bash
# Redémarrer un service spécifique
sudo systemctl restart dispycluster-controller

# Redémarrer tous les services
sudo systemctl restart dispycluster-controller dispycluster-monitoring dispycluster-scheduler dispycluster-gateway
```

## Exemples d'utilisation

### Script de test complet

```bash
# Exécuter les exemples
python3 examples/cluster_usage_examples.py
```

### Intégration avec des scripts existants

```python
# Dans vos scripts de scraping existants
import requests

def submit_scraping_job(urls, max_pages=10):
    response = requests.post("http://localhost:8084/scrape/batch", json={
        "urls": urls,
        "max_pages": max_pages,
        "priority": 1
    })
    return response.json()

# Utilisation
job_result = submit_scraping_job(["https://example.com"], max_pages=5)
print(f"Job créé: {job_result['job_ids']}")
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

### Performance dégradée

1. Vérifier les métriques :
```bash
curl http://localhost:8082/cluster/health
```

2. Analyser les performances :
```bash
curl http://localhost:8082/performance?hours=1
```

3. Vérifier les alertes :
```bash
curl http://localhost:8082/alerts
```

## Sécurité

### Configuration de production

Pour un déploiement en production :

1. Modifier `config/services_config.py` :
```python
SECURITY_CONFIG = {
    "api_key_required": True,
    "cors_origins": ["https://yourdomain.com"],
    "rate_limiting": {
        "enabled": True,
        "requests_per_minute": 100
    }
}
```

2. Configurer un reverse proxy (nginx) :
```nginx
server {
    listen 80;
    server_name your-cluster.com;
    
    location / {
        proxy_pass http://localhost:8084;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
    }
}
```

3. Activer HTTPS avec Let's Encrypt

## Support et contribution

Pour signaler des problèmes ou proposer des améliorations, consultez les logs des services et utilisez les outils de diagnostic fournis.

Les services sont conçus pour être modulaires et extensibles. Chaque service peut être modifié indépendamment sans affecter les autres.