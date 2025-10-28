"""Stratégies d'équilibrage de charge.

Contient deux approches: round-robin et aléatoire pondéré.
Ces stratégies sont utilisées par le dispatcher pour choisir un worker.
"""

from typing import List, Dict, Optional
import random

class LoadBalancer:
    def __init__(self) -> None:
        self._rr_index: int = 0

    def pick_round_robin(self, nodes: List[str]) -> Optional[str]:
        """Retourne le prochain noeud en round-robin, ou None si liste vide."""
        if not nodes:
            return None
        node = nodes[self._rr_index % len(nodes)]
        self._rr_index += 1
        return node

    def pick_random_weighted(self, nodes: List[str], weights: Optional[Dict[str, float]] = None) -> Optional[str]:
        """Retourne un noeud aléatoire, biaisé par `weights` si fourni.

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

