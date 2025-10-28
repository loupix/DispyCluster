#!/usr/bin/env python3
"""
Diagnostic de santé du cluster DispyCluster
Vérifie l'état de tous les nœuds et services
"""

import sys
import os
import time
import yaml
import socket
import subprocess
from pathlib import Path
from datetime import datetime

# Ajouter le répertoire parent au path pour importer les modules
sys.path.append(str(Path(__file__).parent.parent.parent))

import dispy
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

def check_system_resources():
    """Vérifie les ressources système locales"""
    print("=== Ressources système locales ===")
    
    try:
        import psutil
        
        # CPU
        cpu_percent = psutil.cpu_percent(interval=1)
        cpu_count = psutil.cpu_count()
        print(f"CPU: {cpu_percent}% utilisé ({cpu_count} cœurs)")
        
        # Mémoire
        memory = psutil.virtual_memory()
        print(f"Mémoire: {memory.percent}% utilisée ({memory.used // (1024**3)}GB / {memory.total // (1024**3)}GB)")
        
        # Disque
        disk = psutil.disk_usage('/')
        print(f"Disque: {disk.percent}% utilisé ({disk.used // (1024**3)}GB / {disk.total // (1024**3)}GB)")
        
        # Réseau
        network = psutil.net_io_counters()
        print(f"Réseau: {network.bytes_sent // (1024**2)}MB envoyés, {network.bytes_recv // (1024**2)}MB reçus")
        
    except ImportError:
        print("psutil non disponible, utilisation des commandes système")
        
        # CPU avec top
        try:
            result = subprocess.run(['top', '-bn1'], capture_output=True, text=True, timeout=5)
            if result.returncode == 0:
                lines = result.stdout.split('\n')
                for line in lines:
                    if 'Cpu(s)' in line:
                        print(f"CPU: {line}")
                        break
        except:
            print("Impossible d'obtenir les infos CPU")
        
        # Mémoire avec free
        try:
            result = subprocess.run(['free', '-h'], capture_output=True, text=True, timeout=5)
            if result.returncode == 0:
                lines = result.stdout.split('\n')
                if len(lines) > 1:
                    print(f"Mémoire: {lines[1]}")
        except:
            print("Impossible d'obtenir les infos mémoire")

def check_network_connectivity(host):
    """Vérifie la connectivité réseau vers un hôte"""
    print(f"\n=== Connectivité réseau: {host} ===")
    
    # Test ping
    try:
        result = subprocess.run(['ping', '-c', '3', '-W', '2', host], 
                              capture_output=True, text=True, timeout=10)
        if result.returncode == 0:
            print("✓ Ping: OK")
            
            # Extraire le temps de réponse moyen
            lines = result.stdout.split('\n')
            for line in lines:
                if 'avg' in line:
                    print(f"  Temps de réponse: {line.split('=')[1].strip()}")
                    break
        else:
            print("✗ Ping: ÉCHEC")
            return False
    except Exception as e:
        print(f"✗ Ping: Erreur - {e}")
        return False
    
    # Test des ports dispy
    ports = {
        'Scheduler': 51347,
        'Node': 51348
    }
    
    for service, port in ports.items():
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
                sock.settimeout(5)
                result = sock.connect_ex((host, port))
                if result == 0:
                    print(f"✓ Port {service} ({port}): OK")
                else:
                    print(f"✗ Port {service} ({port}): FERMÉ")
        except Exception as e:
            print(f"✗ Port {service} ({port}): Erreur - {e}")
    
    return True

def check_dispy_services():
    """Vérifie les services dispy locaux"""
    print("\n=== Services Dispy locaux ===")
    
    # Vérifier si dispy est installé
    try:
        import dispy
        print(f"✓ Dispy installé: version {dispy.__version__}")
    except ImportError:
        print("✗ Dispy non installé")
        return False
    
    # Vérifier la configuration
    print(f"IP locale: {LOCAL_IP}")
    print(f"Scheduler: {dispy.config.SchedulerIPAddr}:{dispy.config.SchedulerPort}")
    print(f"Node: {dispy.config.NodeIPAddr}:{dispy.config.NodePort}")
    
    # Vérifier les ports locaux (ports par défaut dispy)
    ports = [9700, 9701]  # Ports par défaut dispy
    for port in ports:
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
                sock.settimeout(1)
                result = sock.connect_ex(('localhost', port))
                if result == 0:
                    print(f"✓ Port local {port}: OCCUPÉ")
                else:
                    print(f"○ Port local {port}: LIBRE")
        except:
            print(f"? Port local {port}: Indéterminé")
    
    return True

def check_cluster_status():
    """Vérifie le statut du cluster dispy"""
    print("\n=== Statut du cluster Dispy ===")
    
    try:
        # Créer un cluster de test
        def test_func(x):
            return x * 2
        
        cluster = dispy.JobCluster(test_func)
        time.sleep(3)  # Attendre la connexion des nœuds
        
        # Obtenir le statut
        status = cluster.status()
        print(f"Statut du cluster: {status}")
        
        # Lister les nœuds
        nodes = cluster.nodes()
        print(f"Nœuds connectés: {len(nodes)}")
        
        for node in nodes:
            print(f"  - {node.name}: {node.status}")
            if hasattr(node, 'avail_info'):
                print(f"    CPU: {node.avail_info.cpu_cores}, Mémoire: {node.avail_info.avail_mem}MB")
        
        cluster.close()
        return len(nodes) > 0
        
    except Exception as e:
        print(f"✗ Erreur lors de la vérification du cluster: {e}")
        return False

def check_logs():
    """Vérifie les logs système"""
    print("\n=== Vérification des logs ===")
    
    # Logs système
    log_files = [
        '/var/log/syslog',
        '/var/log/messages',
        '/var/log/kern.log'
    ]
    
    for log_file in log_files:
        if os.path.exists(log_file):
            try:
                # Chercher les erreurs récentes
                result = subprocess.run(['tail', '-n', '50', log_file], 
                                      capture_output=True, text=True, timeout=10)
                if result.returncode == 0:
                    lines = result.stdout.split('\n')
                    error_count = sum(1 for line in lines if 'error' in line.lower() or 'fail' in line.lower())
                    print(f"✓ {log_file}: {error_count} erreurs récentes")
                else:
                    print(f"? {log_file}: Impossible de lire")
            except:
                print(f"? {log_file}: Erreur de lecture")
        else:
            print(f"○ {log_file}: Non trouvé")

def main():
    print("=== Diagnostic de santé du cluster DispyCluster ===")
    print(f"Date: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
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
    
    # Vérifications locales
    check_system_resources()
    check_dispy_services()
    
    # Vérifications réseau
    if master:
        check_network_connectivity(master)
    
    for worker in workers:
        check_network_connectivity(worker)
    
    # Vérification du cluster
    cluster_ok = check_cluster_status()
    
    # Vérification des logs
    check_logs()
    
    # Résumé final
    print("\n=== Résumé du diagnostic ===")
    if cluster_ok:
        print("✓ Le cluster semble fonctionner correctement")
        return 0
    else:
        print("✗ Le cluster a des problèmes")
        return 1

if __name__ == "__main__":
    sys.exit(main())