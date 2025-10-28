"""Gestionnaire principal du cluster intégré dans l'interface web.

Algorithme adapté du core/cluster_manager.py original.
"""

from typing import List, Dict, Optional
from datetime import datetime
import asyncio
import httpx
from pathlib import Path
import yaml
import os
from web.config.logging_config import get_logger

# Configuration du logger
logger = get_logger(__name__)

class ClusterManager:
    def __init__(self, nodes: Optional[List[str]] = None) -> None:
        """Initialise le gestionnaire avec une liste optionnelle de nœuds.

        Args:
            nodes: liste d'hôtes (DNS ou IP) connus du cluster.
        """
        # Charger la config YAML si aucune liste fournie
        if nodes is None:
            config_path = Path(__file__).parents[1] / "nodes.yaml"
            if config_path.exists():
                try:
                    with open(config_path, "r", encoding="utf-8") as f:
                        cfg = yaml.safe_load(f) or {}
                    workers = cfg.get("workers", [])
                    self.master: Optional[str] = cfg.get("master")
                    self.nodes: List[str] = list(workers)
                except Exception:
                    self.master = None
                    self.nodes = []
            else:
                self.master = None
                self.nodes = []
        else:
            self.master = None
            self.nodes = nodes
        self.node_status: Dict[str, str] = {node: "unknown" for node in self.nodes}
        # Mode simulation: considérer les nœuds en ligne sans dépendre d'exporters
        self._simulate_nodes: bool = os.getenv("WEB_SIMULATE_NODES", "1") in ("1", "true", "True")
        self.node_metrics: Dict[str, Dict] = {}
        self.last_update: Dict[str, datetime] = {}
        # Stockage pour calculer l'utilisation CPU à partir des compteurs node_exporter
        self._cpu_prev: Dict[str, Dict[str, float]] = {}

    def set_nodes(self, nodes: List[str]) -> None:
        """Met à jour la liste des nœuds et préserve les statuts connus."""
        self.nodes = nodes
        self.node_status = {node: self.node_status.get(node, "unknown") for node in nodes}

    def mark_node_status(self, node: str, status: str) -> None:
        """Marque le statut d'un nœud.

        Exemples de `status`: "ready", "down", "busy".
        """
        if node not in self.node_status:
            self.node_status[node] = status
        else:
            self.node_status[node] = status
        self.last_update[node] = datetime.now()

    def get_available_nodes(self) -> List[str]:
        """Retourne la liste des nœuds marqués comme prêts."""
        return [n for n, s in self.node_status.items() if s == "ready"]

    def get_node_health(self, node: str) -> Dict:
        """Récupère l'état de santé d'un nœud."""
        return {
            "node": node,
            "status": self.node_status.get(node, "unknown"),
            "last_update": self.last_update.get(node),
            "metrics": self.node_metrics.get(node, {})
        }

    def update_node_metrics(self, node: str, metrics: Dict) -> None:
        """Met à jour les métriques d'un nœud."""
        self.node_metrics[node] = metrics
        self.last_update[node] = datetime.now()

    async def check_node_health(self, node: str) -> bool:
        """Vérifie la santé d'un nœud via HTTP."""
        if self._simulate_nodes:
            self.mark_node_status(node, "ready")
            return True
        try:
            # 1) Ping rapide (Windows)
            ping_ok = await self._ping_host(node)
            # 2) TCP 9100 (node_exporter)
            tcp_9100 = await self._tcp_check(node, 9100, timeout_s=1.5)
            # 3) TCP 22 (SSH) comme fallback
            tcp_22 = await self._tcp_check(node, 22, timeout_s=1.5)

            # logger.debug(f"Vérification {node}: ping={ping_ok}, tcp_9100={tcp_9100}, tcp_22={tcp_22}")

            if ping_ok or tcp_9100 or tcp_22:
                self.mark_node_status(node, "ready")
                # Optionnel: mise à jour métriques basiques si exporter dispo
                if tcp_9100:
                    logger.debug(f"Tentative de récupération des métriques pour {node}")
                    await self._try_update_basic_metrics(node)
                return True
            else:
                self.mark_node_status(node, "down")
                return False
        except Exception:
            self.mark_node_status(node, "down")
            return False

    async def check_all_nodes(self) -> Dict[str, bool]:
        """Vérifie la santé de tous les nœuds."""
        if self._simulate_nodes:
            for node in self.nodes:
                self.mark_node_status(node, "ready")
            return {node: True for node in self.nodes}

        tasks = [self.check_node_health(node) for node in self.nodes]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        health_status = {}
        for i, result in enumerate(results):
            node = self.nodes[i]
            if isinstance(result, Exception):
                health_status[node] = False
                self.mark_node_status(node, "down")
            else:
                health_status[node] = result
        
        return health_status

    async def _ping_host(self, host: str) -> bool:
        """Ping ICMP 1 paquet sous Windows (fallback silencieux)."""
        try:
            proc = await asyncio.create_subprocess_exec(
                "ping", "-n", "1", "-w", "1000", host,
                stdout=asyncio.subprocess.DEVNULL,
                stderr=asyncio.subprocess.DEVNULL,
            )
            await proc.wait()
            return proc.returncode == 0
        except Exception:
            return False

    async def _tcp_check(self, host: str, port: int, timeout_s: float = 2.0) -> bool:
        try:
            fut = asyncio.open_connection(host=host, port=port)
            reader, writer = await asyncio.wait_for(fut, timeout=timeout_s)
            writer.close()
            if hasattr(writer, 'wait_closed'):
                try:
                    await writer.wait_closed()
                except Exception:
                    pass
            return True
        except Exception:
            return False

    async def _try_update_basic_metrics(self, node: str) -> None:
        """Récupère quelques métriques simples depuis node_exporter si dispo."""
        try:
            async with httpx.AsyncClient(timeout=2.0) as client:
                resp = await client.get(f"http://{node}:9100/metrics")
                if resp.status_code != 200:
                    print(f"Erreur HTTP {resp.status_code} pour {node}")
                    return
                text = resp.text
                cpu_usage, mem_usage = self._parse_exporter_metrics(node, text)
                # print(f"Métriques {node}: CPU={cpu_usage:.1f}%, MEM={mem_usage:.1f}%")
                self.update_node_metrics(node, {"cpu_usage": cpu_usage, "memory_usage": mem_usage, "disk_usage": 0.0})
        except Exception as e:
            print(f"Erreur métriques {node}: {e}")
            return

    def _parse_exporter_metrics(self, node: str, metrics_text: str) -> (float, float):
        """Calcule CPU% et MEM% à partir des métriques node_exporter.

        CPU% est estimé via la variation des compteurs node_cpu_seconds_total sur toutes les CPUs
        entre deux scrapes. Si pas d'échantillon précédent, retourne 0.0 et enregistre l'état.

        MEM% est calculé via 1 - MemAvailable / MemTotal.
        """
        total_by_mode = {}
        mem_total = None
        mem_avail = None

        for line in metrics_text.splitlines():
            if not line or line.startswith('#'):
                continue
            if line.startswith('node_cpu_seconds_total'):
                # Exemple: node_cpu_seconds_total{cpu="0",mode="idle"} 1.234
                try:
                    parts = line.split('}')
                    labels = parts[0]
                    value = float(parts[1].strip())
                    # extraire mode="..."
                    if 'mode="' in labels:
                        mstart = labels.index('mode="') + 6
                        mend = labels.index('"', mstart)
                        mode = labels[mstart:mend]
                    else:
                        mode = 'unknown'
                    total_by_mode[mode] = total_by_mode.get(mode, 0.0) + value
                except Exception:
                    continue
            elif line.startswith('node_memory_MemTotal_bytes'):
                try:
                    mem_total = float(line.split(' ')[-1])
                except Exception:
                    pass
            elif line.startswith('node_memory_MemAvailable_bytes'):
                try:
                    mem_avail = float(line.split(' ')[-1])
                except Exception:
                    pass

        # Mémoire
        mem_usage = 0.0
        if mem_total and mem_avail is not None and mem_total > 0:
            mem_usage = max(0.0, min(100.0, (1.0 - (mem_avail / mem_total)) * 100.0))

        # CPU
        now_total = sum(total_by_mode.values()) if total_by_mode else None
        now_idle = total_by_mode.get('idle', None)
        cpu_usage = 0.0
        if now_total is not None and now_idle is not None:
            prev = self._cpu_prev.get(node)
            if prev:
                dt_total = now_total - prev.get('total', 0.0)
                dt_idle = now_idle - prev.get('idle', 0.0)
                if dt_total > 0:
                    cpu_usage = max(0.0, min(100.0, (1.0 - (dt_idle / dt_total)) * 100.0))
            # MàJ état précédent
            self._cpu_prev[node] = {'total': now_total, 'idle': now_idle}

        return cpu_usage, mem_usage

    async def check_infrastructure(self) -> Dict[str, Dict[str, bool]]:
        """Vérifie ports Dispy (9700/9701) et scheduler legacy (8083) sur le master."""
        target = self.master or "node13.lan"
        dispy_9700 = await self._tcp_check(target, 9700, timeout_s=1.5)
        dispy_9701 = await self._tcp_check(target, 9701, timeout_s=1.5)
        sched_8083 = await self._tcp_check(target, 8083, timeout_s=1.5)
        return {
            "dispy": {"9700": dispy_9700, "9701": dispy_9701},
            "scheduler": {"8083": sched_8083}
        }

    def submit_job(self, job_payload: dict) -> Optional[str]:
        """Sélectionne un nœud pour exécuter `job_payload`.

        Stratégie intelligente: choisit le nœud avec le moins de charge.
        """
        available = self.get_available_nodes()
        if not available:
            return None
        
        # Stratégie de sélection basée sur les métriques
        best_node = None
        best_score = float('inf')
        
        for node in available:
            metrics = self.node_metrics.get(node, {})
            cpu_usage = metrics.get('cpu_usage', 0)
            memory_usage = metrics.get('memory_usage', 0)
            
            # Score basé sur CPU et mémoire (plus bas = mieux)
            score = cpu_usage + memory_usage
            
            if score < best_score:
                best_score = score
                best_node = node
        
        return best_node or available[0]

    def get_cluster_stats(self) -> Dict:
        """Retourne les statistiques globales du cluster."""
        total_nodes = len(self.nodes)
        ready_nodes = len(self.get_available_nodes())
        down_nodes = total_nodes - ready_nodes
        
        # Calculer les métriques moyennes
        cpu_values = []
        memory_values = []
        disk_values = []
        
        for node in self.nodes:
            metrics = self.node_metrics.get(node, {})
            if metrics:
                cpu_values.append(metrics.get('cpu_usage', 0))
                memory_values.append(metrics.get('memory_usage', 0))
                disk_values.append(metrics.get('disk_usage', 0))
        
        return {
            "total_nodes": total_nodes,
            "ready_nodes": ready_nodes,
            "down_nodes": down_nodes,
            "cpu_usage_avg": sum(cpu_values) / len(cpu_values) if cpu_values else 0,
            "memory_usage_avg": sum(memory_values) / len(memory_values) if memory_values else 0,
            "disk_usage_avg": sum(disk_values) / len(disk_values) if disk_values else 0,
            "last_check": datetime.now().isoformat()
        }