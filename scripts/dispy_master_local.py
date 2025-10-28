#!/usr/bin/env python3
"""
Cluster Dispy maître pour DispyCluster
Version adaptée pour Windows avec workers locaux
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

print("=== Cluster Dispy Maître DispyCluster ===")
print(f"Version Dispy: {dispy.__version__}")
print(f"Projet: {project_dir}")
print()

# Fonction de computation basée sur les workers existants
def cpu_computation(data):
    """Computation CPU basée sur cpu_worker.py"""
    try:
        iterations = data.get('iterations', 100000)
        print(f"Calcul π avec {iterations} itérations...")
        
        # Série de Leibniz pour π (comme dans cpu_worker.py)
        acc = 0.0
        for k in range(iterations):
            acc += ((-1) ** k) / (2 * k + 1)
        pi_approx = 4 * acc
        
        return {
            'success': True,
            'pi_approximation': pi_approx,
            'iterations': iterations,
            'worker': 'cpu_worker'
        }
    except Exception as e:
        return {
            'success': False,
            'error': str(e),
            'worker': 'cpu_worker'
        }

def scraping_computation(data):
    """Computation de scraping basée sur scraper_worker.py"""
    try:
        url = data.get('url', '')
        max_pages = data.get('max_pages', 5)
        timeout_s = data.get('timeout_s', 10)
        
        print(f"Scraping: {url}")
        
        # Import des fonctions de scraping
        from workers.scraper_worker import scrape_site
        
        result = scrape_site(
            start_url=url,
            max_pages=max_pages,
            same_origin_only=True,
            timeout_s=timeout_s
        )
        
        return {
            'success': True,
            'result': result,
            'worker': 'scraper_worker'
        }
    except Exception as e:
        return {
            'success': False,
            'error': str(e),
            'worker': 'scraper_worker'
        }

def enhanced_scraping_computation(data):
    """Computation de scraping avancée"""
    try:
        url = data.get('url', '')
        print(f"Scraping avancé: {url}")
        
        # Import des fonctions de scraping avancées
        from workers.enhanced_scraper_worker import enhanced_scrape
        
        result = enhanced_scrape(url)
        
        return {
            'success': True,
            'result': result,
            'worker': 'enhanced_scraper_worker'
        }
    except Exception as e:
        return {
            'success': False,
            'error': str(e),
            'worker': 'enhanced_scraper_worker'
        }

def main():
    """Fonction principale pour démarrer le cluster"""
    try:
        print("Création du cluster Dispy...")
        
        # Créer le cluster avec la fonction de computation par défaut
        cluster = dispy.JobCluster(cpu_computation)
        print("✓ Cluster CPU créé avec succès")
        
        # Afficher les informations du cluster
        print(f"Type de cluster: {type(cluster).__name__}")
        print("Cluster prêt à recevoir des jobs")
        
        # Garder le cluster actif
        print("\nCluster actif, en attente de tâches...")
        print("Appuyez sur Ctrl+C pour arrêter")
        
        while True:
            time.sleep(1)
            
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