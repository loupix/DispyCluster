#!/bin/bash

# Script pour corriger la résolution DNS et configurer les noms .lan
# Usage: ./fix_dns_resolution.sh

set -e

# Couleurs pour les messages
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo -e "${GREEN}=== Correction de la résolution DNS ===${NC}"

# Vérifier les services DNS
echo -e "\n${BLUE}--- Vérification des services DNS ---${NC}"

# Vérifier systemd-resolved
if systemctl is-active systemd-resolved >/dev/null 2>&1; then
    echo -e "${GREEN}✓ systemd-resolved actif${NC}"
else
    echo -e "${YELLOW}⚠ systemd-resolved inactif${NC}"
    echo -e "${YELLOW}Démarrage de systemd-resolved...${NC}"
    sudo systemctl start systemd-resolved
    sudo systemctl enable systemd-resolved
fi

# Vérifier avahi-daemon
if systemctl is-active avahi-daemon >/dev/null 2>&1; then
    echo -e "${GREEN}✓ avahi-daemon actif${NC}"
else
    echo -e "${YELLOW}⚠ avahi-daemon inactif${NC}"
    echo -e "${YELLOW}Démarrage d'avahi-daemon...${NC}"
    sudo systemctl start avahi-daemon
    sudo systemctl enable avahi-daemon
fi

# Vérifier la configuration DNS
echo -e "\n${BLUE}--- Configuration DNS actuelle ---${NC}"
echo -e "${YELLOW}Serveurs DNS configurés:${NC}"
cat /etc/resolv.conf | grep nameserver

# Tester la résolution DNS
echo -e "\n${BLUE}--- Test de résolution DNS ---${NC}"
if nslookup google.com >/dev/null 2>&1; then
    echo -e "${GREEN}✓ Résolution DNS externe OK${NC}"
else
    echo -e "${RED}✗ Problème de résolution DNS externe${NC}"
    echo -e "${YELLOW}Configuration de serveurs DNS publics...${NC}"
    
    # Sauvegarder la configuration actuelle
    sudo cp /etc/resolv.conf /etc/resolv.conf.backup
    
    # Configurer des serveurs DNS publics
    cat << EOF | sudo tee /etc/resolv.conf
# Configuration DNS automatique
nameserver 8.8.8.8
nameserver 8.8.4.4
nameserver 1.1.1.1
EOF
    
    echo -e "${GREEN}Serveurs DNS publics configurés${NC}"
fi

# Configuration des noms .lan dans /etc/hosts
echo -e "\n${BLUE}--- Configuration des noms .lan ---${NC}"

# Demander les adresses IP des nœuds
echo -e "${YELLOW}Configuration manuelle des noms .lan${NC}"
echo -e "${YELLOW}Entrez les adresses IP correspondant aux noms de nœuds:${NC}"

# Sauvegarder /etc/hosts
sudo cp /etc/hosts /etc/hosts.backup

# Ajouter les entrées pour les nœuds
echo -e "\n# Configuration des nœuds du cluster DispyCluster" | sudo tee -a /etc/hosts
echo -e "# Ajouté le $(date)" | sudo tee -a /etc/hosts

# Configuration interactive
NODES_FILE="inventory/nodes.yaml"
if [[ -f "$NODES_FILE" ]]; then
    WORKERS=$(grep -E "^\s*-\s+" "$NODES_FILE" | sed 's/^\s*-\s*//' | tr -d ' ')
    
    for worker in $WORKERS; do
        echo -e "\n${BLUE}--- Configuration de $worker ---${NC}"
        read -p "Adresse IP pour $worker: " ip
        
        if [[ -n "$ip" ]]; then
            echo -e "${GREEN}Ajout de $ip $worker dans /etc/hosts${NC}"
            echo "$ip $worker" | sudo tee -a /etc/hosts
        else
            echo -e "${YELLOW}Ignoré (adresse IP vide)${NC}"
        fi
    done
else
    echo -e "${RED}Fichier $NODES_FILE non trouvé${NC}"
    echo -e "${YELLOW}Configuration manuelle:${NC}"
    
    while true; do
        echo -e "\n${BLUE}--- Ajout manuel ---${NC}"
        read -p "Nom du nœud (ex: node6.lan) ou 'fin' pour terminer: " node_name
        if [[ "$node_name" == "fin" || "$node_name" == "" ]]; then
            break
        fi
        
        read -p "Adresse IP pour $node_name: " ip
        if [[ -n "$ip" ]]; then
            echo -e "${GREEN}Ajout de $ip $node_name dans /etc/hosts${NC}"
            echo "$ip $node_name" | sudo tee -a /etc/hosts
        fi
    done
fi

# Tester la résolution des noms .lan
echo -e "\n${BLUE}--- Test de résolution des noms .lan ---${NC}"
if [[ -f "$NODES_FILE" ]]; then
    WORKERS=$(grep -E "^\s*-\s+" "$NODES_FILE" | sed 's/^\s*-\s+//' | tr -d ' ')
    
    for worker in $WORKERS; do
        echo -e "${YELLOW}Test de résolution pour $worker...${NC}"
        if nslookup "$worker" >/dev/null 2>&1; then
            IP=$(nslookup "$worker" | grep -A1 "Name:" | grep "Address:" | awk '{print $2}' | head -1)
            echo -e "${GREEN}✓ $worker résolu vers $IP${NC}"
        else
            echo -e "${RED}✗ $worker non résolu${NC}"
        fi
    done
fi

# Test de connectivité SSH
echo -e "\n${BLUE}--- Test de connectivité SSH ---${NC}"
if [[ -f "$NODES_FILE" ]]; then
    WORKERS=$(grep -E "^\s*-\s+" "$NODES_FILE" | sed 's/^\s*-\s+//' | tr -d ' ')
    
    for worker in $WORKERS; do
        echo -e "${YELLOW}Test SSH sur $worker...${NC}"
        if timeout 5 bash -c "</dev/tcp/$worker/22" 2>/dev/null; then
            echo -e "${GREEN}✓ Port SSH (22) ouvert sur $worker${NC}"
        else
            echo -e "${RED}✗ Port SSH (22) fermé/inaccessible sur $worker${NC}"
        fi
    done
fi

# Recommandations finales
echo -e "\n${BLUE}=== Recommandations ===${NC}"
echo -e "${GREEN}Configuration DNS terminée !${NC}"
echo -e "\n${YELLOW}Prochaines étapes:${NC}"
echo -e "1. Vérifiez que tous les nœuds RPi sont allumés et connectés"
echo -e "2. Testez la connectivité: ./scripts/network/test_ssh_access.sh"
echo -e "3. Configurez SSH sans mot de passe: ./scripts/network/setup_ssh_keys.sh"

# Option pour restaurer la configuration
echo -e "\n${YELLOW}En cas de problème, vous pouvez restaurer:${NC}"
echo -e "  sudo cp /etc/hosts.backup /etc/hosts"
echo -e "  sudo cp /etc/resolv.conf.backup /etc/resolv.conf"

echo -e "\n${GREEN}Correction DNS terminée !${NC}"