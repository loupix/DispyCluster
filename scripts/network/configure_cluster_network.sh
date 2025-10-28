#!/bin/bash

# Configuration réseau pour le cluster DispyCluster
# Configure les paramètres réseau optimaux pour dispy

set -e

echo "=== Configuration réseau du cluster DispyCluster ==="
echo "Optimisation des paramètres réseau pour dispy"
echo ""

# Fonction pour obtenir l'IP locale
get_local_ip() {
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

# Fonction pour vérifier si on est root
check_root() {
    if [ "$EUID" -ne 0 ]; then
        echo "Ce script doit être exécuté en tant que root"
        echo "Utilisez: sudo $0"
        exit 1
    fi
}

# Fonction pour configurer les paramètres réseau
configure_network_params() {
    echo "Configuration des paramètres réseau..."
    
    # Paramètres TCP pour dispy
    echo "Configuration des paramètres TCP..."
    
    # Augmenter les buffers TCP
    echo "net.core.rmem_max = 134217728" >> /etc/sysctl.conf
    echo "net.core.wmem_max = 134217728" >> /etc/sysctl.conf
    echo "net.ipv4.tcp_rmem = 4096 65536 134217728" >> /etc/sysctl.conf
    echo "net.ipv4.tcp_wmem = 4096 65536 134217728" >> /etc/sysctl.conf
    
    # Optimiser les timeouts
    echo "net.ipv4.tcp_keepalive_time = 600" >> /etc/sysctl.conf
    echo "net.ipv4.tcp_keepalive_intvl = 60" >> /etc/sysctl.conf
    echo "net.ipv4.tcp_keepalive_probes = 3" >> /etc/sysctl.conf
    
    # Augmenter les limites de connexions
    echo "net.core.somaxconn = 65535" >> /etc/sysctl.conf
    echo "net.ipv4.tcp_max_syn_backlog = 65535" >> /etc/sysctl.conf
    
    # Appliquer les changements
    sysctl -p
    
    echo "✓ Paramètres réseau configurés"
}

# Fonction pour configurer le firewall
configure_firewall() {
    echo "Configuration du firewall..."
    
    # Vérifier si ufw est installé
    if command -v ufw >/dev/null 2>&1; then
        echo "Configuration d'ufw..."
        
        # Activer ufw
        ufw --force enable
        
        # Autoriser SSH
        ufw allow ssh
        
        # Autoriser les ports dispy
        ufw allow 51347/tcp comment "Dispy Scheduler"
        ufw allow 51348/tcp comment "Dispy Node"
        
        # Autoriser les ports de monitoring
        ufw allow 9090/tcp comment "Prometheus"
        ufw allow 3000/tcp comment "Grafana"
        
        echo "✓ Firewall configuré"
    else
        echo "ufw non installé, configuration manuelle nécessaire"
    fi
}

# Fonction pour configurer les hosts
configure_hosts() {
    echo "Configuration du fichier hosts..."
    
    local_ip=$(get_local_ip)
    
    # Ajouter les entrées pour le cluster
    echo "" >> /etc/hosts
    echo "# DispyCluster configuration" >> /etc/hosts
    echo "$local_ip dispycluster-master" >> /etc/hosts
    
    echo "✓ Fichier hosts configuré"
}

# Fonction pour tester la connectivité
test_connectivity() {
    echo "Test de connectivité..."
    
    # Test des ports locaux
    local_ip=$(get_local_ip)
    
    echo "Test des ports dispy locaux..."
    
    # Test port scheduler
    if nc -z localhost 51347 2>/dev/null; then
        echo "✓ Port 51347 (Scheduler): OK"
    else
        echo "○ Port 51347 (Scheduler): Libre"
    fi
    
    # Test port node
    if nc -z localhost 51348 2>/dev/null; then
        echo "✓ Port 51348 (Node): OK"
    else
        echo "○ Port 51348 (Node): Libre"
    fi
    
    echo "✓ Tests de connectivité terminés"
}

# Fonction pour afficher la configuration
show_config() {
    echo "=== Configuration réseau actuelle ==="
    
    local_ip=$(get_local_ip)
    echo "IP locale: $local_ip"
    
    echo ""
    echo "Paramètres TCP:"
    sysctl net.core.rmem_max net.core.wmem_max net.ipv4.tcp_rmem net.ipv4.tcp_wmem 2>/dev/null || echo "Paramètres non configurés"
    
    echo ""
    echo "Statut du firewall:"
    if command -v ufw >/dev/null 2>&1; then
        ufw status
    else
        echo "ufw non installé"
    fi
    
    echo ""
    echo "Ports en écoute:"
    netstat -tlnp 2>/dev/null | grep -E ':(51347|51348|22|80|443)' || echo "Aucun port pertinent en écoute"
}

# Fonction principale
main() {
    echo "Début de la configuration réseau du cluster..."
    echo ""
    
    # Vérifier les privilèges
    check_root
    
    # Obtenir l'IP locale
    local_ip=$(get_local_ip)
    echo "IP locale détectée: $local_ip"
    
    if [ -z "$local_ip" ]; then
        echo "Erreur: Impossible de détecter l'IP locale"
        exit 1
    fi
    
    echo ""
    
    # Configuration des paramètres réseau
    configure_network_params
    echo ""
    
    # Configuration du firewall
    configure_firewall
    echo ""
    
    # Configuration des hosts
    configure_hosts
    echo ""
    
    # Test de connectivité
    test_connectivity
    echo ""
    
    # Affichage de la configuration
    show_config
    echo ""
    
    echo "=== Configuration terminée ==="
    echo "Redémarrage recommandé pour appliquer tous les changements"
    echo "Utilisez: sudo reboot"
}

# Exécution du script
main "$@"