#!/bin/bash

# Script pour gérer les fichiers de cache dispy
# Déplace les fichiers _dispy_* vers le dossier temp/

echo "=== Gestion des fichiers de cache dispy ==="

# Créer le dossier temp s'il n'existe pas
mkdir -p temp

# Compter les fichiers _dispy_* existants
DISPY_FILES=$(ls _dispy_* 2>/dev/null | wc -l)

if [ "$DISPY_FILES" -eq 0 ]; then
    echo "Aucun fichier de cache dispy trouvé"
    exit 0
fi

echo "Fichiers de cache dispy trouvés: $DISPY_FILES"

# Déplacer tous les fichiers _dispy_* vers temp/
echo "Déplacement des fichiers vers temp/..."
mv _dispy_* temp/ 2>/dev/null

# Vérifier le résultat
MOVED_FILES=$(ls temp/_dispy_* 2>/dev/null | wc -l)
echo "Fichiers déplacés: $MOVED_FILES"

# Afficher la liste des fichiers déplacés
echo "Fichiers dans temp/:"
ls -la temp/_dispy_* 2>/dev/null || echo "Aucun fichier dans temp/"

echo "=== Gestion terminée ==="