#!/usr/bin/env python3
"""
Diagnostic de performance des nœuds du cluster
Mesure les performances de chaque nœud individuellement
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

def cpu_benchmark():
    """Benchmark CPU simple"""
    import time
    import math
    
    start_time = time.time()
    
    # Calcul intensif
    result = 0
    for i in range(1000000):
        result += math.sqrt(i)
    
    end_time = time.time()
    return end_time - start_time

def memory_benchmark():
    """Benchmark mémoire"""
    import time
    
    start_time = time.time()
    
    # Allocation de mémoire
    data = []
    for i in range(100000):
        data.append([0] * 100)
    
    # Libération
    del data
    
    end_time = time.time()
    return end_time - start_time

def network_benchmark():
    """Benchmark réseau local"""
    import time
    import socket
    
    start_time = time.time()
    
    # Test de connexion locale
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
            sock.settimeout(5)
            sock.connect(('localhost', 22))  # SSH port
    except:
        pass  # Ignorer les erreurs de connexion
    
    end_time = time.time()
    return end_time - start_time

def disk_benchmark():
    """Benchmark disque"""
    import time
    import tempfile
    
    start_time = time.time()
    
    # Test d'écriture
    with tempfile.NamedTemporaryFile(delete=False) as f:
        data = b'0' * 1024 * 1024  # 1MB
        f.write(data)
        temp_file = f.name
    
    # Test de lecture
    with open(temp_file, 'rb') as f:
        f.read()
    
    # Nettoyage
    os.unlink(temp_file)
    
    end_time = time.time()
    return end_time - start_time

def get_system_info():
    """Obtient les informations système"""
    info = {
        'hostname': socket.gethostname(),
        'cpu_count': 0,
        'memory_total': 0,
        'disk_total': 0
    }
    
    try:
        import psutil
        info['cpu_count'] = psutil.cpu_count()
        info['memory_total'] = psutil.virtual_memory().total
        info['disk_total'] = psutil.disk_usage('/').total
    except ImportError:
        # Fallback avec des commandes système
        try:
            result = subprocess.run(['nproc'], capture_output=True, text=True)
            if result.returncode == 0:
                info['cpu_count'] = int(result.stdout.strip())
        except:
            pass
        
        try:
            result = subprocess.run(['free', '-b'], capture_output=True, text=True)
            if result.returncode == 0:
                lines = result.stdout.split('\n')
                if len(lines) > 1:
                    parts = lines[1].split()
                    if len(parts) > 1:
                        info['memory_total'] = int(parts[1])
        except:
            pass
    
    return info

def test_node_performance(node_name):
    """Teste les performances d'un nœud spécifique"""
    print(f"\n=== Test de performance: {node_name} ===")
    
    # Fonction de test à exécuter sur le nœud
    def performance_test():
        import time
        import socket
        
        results = {
            'hostname': socket.gethostname(),
            'timestamp': time.time(),
            'cpu_time': 0,
            'memory_time': 0,
            'network_time': 0,
            'disk_time': 0,
            'system_info': {}
        }
        
        try:
            # Benchmark CPU
            start = time.time()
            result = 0
            for i in range(500000):  # Réduit pour éviter les timeouts
                result += i ** 0.5
            results['cpu_time'] = time.time() - start
            
            # Benchmark mémoire
            start = time.time()
            data = []
            for i in range(50000):
                data.append([0] * 50)
            del data
            results['memory_time'] = time.time() - start
            
            # Benchmark réseau
            start = time.time()
            try:
                with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
                    sock.settimeout(2)
                    sock.connect(('localhost', 22))
            except:
                pass
            results['network_time'] = time.time() - start
            
            # Benchmark disque
            start = time.time()
            import tempfile
            with tempfile.NamedTemporaryFile(delete=False) as f:
                f.write(b'0' * 1024 * 512)  # 512KB
                temp_file = f.name
            with open(temp_file, 'rb') as f:
                f.read()
            os.unlink(temp_file)
            results['disk_time'] = time.time() - start
            
            # Informations système
            try:
                import psutil
                results['system_info'] = {
                    'cpu_count': psutil.cpu_count(),
                    'memory_total': psutil.virtual_memory().total,
                    'disk_total': psutil.disk_usage('/').total
                }
            except:
                results['system_info'] = {'error': 'psutil non disponible'}
            
        except Exception as e:
            results['error'] = str(e)
        
        return results
    
    try:
        # Créer un cluster pour ce nœud spécifique
        cluster = dispy.JobCluster(performance_test, nodes=[node_name])
        time.sleep(3)  # Attendre la connexion
        
        # Vérifier que le nœud est connecté
        nodes = cluster.nodes()
        if not nodes:
            print(f"✗ Nœud {node_name} non connecté")
            cluster.close()
            return None
        
        # Soumettre le test de performance
        job = cluster.submit()
        result = job()
        
        if 'error' in result:
            print(f"✗ Erreur sur {node_name}: {result['error']}")
        else:
            print(f"✓ Test terminé sur {node_name}")
            print(f"  Hostname: {result['hostname']}")
            print(f"  CPU: {result['cpu_time']:.3f}s")
            print(f"  Mémoire: {result['memory_time']:.3f}s")
            print(f"  Réseau: {result['network_time']:.3f}s")
            print(f"  Disque: {result['disk_time']:.3f}s")
            
            if 'system_info' in result and 'error' not in result['system_info']:
                sys_info = result['system_info']
                print(f"  CPU cores: {sys_info.get('cpu_count', 'N/A')}")
                print(f"  Mémoire totale: {sys_info.get('memory_total', 0) // (1024**3)}GB")
                print(f"  Disque total: {sys_info.get('disk_total', 0) // (1024**3)}GB")
        
        cluster.close()
        return result
        
    except Exception as e:
        print(f"✗ Erreur lors du test de {node_name}: {e}")
        return None

