#!/usr/bin/env python3
"""
Test de connectivité réseau du cluster DispyCluster
Teste la connectivité entre tous les nœuds du cluster
"""

import sys
import os
import time
import yaml
import socket
import subprocess
from pathlib import Path
from datetime import datetime

# Ajouter le répertoire parent au path pour importer les modules
sys.path.append(str(Path(__file__).parent.parent.parent))

from config.dispy_config import LOCAL_IP

def load_nodes_config():
    """Charge la configuration des nœuds depuis nodes.yaml"""
    config_path = Path(__file__).parent.parent.parent / "inventory" / "nodes.yaml"
    try:
        with open(config_path, 'r') as f:
            config = yaml.safe_load(f)
        return config
    except Exception as e:
        print(f"Erreur lors du chargement de la config: {e}")
        return None

def test_ping(host, count=3, timeout=5):
    """Test de ping vers un hôte"""
    try:
        cmd = ['ping', '-c', str(count), '-W', str(timeout), host]
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout+2)
        
        if result.returncode == 0:
            # Extraire les statistiques
            lines = result.stdout.split('\n')
            stats = {}
            
            for line in lines:
                if 'packets transmitted' in line:
                    parts = line.split(',')
                    stats['transmitted'] = int(parts[0].split()[0])
                    stats['received'] = int(parts[1].split()[0])
                    stats['loss'] = float(parts[2].split()[0].replace('%', ''))
                elif 'rtt min/avg/max' in line:
                    rtt_part = line.split('=')[1].strip()
                    rtt_values = rtt_part.split('/')
                    stats['rtt_min'] = float(rtt_values[0])
                    stats['rtt_avg'] = float(rtt_values[1])
                    stats['rtt_max'] = float(rtt_values[2])
            
            return {'success': True, 'stats': stats}
        else:
            return {'success': False, 'error': 'Ping failed'}
            
    except subprocess.TimeoutExpired:
        return {'success': False, 'error': 'Timeout'}
    except Exception as e:
        return {'success': False, 'error': str(e)}

def test_port(host, port, timeout=5):
    """Test de connectivité sur un port spécifique"""
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
            sock.settimeout(timeout)
            start_time = time.time()
            result = sock.connect_ex((host, port))
            end_time = time.time()
            
            return {
                'success': result == 0,
                'response_time': end_time - start_time,
                'error': None if result == 0 else f'Connection failed with code {result}'
            }
    except Exception as e:
        return {'success': False, 'error': str(e), 'response_time': None}

def test_dispy_ports(host):
    """Test des ports spécifiques à dispy (ports par défaut)"""
    ports = {
        'Scheduler': 9700,
        'Node': 9701
    }
    
    results = {}
    for service, port in ports.items():
        results[service] = test_port(host, port)
    
    return results

def test_ssh_connectivity(host):
    """Test de connectivité SSH"""
    try:
        cmd = ['ssh', '-o', 'ConnectTimeout=5', '-o', 'BatchMode=yes', host, 'echo "SSH OK"']
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=10)
        
        return {
            'success': result.returncode == 0,
            'output': result.stdout.strip() if result.returncode == 0 else result.stderr.strip(),
            'error': None if result.returncode == 0 else 'SSH connection failed'
        }
    except subprocess.TimeoutExpired:
        return {'success': False, 'error': 'SSH timeout'}
    except Exception as e:
        return {'success': False, 'error': str(e)}

def test_bandwidth(host, duration=10):
    """Test de bande passante (simplifié)"""
    try:
        # Test avec iperf si disponible
        cmd = ['iperf3', '-c', host, '-t', str(duration), '-f', 'M']
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=duration+5)
        
        if result.returncode == 0:
            # Parser les résultats iperf
            lines = result.stdout.split('\n')
            for line in lines:
                if 'sender' in line and 'Mbits/sec' in line:
                    parts = line.split()
                    bandwidth = float(parts[6])
                    return {'success': True, 'bandwidth': bandwidth, 'unit': 'Mbps'}
            
            return {'success': False, 'error': 'Could not parse iperf results'}
        else:
            return {'success': False, 'error': 'iperf failed'}
            
    except subprocess.TimeoutExpired:
        return {'success': False, 'error': 'iperf timeout'}
    except FileNotFoundError:
        return {'success': False, 'error': 'iperf3 not installed'}
    except Exception as e:
        return {'success': False, 'error': str(e)}

