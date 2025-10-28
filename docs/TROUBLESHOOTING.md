# Guide de dépannage DispyCluster

Ce guide vous aide à résoudre les problèmes courants avec votre cluster DispyCluster.

## 🔍 Diagnostic rapide

### Vérification de base

```bash
# Test complet des services
sudo bash scripts/test_services.sh

# Vérification manuelle
curl http://localhost:8084/health
```

### Commandes de diagnostic

```bash
# Statut des services
sudo systemctl status dispycluster-*

# Ports ouverts
sudo netstat -tlnp | grep -E "808[0-4]"

# Logs récents
journalctl -u dispycluster-controller --since "1 hour ago"
```

## 🚨 Problèmes courants

### 1. Services non accessibles

#### Symptômes
- Erreur "Connection refused" sur les ports 8080-8084
- Services systemd inactifs
- API Gateway non accessible

#### Solutions

**Vérifier les services systemd :**
```bash
# Lister tous les services DispyCluster
sudo systemctl list-units --type=service | grep dispycluster

# Redémarrer tous les services
sudo systemctl restart dispycluster-controller dispycluster-monitoring dispycluster-scheduler dispycluster-gateway

# Vérifier le statut
sudo systemctl status dispycluster-*
```

**Vérifier les ports :**
```bash
# Vérifier que les ports sont ouverts
sudo netstat -tlnp | grep -E "808[0-4]"

# Tester la connectivité
curl -v http://localhost:8084/health
```

**Vérifier les logs :**
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

#### Solutions avancées

**Réinstaller les services :**
```bash
# Arrêter tous les services
sudo systemctl stop dispycluster-*

# Réinstaller
sudo bash scripts/install_services.sh

# Redémarrer
sudo systemctl start dispycluster-*
```

**Vérifier les permissions :**
```bash
# Vérifier les permissions des fichiers
ls -la /opt/dispycluster/services/

# Corriger si nécessaire
sudo chown -R pi:pi /opt/dispycluster/
sudo chmod +x /opt/dispycluster/services/*.py
```

### 2. Workers non détectés

#### Symptômes
- Workers affichés comme "offline" dans l'API
- Erreurs de connexion aux workers
- Jobs non distribués

#### Solutions

**Vérifier la connectivité réseau :**
```bash
# Tester la connectivité
ping node6.lan
ping node7.lan
ping node8.lan

# Tester les ports spécifiques
telnet node6.lan 8080
telnet node6.lan 9100
```

**Vérifier les services sur les workers :**
```bash
# Vérifier le service de scraping
curl http://node6.lan:8080/health

# Vérifier node_exporter
curl http://node6.lan:9100/metrics
```

**Ping via l'API :**
```bash
# Ping d'un worker spécifique
curl -X POST http://localhost:8081/workers/node6.lan/ping

# Vérifier le statut
curl http://localhost:8081/workers
```

#### Solutions avancées

**Réinstaller les workers :**
```bash
# Sur chaque worker
ssh pi@node6.lan "sudo systemctl restart dispynode"
ssh pi@node6.lan "sudo systemctl restart node_exporter"
```

**Vérifier la configuration réseau :**
```bash
# Vérifier les résolutions DNS
nslookup node6.lan
nslookup node7.lan
nslookup node8.lan

# Vérifier les routes
ip route show
```

### 3. Performance dégradée

#### Symptômes
- Jobs qui prennent trop de temps
- Workers surchargés
- Erreurs de timeout

#### Solutions

**Vérifier les métriques :**
```bash
# Santé du cluster
curl http://localhost:8082/cluster/health

# Performance détaillée
curl http://localhost:8082/performance?hours=1

# Métriques des nœuds
curl http://localhost:8082/nodes
```

**Analyser les alertes :**
```bash
# Alertes actives
curl http://localhost:8082/alerts

# Détails d'un nœud
curl http://localhost:8082/nodes/node6.lan
```

**Optimiser la configuration :**
```bash
# Éditer la configuration
nano config/services_config.py

# Ajuster les limites
LIMITS = {
    "max_pages_per_job": 50,  # Réduire si nécessaire
    "max_timeout_seconds": 60,  # Timeout plus court
    "max_priority": 5  # Limiter les priorités
}
```

