#!/usr/bin/env python3
"""Nettoyage des anciennes clés Redis."""

import sys
import os
import redis

# Ajouter le répertoire parent au path
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

def cleanup_old_keys():
    """Nettoie les anciennes clés Redis."""
    print("🧹 Nettoyage des anciennes clés Redis...")
    print("=" * 50)
    
    try:
        from web.config.metrics_config import REDIS_CONFIG
        redis_client = redis.Redis(**REDIS_CONFIG)
        
        # Vérifier les clés avant nettoyage
        old_keys = redis_client.keys("history:*:*")  # Ancien format
        timestamp_keys = redis_client.keys("timestamps:*")
        
        print(f"📊 Clés à nettoyer:")
        print(f"  - history:*:*: {len(old_keys)} clés")
        print(f"  - timestamps:*: {len(timestamp_keys)} clés")
        
        total_old = len(old_keys) + len(timestamp_keys)
        
        if total_old == 0:
            print("✅ Aucune ancienne clé à nettoyer")
            return True
        
        # Demander confirmation
        print(f"\n⚠️  {total_old} clés vont être supprimées")
        response = input("Continuer ? (y/N): ").strip().lower()
        
        if response != 'y':
            print("❌ Nettoyage annulé")
            return False
        
        # Supprimer les anciennes clés
        print("\n🗑️  Suppression des anciennes clés...")
        
        deleted_count = 0
        
        # Supprimer les clés history:*:*
        if old_keys:
            deleted_count += redis_client.delete(*old_keys)
            print(f"✅ {len(old_keys)} clés history:*:* supprimées")
        
        # Supprimer les clés timestamps:*
        if timestamp_keys:
            deleted_count += redis_client.delete(*timestamp_keys)
            print(f"✅ {len(timestamp_keys)} clés timestamps:* supprimées")
        
        print(f"\n🎉 Nettoyage terminé: {deleted_count} clés supprimées")
        
        # Vérifier les clés restantes
        new_keys = redis_client.keys("history:*")
        print(f"📊 Clés restantes: {len(new_keys)}")
        
        if len(new_keys) <= 10:
            print("✅ Système optimisé: très peu de clés Redis")
        else:
            print("⚠️  Encore beaucoup de clés, vérifier")
        
        return True
        
    except Exception as e:
        print(f"❌ Erreur lors du nettoyage: {e}")
        return False

def main():
    """Fonction principale."""
    success = cleanup_old_keys()
    
    if success:
        print("\n🚀 Le système est maintenant optimisé !")
        print("📊 Avantages:")
        print("  - Réduction drastique du nombre de clés Redis")
        print("  - Stockage par liste (plus efficace)")
        print("  - Même fonctionnalité pour les graphiques")
    else:
        print("\n❌ Nettoyage échoué ou annulé.")

if __name__ == "__main__":
    main()
