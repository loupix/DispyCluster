from datetime import datetime, timedelta
from web.celery_app import celery_app
import httpx
import asyncio
import json
import redis
from typing import Dict, List, Any
from web.config.metrics_config import NODES, REDIS_CONFIG, METRICS_CONFIG
from web.config.logging_config import get_logger
from web.core.metrics_history import history_manager
from web.core.redis_ts import xadd, ts_add

# Configuration du logger
logger = get_logger(__name__)

# Client Redis configuré
redis_client = redis.Redis(**REDIS_CONFIG)

# Cache pour les mesures CPU précédentes (nécessaire pour calculer l'utilisation)
cpu_prev_cache = {}

@celery_app.task
def collect_metrics():
    """Collecte optimisée des métriques avec cache Redis."""
    try:
        # Exécuter la collecte asynchrone
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        result = loop.run_until_complete(_collect_metrics_async())
        loop.close()
        
        return {
            "status": "collected",
            "timestamp": datetime.utcnow().isoformat(),
                "nodes_processed": result.get("nodes_processed", 0),
                "cache_updated": result.get("cache_updated", False)
            }
    except Exception as e:
        logger.error(f"Erreur collecte: {e}")
        return {
            "status": "error",
            "timestamp": datetime.utcnow().isoformat(),
            "error": str(e)
        }

async def _collect_metrics_async():
    """Collecte asynchrone des métriques depuis node_exporter."""
    results = {"nodes_processed": 0, "cache_updated": False}
    
    async with httpx.AsyncClient(timeout=METRICS_CONFIG["node_exporter_timeout"]) as client:
        # Collecter les métriques de tous les nœuds en parallèle
        tasks = [_collect_node_metrics(client, node) for node in NODES]
        node_results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Traiter les résultats et mettre à jour le cache
        for i, result in enumerate(node_results):
            if isinstance(result, Exception):
                continue
                
            if result and result.get("metrics"):
                node = NODES[i]
                # Stocker les métriques individuelles (cache actuel)
                redis_client.setex(
                    f"metrics:{node}", 
                    METRICS_CONFIG["cache_ttl"], 
                    json.dumps(result["metrics"])
                )
                
                # Stocker dans l'historique
                history_manager.store_metrics_point(node, result["metrics"])

                # Publier dans Redis Streams pour ingestion TimeSeries
                try:
                    metrics = result["metrics"]
                    labels = {"host": node}
                    if "cpu_usage" in metrics:
                        xadd("metrics:ingest", {"metric": "cpu.usage", "value": str(metrics["cpu_usage"]), "labels": json.dumps(labels)}, maxlen_approx=200000)
                        # Ecriture directe TS (en parallèle du Stream)
                        ts_add("ts:cpu.usage", float(metrics["cpu_usage"]), labels_if_create={"metric": "cpu.usage", "host": node})
                    if "memory_usage" in metrics:
                        xadd("metrics:ingest", {"metric": "memory.usage", "value": str(metrics["memory_usage"]), "labels": json.dumps(labels)}, maxlen_approx=200000)
                        ts_add("ts:memory.usage", float(metrics["memory_usage"]), labels_if_create={"metric": "memory.usage", "host": node})
                    if "disk_usage" in metrics:
                        xadd("metrics:ingest", {"metric": "disk.usage", "value": str(metrics["disk_usage"]), "labels": json.dumps(labels)}, maxlen_approx=200000)
                        ts_add("ts:disk.usage", float(metrics["disk_usage"]), labels_if_create={"metric": "disk.usage", "host": node})
                    if "temperature" in metrics and metrics["temperature"]:
                        xadd("metrics:ingest", {"metric": "temperature", "value": str(metrics["temperature"]), "labels": json.dumps(labels)}, maxlen_approx=200000)
                        ts_add("ts:temperature", float(metrics["temperature"]), labels_if_create={"metric": "temperature", "host": node})
                except Exception as stream_err:
                    logger.warning(f"Publication Streams métriques échouée pour {node}: {stream_err}")
                
                results["nodes_processed"] += 1
        
        # Mettre à jour les métriques agrégées
        if results["nodes_processed"] > 0:
            _update_aggregated_metrics()
            results["cache_updated"] = True
    
    return results

