"""Gestionnaire WebSocket avec support Redis pub/sub pour le monitoring en temps réel."""

import asyncio
import json
import logging
from typing import Dict, Set, Any
from datetime import datetime

import redis
import socketio
from socketio import AsyncServer, AsyncNamespace

from web.config.metrics_config import REDIS_CONFIG
from web.config.logging_config import get_logger

logger = get_logger(__name__)


class WebSocketManager:
    """Gestionnaire central pour les connexions WebSocket."""
    
    def __init__(self):
        self.sio = AsyncServer(
            cors_allowed_origins="*",
            async_mode="asgi",
            logger=False,
            engineio_logger=False
        )
        self.app = None
        self.redis_client = redis.Redis(**REDIS_CONFIG)
        self.pubsub = None
        self.connected_clients: Set[str] = set()
        self.namespaces = {}
        
    def init_app(self, app):
        """Initialiser l'application WebSocket avec FastAPI."""
        self.app = socketio.ASGIApp(self.sio, app)
        self._setup_namespaces()
        self._setup_event_handlers()
        
    def _setup_namespaces(self):
        """Configurer les namespaces WebSocket."""
        # Namespace pour le monitoring du cluster
        monitoring_ns = MonitoringNamespace("/monitoring")
        self.sio.register_namespace(monitoring_ns)
        self.namespaces["monitoring"] = monitoring_ns
        
        # Namespace pour la santé du système
        health_ns = HealthNamespace("/health")
        self.sio.register_namespace(health_ns)
        self.namespaces["health"] = health_ns
        
    def _setup_event_handlers(self):
        """Configurer les gestionnaires d'événements globaux."""
        
        @self.sio.event
        async def connect(sid, environ):
            """Event appelé lors d'une connexion."""
            self.connected_clients.add(sid)
            await self.sio.emit("connection_confirmed", {
                "sid": sid,
                "timestamp": datetime.now().isoformat()
            }, room=sid)
            
        @self.sio.event
        async def disconnect(sid):
            """Event appelé lors d'une déconnexion."""
            self.connected_clients.discard(sid)
    
    async def start_redis_subscriber(self):
        """Démarrer l'abonnement Redis pour recevoir les événements."""
        self.pubsub = self.redis_client.pubsub(ignore_subscribe_messages=True)
        
        # S'abonner aux canaux Redis pour le monitoring et Celery
        self.pubsub.subscribe(
            "cluster:metrics",
            "cluster:health",
            "cluster:alerts",
            "celery:metrics"
        )
        
        # Boucle pour écouter les messages Redis
        asyncio.create_task(self._redis_listener())
        
    async def _redis_listener(self):
        """Écouter les messages Redis et les diffuser via WebSocket."""
        try:
            while True:
                message = self.pubsub.get_message(timeout=1.0)
                if message:
                    # Ne traiter que les messages userland
                    if message.get("type") != "message":
                        await asyncio.sleep(0)
                        continue

                    channel = message.get("channel")
                    if isinstance(channel, (bytes, bytearray)):
                        channel = channel.decode("utf-8", errors="ignore")

                    data_raw = message.get("data")
                    # Convertir en dict si possible
                    if isinstance(data_raw, (bytes, bytearray)):
                        data_raw = data_raw.decode("utf-8", errors="ignore")
                    if isinstance(data_raw, str):
                        try:
                            data = json.loads(data_raw)
                        except Exception:
                            data = {"message": data_raw}
                    elif isinstance(data_raw, dict):
                        data = data_raw
                    else:
                        data = {"data": data_raw}

                    # Diffuser l'événement aux clients connectés
                    if isinstance(channel, str) and channel:
                        # 1) Event global (compat)
                        event_name = f"redis_{channel.replace(':', '_')}"
                        await self.sio.emit(event_name, data)

                        # 2) Event vers namespaces dédiés
                        if channel == "cluster:metrics":
                            # Monitoring namespace
                            try:
                                await self.sio.emit("cluster_metrics", data, namespace="/monitoring")
                            except Exception:
                                pass
                        elif channel == "cluster:health":
                            # Health namespace
                            try:
                                await self.sio.emit("health_update", data, namespace="/health")
                            except Exception:
                                pass
                        elif channel == "cluster:alerts":
                            # Monitoring namespace
                            try:
                                await self.sio.emit("alerts_update", data, namespace="/monitoring")
                            except Exception:
                                pass
                    
                await asyncio.sleep(0.1)
                
        except Exception as e:
            logger.error(f"Erreur dans le listener Redis: {e}")
            await asyncio.sleep(5)
            # Redémarrer le listener en cas d'erreur
            asyncio.create_task(self._redis_listener())
    
    async def publish_event(self, channel: str, data: Dict[str, Any]):
        """Publier un événement sur Redis."""
        try:
            self.redis_client.publish(channel, json.dumps(data))
        except Exception as e:
            logger.error(f"Erreur lors de la publication sur Redis: {e}")
    
    async def broadcast_to_all(self, event: str, data: Dict[str, Any]):
        """Diffuser un événement à tous les clients connectés."""
        try:
            await self.sio.emit(event, data)
        except Exception as e:
            logger.error(f"Erreur lors de la diffusion: {e}")


