#!/bin/bash

# Script de réparation des packages Raspberry Pi
# Corrige les problèmes courants de dpkg et apt

set -e

echo "=== Réparation des packages Raspberry Pi ==="
echo ""

# Vérifier les privilèges
if [ "${EUID}" -ne 0 ]; then
    echo "Ce script doit être exécuté en root"
    exit 1
fi

# Fonction de réparation complète
repair_package_system() {
    echo "Début de la réparation du système de packages..."
    
    # 1. Arrêter les processus apt qui pourraient bloquer
    echo "Arrêt des processus apt..."
    pkill -f apt || true
    pkill -f dpkg || true
    sleep 2
    
    # 2. Supprimer les locks
    echo "Suppression des locks..."
    rm -f /var/lib/dpkg/lock*
    rm -f /var/cache/apt/archives/lock
    rm -f /var/lib/apt/lists/lock
    
    # 3. Corriger les packages cassés
    echo "Correction des packages cassés..."
    dpkg --configure -a || true
    
    # 4. Nettoyer le cache
    echo "Nettoyage du cache..."
    apt-get clean
    apt-get autoclean
    
    # 5. Réparer les dépendances
    echo "Réparation des dépendances..."
    apt-get -f install -y || true
    
    # 6. Corriger spécifiquement raspberrypi-bootloader
    echo "Correction du package raspberrypi-bootloader..."
    if dpkg -l | grep -q "raspberrypi-bootloader"; then
        apt-get --fix-missing install raspberrypi-bootloader -y || true
    fi
    
    # 7. Nettoyer les listes corrompues
    echo "Nettoyage des listes de packages..."
    rm -rf /var/lib/apt/lists/*
    
    # 8. Recréer les listes
    echo "Recréation des listes de packages..."
    apt-get update
    
    # 9. Réparer à nouveau
    echo "Réparation finale..."
    apt-get -f install -y || true
    
    echo "✓ Réparation terminée"
}

# Fonction de test
test_package_system() {
    echo "Test du système de packages..."
    
    if apt-get update >/dev/null 2>&1; then
        echo "✓ apt-get update fonctionne"
    else
        echo "✗ apt-get update échoue"
        return 1
    fi
    
    if dpkg --configure -a >/dev/null 2>&1; then
        echo "✓ dpkg --configure fonctionne"
    else
        echo "✗ dpkg --configure échoue"
        return 1
    fi
    
    echo "✓ Système de packages fonctionnel"
    return 0
}

# Menu principal
case "${1:-repair}" in
    repair)
        repair_package_system
        echo ""
        echo "Test du système après réparation..."
        if test_package_system; then
            echo ""
            echo "✓ Système de packages réparé avec succès !"
            echo "Tu peux maintenant relancer l'installation :"
            echo "  sudo scripts/dispycluster.sh install-worker"
        else
            echo ""
            echo "✗ Problème persistant, redémarre le Raspberry Pi et relance ce script"
        fi
        ;;
    test)
        if test_package_system; then
            echo "✓ Système de packages OK"
            exit 0
        else
            echo "✗ Système de packages défaillant"
            exit 1
        fi
        ;;
    clean)
        echo "Nettoyage complet du système de packages..."
        apt-get clean
        apt-get autoclean
        apt-get autoremove -y
        rm -rf /var/lib/apt/lists/*
        apt-get update
        echo "✓ Nettoyage terminé"
        ;;
    *)
        echo "Usage: $0 [repair|test|clean]"
        echo ""
        echo "  repair - Réparer le système de packages (défaut)"
        echo "  test   - Tester le système de packages"
        echo "  clean  - Nettoyer le cache des packages"
        exit 1
        ;;
esac