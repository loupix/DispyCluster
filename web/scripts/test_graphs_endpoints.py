#!/usr/bin/env python3
"""Test des endpoints de graphiques."""

import requests
import json
import time

def test_endpoints():
    """Test des endpoints de graphiques."""
    base_url = "http://localhost:8085"
    
    print("🧪 Test des endpoints de graphiques...")
    print("=" * 50)
    
    # Attendre que l'application démarre
    print("⏳ Attente du démarrage de l'application...")
    time.sleep(5)
    
    endpoints = [
        ("CPU History", "/api/graphs/cpu-history?hours=1"),
        ("Memory History", "/api/graphs/memory-history?hours=1"),
        ("Disk History", "/api/graphs/disk-history?hours=1"),
        ("Temperature History", "/api/graphs/temperature-history?hours=1"),
        ("Combined History", "/api/graphs/combined-history?hours=1"),
        ("Nodes List", "/api/graphs/nodes-list"),
        ("Realtime Data", "/api/graphs/realtime-data")
    ]
    
    results = []
    
    for name, endpoint in endpoints:
        try:
            print(f"🔗 Test {name}...")
            response = requests.get(f"{base_url}{endpoint}", timeout=10)
            
            if response.status_code == 200:
                data = response.json()
                points = data.get('data_points', 0)
                print(f"  ✅ Succès: {points} points de données")
                results.append((name, True, points))
            else:
                print(f"  ❌ Erreur HTTP {response.status_code}")
                results.append((name, False, 0))
                
        except Exception as e:
            print(f"  ❌ Erreur: {e}")
            results.append((name, False, 0))
    
    # Résumé
    print("\n" + "=" * 50)
    print("📊 RÉSUMÉ DES TESTS:")
    
    success_count = 0
    total_points = 0
    
    for name, success, points in results:
        status = "✅" if success else "❌"
        print(f"  {status} {name}: {points} points")
        if success:
            success_count += 1
            total_points += points
    
    print(f"\n📈 Résultat: {success_count}/{len(results)} endpoints fonctionnels")
    print(f"📊 Total: {total_points} points de données")
    
    if success_count > 0:
        print("\n🎉 Les graphiques devraient maintenant afficher des données !")
        print("   Visitez: http://localhost:8085/monitoring")
    else:
        print("\n❌ Aucun endpoint ne fonctionne. Vérifiez l'application.")

if __name__ == "__main__":
    test_endpoints()

