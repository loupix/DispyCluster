#!/usr/bin/env python3
"""Test rapide du système de graphiques."""

import sys
import os
import json
import random
import redis
from datetime import datetime, timedelta

# Configuration Redis
REDIS_CONFIG = {
    "host": "node13.lan",
    "port": 6379,
    "db": 2,
    "decode_responses": True
}

def test_redis_connection():
    """Test de connexion Redis."""
    try:
        client = redis.Redis(**REDIS_CONFIG)
        client.ping()
        print("✅ Connexion Redis OK")
        return client
    except Exception as e:
        print(f"❌ Erreur Redis: {e}")
        return None

def generate_simple_test_data(redis_client):
    """Génère des données de test simples."""
    print("📈 Génération de données de test...")
    
    nodes = ["node6.lan", "node7.lan", "node9.lan", "node12.lan", "node13.lan", "node14.lan"]
    points_generated = 0
    
    # Générer 24 points (une heure, toutes les 2.5 minutes)
    for i in range(24):
        timestamp = datetime.utcnow() - timedelta(minutes=i * 2.5)
        timestamp_key = timestamp.strftime("%Y%m%d%H%M%S")
        
        for node in nodes:
            # Métriques réalistes
            metrics = {
                "cpu_usage": random.uniform(0.1, 15.0),
                "memory_usage": random.uniform(25.0, 70.0),
                "disk_usage": random.uniform(20.0, 85.0),
                "temperature": random.uniform(35.0, 55.0)
            }
            
            # Stocker dans Redis
            history_key = f"history:{node}:{timestamp_key}"
            history_data = {
                "timestamp": timestamp.isoformat(),
                "node": node,
                "metrics": metrics
            }
            
            redis_client.setex(history_key, 7 * 24 * 60 * 60, json.dumps(history_data))
            
            # Ajouter à la liste des timestamps
            timestamps_key = f"timestamps:{node}"
            redis_client.zadd(timestamps_key, {timestamp_key: timestamp.timestamp()})
            redis_client.expire(timestamps_key, 7 * 24 * 60 * 60)
            
            points_generated += 1
    
    print(f"✅ {points_generated} points générés pour {len(nodes)} nœuds")
    return points_generated

def test_api_endpoints():
    """Test des endpoints API."""
    print("\n🌐 Test des endpoints API...")
    
    import requests
    
    base_url = "http://localhost:8085"
    endpoints = [
        "/api/graphs/cpu-history?hours=1",
        "/api/graphs/memory-history?hours=1",
        "/api/graphs/disk-history?hours=1",
        "/api/graphs/temperature-history?hours=1"
    ]
    
    for endpoint in endpoints:
        try:
            response = requests.get(f"{base_url}{endpoint}", timeout=5)
            if response.status_code == 200:
                data = response.json()
                print(f"  ✅ {endpoint}: {data.get('data_points', 0)} points")
            else:
                print(f"  ❌ {endpoint}: HTTP {response.status_code}")
        except Exception as e:
            print(f"  ⚠️  {endpoint}: {e}")

def main():
    """Fonction principale."""
    print("🚀 Test rapide du système de graphiques")
    print("=" * 50)
    
    # Test Redis
    redis_client = test_redis_connection()
    if not redis_client:
        print("❌ Impossible de continuer sans Redis")
        return
    
    # Générer des données de test
    points = generate_simple_test_data(redis_client)
    if points > 0:
        print("✅ Données de test générées avec succès !")
        print("\n📊 Pour voir les graphiques:")
        print("   1. Démarrez l'application: python -m uvicorn web.app:app --host 0.0.0.0 --port 8085")
        print("   2. Visitez: http://localhost:8085/monitoring")
        print("   3. Les graphiques devraient maintenant afficher des données")
    else:
        print("❌ Erreur lors de la génération des données")
    
    # Test des endpoints (si l'app est démarrée)
    print("\n" + "=" * 50)
    test_api_endpoints()

if __name__ == "__main__":
    main()

