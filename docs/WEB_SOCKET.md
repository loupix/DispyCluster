# WebSocket Support - DispyCluster

## Vue d'ensemble

L'implémentation WebSocket permet un monitoring en temps réel du cluster via des connexions persistantes et l'utilisation de Redis pub/sub pour la communication événementielle.

## Architecture

### Composants

1. **WebSocketManager** (`web/core/websocket_manager.py`)
   - Gestionnaire central pour les connexions WebSocket
   - Gère l'abonnement Redis pub/sub
   - Diffuse les événements en temps réel aux clients connectés

2. **Namespaces**
   - `/health` : Monitorage de la santé du système
   - `/monitoring` : Monitorage des nœuds et du cluster

3. **Redis Pub/Sub**
   - Canaux utilisés :
     - `cluster:metrics` : Métriques du cluster
     - `cluster:health` : État de santé
     - `cluster:alerts` : Alertes système

## Installation

Les dépendances sont déjà incluses dans `requirements.txt` :

```
python-socketio==5.11.0
python-socketio[asyncio]==5.11.0
```

Pour installer :

```bash
conda activate dispycluster
pip install -r requirements.txt
```

## Utilisation

### Démarrage du serveur

Le WebSocket Manager se lance automatiquement avec l'application :

```bash
python web/app.py
```

Ou via le script de démarrage existant.

### Page de test

Accédez à la page de test WebSocket :
```
http://localhost:8085/websocket-test
```

### Client JavaScript

Exemple de connexion :

```javascript
// Connexion au namespace principal
const socket = io('http://localhost:8085');

// Écouter les événements Redis
socket.on('redis_cluster_metrics', (data) => {
    console.log('Métriques du cluster:', data);
});

// Se connecter au namespace health
const healthSocket = io('http://localhost:8085/health');
healthSocket.emit('request_health', {});

// Se connecter au namespace monitoring
const monitoringSocket = io('http://localhost:8085/monitoring');
monitoringSocket.emit('request_nodes_status', {});
```

## Événements disponibles

### Namespace `/health`

- **request_health** : Demander l'état de santé
- **health_response** : Réponse avec les données de santé
- **health_connected** : Confirmation de connexion

### Namespace `/monitoring`

- **request_cluster_status** : Demander l'état du cluster
- **request_nodes_status** : Demander l'état des nœuds
- **cluster_status_response** : Réponse avec l'état du cluster
- **nodes_status_response** : Réponse avec l'état des nœuds
- **subscribe_to_updates** : S'abonner aux mises à jour

### Événements Redis

- **redis_cluster_metrics** : Métriques du cluster publiées sur Redis
- **redis_cluster_health** : État de santé publié sur Redis
- **redis_cluster_alerts** : Alertes publiées sur Redis

## Routes API avec support WebSocket

Les routes suivantes publient automatiquement sur Redis lorsqu'elles sont appelées :

- **GET /api/health** : Retourne maintenant le nombre de clients WebSocket connectés
- **GET /api/cluster/nodes** : Publie les données des nœuds sur Redis

## Configuration

La configuration Redis se trouve dans `web/config/metrics_config.py` :

```python
REDIS_CONFIG = {
    "host": REDIS_HOST,
    "port": REDIS_PORT,
    "db": REDIS_METRICS_DB,
    "decode_responses": True
}
```

## Utilisation de Redis Pub/Sub

### Publier un événement

```python
await websocket_manager.publish_event("cluster:metrics", {
    "nodes": nodes_data,
    "timestamp": datetime.now().isoformat()
})
```

### S'abonner manuellement (côté serveur)

Le WebSocketManager s'abonne automatiquement aux canaux Redis et diffuse les messages aux clients connectés.

## Dépannage

### Erreur de connexion Redis

Vérifiez que Redis est actif :
```bash
redis-cli ping
```

### Clients non connectés

Vérifiez les logs du serveur pour les erreurs de connexion WebSocket.

### Namespaces non reconnus

Assurez-vous que les namespaces sont bien enregistrés dans `WebSocketManager._setup_namespaces()`.

## Améliorations futures

- Support de l'authentification pour les WebSockets
- Compression des messages volumineux
- Rate limiting pour les clients
- Persistance des événements dans Redis
- Dashboard temps réel intégré