#### Solutions avancées

**Redistribuer les charges :**
```bash
# Arrêter les jobs en cours
curl http://localhost:8081/jobs | jq '.[] | select(.status == "running") | .id' | xargs -I {} curl -X POST http://localhost:8081/jobs/{}/cancel

# Redémarrer les services
sudo systemctl restart dispycluster-controller
```

**Vérifier les ressources :**
```bash
# Utilisation CPU
top -p $(pgrep -f dispycluster)

# Utilisation mémoire
free -h

# Utilisation disque
df -h
```

### 4. Erreurs de scraping

#### Symptômes
- Jobs qui échouent
- Erreurs de timeout
- Sites inaccessibles

#### Solutions

**Vérifier les logs des jobs :**
```bash
# Lister les jobs récents
curl http://localhost:8081/jobs | jq '.[] | select(.status == "failed")'

# Détails d'un job spécifique
curl http://localhost:8081/jobs/job_123
```

**Tester manuellement :**
```bash
# Test simple
curl -X POST http://localhost:8084/scrape \
  -H "Content-Type: application/json" \
  -d '{"start_url": "https://httpbin.org/html", "max_pages": 1}'
```

**Ajuster les paramètres :**
```bash
# Timeout plus long
curl -X POST http://localhost:8084/scrape \
  -H "Content-Type: application/json" \
  -d '{
    "start_url": "https://example.com",
    "max_pages": 5,
    "timeout_s": 60,
    "priority": 1
  }'
```

#### Solutions avancées

**Vérifier la connectivité internet :**
```bash
# Test de connectivité
curl -I https://httpbin.org/html
curl -I https://example.com
```

**Ajuster la configuration de scraping :**
```python
# Dans config/services_config.py
SCRAPING_CONFIG = {
    "default_user_agent": "DispyCluster/1.0",
    "delay_between_requests": 2,  # Délai plus long
    "max_redirects": 10,  # Plus de redirections
    "timeout": 30  # Timeout plus long
}
```

### 5. Problèmes de planification

#### Symptômes
- Tâches planifiées non exécutées
- Workflows qui échouent
- Scheduler non accessible

#### Solutions

**Vérifier le scheduler :**
```bash
# Statut du scheduler
curl http://localhost:8083/health

# Tâches planifiées
curl http://localhost:8083/tasks

# Planning
curl http://localhost:8083/schedule
```

**Vérifier les logs :**
```bash
# Logs du scheduler
journalctl -u dispycluster-scheduler -f
```

**Tester une tâche simple :**
```bash
# Créer une tâche de test
curl -X POST http://localhost:8083/tasks \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Test",
    "urls": ["https://httpbin.org/html"],
    "max_pages": 1,
    "schedule_type": "once",
    "schedule_config": {}
  }'
```

#### Solutions avancées

**Redémarrer le scheduler :**
```bash
sudo systemctl restart dispycluster-scheduler
```

**Vérifier la configuration :**
```bash
# Vérifier la configuration du scheduler
cat /opt/dispycluster/services/scheduler_service.py | grep -A 10 "SCHEDULER_CONFIG"
```

## 🔧 Outils de diagnostic

### Scripts de diagnostic

```bash
# Test complet
sudo bash scripts/test_services.sh

# Vérification des services
sudo /opt/dispycluster/check_services.sh

# Test de connectivité
ping -c 3 node6.lan
ping -c 3 node7.lan
ping -c 3 node8.lan
```

### Commandes de monitoring

```bash
# Surveillance en temps réel
watch -n 5 'curl -s http://localhost:8084/health | jq'

# Métriques des nœuds
watch -n 10 'curl -s http://localhost:8082/nodes | jq'

# Jobs en cours
watch -n 5 'curl -s http://localhost:8081/jobs | jq ".[] | select(.status == \"running\")"'
```

### Logs utiles

