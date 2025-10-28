#!/usr/bin/env python3
"""
Workers Dispy locaux pour DispyCluster
Démarre plusieurs workers sur la machine locale
"""

import sys
import os
import time
import dispy
import threading
from pathlib import Path

# Ajouter le répertoire du projet au PYTHONPATH
project_dir = Path(__file__).parent.parent
if str(project_dir) not in sys.path:
    sys.path.insert(0, str(project_dir))

print("=== Workers Dispy Locaux DispyCluster ===")
print(f"Version Dispy: {dispy.__version__}")
print(f"Projet: {project_dir}")
print()

def start_worker(worker_id):
    """Démarre un worker avec un ID spécifique"""
    try:
        print(f"Démarrage du worker {worker_id}...")
        dispy.start_node()
    except KeyboardInterrupt:
        print(f"Arrêt du worker {worker_id}")
    except Exception as e:
        print(f"Erreur worker {worker_id}: {e}")

def main():
    """Fonction principale pour démarrer les workers"""
    try:
        # Nombre de workers à démarrer
        num_workers = 3
        
        print(f"Démarrage de {num_workers} workers locaux...")
        
        # Démarrer les workers dans des threads séparés
        threads = []
        for i in range(num_workers):
            thread = threading.Thread(target=start_worker, args=(i+1,))
            thread.daemon = True
            thread.start()
            threads.append(thread)
            time.sleep(1)  # Pause entre les démarrages
        
        print("✓ Tous les workers sont démarrés")
        print("Workers actifs, en attente de tâches...")
        print("Appuyez sur Ctrl+C pour arrêter")
        
        # Garder les workers actifs
        while True:
            time.sleep(1)
            
    except KeyboardInterrupt:
        print("\nArrêt des workers...")
        print("✓ Workers arrêtés")
    except Exception as e:
        print(f"Erreur: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

if __name__ == "__main__":
    main()