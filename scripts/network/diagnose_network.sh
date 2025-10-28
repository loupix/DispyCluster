#!/bin/bash

# Script de diagnostic réseau pour le cluster RPi
# Usage: ./diagnose_network.sh

set -e

# Couleurs pour les messages
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo -e "${GREEN}=== Diagnostic réseau du cluster RPi ===${NC}"

# Informations sur le nœud actuel
echo -e "\n${BLUE}--- Informations sur le nœud actuel ---${NC}"
echo -e "${YELLOW}Nom d'hôte:${NC} $(hostname)"
echo -e "${YELLOW}Adresse IP:${NC} $(hostname -I)"
echo -e "${YELLOW}Interface réseau principale:${NC}"
ip route | grep default | head -1

# Configuration réseau
echo -e "\n${BLUE}--- Configuration réseau ---${NC}"
echo -e "${YELLOW}Interfaces réseau:${NC}"
ip addr show | grep -E "inet |UP|DOWN" | grep -v "127.0.0.1"

echo -e "\n${YELLOW}Table de routage:${NC}"
ip route

# Test de connectivité locale
echo -e "\n${BLUE}--- Test de connectivité locale ---${NC}"
if ping -c 1 -W 2 127.0.0.1 >/dev/null 2>&1; then
    echo -e "${GREEN}✓ Loopback (127.0.0.1) OK${NC}"
else
    echo -e "${RED}✗ Loopback (127.0.0.1) ÉCHEC${NC}"
fi

# Test de connectivité vers la passerelle
GATEWAY=$(ip route | grep default | awk '{print $3}' | head -1)
if [[ -n "$GATEWAY" ]]; then
    echo -e "${YELLOW}Test de la passerelle ($GATEWAY)...${NC}"
    if ping -c 1 -W 2 "$GATEWAY" >/dev/null 2>&1; then
        echo -e "${GREEN}✓ Passerelle ($GATEWAY) accessible${NC}"
    else
        echo -e "${RED}✗ Passerelle ($GATEWAY) inaccessible${NC}"
    fi
else
    echo -e "${RED}✗ Aucune passerelle configurée${NC}"
fi

# Test DNS
echo -e "\n${BLUE}--- Test DNS ---${NC}"
if nslookup google.com >/dev/null 2>&1; then
    echo -e "${GREEN}✓ Résolution DNS fonctionnelle${NC}"
else
    echo -e "${RED}✗ Problème de résolution DNS${NC}"
fi

# Test de résolution des noms de nœuds
echo -e "\n${BLUE}--- Test de résolution des noms de nœuds ---${NC}"
NODES_FILE="inventory/nodes.yaml"
if [[ -f "$NODES_FILE" ]]; then
    WORKERS=$(grep -E "^\s*-\s+" "$NODES_FILE" | sed 's/^\s*-\s*//' | tr -d ' ')
    
    for worker in $WORKERS; do
        echo -e "${YELLOW}Test de résolution pour $worker...${NC}"
        if nslookup "$worker" >/dev/null 2>&1; then
            IP=$(nslookup "$worker" | grep -A1 "Name:" | grep "Address:" | awk '{print $2}' | head -1)
            echo -e "${GREEN}✓ $worker résolu vers $IP${NC}"
        else
            echo -e "${RED}✗ $worker non résolu${NC}"
        fi
    done
else
    echo -e "${RED}Fichier $NODES_FILE non trouvé${NC}"
fi

