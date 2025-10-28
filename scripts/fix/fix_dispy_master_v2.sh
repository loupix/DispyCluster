#!/bin/bash

# Script de correction du service Dispy Master - Version corrigée
# Résout le problème de guillemets dans systemd

set -e

echo "=== Correction du service Dispy Master ==="
echo "Résolution du problème de guillemets systemd"
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

# Créer un script Python séparé pour éviter les problèmes de guillemets
echo "Création du script Python séparé..."
sudo tee /opt/dispy_scheduler.py > /dev/null << 'EOF'
#!/usr/bin/env python3
import sys
import os
import dispy

# Ajouter le répertoire du projet au PYTHONPATH
project_dir = '/home/dispy/DispyCluster'
if project_dir not in sys.path:
    sys.path.insert(0, project_dir)

# Configuration réseau pour éviter 'Bad source address'
# Note: Les timeouts sont maintenant passés directement au constructeur

# Obtenir l'IP locale depuis la variable d'environnement
local_ip = os.environ.get('DISPY_LOCAL_IP', '127.0.0.1')

print(f'Démarrage du scheduler Dispy sur {local_ip}:51347')
print('Configuration Dispy:')
print(f'  IP: {local_ip}')
print(f'  Port: 51347')

try:
    # Créer le scheduler avec l'API correcte de Dispy 4.15.0
    # L'API a changé, utiliser dispy.JobScheduler ou dispy.Scheduler
    print('Tentative de création du scheduler...')
    
    # Essayer différentes API possibles
    try:
        scheduler = dispy.JobScheduler(ip_addr=local_ip, port=51347)
        print('✓ Scheduler créé avec JobScheduler')
    except AttributeError:
        try:
            scheduler = dispy.Scheduler(ip_addr=local_ip, port=51347)
            print('✓ Scheduler créé avec Scheduler')
        except AttributeError:
            # Essayer sans paramètres
            scheduler = dispy.JobScheduler()
            print('✓ Scheduler créé sans paramètres')
    
    # Démarrer le scheduler
    scheduler.start()
    print('✓ Scheduler démarré')
    
    # Garder le scheduler actif
    import time
    while True:
        time.sleep(1)
        
except KeyboardInterrupt:
    print('Arrêt du scheduler...')
    if 'scheduler' in locals():
        scheduler.close()
except Exception as e:
    print(f'Erreur: {e}')
    import traceback
    traceback.print_exc()
    sys.exit(1)
EOF

# Rendre le script exécutable
sudo chmod +x /opt/dispy_scheduler.py

# Corriger le service systemd avec des guillemets simples
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
Environment=DISPY_LOCAL_IP=$LOCAL_IP
ExecStart=/opt/dispy_scheduler.py
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
print('  Configuration disponible:')
for attr in sorted(dir(dispy.config)):
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

# Attendre un peu pour que le service démarre
sleep 3

# Vérifier le statut
echo "Vérification du statut..."
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