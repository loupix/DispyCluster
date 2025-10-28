# DispyCluster Web Interface

Interface web moderne et unifiée pour la gestion du cluster DispyCluster.

## 🚀 Fonctionnalités

- **Dashboard en temps réel** : Vue d'ensemble du cluster avec métriques live
- **Gestion des jobs** : Création, surveillance et contrôle des tâches
- **Monitoring avancé** : Surveillance des nœuds, CPU, mémoire, réseau
- **Interface moderne** : Design épuré avec animations fluides
- **API RESTful** : Endpoints complets pour l'intégration
- **Base de données** : Stockage SQLite pour la persistance

## 📁 Structure

```
web/
├── app.py                 # Application FastAPI principale
├── run.py                 # Script de démarrage
├── requirements.txt       # Dépendances Python
├── api/                   # Endpoints API
│   ├── cluster.py         # Gestion du cluster
│   ├── jobs.py           # Gestion des jobs
│   └── monitoring.py     # Monitoring et métriques
├── templates/            # Templates HTML
│   ├── base.html         # Template de base
│   ├── dashboard.html    # Page d'accueil
│   ├── jobs.html         # Gestion des jobs
│   ├── nodes.html        # Nœuds du cluster
│   └── monitoring.html   # Monitoring avancé
├── static/               # Fichiers statiques
│   ├── css/              # Styles CSS
│   └── js/               # JavaScript
└── data/                # Base de données SQLite
```

## 🛠️ Installation

### Prérequis

- Python 3.8+
- Environnement conda `dispycluster` activé

### Installation des dépendances

```bash
# Activer l'environnement conda
conda activate dispycluster

# Installer les dépendances
pip install -r requirements.txt
```

### Configuration

1. **Services backend** : Assurez-vous que les services suivants sont démarrés :
   - API Gateway (port 8084)
   - Monitoring Service (port 8082)
   - Cluster Controller (port 8081)
   - Scheduler Service (port 8083)

2. **Base de données** : La base SQLite sera créée automatiquement au premier démarrage.

## 🚀 Démarrage

### Mode développement

```bash
# Démarrer avec rechargement automatique
python run.py
```

### Mode production

```bash
# Démarrer avec uvicorn
uvicorn app:app --host 0.0.0.0 --port 8085
```

L'interface sera accessible sur : http://localhost:8085

## 📊 API Endpoints

### Cluster
- `GET /api/cluster/overview` - Vue d'ensemble
- `GET /api/cluster/nodes` - Liste des nœuds
- `GET /api/cluster/nodes/{node_name}` - Détails d'un nœud
- `GET /api/cluster/health` - Santé du cluster

### Jobs
- `GET /api/jobs` - Liste des jobs
- `POST /api/jobs` - Créer un job
- `GET /api/jobs/{job_id}` - Détails d'un job
- `PUT /api/jobs/{job_id}` - Mettre à jour un job
- `DELETE /api/jobs/{job_id}` - Annuler un job

### Monitoring
- `GET /api/monitoring/health` - Santé du monitoring
- `GET /api/monitoring/nodes` - Statut des nœuds
- `GET /api/monitoring/metrics` - Métriques du cluster
- `GET /api/monitoring/alerts` - Alertes actives
- `POST /api/monitoring/collect_metrics` - Collecte forcée

## 🎨 Interface

### Dashboard
- Métriques en temps réel
- État des services
- Activité récente
- Alertes actives

### Gestion des Jobs
- Création de jobs (scraping, traitement, analyse)
- Surveillance en temps réel
- Historique et logs
- Gestion des priorités

### Monitoring
- Graphiques de performance
- Métriques détaillées
- Alertes et événements
- Export des données

### Nœuds
- Vue d'ensemble des nœuds
- Métriques individuelles
- Graphiques de performance
- Gestion des nœuds

## 🔧 Configuration

### Variables d'environnement

```bash
# Port de l'interface web
PORT=8085

# Mode debug
DEBUG=false

# Hôte
HOST=0.0.0.0
```

### Services backend

Les URLs des services sont configurées dans `app.py` :

```python
SERVICES = {
    "cluster_controller": "http://localhost:8081",
    "monitoring": "http://localhost:8082", 
    "scheduler": "http://localhost:8083",
    "scraper": "http://localhost:8080",
    "api_gateway": "http://localhost:8084"
}
```

## 📈 Monitoring

### Métriques collectées

- **CPU** : Utilisation par nœud
- **Mémoire** : RAM utilisée
- **Disque** : Espace disque
- **Réseau** : Trafic entrant/sortant
- **Température** : Température des nœuds
- **Jobs** : Statistiques d'exécution

### Alertes

- Nœuds hors ligne
- CPU/Mémoire élevés
- Erreurs de jobs
- Problèmes de connectivité

## 🚨 Dépannage

### Problèmes courants

1. **Services indisponibles** : Vérifiez que tous les services backend sont démarrés
2. **Base de données** : Vérifiez les permissions du dossier `data/`
3. **Port occupé** : Changez le port dans `run.py`

### Logs

Les logs sont affichés dans la console. Pour plus de détails :

```bash
# Mode debug
DEBUG=true python run.py
```

## 🔄 Intégration

### WebSocket (optionnel)

Pour les mises à jour en temps réel, un WebSocket peut être configuré :

```javascript
const ws = new WebSocket('ws://localhost:8085/ws');
ws.onmessage = (event) => {
    const data = JSON.parse(event.data);
    // Traiter les mises à jour
};
```

### API externe

L'interface expose une API RESTful complète pour l'intégration avec d'autres systèmes.

## 📝 Développement

### Ajout de nouvelles pages

1. Créer le template HTML dans `templates/`
2. Ajouter la route dans `app.py`
3. Créer les endpoints API si nécessaire

### Ajout de nouvelles métriques

1. Modifier le service de monitoring
2. Ajouter les endpoints dans `api/monitoring.py`
3. Mettre à jour l'interface

## 🤝 Contribution

1. Fork le projet
2. Créer une branche feature
3. Commiter les changements
4. Pousser vers la branche
5. Ouvrir une Pull Request

## 📄 Licence

Ce projet fait partie de DispyCluster et suit la même licence.