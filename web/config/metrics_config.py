"""Configuration pour les métriques et le cache Redis."""

import os
import yaml
from pathlib import Path
from typing import List, Dict, Any

# Configuration Redis
REDIS_HOST = os.getenv("REDIS_HOST", "node13.lan")
REDIS_PORT = int(os.getenv("REDIS_PORT", "6379"))
REDIS_METRICS_DB = int(os.getenv("REDIS_METRICS_DB", "2"))

# Configuration des métriques
METRICS_CACHE_TTL = int(os.getenv("METRICS_CACHE_TTL", "300"))
METRICS_AGGREGATED_TTL = int(os.getenv("METRICS_AGGREGATED_TTL", "300"))
METRICS_COLLECTION_INTERVAL = int(os.getenv("METRICS_COLLECTION_INTERVAL", "10"))

# Configuration node_exporter
NODE_EXPORTER_PORT = int(os.getenv("NODE_EXPORTER_PORT", "9100"))
NODE_EXPORTER_TIMEOUT = int(os.getenv("NODE_EXPORTER_TIMEOUT", "5"))

def load_nodes_from_yaml() -> List[str]:
    """Charge la liste des nœuds depuis nodes.yaml."""
    try:
        # Essayer d'abord le fichier dans le dossier web
        nodes_file = Path(__file__).parent.parent / "nodes.yaml"
        if not nodes_file.exists():
            # Fallback vers le fichier à la racine
            nodes_file = Path(__file__).parent.parent.parent / "inventory" / "nodes.yaml"
        
        if not nodes_file.exists():
            # Fallback vers la liste par défaut
            return [
                "node6.lan", "node7.lan", "node9.lan", "node10.lan",
                "node11.lan", "node12.lan", "node13.lan", "node14.lan"
            ]
        
        with open(nodes_file, 'r', encoding='utf-8') as f:
            data = yaml.safe_load(f)
        
        if 'workers' in data and isinstance(data['workers'], list):
            return data['workers']
        
        # Si pas de workers, retourner la liste par défaut
        return [
            "node6.lan", "node7.lan", "node9.lan", "node10.lan",
            "node11.lan", "node12.lan", "node13.lan", "node14.lan"
        ]
        
    except Exception as e:
        print(f"Erreur chargement nodes.yaml: {e}")
        # Fallback vers la liste par défaut
        return [
            "node6.lan", "node7.lan", "node9.lan", "node10.lan",
            "node11.lan", "node12.lan", "node13.lan", "node14.lan"
        ]

# Liste des nœuds chargée depuis nodes.yaml
NODES = load_nodes_from_yaml()

# Configuration Redis complète
REDIS_CONFIG = {
    "host": REDIS_HOST,
    "port": REDIS_PORT,
    "db": REDIS_METRICS_DB,
    "decode_responses": True
}

# Configuration des métriques
METRICS_CONFIG = {
    "cache_ttl": METRICS_CACHE_TTL,
    "aggregated_ttl": METRICS_AGGREGATED_TTL,
    "collection_interval": METRICS_COLLECTION_INTERVAL,
    "node_exporter_port": NODE_EXPORTER_PORT,
    "node_exporter_timeout": NODE_EXPORTER_TIMEOUT
}
