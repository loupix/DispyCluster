#!/bin/bash

# Script d'installation worker Dispy pour JobCluster
# Compatible avec l'API Dispy 4.15.2+

set -e

echo "=== Installation Worker Dispy pour JobCluster ==="
echo "Installation optimisée pour l'API Dispy 4.15.2+"
echo ""

# Vérifier les privilèges
if [ "${EUID}" -ne 0 ]; then
    echo "Ce script doit être exécuté en root"
    exit 1
fi

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

# Installation des dépendances
echo ""
echo "=== Installation des dépendances ==="

# Fonction pour réparer le système de packages
repair_package_system() {
    echo "Réparation du système de packages..."
    
    # Corriger les packages cassés
    dpkg --configure -a || true
    
    # Nettoyer le cache
    apt-get clean
    apt-get autoclean
    
    # Réparer les dépendances
    apt-get -f install -y || true
    
    # Corriger spécifiquement raspberrypi-bootloader si nécessaire
    if dpkg -l | grep -q "raspberrypi-bootloader"; then
        echo "Correction du package raspberrypi-bootloader..."
        apt-get --fix-missing install raspberrypi-bootloader -y || true
    fi
    
    # Nettoyer les listes corrompues si nécessaire
    if [ ! -f /var/lib/apt/lists/lock ]; then
        rm -rf /var/lib/apt/lists/*
    fi
}

# Mettre à jour le système avec gestion d'erreurs
echo "Mise à jour du système de packages..."
if ! apt-get update; then
    echo "Erreur lors de la mise à jour, réparation du système..."
    repair_package_system
    apt-get update
fi

# Mise à jour des packages avec gestion d'erreurs
echo "Mise à jour des packages installés..."
if ! apt-get -y upgrade; then
    echo "Erreur lors de la mise à jour, réparation du système..."
    repair_package_system
    apt-get -y upgrade --fix-missing
fi

# Installer Python et pip avec gestion d'erreurs
echo "Installation des packages Python et utilitaires..."
if ! apt-get -y install python3 python3-pip python3-venv curl wget tar; then
    echo "Erreur lors de l'installation des packages, réparation..."
    repair_package_system
    apt-get -y install python3 python3-pip python3-venv curl wget tar
fi

# Mettre à jour pip
python3 -m pip install --upgrade pip setuptools wheel

# Installer Dispy 4.15.2+
echo "Installation de Dispy 4.15.2+..."
pip3 install --no-cache-dir dispy==4.15.2

# Vérifier l'installation
echo "Vérification de l'installation Dispy..."
python3 -c "import dispy; print(f'✓ Dispy {dispy.__version__} installé')"

# Créer l'utilisateur de service
echo ""
echo "=== Configuration de l'utilisateur de service ==="

echo "Création utilisateur de service 'dispy' si nécessaire..."
if ! id -u dispy >/dev/null 2>&1; then
    useradd -r -s /usr/sbin/nologin -d /var/lib/dispy dispy
    echo "✓ Utilisateur dispy créé"
else
    echo "✓ Utilisateur dispy existe déjà"
fi

# Créer le répertoire de travail
echo "Création du répertoire de travail..."
mkdir -p /var/lib/dispy
chown -R dispy:dispy /var/lib/dispy
chmod 755 /var/lib/dispy
echo "✓ Répertoire /var/lib/dispy créé et configuré"

# Créer le répertoire temporaire pour dispynode
echo "Création du répertoire temporaire dispynode..."
mkdir -p /tmp/dispy/node
chown -R dispy:dispy /tmp/dispy
chmod 755 /tmp/dispy
chmod 755 /tmp/dispy/node
echo "✓ Répertoire /tmp/dispy créé et configuré"

# Créer le script Python pour le worker
echo ""
echo "=== Création du script worker ==="

cat >/opt/dispy_worker.py <<'PYTHON_SCRIPT'
#!/usr/bin/env python3
# Script worker Dispy pour JobCluster (API 4.15.2+)
# Utilise dispynode.py directement au lieu de l'API Python

import sys
import os
import subprocess
import signal
import time

# Obtenir l'IP locale depuis la variable d'environnement
local_ip = os.environ.get('DISPY_LOCAL_IP', '127.0.0.1')

print(f'=== DispyNode Worker pour JobCluster ===')
print(f'Démarrage sur {local_ip}:51348')
print('Utilisation de dispynode.py (API 4.15.2+)')

# Trouver le script dispynode.py
dispy_paths = [
    '/usr/local/bin/dispynode.py',
    '/usr/bin/dispynode.py',
    '/opt/dispynode.py'
]

dispy_script = None
for path in dispy_paths:
    if os.path.exists(path):
        dispy_script = path
        break

if not dispy_script:
    # Essayer de trouver via Python
    try:
        import dispy
        dispy_dir = os.path.dirname(dispy.__file__)
        dispy_script = os.path.join(dispy_dir, 'dispynode.py')
        if not os.path.exists(dispy_script):
            dispy_script = None
    except ImportError:
        pass

if not dispy_script:
    print('✗ Script dispynode.py introuvable')
    sys.exit(1)

print(f'✓ Script dispynode trouvé: {dispy_script}')

# Configuration du processus dispynode
process = None

def signal_handler(signum, frame):
    print('Signal reçu, arrêt du worker...')
    if process:
        process.terminate()
        try:
            process.wait(timeout=5)
        except subprocess.TimeoutExpired:
            process.kill()
    sys.exit(0)

# Enregistrer les gestionnaires de signaux
signal.signal(signal.SIGTERM, signal_handler)
signal.signal(signal.SIGINT, signal_handler)

try:
    # Créer le répertoire temporaire si nécessaire
    import stat
    tmp_dispy_dir = '/tmp/dispy/node'
    os.makedirs(tmp_dispy_dir, exist_ok=True)
    os.chmod(tmp_dispy_dir, stat.S_IRUSR | stat.S_IWUSR | stat.S_IXUSR | 
             stat.S_IRGRP | stat.S_IXGRP | stat.S_IROTH | stat.S_IXOTH)
    
    # Démarrer dispynode avec les paramètres appropriés
    cmd = [
        sys.executable, dispy_script,
        '--host', local_ip,
        '--name', f'worker-{local_ip}',
        '--daemon'
    ]
    
    print(f'Commande: {" ".join(cmd)}')
    print('Démarrage de dispynode...')
    
    process = subprocess.Popen(
        cmd,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True
    )
    
    print('✓ DispyNode démarré avec succès')
    print('Nœud prêt à recevoir des tâches du JobCluster')
    
    # Attendre que le processus se termine
    while True:
        if process.poll() is not None:
            stdout, stderr = process.communicate()
            if stdout:
                print(f'Sortie: {stdout}')
            if stderr:
                print(f'Erreur: {stderr}')
            print(f'Processus terminé avec le code: {process.returncode}')
            break
        time.sleep(1)
        
except Exception as e:
    print(f'Erreur: {e}')
    import traceback
    traceback.print_exc()
    if process:
        process.terminate()
    sys.exit(1)
PYTHON_SCRIPT

# Rendre le script exécutable
chmod +x /opt/dispy_worker.py

# Créer le service systemd
echo ""
echo "=== Configuration du service systemd ==="

cat >/etc/systemd/system/dispy-worker.service <<EOF
[Unit]
Description=Dispy Worker (DispyNode pour JobCluster)
After=network-online.target
Wants=network-online.target

[Service]
Type=simple
User=dispy
Group=dispy
WorkingDirectory=/opt
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

# Recharger systemd
systemctl daemon-reload

# Activer le service
systemctl enable dispy-worker.service

# Test de la configuration avant de démarrer
echo ""
echo "=== Test de la configuration ==="

echo "Test de la configuration dispynode..."
python3 -c "
import sys
import os
import subprocess

# Trouver le script dispynode.py
dispy_paths = [
    '/usr/local/bin/dispynode.py',
    '/usr/bin/dispynode.py',
    '/opt/dispynode.py'
]

dispy_script = None
for path in dispy_paths:
    if os.path.exists(path):
        dispy_script = path
        break

if not dispy_script:
    try:
        import dispy
        dispy_dir = os.path.dirname(dispy.__file__)
        dispy_script = os.path.join(dispy_dir, 'dispynode.py')
        if not os.path.exists(dispy_script):
            dispy_script = None
    except ImportError:
        pass

if dispy_script:
    print(f'✓ Script dispynode trouvé: {dispy_script}')
    
    # Test rapide de dispynode
    try:
        result = subprocess.run([
            sys.executable, dispy_script, '--help'
        ], capture_output=True, text=True, timeout=10)
        
        if result.returncode == 0:
            print('✓ dispynode.py fonctionne correctement')
        else:
            print(f'✗ Erreur dispynode: {result.stderr}')
    except Exception as e:
        print(f'✗ Erreur test dispynode: {e}')
else:
    print('✗ Script dispynode.py introuvable')
"

# Démarrer le service
echo ""
echo "Démarrage du service dispy-worker..."
systemctl start dispy-worker.service

# Attendre un peu pour que le service démarre
sleep 3

# Vérifier le statut
echo "Vérification du statut du service..."
systemctl status dispy-worker.service --no-pager

# Configuration du firewall
echo ""
echo "=== Configuration du firewall ==="

if command -v ufw >/dev/null 2>&1; then
    ufw allow 51348/tcp comment "Dispy Worker"
    ufw allow 22/tcp comment "SSH"
    echo "✓ Règles firewall ajoutées"
else
    echo "UFW non installé, configuration manuelle nécessaire"
fi

# Installation de node_exporter (optionnel)
echo ""
echo "=== Installation de node_exporter (optionnel) ==="

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
if [ -f "${SCRIPT_DIR}/node_exporter_install.sh" ]; then
    echo "Installation de node_exporter..."
    bash "${SCRIPT_DIR}/node_exporter_install.sh"
else
    echo "Script node_exporter_install.sh introuvable, installation manuelle nécessaire"
fi

echo ""
echo "=== Installation worker terminée ==="
echo ""
echo "Le worker est maintenant prêt à recevoir des tâches du JobCluster !"
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
echo "  python3 -c \"import dispy; print(f'Dispy {dispy.__version__} installé')\""
echo "  python3 -c \"import subprocess; subprocess.run(['python3', '-m', 'dispynode', '--help'])\""
echo ""
echo "Le worker écoute sur le port 51348 et est prêt pour JobCluster !"