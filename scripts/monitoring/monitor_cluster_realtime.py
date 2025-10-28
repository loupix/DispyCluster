#!/usr/bin/env python3
"""
Monitoring en temps réel du cluster DispyCluster
Affiche l'état du cluster en continu avec mise à jour automatique
"""

import sys
import os
import time
import yaml
import signal
from pathlib import Path
from datetime import datetime

# Ajouter le répertoire parent au path pour importer les modules
sys.path.append(str(Path(__file__).parent.parent.parent))

import dispy
from config.dispy_config import LOCAL_IP

class ClusterMonitor:
    def __init__(self):
        self.running = True
        self.config = self.load_nodes_config()
        self.cluster = None
        
        # Gestionnaire de signal pour arrêt propre
        signal.signal(signal.SIGINT, self.signal_handler)
        signal.signal(signal.SIGTERM, self.signal_handler)
    
    def signal_handler(self, signum, frame):
        """Gestionnaire de signal pour arrêt propre"""
        print("\nArrêt du monitoring...")
        self.running = False
        if self.cluster:
            self.cluster.close()
        sys.exit(0)
    
    def load_nodes_config(self):
        """Charge la configuration des nœuds depuis nodes.yaml"""
        config_path = Path(__file__).parent.parent.parent / "inventory" / "nodes.yaml"
        try:
            with open(config_path, 'r') as f:
                config = yaml.safe_load(f)
            return config
        except Exception as e:
            print(f"Erreur lors du chargement de la config: {e}")
            return None
    
    def clear_screen(self):
        """Efface l'écran"""
        os.system('clear' if os.name == 'posix' else 'cls')
    
    def get_system_info(self):
        """Obtient les informations système locales"""
        try:
            import psutil
            
            cpu_percent = psutil.cpu_percent(interval=0.1)
            memory = psutil.virtual_memory()
            disk = psutil.disk_usage('/')
            
            return {
                'cpu_percent': cpu_percent,
                'memory_percent': memory.percent,
                'memory_used': memory.used // (1024**3),
                'memory_total': memory.total // (1024**3),
                'disk_percent': disk.percent,
                'disk_used': disk.used // (1024**3),
                'disk_total': disk.total // (1024**3)
            }
        except ImportError:
            return None
    
    def get_cluster_status(self):
        """Obtient le statut du cluster"""
        if not self.cluster:
            return None
        
        try:
            status = self.cluster.status()
            nodes = self.cluster.nodes()
            
            return {
                'status': status,
                'nodes': nodes,
                'node_count': len(nodes)
            }
        except Exception as e:
            return {'error': str(e)}
    
    def display_header(self):
        """Affiche l'en-tête du monitoring"""
        print("=" * 80)
        print("MONITORING CLUSTER DISPYCLUSTER - TEMPS RÉEL")
        print("=" * 80)
        print(f"Date: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"IP locale: {LOCAL_IP}")
        print("=" * 80)
    
    def display_system_info(self, sys_info):
        """Affiche les informations système"""
        print("\n📊 SYSTÈME LOCAL")
        print("-" * 40)
        
        if sys_info:
            print(f"CPU: {sys_info['cpu_percent']:5.1f}%")
            print(f"Mémoire: {sys_info['memory_percent']:5.1f}% ({sys_info['memory_used']}GB / {sys_info['memory_total']}GB)")
            print(f"Disque: {sys_info['disk_percent']:5.1f}% ({sys_info['disk_used']}GB / {sys_info['disk_total']}GB)")
        else:
            print("Informations système non disponibles")
    
    def display_cluster_info(self, cluster_status):
        """Affiche les informations du cluster"""
        print("\n🖥️  CLUSTER DISPY")
        print("-" * 40)
        
        if cluster_status and 'error' not in cluster_status:
            print(f"Statut: {cluster_status['status']}")
            print(f"Nœuds connectés: {cluster_status['node_count']}")
            
            if cluster_status['nodes']:
                print("\nNœuds:")
                for node in cluster_status['nodes']:
                    status_icon = "🟢" if node.status == "Available" else "🔴"
                    print(f"  {status_icon} {node.name}: {node.status}")
                    
                    if hasattr(node, 'avail_info'):
                        print(f"    CPU: {node.avail_info.cpu_cores} cœurs")
                        print(f"    Mémoire: {node.avail_info.avail_mem}MB")
        else:
            if cluster_status and 'error' in cluster_status:
                print(f"❌ Erreur: {cluster_status['error']}")
            else:
                print("❌ Cluster non disponible")
    
    def display_network_info(self):
        """Affiche les informations réseau"""
        print("\n🌐 RÉSEAU")
        print("-" * 40)
        
        if self.config:
            workers = self.config.get('workers', [])
            master = self.config.get('master', '')
            
            print(f"Master: {master}")
            print(f"Workers: {len(workers)}")
            
            # Test de connectivité rapide
            for worker in workers[:3]:  # Limiter à 3 pour éviter la surcharge
                try:
                    import subprocess
                    result = subprocess.run(['ping', '-c', '1', '-W', '1', worker], 
                                          capture_output=True, text=True, timeout=3)
                    status = "🟢" if result.returncode == 0 else "🔴"
                    print(f"  {status} {worker}")
                except:
                    print(f"  ❓ {worker}")
            
            if len(workers) > 3:
                print(f"  ... et {len(workers) - 3} autres")
    
    def display_footer(self):
        """Affiche le pied de page"""
        print("\n" + "=" * 80)
        print("Appuyez sur Ctrl+C pour arrêter le monitoring")
        print("=" * 80)
    
    def run(self):
        """Lance le monitoring en temps réel"""
        if not self.config:
            print("Impossible de charger la configuration des nœuds")
            return 1
        
        print("Initialisation du monitoring...")
        
        # Créer un cluster de test pour le monitoring
        def monitor_func():
            import time
            import socket
            return {
                'hostname': socket.gethostname(),
                'timestamp': time.time()
            }
        
        try:
            self.cluster = dispy.JobCluster(monitor_func, nodes=self.config.get('workers', []))
            time.sleep(3)  # Attendre la connexion des nœuds
        except Exception as e:
            print(f"Erreur lors de la création du cluster: {e}")
            return 1
        
        print("Monitoring démarré. Mise à jour toutes les 5 secondes...")
        time.sleep(2)
        
        while self.running:
            try:
                self.clear_screen()
                self.display_header()
                
                # Informations système
                sys_info = self.get_system_info()
                self.display_system_info(sys_info)
                
                # Informations cluster
                cluster_status = self.get_cluster_status()
                self.display_cluster_info(cluster_status)
                
                # Informations réseau
                self.display_network_info()
                
                self.display_footer()
                
                # Attendre avant la prochaine mise à jour
                time.sleep(5)
                
            except KeyboardInterrupt:
                break
            except Exception as e:
                print(f"Erreur lors du monitoring: {e}")
                time.sleep(5)
        
        # Nettoyage
        if self.cluster:
            self.cluster.close()
        
        print("Monitoring arrêté.")
        return 0

def main():
    monitor = ClusterMonitor()
    return monitor.run()

if __name__ == "__main__":
    sys.exit(main())