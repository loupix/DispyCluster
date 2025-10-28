#!/bin/bash

# Script pour nettoyer les fichiers de cache dispy
# Supprime les anciens fichiers de cache et nettoie le dossier temp/

echo "=== Nettoyage des fichiers de cache dispy ==="

# Créer le dossier temp s'il n'existe pas
mkdir -p temp

# Compter les fichiers _dispy_* dans temp/
CACHE_FILES=$(ls temp/_dispy_* 2>/dev/null | wc -l)

if [ "$CACHE_FILES" -eq 0 ]; then
    echo "Aucun fichier de cache à nettoyer"
    exit 0
fi

echo "Fichiers de cache à nettoyer: $CACHE_FILES"

# Afficher les fichiers avant suppression
echo "Fichiers qui seront supprimés:"
ls -la temp/_dispy_* 2>/dev/null

# Demander confirmation
read -p "Voulez-vous supprimer ces fichiers de cache ? (y/N): " -n 1 -r
echo
if [[ $REPLY =~ ^[Yy]$ ]]; then
    # Supprimer les fichiers de cache
    rm -f temp/_dispy_*
    echo "Fichiers de cache supprimés"
    
    # Vérifier le résultat
    REMAINING_FILES=$(ls temp/_dispy_* 2>/dev/null | wc -l)
    echo "Fichiers restants: $REMAINING_FILES"
else
    echo "Nettoyage annulé"
fi

echo "=== Nettoyage terminé ==="