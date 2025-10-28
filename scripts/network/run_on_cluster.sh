#!/bin/bash

# Script pour exécuter des commandes sur tous les nœuds du cluster RPi
# Usage: ./run_on_cluster.sh "commande à exécuter" [utilisateur]
# Exemple: ./run_on_cluster.sh "sudo systemctl status dispy" pi

set -e

# Couleurs pour les messages
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Vérifier les arguments
if [[ $# -lt 1 ]]; then
    echo -e "${RED}Usage: $0 \"commande à exécuter\" [utilisateur]${NC}"
    echo -e "${YELLOW}Exemples:${NC}"
    echo -e "  $0 \"uptime\" pi"
    echo -e "  $0 \"sudo systemctl status dispy\" pi"
    echo -e "  $0 \"df -h\" pi"
    exit 1
fi

COMMAND="$1"
USERNAME="${2:-pi}"

echo -e "${GREEN}=== Exécution sur le cluster RPi ===${NC}"
echo -e "${BLUE}Commande: $COMMAND${NC}"
echo -e "${BLUE}Utilisateur: $USERNAME${NC}"

# Lire la liste des nœuds depuis le fichier de configuration
NODES_FILE="inventory/nodes.yaml"
if [[ ! -f "$NODES_FILE" ]]; then
    echo -e "${RED}Erreur: Fichier $NODES_FILE non trouvé${NC}"
    exit 1
fi

# Extraire la liste des workers
WORKERS=$(grep -E "^\s*-\s+" "$NODES_FILE" | sed 's/^\s*-\s*//' | tr -d ' ')

echo -e "${GREEN}Nœuds cibles:${NC}"
echo "$WORKERS"

# Fonction pour exécuter la commande sur un nœud
execute_on_node() {
    local node=$1
    local user=$2
    local cmd=$3
    
    echo -e "\n${YELLOW}--- Exécution sur $node ---${NC}"
    
    # Exécuter la commande avec timeout
    if timeout 30 ssh -o ConnectTimeout=10 -o BatchMode=yes -o StrictHostKeyChecking=no "$user@$node" "$cmd" 2>/dev/null; then
        echo -e "${GREEN}✓ Commande exécutée avec succès sur $node${NC}"
        return 0
    else
        echo -e "${RED}✗ Échec de l'exécution sur $node${NC}"
        return 1
    fi
}

# Statistiques
SUCCESS_COUNT=0
TOTAL_COUNT=0

# Exécuter sur chaque nœud
for worker in $WORKERS; do
    TOTAL_COUNT=$((TOTAL_COUNT + 1))
    
    if execute_on_node "$worker" "$USERNAME" "$COMMAND"; then
        SUCCESS_COUNT=$((SUCCESS_COUNT + 1))
    fi
done

# Résumé
echo -e "\n${GREEN}=== Résumé ===${NC}"
echo -e "${GREEN}Nœuds traités avec succès: $SUCCESS_COUNT/$TOTAL_COUNT${NC}"

if [[ $SUCCESS_COUNT -eq $TOTAL_COUNT ]]; then
    echo -e "${GREEN}✓ Commande exécutée sur tous les nœuds${NC}"
elif [[ $SUCCESS_COUNT -gt 0 ]]; then
    echo -e "${YELLOW}⚠ Commande exécutée sur $SUCCESS_COUNT nœuds seulement${NC}"
else
    echo -e "${RED}❌ Aucun nœud n'a pu exécuter la commande${NC}"
fi

echo -e "\n${GREEN}Exécution terminée !${NC}"