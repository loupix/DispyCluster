#!/usr/bin/env python3
"""
Monitoring des logs du cluster DispyCluster
Surveille les logs système et dispy pour détecter les problèmes
"""

import sys
import os
import time
import yaml
import signal
import subprocess
from pathlib import Path
from datetime import datetime, timedelta

# Ajouter le répertoire parent au path pour importer les modules
sys.path.append(str(Path(__file__).parent.parent.parent))

from config.dispy_config import LOCAL_IP

class LogMonitor:
    def __init__(self):
        self.running = True
        self.config = self.load_nodes_config()
        self.log_files = []
        self.error_patterns = [
            'error', 'fail', 'exception', 'timeout', 'connection refused',
            'bad source address', 'dispy', 'cluster'
        ]
        
        # Gestionnaire de signal pour arrêt propre
        signal.signal(signal.SIGINT, self.signal_handler)
        signal.signal(signal.SIGTERM, self.signal_handler)
    
    def signal_handler(self, signum, frame):
        """Gestionnaire de signal pour arrêt propre"""
        print("\nArrêt du monitoring des logs...")
        self.running = False
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
    
    def setup_log_files(self):
        """Configure les fichiers de logs à surveiller"""
        self.log_files = []
        
        # Logs système
        system_logs = [
            '/var/log/syslog',
            '/var/log/messages',
            '/var/log/kern.log',
            '/var/log/daemon.log'
        ]
        
        for log_file in system_logs:
            if os.path.exists(log_file):
                self.log_files.append({
                    'path': log_file,
                    'type': 'system',
                    'last_position': 0
                })
        
        # Logs dispy (si ils existent)
        dispy_logs = [
            '/var/log/dispy.log',
            '/tmp/dispy.log',
            'dispy.log'
        ]
        
        for log_file in dispy_logs:
            if os.path.exists(log_file):
                self.log_files.append({
                    'path': log_file,
                    'type': 'dispy',
                    'last_position': 0
                })
        
        print(f"Surveillance de {len(self.log_files)} fichiers de logs")
    
    def get_log_position(self, file_path):
        """Obtient la position actuelle dans le fichier de log"""
        try:
            with open(file_path, 'r') as f:
                f.seek(0, 2)  # Aller à la fin
                return f.tell()
        except:
            return 0
    
    def read_new_logs(self, log_info):
        """Lit les nouvelles entrées de log"""
        new_entries = []
        
        try:
            with open(log_info['path'], 'r') as f:
                f.seek(log_info['last_position'])
                new_content = f.read()
                
                if new_content:
                    lines = new_content.strip().split('\n')
                    for line in lines:
                        if line.strip():
                            new_entries.append({
                                'file': log_info['path'],
                                'type': log_info['type'],
                                'content': line.strip(),
                                'timestamp': datetime.now()
                            })
                
                # Mettre à jour la position
                log_info['last_position'] = f.tell()
                
        except Exception as e:
            print(f"Erreur lors de la lecture de {log_info['path']}: {e}")
        
        return new_entries
    
    def is_error_log(self, log_entry):
        """Détermine si une entrée de log est une erreur"""
        content_lower = log_entry['content'].lower()
        return any(pattern in content_lower for pattern in self.error_patterns)
    
    def format_log_entry(self, log_entry):
        """Formate une entrée de log pour l'affichage"""
        timestamp = log_entry['timestamp'].strftime('%H:%M:%S')
        file_name = os.path.basename(log_entry['file'])
        
        if self.is_error_log(log_entry):
            return f"🔴 {timestamp} [{file_name}] {log_entry['content']}"
        else:
            return f"ℹ️  {timestamp} [{file_name}] {log_entry['content']}"
    
    def check_remote_logs(self):
        """Vérifie les logs sur les nœuds distants"""
        if not self.config:
            return []
        
        remote_entries = []
        workers = self.config.get('workers', [])
        
        for worker in workers[:3]:  # Limiter à 3 pour éviter la surcharge
            try:
                # Vérifier les logs système distants
                cmd = f"ssh {worker} 'tail -n 10 /var/log/syslog 2>/dev/null || echo \"Logs non accessibles\"'"
                result = subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=10)
                
                if result.returncode == 0:
                    lines = result.stdout.strip().split('\n')
                    for line in lines:
                        if line.strip() and 'Logs non accessibles' not in line:
                            remote_entries.append({
                                'file': f"{worker}:/var/log/syslog",
                                'type': 'remote',
                                'content': line.strip(),
                                'timestamp': datetime.now()
                            })
                
            except Exception as e:
                remote_entries.append({
                    'file': f"{worker}:error",
                    'type': 'remote',
                    'content': f"Erreur de connexion: {e}",
                    'timestamp': datetime.now()
                })
        
        return remote_entries
    
    def display_header(self):
        """Affiche l'en-tête du monitoring"""
        print("=" * 80)
        print("MONITORING DES LOGS CLUSTER DISPYCLUSTER")
        print("=" * 80)
        print(f"Date: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"IP locale: {LOCAL_IP}")
        print("=" * 80)
    
    def display_log_summary(self, all_entries):
        """Affiche un résumé des logs"""
        print(f"\n📊 RÉSUMÉ DES LOGS")
        print("-" * 40)
        
        error_count = sum(1 for entry in all_entries if self.is_error_log(entry))
        total_count = len(all_entries)
        
        print(f"Total des entrées: {total_count}")
        print(f"Erreurs détectées: {error_count}")
        
        if error_count > 0:
            print("⚠️  Des erreurs ont été détectées!")
        else:
            print("✅ Aucune erreur détectée")
    
    def display_recent_logs(self, all_entries, max_entries=20):
        """Affiche les logs récents"""
        print(f"\n📝 LOGS RÉCENTS (dernières {max_entries} entrées)")
        print("-" * 40)
        
        # Trier par timestamp (plus récent en premier)
        sorted_entries = sorted(all_entries, key=lambda x: x['timestamp'], reverse=True)
        
        for entry in sorted_entries[:max_entries]:
            print(self.format_log_entry(entry))
    
    def display_footer(self):
        """Affiche le pied de page"""
        print("\n" + "=" * 80)
        print("Appuyez sur Ctrl+C pour arrêter le monitoring des logs")
        print("=" * 80)
    
    def run(self):
        """Lance le monitoring des logs"""
        if not self.config:
            print("Impossible de charger la configuration des nœuds")
            return 1
        
        print("Initialisation du monitoring des logs...")
        self.setup_log_files()
        
        if not self.log_files:
            print("Aucun fichier de log trouvé à surveiller")
            return 1
        
        print("Monitoring des logs démarré. Mise à jour toutes les 10 secondes...")
        time.sleep(2)
        
        all_entries = []
        
        while self.running:
            try:
                os.system('clear' if os.name == 'posix' else 'cls')
                self.display_header()
                
                # Lire les nouveaux logs locaux
                new_entries = []
                for log_info in self.log_files:
                    entries = self.read_new_logs(log_info)
                    new_entries.extend(entries)
                
                # Lire les logs distants
                remote_entries = self.check_remote_logs()
                new_entries.extend(remote_entries)
                
                # Ajouter aux entrées totales
                all_entries.extend(new_entries)
                
                # Garder seulement les 100 dernières entrées
                if len(all_entries) > 100:
                    all_entries = all_entries[-100:]
                
                # Afficher le résumé
                self.display_log_summary(all_entries)
                
                # Afficher les logs récents
                self.display_recent_logs(all_entries)
                
                self.display_footer()
                
                # Attendre avant la prochaine mise à jour
                time.sleep(10)
                
            except KeyboardInterrupt:
                break
            except Exception as e:
                print(f"Erreur lors du monitoring des logs: {e}")
                time.sleep(10)
        
        print("Monitoring des logs arrêté.")
        return 0

def main():
    monitor = LogMonitor()
    return monitor.run()

if __name__ == "__main__":
    sys.exit(main())