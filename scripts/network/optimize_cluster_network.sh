#!/bin/bash

# Optimisation réseau pour le cluster DispyCluster
# Optimise les paramètres réseau pour de meilleures performances

set -e

echo "=== Optimisation réseau du cluster DispyCluster ==="
echo "Optimisation des paramètres pour de meilleures performances"
echo ""

# Fonction pour vérifier si on est root
check_root() {
    if [ "$EUID" -ne 0 ]; then
        echo "Ce script doit être exécuté en tant que root"
        echo "Utilisez: sudo $0"
        exit 1
    fi
}

# Fonction pour sauvegarder la configuration actuelle
backup_config() {
    echo "Sauvegarde de la configuration actuelle..."
    
    # Sauvegarder sysctl.conf
    if [ -f /etc/sysctl.conf ]; then
        cp /etc/sysctl.conf /etc/sysctl.conf.backup.$(date +%Y%m%d_%H%M%S)
        echo "✓ Configuration sysctl sauvegardée"
    fi
    
    # Sauvegarder les limites système
    if [ -f /etc/security/limits.conf ]; then
        cp /etc/security/limits.conf /etc/security/limits.conf.backup.$(date +%Y%m%d_%H%M%S)
        echo "✓ Configuration des limites sauvegardée"
    fi
}

# Fonction pour optimiser les paramètres TCP
optimize_tcp() {
    echo "Optimisation des paramètres TCP..."
    
    # Supprimer les anciennes configurations dispy si elles existent
    sed -i '/# DispyCluster optimization/,/# End DispyCluster optimization/d' /etc/sysctl.conf
    
    # Ajouter les optimisations TCP
    cat >> /etc/sysctl.conf << EOF

# DispyCluster optimization
# Optimisations TCP pour le cluster
net.core.rmem_max = 134217728
net.core.wmem_max = 134217728
net.core.rmem_default = 262144
net.core.wmem_default = 262144
net.ipv4.tcp_rmem = 4096 65536 134217728
net.ipv4.tcp_wmem = 4096 65536 134217728
net.ipv4.tcp_congestion_control = bbr
net.ipv4.tcp_slow_start_after_idle = 0
net.ipv4.tcp_tw_reuse = 1
net.ipv4.tcp_fin_timeout = 15
net.ipv4.tcp_keepalive_time = 600
net.ipv4.tcp_keepalive_intvl = 60
net.ipv4.tcp_keepalive_probes = 3
net.ipv4.tcp_max_syn_backlog = 65535
net.core.somaxconn = 65535
net.core.netdev_max_backlog = 5000
net.ipv4.tcp_window_scaling = 1
net.ipv4.tcp_timestamps = 1
net.ipv4.tcp_sack = 1
net.ipv4.tcp_fack = 1
net.ipv4.tcp_low_latency = 1
net.ipv4.tcp_no_delay_ack = 1
net.ipv4.tcp_mtu_probing = 1
# End DispyCluster optimization
EOF
    
    echo "✓ Paramètres TCP optimisés"
}

# Fonction pour optimiser les limites système
optimize_limits() {
    echo "Optimisation des limites système..."
    
    # Supprimer les anciennes limites dispy si elles existent
    sed -i '/# DispyCluster limits/,/# End DispyCluster limits/d' /etc/security/limits.conf
    
    # Ajouter les limites optimisées
    cat >> /etc/security/limits.conf << EOF

# DispyCluster limits
# Limites optimisées pour le cluster
* soft nofile 65535
* hard nofile 65535
* soft nproc 65535
* hard nproc 65535
* soft memlock unlimited
* hard memlock unlimited
* soft stack 8192
* hard stack 8192
# End DispyCluster limits
EOF
    
    echo "✓ Limites système optimisées"
}

# Fonction pour optimiser les paramètres réseau
optimize_network() {
    echo "Optimisation des paramètres réseau..."
    
    # Optimiser les buffers réseau
    echo "net.core.netdev_budget = 600" >> /etc/sysctl.conf
    echo "net.core.netdev_max_backlog = 5000" >> /etc/sysctl.conf
    
    # Optimiser les paramètres IP
    echo "net.ipv4.ip_forward = 0" >> /etc/sysctl.conf
    echo "net.ipv4.conf.all.accept_redirects = 0" >> /etc/sysctl.conf
    echo "net.ipv4.conf.all.send_redirects = 0" >> /etc/sysctl.conf
    echo "net.ipv4.conf.all.accept_source_route = 0" >> /etc/sysctl.conf
    echo "net.ipv4.conf.all.log_martians = 1" >> /etc/sysctl.conf
    
    echo "✓ Paramètres réseau optimisés"
}