async def _collect_node_metrics(client: httpx.AsyncClient, node: str) -> Dict[str, Any]:
    """Collecte les métriques d'un nœud spécifique."""
    try:
        # Vérifier la santé du nœud d'abord
        health_url = f"http://{node}:{METRICS_CONFIG['node_exporter_port']}/"
        response = await client.get(health_url)
        
        if response.status_code != 200:
            return None
        
        # Récupérer les métriques
        metrics_url = f"http://{node}:{METRICS_CONFIG['node_exporter_port']}/metrics"
        response = await client.get(metrics_url)
        
        if response.status_code == 200:
            metrics = _parse_node_exporter_metrics(response.text, node)
            return {"node": node, "metrics": metrics}
        else:
            return None
            
    except Exception:
        return None

def _parse_node_exporter_metrics(metrics_text: str, node: str) -> Dict[str, Any]:
    """Parse les métriques node_exporter et calcule les valeurs."""
    metrics = {}
    lines = metrics_text.strip().split('\n')
    
    # Variables pour le calcul CPU
    cpu_user = 0
    cpu_system = 0
    cpu_idle = 0
    
    for line in lines:
        if line.startswith('#') or not line.strip():
            continue
            
        # CPU usage
        if 'node_cpu_seconds_total' in line and 'mode="user"' in line:
            cpu_user = float(line.split()[-1])
        elif 'node_cpu_seconds_total' in line and 'mode="system"' in line:
            cpu_system = float(line.split()[-1])
        elif 'node_cpu_seconds_total' in line and 'mode="idle"' in line:
            cpu_idle = float(line.split()[-1])
        
        # Memory
        elif 'node_memory_MemTotal_bytes' in line:
            metrics['memory_total'] = float(line.split()[-1])
        elif 'node_memory_MemAvailable_bytes' in line:
            metrics['memory_available'] = float(line.split()[-1])
        
        # Disk
        elif 'node_filesystem_size_bytes' in line and 'mountpoint="/"' in line:
            metrics['disk_total'] = float(line.split()[-1])
        elif 'node_filesystem_avail_bytes' in line and 'mountpoint="/"' in line:
            metrics['disk_available'] = float(line.split()[-1])
        
        # Temperature
        elif 'node_thermal_zone_temp' in line:
            metrics['temperature'] = float(line.split()[-1])
        elif 'node_hwmon_temp_celsius' in line:
            metrics['temperature'] = float(line.split()[-1])
    
    # Calculer l'utilisation CPU
    if node in cpu_prev_cache:
        prev = cpu_prev_cache[node]
        cpu_usage = _calculate_cpu_usage(
            cpu_user, cpu_system, cpu_idle,
            prev.get('cpu_user', 0), prev.get('cpu_system', 0), prev.get('cpu_idle', 0)
        )
        metrics['cpu_usage'] = cpu_usage
    else:
        metrics['cpu_usage'] = 0
    
    # Mettre à jour le cache CPU
    cpu_prev_cache[node] = {
        'cpu_user': cpu_user,
        'cpu_system': cpu_system,
        'cpu_idle': cpu_idle
    }
    
    # Calculer l'utilisation mémoire
    if 'memory_total' in metrics and 'memory_available' in metrics:
        memory_used = metrics['memory_total'] - metrics['memory_available']
        metrics['memory_usage'] = (memory_used / metrics['memory_total']) * 100
    else:
        metrics['memory_usage'] = 0
    
    # Calculer l'utilisation disque
    if 'disk_total' in metrics and 'disk_available' in metrics:
        disk_used = metrics['disk_total'] - metrics['disk_available']
        metrics['disk_usage'] = (disk_used / metrics['disk_total']) * 100
    else:
        metrics['disk_usage'] = 0
    
    return metrics

def _calculate_cpu_usage(user, system, idle, prev_user, prev_system, prev_idle):
    """Calcule l'utilisation CPU basée sur les mesures précédentes."""
    try:
        user_diff = user - prev_user
        system_diff = system - prev_system
        idle_diff = idle - prev_idle
        
        total_diff = user_diff + system_diff + idle_diff
        if total_diff > 0:
            return ((user_diff + system_diff) / total_diff) * 100
        return 0
    except:
        return 0

