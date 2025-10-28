#!/usr/bin/env python3
"""
Test complet du cluster DispyCluster
Teste la création, la distribution de tâches et la récupération des résultats
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

def test_computation(data):
    """Fonction de test pour le cluster"""
    import time
    import socket
    
    # Simulation d'un travail
    time.sleep(1)
    
    # Informations sur le nœud qui exécute
    hostname = socket.gethostname()
    
    return {
        'input': data,
        'result': data * 2,
        'hostname': hostname,
        'timestamp': time.time()
    }

def test_cpu_intensive(data):
    """Fonction de test CPU intensive"""
    import time
    
    # Simulation d'un calcul CPU intensif
    result = 0
    for i in range(data * 1000):
        result += i ** 0.5
    
    return {
        'input': data,
        'result': result,
        'computation_time': time.time()
    }

def main():
    print("=== Test complet du cluster DispyCluster ===")
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
    
    cluster = None
    try:
        # Test 1: Création du cluster
        print("Test 1: Création du cluster...")
        cluster = dispy.JobCluster(test_computation, nodes=workers)
        print("✓ Cluster créé avec succès")
        
        # Attendre que les nœuds se connectent
        print("Attente de la connexion des nœuds...")
        time.sleep(5)
        
        # Vérifier le statut
        status = cluster.status()
        print(f"Statut du cluster: {status}")
        
        # Afficher le statut détaillé du cluster
        print("Statut détaillé du cluster:")
        cluster.print_status()
        
        # Vérifier le statut pour voir s'il y a des nœuds
        if hasattr(status, 'nodes') and status.nodes:
            print(f"Nœuds connectés: {len(status.nodes)}")
        else:
            print("Aucun nœud connecté pour le moment")
        
        print()
        
        # Test 2: Distribution de tâches simples
        print("Test 2: Distribution de tâches simples...")
        jobs = []
        
        for i in range(5):
            job = cluster.submit(i)
            jobs.append(job)
            print(f"  Tâche {i} soumise")
        
        # Attendre les résultats
        print("Attente des résultats...")
        results = []
        for i, job in enumerate(jobs):
            result = job()
            results.append(result)
            print(f"  Tâche {i}: {result}")
        
        print("✓ Tâches simples terminées")
        print()
        
        # Test 3: Tâches CPU intensives
        print("Test 3: Tâches CPU intensives...")
        
        # Créer un nouveau cluster pour les tâches CPU intensives
        cluster.close()
        cluster = dispy.JobCluster(test_cpu_intensive, nodes=workers)
        time.sleep(3)
        
        cpu_jobs = []
        for i in range(3):
            job = cluster.submit(i + 10)
            cpu_jobs.append(job)
            print(f"  Tâche CPU {i} soumise")
        
        # Attendre les résultats
        print("Attente des résultats CPU...")
        cpu_results = []
        for i, job in enumerate(cpu_jobs):
            result = job()
            cpu_results.append(result)
            print(f"  Tâche CPU {i}: {result}")
        
        print("✓ Tâches CPU intensives terminées")
        print()
        
        # Test 4: Test de charge
        print("Test 4: Test de charge...")
        load_jobs = []
        
        for i in range(10):
            job = cluster.submit(i + 100)
            load_jobs.append(job)
        
        print(f"10 tâches de charge soumises")
        
        # Attendre tous les résultats
        load_results = []
        for i, job in enumerate(load_jobs):
            result = job()
            load_results.append(result)
            print(f"  Tâche de charge {i}: terminée")
        
        print("✓ Test de charge terminé")
        print()
        
        # Statistiques finales
        print("=== Statistiques finales ===")
        final_status = cluster.status()
        print(f"Statut final: {final_status}")
        
        # Afficher le statut final
        print("Statut final détaillé:")
        cluster.print_status()
        
        print("✓ Tous les tests sont passés avec succès!")
        return 0
        
    except Exception as e:
        print(f"✗ Erreur lors des tests: {e}")
        import traceback
        traceback.print_exc()
        return 1
        
    finally:
        if cluster:
            cluster.close()
            print("Cluster fermé proprement")

if __name__ == "__main__":
    sys.exit(main())