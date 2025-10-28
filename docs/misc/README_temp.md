# Dossier temporaire

Ce dossier contient les fichiers temporaires et de cache du cluster DispyCluster.

## Fichiers de cache dispy

Les fichiers `_dispy_*.dat`, `_dispy_*.dir` et `_dispy_*.bak` sont créés automatiquement par dispy pour :

- **Cache de découverte** des nœuds du cluster
- **Métadonnées** de connexion et de performance  
- **État du cluster** en temps réel
- **Logs de communication** entre les nœuds

### Gestion

- **Déplacer les fichiers** : `./scripts/network/manage_dispy_cache.sh`
- **Nettoyer le cache** : `./scripts/network/clean_dispy_cache.sh`

### Important

- Ces fichiers se recréent automatiquement à chaque utilisation du cluster
- Il n'est pas nécessaire de les supprimer manuellement
- Ils sont ignorés par Git (voir `.gitignore`)

## Autres fichiers temporaires

Ce dossier peut également contenir d'autres fichiers temporaires générés par les scripts du cluster.