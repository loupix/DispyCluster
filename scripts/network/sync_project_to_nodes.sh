#!/bin/bash

# Script de synchronisation du projet DispyCluster vers tous les nœuds
# Copie le projet vers /home/dispy/DispyCluster sur chaque nœud

set -e

echo "=== Synchronisation du projet DispyCluster ==="
echo "Copie vers /home/dispy/DispyCluster sur tous les nœuds"
echo ""

# Charger la configuration des nœuds
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"
NODES_CONFIG="$PROJECT_ROOT/inventory/nodes.yaml"

if [ ! -f "$NODES_CONFIG" ]; then
    echo "✗ Fichier de configuration des nœuds non trouvé: $NODES_CONFIG"
    exit 1
fi

# Extraire la liste des nœuds depuis le fichier YAML
NODES=$(grep -E "^\s*-\s+" "$NODES_CONFIG" | sed 's/^\s*-\s*//' | tr -d ' ')

if [ -z "$NODES" ]; then
    echo "✗ Aucun nœud trouvé dans la configuration"
    exit 1
fi

echo "Nœuds détectés:"
for node in $NODES; do
    echo "  - $node"
done
echo ""

# Fonction pour tester la connectivité
test_connectivity() {
    local node=$1
    if ping -c 1 -w 2 "$node" >/dev/null 2>&1; then
        return 0
    else
        return 1
    fi
}

# Fonction pour synchroniser un nœud
sync_node() {
    local node=$1
    local username=""
    
    # Déterminer l'utilisateur selon le nœud
    case "$node" in
        node9.lan|node10.lan)
            username="pi"
            ;;
        *)
            username="dispy"
            ;;
    esac
    
    echo "Synchronisation de $node (utilisateur: $username)..."
    
    # Tester la connectivité
    if ! test_connectivity "$node"; then
        echo "  ✗ Impossible de joindre $node"
        return 1
    fi
    
    # Créer le répertoire de destination
    echo "  Création du répertoire de destination..."
    ssh "$username@$node" "sudo mkdir -p /home/dispy/DispyCluster && sudo chown dispy:dispy /home/dispy/DispyCluster"
    
    # Synchroniser les fichiers (exclure les fichiers temporaires et de cache)
    echo "  Synchronisation des fichiers..."
    rsync -avz --delete \
        --exclude='*.pyc' \
        --exclude='__pycache__/' \
        --exclude='.git/' \
        --exclude='_dispy_*' \
        --exclude='*.log' \
        --exclude='temp_*' \
        "$PROJECT_ROOT/" "$username@$node:/tmp/DispyCluster/"
    
    # Copier vers le répertoire final
    echo "  Installation finale..."
    ssh "$username@$node" "sudo cp -r /tmp/DispyCluster/* /home/dispy/DispyCluster/ && sudo chown -R dispy:dispy /home/dispy/DispyCluster"
    
    # Nettoyer le répertoire temporaire
    ssh "$username@$node" "sudo rm -rf /tmp/DispyCluster"
    
    echo "  ✓ Synchronisation terminée pour $node"
}

# Synchroniser tous les nœuds
echo "Début de la synchronisation..."
echo ""

SUCCESS_COUNT=0
TOTAL_COUNT=0

for node in $NODES; do
    TOTAL_COUNT=$((TOTAL_COUNT + 1))
    echo "--- Nœud $node ---"
    
    if sync_node "$node"; then
        SUCCESS_COUNT=$((SUCCESS_COUNT + 1))
    else
        echo "  ✗ Échec de la synchronisation pour $node"
    fi
    
    echo ""
done

# Résumé
echo "=== Résumé de la synchronisation ==="
echo "Nœuds synchronisés avec succès: $SUCCESS_COUNT/$TOTAL_COUNT"

if [ $SUCCESS_COUNT -eq $TOTAL_COUNT ]; then
    echo "✓ Tous les nœuds ont été synchronisés avec succès !"
    exit 0
else
    echo "⚠ Certains nœuds n'ont pas pu être synchronisés"
    exit 1
fi