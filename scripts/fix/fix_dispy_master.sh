#!/bin/bash

# Script de correction du service Dispy Master
# Corrige le problème du binaire dispyscheduler manquant

set -e

echo "=== Correction du service Dispy Master ==="
echo "Résolution du problème 'dispyscheduler: No such file or directory'"
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

# Arrêter le service existant
echo "Arrêt du service dispy-master..."
sudo systemctl stop dispy-master.service 2>/dev/null || true

# Corriger le service systemd
echo "Correction du service systemd..."
sudo tee /etc/systemd/system/dispy-master.service > /dev/null << EOF
[Unit]
Description=Dispy Master (dispyscheduler)
After=network-online.target
Wants=network-online.target

[Service]
Type=simple
User=pi
WorkingDirectory=/home/dispy/DispyCluster
Environment=PYTHONPATH=/home/dispy/DispyCluster
ExecStart=/usr/bin/python3 -c "
import sys
sys.path.insert(0, '/home/dispy/DispyCluster')
import dispy
import socket

# Configuration réseau pour éviter 'Bad source address'
dispy.config.ClientTimeout = 60
dispy.config.NodeTimeout = 30

print('Démarrage du scheduler Dispy sur $LOCAL_IP:51347')
print('Configuration Dispy:')
print(f'  Client Timeout: {dispy.config.ClientTimeout}s')
print(f'  Node Timeout: {dispy.config.NodeTimeout}s')

# Créer le scheduler avec l'IP spécifiée
scheduler = dispy.JobScheduler(ip_addr='$LOCAL_IP', port=51347)
scheduler.start()
"
Restart=always
RestartSec=10
StandardOutput=journal
StandardError=journal

[Install]
WantedBy=multi-user.target
EOF

# Recharger systemd
echo "Rechargement de systemd..."
sudo systemctl daemon-reload

# Activer le service
echo "Activation du service..."
sudo systemctl enable dispy-master.service

# Vérifier que Dispy est installé
echo "Vérification de l'installation Dispy..."
if python3 -c "import dispy" 2>/dev/null; then
    echo "✓ Dispy est installé"
else
    echo "Installation de Dispy..."
    pip3 install dispy==4.15.0
fi

# Test de la configuration
echo "Test de la configuration..."
python3 -c "
import sys
sys.path.insert(0, '/home/dispy/DispyCluster')
import dispy

print('Configuration Dispy:')
print(f'  Version Dispy: {dispy.__version__}')
print(f'  Configuration disponible:')
for attr in dir(dispy.config):
    if not attr.startswith('_'):
        try:
            value = getattr(dispy.config, attr)
            print(f'    {attr}: {value}')
        except:
            pass
"

# Démarrer le service
echo "Démarrage du service..."
sudo systemctl start dispy-master.service

# Vérifier le statut
echo "Vérification du statut..."
sleep 2
sudo systemctl status dispy-master.service --no-pager

# Vérifier les ports
echo ""
echo "Vérification des ports..."
if sudo netstat -tlnp 2>/dev/null | grep -q "51347"; then
    echo "✓ Port 51347 (scheduler) ouvert"
else
    echo "✗ Port 51347 non ouvert"
fi

echo ""
echo "=== Correction terminée ==="
echo ""
echo "Pour vérifier le service:"
echo "  sudo systemctl status dispy-master.service"
echo ""
echo "Pour voir les logs:"
echo "  journalctl -u dispy-master.service -f"
echo ""
echo "Pour redémarrer le service:"
echo "  sudo systemctl restart dispy-master.service"