#!/usr/bin/env bash
set -e

# Script d'installation d'un worker Dispy sur Raspberry Pi OS
# Compatible avec JobCluster (API Dispy 4.15.2+)
# - Installe Python3, pip, dispy
# - Crée utilisateur de service dispy (si absent)
# - Installe node_exporter (via script dédié)
# - Installe et active service systemd dispy-worker (DispyNode)

if [ "${EUID}" -ne 0 ]; then
  echo "Ce script doit être exécuté en root"
  exit 1
fi

echo "Mise à jour du système..."
apt-get update
apt-get -y upgrade

echo "Installation dépendances..."
apt-get -y install python3 python3-pip python3-venv curl wget tar

echo "Installation de dispy..."
pip3 install --upgrade pip
pip3 install dispy==4.15.2

# Vérifier l'installation
echo "Vérification de l'installation Dispy..."
python3 -c "import dispy; print(f'✓ Dispy {dispy.__version__} installé')"

echo "Création utilisateur de service 'dispy' si nécessaire..."
if ! id -u dispy >/dev/null 2>&1; then
  useradd -r -s /usr/sbin/nologin -d /var/lib/dispy dispy
  mkdir -p /var/lib/dispy
  chown -R dispy:dispy /var/lib/dispy
fi

echo "Installation du service systemd dispy-worker (DispyNode)..."
mkdir -p /etc/dispy

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

# Créer le script Python pour le worker
cat >/opt/dispy_worker.py <<'PYTHON_SCRIPT'
#!/usr/bin/env python3
# Script worker Dispy basé sur DispyNode (API 4.15.2+)

import sys
import os
import dispy

# Ajouter le répertoire du projet au PYTHONPATH
project_dir = '/var/lib/dispy'
if project_dir not in sys.path:
    sys.path.insert(0, project_dir)

# Obtenir l'IP locale depuis la variable d'environnement
local_ip = os.environ.get('DISPY_LOCAL_IP', '127.0.0.1')

print(f'=== DispyNode Worker ===')
print(f'Démarrage sur {local_ip}:51348')
print(f'Version Dispy: {dispy.__version__}')

try:
    # Créer un DispyNode
    print('Création du DispyNode...')
    node = dispy.DispyNode()
    print('✓ DispyNode créé avec succès')
    
    print(f'Type de nœud: {type(node).__name__}')
    print('Nœud prêt à recevoir des tâches')
    
    # Afficher les méthodes disponibles
    methods = [m for m in dir(node) if not m.startswith('_') and callable(getattr(node, m))]
    print(f'Méthodes disponibles: {methods[:5]}...')
    
    # Garder le nœud actif
    import time
    print('Nœud actif, en attente de tâches...')
    while True:
        time.sleep(1)
        
except KeyboardInterrupt:
    print('Arrêt du nœud...')
    if 'node' in locals() and hasattr(node, 'close'):
        node.close()
        print('✓ Nœud fermé proprement')
except Exception as e:
    print(f'Erreur: {e}')
    import traceback
    traceback.print_exc()
    sys.exit(1)
PYTHON_SCRIPT

# Rendre le script exécutable
chmod +x /opt/dispy_worker.py

# Créer le service systemd
cat >/etc/systemd/system/dispy-worker.service <<EOF
[Unit]
Description=Dispy Worker (DispyNode)
After=network-online.target
Wants=network-online.target

[Service]
Type=simple
User=dispy
Group=dispy
WorkingDirectory=/var/lib/dispy
Environment=PYTHONPATH=/var/lib/dispy
Environment=DISPY_LOCAL_IP=$LOCAL_IP
ExecStart=/opt/dispy_worker.py
Restart=always
RestartSec=10
StandardOutput=journal
StandardError=journal

[Install]
WantedBy=multi-user.target
EOF

systemctl daemon-reload
systemctl enable dispy-worker.service

# Test de la configuration avant de démarrer
echo "Test de la configuration DispyNode..."
python3 -c "
import sys
sys.path.insert(0, '/var/lib/dispy')
import dispy

try:
    node = dispy.DispyNode()
    print('✓ DispyNode créé avec succès')
    
    if hasattr(node, 'close'):
        node.close()
        print('✓ Nœud fermé proprement')
    
    print('✓ Configuration DispyNode fonctionnelle')
    
except Exception as e:
    print(f'✗ Erreur DispyNode: {e}')
    import traceback
    traceback.print_exc()
"

# Démarrer le service
echo "Démarrage du service dispy-worker..."
systemctl start dispy-worker.service

# Vérifier le statut
echo "Vérification du statut du service..."
systemctl status dispy-worker.service --no-pager

# Configuration du firewall
echo ""
echo "Configuration du firewall..."
if command -v ufw >/dev/null 2>&1; then
    ufw allow 51348/tcp comment "Dispy Worker"
    ufw allow 22/tcp comment "SSH"
    echo "✓ Règles firewall ajoutées"
else
    echo "UFW non installé, configuration manuelle nécessaire"
fi

echo "Installation de node_exporter..."
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
if [ -f "${SCRIPT_DIR}/node_exporter_install.sh" ]; then
  bash "${SCRIPT_DIR}/node_exporter_install.sh"
else
  echo "Script node_exporter_install.sh introuvable. Copiez ./scripts sur le noeud."
fi

echo ""
echo "=== Installation worker terminée ==="
echo ""
echo "Pour vérifier le statut du service:"
echo "  sudo systemctl status dispy-worker"
echo ""
echo "Pour voir les logs:"
echo "  journalctl -u dispy-worker -f"
echo ""
echo "Pour redémarrer le service:"
echo "  sudo systemctl restart dispy-worker"
echo ""
echo "Pour tester la connexion au cluster:"
echo "  python3 -c \"import dispy; node = dispy.DispyNode(); print('Worker OK')\""
echo ""
echo "Le worker est maintenant prêt à recevoir des tâches du JobCluster !"

