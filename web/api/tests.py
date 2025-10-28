"""API endpoints pour les tests en temps réel."""

from fastapi import APIRouter, HTTPException, BackgroundTasks
from typing import Dict, List, Any, Optional
from datetime import datetime
import asyncio
import subprocess
import os
import sys
from pathlib import Path

router = APIRouter(prefix="/api/tests", tags=["tests"])

# Configuration des tests
TESTS_DIR = Path(__file__).parent.parent.parent / "scripts" / "test"
TESTS_CONFIG = {
    "dispy-cluster": {
        "script": "test_dispy_cluster.py",
        "name": "Test Cluster Dispy",
        "description": "Test complet du cluster DispyCluster",
        "category": "Cluster",
        "estimated_duration": 300  # 5 minutes
    },
    "workers-functionality": {
        "script": "test_workers_functionality.py",
        "name": "Test Workers",
        "description": "Test de fonctionnalité des workers",
        "category": "Workers",
        "estimated_duration": 420  # 7 minutes
    },
    "cluster-connectivity": {
        "script": "test_cluster_connectivity.py",
        "name": "Test Connectivité",
        "description": "Test de connectivité du cluster",
        "category": "Réseau",
        "estimated_duration": 120  # 2 minutes
    },
    "dispy-api": {
        "script": "test_dispy_api_final.sh",
        "name": "Test API Dispy",
        "description": "Test de l'API Dispy",
        "category": "API",
        "estimated_duration": 180  # 3 minutes
    },
    "services": {
        "script": "test_services.sh",
        "name": "Test Services",
        "description": "Test des services du cluster",
        "category": "Services",
        "estimated_duration": 240  # 4 minutes
    }
}

# Stockage des tests en cours
running_tests = {}
test_results = []

@router.get("/available")
async def get_available_tests():
    """Liste des tests disponibles."""
    tests = []
    for test_id, test_config in TESTS_CONFIG.items():
        tests.append({
            "id": test_id,
            "script": test_config["script"],
            "name": test_config["name"],
            "description": test_config["description"],
            "category": test_config["category"],
            "estimated_duration": test_config["estimated_duration"]
        })
    
    return {
        "tests": tests,
        "total": len(tests)
    }

@router.get("/running")
async def get_running_tests():
    """Tests en cours d'exécution."""
    return {
        "running_tests": list(running_tests.values()),
        "count": len(running_tests)
    }

@router.get("/results")
async def get_test_results(limit: int = 50):
    """Résultats des tests."""
    return {
        "results": test_results[-limit:],
        "total": len(test_results)
    }

@router.post("/run/{test_id}")
async def run_test(test_id: str, background_tasks: BackgroundTasks):
    """Lancer un test spécifique."""
    if test_id not in TESTS_CONFIG:
        raise HTTPException(status_code=404, detail="Test non trouvé")
    
    if test_id in running_tests:
        raise HTTPException(status_code=400, detail="Test déjà en cours")
    
    # Créer l'entrée du test
    test_info = {
        "id": test_id,
        "name": TESTS_CONFIG[test_id]["name"],
        "start_time": datetime.now().isoformat(),
        "status": "starting",
        "progress": 0
    }
    
    running_tests[test_id] = test_info
    
    # Lancer le test en arrière-plan
    background_tasks.add_task(execute_test, test_id)
    
    return {"message": f"Test {test_id} lancé", "test_info": test_info}

@router.post("/run-all")
async def run_all_tests(background_tasks: BackgroundTasks):
    """Lancer tous les tests disponibles."""
    launched_tests = []
    
    for test_id in TESTS_CONFIG.keys():
        if test_id not in running_tests:
            test_info = {
                "id": test_id,
                "name": TESTS_CONFIG[test_id]["name"],
                "start_time": datetime.now().isoformat(),
                "status": "starting",
                "progress": 0
            }
            
            running_tests[test_id] = test_info
            background_tasks.add_task(execute_test, test_id)
            launched_tests.append(test_info)
    
    return {
        "message": f"{len(launched_tests)} tests lancés",
        "launched_tests": launched_tests
    }

@router.post("/stop/{test_id}")
async def stop_test(test_id: str):
    """Arrêter un test en cours."""
    if test_id not in running_tests:
        raise HTTPException(status_code=404, detail="Test non trouvé")
    
    # Marquer comme arrêté
    running_tests[test_id]["status"] = "stopped"
    running_tests[test_id]["end_time"] = datetime.now().isoformat()
    
    # Ajouter aux résultats
    test_results.append({
        **running_tests[test_id],
        "status": "stopped",
        "result": {"success": False, "message": "Test arrêté par l'utilisateur"}
    })
    
    # Retirer des tests en cours
    del running_tests[test_id]
    
    return {"message": f"Test {test_id} arrêté"}

