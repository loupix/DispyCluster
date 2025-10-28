"""Exemples d'utilisation des nouveaux services DispyCluster.

Ce script montre comment utiliser les différents services pour
gérer le cluster et effectuer des tâches de scraping.
"""

import asyncio
import json
import time
from datetime import datetime, timedelta
from typing import List, Dict, Any

import requests
import httpx

# Configuration
API_GATEWAY_URL = "http://localhost:8084"
CLUSTER_CONTROLLER_URL = "http://localhost:8081"
MONITORING_URL = "http://localhost:8082"
SCHEDULER_URL = "http://localhost:8083"

def test_api_gateway():
    """Tester l'API Gateway."""
    print("=== Test de l'API Gateway ===")
    
    try:
        # Vérifier la santé
        response = requests.get(f"{API_GATEWAY_URL}/health")
        print(f"Statut de l'API Gateway: {response.json()}")
        
        # Vue d'ensemble du cluster
        response = requests.get(f"{API_GATEWAY_URL}/overview")
        overview = response.json()
        print(f"Vue d'ensemble du cluster: {overview['status']}")
        print(f"Services: {overview['services']}")
        
        # Tableau de bord
        response = requests.get(f"{API_GATEWAY_URL}/dashboard")
        dashboard = response.json()
        print(f"Données du tableau de bord disponibles: {len(dashboard['data'])} sections")
        
    except Exception as e:
        print(f"Erreur lors du test de l'API Gateway: {e}")

def test_cluster_controller():
    """Tester le contrôleur du cluster."""
    print("\n=== Test du contrôleur du cluster ===")
    
    try:
        # Statistiques du cluster
        response = requests.get(f"{CLUSTER_CONTROLLER_URL}/cluster")
        stats = response.json()
        print(f"Statistiques du cluster:")
        print(f"  - Workers en ligne: {stats['online_workers']}/{stats['total_workers']}")
        print(f"  - Jobs en attente: {stats['pending_jobs']}")
        print(f"  - Jobs en cours: {stats['running_jobs']}")
        
        # Ping des workers
        for node in ["node6.lan", "node7.lan", "node9.lan"]:
            try:
                response = requests.post(f"{CLUSTER_CONTROLLER_URL}/workers/{node}/ping")
                result = response.json()
                print(f"  - {node}: {result['status']}")
            except:
                print(f"  - {node}: hors ligne")
        
        # Lancer un scraping simple
        print("\nLancement d'un scraping de test...")
        response = requests.post(f"{CLUSTER_CONTROLLER_URL}/scrape", json={
            "start_url": "https://httpbin.org/html",
            "max_pages": 1,
            "same_origin_only": True,
            "timeout_s": 10,
            "priority": 1
        })
        
        if response.status_code == 200:
            result = response.json()
            print(f"Job créé: {result['job_id']}")
            
            # Attendre un peu et vérifier le statut
            time.sleep(2)
            response = requests.get(f"{CLUSTER_CONTROLLER_URL}/jobs/{result['job_id']}")
            job = response.json()
            print(f"Statut du job: {job['status']}")
        
    except Exception as e:
        print(f"Erreur lors du test du contrôleur: {e}")

def test_monitoring():
    """Tester le service de monitoring."""
    print("\n=== Test du service de monitoring ===")
    
    try:
        # Santé du cluster
        response = requests.get(f"{MONITORING_URL}/cluster/health")
        health = response.json()
        print(f"Santé du cluster: {health['overall_status']}")
        print(f"Workers en ligne: {health['nodes_online']}/{health['nodes_total']}")
        
        if health['issues']:
            print("Problèmes détectés:")
            for issue in health['issues']:
                print(f"  - {issue}")
        
        # Statut des nœuds
        response = requests.get(f"{MONITORING_URL}/nodes")
        nodes = response.json()
        print(f"\nStatut des nœuds:")
        for node in nodes[:3]:  # Afficher seulement les 3 premiers
            print(f"  - {node['node']}: {node['status']}")
            if node['status'] == 'online':
                print(f"    CPU: {node['cpu_usage']:.1f}%")
                print(f"    Mémoire: {node['memory_usage']:.1f}%")
        
        # Métriques
        response = requests.get(f"{MONITORING_URL}/metrics")
        metrics = response.json()
        print(f"\nMétriques collectées: {metrics['total_metrics_collected']}")
        
    except Exception as e:
        print(f"Erreur lors du test du monitoring: {e}")

def test_scheduler():
    """Tester le service de planification."""
    print("\n=== Test du service de planification ===")
    
    try:
        # Créer une tâche planifiée
        print("Création d'une tâche planifiée...")
        response = requests.post(f"{SCHEDULER_URL}/tasks", json={
            "name": "Test scraping quotidien",
            "urls": ["https://httpbin.org/html", "https://httpbin.org/json"],
            "max_pages": 2,
            "same_origin_only": True,
            "timeout_s": 15,
            "priority": 1,
            "schedule_type": "interval",
            "schedule_config": {"seconds": 300},  # Toutes les 5 minutes
            "description": "Tâche de test pour le scraping"
        })
        
        if response.status_code == 200:
            result = response.json()
            task_id = result['task_id']
            print(f"Tâche créée: {task_id}")
            
            # Lister les tâches
            response = requests.get(f"{SCHEDULER_URL}/tasks")
            tasks = response.json()
            print(f"Tâches planifiées: {len(tasks)}")
            
            # Exécuter la tâche immédiatement
            print("Exécution immédiate de la tâche...")
            response = requests.post(f"{SCHEDULER_URL}/tasks/{task_id}/run")
            if response.status_code == 200:
                print("Tâche lancée avec succès")
            
            # Vérifier l'historique
            time.sleep(3)
            response = requests.get(f"{SCHEDULER_URL}/history?limit=5")
            history = response.json()
            print(f"Historique des tâches: {len(history)} entrées")
        
    except Exception as e:
        print(f"Erreur lors du test du planificateur: {e}")

