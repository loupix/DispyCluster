Architecture DispyCluster
=========================

Objectif
--------
Monter un cluster de calcul basé sur Dispy avec:
- Un noeud maître: planification des jobs (dispyscheduler), Prometheus + Grafana
- Des noeuds workers: exécution (dispynode)
- Un monitoring léger via node_exporter sur chaque RPi

Topologie
---------
- Maître: `master.lan` (ou une machine dédiée)
- Workers: `node6.lan` à `node14.lan`

Flux principaux
---------------
- Les clients soumettent des jobs au maître Dispy (scheduler)
- Le scheduler distribue aux `dispynode` sur les RPi
- Prometheus scrappe les `node_exporter` de chaque RPi
- Grafana lit Prometheus et affiche des tableaux de bord

Composants
----------
- Dispy Scheduler (maître): binaire `dispyscheduler`
- Dispy Node (worker): binaire `dispynode`
- Node Exporter (workers): exposition de métriques système sur port 9100
- Prometheus (maître): scrappe les metrics
- Grafana (maître): visualisation

Réseau et ports
---------------
- dispyscheduler: 51347 (par défaut Dispy utilise des ports dynamiques, on laisse par défaut)
- dispynode: 51348+ (gérés par Dispy)
- node_exporter: 9100
- Prometheus: 9090
- Grafana: 3000

Sécurité minimale
-----------------
- Accès SSH restreint au maître
- Réseau LAN de confiance
- Mots de passe Grafana à changer après le premier login

Déploiement
-----------
1. Installer les workers: `scripts/install_node.sh`
2. Installer le maître: `scripts/install_master.sh`
3. Activer services systemd sur tous les hôtes
4. Lancer `monitoring/docker-compose.yml`

