# Intégration Dispy 4.15 dans DispyCluster Web Interface

## 🚀 Vue d'ensemble

L'interface web DispyCluster intègre maintenant **Dispy 4.15** comme backend de distribution des tâches, offrant une gestion intelligente et distribuée des jobs sur le cluster de Raspberry Pi.

## 🔧 Architecture

### Composants principaux

1. **Dispatcher avec Dispy** (`web/core/dispatcher.py`)
   - Cluster Dispy automatique
   - Distribution intelligente des tâches
   - Tolérance aux pannes intégrée
   - Fallback vers simulation si Dispy indisponible

2. **Vues intelligentes** (`web/views/`)
   - ClusterView : Gestion du cluster avec Dispy
   - MonitoringView : Surveillance avancée
   - Intégration transparente des algorithmes

3. **API RESTful** (`web/app.py`)
   - Endpoints pour cluster, jobs, monitoring
   - Endpoints spécifiques Dispy
   - Interface web moderne

## 📊 Fonctionnalités Dispy

### Distribution automatique
```python
# Le dispatcher utilise automatiquement Dispy
dispatcher = Dispatcher(worker_registry, task_queue)
result = await dispatcher.dispatch_once()
```

### Gestion du cluster
```python
# Statut du cluster Dispy
dispy_status = dispatcher.get_dispy_status()
# {
#   "status": "active",
#   "nodes": 7,
#   "active_jobs": 3,
#   "total_jobs": 150
# }
```

### Nettoyage automatique
```python
# Nettoyer les jobs terminés
cleaned = dispatcher.cleanup_dispy_jobs()
```

## 🛠️ Configuration

### Dépendances
```bash
pip install dispy==4.15.0
```

### Variables d'environnement
```bash
# Configuration Dispy
DISPY_NODES="node6.lan,node7.lan,node9.lan,node10.lan,node11.lan,node12.lan,node14.lan"
DISPY_PORT=51347
DISPY_CLEANUP_INTERVAL=300
```

## 📡 API Endpoints

### Cluster
- `GET /api/cluster/overview` - Vue d'ensemble avec Dispy
- `GET /api/cluster/nodes` - Nœuds du cluster
- `GET /api/cluster/optimize` - Optimisation automatique

### Jobs
- `POST /api/jobs` - Créer un job (via Dispy)
- `GET /api/jobs/status` - Statut des jobs
- `GET /api/jobs/{job_id}` - Détails d'un job

### Monitoring
- `GET /api/metrics` - Métriques en temps réel
- `GET /api/alerts` - Alertes intelligentes
- `GET /api/monitoring/export` - Export des données

### Dispy spécifique
- `GET /api/dispy/status` - Statut du cluster Dispy
- `POST /api/dispy/cleanup` - Nettoyage des jobs

## 🎯 Algorithmes intégrés

### 1. Cluster Manager
- Gestion intelligente des nœuds
- Détection automatique de la santé
- Sélection optimale des workers

### 2. Load Balancer
- Round-robin
- Random weighted
- Least connections
- Best performance
- Least recent

### 3. Task Queue
- Priorités multiples
- Retry automatique
- Historique complet
- Nettoyage automatique

### 4. Worker Registry
- Capacités des workers
- Métriques de performance
- Heartbeat monitoring
- Score de performance

### 5. Fault Tolerance
- Circuit breaker
- Retry policy
- Health checker
- Gestion des erreurs

## 🔄 Workflow des tâches

1. **Soumission** : Job créé et ajouté à la file
2. **Sélection** : Worker optimal choisi par l'algorithme
3. **Distribution** : Tâche envoyée via Dispy au worker
4. **Exécution** : Worker exécute la tâche
5. **Résultat** : Retour du résultat via Dispy
6. **Mise à jour** : Statut et métriques mis à jour

## 📈 Monitoring avancé

### Métriques collectées
- Performance des workers
- Taux de succès des jobs
- Utilisation des ressources
- Latence du réseau
- Erreurs et échecs

### Alertes intelligentes
- Workers en panne
- Surcharge du cluster
- Erreurs de distribution
- Performance dégradée

### Recommandations automatiques
- Optimisation de la stratégie
- Ajout de workers
- Nettoyage des ressources
- Rééquilibrage de charge

## 🚀 Démarrage

### Installation
```bash
cd web
pip install -r requirements.txt
```

### Démarrage
```bash
python run.py
```

### Accès
- Interface web : http://localhost:8085
- API : http://localhost:8085/api
- Documentation : http://localhost:8085/docs

## 🔧 Configuration avancée

### Cluster Dispy personnalisé
```python
# Dans web/core/dispatcher.py
def _init_dispy_cluster(self):
    self.dispy_cluster = dispy.JobCluster(
        self._dispatch_function,
        nodes=['node6.lan', 'node7.lan'],
        depends=['dispy', 'requests'],
        reentrant=True,
        cleanup=True,
        loglevel=dispy.logger.DEBUG
    )
```

### Fonctions de dispatch personnalisées
```python
def _dispatch_function(self, task_data):
    """Fonction personnalisée pour l'exécution des tâches."""
    # Logique d'exécution spécifique
    return {"success": True, "result": "Task completed"}
```

## 🐛 Dépannage

### Problèmes courants

1. **Cluster Dispy non initialisé**
   - Vérifier la connectivité réseau
   - Vérifier que les nœuds sont accessibles
   - Consulter les logs pour plus de détails

2. **Jobs en échec**
   - Vérifier les capacités des workers
   - Consulter les métriques de performance
   - Utiliser l'optimisation automatique

3. **Performance dégradée**
   - Vérifier l'état des workers
   - Consulter les alertes
   - Optimiser la stratégie de dispatch

### Logs et debugging
```bash
# Mode debug
DEBUG=true python run.py

# Logs Dispy
export DISPY_LOGLEVEL=DEBUG
```

## 📚 Documentation

- **Dispy 4.15** : https://dispy.sourceforge.net/
- **API Documentation** : http://localhost:8085/docs
- **Interface Web** : http://localhost:8085

## 🤝 Contribution

Pour contribuer à l'intégration Dispy :

1. Fork le projet
2. Créer une branche feature
3. Implémenter les améliorations
4. Tester avec le cluster
5. Soumettre une PR

## 📄 Licence

Ce projet utilise Dispy 4.15 sous licence BSD et suit la même licence que DispyCluster.