#!/usr/bin/env python3
"""
Script pour démarrer automatiquement tous les workers du cluster
"""

import sys
import os
import time
import yaml
import subprocess
from pathlib import Path

# Ajouter le répertoire parent au path pour importer les modules
sys.path.append(str(Path(__file__).parent.parent))

from config.dispy_config import LOCAL_IP

def load_nodes_config():
    """Charge la configuration des nœuds depuis nodes.yaml"""
    config_path = Path(__file__).parent.parent / "inventory" / "nodes.yaml"
    try:
        with open(config_path, 'r') as f:
            config = yaml.safe_load(f)
        return config
    except Exception as e:
        print(f"Erreur lors du chargement de la config: {e}")
        return None

def start_worker_on_node(node, username='pi'):
    """Démarre un worker sur un nœud distant"""
    print(f"Démarrage du worker sur {node}...")
    
    # Commande pour démarrer le worker
    worker_script = '''
import dispy
import sys
print(f"Démarrage du worker dispy sur {sys.platform}")
try:
    dispy.start_node()
except KeyboardInterrupt:
    print("Arrêt du worker")
'''
    
    # Commande SSH pour exécuter le script
    ssh_cmd = [
        'ssh', f'{username}@{node}',
        f'python3 -c "{worker_script}"'
    ]
    
    try:
        print(f"  Connexion SSH vers {node}...")
        process = subprocess.Popen(ssh_cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        
        # Attendre un peu pour voir si ça démarre
        time.sleep(2)
        
        if process.poll() is None:
            print(f"  ✓ Worker démarré sur {node}")
            return True
        else:
            stdout, stderr = process.communicate()
            print(f"  ✗ Erreur sur {node}: {stderr}")
            return False
            
    except Exception as e:
        print(f"  ✗ Erreur de connexion à {node}: {e}")
        return False

def main():
    print("=== Démarrage automatique des workers DispyCluster ===")
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
    
    # Demander confirmation
    print("Ce script va démarrer des workers sur tous les nœuds.")
    print("Assurez-vous que :")
    print("- SSH est configuré sur tous les nœuds")
    print("- dispy est installé sur tous les nœuds")
    print("- Vous avez les permissions SSH")
    print()
    
    confirm = input("Continuer? (y/N): ").lower()
    if confirm != 'y':
        print("Annulé.")
        return 0
    
    # Démarrer les workers
    success_count = 0
    for worker in workers:
        if start_worker_on_node(worker):
            success_count += 1
        time.sleep(1)  # Pause entre les démarrages
    
    print()
    print("=== Résumé ===")
    print(f"Workers démarrés: {success_count}/{len(workers)}")
    
    if success_count > 0:
        print("✓ Certains workers sont démarrés")
        print("Vous pouvez maintenant tester le cluster avec:")
        print("  python scripts/test/test_dispy_cluster.py")
    else:
        print("✗ Aucun worker n'a pu être démarré")
        print("Vérifiez la connectivité SSH et l'installation de dispy")
    
    return 0

if __name__ == "__main__":
    sys.exit(main())