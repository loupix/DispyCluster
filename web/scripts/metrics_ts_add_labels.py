"""Script pour ajouter les labels aux séries TimeSeries existantes.

Usage:
    python -m web.scripts.metrics_ts_add_labels
"""

from web.core.redis_ts import get_redis_client, ts_alter, has_timeseries
from web.config.metrics_config import NODES


def main():
    if not has_timeseries():
        print("Erreur: module RedisTimeSeries non disponible")
        return
    
    client = get_redis_client()
    
    # 1. Ajouter les labels à la série globale ts:cpu.usage
    global_key = "ts:cpu.usage"
    try:
        # Vérifier que la série existe
        client.execute_command("TS.INFO", global_key)
        ts_alter(global_key, labels={"metric": "cpu.usage", "host": "all"})
        print(f"✓ Labels ajoutés à {global_key}")
    except Exception as e:
        if "does not exist" in str(e):
            print(f"✗ {global_key} n'existe pas")
        else:
            print(f"✗ Erreur pour {global_key}: {e}")
    
    # 2. Ajouter les labels aux séries par hôte
    for node in NODES:
        key = f"ts:cpu.usage:host:{node}"
        try:
            # Vérifier que la série existe
            client.execute_command("TS.INFO", key)
            ts_alter(key, labels={"metric": "cpu.usage", "host": node})
            print(f"✓ Labels ajoutés à {key}")
        except Exception as e:
            if "does not exist" in str(e):
                print(f"✗ {key} n'existe pas")
            else:
                print(f"✗ Erreur pour {key}: {e}")
    
    print("\nVérification avec TS.MRANGE:")
    try:
        result = client.execute_command("TS.MRANGE", "-", "+", "WITHLABELS", "FILTER", "metric=cpu.usage")
        print(f"✓ Trouvé {len(result)} série(s) avec label metric=cpu.usage")
        for serie in result:
            key = serie[0]
            labels_list = serie[1] if len(serie) > 1 else []
            labels = {k: v for k, v in labels_list}
            print(f"  - {key}: {labels}")
    except Exception as e:
        print(f"✗ Erreur TS.MRANGE: {e}")


if __name__ == "__main__":
    main()

