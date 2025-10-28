# Scripts DispyCluster

Ce répertoire contient tous les scripts de test, diagnostic, monitoring et configuration réseau pour le cluster DispyCluster.

## Structure

```
scripts/
├── cluster_manager.py          # Gestionnaire principal (interface unifiée)
├── test/                       # Scripts de test
│   ├── test_cluster_connectivity.py
│   ├── test_dispy_cluster.py
│   └── test_workers_functionality.py
├── diagnostic/                 # Scripts de diagnostic
│   ├── diagnose_cluster_health.py
│   └── diagnose_node_performance.py
├── monitoring/                 # Scripts de monitoring
│   ├── monitor_cluster_realtime.py
│   └── monitor_cluster_logs.py
└── network/                    # Scripts de configuration réseau
    ├── configure_cluster_network.sh    # Configuration réseau du cluster
    ├── configure_network.sh            # Configuration réseau générale
    ├── configure_ufw.sh                # Configuration du firewall UFW
    ├── configure_ufw_worker.sh         # Configuration UFW pour workers
    ├── disable_ufw.sh                  # Désactivation du firewall
    ├── discover_rpi_nodes.sh           # Découverte automatique des nœuds RPi
    ├── diagnose_network.sh             # Diagnostic des problèmes réseau
    ├── fix_dns_resolution.sh           # Correction des problèmes DNS
    ├── fix_user_home.sh                # Correction du home directory utilisateur
    ├── optimize_cluster_network.sh     # Optimisation réseau du cluster
    ├── run_on_cluster.sh               # Exécution de commandes sur le cluster
    ├── sync_project_to_nodes.sh        # Synchronisation du projet vers tous les nœuds
    ├── sync_project_to_nodes.ps1       # Version PowerShell pour Windows
    ├── sync_ssh_keys_from_master.sh    # Synchronisation des clés SSH depuis le maître
    ├── sync_ssh_keys_from_master.ps1   # Version PowerShell pour Windows
    ├── sync_ssh_keys_no_sudo.sh        # Synchronisation SSH sans sudo
    ├── manage_dispy_cache.sh           # Gestion des fichiers de cache dispy
    ├── manage_dispy_cache.ps1          # Version PowerShell pour Windows
    ├── clean_dispy_cache.sh            # Nettoyage des fichiers de cache dispy
    └── test_cluster_network.py         # Test de connectivité réseau
```

## Utilisation

### Gestionnaire principal

Le script `cluster_manager.py` fournit une interface unifiée pour tous les autres scripts :

```bash
python3 scripts/cluster_manager.py
```

### Scripts de test

#### Test de connectivité
```bash
python3 scripts/test/test_cluster_connectivity.py
```
- Vérifie la connectivité réseau vers tous les nœuds
- Teste les ports dispy (51347, 51348)
- Affiche un résumé de la connectivité

#### Test complet du cluster
```bash
python3 scripts/test/test_dispy_cluster.py
```
- Teste la création et la gestion du cluster
- Distribue des tâches de test
- Vérifie la récupération des résultats

#### Test des workers
```bash
python3 scripts/test/test_workers_functionality.py
```
- Teste chaque type de worker (CPU, GPU, scraper, etc.)
- Vérifie les performances de chaque worker
- Affiche les résultats par type de worker

### Scripts de diagnostic

#### Diagnostic de santé
```bash
python3 scripts/diagnostic/diagnose_cluster_health.py
```
- Vérifie l'état de tous les nœuds
- Contrôle les ressources système
- Analyse les logs système

#### Diagnostic de performance
```bash
python3 scripts/diagnostic/diagnose_node_performance.py
```
- Mesure les performances de chaque nœud
- Compare les performances entre nœuds
- Génère un rapport de performance

### Scripts de monitoring

#### Monitoring temps réel
```bash
python3 scripts/monitoring/monitor_cluster_realtime.py
```
- Affiche l'état du cluster en temps réel
- Met à jour automatiquement toutes les 5 secondes
- Montre les ressources système et l'état des nœuds

#### Monitoring des logs
```bash
python3 scripts/monitoring/monitor_cluster_logs.py
```
- Surveille les logs système et dispy
- Détecte automatiquement les erreurs
- Affiche les logs récents avec mise en évidence des erreurs

### Scripts de configuration réseau

#### Configuration réseau
```bash
sudo scripts/network/configure_cluster_network.sh
```
- Configure les paramètres réseau optimaux
- Configure le firewall pour dispy
- Teste la connectivité

#### Test de connectivité réseau
```bash
python3 scripts/network/test_cluster_network.py
```
- Teste la connectivité entre tous les nœuds
- Mesure les performances réseau
- Génère un rapport de connectivité

#### Optimisation réseau
```bash
sudo scripts/network/optimize_cluster_network.sh
```
- Optimise les paramètres TCP
- Configure les limites système
- Améliore les performances réseau

#### Configuration SSH sans mot de passe
```bash
scripts/network/setup_ssh_keys.sh
```
- Génère une clé SSH sur le nœud maître
- Copie la clé publique vers tous les nœuds workers
- Configure l'accès SSH sans mot de passe
- **Important : À exécuter depuis le nœud maître**

#### Test d'accès SSH
```bash
scripts/network/test_ssh_access.sh
```
- Teste l'accès SSH sans mot de passe sur tous les nœuds
- Vérifie la connectivité réseau
- Affiche un rapport détaillé des tests

