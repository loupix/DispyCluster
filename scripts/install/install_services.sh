#!/bin/bash

# Script d'installation des nouveaux services pour DispyCluster
# Ce script installe et configure les services de contrôle, monitoring, 
# planification et API Gateway

set -e

echo "=== Installation des services DispyCluster ==="

# Vérifier que nous sommes sur le nœud maître
if [ ! -f "/etc/systemd/system/dispyscheduler.service" ]; then
    echo "Erreur: Ce script doit être exécuté sur le nœud maître"
    echo "Assurez-vous d'avoir installé le maître avec scripts/install_master.sh"
    exit 1
fi

# Créer le répertoire des services s'il n'existe pas
mkdir -p /opt/dispycluster/services
mkdir -p /opt/dispycluster/logs

# Copier les services
echo "Copie des services..."
cp services/cluster_controller.py /opt/dispycluster/services/
cp services/monitoring_service.py /opt/dispycluster/services/
cp services/scheduler_service.py /opt/dispycluster/services/
cp services/api_gateway.py /opt/dispycluster/services/

# Installer les dépendances Python
echo "Installation des dépendances Python..."
pip3 install fastapi uvicorn aiohttp httpx apscheduler requests pydantic

# Créer les services systemd
echo "Création des services systemd..."

# Service de contrôle du cluster
cat > /etc/systemd/system/dispycluster-controller.service << 'EOF'
[Unit]
Description=DispyCluster Controller Service
After=network.target dispyscheduler.service
Wants=dispyscheduler.service

[Service]
Type=simple
User=pi
WorkingDirectory=/opt/dispycluster
ExecStart=/usr/bin/python3 /opt/dispycluster/services/cluster_controller.py
Restart=always
RestartSec=10
StandardOutput=journal
StandardError=journal

[Install]
WantedBy=multi-user.target
EOF

# Service de monitoring
cat > /etc/systemd/system/dispycluster-monitoring.service << 'EOF'
[Unit]
Description=DispyCluster Monitoring Service
After=network.target
Wants=network.target

[Service]
Type=simple
User=pi
WorkingDirectory=/opt/dispycluster
ExecStart=/usr/bin/python3 /opt/dispycluster/services/monitoring_service.py
Restart=always
RestartSec=10
StandardOutput=journal
StandardError=journal

[Install]
WantedBy=multi-user.target
EOF

# Service de planification
cat > /etc/systemd/system/dispycluster-scheduler.service << 'EOF'
[Unit]
Description=DispyCluster Scheduler Service
After=network.target dispycluster-controller.service
Wants=dispycluster-controller.service

[Service]
Type=simple
User=pi
WorkingDirectory=/opt/dispycluster
ExecStart=/usr/bin/python3 /opt/dispycluster/services/scheduler_service.py
Restart=always
RestartSec=10
StandardOutput=journal
StandardError=journal

[Install]
WantedBy=multi-user.target
EOF

# Service API Gateway
cat > /etc/systemd/system/dispycluster-gateway.service << 'EOF'
[Unit]
Description=DispyCluster API Gateway
After=network.target dispycluster-controller.service dispycluster-monitoring.service dispycluster-scheduler.service
Wants=dispycluster-controller.service dispycluster-monitoring.service dispycluster-scheduler.service

[Service]
Type=simple
User=pi
WorkingDirectory=/opt/dispycluster
ExecStart=/usr/bin/python3 /opt/dispycluster/services/api_gateway.py
Restart=always
RestartSec=10
StandardOutput=journal
StandardError=journal

[Install]
WantedBy=multi-user.target
EOF

# Créer un script de démarrage
cat > /opt/dispycluster/start_services.sh << 'EOF'
#!/bin/bash

echo "Démarrage des services DispyCluster..."

# Démarrer les services dans l'ordre
systemctl start dispycluster-controller
sleep 5

systemctl start dispycluster-monitoring
sleep 5

systemctl start dispycluster-scheduler
sleep 5

systemctl start dispycluster-gateway

echo "Services démarrés. Vérification du statut..."
systemctl status dispycluster-controller dispycluster-monitoring dispycluster-scheduler dispycluster-gateway
EOF

chmod +x /opt/dispycluster/start_services.sh

# Créer un script d'arrêt
cat > /opt/dispycluster/stop_services.sh << 'EOF'
#!/bin/bash

echo "Arrêt des services DispyCluster..."

systemctl stop dispycluster-gateway
systemctl stop dispycluster-scheduler
systemctl stop dispycluster-monitoring
systemctl stop dispycluster-controller

echo "Services arrêtés."
EOF

chmod +x /opt/dispycluster/stop_services.sh

# Créer un script de vérification
cat > /opt/dispycluster/check_services.sh << 'EOF'
#!/bin/bash

echo "=== Vérification des services DispyCluster ==="

services=("dispycluster-controller" "dispycluster-monitoring" "dispycluster-scheduler" "dispycluster-gateway")

for service in "${services[@]}"; do
    if systemctl is-active --quiet $service; then
        echo "✓ $service: ACTIF"
    else
        echo "✗ $service: INACTIF"
    fi
done

echo ""
echo "=== Ports des services ==="
echo "Contrôleur: http://localhost:8081"
echo "Monitoring: http://localhost:8082"
echo "Planificateur: http://localhost:8083"
echo "API Gateway: http://localhost:8084"
echo "Scraper (existant): http://localhost:8080"

echo ""
echo "=== Test rapide de l'API Gateway ==="
curl -s http://localhost:8084/health | python3 -m json.tool || echo "API Gateway non accessible"
EOF

chmod +x /opt/dispycluster/check_services.sh

# Recharger systemd
systemctl daemon-reload

# Activer les services
systemctl enable dispycluster-controller
systemctl enable dispycluster-monitoring
systemctl enable dispycluster-scheduler
systemctl enable dispycluster-gateway

echo ""
echo "=== Installation terminée ==="
echo ""
echo "Services installés:"
echo "- Contrôleur du cluster (port 8081)"
echo "- Monitoring (port 8082)"
echo "- Planificateur (port 8083)"
echo "- API Gateway (port 8084)"
echo ""
echo "Pour démarrer les services:"
echo "  sudo systemctl start dispycluster-controller dispycluster-monitoring dispycluster-scheduler dispycluster-gateway"
echo ""
echo "Ou utiliser le script:"
echo "  sudo /opt/dispycluster/start_services.sh"
echo ""
echo "Pour vérifier le statut:"
echo "  sudo /opt/dispycluster/check_services.sh"
echo ""
echo "Logs des services:"
echo "  journalctl -u dispycluster-controller -f"
echo "  journalctl -u dispycluster-monitoring -f"
echo "  journalctl -u dispycluster-scheduler -f"
echo "  journalctl -u dispycluster-gateway -f"