def test_batch_scraping():
    """Tester le scraping en lot."""
    print("\n=== Test du scraping en lot ===")
    
    try:
        # URLs de test
        test_urls = [
            "https://httpbin.org/html",
            "https://httpbin.org/json",
            "https://httpbin.org/xml",
            "https://httpbin.org/robots.txt"
        ]
        
        print(f"Lancement d'un scraping en lot sur {len(test_urls)} URLs...")
        response = requests.post(f"{CLUSTER_CONTROLLER_URL}/scrape/batch", json={
            "urls": test_urls,
            "max_pages": 1,
            "same_origin_only": True,
            "timeout_s": 10,
            "priority": 2
        })
        
        if response.status_code == 200:
            result = response.json()
            print(f"Jobs créés: {result['job_ids']}")
            
            # Surveiller les jobs
            print("Surveillance des jobs...")
            for i in range(5):
                time.sleep(2)
                response = requests.get(f"{CLUSTER_CONTROLLER_URL}/jobs")
                jobs = response.json()
                
                running_jobs = [job for job in jobs if job['status'] == 'running']
                completed_jobs = [job for job in jobs if job['status'] == 'completed']
                
                print(f"  - Jobs en cours: {len(running_jobs)}")
                print(f"  - Jobs terminés: {len(completed_jobs)}")
                
                if len(running_jobs) == 0:
                    break
        
    except Exception as e:
        print(f"Erreur lors du test du scraping en lot: {e}")

def test_workflow():
    """Tester la création d'un workflow."""
    print("\n=== Test de création d'un workflow ===")
    
    try:
        # Créer un workflow simple
        workflow_steps = [
            {
                "step_id": "step1",
                "name": "Scraping initial",
                "action": "scrape",
                "config": {
                    "urls": ["https://httpbin.org/html"],
                    "max_pages": 1
                }
            },
            {
                "step_id": "step2", 
                "name": "Attente",
                "action": "wait",
                "config": {"seconds": 5},
                "depends_on": ["step1"]
            },
            {
                "step_id": "step3",
                "name": "Scraping final",
                "action": "scrape", 
                "config": {
                    "urls": ["https://httpbin.org/json"],
                    "max_pages": 1
                },
                "depends_on": ["step2"]
            }
        ]
        
        print("Création d'un workflow...")
        response = requests.post(f"{SCHEDULER_URL}/workflows", json={
            "name": "Workflow de test",
            "description": "Workflow simple pour tester le système",
            "steps": workflow_steps,
            "schedule_type": "once",
            "schedule_config": {}
        })
        
        if response.status_code == 200:
            result = response.json()
            workflow_id = result['workflow_id']
            print(f"Workflow créé: {workflow_id}")
            
            # Exécuter le workflow
            print("Exécution du workflow...")
            response = requests.post(f"{SCHEDULER_URL}/workflows/{workflow_id}/run")
            if response.status_code == 200:
                print("Workflow lancé avec succès")
        
    except Exception as e:
        print(f"Erreur lors du test du workflow: {e}")

def test_performance_monitoring():
    """Tester le monitoring des performances."""
    print("\n=== Test du monitoring des performances ===")
    
    try:
        # Rapport de performance
        response = requests.get(f"{MONITORING_URL}/performance?hours=1")
        performance = response.json()
        
        print(f"Rapport de performance (1 heure):")
        print(f"  - Jobs totaux: {performance['total_jobs']}")
        print(f"  - Jobs réussis: {performance['successful_jobs']}")
        print(f"  - Jobs échoués: {performance['failed_jobs']}")
        print(f"  - Débit par heure: {performance['throughput_per_hour']:.1f}")
        
        if performance['top_performing_nodes']:
            print("  - Meilleurs nœuds:")
            for node in performance['top_performing_nodes']:
                print(f"    * {node['node']}: {node['pages_scraped']} pages")
        
        # Alertes
        response = requests.get(f"{MONITORING_URL}/alerts")
        alerts = response.json()
        print(f"\nAlertes actives: {alerts['alert_count']}")
        
    except Exception as e:
        print(f"Erreur lors du test du monitoring des performances: {e}")

def main():
    """Fonction principale pour exécuter tous les tests."""
    print("=== Tests des services DispyCluster ===")
    print(f"Timestamp: {datetime.now().isoformat()}")
    print()
    
    # Tests des services
    test_api_gateway()
    test_cluster_controller()
    test_monitoring()
    test_scheduler()
    test_batch_scraping()
    test_workflow()
    test_performance_monitoring()
    
    print("\n=== Tests terminés ===")
    print("Pour plus d'informations, consultez les logs des services:")
    print("  journalctl -u dispycluster-controller -f")
    print("  journalctl -u dispycluster-monitoring -f")
    print("  journalctl -u dispycluster-scheduler -f")
    print("  journalctl -u dispycluster-gateway -f")

if __name__ == "__main__":
    main()