def main():
    print("=== Diagnostic de performance des nœuds DispyCluster ===")
    print(f"Date: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"IP locale: {LOCAL_IP}")
    print()
    
    # Charger la configuration
    config = load_nodes_config()
    if not config:
        print("Impossible de charger la configuration des nœuds")
        return 1
    
    workers = config.get('workers', [])
    print(f"Nœuds workers: {workers}")
    print()
    
    # Test de performance local
    print("=== Test de performance local ===")
    local_info = get_system_info()
    print(f"Hostname: {local_info['hostname']}")
    print(f"CPU cores: {local_info['cpu_count']}")
    print(f"Mémoire: {local_info['memory_total'] // (1024**3)}GB")
    print(f"Disque: {local_info['disk_total'] // (1024**3)}GB")
    
    # Tests de performance locaux
    print("\nBenchmarks locaux:")
    cpu_time = cpu_benchmark()
    memory_time = memory_benchmark()
    network_time = network_benchmark()
    disk_time = disk_benchmark()
    
    print(f"  CPU: {cpu_time:.3f}s")
    print(f"  Mémoire: {memory_time:.3f}s")
    print(f"  Réseau: {network_time:.3f}s")
    print(f"  Disque: {disk_time:.3f}s")
    
    # Tests de performance des nœuds distants
    print("\n=== Tests de performance des nœuds distants ===")
    results = {}
    
    for worker in workers:
        result = test_node_performance(worker)
        if result:
            results[worker] = result
    
    # Résumé comparatif
    print("\n=== Résumé comparatif ===")
    if results:
        print("Nœud\t\tCPU\tMémoire\tRéseau\tDisque")
        print("-" * 50)
        
        # Local
        print(f"Local\t\t{cpu_time:.3f}\t{memory_time:.3f}\t{network_time:.3f}\t{disk_time:.3f}")
        
        # Nœuds distants
        for node, result in results.items():
            if 'error' not in result:
                print(f"{node}\t\t{result['cpu_time']:.3f}\t{result['memory_time']:.3f}\t{result['network_time']:.3f}\t{result['disk_time']:.3f}")
            else:
                print(f"{node}\t\tErreur")
    
    print("\n✓ Diagnostic de performance terminé")
    return 0

if __name__ == "__main__":
    sys.exit(main())