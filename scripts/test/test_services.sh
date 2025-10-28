#!/bin/bash

# Script de test rapide pour les services DispyCluster
# Ce script vérifie que tous les services sont accessibles et fonctionnels

set -e

echo "=== Test des services DispyCluster ==="
echo "Timestamp: $(date)"
echo ""

# Couleurs pour l'affichage
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Fonction pour tester un endpoint
test_endpoint() {
    local url=$1
    local name=$2
    local expected_status=${3:-200}
    
    echo -n "Test de $name... "
    
    if response=$(curl -s -w "%{http_code}" -o /dev/null "$url" 2>/dev/null); then
        if [ "$response" = "$expected_status" ]; then
            echo -e "${GREEN}✓ OK${NC} (HTTP $response)"
            return 0
        else
            echo -e "${YELLOW}⚠ WARNING${NC} (HTTP $response, attendu $expected_status)"
            return 1
        fi
    else
        echo -e "${RED}✗ ERREUR${NC} (Service non accessible)"
        return 1
    fi
}

# Fonction pour tester un endpoint avec JSON
test_json_endpoint() {
    local url=$1
    local name=$2
    local key=$3
    
    echo -n "Test de $name... "
    
    if response=$(curl -s "$url" 2>/dev/null); then
        if echo "$response" | jq -e ".$key" >/dev/null 2>&1; then
            echo -e "${GREEN}✓ OK${NC} (JSON valide)"
            return 0
        else
            echo -e "${YELLOW}⚠ WARNING${NC} (JSON invalide ou clé '$key' manquante)"
            return 1
        fi
    else
        echo -e "${RED}✗ ERREUR${NC} (Service non accessible)"
        return 1
    fi
}

# Vérifier que jq est installé
if ! command -v jq &> /dev/null; then
    echo "Installation de jq..."
    sudo apt-get update && sudo apt-get install -y jq
fi

# Tests des services individuels
echo "=== Tests des services individuels ==="

# Test du contrôleur du cluster
test_endpoint "http://localhost:8081/health" "Contrôleur du cluster"
test_json_endpoint "http://localhost:8081/cluster" "Statistiques du cluster" "total_workers"

# Test du service de monitoring
test_endpoint "http://localhost:8082/health" "Service de monitoring"
test_json_endpoint "http://localhost:8082/cluster/health" "Santé du cluster" "overall_status"

# Test du planificateur
test_endpoint "http://localhost:8083/health" "Planificateur"
test_json_endpoint "http://localhost:8083/tasks" "Tâches planifiées" "length"

# Test de l'API Gateway
test_endpoint "http://localhost:8084/health" "API Gateway"
test_json_endpoint "http://localhost:8084/overview" "Vue d'ensemble" "status"

# Test du service de scraping existant
test_endpoint "http://localhost:8080/health" "Service de scraping"

echo ""
echo "=== Tests fonctionnels ==="

# Test de ping des workers
echo "Test de ping des workers..."
for node in node6.lan node7.lan node9.lan; do
    echo -n "  Ping $node... "
    if response=$(curl -s -X POST "http://localhost:8081/workers/$node/ping" 2>/dev/null); then
        if echo "$response" | jq -e '.status' >/dev/null 2>&1; then
            status=$(echo "$response" | jq -r '.status')
            if [ "$status" = "online" ]; then
                echo -e "${GREEN}✓ En ligne${NC}"
            else
                echo -e "${YELLOW}⚠ $status${NC}"
            fi
        else
            echo -e "${YELLOW}⚠ Réponse invalide${NC}"
        fi
    else
        echo -e "${RED}✗ Hors ligne${NC}"
    fi
done

