#!/bin/bash

# Script pour forcer la correction du home directory de l'utilisateur dispy
# À exécuter depuis node13

echo "=== Correction forcée du home directory pour dispy ==="

# Fonction pour corriger le home directory sur un nœud
fix_dispy_home_force() {
    local node=$1
    
    echo "--- Correction forcée sur $node ---"
    
    # Tuer tous les processus de l'utilisateur dispy
    echo "Arrêt des processus dispy..."
    ssh pi@$node "
        # Tuer tous les processus de dispy
        sudo pkill -u dispy 2>/dev/null || true
        sleep 2
        
        # Forcer l'arrêt si nécessaire
        sudo pkill -9 -u dispy 2>/dev/null || true
        sleep 1
    "
    
    # Corriger le home directory
    echo "Correction du home directory..."
    ssh pi@$node "
        # Changer le home directory vers /home/dispy
        sudo usermod -d /home/dispy dispy
        
        # Créer le répertoire /home/dispy s'il n'existe pas
        sudo mkdir -p /home/dispy
        
        # Copier les fichiers de /var/lib/dispy vers /home/dispy si nécessaire
        if [ -d /var/lib/dispy ] && [ \"\$(ls -A /var/lib/dispy 2>/dev/null)\" ]; then
            echo 'Copie des fichiers de /var/lib/dispy vers /home/dispy...'
            sudo cp -r /var/lib/dispy/* /home/dispy/ 2>/dev/null || true
        fi
        
        # Définir les bonnes permissions
        sudo chown -R dispy:dispy /home/dispy
        sudo chmod 755 /home/dispy
        
        echo 'Home directory corrigé pour dispy'
    "
    
    # Vérifier la correction
    echo "Vérification de la correction..."
    ssh pi@$node "
        echo 'Utilisateur dispy après correction:'
        getent passwd dispy
        
        echo 'Contenu de /home/dispy:'
        ls -la /home/dispy/
        
        echo 'Contenu de /var/lib/dispy:'
        ls -la /var/lib/dispy/ 2>/dev/null || echo 'Pas de /var/lib/dispy'
    "
    
    # Tester la connexion SSH
    echo "Test de la connexion SSH..."
    if ssh -o BatchMode=yes -o ConnectTimeout=5 "dispy@$node" "echo 'Connexion dispy OK'" 2>/dev/null; then
        echo "✓ Connexion dispy@$node corrigée"
        return 0
    else
        echo "✗ Échec de la correction pour dispy@$node"
        return 1
    fi
}

# Corriger node9 et node10
fix_dispy_home_force "node9.lan"
fix_dispy_home_force "node10.lan"

echo "=== Test final ==="
echo "Test de dispy@node9.lan..."
if ssh -o BatchMode=yes -o ConnectTimeout=5 "dispy@node9.lan" "echo 'OK'" 2>/dev/null; then
    echo "✓ dispy@node9.lan: Connexion OK"
else
    echo "✗ dispy@node9.lan: Connexion échoue"
fi

echo "Test de dispy@node10.lan..."
if ssh -o BatchMode=yes -o ConnectTimeout=5 "dispy@node10.lan" "echo 'OK'" 2>/dev/null; then
    echo "✓ dispy@node10.lan: Connexion OK"
else
    echo "✗ dispy@node10.lan: Connexion échoue"
fi

echo "=== Correction terminée ==="