"""Gestionnaire ultra-simple de l'historique des métriques."""

import json
import redis
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional
from web.config.metrics_config import REDIS_CONFIG
from web.config.logging_config import get_logger

logger = get_logger(__name__)

class MetricsHistoryManager:
    """Gestionnaire ultra-simple de l'historique des métriques."""
    
    def __init__(self):
        self.redis_client = redis.Redis(**REDIS_CONFIG)
        # TTL pour l'historique : 7 jours
        self.history_ttl = 7 * 24 * 60 * 60  # 7 jours en secondes
        # Taille max de la liste par nœud : 20,160 points (7 jours * 24h * 60min / 5min)
        self.max_points_per_node = 20160
        
    def store_metrics_point(self, node: str, metrics: Dict[str, Any]) -> bool:
        """Stocke un point de métriques dans une liste Redis."""
        try:
            timestamp = datetime.utcnow()
            
            # Clé pour l'historique du nœud
            history_key = f"history:{node}"
            
            # Données à stocker
            point_data = {
                "timestamp": timestamp.isoformat(),
                "metrics": metrics
            }
            
            # Ajouter à la liste (push à gauche)
            self.redis_client.lpush(history_key, json.dumps(point_data))
            
            # Limiter la taille de la liste
            self.redis_client.ltrim(history_key, 0, self.max_points_per_node - 1)
            
            # Définir le TTL
            self.redis_client.expire(history_key, self.history_ttl)
            
            logger.debug(f"Point stocké dans liste pour {node}")
            return True
            
        except Exception as e:
            logger.error(f"Erreur stockage liste {node}: {e}")
            return False
    
    def get_node_history(self, node: str, hours: int = 24) -> List[Dict[str, Any]]:
        """Récupère l'historique d'un nœud pour les dernières heures."""
        try:
            history_key = f"history:{node}"
            
            # Récupérer tous les points de la liste
            points_data = self.redis_client.lrange(history_key, 0, -1)
            
            history = []
            cutoff_time = datetime.utcnow() - timedelta(hours=hours)
            
            for point_data in points_data:
                # Gérer les cas où point_data est bytes ou string
                if isinstance(point_data, bytes):
                    point = json.loads(point_data.decode())
                else:
                    point = json.loads(point_data)
                timestamp = datetime.fromisoformat(point["timestamp"].replace("Z", "+00:00"))
                
                # Filtrer par période
                if timestamp >= cutoff_time:
                    history.append({
                        "timestamp": point["timestamp"],
                        "node": node,
                        "metrics": point["metrics"]
                    })
            
            # Trier par timestamp (plus récent en premier)
            history.sort(key=lambda x: x["timestamp"], reverse=True)
            return history
            
        except Exception as e:
            logger.error(f"Erreur récupération historique {node}: {e}")
            return []
    
    def get_cluster_history(self, hours: int = 24) -> Dict[str, List[Dict[str, Any]]]:
        """Récupère l'historique de tous les nœuds du cluster."""
        try:
            # Récupérer tous les nœuds depuis les clés d'historique
            pattern = "history:*"
            history_keys = self.redis_client.keys(pattern)
            
            cluster_history = {}
            for key in history_keys:
                # Gérer les cas où key est bytes ou string
                if isinstance(key, bytes):
                    node = key.decode().replace("history:", "")
                else:
                    node = key.replace("history:", "")
                cluster_history[node] = self.get_node_history(node, hours)
            
            return cluster_history
            
        except Exception as e:
            logger.error(f"Erreur récupération historique cluster: {e}")
            return {}
    
    def get_aggregated_history(self, hours: int = 24, interval_minutes: int = 5) -> List[Dict[str, Any]]:
        """Récupère l'historique agrégé du cluster."""
        try:
            cluster_history = self.get_cluster_history(hours)
            
            # Grouper par intervalles de temps
            intervals = {}
            interval_seconds = interval_minutes * 60
            
            for node, history in cluster_history.items():
                for point in history:
                    timestamp = datetime.fromisoformat(point["timestamp"].replace("Z", "+00:00"))
                    interval_key = int(timestamp.timestamp() // interval_seconds) * interval_seconds
                    
                    if interval_key not in intervals:
                        intervals[interval_key] = {
                            "timestamp": datetime.fromtimestamp(interval_key).isoformat(),
                            "nodes": {},
                            "cluster_stats": {
                                "avg_cpu": 0,
                                "avg_memory": 0,
                                "avg_disk": 0,
                                "avg_temperature": 0,
                                "online_nodes": 0,
                                "total_nodes": 0
                            }
                        }
                    
                    intervals[interval_key]["nodes"][node] = point["metrics"]
            
            # Calculer les statistiques agrégées
            aggregated_history = []
            for interval_key in sorted(intervals.keys()):
                interval_data = intervals[interval_key]
                nodes_data = interval_data["nodes"]
                
                if nodes_data:
                    # Calculer les moyennes
                    cpu_values = [data.get("cpu_usage", 0) for data in nodes_data.values()]
                    memory_values = [data.get("memory_usage", 0) for data in nodes_data.values()]
                    disk_values = [data.get("disk_usage", 0) for data in nodes_data.values()]
                    temp_values = [data.get("temperature", 0) for data in nodes_data.values() if data.get("temperature", 0) > 0]
                    
                    interval_data["cluster_stats"]["avg_cpu"] = sum(cpu_values) / len(cpu_values) if cpu_values else 0
                    interval_data["cluster_stats"]["avg_memory"] = sum(memory_values) / len(memory_values) if memory_values else 0
                    interval_data["cluster_stats"]["avg_disk"] = sum(disk_values) / len(disk_values) if disk_values else 0
                    interval_data["cluster_stats"]["avg_temperature"] = sum(temp_values) / len(temp_values) if temp_values else 0
                    interval_data["cluster_stats"]["online_nodes"] = len([v for v in cpu_values if v > 0])
                    interval_data["cluster_stats"]["total_nodes"] = len(nodes_data)
                
                aggregated_history.append(interval_data)
            
            return aggregated_history
            
        except Exception as e:
            logger.error(f"Erreur calcul historique agrégé: {e}")
            return []
    
    def cleanup_old_data(self) -> int:
        """Nettoie les anciennes données expirées."""
        try:
            # Les données sont automatiquement supprimées par Redis avec le TTL
            pattern = "history:*"
            history_keys = self.redis_client.keys(pattern)
            
            cleaned = 0
            for key in history_keys:
                # Vérifier si la clé a expiré
                if not self.redis_client.exists(key):
                    cleaned += 1
            
            logger.info(f"Nettoyage terminé: {cleaned} clés supprimées")
            return cleaned
            
        except Exception as e:
            logger.error(f"Erreur nettoyage: {e}")
            return 0

# Instance globale
history_manager = MetricsHistoryManager()
