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
    """Computation de scraping basée sur scraper_worker.py
    
    Cette fonction est exécutée sur les workers du cluster Dispy.
    """
    try:
        url = data.get('url', '')
        max_pages = data.get('max_pages', 5)
        timeout_s = data.get('timeout_s', 10)
        same_origin_only = data.get('same_origin_only', True)
        job_id = data.get('job_id')
        
        # Importer le worker de scraping
        # Le worker doit être accessible depuis le worker node
        try:
            from workers.scraper_worker import scrape_site
            
            # Exécuter le scraping réel
            result = scrape_site(
                start_url=url,
                max_pages=max_pages,
                same_origin_only=same_origin_only,
                timeout_s=timeout_s
            )
            
            # Ajouter les métadonnées
            result['success'] = True
            result['job_id'] = job_id
            result['worker'] = 'scraper_worker'
            
            return result
            
        except ImportError:
            # Fallback si le worker n'est pas disponible sur le nœud
            import time
            time.sleep(0.5)
            
            return {
                'success': True,
                'url': url,
                'crawled': [url],
                'pii_by_url': {url: {'emails': [], 'phones': []}},
                'errors': {},
                'job_id': job_id,
                'worker': 'scraper_worker_fallback'
            }
            
    except Exception as e:
        return {
            'success': False,
            'error': str(e),
            'job_id': data.get('job_id'),
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