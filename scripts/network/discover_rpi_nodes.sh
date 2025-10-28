#!/bin/bash

# Script pour découvrir les adresses IP des nœuds RPi sur le réseau
# Usage: ./discover_rpi_nodes.sh

set -e

# Couleurs pour les messages
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo -e "${GREEN}=== Découverte des nœuds RPi sur le réseau ===${NC}"

# Obtenir le réseau local
LOCAL_NETWORK=$(ip route | grep -E "192\.168\.|10\.|172\." | head -1 | awk '{print $1}')
if [[ -z "$LOCAL_NETWORK" ]]; then
    # Fallback: utiliser l'interface principale
    MAIN_INTERFACE=$(ip route | grep default | head -1 | awk '{print $5}')
    LOCAL_NETWORK=$(ip addr show "$MAIN_INTERFACE" | grep "inet " | awk '{print $2}' | head -1)
fi
echo -e "${BLUE}Réseau local détecté: $LOCAL_NETWORK${NC}"

# Fonction pour tester si une IP répond au ping
test_ping() {
    local ip=$1
    if ping -c 1 -W 1 "$ip" >/dev/null 2>&1; then
        return 0
    else
        return 1
    fi
}

# Fonction pour tester le port SSH
test_ssh_port() {
    local ip=$1
    if timeout 3 bash -c "</dev/tcp/$ip/22" 2>/dev/null; then
        return 0
    else
        return 1
    fi
}

# Fonction pour obtenir le nom d'hôte via SSH
get_hostname() {
    local ip=$1
    local user=${2:-pi}
    
    # Essayer de se connecter et récupérer le hostname
    if timeout 10 ssh -o ConnectTimeout=5 -o StrictHostKeyChecking=no -o BatchMode=yes "$user@$ip" "hostname" 2>/dev/null; then
        return 0
    else
        return 1
    fi
}

# Fonction pour obtenir des infos système via SSH
get_system_info() {
    local ip=$1
    local user=${2:-pi}
    
    echo -e "${YELLOW}Informations système pour $ip:${NC}"
    if timeout 10 ssh -o ConnectTimeout=5 -o StrictHostKeyChecking=no -o BatchMode=yes "$user@$ip" "echo 'Hostname:' \$(hostname); echo 'Uptime:' \$(uptime); echo 'OS:' \$(cat /etc/os-release | grep PRETTY_NAME | cut -d'=' -f2 | tr -d '\"')" 2>/dev/null; then
        echo -e "${GREEN}✓ Informations récupérées${NC}"
    else
        echo -e "${RED}✗ Impossible de récupérer les informations${NC}"
    fi
}

# Scanner le réseau
echo -e "\n${BLUE}Scan du réseau $LOCAL_NETWORK...${NC}"
echo -e "${YELLOW}(Cela peut prendre quelques minutes)${NC}"

# Extraire la plage d'adresses
NETWORK_BASE=$(echo "$LOCAL_NETWORK" | cut -d'/' -f1 | cut -d'.' -f1-3)
echo -e "${BLUE}Scan de la plage: $NETWORK_BASE.1-254${NC}"

# Tableau pour stocker les résultats
declare -a FOUND_NODES=()
declare -a SSH_NODES=()

# Scanner les adresses IP
for i in {1..254}; do
    IP="$NETWORK_BASE.$i"
    
    # Éviter de scanner notre propre IP
    if [[ "$IP" == "192.168.1.189" ]]; then
        continue
    fi
    
    echo -ne "\r${YELLOW}Scan en cours: $IP${NC}"
    
    if test_ping "$IP"; then
        echo -e "\n${GREEN}✓ $IP répond au ping${NC}"
        FOUND_NODES+=("$IP")
        
        # Tester le port SSH
        if test_ssh_port "$IP"; then
            echo -e "${GREEN}  ✓ Port SSH (22) ouvert${NC}"
            SSH_NODES+=("$IP")
        else
            echo -e "${YELLOW}  ⚠ Port SSH fermé${NC}"
        fi
    fi
done

echo -e "\n"

# Résumé des découvertes
echo -e "${BLUE}=== Résumé de la découverte ===${NC}"
echo -e "${GREEN}Adresses IP répondant au ping: ${#FOUND_NODES[@]}${NC}"
echo -e "${GREEN}Adresses IP avec SSH ouvert: ${#SSH_NODES[@]}${NC}"

if [[ ${#FOUND_NODES[@]} -gt 0 ]]; then
    echo -e "\n${YELLOW}Adresses découvertes:${NC}"
    for ip in "${FOUND_NODES[@]}"; do
        echo -e "  - $ip"
    done
fi

if [[ ${#SSH_NODES[@]} -gt 0 ]]; then
    echo -e "\n${GREEN}Adresses avec SSH accessible:${NC}"
    for ip in "${SSH_NODES[@]}"; do
        echo -e "  - $ip"
    done
    
    # Essayer d'obtenir des informations sur les nœuds SSH
    echo -e "\n${BLUE}=== Informations sur les nœuds SSH ===${NC}"
    for ip in "${SSH_NODES[@]}"; do
        echo -e "\n${YELLOW}--- $ip ---${NC}"
        
        # Essayer différents utilisateurs
        for user in pi root raspberry; do
            echo -e "${BLUE}Test avec utilisateur: $user${NC}"
            if get_hostname "$ip" "$user"; then
                echo -e "${GREEN}✓ Connexion SSH réussie avec $user@$ip${NC}"
                get_system_info "$ip" "$user"
                break
            else
                echo -e "${RED}✗ Échec avec $user@$ip${NC}"
            fi
        done
    done
fi

# Générer un fichier de configuration
if [[ ${#SSH_NODES[@]} -gt 0 ]]; then
    echo -e "\n${BLUE}=== Génération du fichier de configuration ===${NC}"
    
    cat > inventory/nodes_discovered.yaml << EOF
# Configuration des nœuds découverts automatiquement
# Généré le $(date)

# Nœuds avec SSH accessible
workers_discovered:
EOF
    
    for ip in "${SSH_NODES[@]}"; do
        echo "  - $ip" >> inventory/nodes_discovered.yaml
    done
    
    echo -e "${GREEN}Configuration sauvegardée dans inventory/nodes_discovered.yaml${NC}"
    
    # Proposer la configuration SSH
    echo -e "\n${YELLOW}Veux-tu configurer SSH sans mot de passe pour ces nœuds ?${NC}"
    read -p "Oui/Non (y/N): " -n 1 -r
    echo
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        echo -e "${GREEN}Exécution de la configuration SSH...${NC}"
        ./scripts/network/setup_ssh_keys_ip.sh
    fi
else
    echo -e "\n${RED}Aucun nœud SSH accessible trouvé${NC}"
    echo -e "${YELLOW}Vérifiez que:${NC}"
    echo -e "  - Les nœuds RPi sont allumés et connectés au réseau"
    echo -e "  - SSH est activé sur les nœuds RPi"
    echo -e "  - Les nœuds sont sur le même réseau que le maître"
fi

echo -e "\n${GREEN}Découverte terminée !${NC}"