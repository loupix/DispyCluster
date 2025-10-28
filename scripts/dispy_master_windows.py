#!/usr/bin/env python3
"""
Cluster Dispy maître pour DispyCluster - Version Windows
Utilise des fonctions définies dans un module séparé
"""

import sys
import os
import time
import dispy
from pathlib import Path

# Ajouter le répertoire du projet au PYTHONPATH
project_dir = Path(__file__).parent.parent
if str(project_dir) not in sys.path:
    sys.path.insert(0, str(project_dir))

# Importer les fonctions de computation
from scripts.dispy_functions import cpu_computation, scraping_computation, enhanced_computation

print("=== Cluster Dispy Maître DispyCluster (Windows) ===")
print(f"Version Dispy: {dispy.__version__}")
print(f"Projet: {project_dir}")
print()

def main():
    """Fonction principale pour démarrer le cluster"""
    try:
        print("Création du cluster Dispy...")
        
        # Déterminer le répertoire de cache Dispy
        cache_dir = os.environ.get("DISPY_CACHE_DIR")
        if not cache_dir:
            cache_dir = str(project_dir / "temp" / "dispy")
        try:
            os.makedirs(cache_dir, exist_ok=True)
        except Exception:
            pass

        # Changer temporairement de CWD pour que _dispy_* s'écrivent dans ce dossier
        cwd_before = os.getcwd()
        try:
            os.chdir(cache_dir)
            # Créer le cluster avec la fonction de computation CPU
            cluster = dispy.JobCluster(cpu_computation)
        finally:
            os.chdir(cwd_before)
        print("✓ Cluster CPU créé avec succès")
        
        # Afficher les informations du cluster
        print(f"Type de cluster: {type(cluster).__name__}")
        print("Cluster prêt à recevoir des jobs")
        
        # Garder le cluster actif
        print("\nCluster actif, en attente de tâches...")
        print("Appuyez sur Ctrl+C pour arrêter")
        
        job_count = 0
        while True:
            time.sleep(1)
            
            # Soumettre un job de test toutes les 10 secondes
            if job_count % 10 == 0:
                try:
                    job = cluster.submit({'iterations': 10000})
                    print(f"Job de test soumis (ID: {job.id})")
                except Exception as e:
                    print(f"Erreur soumission job: {e}")
            
            job_count += 1
            
    except KeyboardInterrupt:
        print("\nArrêt du cluster...")
        if 'cluster' in locals() and hasattr(cluster, 'close'):
            cluster.close()
            print("✓ Cluster fermé proprement")
    except Exception as e:
        print(f"Erreur: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

if __name__ == "__main__":
    main()