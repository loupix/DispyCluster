#!/bin/bash

# Script principal DispyCluster - Point d'entrée unifié
# Regroupe toutes les fonctionnalités principales

set -e

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"

# Couleurs pour l'affichage
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Fonction d'affichage
print_header() {
    echo -e "${BLUE}=== $1 ===${NC}"
}

print_success() {
    echo -e "${GREEN}✓ $1${NC}"
}

print_warning() {
    echo -e "${YELLOW}⚠ $1${NC}"
}

print_error() {
    echo -e "${RED}✗ $1${NC}"
}

# Fonction d'aide
show_help() {
    echo "DispyCluster - Script principal"
    echo ""
    echo "Usage: $0 [COMMAND]"
    echo ""
    echo "Commandes disponibles:"
    echo ""
echo "  install     - Installation complète du cluster"
echo "  install-jobcluster - Installation JobCluster (API 4.15.2+)"
echo "  install-master - Installation du nœud maître"
echo "  install-node   - Installation d'un nœud worker"
echo "  install-worker - Installation worker JobCluster (recommandé)"
echo "  install-services - Installation des services avancés"
    echo ""
echo "  fix         - Correction des problèmes"
echo "  fix-dispy   - Correction du service Dispy"
echo "  fix-deps    - Correction des dépendances"
echo "  fix-packages - Correction du système de packages"
echo "  fix-raspberry - Correction spécifique Raspberry Pi"
    echo ""
    echo "  test        - Tests du système"
    echo "  test-api    - Test de l'API Dispy"
    echo "  test-services - Test des services"
    echo ""
    echo "  network     - Configuration réseau"
    echo "  configure-network - Configuration réseau complète"
    echo "  configure-ufw - Configuration du firewall"
    echo ""
    echo "  diagnostic  - Diagnostic du système"
    echo "  healthcheck - Vérification de santé"
    echo ""
    echo "  monitoring  - Installation du monitoring"
    echo "  node-exporter - Installation node_exporter"
    echo ""
    echo "  help        - Afficher cette aide"
    echo ""
    echo "Exemples:"
    echo "  $0 install          # Installation complète"
echo "  $0 install-jobcluster # Installation JobCluster (recommandé)"
echo "  $0 install-worker     # Installation worker JobCluster"
    echo "  $0 fix-dispy        # Correction du service Dispy"
echo "  $0 fix-packages     # Correction du système de packages"
    echo "  $0 test-services    # Test des services"
    echo "  $0 diagnostic       # Diagnostic du système"
}

# Fonction d'installation complète
install_complete() {
    print_header "Installation complète DispyCluster"
    
    echo "Cette commande va installer:"
    echo "- Le nœud maître avec Dispy"
    echo "- Les services avancés"
    echo "- Le monitoring"
    echo "- La configuration réseau"
    echo ""
    
    read -p "Continuer? (y/N): " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        echo "Installation annulée"
        exit 0
    fi
    
    # Installation du maître
    if [ -f "$SCRIPT_DIR/install/install_master.sh" ]; then
        print_header "Installation du nœud maître"
        bash "$SCRIPT_DIR/install/install_master.sh"
        print_success "Nœud maître installé"
    else
        print_error "Script d'installation du maître non trouvé"
    fi
    
    # Installation des services
    if [ -f "$SCRIPT_DIR/install/install_services.sh" ]; then
        print_header "Installation des services avancés"
        bash "$SCRIPT_DIR/install/install_services.sh"
        print_success "Services avancés installés"
    else
        print_error "Script d'installation des services non trouvé"
    fi
    
    # Configuration réseau
    if [ -f "$SCRIPT_DIR/network/configure_network.sh" ]; then
        print_header "Configuration réseau"
        bash "$SCRIPT_DIR/network/configure_network.sh"
        print_success "Réseau configuré"
    else
        print_error "Script de configuration réseau non trouvé"
    fi
    
    # Installation du monitoring
    if [ -f "$SCRIPT_DIR/monitoring/node_exporter_install.sh" ]; then
        print_header "Installation du monitoring"
        bash "$SCRIPT_DIR/monitoring/node_exporter_install.sh"
        print_success "Monitoring installé"
    else
        print_error "Script d'installation du monitoring non trouvé"
    fi
    
    print_success "Installation complète terminée!"
    echo ""
    echo "Prochaines étapes:"
    echo "1. Installer les nœuds workers: $0 install-node"
    echo "2. Tester le système: $0 test-services"
    echo "3. Vérifier la santé: $0 healthcheck"
}

