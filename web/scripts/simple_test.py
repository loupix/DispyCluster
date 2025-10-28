#!/usr/bin/env python3
"""Test simple de l'application."""

import sys
import os
import requests
import time

# Ajouter le répertoire parent au path
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

def test_app_startup():
    """Test si l'application peut démarrer."""
    try:
        print("🧪 Test de démarrage de l'application...")
        
        # Importer l'application
        from web.app import app
        print("✅ Application importée avec succès")
        
        # Tester les routes
        print("🔍 Test des routes...")
        
        # Vérifier que les routes existent
        routes = [route.path for route in app.routes]
        print(f"📋 {len(routes)} routes trouvées")
        
        # Vérifier les routes de graphiques
        graph_routes = [r for r in routes if 'graphs' in r]
        print(f"📊 Routes de graphiques: {len(graph_routes)}")
        for route in graph_routes[:5]:  # Afficher les 5 premières
            print(f"  - {route}")
        
        return True
        
    except Exception as e:
        print(f"❌ Erreur: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_redis_connection():
    """Test de connexion Redis."""
    try:
        print("\n🔗 Test de connexion Redis...")
        import redis
        from web.config.metrics_config import REDIS_CONFIG
        
        client = redis.Redis(**REDIS_CONFIG)
        client.ping()
        print("✅ Redis connecté")
        
        # Vérifier les données de test
        keys = client.keys("history:*")
        print(f"📊 {len(keys)} clés d'historique trouvées")
        
        return True
        
    except Exception as e:
        print(f"❌ Erreur Redis: {e}")
        return False

def main():
    """Fonction principale."""
    print("🚀 Test simple du système de graphiques")
    print("=" * 50)
    
    # Test 1: Démarrage de l'application
    app_ok = test_app_startup()
    
    # Test 2: Connexion Redis
    redis_ok = test_redis_connection()
    
    # Résumé
    print("\n" + "=" * 50)
    print("📊 RÉSUMÉ:")
    print(f"  {'✅' if app_ok else '❌'} Application: {'OK' if app_ok else 'ERREUR'}")
    print(f"  {'✅' if redis_ok else '❌'} Redis: {'OK' if redis_ok else 'ERREUR'}")
    
    if app_ok and redis_ok:
        print("\n🎉 Le système est prêt !")
        print("   Pour démarrer l'application:")
        print("   python -c \"import sys; sys.path.append('.'); from web.app import app; import uvicorn; uvicorn.run(app, host='0.0.0.0', port=8085)\"")
    else:
        print("\n⚠️  Des problèmes ont été détectés.")

if __name__ == "__main__":
    main()
