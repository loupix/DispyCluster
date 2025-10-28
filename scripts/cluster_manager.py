#!/usr/bin/env python3
"""
Gestionnaire principal du cluster DispyCluster
Interface unifiée pour tous les scripts de test, diagnostic, monitoring et réseau
"""

import sys
import os
import subprocess
from pathlib import Path

# Ajouter le répertoire parent au path pour importer les modules
sys.path.append(str(Path(__file__).parent.parent))

from config.dispy_config import LOCAL_IP

class ClusterManager:
    def __init__(self):
        self.script_dir = Path(__file__).parent
        self.project_root = self.script_dir.parent
        
    def show_menu(self):
        """Affiche le menu principal"""
        print("=" * 60)
        print("GESTIONNAIRE DU CLUSTER DISPYCLUSTER")
        print("=" * 60)
        print(f"IP locale: {LOCAL_IP}")
        print()
        print("1. Tests du cluster")
        print("2. Diagnostics")
        print("3. Monitoring")
        print("4. Configuration réseau")
        print("5. Quitter")
        print()
    
    def show_test_menu(self):
        """Affiche le menu des tests"""
        print("\n=== TESTS DU CLUSTER ===")
        print("1. Test de connectivité")
        print("2. Test complet du cluster")
        print("3. Test des workers")
        print("4. Retour au menu principal")
        print()
    
    def show_diagnostic_menu(self):
        """Affiche le menu des diagnostics"""
        print("\n=== DIAGNOSTICS ===")
        print("1. Diagnostic de santé du cluster")
        print("2. Diagnostic de performance des nœuds")
        print("3. Retour au menu principal")
        print()
    
    def show_monitoring_menu(self):
        """Affiche le menu du monitoring"""
        print("\n=== MONITORING ===")
        print("1. Monitoring temps réel")
        print("2. Monitoring des logs")
        print("3. Retour au menu principal")
        print()
    
    def show_network_menu(self):
        """Affiche le menu de configuration réseau"""
        print("\n=== CONFIGURATION RÉSEAU ===")
        print("1. Configuration réseau du cluster")
        print("2. Test de connectivité réseau")
        print("3. Optimisation réseau")
        print("4. Retour au menu principal")
        print()
    
    def run_script(self, script_path, args=None):
        """Exécute un script"""
        try:
            if script_path.suffix == '.py':
                cmd = [sys.executable, str(script_path)]
            else:
                cmd = [str(script_path)]
            
            if args:
                cmd.extend(args)
            
            print(f"Exécution de: {' '.join(cmd)}")
            print("-" * 40)
            
            result = subprocess.run(cmd, cwd=self.project_root)
            return result.returncode == 0
            
        except Exception as e:
            print(f"Erreur lors de l'exécution: {e}")
            return False
    
    def handle_test_menu(self):
        """Gère le menu des tests"""
        while True:
            self.show_test_menu()
            choice = input("Choix: ").strip()
            
            if choice == '1':
                script = self.script_dir / "test" / "test_cluster_connectivity.py"
                self.run_script(script)
            elif choice == '2':
                script = self.script_dir / "test" / "test_dispy_cluster.py"
                self.run_script(script)
            elif choice == '3':
                script = self.script_dir / "test" / "test_workers_functionality.py"
                self.run_script(script)
            elif choice == '4':
                break
            else:
                print("Choix invalide")
            
            input("\nAppuyez sur Entrée pour continuer...")
    
    def handle_diagnostic_menu(self):
        """Gère le menu des diagnostics"""
        while True:
            self.show_diagnostic_menu()
            choice = input("Choix: ").strip()
            
            if choice == '1':
                script = self.script_dir / "diagnostic" / "diagnose_cluster_health.py"
                self.run_script(script)
            elif choice == '2':
                script = self.script_dir / "diagnostic" / "diagnose_node_performance.py"
                self.run_script(script)
            elif choice == '3':
                break
            else:
                print("Choix invalide")
            
            input("\nAppuyez sur Entrée pour continuer...")
    
    def handle_monitoring_menu(self):
        """Gère le menu du monitoring"""
        while True:
            self.show_monitoring_menu()
            choice = input("Choix: ").strip()
            
            if choice == '1':
                script = self.script_dir / "monitoring" / "monitor_cluster_realtime.py"
                self.run_script(script)
            elif choice == '2':
                script = self.script_dir / "monitoring" / "monitor_cluster_logs.py"
                self.run_script(script)
            elif choice == '3':
                break
            else:
                print("Choix invalide")
            
            input("\nAppuyez sur Entrée pour continuer...")
    
    def handle_network_menu(self):
        """Gère le menu de configuration réseau"""
        while True:
            self.show_network_menu()
            choice = input("Choix: ").strip()
            
            if choice == '1':
                script = self.script_dir / "network" / "configure_cluster_network.sh"
                print("Note: Ce script nécessite des privilèges root")
                if input("Continuer? (y/N): ").lower() == 'y':
                    self.run_script(script)
            elif choice == '2':
                script = self.script_dir / "network" / "test_cluster_network.py"
                self.run_script(script)
            elif choice == '3':
                script = self.script_dir / "network" / "optimize_cluster_network.sh"
                print("Note: Ce script nécessite des privilèges root")
                if input("Continuer? (y/N): ").lower() == 'y':
                    self.run_script(script)
            elif choice == '4':
                break
            else:
                print("Choix invalide")
            
            input("\nAppuyez sur Entrée pour continuer...")
    
    def run(self):
        """Lance le gestionnaire principal"""
        while True:
            self.show_menu()
            choice = input("Choix: ").strip()
            
            if choice == '1':
                self.handle_test_menu()
            elif choice == '2':
                self.handle_diagnostic_menu()
            elif choice == '3':
                self.handle_monitoring_menu()
            elif choice == '4':
                self.handle_network_menu()
            elif choice == '5':
                print("Au revoir!")
                break
            else:
                print("Choix invalide")
                input("\nAppuyez sur Entrée pour continuer...")

def main():
    manager = ClusterManager()
    manager.run()

if __name__ == "__main__":
    main()