# Test de création d'un job de scraping
echo ""
echo "Test de création d'un job de scraping..."
if response=$(curl -s -X POST "http://localhost:8081/scrape" \
    -H "Content-Type: application/json" \
    -d '{"start_url": "https://httpbin.org/html", "max_pages": 1, "timeout_s": 10}' 2>/dev/null); then
    
    if echo "$response" | jq -e '.job_id' >/dev/null 2>&1; then
        job_id=$(echo "$response" | jq -r '.job_id')
        echo -e "${GREEN}✓ Job créé: $job_id${NC}"
        
        # Attendre un peu et vérifier le statut
        echo "Attente de l'exécution du job..."
        sleep 3
        
        if status_response=$(curl -s "http://localhost:8081/jobs/$job_id" 2>/dev/null); then
            if echo "$status_response" | jq -e '.status' >/dev/null 2>&1; then
                status=$(echo "$status_response" | jq -r '.status')
                echo -e "Statut du job: ${GREEN}$status${NC}"
            fi
        fi
    else
        echo -e "${YELLOW}⚠ Erreur lors de la création du job${NC}"
    fi
else
    echo -e "${RED}✗ Impossible de créer un job${NC}"
fi

# Test de création d'une tâche planifiée
echo ""
echo "Test de création d'une tâche planifiée..."
if response=$(curl -s -X POST "http://localhost:8083/tasks" \
    -H "Content-Type: application/json" \
    -d '{
        "name": "Test automatique",
        "urls": ["https://httpbin.org/html"],
        "max_pages": 1,
        "schedule_type": "once",
        "schedule_config": {}
    }' 2>/dev/null); then
    
    if echo "$response" | jq -e '.task_id' >/dev/null 2>&1; then
        task_id=$(echo "$response" | jq -r '.task_id')
        echo -e "${GREEN}✓ Tâche créée: $task_id${NC}"
        
        # Exécuter la tâche immédiatement
        echo "Exécution immédiate de la tâche..."
        if curl -s -X POST "http://localhost:8083/tasks/$task_id/run" >/dev/null; then
            echo -e "${GREEN}✓ Tâche lancée${NC}"
        else
            echo -e "${YELLOW}⚠ Erreur lors du lancement${NC}"
        fi
    else
        echo -e "${YELLOW}⚠ Erreur lors de la création de la tâche${NC}"
    fi
else
    echo -e "${RED}✗ Impossible de créer une tâche${NC}"
fi

# Test du tableau de bord
echo ""
echo "Test du tableau de bord..."
if response=$(curl -s "http://localhost:8084/dashboard" 2>/dev/null); then
    if echo "$response" | jq -e '.data' >/dev/null 2>&1; then
        echo -e "${GREEN}✓ Tableau de bord accessible${NC}"
        
        # Afficher quelques statistiques
        if echo "$response" | jq -e '.data.cluster_stats' >/dev/null 2>&1; then
            total_workers=$(echo "$response" | jq -r '.data.cluster_stats.total_workers // "N/A"')
            online_workers=$(echo "$response" | jq -r '.data.cluster_stats.online_workers // "N/A"')
            echo "  - Workers: $online_workers/$total_workers en ligne"
        fi
    else
        echo -e "${YELLOW}⚠ Données du tableau de bord invalides${NC}"
    fi
else
    echo -e "${RED}✗ Tableau de bord non accessible${NC}"
fi

echo ""
echo "=== Résumé des tests ==="

# Compter les services en ligne
services_online=0
total_services=5

for port in 8080 8081 8082 8083 8084; do
    if curl -s "http://localhost:$port/health" >/dev/null 2>&1; then
        ((services_online++))
    fi
done

echo "Services en ligne: $services_online/$total_services"

if [ $services_online -eq $total_services ]; then
    echo -e "${GREEN}✓ Tous les services sont opérationnels${NC}"
    exit 0
elif [ $services_online -gt 0 ]; then
    echo -e "${YELLOW}⚠ Certains services sont hors ligne${NC}"
    exit 1
else
    echo -e "${RED}✗ Aucun service n'est accessible${NC}"
    exit 2
fi