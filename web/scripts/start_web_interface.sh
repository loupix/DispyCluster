#!/bin/bash
"""Script de démarrage de l'interface web DispyCluster."""

echo "🚀 Démarrage de l'interface web DispyCluster"
echo "=============================================="

# Vérifier l'environnement conda
if command -v conda &> /dev/null; then
    echo "📦 Activation de l'environnement conda 'dispycluster'..."
    conda activate dispycluster
    if [ $? -eq 0 ]; then
        echo "✅ Environnement conda activé"
    else
        echo "⚠️  Impossible d'activer l'environnement conda, utilisation de l'environnement actuel"
    fi
else
    echo "⚠️  Conda non trouvé, utilisation de l'environnement actuel"
fi

# Vérifier les dépendances
echo "🔍 Vérification des dépendances..."
cd "$(dirname "$0")/.."

if [ ! -f "requirements.txt" ]; then
    echo "❌ Fichier requirements.txt non trouvé"
    exit 1
fi

# Installer les dépendances si nécessaire
echo "📥 Installation des dépendances..."
pip install -r requirements.txt

if [ $? -eq 0 ]; then
    echo "✅ Dépendances installées"
else
    echo "❌ Erreur lors de l'installation des dépendances"
    exit 1
fi

# Vérifier Dispy
echo "🔍 Vérification de Dispy..."
python -c "import dispy; print(f'Dispy version: {dispy.__version__}')" 2>/dev/null
if [ $? -eq 0 ]; then
    echo "✅ Dispy disponible"
else
    echo "❌ Dispy non disponible, installation..."
    pip install dispy==4.15.0
fi

# Vérifier la configuration
echo "⚙️  Vérification de la configuration..."
if [ ! -d "templates" ]; then
    echo "❌ Dossier templates manquant"
    exit 1
fi

if [ ! -d "static" ]; then
    echo "❌ Dossier static manquant"
    exit 1
fi

if [ ! -f "app.py" ]; then
    echo "❌ Fichier app.py manquant"
    exit 1
fi

echo "✅ Configuration vérifiée"

# Créer le dossier data si nécessaire
mkdir -p data

# Démarrer l'interface web
echo "🌐 Démarrage de l'interface web..."
echo "   URL: http://localhost:8085"
echo "   API: http://localhost:8085/api"
echo "   Tests: http://localhost:8085/tests"
echo ""
echo "Appuyez sur Ctrl+C pour arrêter"
echo ""

# Démarrer avec uvicorn
python -m uvicorn app:app --host 0.0.0.0 --port 8085 --reload