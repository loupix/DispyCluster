"""
Fonctions de computation pour DispyCluster
Définies dans un module séparé pour éviter les problèmes d'inspection sur Windows
"""

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

def scraping_computation(data):
    """Computation de scraping basée sur scraper_worker.py"""
    try:
        url = data.get('url', '')
        max_pages = data.get('max_pages', 5)
        timeout_s = data.get('timeout_s', 10)
        
        # Simulation de scraping pour éviter les dépendances externes
        import time
        time.sleep(0.5)  # Simulation du temps de traitement
        
        return {
            'success': True,
            'url': url,
            'links_found': 15,
            'pages_scraped': max_pages,
            'worker': 'scraper_worker'
        }
    except Exception as e:
        return {
            'success': False,
            'error': str(e),
            'worker': 'scraper_worker'
        }

def enhanced_computation(data):
    """Computation avancée"""
    try:
        task_type = data.get('type', 'default')
        
        # Simulation de différents types de tâches
        import time
        time.sleep(0.3)
        
        return {
            'success': True,
            'task_type': task_type,
            'result': f'Tâche {task_type} terminée',
            'worker': 'enhanced_worker'
        }
    except Exception as e:
        return {
            'success': False,
            'error': str(e),
            'worker': 'enhanced_worker'
        }