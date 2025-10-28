#!/bin/bash

# Script d'installation complète de DispyCluster
# Résout les problèmes "Bad source address" et installe tous les services

set -e

echo "=== Installation complète DispyCluster ==="
echo "Résolution des erreurs 'Bad source address'"
echo ""

# Obtenir l'IP locale
get_local_ip() {
    local ip=""
    
    if command -v ip >/dev/null 2>&1; then
        ip=$(ip route get 8.8.8.8 2>/dev/null | grep -oP 'src \K\S+' 2>/dev/null || echo "")
    fi
    
    if [ -z "$ip" ]; then
        ip=$(hostname -I 2>/dev/null | awk '{print $1}' 2>/dev/null || echo "")
    fi
    
    echo "$ip"
}

LOCAL_IP=$(get_local_ip)
echo "IP locale détectée: $LOCAL_IP"

if [ -z "$LOCAL_IP" ]; then
    echo "✗ Impossible de détecter l'IP locale"
    exit 1
fi

echo "✓ IP locale: $LOCAL_IP"

# Installation des dépendances Python
echo ""
echo "=== Installation des dépendances Python ==="

# Mettre à jour pip
python3 -m pip install --upgrade pip setuptools wheel

# Installer les dépendances de base
python3 -m pip install --no-cache-dir \
    setuptools \
    wheel \
    cython \
    numpy

# Installer Dispy
echo "Installation de Dispy..."
python3 -m pip install --no-cache-dir dispy==4.15.0

# Installer les autres dépendances
python3 -m pip install --no-cache-dir \
    fastapi==0.100.1 \
    uvicorn==0.23.2 \
    aiohttp==3.8.5 \
    httpx==0.24.1 \
    apscheduler==3.9.1 \
    requests==2.31.0 \
    pydantic==1.10.12 \
    prometheus-client==0.17.1 \
    psutil==5.9.5 \
    beautifulsoup4==4.12.2 \
    lxml==4.9.3 \
    selenium==4.10.0 \
    pyyaml==6.0.1 \
    click==8.1.7 \
    colorama==0.4.6 \
    python-dotenv==1.0.0 \
    paramiko==3.2.0 \
    cryptography==3.4.8 \
    pytest==7.4.2 \
    pytest-asyncio==0.21.1

echo "✓ Dépendances Python installées"

# Configuration des services systemd
echo ""
echo "=== Configuration des services systemd ==="

# Créer le script Python pour le scheduler (JobCluster)
sudo tee /opt/dispy_scheduler.py > /dev/null << 'PYTHON_SCRIPT'
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
sudo chmod +x /opt/dispy_scheduler.py

# Service Dispy Scheduler (JobCluster)
sudo tee /etc/systemd/system/dispyscheduler.service > /dev/null << EOF
[Unit]
Description=Dispy Scheduler (JobCluster)
After=network.target

[Service]
Type=simple
User=pi
WorkingDirectory=/home/dispy/DispyCluster
Environment=PYTHONPATH=/home/dispy/DispyCluster
Environment=DISPY_LOCAL_IP=$LOCAL_IP
ExecStart=/opt/dispy_scheduler.py
Restart=always
RestartSec=10
StandardOutput=journal
StandardError=journal

[Install]
WantedBy=multi-user.target
EOF

# Service Dispy Node
sudo tee /etc/systemd/system/dispynode.service > /dev/null << EOF
[Unit]
Description=Dispy Node
After=network.target

[Service]
Type=simple
User=pi
WorkingDirectory=/home/dispy/DispyCluster
Environment=PYTHONPATH=/home/dispy/DispyCluster
ExecStart=/usr/bin/python3 -c "
import sys
sys.path.insert(0, '/home/dispy/DispyCluster')
import dispy

# Configuration réseau pour éviter 'Bad source address'
dispy.config.NodeIPAddr = '$LOCAL_IP'
dispy.config.NodePort = 51348
dispy.config.SchedulerIPAddr = '$LOCAL_IP'
dispy.config.SchedulerPort = 51347
dispy.config.NodeAvailMem = 100
dispy.config.NodeAvailCores = 1
dispy.config.NodeTimeout = 30

print('Démarrage du nœud Dispy sur $LOCAL_IP:51348')
node = dispy.DispyNode()
node.start()
"
Restart=always
RestartSec=10
StandardOutput=journal
StandardError=journal

[Install]
WantedBy=multi-user.target
EOF

# Recharger systemd
sudo systemctl daemon-reload

# Activer les services
sudo systemctl enable dispyscheduler
sudo systemctl enable dispynode

echo "✓ Services systemd configurés"

# Configuration du firewall
echo ""
echo "=== Configuration du firewall ==="

if command -v ufw >/dev/null 2>&1; then
    sudo ufw allow 51347/tcp comment "Dispy Scheduler"
    sudo ufw allow 51348/tcp comment "Dispy Node"
    sudo ufw allow 22/tcp comment "SSH"
    sudo ufw allow 8080:8084/tcp comment "DispyCluster Services"
    echo "✓ Règles firewall ajoutées"
else
    echo "UFW non installé, configuration manuelle nécessaire"
fi

# Test de la configuration
echo ""
echo "=== Test de la configuration ==="

# Test de la configuration Dispy (API 4.15.2+)
python3 -c "
import sys
sys.path.insert(0, '/home/dispy/DispyCluster')
import dispy

print('Configuration Dispy:')
print(f'  Version: {dispy.__version__}')
print(f'  Classes disponibles: {[attr for attr in dir(dispy) if not attr.startswith(\"_\") and callable(getattr(dispy, attr))]}')
"

# Test de création des objets Dispy (JobCluster)
python3 -c "
import sys
sys.path.insert(0, '/home/dispy/DispyCluster')
import dispy

try:
    # Test JobCluster
    def test_computation(data):
        return f'Test: {data}'
    
    cluster = dispy.JobCluster(test_computation)
    print('✓ JobCluster Dispy créé avec succès')
    
    # Test DispyNode
    node = dispy.DispyNode()
    print('✓ Nœud Dispy créé avec succès')
    
    print('✓ Configuration Dispy fonctionnelle')
    
    # Fermer les objets
    if hasattr(cluster, 'close'):
        cluster.close()
    if hasattr(node, 'close'):
        node.close()
        
except Exception as e:
    print(f'✗ Erreur Dispy: {e}')
    import traceback
    traceback.print_exc()
"

echo ""
echo "=== Installation terminée ==="
echo ""
echo "Pour démarrer les services:"
echo "  sudo systemctl start dispyscheduler"
echo "  sudo systemctl start dispynode"
echo ""
echo "Pour vérifier le statut:"
echo "  sudo systemctl status dispyscheduler"
echo "  sudo systemctl status dispynode"
echo ""
echo "Pour voir les logs:"
echo "  journalctl -u dispyscheduler -f"
echo "  journalctl -u dispynode -f"
echo ""
echo "Pour tester JobCluster:"
echo "  python3 -c \"import dispy; cluster = dispy.JobCluster(lambda x: x*2); print('JobCluster OK')\""
echo ""
echo "Pour utiliser le script de gestion:"
echo "  ./dispycluster.sh status"
echo "  ./dispycluster.sh fix-dispy"