@router.post("/stop-all")
async def stop_all_tests():
    """Arrêter tous les tests en cours."""
    stopped_count = len(running_tests)
    
    for test_id in list(running_tests.keys()):
        running_tests[test_id]["status"] = "stopped"
        running_tests[test_id]["end_time"] = datetime.now().isoformat()
        
        test_results.append({
            **running_tests[test_id],
            "status": "stopped",
            "result": {"success": False, "message": "Test arrêté par l'utilisateur"}
        })
    
    running_tests.clear()
    
    return {"message": f"{stopped_count} tests arrêtés"}

@router.delete("/results")
async def clear_results():
    """Nettoyer les résultats des tests."""
    global test_results
    test_results.clear()
    return {"message": "Résultats nettoyés"}

@router.get("/stats")
async def get_test_stats():
    """Statistiques des tests."""
    total_tests = len(test_results)
    passed_tests = len([r for r in test_results if r.get("status") == "passed"])
    failed_tests = len([r for r in test_results if r.get("status") == "failed"])
    running_count = len(running_tests)
    
    success_rate = (passed_tests / total_tests * 100) if total_tests > 0 else 0
    
    return {
        "total_tests": total_tests,
        "passed_tests": passed_tests,
        "failed_tests": failed_tests,
        "running_tests": running_count,
        "success_rate": round(success_rate, 1)
    }

async def execute_test(test_id: str):
    """Exécuter un test en arrière-plan."""
    test_config = TESTS_CONFIG[test_id]
    script_path = TESTS_DIR / test_config["script"]
    
    if not script_path.exists():
        # Marquer comme échoué
        running_tests[test_id]["status"] = "failed"
        running_tests[test_id]["end_time"] = datetime.now().isoformat()
        running_tests[test_id]["progress"] = 100
        
        test_results.append({
            **running_tests[test_id],
            "result": {"success": False, "message": f"Script {test_config['script']} non trouvé"}
        })
        
        del running_tests[test_id]
        return
    
    try:
        # Mettre à jour le statut
        running_tests[test_id]["status"] = "running"
        running_tests[test_id]["progress"] = 10
        
        # Exécuter le script
        if script_path.suffix == '.py':
            # Script Python
            result = subprocess.run([
                sys.executable, str(script_path)
            ], capture_output=True, text=True, timeout=600)  # 10 minutes timeout
        else:
            # Script shell
            result = subprocess.run([
                str(script_path)
            ], capture_output=True, text=True, timeout=600, shell=True)
        
        # Analyser le résultat
        success = result.returncode == 0
        
        # Mettre à jour le statut
        running_tests[test_id]["status"] = "passed" if success else "failed"
        running_tests[test_id]["end_time"] = datetime.now().isoformat()
        running_tests[test_id]["progress"] = 100
        
        # Ajouter aux résultats
        test_results.append({
            **running_tests[test_id],
            "result": {
                "success": success,
                "message": "Test terminé avec succès" if success else "Test échoué",
                "stdout": result.stdout,
                "stderr": result.stderr,
                "return_code": result.returncode
            }
        })
        
    except subprocess.TimeoutExpired:
        # Timeout
        running_tests[test_id]["status"] = "failed"
        running_tests[test_id]["end_time"] = datetime.now().isoformat()
        running_tests[test_id]["progress"] = 100
        
        test_results.append({
            **running_tests[test_id],
            "result": {"success": False, "message": "Test timeout (10 minutes)"}
        })
        
    except Exception as e:
        # Erreur d'exécution
        running_tests[test_id]["status"] = "failed"
        running_tests[test_id]["end_time"] = datetime.now().isoformat()
        running_tests[test_id]["progress"] = 100
        
        test_results.append({
            **running_tests[test_id],
            "result": {"success": False, "message": f"Erreur d'exécution: {str(e)}"}
        })
    
    finally:
        # Retirer des tests en cours
        if test_id in running_tests:
            del running_tests[test_id]

@router.get("/export")
async def export_results(format: str = "json"):
    """Exporter les résultats des tests."""
    if format == "json":
        return {
            "format": "json",
            "data": {
                "timestamp": datetime.now().isoformat(),
                "results": test_results,
                "stats": await get_test_stats()
            }
        }
    elif format == "csv":
        # Convertir en CSV
        import csv
        import io
        
        output = io.StringIO()
        writer = csv.writer(output)
        
        # En-têtes
        writer.writerow(["test_id", "name", "status", "start_time", "end_time", "success", "message"])
        
        # Données
        for result in test_results:
            writer.writerow([
                result.get("id", ""),
                result.get("name", ""),
                result.get("status", ""),
                result.get("start_time", ""),
                result.get("end_time", ""),
                result.get("result", {}).get("success", False),
                result.get("result", {}).get("message", "")
            ])
        
        return {
            "format": "csv",
            "data": output.getvalue()
        }
    else:
        raise HTTPException(status_code=400, detail="Format non supporté")