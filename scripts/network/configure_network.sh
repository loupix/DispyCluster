#!/bin/bash

# Script de configuration réseau pour DispyCluster
# Résout les erreurs "Bad source address" et problèmes de communication

set -e

echo "=== Configuration réseau DispyCluster ==="
echo "Résolution des erreurs 'Bad source address'"
echo ""

# Fonction pour obtenir l'IP locale
get_local_ip() {
    local ip=""
    
    # Essayer plusieurs méthodes
    if command -v ip >/dev/null 2>&1; then
        ip=$(ip route get 8.8.8.8 2>/dev/null | grep -oP 'src \K\S+' 2>/dev/null || echo "")
    fi
    
    if [ -z "$ip" ]; then
        ip=$(hostname -I 2>/dev/null | awk '{print $1}' 2>/dev/null || echo "")
    fi
    
    if [ -z "$ip" ]; then
        ip=$(ifconfig 2>/dev/null | grep -oP 'inet \K\S+' | grep -v '127.0.0.1' | head -1 2>/dev/null || echo "")
    fi
    
    echo "$ip"
}

# Obtenir l'IP locale
LOCAL_IP=$(get_local_ip)
echo "IP locale détectée: $LOCAL_IP"

if [ -z "$LOCAL_IP" ]; then
    echo "✗ Impossible de détecter l'IP locale"
    echo "Vérifiez votre configuration réseau"
    exit 1
fi

echo "✓ IP locale: $LOCAL_IP"

# Configuration des services systemd pour Dispy
echo ""
echo "=== Configuration des services Dispy ===""

# Configuration du scheduler
echo "Configuration du scheduler Dispy..."
sudo tee /etc/systemd/system/dispyscheduler.service > /dev/null << EOF
[Unit]
Description=Dispy Scheduler
After=network.target

[Service]
Type=simple
User=pi
WorkingDirectory=/home/pi/DispyCluster
Environment=PYTHONPATH=/home/pi/DispyCluster
ExecStart=/usr/bin/python3 -c "
import dispy
import sys
sys.path.insert(0, '/home/pi/DispyCluster')

# Configuration réseau
dispy.config.SchedulerIPAddr = '$LOCAL_IP'
dispy.config.SchedulerPort = 51347
dispy.config.ClientTimeout = 60
dispy.config.NodeTimeout = 30

# Démarrer le scheduler
scheduler = dispy.JobScheduler()
scheduler.start()
"
Restart=always
RestartSec=10
StandardOutput=journal
StandardError=journal

[Install]
WantedBy=multi-user.target
EOF

# Configuration du nœud
echo "Configuration du nœud Dispy..."
sudo tee /etc/systemd/system/dispynode.service > /dev/null << EOF
[Unit]
Description=Dispy Node
After=network.target

[Service]
Type=simple
User=pi
WorkingDirectory=/home/pi/DispyCluster
Environment=PYTHONPATH=/home/pi/DispyCluster
ExecStart=/usr/bin/python3 -c "
import dispy
import sys
sys.path.insert(0, '/home/pi/DispyCluster')

# Configuration réseau
dispy.config.NodeIPAddr = '$LOCAL_IP'
dispy.config.NodePort = 51348
dispy.config.SchedulerIPAddr = '$LOCAL_IP'
dispy.config.SchedulerPort = 51347
dispy.config.NodeAvailMem = 100
dispy.config.NodeAvailCores = 1
dispy.config.NodeTimeout = 30

# Démarrer le nœud
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
echo "Rechargement de systemd..."
sudo systemctl daemon-reload

# Activer les services
echo "Activation des services..."
sudo systemctl enable dispyscheduler
sudo systemctl enable dispynode

# Configuration des ports dans le firewall
echo ""
echo "=== Configuration du firewall ==="

# Vérifier si ufw est installé
if command -v ufw >/dev/null 2>&1; then
    echo "Configuration du firewall UFW..."
    sudo ufw allow 51347/tcp comment "Dispy Scheduler"
    sudo ufw allow 51348/tcp comment "Dispy Node"
    sudo ufw allow 22/tcp comment "SSH"
    sudo ufw allow 8080:8084/tcp comment "DispyCluster Services"
    echo "✓ Règles firewall ajoutées"
else
    echo "UFW non installé, configuration manuelle nécessaire"
fi

# Configuration des services DispyCluster
echo ""
echo "=== Configuration des services DispyCluster ==="

# Mettre à jour la configuration des services
cat > config/network_config.py << EOF
# Configuration réseau pour DispyCluster
# Généré automatiquement

# IP locale détectée
LOCAL_IP = "$LOCAL_IP"

# Configuration des nœuds du cluster
CLUSTER_NODES = [
    "node6.lan", "node7.lan", "node8.lan", "node9.lan", 
    "node10.lan", "node11.lan", "node12.lan", "node13.lan", "node14.lan"
]

# Ports des services
SERVICE_PORTS = {
    "cluster_controller": 8081,
    "monitoring": 8082,
    "scheduler": 8083,
    "api_gateway": 8084,
    "scraper": 8080,
    "dispy_scheduler": 51347,
    "dispy_node": 51348,
    "node_exporter": 9100,
    "prometheus": 9090,
    "grafana": 3000
}

# Configuration Dispy
DISPY_CONFIG = {
    "scheduler_ip": LOCAL_IP,
    "scheduler_port": 51347,
    "node_ip": LOCAL_IP,
    "node_port": 51348,
    "client_timeout": 60,
    "node_timeout": 30,
    "node_avail_mem": 100,  # MB
    "node_avail_cores": 1
}

print("Configuration réseau DispyCluster:")
print(f"  IP locale: {LOCAL_IP}")
print(f"  Port scheduler: {SERVICE_PORTS['dispy_scheduler']}")
print(f"  Port nœud: {SERVICE_PORTS['dispy_node']}")
print(f"  Nœuds du cluster: {len(CLUSTER_NODES)}")
EOF

echo "✓ Configuration réseau créée dans config/network_config.py"

# Test de la configuration
echo ""
echo "=== Test de la configuration ==="

# Test de la configuration Python
python3 config/network_config.py

# Test de connectivité réseau
echo ""
echo "Test de connectivité réseau..."
for node in node6.lan node7.lan node8.lan node9.lan node10.lan node11.lan node12.lan node13.lan node14.lan; do
    if ping -c 1 -W 2 "$node" >/dev/null 2>&1; then
        echo "✓ $node: accessible"
    else
        echo "✗ $node: inaccessible"
    fi
done

echo ""
echo "=== Configuration terminée ==="
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
echo "Pour tester la communication:"
echo "  python3 -c \"import dispy; print('Dispy configuré:', dispy.config.SchedulerIPAddr)\""