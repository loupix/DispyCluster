# Quick Start - WebSocket Support

## Récapitulatif

✅ **OUI**, les routes `/api/health` et `/api/cluster/nodes` ont été migrées vers WebSocket **ET** elles sont disponibles sur toutes les pages qui les utilisent.

## Comment utiliser

### Démarrage du serveur

```bash
conda activate dispycluster
cd web
python app.py
```

### Pages bénéficiant automatiquement du WebSocket

Toutes les pages utilisent maintenant le WebSocket pour les mises à jour en temps réel :

1. **Dashboard** (`/`) - Dashboard principal
2. **Nodes** (`/nodes`) - Liste des nœuds  
3. **Monitoring** (`/monitoring`) - Page de monitoring
4. **Base template** - Toutes les pages qui héritent de `base.html`

### Ce qui se passe automatiquement

1. **Connexion automatique** : Dès qu'une page se charge, WebSocket se connecte
2. **Mises à jour en temps réel** : Quand `/api/cluster/nodes` est appelé, tous les clients connectés reçoivent les nouvelles données
3. **Pas de code supplémentaire nécessaire** : Fonctionne out-of-the-box

### Test rapide

1. Ouvrir deux onglets avec le dashboard
2. Dans un onglet, rafraîchir les données
3. Le deuxième onglet se met à jour automatiquement (via WebSocket + Redis)

### Utiliser Redis Pub/Sub

**OUI**, on utilise Redis pub/sub ! Voici comment :

```python
# Publier un événement
await websocket_manager.publish_event("cluster:metrics", {
    "nodes": nodes_data,
    "timestamp": datetime.now().isoformat()
})
```

Cela déclenche automatiquement l'événement `redis_cluster_metrics` pour tous les clients WebSocket connectés.

## Documentation complète

- `docs/WEB_SOCKET.md` : Documentation technique complète
- `docs/websocket_implementation_summary.md` : Résumé de l'implémentation

