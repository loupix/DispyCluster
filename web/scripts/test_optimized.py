#!/usr/bin/env python3
"""Test du système de graphiques optimisé."""

import sys
import os
import json
import redis
from datetime import datetime, timedelta

# Ajouter le répertoire parent au path
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

def test_optimized_system():
    """Test du système optimisé."""
    print("🧪 Test du système de graphiques optimisé...")
    print("=" * 50)
    
    try:
        # Test 1: Import du module
        print("📦 Test d'import...")
        from web.core.metrics_history import history_manager
        print("✅ Module importé avec succès")
        
        # Test 2: Connexion Redis
        print("\n🔗 Test de connexion Redis...")
        from web.config.metrics_config import REDIS_CONFIG
        redis_client = redis.Redis(**REDIS_CONFIG)
        redis_client.ping()
        print("✅ Redis connecté")
        
        # Test 3: Vérifier les clés existantes
        print("\n📊 Vérification des clés Redis...")
        old_keys = redis_client.keys("history:*:*")  # Ancien format
        new_keys = redis_client.keys("history:*")    # Nouveau format (sans timestamp)
        
        print(f"  🔍 Clés ancien format: {len(old_keys)}")
        print(f"  🔍 Clés nouveau format: {len(new_keys)}")
        
        if len(new_keys) > 0:
            print("✅ Système optimisé en cours d'utilisation")
        elif len(old_keys) > 0:
            print("⚠️  Ancien système encore présent")
        else:
            print("ℹ️  Aucune donnée historique trouvée")
        
        # Test 4: Test de stockage
        print("\n📝 Test de stockage...")
        test_metrics = {
            "cpu_usage": 25.5,
            "memory_usage": 60.2,
            "disk_usage": 45.8,
            "temperature": 42.3
        }
        
        success = history_manager.store_metrics_point("test_node", test_metrics)
        if success:
            print("✅ Stockage réussi")
        else:
            print("❌ Échec du stockage")
            return False
        
        # Test 5: Test de récupération
        print("\n📈 Test de récupération...")
        history = history_manager.get_node_history("test_node", 1)
        if history and len(history) > 0:
            print(f"✅ Historique récupéré: {len(history)} points")
            latest = history[0]  # Plus récent en premier
            print(f"📊 Dernière métrique: CPU {latest['metrics']['cpu_usage']}%")
        else:
            print("❌ Aucun historique trouvé")
            return False
        
        # Test 6: Vérifier le nombre de clés après test
        print("\n🔍 Vérification finale des clés...")
        final_keys = redis_client.keys("history:*")
        print(f"📊 Nombre total de clés: {len(final_keys)}")
        
        if len(final_keys) <= 10:  # Maximum 6 nœuds + quelques tests
            print("✅ Système optimisé: très peu de clés Redis")
        else:
            print("⚠️  Nombre de clés élevé, vérifier l'optimisation")
        
        return True
        
    except Exception as e:
        print(f"❌ Erreur lors du test: {e}")
        import traceback
        traceback.print_exc()
        return False

def main():
    """Fonction principale."""
    success = test_optimized_system()
    
    print("\n" + "=" * 50)
    if success:
        print("🎉 Système optimisé fonctionnel !")
        print("📊 Avantages:")
        print("  - Réduction drastique du nombre de clés Redis")
        print("  - Stockage par liste (plus efficace)")
        print("  - Même fonctionnalité pour les graphiques")
        print("\n🚀 Pour démarrer:")
        print("  python start_graphs.py")
        print("  http://localhost:8085/monitoring")
    else:
        print("❌ Des problèmes ont été détectés.")

if __name__ == "__main__":
    main()
