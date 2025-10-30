#!/bin/bash
# Script de démarrage pour Raspberry Pi
# Équivalent de start_all.ps1 pour Linux

set -e  # Arrêter en cas d'erreur

# Couleurs pour les messages
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo -e "${GREEN}=== Démarrage DispyCluster ===${NC}"

# Détecter et activer l'environnement (conda ou venv)
ACTIVATE_FAILED=false

# Essayer conda d'abord
if command -v conda &> /dev/null; then
    echo "Tentative d'activation avec conda..."
    source "$(conda info --base)/etc/profile.d/conda.sh"
    conda activate dispycluster 2>/dev/null
    
    if [ $? -eq 0 ]; then
        echo -e "${GREEN}Environnement conda actif: $CONDA_DEFAULT_ENV${NC}"
        ENV_ACTIVATED=true
    else
        echo -e "${YELLOW}Environnement conda non trouvé, essai avec venv...${NC}"
        ACTIVATE_FAILED=true
    fi
else
    ACTIVATE_FAILED=true
fi

# Si conda n'a pas fonctionné, essayer venv
if [ "$ACTIVATE_FAILED" = true ]; then
    if [ -d "venv" ]; then
        echo "Activation de l'environnement venv..."
        source venv/bin/activate
        echo -e "${GREEN}Environnement venv actif${NC}"
        ENV_ACTIVATED=true
    else
        echo -e "${RED}Erreur: aucun environnement trouvé (conda ou venv)${NC}"
        echo "Exécutez d'abord: ./install_rpi_environment.sh"
        exit 1
    fi
fi

# Config Redis distant
export REDIS_HOST=localhost
export REDIS_PORT=6379
export CELERY_BROKER_URL=redis://localhost:6379/0
export CELERY_RESULT_BACKEND=redis://localhost:6379/1

# Config logging
export LOG_LEVEL=INFO
export LOG_FILE=logs/dispycluster.log

# Vérifier dépendances minimales
echo "Vérification des dépendances..."
python -c "import celery, redis" 2>/dev/null
if [ $? -ne 0 ]; then
    echo -e "${YELLOW}Installation des dépendances web...${NC}"
    pip install -r web/requirements.txt
fi

# Fonction de nettoyage à l'arrêt
cleanup() {
    echo -e "\n${YELLOW}Arrêt des processus...${NC}"
    
    # Arrêter Celery worker
    if [ ! -z "$CELERY_WORKER_PID" ]; then
        echo "Arrêt du worker Celery (PID: $CELERY_WORKER_PID)..."
        kill $CELERY_WORKER_PID 2>/dev/null || true
    fi
    
    # Arrêter Celery beat
    if [ ! -z "$CELERY_BEAT_PID" ]; then
        echo "Arrêt de Celery beat (PID: $CELERY_BEAT_PID)..."
        kill $CELERY_BEAT_PID 2>/dev/null || true
    fi
    
    # Arrêter les services legacy si démarrés
    if [ "$START_LEGACY_SERVICES" = "true" ]; then
        for pid in $SVC_CONTROLLER_PID $SVC_MONITORING_PID $SVC_SCHEDULER_PID $SVC_GATEWAY_PID; do
            if [ ! -z "$pid" ]; then
                kill $pid 2>/dev/null || true
            fi
        done
    fi
    
    echo -e "${GREEN}Arrêt terminé${NC}"
    exit 0
}

# Intercepter Ctrl+C et autres signaux d'arrêt
trap cleanup SIGINT SIGTERM

# Démarrer Celery worker en arrière-plan
echo -e "${GREEN}Démarrage du worker Celery en arrière-plan...${NC}"
export PYTHONUNBUFFERED=1
celery -A web.celery_app.celery_app worker --loglevel=info --concurrency=1 > logs/celery_worker.log 2>&1 &
CELERY_WORKER_PID=$!
echo "Worker Celery démarré (PID: $CELERY_WORKER_PID)"

# Attendre un peu pour le démarrage
sleep 2

# Démarrer Celery beat en arrière-plan
echo -e "${GREEN}Démarrage de Celery beat (scheduler) en arrière-plan...${NC}"
celery -A web.celery_app.celery_app beat --loglevel=info > logs/celery_beat.log 2>&1 &
CELERY_BEAT_PID=$!
echo "Celery beat démarré (PID: $CELERY_BEAT_PID)"

# Attendre un peu
sleep 3

# Optionnel : démarrer les services legacy
START_LEGACY_SERVICES=false
if [ "$START_LEGACY_SERVICES" = "true" ]; then
    echo -e "${YELLOW}Démarrage des services legacy...${NC}"
    
    python legacy/services/cluster_controller.py > logs/cluster_controller.log 2>&1 &
    SVC_CONTROLLER_PID=$!
    sleep 1
    
    python legacy/services/monitoring_service.py > logs/monitoring_service.log 2>&1 &
    SVC_MONITORING_PID=$!
    sleep 1
    
    python legacy/services/scheduler_service.py > logs/scheduler_service.log 2>&1 &
    SVC_SCHEDULER_PID=$!
    sleep 1
    
    python legacy/services/api_gateway.py > logs/api_gateway.log 2>&1 &
    SVC_GATEWAY_PID=$!
    
    # Vérifier les health endpoints
    echo "Vérification des services (health)..."
    health_targets=(
        "cluster_controller:http://localhost:8081/health"
        "monitoring:http://localhost:8082/health"
        "scheduler:http://localhost:8083/health"
        "api_gateway:http://localhost:8084/health"
    )
    
    for target in "${health_targets[@]}"; do
        name=$(echo $target | cut -d: -f1)
        url=$(echo $target | cut -d: -f2-)
        ok=false
        
        for i in {1..20}; do
            if curl -s --connect-timeout 2 $url > /dev/null 2>&1; then
                ok=true
                break
            fi
            sleep 1
        done
        
        if [ "$ok" = true ]; then
            echo -e "${GREEN}✓ $name en ligne: $url${NC}"
        else
            echo -e "${RED}⚠ $name hors ligne: $url${NC}"
        fi
    done
fi

# Créer le répertoire logs s'il n'existe pas
mkdir -p logs

# Lancer l'API/UI en avant-plan
echo -e "${GREEN}Démarrage de l'API/UI (Uvicorn) sur http://0.0.0.0:8085...${NC}"
echo "📊 Graphiques disponibles sur: http://localhost:8085/monitoring"
echo "🔧 API Graphiques: http://localhost:8085/api/graphs/"
export WEB_SIMULATE_NODES=0
uvicorn web.app:create_socketio_app --factory --host 0.0.0.0 --port 8085

# Le cleanup se fera automatiquement via le trap quand uvicorn s'arrêtera

