#!/bin/bash

# Script de réparation du système de packages
# Résout les erreurs dpkg et apt

set -e

echo "=== Réparation du système de packages ==="
echo "Résolution des erreurs dpkg et apt"
echo ""

# Vérifier les privilèges
if [ "${EUID}" -ne 0 ]; then
    echo "Ce script doit être exécuté en root"
    exit 1
fi

echo "1. Arrêt des processus apt en cours..."
# Tuer tous les processus apt en cours
pkill -f apt || true
pkill -f dpkg || true
sleep 2

echo "2. Suppression des verrous apt..."
# Supprimer les verrous apt
rm -f /var/lib/dpkg/lock*
rm -f /var/cache/apt/archives/lock*
rm -f /var/lib/apt/lists/lock*

echo "3. Réparation de la base de données dpkg..."
# Réparer la base de données dpkg
dpkg --configure -a || true

echo "4. Nettoyage des packages cassés..."
# Nettoyage des packages cassés
apt-get clean
apt-get autoclean
apt-get autoremove -y

echo "5. Réparation des packages manquants..."
# Réparer les packages manquants
apt-get install -f -y

echo "6. Mise à jour de la liste des packages..."
# Mettre à jour la liste des packages
apt-get update

echo "7. Réparation spécifique du bootloader..."
# Réparation spécifique du bootloader si nécessaire
if dpkg -l | grep -q "raspberrypi-bootloader"; then
    echo "Réparation du package raspberrypi-bootloader..."
    apt-get install --reinstall raspberrypi-bootloader -y || true
fi

echo "8. Vérification finale..."
# Vérification finale
dpkg --configure -a
apt-get check

echo ""
echo "=== Réparation terminée ==="
echo ""
echo "Le système de packages a été réparé."
echo "Tu peux maintenant relancer l'installation :"
echo "  sudo scripts/dispycluster.sh install-worker"