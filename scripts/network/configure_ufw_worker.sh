#!/bin/bash
set -e

# Script de configuration UFW pour les workers DispyCluster
# Configure les règles de pare-feu pour les nodes workers

if [ "${EUID}" -ne 0 ]; then
  echo "Ce script doit être exécuté en root"
  exit 1
fi

echo "Configuration UFW pour worker DispyCluster..."

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

# Ports spécifiques aux workers
echo "Configuration des ports des workers..."
ufw allow 8080/tcp comment "Scraper Service"
ufw allow 9100/tcp comment "Node Exporter"

# Ports Dispy pour la communication avec le maître
ufw allow 51348:51400/tcp comment "Dispy Workers (ports dynamiques)"

# Autoriser la communication depuis le maître
echo "Configuration des règles pour le maître..."
# Le maître peut être node13.lan ou une autre IP
MASTER_IPS="192.168.1.113"  # IP de node13.lan (à adapter selon votre réseau)

for master_ip in $MASTER_IPS; do
  echo "Autorisation de la communication depuis le maître $master_ip..."
  ufw allow from "$master_ip" to any port 8080 comment "Scraper from master"
  ufw allow from "$master_ip" to any port 9100 comment "Node Exporter from master"
  ufw allow from "$master_ip" to any port 51348:51400 comment "Dispy from master"
done

# Autoriser la communication depuis le réseau local (pour le monitoring)
echo "Configuration des règles pour le réseau local..."
ufw allow from 192.168.1.0/24 to any port 9100 comment "Node Exporter from LAN"
ufw allow from 192.168.1.0/24 to any port 8080 comment "Scraper from LAN"

# Afficher le statut final
echo ""
echo "=== Configuration UFW worker terminée ==="
echo ""
echo "Statut UFW :"
ufw status numbered

echo ""
echo "Règles actives :"
ufw status | grep -E "(8080|9100|51348)"

echo ""
echo "Pour voir toutes les règles :"
echo "  ufw status verbose"

echo ""
echo "Note : Ce worker peut maintenant communiquer avec le maître"
echo "et exposer ses métriques pour le monitoring."