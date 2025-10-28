#!/usr/bin/env python3
"""Script de test pour l'intégration Dispy 4.15 dans l'interface web."""

import sys
import os
import asyncio
import time
from datetime import datetime

# Ajouter le répertoire web au path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from core.cluster_manager import ClusterManager
from core.worker_registry import WorkerRegistry, WorkerStatus
from core.task_queue import TaskQueue, Task, TaskPriority
from core.dispatcher import Dispatcher
from views.cluster_view import ClusterView

def test_dispy_integration():
    """Test complet de l'intégration Dispy."""
    print("🧪 Test d'intégration Dispy 4.15")
    print("=" * 50)
    
    # Initialiser les composants
    print("1. Initialisation des composants...")
    worker_registry = WorkerRegistry()
    task_queue = TaskQueue()
    dispatcher = Dispatcher(worker_registry, task_queue)
    
    # Enregistrer des workers de test
    print("2. Enregistrement des workers...")
    test_nodes = ["node6.lan", "node7.lan", "node9.lan"]
    for node in test_nodes:
        worker_registry.register(node, ["cpu", "scraping"])
        worker_registry.set_status(node, WorkerStatus.READY)
        print(f"   ✓ Worker {node} enregistré")
    
    # Test du statut Dispy
    print("3. Test du statut Dispy...")
    dispy_status = dispatcher.get_dispy_status()
    print(f"   Statut Dispy: {dispy_status['status']}")
    print(f"   Nœuds: {dispy_status['nodes']}")
    print(f"   Jobs actifs: {dispy_status['active_jobs']}")
    
    # Test de création de tâches
    print("4. Test de création de tâches...")
    test_tasks = []
    for i in range(5):
        task = Task(
            payload={"test": f"task_{i}", "data": f"test_data_{i}"},
            requires=["cpu"],
            priority=TaskPriority.NORMAL
        )
        task_queue.push(task)
        test_tasks.append(task)
        print(f"   ✓ Tâche {task.id} créée")
    
    # Test de dispatch
    print("5. Test de dispatch des tâches...")
    dispatch_results = []
    for i in range(3):  # Tester seulement 3 tâches
        result = asyncio.run(dispatcher.dispatch_once())
        if result:
            dispatch_results.append(result)
            print(f"   ✓ Tâche dispatchée: {result['status']}")
        else:
            print("   ⚠ Aucune tâche à dispatcher")
    
    # Test des métriques
    print("6. Test des métriques...")
    stats = dispatcher.get_dispatch_stats()
    print(f"   Total dispatché: {stats['total_dispatched']}")
    print(f"   Succès: {stats['successful_dispatches']}")
    print(f"   Échecs: {stats['failed_dispatches']}")
    print(f"   Taux de succès: {stats['success_rate']:.1f}%")
    
    # Test de nettoyage
    print("7. Test de nettoyage...")
    cleaned = dispatcher.cleanup_dispy_jobs()
    print(f"   Jobs nettoyés: {cleaned}")
    
    # Test de la vue cluster
    print("8. Test de la vue cluster...")
    cluster_view = ClusterView()
    
    # Test de soumission de job
    job_data = {
        "name": "Test Job",
        "job_type": "scraping",
        "parameters": {
            "start_url": "https://example.com",
            "max_pages": 10
        },
        "priority": 2,
        "requires": ["cpu"]
    }
    
    result = asyncio.run(cluster_view.submit_job(job_data))
    print(f"   Job soumis: {result['task_id']}")
    print(f"   Statut: {result['status']}")
    print(f"   Position dans la file: {result['queue_position']}")
    
    # Test d'optimisation
    print("9. Test d'optimisation...")
    optimization_result = asyncio.run(cluster_view.optimize_cluster())
    print(f"   Tâches nettoyées: {optimization_result['cleaned_tasks']}")
    print(f"   Jobs Dispy nettoyés: {optimization_result['cleaned_dispy_jobs']}")
    print(f"   Stratégie optimale: {optimization_result['optimal_strategy']}")
    
    # Test de monitoring
    print("10. Test de monitoring...")
    overview = asyncio.run(cluster_view.get_cluster_overview())
    print(f"   Statut du cluster: {overview['status']}")
    print(f"   Nœuds en ligne: {overview['cluster_stats']['ready_nodes']}")
    print(f"   Nœuds total: {overview['cluster_stats']['total_nodes']}")
    
    # Résumé des tests
    print("\n📊 Résumé des tests:")
    print(f"   ✓ Workers enregistrés: {len(worker_registry.all_hosts())}")
    print(f"   ✓ Tâches créées: {len(test_tasks)}")
    print(f"   ✓ Tâches dispatchées: {len(dispatch_results)}")
    print(f"   ✓ Taux de succès: {stats['success_rate']:.1f}%")
    print(f"   ✓ Jobs nettoyés: {cleaned}")
    
    # Nettoyage
    print("\n🧹 Nettoyage...")
    dispatcher.shutdown_dispy_cluster()
    print("   ✓ Cluster Dispy arrêté")
    
    print("\n✅ Tests d'intégration Dispy terminés avec succès!")

def test_dispy_availability():
    """Test de la disponibilité de Dispy."""
    print("🔍 Test de disponibilité Dispy...")
    
    try:
        import dispy
        print(f"   ✓ Dispy version: {dispy.__version__}")
        return True
    except ImportError as e:
        print(f"   ❌ Dispy non disponible: {e}")
        print("   💡 Installez Dispy avec: pip install dispy==4.15.0")
        return False

def test_network_connectivity():
    """Test de connectivité réseau."""
    print("🌐 Test de connectivité réseau...")
    
    test_nodes = ["node6.lan", "node7.lan", "node9.lan"]
    import socket
    
    for node in test_nodes:
        try:
            socket.gethostbyname(node)
            print(f"   ✓ {node} résolu")
        except socket.gaierror:
            print(f"   ⚠ {node} non résolu (normal en test)")
    
    print("   ℹ️ Connectivité réseau testée")

if __name__ == "__main__":
    print("🚀 Test d'intégration DispyCluster Web Interface")
    print("=" * 60)
    
    # Tests préliminaires
    if not test_dispy_availability():
        print("\n❌ Dispy n'est pas disponible. Arrêt des tests.")
        sys.exit(1)
    
    test_network_connectivity()
    
    print("\n" + "=" * 60)
    
    # Test principal
    try:
        test_dispy_integration()
    except Exception as e:
        print(f"\n❌ Erreur lors des tests: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
    
    print("\n🎉 Tous les tests sont passés avec succès!")