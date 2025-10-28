#!/bin/bash
# Installation de l'environnement pour Raspberry Pi
# Gère les problèmes de SSL avec les anciennes versions de conda

set -e

echo "=== Installation environnement DispyCluster pour Raspberry Pi ==="

# Couleurs
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m'

# Détecter la version de Python
PYTHON_VERSION=$(python3 --version 2>&1 | awk '{print $2}')
echo "Version Python détectée: $PYTHON_VERSION"

# Vérifier si conda est disponible
if command -v conda &> /dev/null; then
    CONDA_VERSION=$(conda --version)
    echo "Conda détecté: $CONDA_VERSION"
    
    # Option 1: Mettre à jour conda d'abord
    echo -e "${YELLOW}Tentative de mise à jour de conda...${NC}"
    conda update -y conda 2>/dev/null || echo "Mise à jour de conda échouée"
    
    # Option 2: Créer l'environnement avec SSL désactivé temporairement
    echo -e "${YELLOW}Création de l'environnement conda avec SSL désactivé...${NC}"
    conda config --set ssl_verify false
    
    # Installer les dépendances conda de base
    conda create -n dispycluster python=3.9 -y
    
    # Activer l'environnement
    source "$(conda info --base)/etc/profile.d/conda.sh"
    conda activate dispycluster
    
    # Réactiver SSL après création
    conda config --set ssl_verify true
    
    echo -e "${GREEN}Environnement conda créé${NC}"
else
    echo -e "${YELLOW}Conda non disponible, utilisation de venv${NC}"
    
    # Créer un environnement virtuel avec venv
    python3 -m venv venv
    
    # Activer l'environnement
    source venv/bin/activate
    
    echo -e "${GREEN}Environnement venv créé${NC}"
fi

# Mettre à jour pip
echo "Mise à jour de pip..."
pip install --upgrade pip setuptools wheel

# Installer les dépendances principales
echo "Installation des dépendances web..."
pip install -r web/requirements.txt

# Installer les dépendances supplémentaires si disponibles
if [ -f requirements.txt ]; then
    echo "Installation des dépendances additionnelles..."
    pip install -r requirements.txt
fi

echo -e "${GREEN}=== Installation terminée ===${NC}"
echo ""
echo "Pour activer l'environnement:"
echo "  - Avec conda: conda activate dispycluster"
echo "  - Avec venv: source venv/bin/activate"



