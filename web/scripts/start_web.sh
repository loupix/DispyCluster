#!/bin/bash
# Script de démarrage pour l'interface web DispyCluster

echo "🚀 Démarrage de DispyCluster Web Interface"

# Vérifier l'environnement conda
if ! command -v conda &> /dev/null; then
    echo "❌ Conda n'est pas installé"
    exit 1
fi

# Activer l'environnement conda
echo "🔧 Activation de l'environnement conda 'dispycluster'"
source $(conda info --base)/etc/profile.d/conda.sh
conda activate dispycluster

if [ "$CONDA_DEFAULT_ENV" != "dispycluster" ]; then
    echo "❌ Impossible d'activer l'environnement 'dispycluster'"
    echo "💡 Créez l'environnement avec: conda env create -f environment.yml"
    exit 1
fi

echo "✅ Environnement activé: $CONDA_DEFAULT_ENV"

# Vérifier les dépendances
echo "📦 Vérification des dépendances..."
python -c "import fastapi, uvicorn, jinja2, httpx, sqlite3" 2>/dev/null
if [ $? -ne 0 ]; then
    echo "📥 Installation des dépendances..."
    pip install -r requirements.txt
fi

# Créer le dossier de données si nécessaire
mkdir -p data

# Vérifier les services backend
echo "🔍 Vérification des services backend..."

services=("http://localhost:8081" "http://localhost:8082" "http://localhost:8083" "http://localhost:8084")
service_names=("Cluster Controller" "Monitoring" "Scheduler" "API Gateway")

for i in "${!services[@]}"; do
    if curl -s --connect-timeout 2 "${services[$i]}/health" > /dev/null 2>&1; then
        echo "✅ ${service_names[$i]} (${services[$i]}) - En ligne"
    else
        echo "⚠️  ${service_names[$i]} (${services[$i]}) - Hors ligne"
    fi
done

# Démarrer l'interface web
echo "🌐 Démarrage de l'interface web..."
echo "📍 URL: http://localhost:8085"
echo "🛑 Arrêt: Ctrl+C"

# Variables d'environnement
export HOST=0.0.0.0
export PORT=8085
export DEBUG=false

# Démarrer l'application
python run.py