# Scan du réseau local
echo -e "\n${BLUE}--- Scan du réseau local ---${NC}"
LOCAL_NETWORK=$(ip route | grep -E "192\.168\.|10\.|172\." | head -1 | awk '{print $1}')
if [[ -n "$LOCAL_NETWORK" ]]; then
    echo -e "${YELLOW}Scan du réseau $LOCAL_NETWORK...${NC}"
    echo -e "${YELLOW}(Cela peut prendre quelques secondes)${NC}"
    
    # Utiliser nmap si disponible, sinon ping simple
    if command -v nmap &> /dev/null; then
        nmap -sn "$LOCAL_NETWORK" 2>/dev/null | grep -E "Nmap scan report|MAC Address" | head -20
    else
        echo -e "${YELLOW}nmap non disponible, test ping simple...${NC}"
        # Test ping sur quelques adresses communes
        for i in {1..10}; do
            IP="${LOCAL_NETWORK%.*}.$i"
            if ping -c 1 -W 1 "$IP" >/dev/null 2>&1; then
                echo -e "${GREEN}✓ $IP accessible${NC}"
            fi
        done
    fi
else
    echo -e "${RED}Aucun réseau local détecté${NC}"
fi

# Test des ports SSH
echo -e "\n${BLUE}--- Test des ports SSH ---${NC}"
if [[ -f "$NODES_FILE" ]]; then
    WORKERS=$(grep -E "^\s*-\s+" "$NODES_FILE" | sed 's/^\s*-\s*//' | tr -d ' ')
    
    for worker in $WORKERS; do
        echo -e "${YELLOW}Test SSH sur $worker...${NC}"
        if timeout 5 bash -c "</dev/tcp/$worker/22" 2>/dev/null; then
            echo -e "${GREEN}✓ Port SSH (22) ouvert sur $worker${NC}"
        else
            echo -e "${RED}✗ Port SSH (22) fermé/inaccessible sur $worker${NC}"
        fi
    done
fi

# Informations sur les services réseau
echo -e "\n${BLUE}--- Services réseau ---${NC}"
echo -e "${YELLOW}Service SSH:${NC}"
if systemctl is-active ssh >/dev/null 2>&1; then
    echo -e "${GREEN}✓ SSH actif${NC}"
else
    echo -e "${RED}✗ SSH inactif${NC}"
fi

echo -e "\n${YELLOW}Service avahi-daemon (mDNS):${NC}"
if systemctl is-active avahi-daemon >/dev/null 2>&1; then
    echo -e "${GREEN}✓ avahi-daemon actif${NC}"
else
    echo -e "${YELLOW}⚠ avahi-daemon inactif (peut expliquer les problèmes de résolution .lan)${NC}"
fi

# Recommandations
echo -e "\n${BLUE}=== Recommandations ===${NC}"

# Vérifier si avahi est installé et démarré
if ! systemctl is-active avahi-daemon >/dev/null 2>&1; then
    echo -e "${YELLOW}1. Démarrer avahi-daemon pour la résolution .lan:${NC}"
    echo -e "   sudo systemctl start avahi-daemon"
    echo -e "   sudo systemctl enable avahi-daemon"
fi

# Vérifier la configuration réseau
if [[ -z "$GATEWAY" ]]; then
    echo -e "${RED}2. Problème de configuration réseau - aucune passerelle${NC}"
    echo -e "   Vérifiez la configuration DHCP ou configurez manuellement"
fi

# Vérifier les noms de nœuds
UNRESOLVED_NODES=0
if [[ -f "$NODES_FILE" ]]; then
    WORKERS=$(grep -E "^\s*-\s+" "$NODES_FILE" | sed 's/^\s*-\s+//' | tr -d ' ')
    for worker in $WORKERS; do
        if ! nslookup "$worker" >/dev/null 2>&1; then
            UNRESOLVED_NODES=$((UNRESOLVED_NODES + 1))
        fi
    done
fi

if [[ $UNRESOLVED_NODES -gt 0 ]]; then
    echo -e "${YELLOW}3. $UNRESOLVED_NODES nœuds non résolus${NC}"
    echo -e "   Options:"
    echo -e "   - Utiliser des adresses IP au lieu des noms"
    echo -e "   - Configurer /etc/hosts sur chaque nœud"
    echo -e "   - Démarrer avahi-daemon sur tous les nœuds"
fi

echo -e "\n${GREEN}Diagnostic terminé !${NC}"