```bash
# Logs système
journalctl -u dispycluster-* --since "1 hour ago"

# Logs Docker (monitoring)
docker logs monitoring-prometheus-1
docker logs monitoring-grafana-1

# Logs Dispy
journalctl -u dispyscheduler -f
journalctl -u dispynode -f
```

## 🚨 Problèmes critiques

### Cluster complètement hors ligne

**Diagnostic :**
```bash
# Vérifier tous les services
sudo systemctl status dispycluster-* dispyscheduler

# Vérifier les ports
sudo netstat -tlnp | grep -E "808[0-4]|51347"

# Vérifier les logs
journalctl -u dispycluster-* --since "1 hour ago"
```

**Solution :**
```bash
# Redémarrer tous les services
sudo systemctl restart dispycluster-* dispyscheduler

# Vérifier le statut
sudo systemctl status dispycluster-* dispyscheduler
```

### Workers complètement inaccessibles

**Diagnostic :**
```bash
# Tester la connectivité
ping node6.lan
ping node7.lan
ping node8.lan

# Vérifier les services sur les workers
ssh pi@node6.lan "sudo systemctl status dispynode node_exporter"
```

**Solution :**
```bash
# Redémarrer les services sur les workers
ssh pi@node6.lan "sudo systemctl restart dispynode node_exporter"
ssh pi@node7.lan "sudo systemctl restart dispynode node_exporter"
ssh pi@node8.lan "sudo systemctl restart dispynode node_exporter"
```

### Monitoring non accessible

**Diagnostic :**
```bash
# Vérifier Docker
docker ps

# Vérifier les conteneurs
docker logs monitoring-prometheus-1
docker logs monitoring-grafana-1
```

**Solution :**
```bash
# Redémarrer le monitoring
cd monitoring
docker compose down
docker compose up -d
```

## 📞 Support et ressources

### Logs à collecter

En cas de problème persistant, collectez ces informations :

```bash
# Créer un rapport de diagnostic
mkdir -p /tmp/dispycluster-debug
cd /tmp/dispycluster-debug

# Statut des services
sudo systemctl status dispycluster-* > services-status.txt

# Logs récents
journalctl -u dispycluster-* --since "1 hour ago" > services-logs.txt

# Configuration réseau
ip addr show > network-config.txt
ip route show > network-routes.txt

# Ports ouverts
sudo netstat -tlnp > open-ports.txt

# Test de connectivité
curl -s http://localhost:8084/health > api-health.json
curl -s http://localhost:8081/cluster > cluster-stats.json
curl -s http://localhost:8082/cluster/health > cluster-health.json

# Créer une archive
tar -czf dispycluster-debug-$(date +%Y%m%d-%H%M%S).tar.gz *.txt *.json
```

### Ressources utiles

- [Documentation complète des services](SERVICES_README.md)
- [Guide de démarrage rapide](QUICK_START.md)
- [Architecture du système](ARCHITECTURE.md)
- [Exemples d'utilisation](../examples/cluster_usage_examples.py)

### Commandes de récupération

```bash
# Réinstallation complète des services
sudo bash scripts/install_services.sh

# Redémarrage complet du cluster
sudo systemctl restart dispycluster-* dispyscheduler
sudo systemctl restart dispynode  # Sur chaque worker

# Redémarrage du monitoring
cd monitoring
docker compose restart
```

## 🎯 Prévention des problèmes

### Maintenance régulière

```bash
# Vérification hebdomadaire
sudo bash scripts/test_services.sh

# Nettoyage des logs
sudo journalctl --vacuum-time=7d

# Vérification de l'espace disque
df -h
```

### Surveillance proactive

```bash
# Script de surveillance
#!/bin/bash
while true; do
    if ! curl -s http://localhost:8084/health > /dev/null; then
        echo "ALERTE: API Gateway non accessible"
        # Envoyer une notification
    fi
    sleep 60
done
```

### Sauvegarde de la configuration

```bash
# Sauvegarder la configuration
tar -czf dispycluster-config-$(date +%Y%m%d).tar.gz \
    config/ \
    inventory/ \
    /etc/systemd/system/dispycluster-*.service
```