def test_node_comprehensive(host):
    """Test complet d'un nœud"""
    print(f"\n=== Test complet: {host} ===")
    
    results = {
        'host': host,
        'ping': None,
        'dispy_ports': None,
        'ssh': None,
        'bandwidth': None
    }
    
    # Test ping
    print("Test ping...")
    results['ping'] = test_ping(host)
    if results['ping']['success']:
        stats = results['ping']['stats']
        print(f"✓ Ping: {stats['received']}/{stats['transmitted']} packets, {stats['loss']}% loss")
        if 'rtt_avg' in stats:
            print(f"  RTT moyen: {stats['rtt_avg']:.2f}ms")
    else:
        print(f"✗ Ping: {results['ping']['error']}")
    
    # Test des ports dispy
    print("Test des ports dispy...")
    results['dispy_ports'] = test_dispy_ports(host)
    for service, result in results['dispy_ports'].items():
        if result['success']:
            print(f"✓ Port {service}: OK ({result['response_time']:.3f}s)")
        else:
            print(f"✗ Port {service}: {result['error']}")
    
    # Test SSH
    print("Test SSH...")
    results['ssh'] = test_ssh_connectivity(host)
    if results['ssh']['success']:
        print(f"✓ SSH: OK")
    else:
        print(f"✗ SSH: {results['ssh']['error']}")
    
    # Test de bande passante
    print("Test de bande passante...")
    results['bandwidth'] = test_bandwidth(host, duration=5)
    if results['bandwidth']['success']:
        print(f"✓ Bande passante: {results['bandwidth']['bandwidth']:.2f} {results['bandwidth']['unit']}")
    else:
        print(f"✗ Bande passante: {results['bandwidth']['error']}")
    
    return results

def generate_report(all_results):
    """Génère un rapport de connectivité"""
    print("\n" + "=" * 80)
    print("RAPPORT DE CONNECTIVITÉ DU CLUSTER")
    print("=" * 80)
    
    # Résumé global
    total_nodes = len(all_results)
    ping_ok = sum(1 for r in all_results if r['ping'] and r['ping']['success'])
    dispy_ok = sum(1 for r in all_results if r['dispy_ports'] and all(p['success'] for p in r['dispy_ports'].values()))
    ssh_ok = sum(1 for r in all_results if r['ssh'] and r['ssh']['success'])
    
    print(f"Total des nœuds testés: {total_nodes}")
    print(f"Ping OK: {ping_ok}/{total_nodes}")
    print(f"Ports Dispy OK: {dispy_ok}/{total_nodes}")
    print(f"SSH OK: {ssh_ok}/{total_nodes}")
    
    # Détails par nœud
    print("\nDétails par nœud:")
    print("-" * 80)
    
    for result in all_results:
        host = result['host']
        print(f"\n{host}:")
        
        # Ping
        if result['ping'] and result['ping']['success']:
            stats = result['ping']['stats']
            print(f"  Ping: ✓ {stats['loss']}% loss, {stats['rtt_avg']:.2f}ms")
        else:
            print(f"  Ping: ✗")
        
        # Ports dispy
        if result['dispy_ports']:
            for service, port_result in result['dispy_ports'].items():
                status = "✓" if port_result['success'] else "✗"
                print(f"  {service}: {status}")
        
        # SSH
        if result['ssh']:
            status = "✓" if result['ssh']['success'] else "✗"
            print(f"  SSH: {status}")
        
        # Bande passante
        if result['bandwidth'] and result['bandwidth']['success']:
            print(f"  Bande passante: {result['bandwidth']['bandwidth']:.2f} {result['bandwidth']['unit']}")
        else:
            print(f"  Bande passante: ✗")
    
    # Recommandations
    print("\n" + "=" * 80)
    print("RECOMMANDATIONS")
    print("=" * 80)
    
    if ping_ok < total_nodes:
        print("⚠️  Certains nœuds ne répondent pas au ping")
        print("   Vérifiez la connectivité réseau et les firewalls")
    
    if dispy_ok < total_nodes:
        print("⚠️  Certains nœuds n'ont pas les ports dispy ouverts")
        print("   Vérifiez la configuration dispy et les firewalls")
    
    if ssh_ok < total_nodes:
        print("⚠️  Certains nœuds ne sont pas accessibles en SSH")
        print("   Vérifiez la configuration SSH et les clés d'authentification")
    
    if ping_ok == total_nodes and dispy_ok == total_nodes and ssh_ok == total_nodes:
        print("✅ Tous les nœuds sont correctement configurés!")

def main():
    print("=== Test de connectivité réseau du cluster DispyCluster ===")
    print(f"Date: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"IP locale: {LOCAL_IP}")
    print()
    
    # Charger la configuration
    config = load_nodes_config()
    if not config:
        print("Impossible de charger la configuration des nœuds")
        return 1
    
    workers = config.get('workers', [])
    master = config.get('master', '')
    
    print(f"Nœuds workers: {workers}")
    print(f"Nœud master: {master}")
    print()
    
    # Tester tous les nœuds
    all_results = []
    
    # Test du master
    if master:
        result = test_node_comprehensive(master)
        all_results.append(result)
    
    # Test des workers
    for worker in workers:
        result = test_node_comprehensive(worker)
        all_results.append(result)
    
    # Générer le rapport
    generate_report(all_results)
    
    return 0

if __name__ == "__main__":
    sys.exit(main())