# Fonction pour optimiser les paramètres de mémoire
optimize_memory() {
    echo "Optimisation des paramètres de mémoire..."
    
    # Optimiser la gestion de la mémoire
    echo "vm.swappiness = 10" >> /etc/sysctl.conf
    echo "vm.dirty_ratio = 15" >> /etc/sysctl.conf
    echo "vm.dirty_background_ratio = 5" >> /etc/sysctl.conf
    echo "vm.dirty_expire_centisecs = 3000" >> /etc/sysctl.conf
    echo "vm.dirty_writeback_centisecs = 500" >> /etc/sysctl.conf
    
    echo "✓ Paramètres de mémoire optimisés"
}

# Fonction pour optimiser les paramètres de CPU
optimize_cpu() {
    echo "Optimisation des paramètres de CPU..."
    
    # Optimiser la planification des tâches
    echo "kernel.sched_rt_runtime_us = -1" >> /etc/sysctl.conf
    echo "kernel.sched_rt_period_us = 1000000" >> /etc/sysctl.conf
    
    echo "✓ Paramètres de CPU optimisés"
}

# Fonction pour appliquer les changements
apply_changes() {
    echo "Application des changements..."
    
    # Appliquer les changements sysctl
    sysctl -p
    
    # Redémarrer les services réseau si nécessaire
    if systemctl is-active --quiet networking; then
        systemctl restart networking
        echo "✓ Service networking redémarré"
    fi
    
    echo "✓ Changements appliqués"
}

# Fonction pour vérifier les optimisations
verify_optimizations() {
    echo "Vérification des optimisations..."
    
    echo ""
    echo "Paramètres TCP optimisés:"
    sysctl net.core.rmem_max net.core.wmem_max net.ipv4.tcp_rmem net.ipv4.tcp_wmem 2>/dev/null || echo "Paramètres non configurés"
    
    echo ""
    echo "Paramètres de mémoire:"
    sysctl vm.swappiness vm.dirty_ratio vm.dirty_background_ratio 2>/dev/null || echo "Paramètres non configurés"
    
    echo ""
    echo "Limites système:"
    ulimit -n
    ulimit -u
    
    echo ""
    echo "Statut des services réseau:"
    systemctl is-active networking || echo "Service networking non actif"
}

# Fonction pour afficher les recommandations
show_recommendations() {
    echo ""
    echo "=== Recommandations ==="
    echo ""
    echo "1. Redémarrez le système pour appliquer tous les changements:"
    echo "   sudo reboot"
    echo ""
    echo "2. Vérifiez que les optimisations sont actives après le redémarrage:"
    echo "   sysctl -a | grep -E '(rmem|wmem|tcp_)'"
    echo ""
    echo "3. Testez les performances du cluster:"
    echo "   python3 scripts/network/test_cluster_network.py"
    echo ""
    echo "4. Surveillez les performances:"
    echo "   python3 scripts/monitoring/monitor_cluster_realtime.py"
    echo ""
    echo "5. Si vous rencontrez des problèmes, restaurez la configuration:"
    echo "   sudo cp /etc/sysctl.conf.backup.* /etc/sysctl.conf"
    echo "   sudo sysctl -p"
}

# Fonction principale
main() {
    echo "Début de l'optimisation réseau du cluster..."
    echo ""
    
    # Vérifier les privilèges
    check_root
    
    # Sauvegarder la configuration
    backup_config
    echo ""
    
    # Optimiser les paramètres
    optimize_tcp
    optimize_limits
    optimize_network
    optimize_memory
    optimize_cpu
    echo ""
    
    # Appliquer les changements
    apply_changes
    echo ""
    
    # Vérifier les optimisations
    verify_optimizations
    echo ""
    
    # Afficher les recommandations
    show_recommendations
    
    echo ""
    echo "=== Optimisation terminée ==="
    echo "Redémarrage recommandé pour appliquer tous les changements"
}

# Exécution du script
main "$@"