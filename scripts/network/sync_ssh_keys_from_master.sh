#!/bin/bash

# Script de synchronisation des clés SSH depuis le nœud maître
# Copie les clés SSH de node13 vers tous les autres nœuds

set -e

echo "=== Synchronisation des clés SSH depuis le nœud maître ==="
echo "Copie des clés SSH de node13 vers tous les autres nœuds"
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
ALL_NODES=$(grep -E "^\s*-\s+" "$NODES_CONFIG" | sed 's/^\s*-\s*//' | tr -d ' ')

if [ -z "$ALL_NODES" ]; then
    echo "✗ Aucun nœud trouvé dans la configuration"
    exit 1
fi

# Identifier le nœud maître
MASTER_NODE="node13.lan"

# Filtrer les nœuds workers (exclure le maître)
NODES=""
for node in $ALL_NODES; do
    if [ "$node" != "$MASTER_NODE" ]; then
        NODES="$NODES $node"
    fi
done
echo "Nœud maître: $MASTER_NODE"
echo "Nœuds workers:"
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

# Fonction pour synchroniser les clés SSH d'un nœud
sync_ssh_keys() {
    local target_node=$1
    local username=""
    
    # Déterminer l'utilisateur selon le nœud
    case "$target_node" in
        node9.lan|node10.lan)
            username="pi"
            ;;
        *)
            username="dispy"
            ;;
    esac
    
    echo "Synchronisation des clés SSH vers $target_node (utilisateur: $username)..."
    
    # Tester la connectivité
    if ! test_connectivity "$target_node"; then
        echo "  ✗ Impossible de joindre $target_node"
        return 1
    fi
    
    # Créer le répertoire .ssh sur le nœud cible
    echo "  Création du répertoire .ssh..."
    ssh "$username@$target_node" "sudo mkdir -p /home/dispy/.ssh && sudo chown dispy:dispy /home/dispy/.ssh && sudo chmod 700 /home/dispy/.ssh"
    
    # Copier la clé publique du maître vers le nœud cible
    echo "  Copie de la clé publique..."
    ssh dispy@$MASTER_NODE "cat ~/.ssh/id_rsa.pub" | ssh "$username@$target_node" "sudo tee /home/dispy/.ssh/authorized_keys && sudo chmod 600 /home/dispy/.ssh/authorized_keys && sudo chown dispy:dispy /home/dispy/.ssh/authorized_keys"
    
    # Copier la clé privée du maître vers le nœud cible (pour la cohérence)
    echo "  Copie de la clé privée..."
    ssh dispy@$MASTER_NODE "cat ~/.ssh/id_rsa" | ssh "$username@$target_node" "sudo tee /home/dispy/.ssh/id_rsa && sudo chmod 600 /home/dispy/.ssh/id_rsa && sudo chown dispy:dispy /home/dispy/.ssh/id_rsa"
    
    # Copier la clé publique du maître vers le nœud cible
    echo "  Copie de la clé publique..."
    ssh dispy@$MASTER_NODE "cat ~/.ssh/id_rsa.pub" | ssh "$username@$target_node" "sudo tee /home/dispy/.ssh/id_rsa.pub && sudo chmod 644 /home/dispy/.ssh/id_rsa.pub && sudo chown dispy:dispy /home/dispy/.ssh/id_rsa.pub"
    
    echo "  ✓ Clés SSH synchronisées pour $target_node"
}

# Vérifier que le nœud maître est accessible
echo "Vérification de l'accès au nœud maître..."
if ! test_connectivity "$MASTER_NODE"; then
    echo "✗ Impossible de joindre le nœud maître $MASTER_NODE"
    exit 1
fi

# Vérifier que les clés SSH existent sur le maître
echo "Vérification des clés SSH sur le maître..."
if ! ssh dispy@$MASTER_NODE "test -f ~/.ssh/id_rsa && test -f ~/.ssh/id_rsa.pub"; then
    echo "✗ Clés SSH manquantes sur le nœud maître $MASTER_NODE"
    echo "  Veuillez générer les clés SSH sur le maître avec:"
    echo "  ssh-keygen -t rsa -b 4096 -f ~/.ssh/id_rsa -N ''"
    exit 1
fi

echo "✓ Clés SSH trouvées sur le nœud maître"
echo ""

# Synchroniser tous les nœuds workers
echo "Début de la synchronisation des clés SSH..."
echo ""

SUCCESS_COUNT=0
TOTAL_COUNT=0

for node in $NODES; do
    if [ "$node" != "$MASTER_NODE" ]; then
        TOTAL_COUNT=$((TOTAL_COUNT + 1))
        echo "--- Nœud $node ---"
        
        if sync_ssh_keys "$node"; then
            SUCCESS_COUNT=$((SUCCESS_COUNT + 1))
        else
            echo "  ✗ Échec de la synchronisation pour $node"
        fi
        
        echo ""
    fi
done

# Test final de connectivité
echo "=== Test de connectivité final ==="
echo "Test de l'accès SSH sans mot de passe depuis le maître vers tous les nœuds..."
echo ""

for node in $NODES; do
    if [ "$node" != "$MASTER_NODE" ]; then
        echo -n "Test $node... "
        if ssh dispy@$MASTER_NODE "ssh dispy@$node 'hostname' >/dev/null 2>&1"; then
            echo "✓ OK"
        else
            echo "✗ Échec"
        fi
    fi
done

# Résumé
echo ""
echo "=== Résumé de la synchronisation ==="
echo "Nœuds synchronisés avec succès: $SUCCESS_COUNT/$TOTAL_COUNT"

if [ $SUCCESS_COUNT -eq $TOTAL_COUNT ]; then
    echo "✓ Toutes les clés SSH ont été synchronisées avec succès !"
    echo "✓ Le nœud maître peut maintenant se connecter sans mot de passe à tous les nœuds"
    exit 0
else
    echo "⚠ Certains nœuds n'ont pas pu être synchronisés"
    exit 1
fi