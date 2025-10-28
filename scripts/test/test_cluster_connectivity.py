#!/usr/bin/env python3
"""
Test de connectivité du cluster DispyCluster
Vérifie que tous les nœuds sont accessibles et répondent correctement
"""

import sys
import os
import socket
import time
import yaml
from pathlib import Path

# Ajouter le répertoire parent au path pour importer les modules
sys.path.append(str(Path(__file__).parent.parent.parent))

from config.dispy_config import LOCAL_IP

def load_nodes_config():
    """Charge la configuration des nœuds depuis nodes.yaml"""
    config_path = Path(__file__).parent.parent.parent / "inventory" / "nodes.yaml"
    try:
        with open(config_path, 'r') as f:
            config = yaml.safe_load(f)
        return config
    except Exception as e:
        print(f"Erreur lors du chargement de la config: {e}")
        return None

def test_ping_connectivity(host, timeout=3):
    """Test de ping vers un hôte"""
    import subprocess
    import platform
    
    try:
        if platform.system().lower() == 'windows':
            # Commande ping pour Windows
            cmd = ['ping', '-n', '1', '-w', str(timeout * 1000), host]
        else:
            # Commande ping pour Linux/Mac
            cmd = ['ping', '-c', '1', '-W', str(timeout), host]
        
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout+2)
        return result.returncode == 0
    except:
        return False

def test_port_connectivity(host, port, timeout=5):
    """Test de connectivité sur un port spécifique"""
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
            sock.settimeout(timeout)
            result = sock.connect_ex((host, port))
            return result == 0
    except:
        return False

def test_dispy_ports(host):
    """Test des ports spécifiques à dispy (ports par défaut)"""
    ports = {
        'Scheduler': 9700,
        'Node': 9701
    }
    
    results = {}
    for service, port in ports.items():
        results[service] = test_port_connectivity(host, port)
    
    return results

def main():
    print("=== Test de connectivité du cluster DispyCluster ===")
    print(f"IP locale: {LOCAL_IP}")
    print()
    
    # Charger la configuration
    config = load_nodes_config()
    if not config:
        print("Impossible de charger la configuration des nœuds")
        return 1
    
    workers = config.get('workers', [])
    master = config.get('master', '')
    
    print(f"Nœuds workers: {workers}")
    print(f"Nœud master: {master}")
    print()
    
    all_ok = True
    
    # Test du master
    if master:
        print(f"Test du master: {master}")
        print("-" * 40)
        
        # Test ping
        ping_ok = test_ping_connectivity(master)
        print(f"Ping: {'✓' if ping_ok else '✗'}")
        
        if ping_ok:
            # Test des ports dispy
            ports_ok = test_dispy_ports(master)
            for service, ok in ports_ok.items():
                print(f"Port {service} (51347): {'✓' if ok else '✗'}")
        else:
            all_ok = False
        
        print()
    
    # Test des workers
    print("Test des workers:")
    print("-" * 40)
    
    for worker in workers:
        print(f"Worker: {worker}")
        
        # Test ping
        ping_ok = test_ping_connectivity(worker)
        print(f"  Ping: {'✓' if ping_ok else '✗'}")
        
        if ping_ok:
            # Test des ports dispy
            ports_ok = test_dispy_ports(worker)
            for service, ok in ports_ok.items():
                print(f"  Port {service}: {'✓' if ok else '✗'}")
        else:
            all_ok = False
        
        print()
    
    # Résumé
    print("=== Résumé ===")
    if all_ok:
        print("✓ Tous les nœuds sont accessibles et répondent correctement")
        return 0
    else:
        print("✗ Certains nœuds ont des problèmes de connectivité")
        return 1

if __name__ == "__main__":
    sys.exit(main())