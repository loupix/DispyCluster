#!/bin/bash

# Script de correction du service Dispy Master - Version finale
# Basé sur la découverte de l'API Dispy 4.15.0

set -e

echo "=== Correction du service Dispy Master ==="
echo "Découverte et utilisation de la bonne API Dispy 4.15.0"
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

# Découvrir l'API Dispy
echo "Découverte de l'API Dispy..."
python3 scripts/test/discover_dispy_api.py

# Créer un script Python basé sur la découverte
echo "Création du script Python basé sur la découverte..."
sudo tee /opt/dispy_scheduler.py > /dev/null << 'EOF'
#!/usr/bin/env python3
# Script de scheduler Dispy basé sur la découverte de l'API

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
    print('Découverte de l\'API Dispy...')
    
    # Lister toutes les classes disponibles
    classes = [attr for attr in dir(dispy) if not attr.startswith('_') and callable(getattr(dispy, attr))]
    print(f'Classes disponibles: {classes}')
    
    # Utiliser JobCluster (la nouvelle API de Dispy 4.15.2)
    print('Utilisation de JobCluster (nouvelle API Dispy 4.15.2)...')
    
    # Définir une fonction de computation par défaut
    def default_computation(data):
        """Fonction de computation par défaut pour le cluster"""
        return f"Traité: {data}"
    
    # Créer un JobCluster avec une fonction de computation
    try:
        # JobCluster nécessite une fonction de computation
        scheduler = dispy.JobCluster(default_computation)
        print('✓ JobCluster créé avec succès')
    except Exception as e:
        print(f'✗ JobCluster échoué: {e}')
        
        # Essayer SharedJobCluster
        try:
            scheduler = dispy.SharedJobCluster(default_computation)
            print('✓ SharedJobCluster créé avec succès')
        except Exception as e:
            print(f'✗ SharedJobCluster échoué: {e}')
            raise Exception('Impossible de créer un cluster avec l\'API disponible')
    
    print(f'Type de scheduler: {type(scheduler).__name__}')
    
    # JobCluster n'a pas besoin d'être démarré explicitement
    print('JobCluster créé et prêt à recevoir des jobs')
    print('Méthodes disponibles:', [m for m in dir(scheduler) if not m.startswith('_') and callable(getattr(scheduler, m))])
    
    # Garder le cluster actif
    import time
    print('Cluster actif, en attente de jobs...')
    while True:
        time.sleep(1)
        
except KeyboardInterrupt:
    print('Arrêt du scheduler...')
    if 'scheduler' in locals() and hasattr(scheduler, 'close'):
        scheduler.close()
except Exception as e:
    print(f'Erreur: {e}')
    import traceback
    traceback.print_exc()
    sys.exit(1)
EOF

# Rendre le script exécutable
sudo chmod +x /opt/dispy_scheduler.py

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