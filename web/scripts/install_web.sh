#!/bin/bash
# Script d'installation pour l'interface web DispyCluster

echo "🚀 Installation de DispyCluster Web Interface"

# Vérifier Python
if ! command -v python3 &> /dev/null; then
    echo "❌ Python 3 n'est pas installé"
    exit 1
fi

# Vérifier conda
if ! command -v conda &> /dev/null; then
    echo "❌ Conda n'est pas installé"
    exit 1
fi

# Activer l'environnement conda
echo "🔧 Activation de l'environnement conda 'dispycluster'"
source $(conda info --base)/etc/profile.d/conda.sh
conda activate dispycluster

if [ "$CONDA_DEFAULT_ENV" != "dispycluster" ]; then
    echo "❌ Environnement 'dispycluster' non trouvé"
    echo "💡 Créez l'environnement avec: conda env create -f ../environment.yml"
    exit 1
fi

echo "✅ Environnement activé: $CONDA_DEFAULT_ENV"

# Installer les dépendances Python
echo "📦 Installation des dépendances Python..."
pip install -r requirements.txt

# Créer les dossiers nécessaires
echo "📁 Création des dossiers..."
mkdir -p data
mkdir -p logs
mkdir -p static/css
mkdir -p static/js

# Vérifier l'installation
echo "🔍 Vérification de l'installation..."
python -c "
import fastapi, uvicorn, jinja2, httpx, sqlite3
print('✅ Toutes les dépendances sont installées')
"

if [ $? -eq 0 ]; then
    echo "✅ Installation réussie !"
    echo ""
    echo "🚀 Pour démarrer l'interface web :"
    echo "   ./scripts/start_web.sh"
    echo ""
    echo "🌐 L'interface sera accessible sur :"
    echo "   http://localhost:8085"
    echo ""
    echo "📚 Documentation :"
    echo "   Voir README.md pour plus d'informations"
else
    echo "❌ Erreur lors de l'installation"
    exit 1
fi