def _update_aggregated_metrics():
    """Met à jour les métriques agrégées dans Redis."""
    try:
        aggregated = {
            "timestamp": datetime.utcnow().isoformat(),
            "nodes": {},
            "cluster_stats": {
                "total_nodes": len(NODES),
                "online_nodes": 0,
                "avg_cpu": 0,
                "avg_memory": 0,
                "avg_temperature": 0
            }
        }
        
        total_cpu = 0
        total_memory = 0
        total_temp = 0
        online_count = 0
        
        for node in NODES:
            node_data = redis_client.get(f"metrics:{node}")
            if node_data:
                metrics = json.loads(node_data)
                aggregated["nodes"][node] = metrics
                
                if metrics.get("cpu_usage", 0) > 0:
                    online_count += 1
                    total_cpu += metrics.get("cpu_usage", 0)
                    total_memory += metrics.get("memory_usage", 0)
                    if "temperature" in metrics:
                        total_temp += metrics["temperature"]
        
        # Calculer les moyennes
        if online_count > 0:
            aggregated["cluster_stats"]["online_nodes"] = online_count
            aggregated["cluster_stats"]["avg_cpu"] = total_cpu / online_count
            aggregated["cluster_stats"]["avg_memory"] = total_memory / online_count
            aggregated["cluster_stats"]["avg_temperature"] = total_temp / online_count
        
        # Stocker dans Redis (metrics agrégées)
        payload = json.dumps(aggregated)
        redis_client.setex("cluster:metrics", METRICS_CONFIG["aggregated_ttl"], payload)
        
        # Publier sur pub/sub cluster:metrics
        try:
            redis_client.publish("cluster:metrics", payload)
        except Exception as pub_err:
            logger.warning(f"Publication pub/sub cluster:metrics échouée: {pub_err}")

        # Calculer et publier la santé globale sur cluster:health
        try:
            total_nodes = aggregated["cluster_stats"].get("total_nodes", 0)
            online_nodes = aggregated["cluster_stats"].get("online_nodes", 0)
            down_nodes = max(total_nodes - online_nodes, 0)
            if down_nodes == 0 and total_nodes > 0:
                overall_status = "healthy"
            elif down_nodes <= total_nodes // 2:
                overall_status = "warning"
            else:
                overall_status = "critical"

            health_data = {
                "timestamp": datetime.utcnow().isoformat(),
                "overall_status": overall_status,
                "nodes_online": online_nodes,
                "nodes_total": total_nodes,
                "issues": [] if overall_status == "healthy" else [f"{down_nodes} nœuds hors ligne"]
            }
            redis_client.publish("cluster:health", json.dumps(health_data))
        except Exception as pub_err:
            logger.warning(f"Publication pub/sub cluster:health échouée: {pub_err}")

        # Générer et publier des alertes sur cluster:alerts
        try:
            alerts = []
            # Seuils simples
            cpu_avg = aggregated["cluster_stats"].get("avg_cpu", 0)
            mem_avg = aggregated["cluster_stats"].get("avg_memory", 0)
            if cpu_avg > 90:
                alerts.append({"id": "high_cpu_avg", "type": "warning", "message": f"CPU moyenne élevée: {cpu_avg:.1f}%"})
            if mem_avg > 90:
                alerts.append({"id": "high_memory_avg", "type": "warning", "message": f"Mémoire moyenne élevée: {mem_avg:.1f}%"})

            # Alertes par nœud (exemple température > 80C)
            for node, metrics in aggregated.get("nodes", {}).items():
                temp = metrics.get("temperature", 0)
                if temp and temp > 80:
                    alerts.append({"id": f"high_temp_{node}", "type": "critical", "message": f"{node}: Température élevée ({temp:.1f}°C)"})

            alerts_payload = {
                "timestamp": datetime.utcnow().isoformat(),
                "active_alerts": alerts,
                "alert_count": len(alerts)
            }
            redis_client.publish("cluster:alerts", json.dumps(alerts_payload))
        except Exception as pub_err:
            logger.warning(f"Publication pub/sub cluster:alerts échouée: {pub_err}")
        
    except Exception:
        pass

@celery_app.task
def get_cached_metrics():
    """Récupère les métriques depuis le cache Redis."""
    try:
        # Métriques agrégées
        aggregated_data = redis_client.get("cluster:metrics")
        if aggregated_data:
            return json.loads(aggregated_data)
        
        # Fallback vers les métriques individuelles
        metrics = {}
        for node in NODES:
            node_data = redis_client.get(f"metrics:{node}")
            if node_data:
                metrics[node] = json.loads(node_data)
        
        return {
            "timestamp": datetime.utcnow().isoformat(),
            "nodes": metrics,
            "cluster_stats": {
                "total_nodes": len(NODES),
                "online_nodes": len(metrics),
                "avg_cpu": 0,
                "avg_memory": 0,
                "avg_temperature": 0
            }
        }
        
    except Exception:
        return {
            "timestamp": datetime.utcnow().isoformat(),
            "nodes": {},
            "cluster_stats": {
                "total_nodes": len(NODES),
                "online_nodes": 0,
                "avg_cpu": 0,
                "avg_memory": 0,
                "avg_temperature": 0
            }
        }