# Fonction de correction
fix_problems() {
    print_header "Correction des problèmes"
    
    echo "Problèmes courants et solutions:"
    echo ""
    echo "1. Service Dispy 'Bad source address'"
    echo "2. Dépendances Python manquantes"
    echo "3. Problèmes de réseau"
    echo "4. Services non accessibles"
    echo ""
    
    read -p "Quel problème voulez-vous corriger? (1-4): " choice
    
    case $choice in
        1)
            if [ -f "$SCRIPT_DIR/fix/fix_dispy_master_v2.sh" ]; then
                bash "$SCRIPT_DIR/fix/fix_dispy_master_v2.sh"
            else
                print_error "Script de correction Dispy non trouvé"
            fi
            ;;
        2)
            if [ -f "$SCRIPT_DIR/fix/fix_dependencies.sh" ]; then
                bash "$SCRIPT_DIR/fix/fix_dependencies.sh"
            else
                print_error "Script de correction des dépendances non trouvé"
            fi
            ;;
        3)
            if [ -f "$SCRIPT_DIR/network/configure_network.sh" ]; then
                bash "$SCRIPT_DIR/network/configure_network.sh"
            else
                print_error "Script de configuration réseau non trouvé"
            fi
            ;;
        4)
            if [ -f "$SCRIPT_DIR/diagnostic/healthcheck.sh" ]; then
                bash "$SCRIPT_DIR/diagnostic/healthcheck.sh"
            else
                print_error "Script de diagnostic non trouvé"
            fi
            ;;
        *)
            print_error "Choix invalide"
            ;;
    esac
}

# Fonction de test
test_system() {
    print_header "Tests du système"
    
    echo "Tests disponibles:"
    echo ""
    echo "1. Test de l'API Dispy"
    echo "2. Test des services"
    echo "3. Test de connectivité réseau"
    echo "4. Test complet"
    echo ""
    
    read -p "Quel test voulez-vous exécuter? (1-4): " choice
    
    case $choice in
        1)
            if [ -f "$SCRIPT_DIR/test/test_dispy_api.sh" ]; then
                bash "$SCRIPT_DIR/test/test_dispy_api.sh"
            else
                print_error "Script de test API non trouvé"
            fi
            ;;
        2)
            if [ -f "$SCRIPT_DIR/test/test_services.sh" ]; then
                bash "$SCRIPT_DIR/test/test_services.sh"
            else
                print_error "Script de test des services non trouvé"
            fi
            ;;
        3)
            if [ -f "$SCRIPT_DIR/diagnostic/diagnose_network.sh" ]; then
                bash "$SCRIPT_DIR/diagnostic/diagnose_network.sh"
            else
                print_error "Script de diagnostic réseau non trouvé"
            fi
            ;;
        4)
            print_header "Test complet"
            if [ -f "$SCRIPT_DIR/test/test_dispy_api.sh" ]; then
                bash "$SCRIPT_DIR/test/test_dispy_api.sh"
            fi
            if [ -f "$SCRIPT_DIR/test/test_services.sh" ]; then
                bash "$SCRIPT_DIR/test/test_services.sh"
            fi
            ;;
        *)
            print_error "Choix invalide"
            ;;
    esac
}

# Fonction de diagnostic
diagnostic_system() {
    print_header "Diagnostic du système"
    
    echo "Diagnostics disponibles:"
    echo ""
    echo "1. Diagnostic réseau"
    echo "2. Vérification de santé"
    echo "3. Diagnostic complet"
    echo ""
    
    read -p "Quel diagnostic voulez-vous exécuter? (1-3): " choice
    
    case $choice in
        1)
            if [ -f "$SCRIPT_DIR/diagnostic/diagnose_network.sh" ]; then
                bash "$SCRIPT_DIR/diagnostic/diagnose_network.sh"
            else
                print_error "Script de diagnostic réseau non trouvé"
            fi
            ;;
        2)
            if [ -f "$SCRIPT_DIR/diagnostic/healthcheck.sh" ]; then
                bash "$SCRIPT_DIR/diagnostic/healthcheck.sh"
            else
                print_error "Script de vérification de santé non trouvé"
            fi
            ;;
        3)
            print_header "Diagnostic complet"
            if [ -f "$SCRIPT_DIR/diagnostic/healthcheck.sh" ]; then
                bash "$SCRIPT_DIR/diagnostic/healthcheck.sh"
            fi
            if [ -f "$SCRIPT_DIR/diagnostic/diagnose_network.sh" ]; then
                bash "$SCRIPT_DIR/diagnostic/diagnose_network.sh"
            fi
            ;;
        *)
            print_error "Choix invalide"
            ;;
    esac
}

