#!/usr/bin/env python3
"""
Test de fonctionnalité des workers DispyCluster
Teste chaque type de worker (CPU, GPU, scraper, etc.) individuellement
"""

import sys
import os
import time
import yaml
from pathlib import Path

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

def test_cpu_worker(data):
    """Test du worker CPU"""
    import time
    import socket
    
    # Simulation d'un travail CPU
    result = 0
    for i in range(data * 1000):
        result += i ** 0.5
    
    return {
        'type': 'cpu',
        'input': data,
        'result': result,
        'hostname': socket.gethostname(),
        'timestamp': time.time()
    }

def test_gpu_worker(data):
    """Test du worker GPU (simulation)"""
    import time
    import socket
    
    # Simulation d'un travail GPU
    time.sleep(0.5)  # Simulation du temps de traitement GPU
    
    return {
        'type': 'gpu',
        'input': data,
        'result': data ** 2,
        'hostname': socket.gethostname(),
        'timestamp': time.time()
    }

def test_scraper_worker(url):
    """Test du worker scraper"""
    import time
    import socket
    import requests
    
    try:
        # Test de scraping simple
        response = requests.get(url, timeout=10)
        return {
            'type': 'scraper',
            'url': url,
            'status_code': response.status_code,
            'content_length': len(response.content),
            'hostname': socket.gethostname(),
            'timestamp': time.time()
        }
    except Exception as e:
        return {
            'type': 'scraper',
            'url': url,
            'error': str(e),
            'hostname': socket.gethostname(),
            'timestamp': time.time()
        }

def test_image_worker(image_data):
    """Test du worker image"""
    import time
    import socket
    
    # Simulation de traitement d'image
    time.sleep(1)
    
    return {
        'type': 'image',
        'input_size': len(str(image_data)),
        'processed': True,
        'hostname': socket.gethostname(),
        'timestamp': time.time()
    }

def test_whisper_worker(audio_data):
    """Test du worker Whisper"""
    import time
    import socket
    
    # Simulation de transcription audio
    time.sleep(2)
    
    return {
        'type': 'whisper',
        'input_size': len(str(audio_data)),
        'transcription': f"Transcription simulée de {audio_data}",
        'hostname': socket.gethostname(),
        'timestamp': time.time()
    }

def main():
    print("=== Test de fonctionnalité des workers DispyCluster ===")
    print(f"Version Dispy: {dispy.__version__}")
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
    
    # Test des différents types de workers
    worker_tests = [
        ('CPU Worker', test_cpu_worker, [10, 20, 30]),
        ('GPU Worker', test_gpu_worker, [5, 15, 25]),
        ('Scraper Worker', test_scraper_worker, ['https://httpbin.org/get', 'https://httpbin.org/json']),
        ('Image Worker', test_image_worker, ['image1.jpg', 'image2.png']),
        ('Whisper Worker', test_whisper_worker, ['audio1.wav', 'audio2.mp3'])
    ]
    
    all_tests_passed = True
    
    for test_name, test_function, test_data in worker_tests:
        print(f"Test: {test_name}")
        print("-" * 40)
        
        cluster = None
        try:
            # Créer le cluster pour ce type de worker
            cluster = dispy.JobCluster(test_function, nodes=workers)
            print(f"✓ Cluster {test_name} créé")
            
            # Attendre la connexion des nœuds
            time.sleep(3)
            
            # Vérifier les nœuds disponibles
            nodes = cluster.nodes()
            print(f"Nœuds disponibles: {len(nodes)}")
            
            if not nodes:
                print(f"✗ Aucun nœud disponible pour {test_name}")
                all_tests_passed = False
                continue
            
            # Soumettre les tâches de test
            jobs = []
            for data in test_data:
                job = cluster.submit(data)
                jobs.append(job)
                print(f"  Tâche soumise: {data}")
            
            # Attendre les résultats
            print("Attente des résultats...")
            results = []
            for i, job in enumerate(jobs):
                try:
                    result = job()
                    results.append(result)
                    print(f"  Résultat {i}: {result}")
                except Exception as e:
                    print(f"  Erreur tâche {i}: {e}")
                    all_tests_passed = False
            
            print(f"✓ {test_name} terminé avec succès")
            
        except Exception as e:
            print(f"✗ Erreur dans {test_name}: {e}")
            all_tests_passed = False
            
        finally:
            if cluster:
                cluster.close()
                print(f"Cluster {test_name} fermé")
        
        print()
    
    # Résumé final
    print("=== Résumé des tests ===")
    if all_tests_passed:
        print("✓ Tous les tests de workers sont passés avec succès!")
        return 0
    else:
        print("✗ Certains tests de workers ont échoué")
        return 1

if __name__ == "__main__":
    sys.exit(main())