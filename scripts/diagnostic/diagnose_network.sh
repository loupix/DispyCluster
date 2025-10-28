#!/bin/bash

# Script de diagnostic et réparation des problèmes réseau DispyCluster
# Résout les erreurs "Bad source address" et problèmes de communication

set -e

echo "=== Diagnostic réseau DispyCluster ==="
echo "Résolution des erreurs 'Bad source address'"
echo ""

# Fonction pour obtenir l'IP locale
get_local_ip() {
    # Essayer plusieurs méthodes pour obtenir l'IP locale
    local ip=""
    
    # Méthode 1: ip route
    if command -v ip >/dev/null 2>&1; then
        ip=$(ip route get 8.8.8.8 2>/dev/null | grep -oP 'src \K\S+' 2>/dev/null || echo "")
    fi
    
    # Méthode 2: hostname -I
    if [ -z "$ip" ]; then
        ip=$(hostname -I 2>/dev/null | awk '{print $1}' 2>/dev/null || echo "")
    fi
    
    # Méthode 3: ifconfig
    if [ -z "$ip" ]; then
        ip=$(ifconfig 2>/dev/null | grep -oP 'inet \K\S+' | grep -v '127.0.0.1' | head -1 2>/dev/null || echo "")
    fi
    
    echo "$ip"
}

# Fonction pour tester la connectivité
test_connectivity() {
    local node=$1
    echo "Test de connectivité vers $node..."
    
    # Test ping
    if ping -c 1 -W 2 "$node" >/dev/null 2>&1; then
        echo "✓ Ping vers $node: OK"
        return 0
    else
        echo "✗ Ping vers $node: ÉCHEC"
        return 1
    fi
}

# Fonction pour vérifier les ports
test_port() {
    local node=$1
    local port=$2
    echo "Test du port $port sur $node..."
    
    if timeout 5 bash -c "</dev/tcp/$node/$port" 2>/dev/null; then
        echo "✓ Port $port sur $node: OUVERT"
        return 0
    else
        echo "✗ Port $port sur $node: FERMÉ"
        return 1
    fi
}

echo "=== Diagnostic réseau ==="

# Obtenir l'IP locale
LOCAL_IP=$(get_local_ip)
echo "IP locale détectée: $LOCAL_IP"

# Vérifier la configuration réseau
echo ""
echo "Configuration réseau actuelle:"
ip addr show 2>/dev/null || ifconfig 2>/dev/null

echo ""
echo "Routes réseau:"
ip route show 2>/dev/null || route -n 2>/dev/null

# Tester la connectivité vers les nœuds
echo ""
echo "=== Test de connectivité des nœuds ==="

# Lire l'inventaire des nœuds
if [ -f "inventory/nodes.yaml" ]; then
    echo "Lecture de l'inventaire des nœuds..."
    
    # Extraire les nœuds du fichier YAML
    NODES=$(grep -E "^\s*host:" inventory/nodes.yaml | sed 's/.*host:\s*//' | tr -d ' ' | tr '\n' ' ')
    
    for node in $NODES; do
        if [ -n "$node" ]; then
            test_connectivity "$node"
            test_port "$node" 22
            test_port "$node" 51348
            echo ""
        fi
    done
else
    echo "Fichier inventory/nodes.yaml non trouvé"
    echo "Test avec les nœuds par défaut..."
    
    for node in node6.lan node7.lan node8.lan node9.lan node10.lan node11.lan node12.lan node13.lan node14.lan; do
        test_connectivity "$node"
        test_port "$node" 22
        test_port "$node" 51348
        echo ""
    done
fi

echo "=== Diagnostic des services Dispy ==="

# Vérifier les services Dispy
echo "Vérification des services Dispy..."
systemctl status dispyscheduler 2>/dev/null || echo "Service dispyscheduler non trouvé"
systemctl status dispynode 2>/dev/null || echo "Service dispynode non trouvé"

