#!/bin/bash
set -e

# Script d'installation du maître Dispy
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
# - Installe Python3, pip, dispy
# - Installe Docker et Docker Compose
# - Installe service systemd dispyscheduler

if [ "${EUID}" -ne 0 ]; then
  echo "Ce script doit être exécuté en root"
  exit 1
fi

echo "Mise à jour du système..."
apt-get update
apt-get -y upgrade

echo "Installation dépendances..."
apt-get -y install python3 python3-pip curl ca-certificates gnupg lsb-release

echo "Installation de dispy..."
pip3 install --upgrade pip
pip3 install dispy

echo "Installation de Docker..."
install -m 0755 -d /etc/apt/keyrings
curl -fsSL https://download.docker.com/linux/$(. /etc/os-release; echo "$ID")/gpg -o /etc/apt/keyrings/docker.gpg
chmod a+r /etc/apt/keyrings/docker.gpg
echo \
  "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.gpg] https://download.docker.com/linux/$(. /etc/os-release; echo "$ID") \
  $(. /etc/os-release; echo "$VERSION_CODENAME") stable" \
  > /etc/apt/sources.list.d/docker.list
apt-get update
apt-get -y install docker-ce docker-ce-cli containerd.io docker-buildx-plugin docker-compose-plugin

echo "Ajout de l'utilisateur courant au groupe docker (si applicable)..."
CURRENT_USER=$(logname 2>/dev/null || echo "")
if [ -n "$CURRENT_USER" ]; then
  usermod -aG docker "$CURRENT_USER" || true
fi

echo "Installation service systemd dispy-master (JobCluster)..."
# Créer le script Python pour le scheduler
cat >/opt/dispy_scheduler.py <<'PYTHON_SCRIPT'
#!/usr/bin/env python3
# Script de scheduler Dispy basé sur JobCluster (API 4.15.2+)

import sys
import os
import dispy

# Ajouter le répertoire du projet au PYTHONPATH
project_dir = '/home/dispy/DispyCluster'
if project_dir not in sys.path:
    sys.path.insert(0, project_dir)

# Obtenir l'IP locale depuis la variable d'environnement
local_ip = os.environ.get('DISPY_LOCAL_IP', '127.0.0.1')

print(f'Démarrage du scheduler Dispy sur {local_ip}:51347')
print('Configuration Dispy:')
print(f'  IP: {local_ip}')
print(f'  Port: 51347')

try:
    # Définir une fonction de computation par défaut
    def default_computation(data):
        """Fonction de computation par défaut pour le cluster"""
        return f"Traité: {data}"
    
    # Créer un JobCluster avec la fonction de computation
    print('Création du JobCluster...')
    cluster = dispy.JobCluster(default_computation)
    print('✓ JobCluster créé avec succès')
    
    print(f'Type de cluster: {type(cluster).__name__}')
    print('Cluster prêt à recevoir des jobs')
    
    # Garder le cluster actif
    import time
    while True:
        time.sleep(1)
        
except KeyboardInterrupt:
    print('Arrêt du cluster...')
    if 'cluster' in locals() and hasattr(cluster, 'close'):
        cluster.close()
except Exception as e:
    print(f'Erreur: {e}')
    import traceback
    traceback.print_exc()
    sys.exit(1)
PYTHON_SCRIPT

# Rendre le script exécutable
chmod +x /opt/dispy_scheduler.py

# Créer le service systemd
cat >/etc/systemd/system/dispy-master.service <<'SERVICE'
[Unit]
Description=Dispy Master (JobCluster)
After=network-online.target
Wants=network-online.target

[Service]
Type=simple
User=pi
WorkingDirectory=/home/dispy/DispyCluster
Environment=PYTHONPATH=/home/dispy/DispyCluster
Environment=DISPY_LOCAL_IP=192.168.1.189
ExecStart=/opt/dispy_scheduler.py
Restart=always
RestartSec=10
StandardOutput=journal
StandardError=journal

[Install]
WantedBy=multi-user.target
SERVICE

systemctl daemon-reload
systemctl enable dispy-master.service
systemctl restart dispy-master.service

echo "Configuration UFW..."
if [ -f "${SCRIPT_DIR}/configure_ufw.sh" ]; then
  bash "${SCRIPT_DIR}/configure_ufw.sh"
else
  echo "Script UFW non trouvé, configuration manuelle nécessaire"
fi

echo "Installation maître terminée. Pensez à lancer le monitoring dans ./monitoring." 

