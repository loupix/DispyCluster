#!/bin/bash
# Installation avec venv uniquement (alternative à conda)
# Fonctionne mieux sur Raspberry Pi avec Python ancien

set -e

echo "=== Installation avec venv (recommandé pour Raspberry Pi) ==="

GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

# Vérifier Python 3
if ! command -v python3 &> /dev/null; then
    echo "Erreur: python3 n'est pas installé"
    exit 1
fi

# Créer l'environnement virtuel
echo "Création de l'environnement virtuel..."
python3 -m venv venv

# Activer l'environnement
source venv/bin/activate

# Mettre à jour pip
echo "Mise à jour de pip..."
pip install --upgrade pip setuptools wheel

# Installer les dépendances avec des versions compatibles RPi
echo "Installation des dépendances..."

# Versions compatibles avec Raspberry Pi (ARM)
pip install \
    fastapi==0.100.1 \
    uvicorn==0.23.2 \
    jinja2==3.1.2 \
    python-multipart==0.0.6 \
    httpx==0.24.1 \
    pydantic==1.10.12 \
    python-jose[cryptography]==3.3.0 \
    passlib[bcrypt]==1.7.4 \
    celery==5.3.4 \
    redis==5.0.1 \
    PyYAML==6.0.1 \
    dispy==4.15.0

echo -e "${GREEN}=== Installation terminée ===${NC}"
echo ""
echo "Pour activer l'environnement:"
echo "  source venv/bin/activate"