# Vérifier les ports Dispy
echo ""
echo "Vérification des ports Dispy..."
netstat -tlnp 2>/dev/null | grep -E "(51347|51348)" || echo "Aucun port Dispy ouvert"

echo ""
echo "=== Solutions pour 'Bad source address' ==="

# Solution 1: Configuration réseau
echo "1. Vérification de la configuration réseau..."
if [ -n "$LOCAL_IP" ]; then
    echo "IP locale: $LOCAL_IP"
    
    # Vérifier si l'IP est dans une plage privée
    if echo "$LOCAL_IP" | grep -E "^192\.168\.|^10\.|^172\.(1[6-9]|2[0-9]|3[0-1])\." >/dev/null; then
        echo "✓ IP dans une plage privée (OK)"
    else
        echo "⚠ IP publique détectée, vérifiez la configuration"
    fi
else
    echo "✗ Impossible de détecter l'IP locale"
fi

# Solution 2: Configuration Dispy
echo ""
echo "2. Configuration Dispy..."

# Créer un fichier de configuration Dispy
cat > /tmp/dispy_config.py << EOF
# Configuration Dispy pour Raspberry Pi
import dispy

# Configuration réseau
dispy.config.NodeAvailMem = 100  # MB
dispy.config.NodeAvailCores = 1
dispy.config.NodeTimeout = 30
dispy.config.ClientTimeout = 60

# Configuration des ports
dispy.config.SchedulerPort = 51347
dispy.config.NodePort = 51348

# Configuration réseau
dispy.config.NodeIPAddr = '$LOCAL_IP'
dispy.config.SchedulerIPAddr = '$LOCAL_IP'

print("Configuration Dispy:")
print(f"  Scheduler IP: {dispy.config.SchedulerIPAddr}")
print(f"  Node IP: {dispy.config.NodeIPAddr}")
print(f"  Scheduler Port: {dispy.config.SchedulerPort}")
print(f"  Node Port: {dispy.config.NodePort}")
EOF

echo "Configuration Dispy créée dans /tmp/dispy_config.py"
python3 /tmp/dispy_config.py

# Solution 3: Test de communication
echo ""
echo "3. Test de communication Dispy..."

# Créer un test simple
cat > /tmp/dispy_test.py << EOF
import dispy
import socket

def test_network():
    try:
        # Test de création d'un scheduler
        scheduler = dispy.JobScheduler()
        print("✓ Scheduler créé avec succès")
        
        # Test de création d'un nœud
        node = dispy.DispyNode()
        print("✓ Nœud créé avec succès")
        
        return True
    except Exception as e:
        print(f"✗ Erreur Dispy: {e}")
        return False

if __name__ == "__main__":
    test_network()
EOF

echo "Test de communication Dispy..."
python3 /tmp/dispy_test.py

echo ""
echo "=== Recommandations ==="
echo ""
echo "Si l'erreur 'Bad source address' persiste:"
echo ""
echo "1. Vérifiez la configuration réseau:"
echo "   - Assurez-vous que tous les nœuds sont sur le même réseau"
echo "   - Vérifiez que les nœuds peuvent se ping mutuellement"
echo "   - Vérifiez que les ports 51347 et 51348 sont ouverts"
echo ""
echo "2. Configuration des nœuds:"
echo "   - Sur chaque nœud: sudo systemctl restart dispynode"
echo "   - Sur le maître: sudo systemctl restart dispyscheduler"
echo ""
echo "3. Configuration manuelle:"
echo "   - Éditez /etc/dispy/dispy.conf sur chaque nœud"
echo "   - Spécifiez l'IP locale explicitement"
echo ""
echo "4. Test de connectivité:"
echo "   - Depuis le maître: telnet node6.lan 51348"
echo "   - Depuis un nœud: telnet master.lan 51347"
echo ""
echo "5. Logs de diagnostic:"
echo "   - journalctl -u dispyscheduler -f"
echo "   - journalctl -u dispynode -f"