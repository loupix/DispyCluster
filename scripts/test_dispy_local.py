#!/usr/bin/env python3
"""
Test du cluster Dispy DispyCluster
Teste les différentes fonctions de computation
"""

import sys
import time
import dispy
from pathlib import Path

# Ajouter le répertoire du projet au PYTHONPATH
project_dir = Path(__file__).parent.parent
if str(project_dir) not in sys.path:
    sys.path.insert(0, str(project_dir))

print("=== Test Cluster Dispy DispyCluster ===")
print(f"Version Dispy: {dispy.__version__}")
print()

def cpu_computation(data):
    """Computation CPU basée sur cpu_worker.py"""
    try:
        iterations = data.get('iterations', 100000)
        
        # Série de Leibniz pour π
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

def test_cpu_computation():
    """Test de la computation CPU"""
    print("Test computation CPU...")
    
    try:
        # Créer le cluster
        cluster = dispy.JobCluster(cpu_computation)
        print("✓ Cluster CPU créé")
        
        # Soumettre des jobs
        jobs = []
        for i in range(3):
            job = cluster.submit({'iterations': 50000})
            jobs.append(job)
            print(f"  Job {i+1} soumis")
        
        # Attendre les résultats
        results = []
        for i, job in enumerate(jobs):
            result = job()
            results.append(result)
            print(f"  Job {i+1} terminé: π ≈ {result.get('pi_approximation', 'N/A')}")
        
        # Fermer le cluster
        cluster.close()
        print("✓ Cluster fermé")
        
        return results
        
    except Exception as e:
        print(f"✗ Erreur test CPU: {e}")
        return []

def test_scraping_computation():
    """Test de la computation de scraping"""
    print("Test computation scraping...")
    
    try:
        # Fonction de scraping simple
        def scraping_computation(data):
            try:
                url = data.get('url', '')
                print(f"Scraping: {url}")
                
                # Simulation de scraping
                time.sleep(1)  # Simulation du temps de traitement
                
                return {
                    'success': True,
                    'url': url,
                    'links_found': 10,
                    'worker': 'scraper_worker'
                }
            except Exception as e:
                return {
                    'success': False,
                    'error': str(e),
                    'worker': 'scraper_worker'
                }
        
        # Créer le cluster
        cluster = dispy.JobCluster(scraping_computation)
        print("✓ Cluster scraping créé")
        
        # Soumettre des jobs de scraping
        urls = [
            'https://example.com',
            'https://httpbin.org',
            'https://jsonplaceholder.typicode.com'
        ]
        
        jobs = []
        for url in urls:
            job = cluster.submit({'url': url})
            jobs.append(job)
            print(f"  Job scraping soumis: {url}")
        
        # Attendre les résultats
        results = []
        for i, job in enumerate(jobs):
            result = job()
            results.append(result)
            print(f"  Job scraping {i+1} terminé: {result.get('links_found', 0)} liens trouvés")
        
        # Fermer le cluster
        cluster.close()
        print("✓ Cluster fermé")
        
        return results
        
    except Exception as e:
        print(f"✗ Erreur test scraping: {e}")
        return []

def main():
    """Fonction principale de test"""
    try:
        print("Démarrage des tests...")
        print()
        
        # Test computation CPU
        cpu_results = test_cpu_computation()
        print()
        
        # Test computation scraping
        scraping_results = test_scraping_computation()
        print()
        
        # Résumé
        print("=== Résumé des tests ===")
        print(f"Tests CPU réussis: {len(cpu_results)}")
        print(f"Tests scraping réussis: {len(scraping_results)}")
        
        if cpu_results and scraping_results:
            print("✓ Tous les tests sont réussis!")
            print("Le cluster Dispy fonctionne correctement")
        else:
            print("✗ Certains tests ont échoué")
        
    except Exception as e:
        print(f"Erreur lors des tests: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

if __name__ == "__main__":
    main()