#### Exécution de commandes sur le cluster
```bash
scripts/network/run_on_cluster.sh "commande" [utilisateur]
```
- Exécute une commande sur tous les nœuds du cluster
- Exemples :
  - `./run_on_cluster.sh "uptime" pi`
  - `./run_on_cluster.sh "sudo systemctl status dispy" pi`
  - `./run_on_cluster.sh "df -h" pi`

#### Synchronisation du projet
```bash
# Version Linux/macOS
./scripts/network/sync_project_to_nodes.sh

# Version Windows PowerShell
.\scripts\network\sync_project_to_nodes.ps1
```
- Synchronise le projet DispyCluster vers `/home/dispy/DispyCluster` sur tous les nœuds
- Détecte automatiquement l'utilisateur approprié (pi ou dispy) selon le nœud
- Exclut les fichiers temporaires et de cache
- Affiche un résumé de la synchronisation

#### Synchronisation des clés SSH depuis le maître
```bash
# Version Linux/macOS
./scripts/network/sync_ssh_keys_from_master.sh

# Version Windows PowerShell
.\scripts\network\sync_ssh_keys_from_master.ps1
```
- Synchronise les clés SSH de node13 (maître) vers tous les autres nœuds
- Permet au nœud maître de se connecter sans mot de passe à tous les nœuds
- Copie les clés publiques et privées pour une cohérence complète
- Teste automatiquement la connectivité après synchronisation

## Prérequis

### Python
- Python 3.6+
- Modules requis : `dispy`, `yaml`, `psutil`, `requests`

### Système
- Accès root pour les scripts de configuration réseau
- SSH configuré pour les tests distants
- iperf3 installé pour les tests de bande passante (optionnel)
- **Pour SSH sans mot de passe :** Exécuter `setup_ssh_keys.sh` depuis le nœud maître

## Configuration

Les scripts utilisent la configuration des nœuds depuis `inventory/nodes.yaml` :

```yaml
workers:
  - node6.lan
  - node7.lan
  - node9.lan
  - node10.lan
  - node11.lan
  - node12.lan
  - node14.lan

master: node13.lan
```

## Dépannage

### Problèmes de connectivité
1. Vérifiez la configuration réseau avec `test_cluster_network.py`
2. Configurez le firewall avec `configure_cluster_network.sh`
3. Vérifiez les logs avec `monitor_cluster_logs.py`

### Problèmes de performance
1. Diagnostiquez les performances avec `diagnose_node_performance.py`
2. Optimisez le réseau avec `optimize_cluster_network.sh`
3. Surveillez en temps réel avec `monitor_cluster_realtime.py`

### Problèmes de cluster
1. Testez la connectivité avec `test_cluster_connectivity.py`
2. Testez le cluster complet avec `test_dispy_cluster.py`
3. Diagnostiquez la santé avec `diagnose_cluster_health.py`

### Problèmes SSH
1. **Synchronisation des clés SSH :** Utilisez `sync_ssh_keys_no_sudo.sh` depuis node13
2. **Correction du home directory :** Utilisez `fix_user_home.sh` si un utilisateur a un mauvais home directory
3. **Diagnostic réseau :** Utilisez `diagnose_network.sh` pour identifier les problèmes de connectivité
4. **Découverte des nœuds :** Utilisez `discover_rpi_nodes.sh` pour trouver automatiquement les nœuds RPi

## Scripts de synchronisation SSH

### Synchronisation depuis le nœud maître
```bash
# Depuis node13 (nœud maître)
./scripts/network/sync_ssh_keys_no_sudo.sh
```
Ce script synchronise les clés SSH de node13 vers tous les autres nœuds.

### Correction des problèmes d'utilisateur
```bash
# Correction du home directory d'un utilisateur
./scripts/network/fix_user_home.sh
```
Ce script corrige les problèmes de home directory (comme `/var/lib/dispy` au lieu de `/home/dispy`).

### Synchronisation du projet
```bash
# Synchronisation du projet vers tous les nœuds
./scripts/network/sync_project_to_nodes.sh
```
Ce script copie le projet DispyCluster vers tous les nœuds du cluster.

## Gestion des fichiers de cache dispy

### Explication des fichiers `_dispy_*.dat`
Les fichiers `_dispy_*.dat`, `_dispy_*.dir` et `_dispy_*.bak` sont créés automatiquement par dispy pour :
- **Cache de découverte** des nœuds du cluster
- **Métadonnées** de connexion et de performance  
- **État du cluster** en temps réel
- **Logs de communication** entre les nœuds

Ces fichiers se recréent automatiquement à chaque utilisation du cluster.

### Gestion des fichiers de cache
```bash
# Déplacer les fichiers de cache vers temp/
./scripts/network/manage_dispy_cache.sh
```
Ce script déplace tous les fichiers `_dispy_*` vers le dossier `temp/` pour garder le répertoire principal propre.

```bash
# Nettoyer les anciens fichiers de cache
./scripts/network/clean_dispy_cache.sh
```
Ce script supprime les anciens fichiers de cache avec confirmation.

### Version PowerShell (Windows)
```powershell
# Déplacer les fichiers de cache
.\scripts\network\manage_dispy_cache.ps1
```

## Notes importantes

- Les scripts de configuration réseau nécessitent des privilèges root
- Certains tests peuvent prendre du temps selon la taille du cluster
- Les scripts de monitoring s'exécutent en continu (Ctrl+C pour arrêter)
- Sauvegardez votre configuration avant d'utiliser les scripts d'optimisation