class MonitoringNamespace(AsyncNamespace):
    """Namespace WebSocket pour le monitoring du cluster."""
    
    def __init__(self, namespace):
        super().__init__(namespace)
        self.logger = get_logger(__name__)
        
    async def on_connect(self, sid, environ):
        """Appelé lors de la connexion au namespace."""
        await self.emit("monitoring_connected", {
            "namespace": "/monitoring",
            "timestamp": datetime.now().isoformat()
        }, room=sid)
        
    async def on_disconnect(self, sid):
        """Appelé lors de la déconnexion du namespace."""
        pass
        
    async def on_request_cluster_status(self, sid, data):
        """Demande l'état du cluster."""
        try:
            from web.views.cluster_view import ClusterView
            
            cluster_view = ClusterView()
            overview = await cluster_view.get_cluster_overview()
            
            await self.emit("cluster_status_response", {
                "data": overview,
                "timestamp": datetime.now().isoformat()
            }, room=sid)
            
        except Exception as e:
            self.logger.error(f"Erreur lors de la récupération du statut du cluster: {e}")
            await self.emit("error", {
                "message": str(e),
                "timestamp": datetime.now().isoformat()
            }, room=sid)
    
    async def on_request_nodes_status(self, sid, data):
        """Demande l'état des nœuds."""
        try:
            from web.views.cluster_view import ClusterView
            
            cluster_view = ClusterView()
            nodes_data = await cluster_view.get_nodes_status()
            
            await self.emit("nodes_status_response", {
                "data": nodes_data,
                "timestamp": datetime.now().isoformat()
            }, room=sid)
            
        except Exception as e:
            self.logger.error(f"Erreur lors de la récupération du statut des nœuds: {e}")
            await self.emit("error", {
                "message": str(e),
                "timestamp": datetime.now().isoformat()
            }, room=sid)
    
    async def on_subscribe_to_updates(self, sid, data):
        """S'abonner aux mises à jour en temps réel."""
        # L'implémentation avec Redis pub/sub se fera via le WebSocketManager
        await self.emit("subscribed_to_updates", {
            "timestamp": datetime.now().isoformat()
        }, room=sid)


class HealthNamespace(AsyncNamespace):
    """Namespace WebSocket pour la santé du système."""
    
    def __init__(self, namespace):
        super().__init__(namespace)
        self.logger = get_logger(__name__)
        
    async def on_connect(self, sid, environ):
        """Appelé lors de la connexion au namespace."""
        await self.emit("health_connected", {
            "namespace": "/health",
            "timestamp": datetime.now().isoformat()
        }, room=sid)
        
    async def on_disconnect(self, sid):
        """Appelé lors de la déconnexion du namespace."""
        pass
        
    async def on_request_health(self, sid, data):
        """Demande l'état de santé."""
        try:
            from web.views.cluster_view import ClusterView
            import httpx
            
            # Récupérer l'état de santé
            cluster_view = ClusterView()
            overview = await cluster_view.get_cluster_overview()
            
            # Calculer le statut de santé
            cluster_stats = overview.get("cluster_stats", {})
            total_nodes = cluster_stats.get("total_nodes", 0)
            ready_nodes = cluster_stats.get("ready_nodes", 0)
            down_nodes = cluster_stats.get("down_nodes", 0)
            
            overall_status = "healthy"
            if down_nodes > 0:
                overall_status = "warning" if down_nodes <= total_nodes // 2 else "critical"
            
            health_data = {
                "status": "healthy",
                "timestamp": datetime.now().isoformat(),
                "version": "2.0.0",
                "cluster": {
                    "overall_status": overall_status,
                    "nodes_online": ready_nodes,
                    "nodes_total": total_nodes,
                    "nodes_down": down_nodes
                }
            }
            
            await self.emit("health_response", {
                "data": health_data,
                "timestamp": datetime.now().isoformat()
            }, room=sid)
            
        except Exception as e:
            self.logger.error(f"Erreur lors de la récupération de la santé: {e}")
            await self.emit("error", {
                "message": str(e),
                "timestamp": datetime.now().isoformat()
            }, room=sid)

