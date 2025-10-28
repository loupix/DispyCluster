# Guide de démarrage rapide DispyCluster

Ce guide vous permet de mettre en place un cluster DispyCluster fonctionnel en moins de 30 minutes.

## 🎯 Objectif

Créer un cluster de Raspberry Pi capable de :
- Scraper des sites web de manière distribuée
- Planifier des tâches récurrentes
- Monitorer les performances en temps réel
- Gérer les workflows complexes

## 📋 Prérequis

### Matériel
- 1 Raspberry Pi maître (Raspberry Pi 3B+ ou 4)
- 3+ Raspberry Pi workers (Raspberry Pi 3B+ ou 4)
- Câbles Ethernet ou WiFi
- Carte SD (16GB minimum) pour chaque Pi

### Logiciel
- Raspberry Pi OS Lite (recommandé)
- Accès SSH depuis le maître vers chaque worker
- Docker et Docker Compose (sur le maître)

## ⚡ Installation en 5 étapes

### Étape 1 : Préparer l'inventaire (2 minutes)

Éditer le fichier `inventory/nodes.yaml` :

```yaml
# Exemple pour 3 workers
nodes:
  - host: node6.lan
    ip: 192.168.1.106
  - host: node7.lan  
    ip: 192.168.1.107
  - host: node8.lan
    ip: 192.168.1.108
```

### Étape 2 : Installer les workers (5 minutes par worker)

Sur chaque Raspberry Pi worker :

```bash
# Copier le script d'installation
scp scripts/install_node.sh pi@node6.lan:~/
scp scripts/install_node.sh pi@node7.lan:~/
scp scripts/install_node.sh pi@node8.lan:~/

# Exécuter sur chaque worker
ssh pi@node6.lan "sudo bash ~/install_node.sh"
ssh pi@node7.lan "sudo bash ~/install_node.sh"  
ssh pi@node8.lan "sudo bash ~/install_node.sh"
```

### Étape 3 : Installer le maître (5 minutes)

Sur le Raspberry Pi maître :

```bash
# Installation du cluster de base
sudo bash scripts/install_master.sh

# Installation des services avancés
sudo bash scripts/install_services.sh
```

### Étape 4 : Démarrer le monitoring (2 minutes)

```bash
# Démarrer Prometheus et Grafana
cd monitoring
docker compose up -d

# Vérifier que les conteneurs sont actifs
docker ps
```

### Étape 5 : Vérifier l'installation (3 minutes)

```bash
# Test complet des services
sudo bash scripts/test_services.sh

# Vérification manuelle
curl http://localhost:8084/health
```

## 🚀 Premier test

### Test de scraping simple

```bash
# Scraping d'un site de test
curl -X POST http://localhost:8084/scrape \
  -H "Content-Type: application/json" \
  -d '{
    "start_url": "https://httpbin.org/html",
    "max_pages": 1,
    "timeout_s": 10
  }'
```

**Résultat attendu :**
```json
{
  "message": "Job créé avec succès",
  "job_id": "job_1_1234567890",
  "status": "pending"
}
```

### Test de scraping en lot

```bash
# Scraping de plusieurs sites
curl -X POST http://localhost:8084/scrape/batch \
  -H "Content-Type: application/json" \
  -d '{
    "urls": [
      "https://httpbin.org/html",
      "https://httpbin.org/json",
      "https://httpbin.org/xml"
    ],
    "max_pages": 1,
    "priority": 2
  }'
```

### Vérifier les résultats

```bash
# Lister les jobs
curl http://localhost:8081/jobs

# Statistiques du cluster
curl http://localhost:8081/cluster

# Santé du cluster
curl http://localhost:8082/cluster/health
```

## 📊 Accéder aux interfaces

### Tableaux de bord
- **API Gateway** : http://localhost:8084
- **Prometheus** : http://localhost:9090
- **Grafana** : http://localhost:3000 (admin/admin)

### Services individuels
- **Contrôleur** : http://localhost:8081
- **Monitoring** : http://localhost:8082
- **Planificateur** : http://localhost:8083

## 🔧 Configuration de base

