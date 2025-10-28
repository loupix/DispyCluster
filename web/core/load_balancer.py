"""Stratégies d'équilibrage de charge intégrées dans l'interface web.

Algorithme adapté du core/load_balancer.py original.
"""

from typing import List, Dict, Optional
import random
import time
from datetime import datetime, timedelta

class LoadBalancer:
    def __init__(self) -> None:
        self._rr_index: int = 0
        self._node_weights: Dict[str, float] = {}
        self._node_performance: Dict[str, List[float]] = {}
        self._last_selection: Dict[str, datetime] = {}

    def pick_round_robin(self, nodes: List[str]) -> Optional[str]:
        """Retourne le prochain nœud en round-robin, ou None si liste vide."""
        if not nodes:
            return None
        node = nodes[self._rr_index % len(nodes)]
        self._rr_index += 1
        return node

    def pick_random_weighted(self, nodes: List[str], weights: Optional[Dict[str, float]] = None) -> Optional[str]:
        """Retourne un nœud aléatoire, biaisé par `weights` si fourni.

        weights: dict host -> poids positif; plus le poids est grand, plus
        la probabilité de sélection augmente.
        """
        if not nodes:
            return None
        if not weights:
            return random.choice(nodes)
        pool = []
        for n in nodes:
            w = max(0.0, float(weights.get(n, 1.0))) if weights else 1.0
            pool.extend([n] * int(max(1, round(w * 10))))
        return random.choice(pool) if pool else None

    def pick_least_connections(self, nodes: List[str], connection_counts: Dict[str, int]) -> Optional[str]:
        """Sélectionne le nœud avec le moins de connexions actives."""
        if not nodes:
            return None
        
        min_connections = float('inf')
        best_node = None
        
        for node in nodes:
            connections = connection_counts.get(node, 0)
            if connections < min_connections:
                min_connections = connections
                best_node = node
        
        return best_node

    def pick_least_recent(self, nodes: List[str]) -> Optional[str]:
        """Sélectionne le nœud utilisé le moins récemment."""
        if not nodes:
            return None
        
        oldest_time = datetime.min
        best_node = None
        
        for node in nodes:
            last_used = self._last_selection.get(node, datetime.min)
            if last_used < oldest_time:
                oldest_time = last_used
                best_node = node
        
        if best_node:
            self._last_selection[best_node] = datetime.now()
        
        return best_node

    def pick_best_performance(self, nodes: List[str], performance_metrics: Dict[str, Dict]) -> Optional[str]:
        """Sélectionne le nœud avec les meilleures performances."""
        if not nodes:
            return None
        
        best_score = float('inf')
        best_node = None
        
        for node in nodes:
            metrics = performance_metrics.get(node, {})
            cpu_usage = metrics.get('cpu_usage', 0)
            memory_usage = metrics.get('memory_usage', 0)
            response_time = metrics.get('response_time', 0)
            
            # Score composite (plus bas = mieux)
            score = (cpu_usage * 0.4 + memory_usage * 0.3 + response_time * 0.3)
            
            if score < best_score:
                best_score = score
                best_node = node
        
        return best_node

    def update_node_performance(self, node: str, response_time: float, success: bool) -> None:
        """Met à jour les métriques de performance d'un nœud."""
        if node not in self._node_performance:
            self._node_performance[node] = []
        
        # Garder seulement les 100 dernières mesures
        self._node_performance[node].append(response_time)
        if len(self._node_performance[node]) > 100:
            self._node_performance[node] = self._node_performance[node][-100:]
        
        # Ajuster le poids basé sur les performances
        if success:
            # Réduire le poids pour les nœuds performants
            self._node_weights[node] = max(0.1, self._node_weights.get(node, 1.0) * 0.95)
        else:
            # Augmenter le poids pour les nœuds en échec
            self._node_weights[node] = min(10.0, self._node_weights.get(node, 1.0) * 1.1)

    def get_node_average_performance(self, node: str) -> float:
        """Retourne la performance moyenne d'un nœud."""
        if node not in self._node_performance or not self._node_performance[node]:
            return 0.0
        
        return sum(self._node_performance[node]) / len(self._node_performance[node])

    def get_balanced_selection(self, nodes: List[str], strategy: str = "round_robin", 
                              weights: Optional[Dict[str, float]] = None,
                              connection_counts: Optional[Dict[str, int]] = None,
                              performance_metrics: Optional[Dict[str, Dict]] = None) -> Optional[str]:
        """Sélection intelligente basée sur la stratégie choisie."""
        
        if strategy == "round_robin":
            return self.pick_round_robin(nodes)
        elif strategy == "random_weighted":
            return self.pick_random_weighted(nodes, weights)
        elif strategy == "least_connections":
            return self.pick_least_connections(nodes, connection_counts or {})
        elif strategy == "least_recent":
            return self.pick_least_recent(nodes)
        elif strategy == "best_performance":
            return self.pick_best_performance(nodes, performance_metrics or {})
        else:
            return self.pick_round_robin(nodes)