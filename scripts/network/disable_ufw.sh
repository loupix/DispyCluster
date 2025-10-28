#!/bin/bash
set -e

# Script pour désactiver UFW sur DispyCluster
# Utile pour le développement ou si vous préférez un autre pare-feu

if [ "${EUID}" -ne 0 ]; then
  echo "Ce script doit être exécuté en root"
  exit 1
fi

echo "Désactivation d'UFW pour DispyCluster..."

# Vérifier le statut actuel
echo "Statut UFW actuel :"
ufw status

echo ""
read -p "Êtes-vous sûr de vouloir désactiver UFW ? (y/N) " -n 1 -r
echo
if [[ ! $REPLY =~ ^[Yy]$ ]]; then
  echo "Annulé."
  exit 0
fi

# Désactiver UFW
echo "Désactivation d'UFW..."
ufw --force disable

echo ""
echo "UFW désactivé."
echo ""
echo "ATTENTION : Votre système n'a plus de pare-feu actif !"
echo "Assurez-vous d'avoir un autre système de protection ou de réactiver UFW :"
echo "  sudo ufw enable"
echo ""
echo "Pour réactiver avec la configuration DispyCluster :"
echo "  sudo bash scripts/configure_ufw.sh"