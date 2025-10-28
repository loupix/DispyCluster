#!/bin/bash

# Script de synchronisation des clés SSH sans sudo
# À exécuter directement sur node13

set -e

echo "=== Synchronisation des clés SSH depuis node13 (sans sudo) ==="
echo "Ce script doit être exécuté sur node13"
echo ""

# Vérifier qu'on est sur node13
CURRENT_HOST=$(hostname)
if [[ "$CURRENT_HOST" != "raspberry-13" ]]; then
    echo "⚠ Attention: Ce script doit être exécuté sur node13 (raspberry-13)"
    echo "  Hostname actuel: $CURRENT_HOST"
    echo "  Continuer quand même ? (y/N)"
    read -r response
    if [[ "$response" != "y" && "$response" != "Y" ]]; then
        exit 1
    fi
fi

# Liste des nœuds workers
WORKER_NODES="node6.lan node7.lan node9.lan node10.lan node11.lan node12.lan node14.lan"

echo "Nœuds workers à synchroniser:"
for node in $WORKER_NODES; do
    echo "  - $node"
done
echo ""

# Vérifier que les clés SSH existent
if [ ! -f ~/.ssh/id_rsa ] || [ ! -f ~/.ssh/id_rsa.pub ]; then
    echo "✗ Clés SSH manquantes sur node13"
    echo "  Génération des clés SSH..."
    ssh-keygen -t rsa -b 4096 -f ~/.ssh/id_rsa -N ""
    echo "✓ Clés SSH générées"
fi

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
    
    echo "Synchronisation vers $node (utilisateur: $username)..."
    
    # Tester la connectivité
    if ! ping -c 1 -w 2 "$node" >/dev/null 2>&1; then
        echo "  ✗ Impossible de joindre $node"
        return 1
    fi
    
    # Créer le répertoire .ssh sur le nœud cible (sans sudo)
    echo "  Création du répertoire .ssh..."
    ssh "$username@$node" "mkdir -p ~/.ssh && chmod 700 ~/.ssh"
    
    # Copier la clé publique
    echo "  Copie de la clé publique..."
    cat ~/.ssh/id_rsa.pub | ssh "$username@$node" "cat > ~/.ssh/authorized_keys && chmod 600 ~/.ssh/authorized_keys"
    
    # Copier la clé privée
    echo "  Copie de la clé privée..."
    cat ~/.ssh/id_rsa | ssh "$username@$node" "cat > ~/.ssh/id_rsa && chmod 600 ~/.ssh/id_rsa"
    
    # Copier la clé publique
    echo "  Copie de la clé publique..."
    cat ~/.ssh/id_rsa.pub | ssh "$username@$node" "cat > ~/.ssh/id_rsa.pub && chmod 644 ~/.ssh/id_rsa.pub"
    
    echo "  ✓ Clés SSH synchronisées pour $node"
}

# Synchroniser tous les nœuds
echo "Début de la synchronisation..."
echo ""

SUCCESS_COUNT=0
TOTAL_COUNT=0

for node in $WORKER_NODES; do
    TOTAL_COUNT=$((TOTAL_COUNT + 1))
    echo "--- Nœud $node ---"
    
    if sync_node "$node"; then
        SUCCESS_COUNT=$((SUCCESS_COUNT + 1))
    else
        echo "  ✗ Échec de la synchronisation pour $node"
    fi
    
    echo ""
done

# Test final de connectivité
echo "=== Test de connectivité final ==="
echo "Test de l'accès SSH sans mot de passe vers tous les nœuds..."
echo ""

for node in $WORKER_NODES; do
    echo -n "Test $node... "
    if ssh dispy@$node 'hostname' >/dev/null 2>&1; then
        echo "✓ OK"
    else
        echo "✗ Échec"
    fi
done

# Résumé
echo ""
echo "=== Résumé de la synchronisation ==="
echo "Nœuds synchronisés avec succès: $SUCCESS_COUNT/$TOTAL_COUNT"

if [ $SUCCESS_COUNT -eq $TOTAL_COUNT ]; then
    echo "✓ Toutes les clés SSH ont été synchronisées avec succès !"
    echo "✓ Node13 peut maintenant se connecter sans mot de passe à tous les nœuds"
    exit 0
else
    echo "⚠ Certains nœuds n'ont pas pu être synchronisés"
    exit 1
fi