# Fonction principale
main() {
    case "${1:-help}" in
        install)
            install_complete
            ;;
        install-jobcluster)
            if [ -f "$SCRIPT_DIR/install/install_jobcluster.sh" ]; then
                bash "$SCRIPT_DIR/install/install_jobcluster.sh"
            else
                print_error "Script d'installation JobCluster non trouvé"
            fi
            ;;
        install-master)
            if [ -f "$SCRIPT_DIR/install/install_master.sh" ]; then
                bash "$SCRIPT_DIR/install/install_master.sh"
            else
                print_error "Script d'installation du maître non trouvé"
            fi
            ;;
        install-node)
            if [ -f "$SCRIPT_DIR/install/install_node.sh" ]; then
                bash "$SCRIPT_DIR/install/install_node.sh"
            else
                print_error "Script d'installation du nœud non trouvé"
            fi
            ;;
        install-worker)
            if [ -f "$SCRIPT_DIR/install/install_worker_jobcluster.sh" ]; then
                bash "$SCRIPT_DIR/install/install_worker_jobcluster.sh"
            else
                print_error "Script d'installation worker JobCluster non trouvé"
            fi
            ;;
        install-services)
            if [ -f "$SCRIPT_DIR/install/install_services.sh" ]; then
                bash "$SCRIPT_DIR/install/install_services.sh"
            else
                print_error "Script d'installation des services non trouvé"
            fi
            ;;
        fix)
            fix_problems
            ;;
        fix-dispy)
            if [ -f "$SCRIPT_DIR/fix/fix_dispy_master_final.sh" ]; then
                bash "$SCRIPT_DIR/fix/fix_dispy_master_final.sh"
            else
                print_error "Script de correction Dispy non trouvé"
            fi
            ;;
        fix-deps)
            if [ -f "$SCRIPT_DIR/fix/fix_dependencies.sh" ]; then
                bash "$SCRIPT_DIR/fix/fix_dependencies.sh"
            else
                print_error "Script de correction des dépendances non trouvé"
            fi
            ;;
        fix-packages)
            if [ -f "$SCRIPT_DIR/fix/fix_package_system.sh" ]; then
                bash "$SCRIPT_DIR/fix/fix_package_system.sh"
            else
                print_error "Script de correction du système de packages non trouvé"
            fi
            ;;
        fix-raspberry)
            if [ -f "$SCRIPT_DIR/fix/fix_raspberry_pi_packages.sh" ]; then
                bash "$SCRIPT_DIR/fix/fix_raspberry_pi_packages.sh"
            else
                print_error "Script de correction Raspberry Pi non trouvé"
            fi
            ;;
        test)
            test_system
            ;;
        test-api)
            if [ -f "$SCRIPT_DIR/test/test_dispy_api.sh" ]; then
                bash "$SCRIPT_DIR/test/test_dispy_api.sh"
            else
                print_error "Script de test API non trouvé"
            fi
            ;;
        test-services)
            if [ -f "$SCRIPT_DIR/test/test_services.sh" ]; then
                bash "$SCRIPT_DIR/test/test_services.sh"
            else
                print_error "Script de test des services non trouvé"
            fi
            ;;
        network)
            if [ -f "$SCRIPT_DIR/network/configure_network.sh" ]; then
                bash "$SCRIPT_DIR/network/configure_network.sh"
            else
                print_error "Script de configuration réseau non trouvé"
            fi
            ;;
        configure-network)
            if [ -f "$SCRIPT_DIR/network/configure_network.sh" ]; then
                bash "$SCRIPT_DIR/network/configure_network.sh"
            else
                print_error "Script de configuration réseau non trouvé"
            fi
            ;;
        configure-ufw)
            if [ -f "$SCRIPT_DIR/network/configure_ufw.sh" ]; then
                bash "$SCRIPT_DIR/network/configure_ufw.sh"
            else
                print_error "Script de configuration UFW non trouvé"
            fi
            ;;
        diagnostic)
            diagnostic_system
            ;;
        healthcheck)
            if [ -f "$SCRIPT_DIR/diagnostic/healthcheck.sh" ]; then
                bash "$SCRIPT_DIR/diagnostic/healthcheck.sh"
            else
                print_error "Script de vérification de santé non trouvé"
            fi
            ;;
        monitoring)
            if [ -f "$SCRIPT_DIR/monitoring/node_exporter_install.sh" ]; then
                bash "$SCRIPT_DIR/monitoring/node_exporter_install.sh"
            else
                print_error "Script d'installation du monitoring non trouvé"
            fi
            ;;
        node-exporter)
            if [ -f "$SCRIPT_DIR/monitoring/node_exporter_install.sh" ]; then
                bash "$SCRIPT_DIR/monitoring/node_exporter_install.sh"
            else
                print_error "Script d'installation node_exporter non trouvé"
            fi
            ;;
        help|--help|-h)
            show_help
            ;;
        *)
            print_error "Commande inconnue: $1"
            echo ""
            show_help
            exit 1
            ;;
    esac
}

# Exécuter la fonction principale
main "$@"