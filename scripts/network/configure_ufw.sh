#!/bin/bash
set -e

# Script de configuration UFW pour DispyCluster
# Configure les règles de pare-feu pour permettre la communication entre les services

if [ "${EUID}" -ne 0 ]; then
  echo "Ce script doit être exécuté en root"
  exit 1
fi

echo "Configuration UFW pour DispyCluster..."

# Activer UFW s'il n'est pas déjà actif
if ! ufw status | grep -q "Status: active"; then
  echo "Activation d'UFW..."
  ufw --force enable
fi

# Règles de base
echo "Configuration des règles de base..."
ufw default deny incoming
ufw default allow outgoing

# SSH (obligatoire pour l'administration)
echo "Autorisation SSH..."
ufw allow ssh
ufw allow 22/tcp

# Ports des services DispyCluster (maître)
echo "Configuration des ports des services..."
ufw allow 8080/tcp comment "Scraper Service"
ufw allow 8081/tcp comment "Cluster Controller"
ufw allow 8082/tcp comment "Monitoring Service"
ufw allow 8083/tcp comment "Scheduler Service"
ufw allow 8084/tcp comment "API Gateway"

# Ports de monitoring
ufw allow 9090/tcp comment "Prometheus"
ufw allow 3000/tcp comment "Grafana"
ufw allow 9100/tcp comment "Node Exporter"

# Port Dispy (pour la communication maître-workers)
ufw allow 51347/tcp comment "Dispy Scheduler"
ufw allow 51348:51400/tcp comment "Dispy Workers (ports dynamiques)"

# Autoriser la communication entre les nodes du cluster
echo "Configuration des règles pour le cluster..."

# Récupérer les IPs des nodes depuis inventory/nodes.yaml
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
INV_FILE="${SCRIPT_DIR}/../inventory/nodes.yaml"

if [ -f "$INV_FILE" ]; then
  echo "Lecture de l'inventaire des nodes..."
  
  # Extraire les IPs des workers (format simple)
  WORKER_IPS=$(grep -E "^\s*-\s*node[0-9]+\.lan" "$INV_FILE" | sed 's/.*- //' | head -10)
  
  for worker in $WORKER_IPS; do
    echo "Autorisation de la communication avec $worker..."
    # Autoriser tous les ports nécessaires depuis chaque worker
    ufw allow from "$worker" to any port 8080 comment "Scraper from $worker"
    ufw allow from "$worker" to any port 8081 comment "Controller from $worker"
    ufw allow from "$worker" to any port 8082 comment "Monitoring from $worker"
    ufw allow from "$worker" to any port 8083 comment "Scheduler from $worker"
    ufw allow from "$worker" to any port 8084 comment "Gateway from $worker"
    ufw allow from "$worker" to any port 9090 comment "Prometheus from $worker"
    ufw allow from "$worker" to any port 3000 comment "Grafana from $worker"
    ufw allow from "$worker" to any port 9100 comment "Node Exporter from $worker"
    ufw allow from "$worker" to any port 51347 comment "Dispy from $worker"
  done
else
  echo "Fichier d'inventaire non trouvé, configuration générique..."
  # Autoriser les sous-réseaux courants pour Raspberry Pi
  ufw allow from 192.168.1.0/24 comment "Réseau local Raspberry Pi"
  ufw allow from 192.168.0.0/24 comment "Réseau local alternatif"
fi

# Règles pour la communication entre workers (si nécessaire)
echo "Configuration des règles inter-workers..."
ufw allow from 192.168.1.0/24 to 192.168.1.0/24 port 9100 comment "Node Exporter inter-workers"
ufw allow from 192.168.1.0/24 to 192.168.1.0/24 port 8080 comment "Scraper inter-workers"

# Afficher le statut final
echo ""
echo "=== Configuration UFW terminée ==="
echo ""
echo "Statut UFW :"
ufw status numbered

echo ""
echo "Règles actives :"
ufw status | grep -E "(808[0-4]|9090|3000|9100|51347)"

echo ""
echo "Pour voir toutes les règles :"
echo "  ufw status verbose"

echo ""
echo "Pour désactiver UFW (si nécessaire) :"
echo "  ufw disable"

echo ""
echo "Pour réinitialiser UFW :"
echo "  ufw --force reset"