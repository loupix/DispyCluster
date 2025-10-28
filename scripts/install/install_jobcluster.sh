#!/bin/bash

# Script d'installation JobCluster Dispy 4.15.2+
# Installation optimisée pour la nouvelle API

set -e

echo "=== Installation JobCluster Dispy 4.15.2+ ==="
echo "Installation optimisée pour la nouvelle API Dispy"
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

# Vérifier les privilèges
if [ "${EUID}" -ne 0 ]; then
    echo "Ce script doit être exécuté en root"
    exit 1
fi

# Installation des dépendances
echo ""
echo "=== Installation des dépendances ==="

# Mettre à jour le système
apt-get update
apt-get -y upgrade

# Installer Python et pip
apt-get -y install python3 python3-pip python3-venv

# Mettre à jour pip
python3 -m pip install --upgrade pip setuptools wheel

# Installer Dispy 4.15.2+
echo "Installation de Dispy 4.15.2+..."
pip3 install --no-cache-dir dispy==4.15.2

# Vérifier l'installation
echo "Vérification de l'installation Dispy..."
python3 -c "import dispy; print(f'✓ Dispy {dispy.__version__} installé')"

# Créer le script Python pour JobCluster
echo ""
echo "=== Création du script JobCluster ==="

cat >/opt/dispy_jobcluster.py <<'PYTHON_SCRIPT'
#!/usr/bin/env python3
# Script JobCluster Dispy 4.15.2+ - Optimisé pour le scraping

import sys
import os
import dispy
import time

# Ajouter le répertoire du projet au PYTHONPATH
project_dir = '/home/dispy/DispyCluster'
if project_dir not in sys.path:
    sys.path.insert(0, project_dir)

# Obtenir l'IP locale depuis la variable d'environnement
local_ip = os.environ.get('DISPY_LOCAL_IP', '127.0.0.1')

print(f'=== JobCluster Dispy 4.15.2+ ===')
print(f'Démarrage sur {local_ip}:51347')
print(f'Version Dispy: {dispy.__version__}')

try:
    # Fonction de computation pour le scraping
    def scraping_computation(url_data):
        """Fonction de computation pour le scraping web"""
        import requests
        from bs4 import BeautifulSoup
        
        try:
            url = url_data.get('url', '')
            timeout = url_data.get('timeout', 10)
            
            print(f'Scraping: {url}')
            
            # Faire la requête
            response = requests.get(url, timeout=timeout)
            response.raise_for_status()
            
            # Parser le HTML
            soup = BeautifulSoup(response.content, 'html.parser')
            
            # Extraire les données
            result = {
                'url': url,
                'status': response.status_code,
                'title': soup.title.string if soup.title else '',
                'links': len(soup.find_all('a')),
                'images': len(soup.find_all('img')),
                'text_length': len(soup.get_text()),
                'success': True
            }
            
            return result
            
        except Exception as e:
            return {
                'url': url_data.get('url', ''),
                'error': str(e),
                'success': False
            }
    
    # Créer le JobCluster avec la fonction de scraping
    print('Création du JobCluster pour le scraping...')
    cluster = dispy.JobCluster(scraping_computation)
    print('✓ JobCluster créé avec succès')
    
    print(f'Type de cluster: {type(cluster).__name__}')
    print('Cluster prêt à recevoir des tâches de scraping')
    
    # Afficher les méthodes disponibles
    methods = [m for m in dir(cluster) if not m.startswith('_') and callable(getattr(cluster, m))]
    print(f'Méthodes disponibles: {methods[:5]}...')
    
    # Garder le cluster actif
    print('Cluster actif, en attente de tâches...')
    while True:
        time.sleep(1)
        
except KeyboardInterrupt:
    print('Arrêt du cluster...')
    if 'cluster' in locals() and hasattr(cluster, 'close'):
        cluster.close()
        print('✓ Cluster fermé proprement')
except Exception as e:
    print(f'Erreur: {e}')
    import traceback
    traceback.print_exc()
    sys.exit(1)
PYTHON_SCRIPT

# Rendre le script exécutable
chmod +x /opt/dispy_jobcluster.py

# Créer le service systemd
echo ""
echo "=== Configuration du service systemd ==="

cat >/etc/systemd/system/dispy-jobcluster.service <<EOF
[Unit]
Description=Dispy JobCluster (Scraping)
After=network-online.target
Wants=network-online.target

[Service]
Type=simple
User=pi
WorkingDirectory=/home/dispy/DispyCluster
Environment=PYTHONPATH=/home/dispy/DispyCluster
Environment=DISPY_LOCAL_IP=$LOCAL_IP
ExecStart=/opt/dispy_jobcluster.py
Restart=always
RestartSec=10
StandardOutput=journal
StandardError=journal

[Install]
WantedBy=multi-user.target
EOF

# Recharger systemd
systemctl daemon-reload

# Activer le service
systemctl enable dispy-jobcluster.service

# Configuration du firewall
echo ""
echo "=== Configuration du firewall ==="

if command -v ufw >/dev/null 2>&1; then
    ufw allow 51347/tcp comment "Dispy JobCluster"
    ufw allow 22/tcp comment "SSH"
    ufw allow 8080:8084/tcp comment "DispyCluster Services"
    echo "✓ Règles firewall ajoutées"
else
    echo "UFW non installé, configuration manuelle nécessaire"
fi

# Test de la configuration
echo ""
echo "=== Test de la configuration ==="

# Test JobCluster
python3 -c "
import sys
sys.path.insert(0, '/home/dispy/DispyCluster')
import dispy

try:
    def test_computation(data):
        return f'Test réussi: {data}'
    
    cluster = dispy.JobCluster(test_computation)
    print('✓ JobCluster créé avec succès')
    
    if hasattr(cluster, 'close'):
        cluster.close()
        print('✓ Cluster fermé proprement')
    
    print('✓ Configuration JobCluster fonctionnelle')
    
except Exception as e:
    print(f'✗ Erreur JobCluster: {e}')
    import traceback
    traceback.print_exc()
"

echo ""
echo "=== Installation terminée ==="
echo ""
echo "Pour démarrer le service:"
echo "  sudo systemctl start dispy-jobcluster"
echo ""
echo "Pour vérifier le statut:"
echo "  sudo systemctl status dispy-jobcluster"
echo ""
echo "Pour voir les logs:"
echo "  journalctl -u dispy-jobcluster -f"
echo ""
echo "Pour tester JobCluster:"
echo "  python3 -c \"import dispy; cluster = dispy.JobCluster(lambda x: x*2); print('JobCluster OK')\""
echo ""
echo "Pour utiliser le script de gestion:"
echo "  ./dispycluster.sh status"
echo "  ./dispycluster.sh fix-dispy"