### Variables d'environnement

```bash
# Ajouter au ~/.bashrc
export DISPYCLUSTER_ENV=development
export DISPYCLUSTER_LOG_LEVEL=INFO
```

### Configuration des services

Éditer `config/services_config.py` si nécessaire :

```python
# Ajuster les limites selon vos besoins
LIMITS = {
    "max_pages_per_job": 100,  # Réduire pour les tests
    "max_urls_per_batch": 10,  # Réduire pour les tests
    "max_timeout_seconds": 60  # Timeout plus court
}
```

## 📅 Planifier une tâche

### Tâche quotidienne

```bash
# Scraping quotidien à 6h du matin
curl -X POST http://localhost:8083/tasks \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Scraping quotidien",
    "urls": ["https://news.com"],
    "max_pages": 10,
    "schedule_type": "cron",
    "schedule_config": {"cron": "0 6 * * *"},
    "priority": 3
  }'
```

### Tâche récurrente

```bash
# Toutes les 2 heures
curl -X POST http://localhost:8083/tasks \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Scraping récurrent",
    "urls": ["https://api.example.com/data"],
    "max_pages": 5,
    "schedule_type": "interval",
    "schedule_config": {"seconds": 7200},
    "priority": 2
  }'
```

## 🔍 Monitoring et surveillance

### Vérifier la santé du cluster

```bash
# Vue d'ensemble
curl http://localhost:8084/overview

# Détails des workers
curl http://localhost:8082/nodes

# Performance
curl http://localhost:8082/performance?hours=1
```

### Surveiller les logs

```bash
# Logs en temps réel
journalctl -u dispycluster-controller -f
journalctl -u dispycluster-monitoring -f
journalctl -u dispycluster-scheduler -f
journalctl -u dispycluster-gateway -f
```

## 🛠️ Gestion des services

### Commandes utiles

```bash
# Démarrer tous les services
sudo /opt/dispycluster/start_services.sh

# Arrêter tous les services
sudo /opt/dispycluster/stop_services.sh

# Vérifier le statut
sudo /opt/dispycluster/check_services.sh

# Redémarrer un service
sudo systemctl restart dispycluster-controller
```

### Vérification du statut

```bash
# Statut des services
sudo systemctl status dispycluster-*

# Ports ouverts
sudo netstat -tlnp | grep -E "808[0-4]"

# Test de connectivité
curl http://localhost:8084/health
```

## 🚨 Dépannage rapide

### Services non accessibles

```bash
# Vérifier les services systemd
sudo systemctl status dispycluster-*

# Redémarrer si nécessaire
sudo systemctl restart dispycluster-controller dispycluster-monitoring dispycluster-scheduler dispycluster-gateway
```

### Workers non détectés

```bash
# Tester la connectivité
ping node6.lan
ping node7.lan
ping node8.lan

# Ping via l'API
curl -X POST http://localhost:8081/workers/node6.lan/ping
```

### Performance dégradée

```bash
# Vérifier les métriques
curl http://localhost:8082/cluster/health

# Analyser les performances
curl http://localhost:8082/performance?hours=1

# Vérifier les alertes
curl http://localhost:8082/alerts
```

## 📚 Prochaines étapes

### Exploration avancée

1. **Workflows complexes** : Créer des workflows avec dépendances
2. **Monitoring personnalisé** : Configurer des alertes spécifiques
3. **Intégration** : Connecter avec vos applications existantes
4. **Optimisation** : Ajuster les paramètres selon vos besoins

### Ressources utiles

- [Documentation complète des services](SERVICES_README.md)
- [Architecture du système](ARCHITECTURE.md)
- [Exemples d'utilisation](../examples/cluster_usage_examples.py)
- [Configuration avancée](../config/services_config.py)

## 🎉 Félicitations !

Votre cluster DispyCluster est maintenant opérationnel ! Vous pouvez :

- Scraper des sites web de manière distribuée
- Planifier des tâches récurrentes
- Monitorer les performances en temps réel
- Gérer des workflows complexes

Pour des fonctionnalités avancées, consultez la [documentation complète](SERVICES_README.md).